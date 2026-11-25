import pytest

from drsim.shared.enums import UnitStatus
from drsim.simulation.entities.units import can_dispatch_transition


@pytest.mark.parametrize(
    ("current_status", "next_status", "expected"),
    [
        (UnitStatus.AVAILABLE, UnitStatus.EN_ROUTE, True),
        (UnitStatus.EN_ROUTE, UnitStatus.ON_SCENE, True),
        (UnitStatus.AVAILABLE, UnitStatus.ON_SCENE, False),
        (UnitStatus.UNAVAILABLE, UnitStatus.EN_ROUTE, False),
    ],
)
def test_can_dispatch_transition(
    current_status: UnitStatus, next_status: UnitStatus, expected: bool
) -> None:
    assert can_dispatch_transition(current_status, next_status) is expected