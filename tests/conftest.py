import json
from pathlib import Path

import pytest

from agent_console.models.event import Event

FIXTURES = Path(__file__).parent / "fixtures"


def payload(sequence=1, event_type="run.started", component="main", **changes):
    data = {
        "schema_version": 1,
        "event_id": f"synthetic-event-{sequence}",
        "run_id": "synthetic-run",
        "sequence": sequence,
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "elapsed_ms": sequence * 10.0,
        "component": component,
        "event_type": event_type,
        "status": event_type.rsplit(".", 1)[-1],
        "level": "info",
        "message": event_type,
        "duration_ms": None,
        "metadata": {},
    }
    data.update(changes)
    return data


@pytest.fixture
def make_event():
    def make(*args, **kwargs):
        return Event.from_dict(payload(*args, **kwargs))

    return make


@pytest.fixture
def encode_event():
    def encode(*args, **kwargs):
        return json.dumps(payload(*args, **kwargs)).encode() + b"\n"

    return encode
