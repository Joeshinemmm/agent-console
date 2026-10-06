import asyncio

import pytest
from test_launcher_ui import book as shared_book
from test_launcher_ui import fill, settle
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Select, Static, TextArea

from agent_console.app import AgentConsole
from agent_console.models.run import Status
from agent_console.sources import SourceItem
from agent_console.state.session import Session
from agent_console.ui.controls import ActionButton
from agent_console.ui.launcher import ConfirmRun, LauncherApp, LauncherScreen
from agent_console.ui.monitor import MonitorScreen
from agent_console.ui.timeline import Timeline

SIZES = [(80, 24), (120, 40), (160, 50)]
book = shared_book


@pytest.mark.parametrize("size", SIZES)
async def test_launcher_responsive_access(book, size):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        form = app.query_one("#launch-form")
        task = app.query_one("#task")
        provider = app.query_one("#provider")
        prompt = app.query_one("#prompt", TextArea)
        if size[0] >= 110:
            assert task.region.y == provider.region.y
            assert task.region.right < provider.region.x
            assert form.max_scroll_y == 0
            assert prompt.region.bottom <= form.region.bottom
        else:
            assert task.region.y < provider.region.y
            assert form.max_scroll_y > 0
            prompt.focus()
            await pilot.pause(0.3)
            assert form.region.y <= prompt.region.y < form.region.bottom
            await pilot.click("#prompt")
            await pilot.press("s", "y", "n")
            assert prompt.text == "syn"
        assert form.max_scroll_x == 0
        for name in ("check-workspace", "start-run", "quit-launcher"):
            button = app.query_one("#" + name)
            assert 0 <= button.region.x < button.region.right <= size[0]
            assert button.region.bottom <= size[1] - 1


@pytest.mark.parametrize("size", SIZES)
async def test_launcher_tab_order(book, size):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        app.query_one("#profile").focus()
        await pilot.pause()
        for name in (
            "workspace",
            "task",
            "provider",
            "model",
            "verify",
            "retries",
            "allow-execution",
            *(("prompt-smaller",) if size[1] >= 46 else ()),
            "prompt-larger",
            "prompt-auto",
            "prompt",
            "check-workspace",
            "start-run",
            "quit-launcher",
        ):
            await pilot.press("tab")
            assert app.focused.id == name
        await pilot.press("shift+tab")
        assert app.focused.id == "start-run"


async def test_launcher_resize_preserves_input(book, tmp_path):
    app = LauncherApp(book)
    async with app.run_test(size=(160, 50)) as pilot:
        fill(app, tmp_path)
        app.query_one("#model", Input).value = "synthetic-override"
        await pilot.resize_terminal(80, 24)
        assert "narrow" in app.screen.classes
        await pilot.resize_terminal(120, 40)
        assert "narrow" not in app.screen.classes
        assert app.query_one("#model", Input).value == "synthetic-override"
        assert app.query_one("#prompt", TextArea).text == "synthetic task"


@pytest.mark.parametrize("denied", [False, True])
async def test_workspace_state_badge(book, tmp_path, denied):
    workspace = tmp_path / ("denied" if denied else "allowed")
    workspace.mkdir()
    app = LauncherApp(book)
    async with app.run_test(size=(120, 40)) as pilot:
        badge = app.query_one("#workspace-state", Static)
        assert "Unchecked" in str(badge.render())
        fill(app, workspace)
        await pilot.click("#check-workspace")
        assert "Checking" in str(badge.render())
        await settle(app, pilot)
        await pilot.click("#back-launcher")
        assert ("Invalid" if denied else "Valid") in str(badge.render())
        app.query_one("#workspace", Input).value = str(tmp_path)
        await pilot.pause()
        assert "Unchecked" in str(badge.render())


async def test_execution_and_verify_context(book):
    app = LauncherApp(book)
    async with app.run_test(size=(120, 40)) as pilot:
        label = app.query_one("#execution-state", Static)
        assert "OFF" in str(label.render())
        await pilot.click("#allow-execution")
        assert "ENABLED" in str(label.render())
        assert "enabled" in label.classes
        app.query_one("#verify", Select).value = "web"
        await pilot.pause()
        assert "pytest + local web" in str(app.query_one("#verify-help", Static).render())
        await pilot.pause(0.3)
        await pilot.click("#allow-execution")
        assert "OFF" in str(label.render())


