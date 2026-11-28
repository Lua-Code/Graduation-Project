import pytest

from drsim.shared.schemas import MapDefinition, ScenarioConfig
from drsim.simulation.world.validation import validate_map, validate_scenario

# A 2 x 2 square: a -- b
#                 |    |
#                 c -- d     (100 m sides, hospital at d)


def _map(**overrides) -> MapDefinition:
    data = {
        "mapId": "tiny",
        "widthMeters": 200,
        "heightMeters": 200,
        "nodes": [
            {"nodeId": "a", "x": 0, "y": 0},
            {"nodeId": "b", "x": 100, "y": 0},
            {"nodeId": "c", "x": 0, "y": 100},
            {"nodeId": "d", "x": 100, "y": 100},
        ],
        "edges": [
            _edge("ab", "a", "b"),
            _edge("ac", "a", "c"),
            _edge("bd", "b", "d"),
            _edge("cd", "c", "d"),
        ],
        "facilities": [
            {"facilityId": "h1", "facilityType": "hospital", "nodeId": "d", "capacity": 5}
        ],
    }
    data.update(overrides)
    return MapDefinition.model_validate(data)


def _edge(edge_id, source, target, *, length=100, state="open", bidirectional=True):
    return {
        "edgeId": edge_id,
        "sourceNodeId": source,
        "targetNodeId": target,
        "lengthMeters": length,
        "speedMetersPerSecond": 10,
        "bidirectional": bidirectional,
        "state": state,
    }


def _scenario(**overrides) -> ScenarioConfig:
    data = {
        "scenarioId": "s",
        "seed": 1,
        "mapId": "tiny",
        "earthquake": {"magnitude": 6.0, "epicenterX": 50, "epicenterY": 50},
        "units": [{"unitId": "u1", "unitType": "ambulance", "nodeId": "a"}],
        "incidents": [
            {
                "incidentId": "i1",
                "incidentType": "building_collapse",
                "nodeId": "b",
                "priority": 3,
                "victimCount": 1,
            }
        ],
    }
    data.update(overrides)
    return ScenarioConfig.model_validate(data)


def _incident(incident_id, node_id):
    return {
        "incidentId": incident_id,
        "incidentType": "building_collapse",
        "nodeId": node_id,
        "priority": 3,
        "victimCount": 1,
    }


# ---------- map ----------


def test_valid_map_has_no_problems():
    assert validate_map(_map()) == ()


def test_road_shorter_than_straight_line_is_reported():
    edges = [_edge("ab", "a", "b", length=50), _edge("ac", "a", "c"), _edge("bd", "b", "d")]
    edges.append(_edge("cd", "c", "d"))
    problems = validate_map(_map(edges=edges))
    assert problems == ("Edge ab is 50 m long but its nodes are 100.0 m apart",)


def test_rounded_length_within_tolerance_is_accepted():
    edges = [_edge("ab", "a", "b", length=99.5), _edge("ac", "a", "c"), _edge("bd", "b", "d")]
    edges.append(_edge("cd", "c", "d"))
    assert validate_map(_map(edges=edges)) == ()


def test_isolated_node_is_reported_both_ways():
    edges = [_edge("ab", "a", "b"), _edge("ac", "a", "c"), _edge("cd", "c", "b")]
    nodes = [
        {"nodeId": "a", "x": 0, "y": 0},
        {"nodeId": "b", "x": 100, "y": 0},
        {"nodeId": "c", "x": 0, "y": 100},
        {"nodeId": "d", "x": 100, "y": 100},
    ]
    edges[2]["lengthMeters"] = 150
    problems = validate_map(_map(nodes=nodes, edges=edges, facilities=[]))
    assert "Node d cannot be reached from a on the initial roads" in problems
    assert "Node d cannot reach a on the initial roads" in problems


def test_blocked_road_counts_as_missing():
    edges = [
        _edge("ab", "a", "b"),
        _edge("ac", "a", "c"),
        _edge("bd", "b", "d", state="blocked"),
        _edge("cd", "c", "d", state="blocked"),
    ]
    problems = validate_map(_map(edges=edges))
    assert "Node d cannot be reached from a on the initial roads" in problems


