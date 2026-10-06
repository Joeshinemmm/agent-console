import asyncio
import sys

import pytest
from conftest import FIXTURES
from textual.widgets import Select, Static

from agent_console.app import AgentConsole
from agent_console.models.run import RunState
from agent_console.sources import SourceItem
from agent_console.sources.file import file_source
from agent_console.sources.subprocess import subprocess_source
from agent_console.state.reducer import apply_event
from agent_console.state.session import Session
from agent_console.ui.timeline import Timeline


async def settle(app, pilot):
    for _ in range(100):
        if app.session.ended:
            break
        await asyncio.sleep(0.02)
    assert app.session.ended
    app.refresh_session(force=True)
    await pilot.pause()


@pytest.mark.parametrize("size", [(120, 40), (80, 24)])
@pytest.mark.parametrize(
    "fixture,status",
    [
        ("successful_developer_run.jsonl", "COMPLETED"),
        ("failed_run.jsonl", "FAILED"),
    ],
)
async def test_tui_startup_and_panels(size, fixture, status):
    app = AgentConsole(file_source(FIXTURES / fixture), Session())
    async with app.run_test(size=size) as pilot:
        await settle(app, pilot)
        assert app.query_one(Timeline).row_count in (8, 12)
        assert status in str(app.query_one("#run-status", Static).render())
        assert app.query_one("#summary").region.bottom <= size[1]
        assert app.query_one("#activity").region.height > 0
        await pilot.press("q")


async def test_tui_multiple_run_selection(encode_event):
    async def source():
        for run_id in ("run-a", "run-b"):
            yield SourceItem("line", encode_event(1, "run.completed", run_id=run_id))

    app = AgentConsole(source(), Session())
    async with app.run_test() as pilot:
        await settle(app, pilot)
        picker = app.query_one(Select)
        assert picker.value == "run-b"
        picker.value = "run-a"
        await pilot.pause()
        assert app.query_one("#run-status").tooltip == "run-a"


async def test_tui_invalid_stream_shows_diagnostic():
    async def source():
        yield SourceItem("line", b"not-json")

    app = AgentConsole(source(), Session())
    async with app.run_test() as pilot:
        await settle(app, pilot)
        assert "Malformed JSON" in str(app.query_one("#diagnostics", Static).render())
        await pilot.press("q")
    assert app.return_value == 2


async def test_tui_quit_cancels_subprocess(encode_event):
    script = f"import sys,time; sys.stdout.buffer.write({encode_event()!r}); time.sleep(30)"
    session = Session()
    app = AgentConsole(subprocess_source([sys.executable, "-u", "-c", script]), session)
    async with app.run_test() as pilot:
        for _ in range(100):
            if session.runs:
                break
            await asyncio.sleep(0.02)
        assert session.runs
        await pilot.press("q")
    assert session.cancelled
    assert app.return_value == 130


async def test_live_timeline_preserves_reading_position(make_event):
    app = AgentConsole(file_source(FIXTURES / "successful_developer_run.jsonl"), Session())
    async with app.run_test(size=(100, 35)) as pilot:
        await settle(app, pilot)
        run = RunState("synthetic-run")
        for sequence in range(1, 41):
            run = apply_event(run, make_event(sequence)).state
        timeline = app.query_one(Timeline)
        timeline.show_run(run)
        await pilot.pause()
        timeline.move_cursor(row=5, scroll=False)
        timeline.scroll_to(y=3, animate=False, force=True)
        await pilot.pause()
        assert not timeline.is_vertical_scroll_end
        run = apply_event(run, make_event(41)).state
        timeline.show_run(run)
        await pilot.pause()
        assert timeline.scroll_y == 3
        assert timeline.cursor_row == 5
