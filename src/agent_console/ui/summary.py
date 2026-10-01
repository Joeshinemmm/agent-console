from rich.text import Text

from agent_console.models.run import RunState
from agent_console.presentation import STYLES
from agent_console.state.session import Session


def summary(run: RunState, session: Session) -> Text:
    status = run.display_status(session.ended)
    result = Text(f"Elapsed {run.elapsed_ms / 1000:.3f}s   Events {run.event_count}   ")
    result.append(f"Errors {run.error_count}   ", style="bold red" if run.error_count else "")
    result.append(str(status).upper(), style=STYLES[status])
    result.append(f"   Issues {session.issue_count}")
    if session.process_exit is not None:
        result.append(f"   Process exit {session.process_exit}")
    return result