def test_degraded_road_still_connects():
    edges = [
        _edge("ab", "a", "b"),
        _edge("ac", "a", "c"),
        _edge("bd", "b", "d", state="degraded"),
        _edge("cd", "c", "d", state="blocked"),
    ]
    assert validate_map(_map(edges=edges)) == ()


def test_one_way_dead_end_is_reported():
    # A ring of one-way roads a -> b -> d -> c -> a is fine; reversing one breaks it.
    ring = [
        _edge("ab", "a", "b", bidirectional=False),
        _edge("bd", "b", "d", bidirectional=False),
        _edge("cd", "d", "c", bidirectional=False),
        _edge("ac", "c", "a", bidirectional=False),
    ]
    assert validate_map(_map(edges=ring)) == ()

    ring[3] = _edge("ac", "a", "c", bidirectional=False)
    problems = validate_map(_map(edges=ring))
    assert "Node b cannot reach a on the initial roads" in problems


def test_map_without_hospital_is_reported():
    assert validate_map(_map(facilities=[])) == ("Map has no hospital",)


def test_zone_outside_map_is_reported():
    zone = {
        "zoneId": "z1",
        "name": "Too big",
        "polygon": [{"x": 0, "y": 0}, {"x": 300, "y": 0}, {"x": 0, "y": 100}],
    }
    assert validate_map(_map(zones=[zone])) == ("Zone z1 extends outside the map",)


# ---------- scenario ----------


def test_valid_scenario_has_no_problems():
    assert validate_scenario(_scenario(), _map()) == ()


def test_wrong_map_is_reported():
    problems = validate_scenario(_scenario(mapId="other"), _map())
    assert problems == ("Scenario expects map other, got tiny",)


def test_duplicate_ids_are_reported():
    unit = {"unitId": "u1", "unitType": "fire", "nodeId": "a"}
    scenario = _scenario(
        units=[unit, unit],
        incidents=[_incident("i1", "b"), _incident("i1", "c")],
    )
    problems = validate_scenario(scenario, _map())
    assert "Unit ID u1 is used more than once" in problems
    assert "Incident ID i1 is used more than once" in problems


def test_epicentre_outside_map_is_reported():
    quake = {"magnitude": 6.0, "epicenterX": 500, "epicenterY": 50}
    problems = validate_scenario(_scenario(earthquake=quake), _map())
    assert problems == ("Earthquake epicentre is outside the map",)


@pytest.mark.parametrize(
    "overrides, expected",
    [
        (
            {"units": [{"unitId": "u1", "unitType": "fire", "nodeId": "zz"}]},
            "Unit u1 is on unknown node zz",
        ),
        ({"incidents": [_incident("i1", "zz")]}, "Incident i1 is on unknown node zz"),
    ],
)
def test_unknown_nodes_are_reported(overrides, expected):
    assert validate_scenario(_scenario(**overrides), _map()) == (expected,)


def test_incident_no_unit_can_reach_is_reported():
    # Only one-way roads out of b: units at a can never get there.
    edges = [
        _edge("ba", "b", "a", bidirectional=False),
        _edge("ac", "a", "c"),
        _edge("bd", "b", "d", bidirectional=False),
        _edge("cd", "c", "d"),
    ]
    problems = validate_scenario(_scenario(), _map(edges=edges))
    assert problems == ("Incident i1 cannot be reached by any unit",)


def test_incident_that_cannot_reach_hospital_is_reported():
    edges = [_edge("ab", "a", "b"), _edge("ac", "a", "c"), _edge("cd", "c", "d", state="blocked")]
    edges.append(_edge("bd", "b", "d", state="blocked"))
    problems = validate_scenario(_scenario(), _map(edges=edges))
    assert problems == ("Incident i1 cannot reach any hospital",)


def test_problems_are_in_stable_order():
    scenario = _scenario(
        incidents=[_incident("i2", "zz"), _incident("i1", "yy")],
    )
    assert validate_scenario(scenario, _map()) == (
        "Incident i1 is on unknown node yy",
        "Incident i2 is on unknown node zz",
    )
