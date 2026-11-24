import os
import subprocess
import sys
from pathlib import Path

import pytest

from drsim.shared.enums import EdgeState
from drsim.shared.schemas import MapDefinition, ScenarioConfig
from drsim.simulation.world.graph import RoadGraph, shortest_route
from drsim.simulation.world.hazards.road_damage import (
    DEFAULT_RULE,
    RULE_VERSION,
    DamageCause,
    EdgeStateChange,
    RoadDamageRule,
    edge_closeness,
    generate_road_damage_schedule,
    road_changes_at,
)
from drsim.simulation.world.loader import load_scenario_with_map

ROOT = Path(__file__).resolve().parents[2]
TICK = 10

# Fixture map (epicentre is at n5 = (1000, 1000), magnitude 6.5 -> radius 750 m):
#
#   n1 --e1-- n2 --e2-- n3        e3, e4, e6 touch n5: closeness 1.0
#   |         |         |         e1, e2, e5, e7 are 800+ m away: closeness 0.0
#   e5        e6        e7
#   |         |         |
#   n4 --e3-- n5 --e4-- n6
NEAR_EDGES = {"e3", "e4", "e6"}
FAR_EDGES = {"e1", "e2", "e5", "e7"}


def _fixture() -> tuple[ScenarioConfig, MapDefinition]:
    return load_scenario_with_map(
        ROOT / "scenarios" / "earthquake_small.json", ROOT / "scenarios" / "maps"
    )


def _scenario(**quake: float) -> ScenarioConfig:
    scenario, _ = _fixture()
    seed = quake.pop("seed", None)
    update: dict[str, object] = {
        "earthquake": scenario.earthquake.model_copy(update=quake),
    }
    if seed is not None:
        update["seed"] = int(seed)
    return scenario.model_copy(update=update)


def _initial_states(map_def: MapDefinition) -> dict[str, EdgeState]:
    return {e.edgeId: e.state for e in map_def.edges}


def _summary(schedule):
    return [(e.tick, e.edge_id, e.new_state.value, e.cause.value) for e in schedule.events]


# ---------- regression and determinism ----------


def test_fixture_schedule_regression():
    """Pins the seed-42 fixture outcome. If the rule changes on purpose, bump
    RULE_VERSION and update this expectation in the same PR."""
    scenario, map_def = _fixture()
    schedule = generate_road_damage_schedule(scenario, map_def)
    assert schedule.rule_version == RULE_VERSION
    assert _summary(schedule) == [
        (0, "e3", "degraded", "initial_damage"),
        (0, "e4", "blocked", "initial_damage"),
        (0, "e6", "degraded", "initial_damage"),
    ]


def test_same_inputs_same_schedule():
    scenario, map_def = _fixture()
    assert generate_road_damage_schedule(scenario, map_def) == generate_road_damage_schedule(
        scenario, map_def
    )


def test_schedule_does_not_depend_on_map_file_order():
    scenario, map_def = _fixture()
    shuffled = map_def.model_copy(
        update={"nodes": tuple(reversed(map_def.nodes)), "edges": tuple(reversed(map_def.edges))}
    )
    assert generate_road_damage_schedule(scenario, map_def) == generate_road_damage_schedule(
        scenario, shuffled
    )


def test_different_seeds_give_different_schedules():
    _, map_def = _fixture()
    schedules = {
        tuple(_summary(generate_road_damage_schedule(_scenario(seed=s), map_def)))
        for s in range(10)
    }
    assert len(schedules) > 1


def test_schedule_is_independent_of_pythonhashseed():
    code = (
        "from drsim.simulation.world.loader import load_scenario_with_map as load;"
        "from drsim.simulation.world.hazards.road_damage import generate_road_damage_schedule;"
        f"s, m = load(r'{ROOT / 'scenarios' / 'earthquake_small.json'}',"
        f" r'{ROOT / 'scenarios' / 'maps'}');"
        "print(generate_road_damage_schedule(s, m))"
    )
    outputs = set()
    for hash_seed in ("0", "1", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        result = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
        )
        outputs.add(result.stdout)
    assert len(outputs) == 1


def test_one_edge_outcome_does_not_shift_other_edges():
    scenario, map_def = _fixture()
    # Pre-block e3 in the map: it gets no events, but every other edge must be unchanged.
    edges = tuple(
        e.model_copy(update={"state": EdgeState.BLOCKED}) if e.edgeId == "e3" else e
        for e in map_def.edges
    )
    changed = generate_road_damage_schedule(scenario, map_def.model_copy(update={"edges": edges}))
    baseline = generate_road_damage_schedule(scenario, map_def)
    assert [e for e in changed.events if e.edge_id == "e3"] == []
    assert [e for e in changed.events if e.edge_id != "e3"] == [
        e for e in baseline.events if e.edge_id != "e3"
    ]


# ---------- the damage rule ----------


def test_roads_outside_radius_are_never_damaged():
    _, map_def = _fixture()
    for seed in range(50):
        schedule = generate_road_damage_schedule(_scenario(seed=seed), map_def)
        assert {e.edge_id for e in schedule.events} <= NEAR_EDGES


def test_weak_earthquake_damages_nothing():
    _, map_def = _fixture()
    scenario = _scenario(magnitude=DEFAULT_RULE.min_damaging_magnitude)
    assert generate_road_damage_schedule(scenario, map_def).events == ()


def test_zero_damage_scale_damages_nothing():
    _, map_def = _fixture()
    for seed in range(20):
        scenario = _scenario(initialDamageScale=0.0, seed=seed)
        assert generate_road_damage_schedule(scenario, map_def).events == ()


