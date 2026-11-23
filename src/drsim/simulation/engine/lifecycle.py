from drsim.shared.enums import RunStatus
from drsim.simulation.state import SimulationState

ALLOWED_TRANSITIONS = {
    RunStatus.CREATED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {RunStatus.PAUSED, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.PAUSED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


class InvalidTransitionError(Exception):
    """Raised when an invalid transition is attempted."""

    pass


def can_transition(current_status: RunStatus, new_status: RunStatus) -> bool:
    """Check if a transition from current_status to new_status is allowed."""
    return new_status in ALLOWED_TRANSITIONS.get(current_status, frozenset())


def is_terminal(status: RunStatus) -> bool:
    """Check if the given status is a terminal state."""
    return status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


def transition(state: SimulationState, new_status: RunStatus) -> None:
    """Attempt to transition the simulation state to a new status."""
    if not can_transition(state.status, new_status):
        raise InvalidTransitionError(f"Cannot transition from {state.status} to {new_status}.")
    state.status = new_status
