import pytest

from drsim.shared.enums import RunStatus
from drsim.simulation.engine.lifecycle import (
    InvalidTransitionError,
    can_transition,
    is_terminal,
    transition,
)
from tests.unit.test_state_init import _state


def test_happy_path():
    s = _state()
    for target in (RunStatus.RUNNING, RunStatus.PAUSED, RunStatus.RUNNING, RunStatus.COMPLETED):
        transition(s, target)
    assert s.status == RunStatus.COMPLETED


def test_invalid_transition_raises_and_keeps_status():
    s = _state()
    with pytest.raises(InvalidTransitionError, match="Cannot transition from created to paused."):
        transition(s, RunStatus.PAUSED)
    assert s.status == RunStatus.CREATED


@pytest.mark.parametrize("t", [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED])
def test_terminal_states_are_final(t):
    assert is_terminal(t)
    assert not any(can_transition(t, other) for other in RunStatus)
