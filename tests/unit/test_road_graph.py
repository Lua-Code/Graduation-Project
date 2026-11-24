from itertools import permutations
from pathlib import Path

import pytest

from drsim.shared.enums import EdgeState
from drsim.shared.schemas import MapDefinition, MapEdge
from drsim.simulation.world.graph import (
    DEGRADED_TRAVEL_MULTIPLIER,
    RoadGraph,
    UnknownNodeError,
    edge_travel_ticks,
    is_reachable,
    shortest_route,
    travel_ticks_matrix,
)
from drsim.simulation.world.loader import load_map

ROOT = Path(__file__).resolve().parents[2]
TICK = 10


def _fixture_map() -> MapDefinition:
    return load_map(ROOT / "scenarios" / "maps" / "synthetic_city_01.json")


def _graph() -> RoadGraph:
    return RoadGraph.from_map(_fixture_map())


def _edge(length: float, speed: float, **kw: object) -> MapEdge:
    data: dict[str, object] = {
        "edgeId": "e",
        "sourceNodeId": "a",
        "targetNodeId": "b",
        "lengthMeters": length,
        "speedMetersPerSecond": speed,
        "state": EdgeState.OPEN,
    }
    data.update(kw)
    return MapEdge.model_validate(data)


def _all_open() -> dict[str, EdgeState]:
    return {e: EdgeState.OPEN for e in _graph().edges}


def _with(**states: EdgeState) -> dict[str, EdgeState]:
    return {**_all_open(), **states}


# ---------- edge travel ticks (D13 / D14) ----------


@pytest.mark.parametrize(
    ("length", "speed", "expected"),
    [
        (100, 10, 1),  # exactly 10 s -> 1 tick
        (200, 10, 2),  # exactly 20 s -> 2 ticks
        (101, 10, 2),  # just above a multiple -> rounds up
        (99, 10, 1),  # just below a multiple -> rounds up
        (5, 10, 1),  # shorter than one tick -> minimum 1
        (230, 10, 3),  # 23 s -> 3 ticks (example from D14)
        (800, 13.9, 6),  # fixture e1: 57.6 s
        (800, 11.1, 8),  # fixture e5: 72.1 s
        (30, 0.1, 30),  # float noise: 300.00000000000006 s must stay 30 ticks
    ],
)
def test_travel_ticks_round_up_with_minimum_one(length, speed, expected):
    assert edge_travel_ticks(_edge(length, speed), EdgeState.OPEN, TICK) == expected


def test_blocked_edge_has_no_travel_time():
    assert edge_travel_ticks(_edge(100, 10), EdgeState.BLOCKED, TICK) is None


def test_degraded_edge_is_slower():
    # 100 m at 10 m/s = 10 s; degraded multiplies time before rounding.
    expected = DEGRADED_TRAVEL_MULTIPLIER * 1
    assert edge_travel_ticks(_edge(100, 10), EdgeState.DEGRADED, TICK) == expected
    assert edge_travel_ticks(_edge(800, 13.9), EdgeState.DEGRADED, TICK) == 12


def test_non_positive_tick_rejected():
    with pytest.raises(ValueError):
        edge_travel_ticks(_edge(100, 10), EdgeState.OPEN, 0)


# ---------- routing on the fixture map ----------
#
#   n1 --e1-- n2 --e2-- n3        horizontal edges: 6 ticks
#   |         |         |         vertical edges:   8 ticks
#   e5        e6        e7
#   |         |         |
#   n4 --e3-- n5 --e4-- n6 (hospital h1)
#
# Every monotone n1 -> n6 path costs 20 ticks, which exercises the tie-break.


def test_route_to_self_is_empty():
    route = shortest_route(_graph(), _all_open(), "n1", "n1", TICK)
    assert route is not None
    assert (route.node_ids, route.edge_ids, route.total_ticks) == (("n1",), (), 0)


def test_tie_break_prefers_lexicographically_smallest_node_path():
    route = shortest_route(_graph(), _all_open(), "n1", "n6", TICK)
    assert route is not None
    assert route.total_ticks == 20
    assert route.node_ids == ("n1", "n2", "n3", "n6")
    assert route.edge_ids == ("e1", "e2", "e7")


def test_blocked_edge_forces_reroute():
    route = shortest_route(_graph(), _with(e2=EdgeState.BLOCKED), "n1", "n6", TICK)
    assert route is not None
    assert route.node_ids == ("n1", "n2", "n5", "n6")
    assert "e2" not in route.edge_ids


def test_degraded_edge_avoided_when_faster_route_exists():
    route = shortest_route(_graph(), _with(e1=EdgeState.DEGRADED), "n1", "n6", TICK)
    assert route is not None
    assert route.node_ids == ("n1", "n4", "n5", "n6")
    assert route.total_ticks == 20


