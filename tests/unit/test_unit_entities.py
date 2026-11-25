import pytest

from drsim.shared.enums import EdgeState, UnitCapability, UnitStatus, UnitType
from drsim.shared.schemas import UnitSpec
from drsim.simulation.entities.units import UnitState, can_dispatch_transition
from drsim.simulation.state import initialize_state
from tests.unit.test_road_graph import _edge
from tests.unit.test_state_init import _state


def test_legacy_units_get_capabilities():
    state = _state()
    assert state.units["unit-004"].is_available(0, UnitCapability.RESCUE)
    assert state.units["unit-001"].is_available(0, UnitCapability.TRANSPORT)
    assert not state.units["unit-003"].is_available(0, UnitCapability.RESCUE)


def test_scenario_can_set_capabilities_and_availability():
    state = _state()
    spec = UnitSpec(
        unitId="fire",
        unitType=UnitType.FIRE,
        nodeId="n1",
        capabilities=(UnitCapability.RESCUE,),
        availableFromTick=2,
    )
    scenario = state.scenario.model_copy(update={"units": (spec,)})
    unit = initialize_state("run", scenario, state.map_def).units["fire"]
    assert not unit.is_available(1)
    assert unit.is_available(2, UnitCapability.RESCUE)
    assert not unit.is_available(2, UnitCapability.TRANSPORT)
    with pytest.raises(ValueError):
        unit.transition(UnitStatus.EN_ROUTE, tick=1, incident_id="i")


def test_dispatch_and_release():
    unit = UnitState("u", UnitType.RESCUE, "a")
    assert not can_dispatch_transition(unit.status, UnitStatus.ON_SCENE)
    with pytest.raises(ValueError):
        unit.transition(UnitStatus.ON_SCENE, tick=0)
    busy = unit.transition(UnitStatus.EN_ROUTE, tick=0, incident_id="i")
    assert busy.assigned_incident_id == "i"
    assert not busy.is_available(0)
    at_scene = busy.transition(UnitStatus.ON_SCENE, tick=1)
    with pytest.raises(ValueError):
        at_scene.transition(UnitStatus.TRANSPORTING, tick=1)
    released = at_scene.transition(UnitStatus.AVAILABLE, tick=2)
    assert released.is_available(2)
    assert released.assigned_incident_id is None


def test_edge_progress_and_arrival():
    busy = UnitState("u", UnitType.RESCUE, "a").transition(
        UnitStatus.EN_ROUTE, tick=0, incident_id="i"
    )
    edge = _edge(200, 10, bidirectional=False)
    with pytest.raises(ValueError):
        busy.enter_edge(edge, EdgeState.BLOCKED, 10)
    moving = busy.enter_edge(edge, EdgeState.OPEN, 10).advance_movement()
    assert moving.node_id == "a"
    assert moving.movement and moving.movement.elapsed_ticks == 1
    with pytest.raises(ValueError):
        moving.enter_edge(edge, EdgeState.OPEN, 10)
    with pytest.raises(ValueError):
        moving.transition(UnitStatus.ON_SCENE, tick=1)
    arrived = moving.advance_movement()
    assert arrived.node_id == "b" and arrived.movement is None
    with pytest.raises(ValueError):
        arrived.enter_edge(edge, EdgeState.OPEN, 10)
