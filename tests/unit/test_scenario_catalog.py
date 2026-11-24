"""Every committed map and scenario must load and pass the world validation checks."""

import importlib.util
from pathlib import Path

import pytest

from drsim.simulation.world.loader import load_map, load_scenario, load_scenario_with_map
from drsim.simulation.world.validation import validate_map, validate_scenario

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "scenarios"
MAPS_DIR = SCENARIOS_DIR / "maps"

SCENARIO_FILES = sorted(SCENARIOS_DIR.glob("*.json"))
MAP_FILES = sorted(MAPS_DIR.glob("*.json"))
CITY02_FILES = [p for p in SCENARIO_FILES if p.stem.startswith("earthquake_city02_")]


def _ids(paths):
    return [p.name for p in paths]


def test_catalog_is_not_empty():
    assert len(SCENARIO_FILES) >= 5 and len(MAP_FILES) >= 2


@pytest.mark.parametrize("path", MAP_FILES, ids=_ids(MAP_FILES))
def test_map_is_valid(path):
    assert validate_map(load_map(path)) == ()


@pytest.mark.parametrize("path", SCENARIO_FILES, ids=_ids(SCENARIO_FILES))
def test_scenario_is_valid(path):
    scenario, map_def = load_scenario_with_map(path, MAPS_DIR)
    assert validate_scenario(scenario, map_def) == ()


def test_scenario_ids_are_unique():
    ids = [load_scenario(p).scenarioId for p in SCENARIO_FILES]
    assert len(ids) == len(set(ids))


def test_city02_variants_differ_only_in_the_earthquake_setup():
    # Units, incidents, seed and map are shared, so comparing two variants isolates the
    # effect of the earthquake (and, for slow_roads, the degraded multiplier).
    scenarios = [load_scenario(p) for p in CITY02_FILES]
    assert len(scenarios) == 4
    shared = {"units", "incidents", "seed", "mapId", "tickDurationSeconds", "maxTicks"}
    first = scenarios[0].model_dump(include=shared)
    for s in scenarios[1:]:
        assert s.model_dump(include=shared) == first


def test_city02_slow_roads_is_severe_with_a_higher_multiplier():
    severe = load_scenario(SCENARIOS_DIR / "earthquake_city02_severe.json")
    slow = load_scenario(SCENARIOS_DIR / "earthquake_city02_severe_slow_roads.json")
    assert slow.earthquake == severe.earthquake
    assert slow.degradedTravelMultiplier > severe.degradedTravelMultiplier


def test_generated_files_match_the_generator():
    # Guards against hand edits: change scripts/generate_city02.py and rerun it instead.
    spec = importlib.util.spec_from_file_location(
        "generate_city02", ROOT / "scripts" / "generate_city02.py"
    )
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)

    for path, expected in generator.generated_files().items():
        actual = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        assert actual == expected, f"{path.name} differs from scripts/generate_city02.py"