@pytest.mark.parametrize("size", SIZES)
async def test_modal_focus_mouse_keyboard_safety(book, tmp_path, size):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        fill(app, tmp_path)
        await pilot.click("#start-run")
        await pilot.pause()
        modal = app.screen
        cancel = modal.query_one("#dismiss-confirm", Button)
        start = modal.query_one("#confirm-start", Button)
        assert not cancel.disabled and cancel.has_focus
        assert not cancel.styles.text_style.reverse
        assert cancel.styles.border_top[0] == "solid"
        assert cancel.region.bottom <= size[1]
        await pilot.click(offset=(0, 0))
        assert app.screen is modal and not cancel.disabled
        assert not cancel.styles.text_style.reverse
        cancel.focus()
        await pilot.press("tab")
        assert start.has_focus and not start.disabled
        assert not start.styles.text_style.reverse
        assert cancel.styles.border_top[0] == "round"
        await pilot.press("shift+tab")
        assert cancel.has_focus
        await pilot.press("enter")
        assert isinstance(app.screen, LauncherScreen)
        assert not app.controller.active and not app.controller.session.runs
        await pilot.click("#start-run")
        assert isinstance(app.screen, ConfirmRun)
        await pilot.press("escape")
        assert isinstance(app.screen, LauncherScreen)
        assert not app.controller.active
        await pilot.pause(0.3)
        await pilot.click("#start-run")
        await pilot.click("#dismiss-confirm")
        assert isinstance(app.screen, LauncherScreen)
        assert not app.controller.active


class ButtonProbe(App):
    def compose(self) -> ComposeResult:
        yield ActionButton("Cancel", id="probe-cancel")
        yield ActionButton("Start", variant="primary", id="probe-start")


async def test_button_hover_pressed_disabled_distinct():
    app = ButtonProbe()
    async with app.run_test() as pilot:
        button = app.query_one("#probe-cancel", Button)
        button.focus()
        focused = button.styles.border_top
        assert not button.styles.text_style.reverse
        await pilot.hover("#probe-cancel")
        assert button.mouse_hover and not button.disabled
        button.active_effect_duration = 1
        await pilot.click("#probe-cancel")
        assert button.has_class("-active")
        assert button.styles.text_style.underline
        assert not button.styles.text_style.reverse
        button.remove_class("-active")
        app.query_one("#probe-start").focus()
        await pilot.hover("#probe-start")
        assert not button.has_focus
        assert button.styles.border_top != focused
        button.disabled = True
        await pilot.pause()
        assert button.styles.text_opacity == 1
        assert button.styles.color.a == 0.6
        assert not button.styles.text_style.reverse
        assert button.styles.border_top != focused


class MonitorProbe(App):
    def __init__(self, source):
        self.session = Session()
        self.monitor = MonitorScreen(source, self.session, on_back=lambda: None)
        super().__init__()

    def get_default_screen(self):
        return self.monitor


async def monitor_ready(app, pilot, *, running=False):
    for _ in range(100):
        if app.session.ended or (running and app.session.runs):
            break
        await asyncio.sleep(0.01)
    app.monitor.refresh_session(force=True)
    await pilot.pause()


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("state", ["running", "completed", "failed", "cancelled"])
async def test_monitor_states_and_layout(encode_event, size, state):
    async def source():
        yield SourceItem("line", encode_event(1, "run.started"))
        yield SourceItem("line", encode_event(2, "developer.started", component="developer"))
        yield SourceItem(
            "line", encode_event(3, "file.created", metadata={"path": "docs/example.md"})
        )
        if state == "running":
            await asyncio.Event().wait()
        else:
            yield SourceItem("line", encode_event(4, "cleanup.completed", component="cleanup"))
            yield SourceItem("line", encode_event(5, "run." + state))
            yield SourceItem("exit", 7 if state == "failed" else 0)

    app = MonitorProbe(source())
    async with app.run_test(size=size) as pilot:
        await monitor_ready(app, pilot, running=state == "running")
        activity = app.query_one("#activity", Static)
        cancel = app.query_one("#cancel-run", Button)
        back = app.query_one("#back-launcher", Button)
        assert cancel.display == (state == "running")
        assert back.disabled == (state == "running")
        if state != "running":
            assert "Run " + state in str(activity.render())
            assert "Cleanup completed" not in str(activity.render())
            assert "docs/example.md" in str(activity.render())
            assert back.variant == "primary"
            assert next(iter(app.session.runs.values())).activity.component == "cleanup"
        assert app.query_one("#summary").region.bottom <= size[1]
        assert back.region.bottom <= size[1] - 1
        assert app.query_one("#monitor-body").max_scroll_x == 0
        assert 4 <= app.query_one(Timeline).region.height <= 8
        timeline = app.query_one(Timeline)
        timeline.focus()
        await pilot.pause()
        assert timeline.styles.border_top[0] == "solid"
        result_panel = app.query_one("#result-scroll")
        result_panel.focus()
        await pilot.pause()
        assert result_panel.styles.border_top[0] == "solid"
        assert timeline.styles.border_top[0] == "round"


