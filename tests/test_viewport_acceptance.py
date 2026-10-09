"""Acceptance uses composited terminal cells, not un-clipped widget render trees.

The supplied normal-window captures have roughly 30 text rows. Their exact cell
size is unknown, so bracket that height/width instead of testing only 120x40.
"""

import asyncio

import pytest
from test_launcher_ui import book as shared_book
from test_ui_polish import MonitorProbe, monitor_ready
from textual.widgets import Button, Input, Select, Switch, TextArea

from agent_console.sources import SourceItem
from agent_console.ui.components import AGENTS
from agent_console.ui.launcher import ConfirmRun, LauncherApp, LauncherScreen
from agent_console.ui.timeline import Timeline

book = shared_book
MID_SIZES = [(110, 28), (120, 30), (120, 34)]
SIZES = [(80, 24), *MID_SIZES, (160, 50)]


def visible_text(app, widget=None):
    """Read the final terminal cells after clipping/overlays have been applied."""
    strips = app.screen._compositor.render_strips()
    if widget is None:
        return "\n".join(strip.text for strip in strips)
    region = widget.region
    return "\n".join(
        strip.crop(max(0, region.x), min(app.size.width, region.right)).text
        for strip in strips[max(0, region.y) : min(app.size.height, region.bottom)]
    )


def assert_inside(widget, parent):
    inner = parent.content_region
    region = widget.region
    assert inner.x <= region.x < region.right <= inner.right
    assert inner.y <= region.y < region.bottom <= inner.bottom


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("checked", [False, True])
async def test_launcher_visible_workflow(book, size, checked):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        app.query_one("#workspace", Input).value = "C:/synthetic/workspace"
        app.query_one("#prompt", TextArea).load_text("Synthetic preview")
        await pilot.pause()
        if checked:
            app.launcher.show_workspace_state("Valid")
            app.launcher.show_status(
                "Valid · COMPLETED · Process exit 0\n"
                "Permissions are not reported by this contract.\n"
                "Check success is not execution approval."
            )
            await pilot.pause()
        form = app.query_one("#launch-form")
        assert form.max_scroll_x == 0
        if size[0] >= 110:
            assert form.max_scroll_y == 0
            assert form.scroll_y == 0
            for selector in (
                "#profile",
                "#workspace",
                "#task",
                "#provider",
                "#model",
                "#verify",
                "#retries",
                "#allow-execution",
                "#prompt",
            ):
                assert_inside(app.query_one(selector), form)
            for label in ("Synthetic preview", "synthetic-model", "Developer", "Codex"):
                assert label in visible_text(app)
            assert app.query_one("#prompt").content_region.height >= 3
        else:
            app.query_one("#prompt").focus()
            await pilot.pause(0.3)
            assert "Synthetic preview" in visible_text(app)
        badge = app.query_one("#workspace-state")
        assert badge.region.right < size[0] // 2
        for selector in ("#check-workspace", "#start-run", "#quit-launcher"):
            button = app.query_one(selector, Button)
            assert_inside(button, app.screen)
            assert str(button.label) in visible_text(app, button)


