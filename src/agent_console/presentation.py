"""Presentation mapping shared by the TUI and plain output; no business state."""

from agent_console.models.event import Event
from agent_console.models.run import Status
from agent_console.state.reducer import is_error

LABELS = {
    "run.started": "Run started",
    "run.completed": "Run completed",
    "run.failed": "Run failed",
    "run.cancelled": "Run cancelled",
    "workspace.validated": "Workspace validated",
    "git.status": "Git status checked",
    "route.selected": "Route selected",
    "file.created": "File created",
    "file.modified": "File modified",
    "file.deleted": "File deleted",
    "security.denied": "Security check denied",
}
STYLES = {
    Status.IDLE: "dim",
    Status.RUNNING: "cyan",
    Status.COMPLETED: "green",
    Status.FAILED: "bold red",
    Status.CANCELLED: "yellow",
    Status.INCOMPLETE: "yellow",
}


def description(event: Event) -> str:
    # Do not render free-form message, metadata, filenames, prompts, or source text.
    return LABELS.get(event.event_type, event.event_type.replace(".", " ").capitalize())


def event_style(event: Event) -> str:
    return "bold red" if is_error(event) else ""
