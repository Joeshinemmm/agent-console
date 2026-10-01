from dataclasses import dataclass
from enum import StrEnum

from agent_console.models.event import Event


class Status(StrEnum):
    IDLE = "Idle"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    INCOMPLETE = "Incomplete"


@dataclass(frozen=True, slots=True)
class RunState:
    run_id: str
    events: tuple[Event, ...] = ()
    components: tuple[tuple[str, Status], ...] = ()
    status: Status = Status.IDLE
    elapsed_ms: float = 0
    error_count: int = 0
    activity: Event | None = None

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def has_terminal_event(self) -> bool:
        return self.status in (Status.COMPLETED, Status.FAILED, Status.CANCELLED)

    def display_status(self, ended: bool) -> Status:
        if ended and not self.has_terminal_event:
            return Status.INCOMPLETE
        return self.status
