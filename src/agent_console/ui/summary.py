from rich.text import Text

from agent_console.models.run import RunState
from agent_console.presentation import STYLES
from agent_console.state.session import Session


def summary(run: RunState, session: Session) -> Text:
    status = run.display_status(session.ended)
    result = Text()
    result.append(str(status).upper(), style=STYLES[status])
    result.append(f"   Elapsed {run.elapsed_ms / 1000:.3f}s   Events {run.event_count}   ")
    result.append(f"Errors {run.error_count}   ", style="bold red" if run.error_count else "")
    result.append(f"   Issues {session.issue_count}")
    if session.process_exit is not None:
        result.append(f"   Process exit {session.process_exit}")
    if session.cancelled:
        result.append("   Cancelled locally", style="yellow")
    if session.ended:
        changes = [event for event in run.events if event.details.path]
        if changes:
            symbols = {"file.created": "+", "file.modified": "M", "file.deleted": "-"}
            result.append(
                "\nFiles: "
                + " · ".join(
                    f"{symbols[event.event_type]} {event.details.path}" for event in changes[-3:]
                )
            )
            if len(changes) > 3:
                result.append(f" (latest 3 of {len(changes)} changes)")
    return result
