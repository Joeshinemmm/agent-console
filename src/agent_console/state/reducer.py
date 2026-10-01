from dataclasses import dataclass

from agent_console.models.event import Event
from agent_console.models.run import RunState, Status

DEFAULT_COMPONENTS = ("main", "developer", "codex", "test", "browser", "desktop", "training")
TERMINALS = {
    "run.completed": Status.COMPLETED,
    "run.failed": Status.FAILED,
    "run.cancelled": Status.CANCELLED,
}
LIFECYCLE = {
    "started": Status.RUNNING,
    "running": Status.RUNNING,
    "resumed": Status.RUNNING,
    "retry": Status.RUNNING,
    "ready": Status.RUNNING,
    "completed": Status.COMPLETED,
    "stopped": Status.COMPLETED,
    "failed": Status.FAILED,
    "denied": Status.FAILED,
    "cancelled": Status.CANCELLED,
}


def lifecycle(event: Event) -> Status | None:
    return LIFECYCLE.get(event.event_type.rsplit(".", 1)[-1]) or LIFECYCLE.get(event.status)


def is_error(event: Event) -> bool:
    return (
        event.level.lower() in ("error", "critical", "fatal") or lifecycle(event) == Status.FAILED
    )


@dataclass(frozen=True, slots=True)
class Reduction:
    state: RunState
    issue: str | None = None
    accepted: bool = True


def apply_event(state: RunState, event: Event, *, max_events: int = 10_000) -> Reduction:
    """Pure reduction. Sequence is authoritative; replay late events deterministically."""
    if state.run_id != event.run_id:
        return Reduction(state, "Event belongs to a different run; discarded.", False)
    for previous in state.events:
        if previous.event_id == event.event_id:
            issue = (
                "Duplicate event ignored." if previous == event else "Conflicting event_id ignored."
            )
            return Reduction(state, issue, False)
        if previous.sequence == event.sequence:
            return Reduction(state, "Conflicting sequence ignored.", False)
    if len(state.events) >= max_events:
        return Reduction(state, "Run event limit reached; event discarded.", False)
    late = bool(state.events and event.sequence < state.events[-1].sequence)
    events = (*state.events, event)
    if late:
        events = tuple(sorted(events, key=lambda item: item.sequence))
    # Rebuild only when a late event changes canonical history. The usual ordered
    # stream updates aggregates from one event without replaying the entire run.
    replay = events if late else (event,)
    components = dict.fromkeys(DEFAULT_COMPONENTS, Status.IDLE)
    if not late:
        components.update(state.components)
    status = Status.IDLE if late else state.status
    activity = None if late else state.activity
    elapsed_ms = 0 if late else state.elapsed_ms
    error_count = 0 if late else state.error_count
    for item in replay:
        components.setdefault(item.component, Status.IDLE)
        component_status = lifecycle(item)
        if component_status:
            components[item.component] = component_status
        if item.event_type in TERMINALS:
            status = TERMINALS[item.event_type]
        elif item.event_type == "run.started" and status not in TERMINALS.values():
            status = Status.RUNNING
        if not item.event_type.startswith("run."):
            activity = item
        elapsed_ms = max(elapsed_ms, item.elapsed_ms)
        error_count += is_error(item)
    if activity is None or activity.event_type.startswith("run."):
        activity = events[-1]
    return Reduction(
        RunState(
            run_id=state.run_id,
            events=events,
            components=tuple(components.items()),
            status=status,
            elapsed_ms=elapsed_ms,
            error_count=error_count,
            activity=activity,
        ),
        "Out-of-order event inserted by sequence." if late else None,
    )
