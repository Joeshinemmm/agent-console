import asyncio
import sys
from pathlib import Path

import pytest
from textual.widgets import Button, Checkbox, Input, Select, Static, TextArea

from agent_console.launcher.profile import ProfileBook, RuntimeProfile
from agent_console.ui.launcher import ConfirmRun, LauncherApp, LauncherScreen
from agent_console.ui.monitor import MonitorScreen


@pytest.fixture
def book():
    profile = RuntimeProfile(
        "synthetic",
        sys.executable,
        str(Path(__file__).with_name("fake_launcher_runtime.py")),
        "synthetic-model",
    )
    return ProfileBook({profile.name: profile}, profile.name)


async def settle(app, pilot):
    for _ in range(200):
        if app.controller.session.ended:
            break
        await asyncio.sleep(0.02)
    assert app.controller.session.ended
    app.screen.refresh_session(force=True)
    await pilot.pause()


def fill(app, tmp_path, prompt="synthetic task"):
    app.launcher.query_one("#workspace", Input).value = str(tmp_path)
    app.launcher.query_one("#prompt", TextArea).load_text(prompt)


async def test_empty_launcher():
    app = LauncherApp(ProfileBook())
    async with app.run_test() as pilot:
        assert isinstance(app.screen, LauncherScreen)
        assert app.query_one("#start-run", Button).disabled
        assert app.query_one("#check-workspace", Button).disabled
        assert not app.controller.active
        await pilot.click("#quit-launcher")


@pytest.mark.parametrize("size", [(120, 50), (80, 24)])
async def test_launcher_confirmation_success_and_back(book, tmp_path, size):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        assert app.query_one("#model", Input).value == "synthetic-model"
        assert app.query_one("#verify", Select).value == "none"
        assert app.query_one("#retries", Input).value == "0"
        assert not app.query_one("#allow-execution", Checkbox).value
        fill(app, tmp_path)
        app.query_one("#allow-execution", Checkbox).value = True
        await pilot.click("#start-run")
        assert isinstance(app.screen, ConfirmRun)
        assert "ENABLED" in app.screen.description
        assert "synthetic task" not in app.screen.description
        assert not app.controller.active
        await pilot.click("#dismiss-confirm")
        assert isinstance(app.screen, LauncherScreen)
        assert not app.controller.active
        await pilot.click("#start-run")
        await pilot.click("#confirm-start")
        assert isinstance(app.screen, MonitorScreen)
        await settle(app, pilot)
        assert app.controller.session.exit_code == 0
        assert "COMPLETED" in str(app.screen.query_one("#run-status", Static).render())
        assert "docs/example.md" in str(app.screen.query_one("#activity", Static).render())
        assert app.screen.query_one("#back-launcher").region.bottom <= size[1]
        await pilot.click("#back-launcher")
        assert isinstance(app.screen, LauncherScreen)
        area = app.query_one("#prompt", TextArea)
        assert area.text == ""
        area.undo()
        assert area.text == ""
        assert not app.query_one("#allow-execution", Checkbox).value
        assert (tmp_path / "docs/example.md").is_file()


@pytest.mark.parametrize("denied", [False, True])
async def test_workspace_check_ui(book, tmp_path, denied):
    workspace = tmp_path / ("denied" if denied else "allowed")
    workspace.mkdir()
    app = LauncherApp(book)
    async with app.run_test(size=(100, 40)) as pilot:
        fill(app, workspace)
        app.query_one("#allow-execution", Checkbox).value = True
        await pilot.click("#check-workspace")
        assert isinstance(app.screen, MonitorScreen)
        await settle(app, pilot)
        await pilot.click("#back-launcher")
        status = str(app.query_one("#launch-status", Static).render())
        assert ("failed" if denied else "Valid") in status
        assert not list(workspace.iterdir())
        assert not app.controller.active
        assert app.query_one("#prompt", TextArea).text == "synthetic task"
        app.query_one("#workspace", Input).value = str(tmp_path)
        await pilot.pause()
        assert "changed" in str(app.query_one("#launch-status", Static).render())


@pytest.mark.parametrize("cancel", [False, True])
async def test_failed_and_cancelled_run_ui(book, tmp_path, cancel):
    app = LauncherApp(book)
    async with app.run_test(size=(100, 40)) as pilot:
        fill(app, tmp_path, "synthetic-wait" if cancel else "synthetic-fail")
        await pilot.click("#start-run")
        await pilot.click("#confirm-start")
        if cancel:
            for _ in range(100):
                if app.controller.session.runs:
                    break
                await asyncio.sleep(0.02)
            await pilot.click("#cancel-run")
        await settle(app, pilot)
        assert app.controller.session.exit_code == (130 if cancel else 7)
        assert not app.controller.active
        assert ("cancelled locally" if cancel else "FAILED") in str(
            app.screen.query_one("#run-status", Static).render()
        )
        await pilot.click("#back-launcher")
        assert isinstance(app.screen, LauncherScreen)


async def test_launcher_validation_and_profile_switch(book, tmp_path):
    book.profiles["other"] = RuntimeProfile(
        "other", sys.executable, book.select().ai_agent_main, "other-model", default_verify="pytest"
    )
    app = LauncherApp(book)
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.click("#start-run")
        assert not app.controller.active
        assert "Workspace" in str(app.query_one("#launch-status", Static).render())
        fill(app, tmp_path, "")
        await pilot.pause(0.3)
        await pilot.click("#start-run")
        assert "prompt" in str(app.query_one("#launch-status", Static).render())
        app.query_one("#allow-execution", Checkbox).value = True
        app.query_one("#profile", Select).value = "other"
        await pilot.pause()
        assert not app.query_one("#allow-execution", Checkbox).value
        assert app.query_one("#model", Input).value == "other-model"
        assert app.query_one("#verify", Select).value == "pytest"