def scenario(encode, state, long=False):
    async def source():
        events = [
            ("run.started", "main"),
            ("route.selected", "routing"),
            ("workspace.validated", "workspace"),
            ("git.status", "git"),
        ]
        if state != "check":
            events += [("developer.started", "developer"), ("codex.turn.started", "codex")]
        if long:
            events += [("tool.completed", "developer")] * 100
        if state not in ("running", "check"):
            events += [
                ("codex.turn.completed", "codex"),
                ("file.created", "developer"),
                ("developer.completed", "developer"),
                ("cleanup.completed", "cleanup"),
            ]
        if state != "running":
            events += [("run.completed" if state == "check" else "run." + state, "main")]
        for number, (event, component) in enumerate(events, 1):
            yield SourceItem(
                "line",
                encode(
                    number,
                    event,
                    component=component,
                    status=(
                        "completed"
                        if event in ("route.selected", "workspace.validated", "git.status")
                        else event.rsplit(".", 1)[-1]
                    ),
                    metadata={"path": "docs/example.md"} if event == "file.created" else {},
                ),
            )
        if state == "running":
            await asyncio.Event().wait()
        else:
            yield SourceItem("exit", 7 if state == "failed" else 0)

    return source()


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("state", ["check", "running", "completed", "failed", "cancelled"])
async def test_monitor_visible_agents_result_and_actions(encode_event, size, state):
    app = MonitorProbe(scenario(encode_event, state))
    async with app.run_test(size=size) as pilot:
        await monitor_ready(app, pilot, running=state == "running")
        body = app.query_one("#monitor-body")
        agents = app.query_one("#component-scroll")
        result = app.query_one("#activity")
        assert body.max_scroll_x == 0
        if size[0] >= 110:
            assert body.max_scroll_y == 0
        elif body.max_scroll_y:
            body.scroll_end(animate=False)
            await pilot.pause()
        assert agents.max_scroll_y == 0
        assert app.query_one("#result-scroll").max_scroll_y == 0
        assert_inside(agents, body)
        assert_inside(result, body)
        assert_inside(app.query_one("#summary"), body)
        for name in AGENTS:
            assert name.capitalize() in visible_text(app, agents)
        assert "Main" not in visible_text(app, agents)
        assert "Main" in visible_text(app, app.query_one("#system-status"))
        assert "main" in dict(next(iter(app.session.runs.values())).components)
        summary_text = visible_text(app, app.query_one("#summary"))
        assert "Events" in summary_text and "Issues" in summary_text
        assert "Process exit" not in summary_text and "docs/example.md" not in summary_text
        if state == "running":
            assert "Codex turn started" in visible_text(app, result)
            assert "Cancel Run" in visible_text(app)
        else:
            headline = "Run completed" if state == "check" else "Run " + state
            assert headline in visible_text(app, result)
            assert "Process exit " + ("7" if state == "failed" else "0") in visible_text(
                app, result
            )
            assert "Stream ended" in visible_text(app, result)
            assert not app.query_one("#cancel-run").display
            if state != "check":
                assert "docs/example.md" in visible_text(app, result)
        action = app.query_one("#cancel-run" if state == "running" else "#back-launcher")
        assert_inside(action, app.screen)
        assert str(action.label) in visible_text(app, action)
        assert app.query_one("#monitor-controls").region.y == body.region.bottom
        assert not app.query_one("#run-picker").display
        assert app.query_one("#run-heading").region.height == 1


@pytest.mark.parametrize("size", MID_SIZES)
async def test_long_timeline_yields_space_to_agents_and_result(encode_event, size):
    app = MonitorProbe(scenario(encode_event, "completed", long=True))
    async with app.run_test(size=size) as pilot:
        await monitor_ready(app, pilot)
        await pilot.pause(0.2)
        timeline = app.query_one(Timeline)
        assert timeline.max_scroll_y > 0
        assert "Run completed" in visible_text(app, timeline)
        assert timeline.content_region.height >= 5
        assert app.query_one("#component-scroll").max_scroll_y == 0
        assert "Training" in visible_text(app, app.query_one("#component-scroll"))
        assert "docs/example.md" in visible_text(app, app.query_one("#activity"))


async def test_short_wide_launcher_stays_two_columns(book):
    app = LauncherApp(book)
    async with app.run_test(size=(120, 30)) as pilot:
        for height in (28, 34, 36, 40, 30):
            await pilot.resize_terminal(120, height)
            assert not app.screen.has_class("narrow")
            assert app.query_one("#task").region.y == app.query_one("#provider").region.y
            assert app.query_one("#profile", Select).compact == (height < 36)


async def test_single_to_multi_run_keeps_selector_accessible(encode_event):
    next_run = asyncio.Event()

    async def source():
        yield SourceItem("line", encode_event(1, "run.completed", run_id="synthetic-first-run"))
        await next_run.wait()
        yield SourceItem("line", encode_event(1, "run.completed", run_id="synthetic-second-run"))

    app = MonitorProbe(source())
    async with app.run_test(size=(120, 30)) as pilot:
        await monitor_ready(app, pilot, running=True)
        picker = app.query_one("#run-picker", Select)
        assert not picker.display
        assert app.query_one("#run-status").tooltip == "synthetic-first-run"
        next_run.set()
        await monitor_ready(app, pilot)
        assert picker.display and picker.region.height == 1
        picker.focus()
        await pilot.press("enter")
        assert "synthetic-first-run" in visible_text(app)
        await pilot.press("up", "enter")
        assert picker.value == "synthetic-first-run"
        assert app.query_one("#run-status").tooltip == "synthetic-first-run"


