from drsim.shared.enums import IncidentStatus
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
