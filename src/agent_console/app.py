from collections.abc import AsyncGenerator

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.events import Resize
from textual.widgets import Footer, Header, Select, Static
from textual.worker import Worker, WorkerCancelled

from agent_console.presentation import STYLES, description
from agent_console.sources import SourceItem
from agent_console.state.session import Session, consume
from agent_console.ui.components import Components
from agent_console.ui.summary import summary
from agent_console.ui.timeline import Timeline


class AgentConsole(App[int]):
    TITLE = "AGENT CONSOLE"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [("q", "quit", "Quit"), ("ctrl+c", "quit", "Stop"), ("tab", "focus_next", "Panel")]
    CSS = """
    Screen { background: $surface; }
    #run-picker { margin: 0 1; height: 3; }
    #run-status { margin: 0 1; height: 1; }
    Timeline { margin: 0 1; border: round $primary; height: 1fr; min-height: 6; }
    #details { margin: 0 1; height: 12; }
    #component-scroll { width: 1fr; border: round $primary; padding: 0 1; }
    #activity { width: 1fr; height: 1fr; border: round $primary; padding: 0 1; }
    #summary { margin: 0 1; height: auto; min-height: 3; border: round $primary; }
    #diagnostics { margin: 0 1; height: 4; color: $warning; }
    """

    def __init__(self, source: AsyncGenerator[SourceItem, None], session: Session) -> None:
        super().__init__()
        self.source = source
        self.session = session
        self.consumer: Worker | None = None
        self.run_ids: list[str] = []
        self.last_revision = -1

    def compose(self) -> ComposeResult:
        yield Header()
        yield Select([], prompt="Waiting for events", id="run-picker")
        yield Static("Waiting for JSONL stream…", id="run-status", markup=False)
        yield Timeline(id="timeline")
        with Horizontal(id="details"):
            with VerticalScroll(id="component-scroll"):
                yield Components(id="components")
            yield Static("Waiting for activity", id="activity", markup=False)
        yield Static("No events received", id="summary", markup=False)
        yield Static("", id="diagnostics", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#component-scroll").border_title = "Components"
        self.query_one("#activity").border_title = "Current activity"
        self.query_one("#summary").border_title = "Run summary"
        self.consumer = self.run_worker(consume(self.source, self.session), name="event-stream")
        self.set_interval(0.1, self.refresh_session)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.refresh_session(force=True)

    def on_resize(self, event: Resize) -> None:
        if self.is_mounted:
            compact = event.size.height < 34
            self.query_one("#details").styles.height = 8 if compact else 12
            self.query_one("#diagnostics").styles.height = 2 if compact else 4
            self.query_one(Timeline).styles.min_height = 4 if compact else 6

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
            label = Text(f"Run {run.run_id}   ")
            label.append(str(status).upper(), style=STYLES[status])
            label.append("   [stream ended]" if self.session.ended else "   [receiving]")
            self.query_one("#run-status", Static).update(label)
            self.query_one(Timeline).show_run(run)
            self.query_one(Components).show_run(run)
            if run.activity:
                activity = Text(run.activity.component.capitalize() + "\n\n", style="bold")
                activity.append(description(run.activity))
                self.query_one("#activity", Static).update(activity)
            self.query_one("#summary", Static).update(summary(run, self.session))
        elif self.session.ended:
            self.query_one("#run-status", Static).update("Stream ended without a valid run")
        diagnostics = list(self.session.diagnostics)[-2:]
        if self.session.stderr_bytes:
            diagnostics.append(f"stderr: {self.session.stderr_bytes} bytes received (text hidden)")
        self.query_one("#diagnostics", Static).update("\n".join(diagnostics))

    async def action_quit(self) -> None:
        if self.consumer and not self.consumer.is_finished:
            self.consumer.cancel()
            try:
                await self.consumer.wait()
            except WorkerCancelled:
                pass
        self.exit(self.session.exit_code)
