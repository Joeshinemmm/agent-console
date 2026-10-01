import asyncio
import io
import sys

import pytest
from conftest import FIXTURES

from agent_console.models.run import Status
from agent_console.protocol.jsonl import MAX_LINE_BYTES
from agent_console.sources.file import file_source, stdin_source
from agent_console.sources.subprocess import subprocess_source
from agent_console.state.session import Session, consume


@pytest.mark.parametrize(
    "filename,status,count,errors",
    [
        ("successful_developer_run.jsonl", Status.COMPLETED, 12, 0),
        ("failed_run.jsonl", Status.FAILED, 8, 2),
    ],
)
async def test_file_replay(filename, status, count, errors):
    session = Session()
    await consume(file_source(FIXTURES / filename), session)
    run = next(iter(session.runs.values()))
    assert run.status == status
    assert run.event_count == count
    assert run.error_count == errors
    assert session.ended


async def test_missing_file(tmp_path):
    session = Session()
    await consume(file_source(tmp_path / "missing.jsonl"), session)
    assert session.exit_code == 2
    assert "Cannot read" in session.diagnostics[0]


async def test_stdin_stream(encode_event):
    session = Session()
    await consume(stdin_source(io.BytesIO(encode_event(1, "run.completed"))), session)
    assert session.exit_code == 0


async def test_file_recovers_after_oversized_and_bad_lines(tmp_path, encode_event):
    path = tmp_path / "events.jsonl"
    path.write_bytes(
        b"x" * (MAX_LINE_BYTES + 30)
        + b"\n\ninvalid\n"
        + encode_event(1, "run.completed").rstrip(b"\n")
    )
    session = Session()
    await consume(file_source(path), session)
    assert next(iter(session.runs.values())).event_count == 1
    assert session.protocol_errors == 2


async def test_subprocess_real_pipes_and_large_stderr(encode_event):
    raw = encode_event(1, "run.completed")
    script = (
        "import sys; sys.stderr.buffer.write(b'synthetic-private' * 20000); "
        f"sys.stderr.flush(); sys.stdout.buffer.write({raw!r}); sys.stdout.flush()"
    )
    session = Session()
    await asyncio.wait_for(
        consume(subprocess_source([sys.executable, "-u", "-c", script]), session), 10
    )
    assert session.exit_code == 0
    assert session.stderr_bytes == len(b"synthetic-private") * 20000
    assert "synthetic-private" not in repr(session)


async def test_subprocess_delivers_before_exit(encode_event):
    raw = encode_event()
    script = (
        f"import sys,time; sys.stdout.buffer.write({raw!r}); sys.stdout.flush(); time.sleep(30)"
    )
    source = subprocess_source([sys.executable, "-u", "-c", script])
    try:
        first = await asyncio.wait_for(anext(source), 5)
        assert first.kind == "line"
        assert first.value == raw.rstrip(b"\n")
    finally:
        await asyncio.wait_for(source.aclose(), 6)


async def test_subprocess_midstream_exit(encode_event):
    script = f"import sys; sys.stdout.buffer.write({encode_event()!r}); sys.exit(9)"
    session = Session()
    await consume(subprocess_source([sys.executable, "-u", "-c", script]), session)
    assert session.exit_code == 9
    assert next(iter(session.runs.values())).display_status(True) == Status.INCOMPLETE


async def test_subprocess_no_terminal_event(encode_event):
    script = f"import sys; sys.stdout.buffer.write({encode_event()!r})"
    session = Session()
    await consume(subprocess_source([sys.executable, "-u", "-c", script]), session)
    assert session.process_exit == 0
    assert session.exit_code == 2


async def test_subprocess_invalid_then_unterminated_json(encode_event):
    raw = b"bad\n" + encode_event(1, "run.completed").rstrip(b"\n")
    script = f"import sys; sys.stdout.buffer.write({raw!r})"
    session = Session()
    await consume(subprocess_source([sys.executable, "-u", "-c", script]), session)
    assert next(iter(session.runs.values())).status == Status.COMPLETED
    assert session.protocol_errors == 1


async def test_subprocess_oversized_line_recovers(encode_event):
    script = (
        f"import sys; sys.stdout.buffer.write(b'x' * {MAX_LINE_BYTES + 100} + b'\\n'); "
        f"sys.stdout.buffer.write({encode_event(1, 'run.completed')!r})"
    )
    session = Session()
    await consume(subprocess_source([sys.executable, "-u", "-c", script]), session)
    assert next(iter(session.runs.values())).event_count == 1
    assert session.protocol_errors == 1


async def test_subprocess_start_failure():
    session = Session()
    await consume(subprocess_source(["nonexistent-synthetic-executable-12345"]), session)
    assert session.process_exit == 127
    assert "Cannot start" in session.diagnostics[0]


async def test_cancellation_stops_child(tmp_path):
    marker = tmp_path / "should-not-exist"
    script = f"import time,pathlib; time.sleep(1.5); pathlib.Path({str(marker)!r}).touch()"
    session = Session()
    task = asyncio.create_task(consume(subprocess_source([sys.executable, "-c", script]), session))
    await asyncio.sleep(0.25)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 6)
    await asyncio.sleep(1.5)
    assert not marker.exists()
    assert session.cancelled
    assert session.exit_code == 130


async def test_command_arguments_are_not_shell_interpreted(encode_event):
    raw = encode_event(1, "run.completed")
    script = (
        f"import sys; assert sys.argv[1] == 'x & echo unsafe'; sys.stdout.buffer.write({raw!r})"
    )
    session = Session()
    await consume(subprocess_source([sys.executable, "-c", script, "x & echo unsafe"]), session)
    assert session.exit_code == 0
