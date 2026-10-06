from collections.abc import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Select, Static
from textual.worker import Worker, WorkerCancelled

from agent_console.presentation import STYLES
from agent_console.sources import ClosableSource
from agent_console.state.session import Session, consume
from agent_console.ui.activity import activity_text
from agent_console.ui.components import Components
from agent_console.ui.controls import ActionButton
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
    #run-picker { margin: 0 1; height: 3; }
    #run-status { margin: 0 1; height: 1; }
    #monitor-body { height: 1fr; }
    Timeline, #component-scroll, #activity, #summary {
        border: round $foreground 20%; border-title-color: $text-muted; border-title-style: bold;
    }
    Timeline { margin: 0 1; height: 8; min-height: 4; }
    Timeline:focus { border: solid $primary; }
    #details { margin: 0 1; height: 12; }
    #component-scroll { width: 1fr; padding: 0 1; }
    #component-scroll:focus-within { border: solid $primary; }
    #activity { width: 1fr; height: 1fr; padding: 0 1;
                overflow-y: auto; }
    #activity:focus { border: solid $primary; }
    #summary { margin: 0 1; height: auto; min-height: 3; max-height: 5;
               overflow-y: auto; }
    #summary:focus { border: solid $primary; }
    #diagnostics { margin: 0 1; height: auto; max-height: 2; overflow-y: auto; color: $warning; }
    #monitor-controls { height: 3; margin: 0 1; }
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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Select([], prompt="Waiting for events", id="run-picker")
        yield Static("Waiting for JSONL stream…", id="run-status", markup=False)
        with VerticalScroll(id="monitor-body", can_focus=False):
            yield Timeline(id="timeline")
            with Horizontal(id="details"):
                with VerticalScroll(id="component-scroll"):
                    yield Components(id="components")
                yield Static("Waiting for activity", id="activity", markup=False)
            yield Static("No events received", id="summary", markup=False)
            yield Static("", id="diagnostics", markup=False)
        if self.on_back:
            with Horizontal(id="monitor-controls"):
                yield ActionButton("Cancel Run", id="cancel-run", variant="warning")
                yield ActionButton("Back to Launcher", id="back-launcher", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#component-scroll").border_title = "Components"
        self.query_one("#activity").border_title = "Current activity"
        self.query_one("#summary").border_title = "Run summary"
        for selector in ("#activity", "#summary", "#diagnostics"):
            self.query_one(selector).can_focus = True
        self.consumer = self.run_worker(consume(self.source, self.session), name="event-stream")
        self.set_interval(0.1, self.refresh_session)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.refresh_session(force=True)

    def on_resize(self, event: Resize) -> None:
        if self.is_mounted:
            self.fit_panels()

    def fit_panels(self) -> None:
        compact = self.size.height < 34
        details_height = (4 if self.on_back else 6) if compact else 12
        self.query_one("#details").styles.height = details_height
        diagnostics = 2 if self.session.diagnostics or self.session.stderr_bytes else 0
        self.query_one("#diagnostics").display = bool(diagnostics)
        # Reserve summary/actions before growing the timeline; long streams scroll inside it.
        available = self.size.height - (
            6 + details_height + 5 + diagnostics + (3 if self.on_back else 0)
        )
        timeline = self.query_one(Timeline)
        timeline.styles.height = max(4, min(max(7, timeline.row_count + 3), 18, available))

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
        if isinstance(selected, str) and selected in self.session.runs:
            run = self.session.runs[selected]
            status = run.display_status(self.session.ended)
            short_id = run.run_id if len(run.run_id) <= 16 else run.run_id[:8] + "…"
            label = Text(f"Run {short_id}   ")
            label.append(str(status).upper(), style=STYLES[status])
            label.append("   [stream ended]" if self.session.ended else "   [receiving]")
            if self.session.cancelled:
                label.append("   [cancelled locally]", style="yellow")
            self.query_one("#run-status", Static).update(label)
            self.query_one("#run-status").tooltip = run.run_id
            self.query_one(Timeline).show_run(run)
            self.query_one(Components).show_run(run)
            self.query_one("#activity").border_title = (
                "Run result" if run.has_terminal_event or self.session.ended else "Current activity"
            )
            self.query_one("#activity", Static).update(activity_text(run, self.session))
            self.query_one("#summary", Static).update(summary(run, self.session))
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
