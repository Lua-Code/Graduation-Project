from drsim.shared.enums import EdgeState, IncidentStatus
from drsim.shared.schemas import SimulationSnapshot
from drsim.simulation.snapshot import build_snapshot
from tests.unit.test_state_init import _state


def test_snapshot_counts_and_order():
    snap = build_snapshot(_state())
    assert (len(snap.units), len(snap.incidents), len(snap.victims)) == (4, 3, 3)
    assert snap.tick == 0 and snap.simulationTimeSeconds == 0
    ids = [v.victimId for v in snap.victims]
    assert ids == sorted(ids)


def test_snapshot_incident_status_is_derived_open_at_start():
    snap = build_snapshot(_state())
    assert all(i.status == IncidentStatus.OPEN for i in snap.incidents)


def test_snapshot_is_deterministic():
    assert build_snapshot(_state()) == build_snapshot(_state())


def test_snapshot_includes_every_map_edge():
    state = _state()
    snap = build_snapshot(state)

    expected_edge_ids = sorted(edge.edgeId for edge in state.map_def.edges)
    actual_edge_ids = [edge.edgeId for edge in snap.edges]

    assert actual_edge_ids == expected_edge_ids


def test_snapshot_uses_changed_edge_state():
    state = _state()
    edge = state.map_def.edges[0]
    state.edge_states[edge.edgeId] = EdgeState.BLOCKED

    snap = build_snapshot(state)

    edge_summary = next(summary for summary in snap.edges if summary.edgeId == edge.edgeId)

    assert edge_summary.state == EdgeState.BLOCKED


def test_snapshot_edges_are_deterministically_ordered():
    snap = build_snapshot(_state())

    edge_ids = [edge.edgeId for edge in snap.edges]

    assert edge_ids == sorted(edge_ids)


def test_snapshot_without_edges_remains_valid():
    snapshot_data = build_snapshot(_state()).model_dump()
    snapshot_data.pop("edges")

    snap = SimulationSnapshot.model_validate(snapshot_data)

    assert snap.edges == ()
