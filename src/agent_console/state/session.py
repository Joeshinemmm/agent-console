import asyncio
from collections import deque
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import dataclass, field

from agent_console.models.run import RunState, Status
from agent_console.protocol.jsonl import parse_line
from agent_console.sources import SourceItem
from agent_console.state.reducer import apply_event


@dataclass
class Session:
    runs: dict[str, RunState] = field(default_factory=dict)
    diagnostics: deque[str] = field(default_factory=lambda: deque(maxlen=100))
    issue_count: int = 0
    protocol_errors: int = 0
    stderr_bytes: int = 0
    process_exit: int | None = None
    ended: bool = False
    cancelled: bool = False
    revision: int = 0
    max_runs: int = 20
    max_events: int = 10_000

    def report(self, message: str, *, error: bool = True) -> None:
        self.issue_count += 1
        self.protocol_errors += error
        self.diagnostics.append(message)
        self.revision += 1

    def accept(self, item: SourceItem) -> None:
        if item.kind == "stderr":
            self.stderr_bytes += int(item.value)
        elif item.kind == "exit":
            self.process_exit = int(item.value)
            if self.process_exit:
                self.report(f"Subprocess exited with code {self.process_exit}.")
        elif item.kind == "issue":
            self.report(str(item.value))
        else:
            assert isinstance(item.value, (str, bytes))
            parsed = parse_line(item.value)
            if parsed.issue:
                self.report(parsed.issue)
            elif parsed.event:
                event = parsed.event
                if event.run_id not in self.runs and len(self.runs) >= self.max_runs:
                    self.report("Session run limit reached; event discarded.")
                    return
                previous = self.runs.get(event.run_id, RunState(event.run_id))
                result = apply_event(previous, event, max_events=self.max_events)
                self.runs[event.run_id] = result.state
                if result.issue:
                    benign = result.issue.startswith(("Duplicate event", "Out-of-order"))
                    self.report(result.issue, error=not benign)
        self.revision += 1

    def finish(self) -> None:
        self.ended = True
        if not self.runs:
            self.report("Stream ended without a valid event.")
        for run in self.runs.values():
            if not run.has_terminal_event:
                self.report("A run ended without a terminal event; status is Incomplete.")
            sequences = [event.sequence for event in run.events]
            if sequences and any(sequence != index for index, sequence in enumerate(sequences, 1)):
                self.report("A run has sequence gaps; some events may be missing.")
        self.revision += 1

    @property
    def exit_code(self) -> int:
        if self.cancelled:
            return 130
        if self.process_exit:
            return self.process_exit if 1 <= self.process_exit <= 125 else 1
        if self.protocol_errors or not self.runs:
            return 2
        if any(run.status != Status.COMPLETED for run in self.runs.values()):
            return 1
        return 0


async def consume(source: AsyncGenerator[SourceItem, None], session: Session) -> None:
    try:
        async with aclosing(source):
            async for item in source:
                session.accept(item)
                await asyncio.sleep(0)
    except asyncio.CancelledError:
        session.cancelled = True
        raise
    finally:
        session.finish()
