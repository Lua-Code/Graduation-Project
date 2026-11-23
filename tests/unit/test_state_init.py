import json
from pathlib import Path

import pytest

from drsim.shared.enums import RunStatus
from drsim.simulation.state import initialize_state
from drsim.simulation.world.loader import ScenarioLoadError, load_scenario_with_map

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / "scenarios" / "earthquake_small.json").read_text(encoding="utf-8"))


def _state():
    scenario, map_def = load_scenario_with_map(
        ROOT / "scenarios" / "earthquake_small.json",
        ROOT / "scenarios" / "maps",
    )
    return initialize_state("run-1", scenario, map_def)


def test_counts():
    s = _state()
    assert (len(s.units), len(s.incidents), len(s.victims)) == (4, 3, 9)
    assert s.tick == 0 and s.status == RunStatus.CREATED


def test_same_seed_same_victims():
    a, b = _state(), _state()
    assert {k: v.health for k, v in a.victims.items()} == {
        k: v.health for k, v in b.victims.items()
    }


def _load(tmp_path, mutate):
    data = json.loads(json.dumps(BASE))
    mutate(data)
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return load_scenario_with_map(p, ROOT / "scenarios" / "maps")


@pytest.mark.parametrize(
    "mutate, msg",
    [
        (lambda d: d["units"][0].update(nodeId="nope"), "Unit unit-001 references unknown node"),
        (
            lambda d: d["incidents"][0].update(nodeId="nope"),
            "Incident inc-001 references unknown node",
        ),
        (lambda d: d["earthquake"].update(epicenterX=999999), "outside the map bounds"),
    ],
)
def test_invalid_combinations_fail_clearly(tmp_path, mutate, msg):
    with pytest.raises(ScenarioLoadError, match=msg):
        _load(tmp_path, mutate)


def test_state_has_roads_and_facilities():
    s = _state()
    assert len(s.edge_states) == len(s.map_def.edges)
    assert len(s.facilities) == len(s.map_def.facilities)