def test_blocked_share_one_blocks_every_damaged_road_with_no_collapse():
    _, map_def = _fixture()
    rule = RoadDamageRule(blocked_share=1.0, secondary_collapse_probability=1.0)
    schedule = generate_road_damage_schedule(_scenario(), map_def, rule)
    assert _summary(schedule) == [(0, e, "blocked", "initial_damage") for e in sorted(NEAR_EDGES)]


def test_degraded_roads_can_collapse_later_within_window():
    _, map_def = _fixture()
    rule = RoadDamageRule(blocked_share=0.0, secondary_collapse_probability=1.0)
    schedule = generate_road_damage_schedule(_scenario(), map_def, rule)

    initial = [e for e in schedule.events if e.cause is DamageCause.INITIAL_DAMAGE]
    later = [e for e in schedule.events if e.cause is DamageCause.SECONDARY_COLLAPSE]
    assert {(e.edge_id, e.new_state, e.tick) for e in initial} == {
        (e, EdgeState.DEGRADED, 0) for e in NEAR_EDGES
    }
    assert {e.edge_id for e in later} == NEAR_EDGES
    for event in later:
        assert event.new_state is EdgeState.BLOCKED
        assert rule.secondary_collapse_min_tick <= event.tick <= rule.secondary_collapse_max_tick


def test_events_sorted_by_tick_then_edge():
    _, map_def = _fixture()
    rule = RoadDamageRule(blocked_share=0.0, secondary_collapse_probability=1.0)
    for seed in range(20):
        events = generate_road_damage_schedule(_scenario(seed=seed), map_def, rule).events
        assert list(events) == sorted(events, key=lambda e: (e.tick, e.edge_id))


def test_already_degraded_road_gets_no_tick0_event_but_may_collapse():
    scenario, map_def = _fixture()
    edges = tuple(
        e.model_copy(update={"state": EdgeState.DEGRADED}) if e.edgeId in NEAR_EDGES else e
        for e in map_def.edges
    )
    rule = RoadDamageRule(blocked_share=0.0, secondary_collapse_probability=1.0)
    schedule = generate_road_damage_schedule(
        scenario, map_def.model_copy(update={"edges": edges}), rule
    )
    assert all(e.cause is DamageCause.SECONDARY_COLLAPSE for e in schedule.events)
    assert {e.edge_id for e in schedule.events} == NEAR_EDGES


def test_closeness_uses_distance_to_road_segment_not_midpoint():
    _, map_def = _fixture()
    pos = {n.nodeId: (n.x, n.y) for n in map_def.nodes}
    e1 = next(e for e in map_def.edges if e.edgeId == "e1")  # (200,200) -> (1000,200)
    # Epicentre right next to the end of e1: far from its midpoint (600,200), close to the road.
    assert edge_closeness(e1, pos, (1000, 300), 750) == pytest.approx(1 - 100 / 750)
    assert edge_closeness(e1, pos, (600, 200), 750) == 1.0
    assert edge_closeness(e1, pos, (600, 1000), 750) == 0.0
    assert edge_closeness(e1, pos, (600, 200), 0) == 0.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"radius_meters_per_magnitude": 0},
        {"blocked_share": 1.5},
        {"secondary_collapse_probability": -0.1},
        {"secondary_collapse_min_tick": 0},
        {"secondary_collapse_min_tick": 50, "secondary_collapse_max_tick": 10},
    ],
)
def test_invalid_rule_rejected(kwargs):
    with pytest.raises(ValueError):
        RoadDamageRule(**kwargs)


# ---------- hazard phase helper ----------


def test_road_changes_at_tick0_reports_old_and_new_state_without_mutating():
    scenario, map_def = _fixture()
    schedule = generate_road_damage_schedule(scenario, map_def)
    states = _initial_states(map_def)
    before = dict(states)

    changes = road_changes_at(schedule, states, tick=0)

    assert states == before
    assert changes == (
        EdgeStateChange("e3", EdgeState.OPEN, EdgeState.DEGRADED, DamageCause.INITIAL_DAMAGE),
        EdgeStateChange("e4", EdgeState.OPEN, EdgeState.BLOCKED, DamageCause.INITIAL_DAMAGE),
        EdgeStateChange("e6", EdgeState.OPEN, EdgeState.DEGRADED, DamageCause.INITIAL_DAMAGE),
    )
    assert road_changes_at(schedule, states, tick=1) == ()


def test_road_changes_never_repair_a_road():
    scenario, map_def = _fixture()
    schedule = generate_road_damage_schedule(scenario, map_def)
    states = {**_initial_states(map_def), "e3": EdgeState.BLOCKED}
    assert "e3" not in {c.edge_id for c in road_changes_at(schedule, states, tick=0)}


# ---------- integration with routing ----------


def _apply(states: dict[str, EdgeState], changes: tuple[EdgeStateChange, ...]) -> None:
    for change in changes:
        states[change.edge_id] = change.new_state


def test_routes_avoid_roads_blocked_by_the_earthquake():
    scenario, map_def = _fixture()
    graph = RoadGraph.from_map(map_def)
    states = _initial_states(map_def)
    _apply(states, road_changes_at(generate_road_damage_schedule(scenario, map_def), states, 0))

    route = shortest_route(graph, states, "n4", "n6", TICK)
    assert route is not None
    assert "e4" not in route.edge_ids  # e4 is blocked for seed 42


def test_full_isolation_makes_incident_node_unreachable():
    _, map_def = _fixture()
    graph = RoadGraph.from_map(map_def)
    rule = RoadDamageRule(blocked_share=1.0)
    schedule = generate_road_damage_schedule(_scenario(), map_def, rule)
    states = _initial_states(map_def)
    _apply(states, road_changes_at(schedule, states, 0))

    assert shortest_route(graph, states, "n1", "n5", TICK) is None
    assert shortest_route(graph, states, "n1", "n6", TICK) is not None
