"""Synthetic repeat-launch checks for session isolation and ownership release."""

import asyncio

import pytest
from test_launcher_ui import book as shared_book
from test_launcher_ui import fill, settle
from textual.widgets import Input, Static, Switch, TextArea

from agent_console.ui.launcher import LauncherApp

book = shared_book


@pytest.mark.parametrize("first_result", ["check", "failed", "cancelled", "completed"])
async def test_new_workspace_run_after_previous_result(book, tmp_path, first_result):
    first_workspace = tmp_path / "first"
    second_workspace = tmp_path / "second"
    first_workspace.mkdir()
    second_workspace.mkdir()
    app = LauncherApp(book)
    async with app.run_test(size=(120, 34)) as pilot:
        prompt = {
            "failed": "synthetic-fail",
            "cancelled": "synthetic-wait",
        }.get(first_result, "synthetic task")
        fill(app, first_workspace, prompt)
        if first_result == "check":
            await pilot.click("#check-workspace")
        else:
            app.query_one("#allow-execution", Switch).value = True
            await pilot.click("#start-run")
            await pilot.pause()
            await pilot.click("#confirm-start")
        if first_result == "cancelled":
            for _ in range(200):
                if app.controller.session.runs:
                    break
                await asyncio.sleep(0.02)
            assert app.controller.session.runs
            await pilot.click("#cancel-run")
        await settle(app, pilot)
        previous = app.controller.session
        assert not app.controller.active
        assert previous.exit_code == {"failed": 7, "cancelled": 130}.get(first_result, 0)
        await pilot.click("#back-launcher")
        if first_result != "check":
            area = app.query_one("#prompt", TextArea)
            area.undo()
            assert area.text == ""
            assert not app.query_one("#allow-execution", Switch).value
        if first_result == "check":
            assert "Valid" in str(app.query_one("#workspace-state", Static).render())
        fill(app, second_workspace)
        app.query_one("#model", Input).value = "synthetic-second-model"
        await pilot.pause()
        assert "Unchecked" in str(app.query_one("#workspace-state", Static).render())
        app.query_one("#allow-execution", Switch).value = True
        await pilot.click("#start-run")
        await pilot.pause()
        await pilot.click("#confirm-start")
        await settle(app, pilot)
        current = app.controller.session
        assert current is not previous
        assert not current.cancelled and not current.issue_count and not current.stderr_bytes
        assert current.exit_code == 0 and not app.controller.active
        assert len(current.runs) == 1
        assert (second_workspace / "docs/example.md").is_file()
        assert (first_workspace / "docs/example.md").exists() == (first_result == "completed")
        await pilot.click("#back-launcher")
        assert app.query_one("#workspace", Input).value == str(second_workspace)
        assert not app.query_one("#allow-execution", Switch).value
        assert app.query_one("#prompt", TextArea).text == ""
