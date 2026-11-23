from pathlib import Path

from drsim.simulation.snapshot import build_snapshot
from drsim.simulation.state import initialize_state
from drsim.simulation.world.loader import load_scenario_with_map

ROOT = Path(__file__).resolve().parents[2]


def _state():
    scenario, map_def = load_scenario_with_map(
        ROOT / "scenarios" / "earthquake_small.json",
        ROOT / "scenarios" / "maps",
    )
    return initialize_state("run-1", scenario, map_def)


def test_snapshot_counts_and_order():
    snap = build_snapshot(_state())
    assert (len(snap.units), len(snap.incidents), len(snap.victims)) == (4, 3, 9)
    assert snap.tick == 0 and snap.simulationTimeSeconds == 0
    ids = [v.victimId for v in snap.victims]
    assert ids == sorted(ids)


def test_snapshot_is_deterministic():
    assert build_snapshot(_state()) == build_snapshot(_state())
