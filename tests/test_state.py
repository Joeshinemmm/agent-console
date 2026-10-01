from dataclasses import FrozenInstanceError
from itertools import permutations

import pytest

from agent_console.models.run import RunState, Status
from agent_console.sources import SourceItem
from agent_console.state.reducer import apply_event
from agent_console.state.session import Session


def reduce(events):
    state = RunState(events[0].run_id)
    for event in events:
        state = apply_event(state, event).state
    return state


def test_reducer_is_pure(make_event):
    original = RunState("synthetic-run")
    result = apply_event(original, make_event())
    assert original.events == ()
    assert result.state.status == Status.RUNNING
    with pytest.raises(FrozenInstanceError):
        result.state.status = Status.FAILED


def test_arrival_order_does_not_change_final_state(make_event):
    events = [
        make_event(),
        make_event(2, "developer.started", "developer"),
        make_event(3, "developer.completed", "developer"),
        make_event(4, "run.completed"),
    ]
    expected = reduce(events)
    for arrival in permutations(events):
        assert reduce(arrival) == expected
    assert dict(expected.components)["developer"] == Status.COMPLETED
    assert expected.activity.sequence == 3


def test_duplicate_and_collision(make_event):
    event = make_event()
    state = reduce([event])
    assert not apply_event(state, event).accepted
    assert "Duplicate" in apply_event(state, event).issue
    assert (
        "Conflicting event_id" in apply_event(state, make_event(2, event_id=event.event_id)).issue
    )
    assert "Conflicting sequence" in apply_event(state, make_event(event_id="another-id")).issue
    assert state.event_count == 1


@pytest.mark.parametrize(
    "terminal,status",
    [
        ("run.completed", Status.COMPLETED),
        ("run.failed", Status.FAILED),
        ("run.cancelled", Status.CANCELLED),
    ],
)
def test_terminal_authority(make_event, terminal, status):
    state = reduce(
        [
            make_event(),
            make_event(2, "tool.failed", "tool"),
            make_event(3, terminal),
            make_event(4, "cleanup.completed", "cleanup"),
        ]
    )
    assert state.status == status
    assert dict(state.components)["tool"] == Status.FAILED
    assert state.error_count == (2 if terminal == "run.failed" else 1)


def test_component_failure_is_not_run_failure(make_event):
    state = reduce([make_event(), make_event(2, "codex.turn.failed", "codex")])
    assert state.status == Status.RUNNING
    assert state.display_status(True) == Status.INCOMPLETE


def test_unknown_event_remains_visible(make_event):
    event = make_event(1, "future.observation", "new_component", status="observed")
    state = reduce([event])
    assert state.events == (event,)
    assert dict(state.components)["new_component"] == Status.IDLE


def test_error_level_and_elapsed(make_event):
    state = reduce(
        [make_event(elapsed_ms=50), make_event(2, "future.alert", level="error", elapsed_ms=20)]
    )
    assert state.error_count == 1
    assert state.elapsed_ms == 50


def test_wrong_run_and_limits(make_event):
    state = RunState("another-run")
    assert not apply_event(state, make_event()).accepted
    state = reduce([make_event()])
    assert not apply_event(state, make_event(2), max_events=1).accepted


def test_session_multiple_runs(encode_event):
    session = Session()
    for run_id in ("run-one", "run-two"):
        session.accept(SourceItem("line", encode_event(run_id=run_id)))
        session.accept(SourceItem("line", encode_event(2, "run.completed", run_id=run_id)))
    session.finish()
    assert len(session.runs) == 2
    assert session.exit_code == 0


def test_gaps_at_eof_and_large_sequence(encode_event):
    session = Session()
    session.accept(SourceItem("line", encode_event(2**63 - 1, "run.completed")))
    session.finish()
    assert any("sequence gaps" in issue for issue in session.diagnostics)
    assert session.exit_code == 2


def test_session_limits_and_bounded_diagnostics(encode_event):
    session = Session(max_runs=1, max_events=1)
    session.accept(SourceItem("line", encode_event()))
    session.accept(SourceItem("line", encode_event(2)))
    session.accept(SourceItem("line", encode_event(run_id="other")))
    for _ in range(150):
        session.accept(SourceItem("line", b"invalid"))
    assert len(session.runs) == 1
    assert session.runs["synthetic-run"].event_count == 1
    assert len(session.diagnostics) == 100
    assert session.issue_count == 152


def test_nonzero_process_does_not_rewrite_protocol_status(encode_event):
    session = Session()
    session.accept(SourceItem("line", encode_event(1, "run.completed")))
    session.accept(SourceItem("exit", 7))
    session.finish()
    assert session.runs["synthetic-run"].status == Status.COMPLETED
    assert session.exit_code == 7


def test_duplicate_and_late_events_are_warnings(encode_event):
    session = Session()
    for line in [encode_event(2, "run.completed"), encode_event(), encode_event()]:
        session.accept(SourceItem("line", line))
    session.finish()
    assert session.issue_count == 2
    assert session.exit_code == 0
