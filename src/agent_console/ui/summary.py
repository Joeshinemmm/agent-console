from rich.text import Text

from agent_console.models.run import RunState
from agent_console.state.session import Session


def summary(run: RunState, session: Session) -> Text:
    result = Text()
    result.append(f"Elapsed {run.elapsed_ms / 1000:.3f}s   Events {run.event_count}   ")
    result.append(f"Errors {run.error_count}", style="bold red" if run.error_count else "")
    result.append(f"   Issues {session.issue_count}")
    return result
