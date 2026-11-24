"""Road graph, edge travel time and deterministic routing (Phase 1, Module B).

Vehicles move only on the road graph. This module answers two questions for the
rest of the system:

* "Can a unit get from A to B?"            -> ``is_reachable`` / ``shortest_route``
* "How many ticks will it take?"           -> ``edge_travel_ticks`` / ``travel_ticks_matrix``

Rules implemented here (see Module Contracts §5.3, D13, D14):

* Travel time is an integer number of ticks: ``ceil(seconds / tickDurationSeconds)``,
  with a minimum of 1 tick for any traversable edge.
* A BLOCKED edge is never part of a route.
* A DEGRADED edge takes ``degraded_multiplier`` times as long (configured per scenario
  via ``ScenarioConfig.degradedTravelMultiplier``).
* Ties are broken deterministically: fewest total ticks first, then the
  lexicographically smallest node-ID sequence, then the smallest edge-ID sequence.

These functions are pure: they read the static map and the current edge states and
never mutate simulation state. The engine owns ``SimulationState.edge_states``.
"""

import heapq
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from drsim.shared.enums import EdgeState
from drsim.shared.schemas import DEFAULT_DEGRADED_TRAVEL_MULTIPLIER, MapDefinition, MapEdge

# Guards against float noise turning an exact multiple (e.g. 20.000000000004 s) into an
# extra tick. Travel times are derived from metres and m/s, so 1e-9 s is far below
# any meaningful difference.
_FLOAT_TOLERANCE_SECONDS = 1e-9

type EdgeStates = Mapping[str, EdgeState]


class UnknownNodeError(ValueError):
    """Raised when a routing query references a node that is not on the map."""


@dataclass(frozen=True)
class Route:
    """A path through the road graph.

    ``node_ids`` starts at the origin and ends at the destination.
    ``edge_ids[i]`` connects ``node_ids[i]`` and ``node_ids[i + 1]``.
    """

    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    total_ticks: int


@dataclass(frozen=True)
class _Step:
    neighbor_id: str
    edge: MapEdge


@dataclass(frozen=True)
class RoadGraph:
    """Static road topology built once from a ``MapDefinition``.

    Holds no live state: edge passability is passed into each query.
    """

    node_ids: frozenset[str]
    edges: Mapping[str, MapEdge]
    adjacency: Mapping[str, tuple[_Step, ...]]

    @classmethod
    def from_map(cls, map_def: MapDefinition) -> "RoadGraph":
        neighbors: dict[str, list[_Step]] = {n.nodeId: [] for n in map_def.nodes}
        for edge in map_def.edges:
            neighbors[edge.sourceNodeId].append(_Step(edge.targetNodeId, edge))
            if edge.bidirectional:
                neighbors[edge.targetNodeId].append(_Step(edge.sourceNodeId, edge))

        # Sorted so iteration order never depends on the order of the map file.
        adjacency = {
            node_id: tuple(sorted(steps, key=lambda s: (s.neighbor_id, s.edge.edgeId)))
            for node_id, steps in neighbors.items()
        }
        return cls(
            node_ids=frozenset(neighbors),
            edges={e.edgeId: e for e in map_def.edges},
            adjacency=adjacency,
        )


def edge_travel_ticks(
    edge: MapEdge,
    state: EdgeState,
    tick_seconds: int,
    *,
    degraded_multiplier: float = DEFAULT_DEGRADED_TRAVEL_MULTIPLIER,
) -> int | None:
    """Integer ticks needed to traverse ``edge`` in ``state``; ``None`` if blocked."""
    if tick_seconds <= 0:
        raise ValueError("tick_seconds must be positive")
    if state is EdgeState.BLOCKED:
        return None

    seconds = edge.lengthMeters / edge.speedMetersPerSecond
    if state is EdgeState.DEGRADED:
        seconds *= degraded_multiplier

    ticks = math.ceil(seconds / tick_seconds - _FLOAT_TOLERANCE_SECONDS / tick_seconds)
    return max(1, ticks)


def _edge_state(edge: MapEdge, edge_states: EdgeStates) -> EdgeState:
    # Falls back to the map's initial state if the engine has no entry for the edge.
    return edge_states.get(edge.edgeId, edge.state)


