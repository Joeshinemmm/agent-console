import argparse
import asyncio
import math
import sys
from pathlib import Path

from agent_console import __version__
from agent_console.presentation import description
from agent_console.sources.file import file_source, stdin_source
from agent_console.sources.subprocess import subprocess_source
from agent_console.state.session import Session, consume


def nonnegative_float(value: str) -> float:
    try:
        result = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected a non-negative finite number.") from None
    if not math.isfinite(result) or result < 0:
        raise argparse.ArgumentTypeError("Expected a non-negative finite number.")
    return result


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Observe schema v1 agent JSONL streams.")
    cli.add_argument("--version", action="version", version=f"agent-console {__version__}")
    commands = cli.add_subparsers(dest="mode", required=True)
    replay = commands.add_parser("replay", help="Display a JSONL file (use - for stdin)")
    replay.add_argument("path", help="JSONL file or - for stdin")
    replay.add_argument(
        "--delay", type=nonnegative_float, default=0, help="Seconds between file lines"
    )
    run = commands.add_parser("run", help="Run an external command and observe stdout JSONL")
    for sub in (replay, run):
        display = sub.add_mutually_exclusive_group()
        display.add_argument("--plain", action="store_true", help="Print a final plain-text report")
        display.add_argument("--tui", action="store_true", help="Force interactive terminal UI")
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- executable [arguments ...]")
    return cli


def plain_report(session: Session) -> None:
    print("AGENT CONSOLE")
    for run in session.runs.values():
        print(f"\nRun {run.run_id} | {run.display_status(session.ended).upper()}")
        for event in run.events[-200:]:
            print(
                f"{event.sequence:>5} {event.elapsed_ms / 1000:>9.3f}s "
                f"{event.component:<14} {description(event)}"
            )
        if len(run.events) > 200:
            print("(Showing the latest 200 timeline events.)")
        print("Components: " + ", ".join(f"{name}={status}" for name, status in run.components))
        print(
            f"Elapsed {run.elapsed_ms / 1000:.3f}s | Events {run.event_count} "
            f"| Errors {run.error_count}"
        )
    print(
        f"\nIssues {session.issue_count} | stderr {session.stderr_bytes} bytes (text hidden) "
        f"| Process exit {session.process_exit if session.process_exit is not None else 'n/a'}"
    )
    for issue in session.diagnostics:
        print(f"! {issue}")


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    is_stdin = args.mode == "replay" and args.path == "-"
    if is_stdin and args.tui:
        cli.error("stdin replay uses plain output; use file replay or run for the interactive UI.")
    if args.mode == "replay":
        source = (
            stdin_source(sys.stdin.buffer) if is_stdin else file_source(Path(args.path), args.delay)
        )
    else:
        command = args.command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            cli.error("run requires an external command after --")
        source = subprocess_source(command)
    session = Session()
    try:
        if args.plain or is_stdin or (not args.tui and not sys.stdout.isatty()):
            asyncio.run(consume(source, session))
            plain_report(session)
            return session.exit_code
        from agent_console.app import AgentConsole

        return AgentConsole(source, session).run() or session.exit_code
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError):
        print("agent-console: input or terminal unavailable; try --plain.", file=sys.stderr)
        return 2
