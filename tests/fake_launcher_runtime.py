"""Synthetic public CLI producer; never imports or invokes an agent runtime."""

import argparse
import json
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--workspace", required=True)
parser.add_argument("--check-workspace", action="store_true")
parser.add_argument("--output", choices=["jsonl"], required=True)
parser.add_argument("--task", choices=["developer"])
parser.add_argument("--provider", choices=["codex"])
parser.add_argument("--codex-model")
parser.add_argument("--verify", choices=["none", "pytest", "web"])
parser.add_argument("--max-retries", type=int, choices=range(4))
parser.add_argument("--allow-execution", action="store_true")
parser.add_argument("prompt", nargs="?")
args = parser.parse_args()
sequence = 0


def emit(event_type, component="main", metadata=None):
    global sequence
    sequence += 1
    print(
        json.dumps(
            {
                "schema_version": 1,
                "event_id": f"synthetic-{sequence}",
                "run_id": "synthetic-launch",
                "sequence": sequence,
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "elapsed_ms": sequence * 10,
                "component": component,
                "event_type": event_type,
                "status": "started" if event_type.endswith("started") else "completed",
                "level": "error" if event_type.endswith("failed") else "info",
                "message": "Synthetic event",
                "duration_ms": None,
                "metadata": metadata or {},
            }
        ),
        flush=True,
    )


emit("run.started")
if Path(args.workspace).name == "denied" or args.prompt == "synthetic-fail":
    emit("run.failed")
    raise SystemExit(7)
emit("workspace.validated", metadata={"external": True})
emit("git.status", metadata={"git_repository": True, "dirty": False})
if not args.check_workspace:
    emit("developer.started", "developer")
    if args.prompt == "synthetic-wait":
        time.sleep(30)
    if args.allow_execution:
        target = Path(args.workspace) / "docs" / "example.md"
        target.parent.mkdir(exist_ok=True)
        target.write_text("Synthetic launcher test.\n", encoding="utf-8")
        emit("file.created", "developer", {"path": "docs/example.md"})
    emit("developer.completed", "developer")
emit("run.completed")