def _require_node(graph: RoadGraph, node_id: str) -> None:
    if node_id not in graph.node_ids:
        raise UnknownNodeError(f"Unknown road node: {node_id}")


def _shortest_routes(
    graph: RoadGraph,
    edge_states: EdgeStates,
    origin: str,
    tick_seconds: int,
    target: str | None = None,
    *,
    degraded_multiplier: float = DEFAULT_DEGRADED_TRAVEL_MULTIPLIER,
) -> dict[str, Route]:
    """Dijkstra from ``origin`` with a total, deterministic ordering on candidate paths.

    Each candidate is ranked by (ticks, node-ID path, edge-ID path). Because two
    equal-cost paths to the same node cannot be prefixes of one another (edge costs are
    >= 1), extending both by the same step preserves their order, so the label kept for
    every node is the minimum under this ranking.
    """
    _require_node(graph, origin)

    best: dict[str, tuple[int, tuple[str, ...], tuple[str, ...]]] = {origin: (0, (origin,), ())}
    heap: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = [(0, (origin,), ())]
    settled: dict[str, Route] = {}

    while heap:
        ticks, nodes, edges = heapq.heappop(heap)
        node_id = nodes[-1]
        if node_id in settled or best[node_id] != (ticks, nodes, edges):
            continue
        settled[node_id] = Route(node_ids=nodes, edge_ids=edges, total_ticks=ticks)
        if node_id == target:
            break

        for step in graph.adjacency[node_id]:
            if step.neighbor_id in settled:
                continue
            cost = edge_travel_ticks(
                step.edge,
                _edge_state(step.edge, edge_states),
                tick_seconds,
                degraded_multiplier=degraded_multiplier,
            )
            if cost is None:
                continue
            candidate = (ticks + cost, nodes + (step.neighbor_id,), edges + (step.edge.edgeId,))
            current = best.get(step.neighbor_id)
            if current is None or candidate < current:
                best[step.neighbor_id] = candidate
                heapq.heappush(heap, candidate)

    return settled


def shortest_route(
    graph: RoadGraph,
    edge_states: EdgeStates,
    origin: str,
    destination: str,
    tick_seconds: int,
    *,
    degraded_multiplier: float = DEFAULT_DEGRADED_TRAVEL_MULTIPLIER,
) -> Route | None:
    """Fastest passable route, or ``None`` if the destination is unreachable.

    ``None`` means infeasible; the command layer maps it to ``ROUTE_INFEASIBLE``.
    """
    _require_node(graph, destination)
    return _shortest_routes(
        graph,
        edge_states,
        origin,
        tick_seconds,
        target=destination,
        degraded_multiplier=degraded_multiplier,
    ).get(destination)


def is_reachable(
    graph: RoadGraph,
    edge_states: EdgeStates,
    origin: str,
    destination: str,
    tick_seconds: int,
    *,
    degraded_multiplier: float = DEFAULT_DEGRADED_TRAVEL_MULTIPLIER,
) -> bool:
    """True if a passable route exists. Backs the dispatch ``ROUTE_INFEASIBLE`` check."""
    route = shortest_route(
        graph,
        edge_states,
        origin,
        destination,
        tick_seconds,
        degraded_multiplier=degraded_multiplier,
    )
    return route is not None


def travel_ticks_matrix(
    graph: RoadGraph,
    edge_states: EdgeStates,
    origins: Iterable[str],
    destinations: Iterable[str],
    tick_seconds: int,
    *,
    degraded_multiplier: float = DEFAULT_DEGRADED_TRAVEL_MULTIPLIER,
) -> dict[tuple[str, str], int | None]:
    """Travel ticks for every (origin, destination) pair; ``None`` where unreachable.

    Intended for allocation strategies (e.g. unit nodes x incident nodes). Runs one
    search per distinct origin.
    """
    destination_ids = sorted(set(destinations))
    for node_id in destination_ids:
        _require_node(graph, node_id)

    matrix: dict[tuple[str, str], int | None] = {}
    for origin in sorted(set(origins)):
        routes = _shortest_routes(
            graph,
            edge_states,
            origin,
            tick_seconds,
            degraded_multiplier=degraded_multiplier,
        )
        for destination in destination_ids:
            route = routes.get(destination)
            matrix[(origin, destination)] = None if route is None else route.total_ticks
    return matrix
