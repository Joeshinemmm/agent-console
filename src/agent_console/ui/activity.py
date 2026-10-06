from rich.text import Text

from agent_console.models.run import RunState
from agent_console.presentation import STYLES, description
from agent_console.state.session import Session


def activity_text(run: RunState, session: Session) -> Text:
    """Present terminal evidence without changing the reducer's current activity."""
    result = Text()
    if session.cancelled:
        result.append("Cancelled locally", style="bold yellow")
        result.append(f"\nRun event status: {run.display_status(session.ended)}")
    elif run.has_terminal_event:
        result.append(f"Run {str(run.status).lower()}", style="bold " + STYLES[run.status])
    elif session.ended:
        result.append("Stream ended without a terminal result", style="yellow")
    elif run.activity:
        result = Text(run.activity.component.capitalize() + "\n", style="bold")
        result.append(description(run.activity))
        return result
    else:
        return Text("Waiting for activity")
    if session.process_exit is not None:
        result.append(
            f"\nProcess exit {session.process_exit}",
            style="bold red" if session.process_exit else "",
        )
    result.append("\nStream ended" if session.ended else "\nWaiting for process / stream end")
    paths = [event for event in run.events if event.details.path]
    if paths:
        result.append(f"\nFile changes reported: {len(paths)}")
        symbols = {"file.created": "+", "file.modified": "M", "file.deleted": "-"}
        for event in paths[-3:]:
            result.append(f"\n{symbols[event.event_type]} {event.details.path}")
        if len(paths) > 3:
            result.append("\nLatest 3 changes shown")
    return result