def test_bidirectional_edge_can_be_traversed_backwards():
    route = shortest_route(_graph(), _all_open(), "n6", "n1", TICK)
    assert route is not None
    assert route.total_ticks == 20
    assert route.node_ids[0] == "n6" and route.node_ids[-1] == "n1"


def test_unreachable_destination_returns_none():
    states = _with(e4=EdgeState.BLOCKED, e7=EdgeState.BLOCKED)
    assert shortest_route(_graph(), states, "n1", "n6", TICK) is None
    assert not is_reachable(_graph(), states, "n1", "n6", TICK)
    assert is_reachable(_graph(), states, "n1", "n5", TICK)


def test_blocked_edge_never_appears_in_any_route():
    graph = _graph()
    nodes = sorted(graph.node_ids)
    for blocked in sorted(graph.edges):
        states = _with(**{blocked: EdgeState.BLOCKED})
        for origin, destination in permutations(nodes, 2):
            route = shortest_route(graph, states, origin, destination, TICK)
            assert route is not None  # the grid stays connected with one edge blocked
            assert blocked not in route.edge_ids


def test_missing_edge_state_falls_back_to_map_state():
    route = shortest_route(_graph(), {}, "n1", "n6", TICK)
    assert route is not None and route.total_ticks == 20


def test_unknown_node_raises():
    with pytest.raises(UnknownNodeError):
        shortest_route(_graph(), _all_open(), "n1", "nope", TICK)
    with pytest.raises(UnknownNodeError):
        shortest_route(_graph(), _all_open(), "nope", "n1", TICK)


# ---------- direction and parallel edges ----------


def _tiny_map(edges: list[dict[str, object]]) -> MapDefinition:
    return MapDefinition.model_validate(
        {
            "mapId": "tiny",
            "widthMeters": 100,
            "heightMeters": 100,
            "nodes": [
                {"nodeId": "a", "x": 0, "y": 0},
                {"nodeId": "b", "x": 50, "y": 0},
            ],
            "edges": edges,
        }
    )


def _tiny_edge(edge_id: str, **kw: object) -> dict[str, object]:
    return {
        "edgeId": edge_id,
        "sourceNodeId": "a",
        "targetNodeId": "b",
        "lengthMeters": 100,
        "speedMetersPerSecond": 10,
        "state": "open",
        **kw,
    }


def test_one_way_edge_only_goes_forward():
    graph = RoadGraph.from_map(_tiny_map([_tiny_edge("e1", bidirectional=False)]))
    assert shortest_route(graph, {}, "a", "b", TICK) is not None
    assert shortest_route(graph, {}, "b", "a", TICK) is None


def test_parallel_edges_pick_fastest_then_smallest_id():
    faster = RoadGraph.from_map(_tiny_map([_tiny_edge("e1", lengthMeters=300), _tiny_edge("e2")]))
    route = shortest_route(faster, {}, "a", "b", TICK)
    assert route is not None and route.edge_ids == ("e2",)

    tied = RoadGraph.from_map(_tiny_map([_tiny_edge("e2"), _tiny_edge("e1")]))
    route = shortest_route(tied, {}, "a", "b", TICK)
    assert route is not None and route.edge_ids == ("e1",)


# ---------- determinism ----------


def test_route_does_not_depend_on_map_file_order():
    original = _fixture_map()
    shuffled = original.model_copy(
        update={
            "nodes": tuple(reversed(original.nodes)),
            "edges": tuple(reversed(original.edges)),
        }
    )
    a, b = RoadGraph.from_map(original), RoadGraph.from_map(shuffled)
    for origin, destination in permutations(sorted(a.node_ids), 2):
        assert shortest_route(a, {}, origin, destination, TICK) == shortest_route(
            b, {}, origin, destination, TICK
        )


# ---------- travel-time matrix ----------


def test_travel_ticks_matrix_matches_single_routes():
    graph = _graph()
    states = _with(e4=EdgeState.BLOCKED, e7=EdgeState.BLOCKED)
    origins, destinations = ["n2", "n1", "n1"], ["n6", "n5"]

    matrix = travel_ticks_matrix(graph, states, origins, destinations, TICK)

    assert set(matrix) == {("n1", "n5"), ("n1", "n6"), ("n2", "n5"), ("n2", "n6")}
    assert matrix[("n1", "n6")] is None
    for (origin, destination), ticks in matrix.items():
        route = shortest_route(graph, states, origin, destination, TICK)
        assert ticks == (None if route is None else route.total_ticks)


def test_travel_ticks_matrix_rejects_unknown_destination():
    with pytest.raises(UnknownNodeError):
        travel_ticks_matrix(_graph(), {}, ["n1"], ["nope"], TICK)
