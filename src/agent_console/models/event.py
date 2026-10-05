"""Schema v1 validation with an intentionally payload-free consumer model."""

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from agent_console.models.details import EventDetails

TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class ProtocolError(ValueError):
    """Safe diagnostic: never includes untrusted input values."""


def token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ProtocolError(f"Invalid {field}: expected a bounded identifier.")
    return value


def number(value: Any, field: str) -> float:
    if type(value) not in (int, float):
        raise ProtocolError(f"Invalid {field}: expected a non-negative finite number.")
    try:
        result = float(value)
    except OverflowError:
        raise ProtocolError(f"Invalid {field}: number is too large.") from None
    if not math.isfinite(result) or result < 0:
        raise ProtocolError(f"Invalid {field}: expected a non-negative finite number.")
    return result


@dataclass(frozen=True, slots=True)
class Event:
    schema_version: int
    event_id: str
    run_id: str
    sequence: int
    timestamp_utc: datetime
    elapsed_ms: float
    component: str
    event_type: str
    status: str
    level: str
    duration_ms: float | None
    details: EventDetails = EventDetails()

    @classmethod
    def from_dict(cls, data: Any) -> "Event":
        if not isinstance(data, dict):
            raise ProtocolError("Event must be a JSON object.")
        required = (
            "schema_version",
            "event_id",
            "run_id",
            "sequence",
            "timestamp_utc",
            "elapsed_ms",
            "component",
            "event_type",
            "status",
            "level",
            "message",
            "duration_ms",
            "metadata",
        )
        for field in required:
            if field not in data:
                raise ProtocolError(f"Missing required field: {field}.")
        if type(data["schema_version"]) is not int:
            raise ProtocolError("Invalid schema_version: expected integer 1.")
        if data["schema_version"] != 1:
            raise ProtocolError("Compatibility error: only schema_version 1 is supported.")
        sequence = data["sequence"]
        if type(sequence) is not int or not 1 <= sequence <= 2**63 - 1:
            raise ProtocolError("Invalid sequence: expected a positive 64-bit integer.")
        stamp = data["timestamp_utc"]
        if not isinstance(stamp, str) or len(stamp) > 64:
            raise ProtocolError("Invalid timestamp_utc: expected an ISO 8601 UTC timestamp.")
        try:
            timestamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if timestamp.utcoffset() != timedelta(0):
                raise ValueError
        except ValueError:
            raise ProtocolError(
                "Invalid timestamp_utc: expected an ISO 8601 UTC timestamp."
            ) from None
        if not isinstance(data["message"], str):
            raise ProtocolError("Invalid message: expected a string.")
        if not isinstance(data["metadata"], dict):
            raise ProtocolError("Invalid metadata: expected an object.")
        duration = data["duration_ms"]
        return cls(
            schema_version=1,
            event_id=token(data["event_id"], "event_id"),
            run_id=token(data["run_id"], "run_id"),
            sequence=sequence,
            timestamp_utc=timestamp,
            elapsed_ms=number(data["elapsed_ms"], "elapsed_ms"),
            component=token(data["component"], "component"),
            event_type=token(data["event_type"], "event_type"),
            status=token(data["status"], "status"),
            level=token(data["level"], "level"),
            duration_ms=None if duration is None else number(duration, "duration_ms"),
            details=EventDetails.from_metadata(data["event_type"], data["metadata"]),
        )
