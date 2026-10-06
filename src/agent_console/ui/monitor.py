from collections.abc import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Button, Footer, Select, Static
from textual.worker import Worker, WorkerCancelled

from agent_console.presentation import STYLES
from agent_console.sources import ClosableSource
from agent_console.state.session import Session, consume
from agent_console.ui.activity import activity_text
from agent_console.ui.components import Components, system_text
from agent_console.ui.controls import ActionButton, ConsoleHeader
from agent_console.ui.summary import summary
from agent_console.ui.timeline import Timeline


class MonitorScreen(Screen):
    TITLE = "AGENT CONSOLE"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Stop / Quit"),
        ("tab", "app.focus_next", "Next"),
        ("shift+tab", "app.focus_previous", "Previous"),
    ]
    DEFAULT_CSS = """
    MonitorScreen { background: $surface; }
    #run-heading { margin: 0 1; height: 1; }
    #run-picker { width: 44; max-width: 55%; height: 1; margin-right: 1; }
    #run-status { width: 1fr; height: 1; }
    #run-status:focus { text-style: underline; }
    #monitor-body { height: auto; }
    Timeline, #component-scroll, #result-scroll, #summary {
        border: round $foreground 20%; border-title-color: $text-muted; border-title-style: bold;
    }
    Timeline { margin: 0 1; height: 8; min-height: 4; }
    Timeline:focus { border: solid $primary; }
    #details { margin: 0 1; height: 8; }
    #component-scroll { width: 1fr; padding: 0 1; }
    #component-scroll:focus-within { border: solid $primary; }
    #result-scroll { width: 1fr; padding: 0 1; }
    #activity { height: auto; }
    #result-scroll:focus { border: solid $primary; }
    #summary { margin: 0 1; height: auto; min-height: 3; max-height: 5;
               overflow-y: auto; }
    #summary:focus { border: solid $primary; }
    #system-status { margin: 0 2; height: auto; overflow-y: auto; }
    #system-status:focus { text-style: underline; }
    #diagnostics { margin: 0 1; height: auto; max-height: 2; overflow-y: auto; color: $warning; }
    #monitor-controls { height: 3; margin: 0 1; background: $panel; }
    #monitor-controls Button { margin-right: 1; }
    """

    def __init__(
        self,
        source: ClosableSource,
        session: Session,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.source = source
        self.session = session
        self.consumer: Worker | None = None
        self.run_ids: list[str] = []
        self.last_revision = -1
        self.on_back = on_back
        self.result_text = Text("Waiting for activity")
        self.pipeline_text = Text()
        self.metrics_text = Text("No events received")

    def compose(self) -> ComposeResult:
        yield ConsoleHeader()
        with Horizontal(id="run-heading"):
            yield Select([], prompt="Runs", id="run-picker", compact=True)
            yield Static("Waiting for JSONL stream…", id="run-status", markup=False)
        with VerticalScroll(id="monitor-body", can_focus=False):
            yield Timeline(id="timeline")
            with Horizontal(id="details"):
                with VerticalScroll(id="component-scroll"):
                    yield Components(id="components")
                with VerticalScroll(id="result-scroll"):
                    yield Static("Waiting for activity", id="activity", markup=False)
            yield Static("", id="system-status", markup=False)
            yield Static("No events received", id="summary", markup=False)
            yield Static("", id="diagnostics", markup=False)
        if self.on_back:
            with Horizontal(id="monitor-controls"):
                yield ActionButton("Cancel Run", id="cancel-run", variant="warning")
                yield ActionButton("Back to Launcher", id="back-launcher", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#component-scroll").border_title = "Agents"
        self.query_one("#result-scroll").border_title = "Current activity"
        self.query_one("#summary").border_title = "Run summary"
        for selector in ("#run-status", "#system-status", "#summary", "#diagnostics"):
            self.query_one(selector).can_focus = True
        self.query_one("#run-picker").display = False
        self.consumer = self.run_worker(consume(self.source, self.session), name="event-stream")
        self.set_interval(0.1, self.refresh_session)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.refresh_session(force=True)

    def on_resize(self, event: Resize) -> None:
        if self.is_mounted:
            self.fit_panels()

    def fit_panels(self) -> None:
        # Size the information first. Only the timeline uses the remaining row budget.
        width = max(1, self.size.width - 2)
        result_rows = len(self.result_text.wrap(self.app.console, max(1, width // 2 - 4)))
        details_height = max(8, result_rows + 2)
        system_rows = len(self.pipeline_text.wrap(self.app.console, max(1, width - 2)))
        if not self.pipeline_text.plain:
            system_rows = 0
        summary_height = max(3, len(self.metrics_text.wrap(self.app.console, width - 2)) + 2)
        self.query_one("#details").styles.height = details_height
        self.query_one("#system-status").display = bool(system_rows)
        self.query_one("#system-status").styles.height = system_rows
        self.query_one("#summary").styles.height = summary_height
        diagnostics = 2 if self.session.diagnostics or self.session.stderr_bytes else 0
        self.query_one("#diagnostics").display = bool(diagnostics)
        self.query_one("#diagnostics").styles.height = diagnostics
        body_budget = self.size.height - 3 - (3 if self.on_back else 0)
        reserved = details_height + system_rows + summary_height + diagnostics
        timeline = self.query_one(Timeline)
        timeline_height = max(4, min(max(5, timeline.row_count + 3), 18, body_budget - reserved))
        timeline.styles.height = timeline_height
        # Keep the action bar stationary while live events grow the timeline.
        self.query_one("#monitor-body").styles.height = body_budget

    def refresh_session(self, force: bool = False) -> None:
        if not force and self.last_revision == self.session.revision:
            return
        self.last_revision = self.session.revision
        picker = self.query_one("#run-picker", Select)
        ids = list(self.session.runs)
        if ids != self.run_ids:
            self.run_ids = ids
            picker.set_options([(Text(run_id), run_id) for run_id in ids])
            if ids:
                picker.value = ids[-1]
        selected = picker.value
        picker.display = len(ids) > 1
        if isinstance(selected, str) and selected in self.session.runs:
            run = self.session.runs[selected]
            status = run.display_status(self.session.ended)
            short_id = run.run_id if len(run.run_id) <= 16 else run.run_id[:8] + "…"
            label = Text(f"Run {short_id}   " if len(ids) == 1 else "")
            label.append(str(status).upper(), style=STYLES[status])
            label.append("   [stream ended]" if self.session.ended else "   [receiving]")
            if self.session.cancelled:
                label.append("   [cancelled locally]", style="yellow")
            self.query_one("#run-status", Static).update(label)
            self.query_one("#run-status").tooltip = run.run_id
            self.query_one(Timeline).show_run(run)
            self.query_one(Components).show_run(run)
            self.query_one("#result-scroll").border_title = (
                "Run result" if run.has_terminal_event or self.session.ended else "Current activity"
            )
            self.result_text = activity_text(run, self.session)
            self.pipeline_text = system_text(run)
            self.metrics_text = summary(run, self.session)
            self.query_one("#activity", Static).update(self.result_text)
            self.query_one("#system-status", Static).update(self.pipeline_text)
            self.query_one("#summary", Static).update(self.metrics_text)
        elif self.session.ended:
            self.query_one("#run-status", Static).update("Stream ended without a valid run")
        diagnostics = list(self.session.diagnostics)[-2:]
        if self.session.stderr_bytes:
            diagnostics.append(f"stderr: {self.session.stderr_bytes} bytes received (text hidden)")
        self.query_one("#diagnostics", Static).update("\n".join(diagnostics))
        self.fit_panels()
        if self.on_back:
            cancel = self.query_one("#cancel-run", Button)
            back = self.query_one("#back-launcher", Button)
            cancel_had_focus = cancel.has_focus
            # A terminal event can precede process exit: keep Cancel until ownership ends.
            cancel.display = not self.session.ended
            cancel.disabled = self.session.ended
            back.disabled = not self.session.ended
            back.variant = "primary" if self.session.ended else "default"
            if self.session.ended and cancel_had_focus:
                back.focus()

    async def stop(self) -> None:
        if self.consumer and not self.consumer.is_finished:
            self.consumer.cancel()
            try:
                await self.consumer.wait()
            except WorkerCancelled:
                pass
        if not self.session.ended:
            await self.source.aclose()
            self.session.cancelled = True
            self.session.finish()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-run":
            event.button.disabled = True
            await self.stop()
            self.refresh_session(force=True)
        elif event.button.id == "back-launcher" and self.session.ended and self.on_back:
            self.on_back()

    async def action_quit(self) -> None:
        await self.stop()
        self.app.exit(self.session.exit_code)