@pytest.mark.parametrize("size", MID_SIZES)
async def test_mid_size_button_family_and_safe_confirmation(book, tmp_path, size):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        app.query_one("#workspace", Input).value = str(tmp_path)
        app.query_one("#prompt", TextArea).load_text("Synthetic preview")
        app.query_one("#allow-execution", Switch).value = True
        await pilot.pause()
        buttons = [
            app.query_one(selector, Button)
            for selector in ("#check-workspace", "#start-run", "#quit-launcher")
        ]
        assert len({button.region.height for button in buttons}) == 1
        assert len({button.styles.padding for button in buttons}) == 1
        assert all(button.styles.border_top[0] == "round" for button in buttons)
        await pilot.click("#start-run")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmRun)
        cancel = app.screen.query_one("#dismiss-confirm", Button)
        start = app.screen.query_one("#confirm-start", Button)
        assert cancel.has_focus and not cancel.disabled
        assert cancel.styles.border_top[1] != start.styles.border_top[1]
        for button in (cancel, start):
            assert_inside(button, app.screen)
            assert str(button.label) in visible_text(app, button)
        assert "ENABLED" in visible_text(app)
        await pilot.press("enter")
        assert isinstance(app.screen, LauncherScreen)
        assert not app.controller.active
        app.query_one("#model").focus()
        await pilot.pause()
        assert app.query_one("#model").styles.text_style.underline
        app.query_one("#profile").focus()
        await pilot.pause()
        assert app.query_one("#profile").query_one("SelectCurrent").styles.text_style.underline


async def test_live_action_position_and_disabled_legibility(encode_event):
    advance = asyncio.Event()
    finish = asyncio.Event()

    async def source():
        yield SourceItem("line", encode_event(1, "run.started"))
        await advance.wait()
        for number in range(2, 40):
            yield SourceItem("line", encode_event(number, "tool.completed", component="developer"))
        await finish.wait()
        yield SourceItem("line", encode_event(40, "run.completed"))
        yield SourceItem("exit", 0)

    app = MonitorProbe(source())
    async with app.run_test(size=(120, 30)) as pilot:
        await monitor_ready(app, pilot, running=True)
        cancel = app.query_one("#cancel-run", Button)
        back = app.query_one("#back-launcher", Button)
        original = cancel.region
        assert back.disabled and "Back to Launcher" in visible_text(app, back)
        assert back.styles.text_opacity == 1 and back.styles.color.a >= 0.6
        advance.set()
        await pilot.pause(0.3)
        assert cancel.region == original
        finish.set()
        await monitor_ready(app, pilot)
        assert not cancel.display and not back.disabled
        assert back.region.y == original.y


@pytest.mark.parametrize("size", [(120, 30), (160, 50)])
async def test_multiple_file_results_and_unknown_component_remain_visible(encode_event, size):
    async def source():
        yield SourceItem("line", encode_event(1, "run.started"))
        yield SourceItem("line", encode_event(2, "tool.completed", component="custom-worker"))
        for number in range(3, 6):
            yield SourceItem(
                "line",
                encode_event(
                    number,
                    "file.created",
                    component="developer",
                    metadata={"path": f"docs/example-{number}.md"},
                ),
            )
        yield SourceItem("line", encode_event(6, "run.completed"))
        yield SourceItem("exit", 0)

    app = MonitorProbe(source())
    async with app.run_test(size=size) as pilot:
        await monitor_ready(app, pilot)
        assert app.query_one("#result-scroll").max_scroll_y == 0
        assert app.query_one("#monitor-body").max_scroll_y == 0
        result = visible_text(app, app.query_one("#activity"))
        for number in range(3, 6):
            assert f"docs/example-{number}.md" in result
        assert "Events" not in result and "Errors" not in result
        assert "Custom-worker Completed" in visible_text(app, app.query_one("#system-status"))
        assert "Training" in visible_text(app, app.query_one("#component-scroll"))
