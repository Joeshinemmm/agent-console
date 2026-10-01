import io
import json

import pytest
from conftest import payload

from agent_console.protocol.jsonl import MAX_LINE_BYTES, LineFramer, parse_line
from agent_console.sources.file import read_line


def test_valid_event():
    result = parse_line(json.dumps(payload()))
    assert result.issue is None
    assert result.event.sequence == 1
    assert result.event.timestamp_utc.utcoffset().total_seconds() == 0


@pytest.mark.parametrize("line", [b"", b"\n", " \r\n"])
def test_blank(line):
    assert parse_line(line).event is None
    assert parse_line(line).issue is None


@pytest.mark.parametrize("line", [b"{", b"hello", b"\xff", b"[]", b"null", b"42", "\ud800"])
def test_invalid_input(line):
    assert parse_line(line).issue


@pytest.mark.parametrize("field", list(payload()))
def test_missing_field(field):
    data = payload()
    del data[field]
    assert "Missing required field" in parse_line(json.dumps(data)).issue


@pytest.mark.parametrize("sequence", [0, -1, 1.5, True, "1", None, 2**63])
def test_invalid_sequence(sequence):
    data = payload()
    data["sequence"] = sequence
    assert "sequence" in parse_line(json.dumps(data)).issue


@pytest.mark.parametrize("version", [2, 100])
def test_unsupported_version(version):
    assert "Compatibility error" in parse_line(json.dumps(payload(schema_version=version))).issue


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", "1"),
        ("elapsed_ms", -1),
        ("elapsed_ms", float("nan")),
        ("elapsed_ms", float("inf")),
        ("elapsed_ms", True),
        ("duration_ms", -5),
        ("duration_ms", "5"),
        ("elapsed_ms", 10**400),
        ("timestamp_utc", "invalid"),
        ("timestamp_utc", "2026-01-01T00:00:00"),
        ("timestamp_utc", "2026-01-01T00:00:00+09:00"),
        ("message", None),
        ("metadata", []),
        ("component", "[red]bad"),
        ("run_id", "x" * 129),
        ("event_type", "bad\x1b[2J"),
    ],
)
def test_invalid_field(field, value):
    assert parse_line(json.dumps(payload(**{field: value}))).issue


def test_unknown_fields_and_event():
    result = parse_line(
        json.dumps(
            payload(event_type="future.signal.ready", component="future", future={"nested": 1})
        )
    )
    assert result.event.event_type == "future.signal.ready"


def test_payloads_not_retained():
    event = parse_line(
        json.dumps(
            payload(message="synthetic-private-prompt", metadata={"token": "synthetic-secret"})
        )
    ).event
    assert "synthetic-private" not in repr(event)
    assert "synthetic-secret" not in repr(event)
    assert not hasattr(event, "message")
    assert not hasattr(event, "metadata")


def test_oversized_line():
    assert "64 KiB" in parse_line(b"x" * (MAX_LINE_BYTES + 1)).issue


def test_deep_json_does_not_crash():
    assert parse_line("[" * 1100 + "]" * 1100).issue


def test_framer_chunks_utf8_crlf_and_eof():
    framer = LineFramer()
    raw = "한글\r\nsecond\nlast".encode()
    lines = []
    for byte in raw:
        lines.extend(framer.feed(bytes([byte])))
    lines.extend(framer.finish())
    assert lines == ["한글\r".encode(), b"second", b"last"]


def test_framer_discards_huge_line_and_recovers():
    framer = LineFramer()
    assert framer.feed(b"x" * (MAX_LINE_BYTES + 1)) == [None]
    assert len(framer.buffer) == 0
    assert framer.feed(b"y" * 100 + b"\n{}\n") == [b"{}"]
    assert framer.finish() == []


@pytest.mark.parametrize("extra", [0, 1])
def test_line_limit_consistent_across_file_and_stream(extra):
    raw = json.dumps(payload()).encode()
    raw += b" " * (MAX_LINE_BYTES + extra - len(raw)) + b"\n"
    from_file = read_line(io.BytesIO(raw))
    from_stream = LineFramer().feed(raw)
    if extra:
        assert from_file.kind == "issue"
        assert from_stream == [None]
        assert parse_line(raw).issue
    else:
        assert from_file.kind == "line"
        assert parse_line(from_file.value).event == parse_line(from_stream[0]).event
        assert parse_line(raw).event