async def test_terminal_before_process_end_keeps_cancel(encode_event):
    async def source():
        yield SourceItem("line", encode_event(1, "run.completed"))
        await asyncio.Event().wait()

    app = MonitorProbe(source())
    async with app.run_test() as pilot:
        await monitor_ready(app, pilot, running=True)
        assert app.query_one("#cancel-run", Button).display
        assert not app.query_one("#cancel-run", Button).disabled
        assert app.query_one("#back-launcher", Button).disabled
        assert "Waiting for process" in str(app.query_one("#activity", Static).render())
        await pilot.click("#cancel-run")
        assert app.session.cancelled
        assert not app.query_one("#cancel-run", Button).display


@pytest.mark.parametrize("size", SIZES)
async def test_monitor_keyboard_navigation_and_compact_activity(encode_event, size):
    async def source():
        yield SourceItem("line", encode_event(1, "developer.started", component="developer"))
        await asyncio.Event().wait()

    app = MonitorProbe(source())
    async with app.run_test(size=size) as pilot:
        await monitor_ready(app, pilot, running=True)
        app.query_one(Timeline).focus()
        await pilot.pause()
        for name in ("component-scroll", "result-scroll", "system-status", "summary", "cancel-run"):
            await pilot.press("tab")
            assert app.focused.id == name
        await pilot.press("shift+tab")
        assert app.focused.id == "summary"
        activity = app.query_one("#activity", Static)
        assert "Developer\nDeveloper started" in str(activity.render())
        assert activity.content_region.height >= 2


@pytest.mark.parametrize("count", [5, 200])
async def test_timeline_height_and_scroll(encode_event, count):
    async def source():
        for number in range(1, count):
            yield SourceItem("line", encode_event(number, "tool.completed"))
        yield SourceItem("line", encode_event(count, "run.completed"))

    app = MonitorProbe(source())
    async with app.run_test(size=(160, 50)) as pilot:
        await monitor_ready(app, pilot)
        timeline = app.query_one(Timeline)
        assert timeline.row_count == count
        assert timeline.region.height == min(count + 3, 18)
        if count == 200:
            assert timeline.max_scroll_y > 0
            timeline.focus()
            await pilot.pause()
            await pilot.press("ctrl+home")
            await pilot.pause(0.3)
            assert timeline.scroll_y == 0


async def test_full_run_selector_and_short_header(encode_event):
    ids = ["synthetic-long-run-identifier-a", "synthetic-long-run-identifier-b"]

    async def source():
        for name in ids:
            yield SourceItem("line", encode_event(1, "run.completed", run_id=name))

    app = AgentConsole(source(), Session())
    async with app.run_test() as pilot:
        await monitor_ready(app, pilot)
        picker = app.query_one("#run-picker", Select)
        assert picker.value == ids[-1]
        assert ids[-1] not in str(app.query_one("#run-status", Static).render())
        assert app.query_one("#run-status").tooltip == ids[-1]
        picker.value = ids[0]
        await pilot.pause()
        assert app.query_one("#run-status").tooltip == ids[0]


def test_components_keep_idle_visible_after_active(make_event):
    from agent_console.models.run import RunState
    from agent_console.ui.components import Components

    widget = Components()
    run = RunState("synthetic", components=(("test", Status.IDLE), ("developer", Status.RUNNING)))
    widget.show_run(run)
    table = widget.render()._renderable
    assert [text.plain for text in table.columns[0]._cells] == [
        "Developer",
        "Codex",
        "Test",
        "Browser",
        "Desktop",
        "Training",
    ]
    assert table.columns[0]._cells[-1].style == "dim"
