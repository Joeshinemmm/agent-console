"""Regression cases for the user's normal-window UI feedback, using synthetic data."""

import pytest
from test_launcher_ui import book as shared_book
from test_ui_polish import MonitorProbe, monitor_ready
from test_viewport_acceptance import SIZES, assert_inside, scenario, visible_text
from textual.widgets import Button, Select, Switch, TextArea

from agent_console.ui.controls import ConsoleHeader
from agent_console.ui.launcher import LauncherApp

book = shared_book


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("selector", ["#profile", "#task", "#provider", "#verify"])
async def test_dropdown_below_control_with_visible_outline(book, size, selector):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        select = app.query_one(selector, Select)
        select.focus()
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause()
        current = select.query_one("SelectCurrent")
        overlay = select.query_one("SelectOverlay")
        assert select.expanded
        assert overlay.region.x == current.region.x
        assert overlay.region.y == current.region.bottom
        assert overlay.region.width == current.region.width
        assert_inside(overlay, app.screen)
        cells = visible_text(app, overlay)
        assert "┌" in cells and "┐" in cells and "└" in cells and "┘" in cells
        if selector == "#profile":
            assert "No runtime configured" not in cells
        if selector == "#verify":
            await pilot.press("down", "enter")
            assert select.value == "pytest"
        else:
            await pilot.press("escape")
        assert not select.expanded
        assert select.has_focus
        assert app.query_one("#launch-form").max_scroll_x == 0


@pytest.mark.parametrize("selector", ["#check-workspace", "#start-run", "#quit-launcher"])
async def test_action_outline_stays_flat_in_every_state(book, selector):
    app = LauncherApp(book)
    async with app.run_test(size=(120, 30)) as pilot:
        button = app.query_one(selector, Button)
        bounds = button.region

        def assert_outline():
            assert button.region == bounds
            assert all(
                edge[0] in ("round", "solid")
                for edge in (
                    button.styles.border_top,
                    button.styles.border_bottom,
                    button.styles.border_left,
                    button.styles.border_right,
                )
            )
            cells = visible_text(app, button)
            assert str(button.label) in cells
            assert cells.count("─") >= 4
            assert not any(block in cells for block in "▀▄▔▁")

        assert_outline()
        await pilot.hover(selector)
        assert_outline()
        button.focus()
        await pilot.pause()
        assert_outline()
        button.add_class("-active")
        await pilot.pause()
        assert_outline()
        assert button.styles.text_style.underline
        button.remove_class("-active")
        button.disabled = True
        await pilot.pause()
        assert_outline()
        assert button.styles.text_opacity == 1
        assert not button.styles.text_style.underline


@pytest.mark.parametrize("size", SIZES)
async def test_prompt_resize_preserves_edits_undo_and_fixed_actions(book, size):
    app = LauncherApp(book)
    async with app.run_test(size=size) as pilot:
        prompt = app.query_one("#prompt", TextArea)
        prompt.load_text("Synthetic text")
        prompt.focus()
        await pilot.press("end", "!")
        text = prompt.text
        action_region = app.query_one("#start-run").region
        initial = prompt.region.height
        larger = app.query_one("#prompt-larger", Button)
        larger.focus()
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause()
        assert prompt.region.height == initial + 3
        assert prompt.text == text
        assert app.query_one("#start-run").region == action_region
        app.query_one("#prompt-smaller").focus()
        await pilot.press("enter")
        await pilot.pause()
        assert prompt.region.height == initial
        for _ in range(8):
            larger.press()
            await pilot.pause()
        assert larger.disabled
        assert prompt.region.height <= min(20, size[1] - 10)
        assert app.query_one("#start-run").region == action_region
        assert app.query_one("#launch-form").max_scroll_x == 0
        app.query_one("#prompt-auto").focus()
        await pilot.press("enter")
        await pilot.pause()
        assert prompt.region.height == initial
        prompt.focus()
        await pilot.press("ctrl+z")
        assert prompt.text == "Synthetic text"
        assert not app.controller.active


async def test_prompt_size_survives_terminal_resize(book):
    app = LauncherApp(book)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.click("#prompt-larger")
        await pilot.pause()
        assert app.query_one("#prompt").region.height == 8
        for size in [(80, 24), (160, 50), (120, 30)]:
            await pilot.resize_terminal(*size)
            assert app.query_one("#prompt").region.height == 8
        await pilot.click("#prompt-auto")
        await pilot.pause()
        assert app.query_one("#prompt").region.height == 5


async def test_switch_is_explicit_and_compact_fields_are_separated(book):
    app = LauncherApp(book)
    async with app.run_test(size=(120, 30)) as pilot:
        switch = app.query_one("#allow-execution", Switch)
        assert not switch.value
        assert "Allow execution: OFF" in visible_text(app)
        switch.focus()
        await pilot.press("space")
        assert switch.value and "ENABLED" in visible_text(app)
        await pilot.click("#allow-execution")
        assert not switch.value
        for selector in ("#model", "#retries", "#profile", "#task", "#verify"):
            control = app.query_one(selector)
            if isinstance(control, Select):
                control = control.query_one("SelectCurrent")
            assert "│" in visible_text(app, control)
        assert "─" in visible_text(app, app.query_one("#run-settings"))
        assert "X" not in visible_text(app, switch)


async def test_header_has_no_inert_icon_or_click_resize(book, encode_event):
    for app in (LauncherApp(book), MonitorProbe(scenario(encode_event, "check"))):
        async with app.run_test(size=(120, 30)) as pilot:
            if isinstance(app, MonitorProbe):
                await monitor_ready(app, pilot)
            header = app.query_one(ConsoleHeader)
            assert visible_text(app, header).strip() == "AGENT CONSOLE"
            before = header.region
            await pilot.hover(ConsoleHeader)
            await pilot.click(ConsoleHeader)
            assert header.region == before
            assert not app.query("HeaderIcon")
