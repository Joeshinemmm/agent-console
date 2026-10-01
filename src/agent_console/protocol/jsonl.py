import json
from dataclasses import dataclass

from agent_console.models.event import Event, ProtocolError

MAX_LINE_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class ParseResult:
    event: Event | None = None
    issue: str | None = None


def parse_line(line: bytes | str) -> ParseResult:
    """Skip blank lines; return bounded, payload-free diagnostics for bad input."""
    if isinstance(line, bytes):
        line = line.removesuffix(b"\n")
        if len(line) > MAX_LINE_BYTES:
            return ParseResult(issue="JSONL line exceeds 64 KiB; discarded.")
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return ParseResult(issue="JSONL line is not valid UTF-8; discarded.")
    else:
        line = line.removesuffix("\n")
        try:
            size = len(line.encode("utf-8"))
        except UnicodeEncodeError:
            return ParseResult(issue="JSONL line is not valid UTF-8; discarded.")
        if size > MAX_LINE_BYTES:
            return ParseResult(issue="JSONL line exceeds 64 KiB; discarded.")
    if not line.strip():
        return ParseResult()
    try:
        data = json.loads(line)
    except (ValueError, RecursionError):
        return ParseResult(issue="Malformed JSON; line discarded.")
    try:
        return ParseResult(event=Event.from_dict(data))
    except ProtocolError as error:
        return ParseResult(issue=str(error))


class LineFramer:
    """Frame arbitrary byte chunks without buffering unbounded lines."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.discarding = False

    def feed(self, chunk: bytes) -> list[bytes | None]:
        lines: list[bytes | None] = []
        parts = chunk.split(b"\n")
        for index, part in enumerate(parts):
            if not self.discarding:
                if len(self.buffer) + len(part) > MAX_LINE_BYTES:
                    self.buffer.clear()
                    self.discarding = True
                    lines.append(None)
                else:
                    self.buffer.extend(part)
            if index < len(parts) - 1:
                if not self.discarding:
                    lines.append(bytes(self.buffer))
                self.buffer.clear()
                self.discarding = False
        return lines

    def finish(self) -> list[bytes | None]:
        lines = [bytes(self.buffer)] if self.buffer and not self.discarding else []
        self.buffer.clear()
        self.discarding = False
        return lines
