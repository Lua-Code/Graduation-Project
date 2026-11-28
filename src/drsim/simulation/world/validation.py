"""Semantic checks for maps and scenarios (Module B).

The Pydantic schemas check each field and the loader checks that IDs refer to real nodes.
This module checks that a map and scenario make sense *as a simulation*:

* every road is at least as long as the straight line between its ends;
* with the map's initial road states, every node can reach every other node;
* the map has at least one hospital, and zones lie inside the map;
* scenario IDs are unique, every unit and incident stands on a real node, and the
  epicentre is inside the map;
* every incident can be reached by at least one unit and can reach a hospital.

Each function returns a tuple of human-readable problems (empty when valid), in a
stable order, so a test or tool can report every problem at once.
"""

import math

from drsim.shared.enums import EdgeState, FacilityType
from drsim.shared.schemas import MapDefinition, ScenarioConfig
from drsim.simulation.world.graph import RoadGraph, travel_ticks_matrix

# Lengths come from JSON and may be rounded; allow a road to be this much shorter
# than the straight line between its ends before calling it wrong.
_LENGTH_TOLERANCE_METERS = 1.0

# Reachability does not depend on travel time, so any valid tick length works here.
_ANY_TICK_SECONDS = 10


def _initial_states(map_def: MapDefinition) -> dict[str, EdgeState]:
    return {e.edgeId: e.state for e in map_def.edges}


def _duplicates(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for item in ids:
        (dupes if item in seen else seen).add(item)
    return sorted(dupes)


def validate_map(map_def: MapDefinition) -> tuple[str, ...]:
    """Problems with a map on its own; empty if the map is usable."""
    problems: list[str] = []
    pos = {n.nodeId: (n.x, n.y) for n in map_def.nodes}

    for edge in sorted(map_def.edges, key=lambda e: e.edgeId):
        (x1, y1), (x2, y2) = pos[edge.sourceNodeId], pos[edge.targetNodeId]
        straight = math.hypot(x2 - x1, y2 - y1)
        if edge.lengthMeters + _LENGTH_TOLERANCE_METERS < straight:
            problems.append(
                f"Edge {edge.edgeId} is {edge.lengthMeters:g} m long but its nodes are "
                f"{straight:.1f} m apart"
            )

    # Strongly connected <=> one node reaches every node and every node reaches it.
    graph = RoadGraph.from_map(map_def)
    states = _initial_states(map_def)
    node_ids = sorted(pos)
    hub = node_ids[0]
    from_hub = travel_ticks_matrix(graph, states, [hub], node_ids, _ANY_TICK_SECONDS)
    to_hub = travel_ticks_matrix(graph, states, node_ids, [hub], _ANY_TICK_SECONDS)
    for node_id in node_ids:
        if from_hub[(hub, node_id)] is None:
            problems.append(f"Node {node_id} cannot be reached from {hub} on the initial roads")
        if to_hub[(node_id, hub)] is None:
            problems.append(f"Node {node_id} cannot reach {hub} on the initial roads")

    if not any(f.facilityType is FacilityType.HOSPITAL for f in map_def.facilities):
        problems.append("Map has no hospital")

    for zone in sorted(map_def.zones, key=lambda z: z.zoneId):
        inside = all(
            0 <= p.x <= map_def.widthMeters and 0 <= p.y <= map_def.heightMeters
            for p in zone.polygon
        )
        if not inside:
            problems.append(f"Zone {zone.zoneId} extends outside the map")

    return tuple(problems)


def validate_scenario(scenario: ScenarioConfig, map_def: MapDefinition) -> tuple[str, ...]:
    """Problems with a scenario on the given map; empty if it can be run.

    Checks the scenario only. Call ``validate_map`` for problems with the map itself.
    """
    problems: list[str] = []

    if scenario.mapId != map_def.mapId:
        problems.append(f"Scenario expects map {scenario.mapId}, got {map_def.mapId}")

    for dupe in _duplicates([u.unitId for u in scenario.units]):
        problems.append(f"Unit ID {dupe} is used more than once")
    for dupe in _duplicates([i.incidentId for i in scenario.incidents]):
        problems.append(f"Incident ID {dupe} is used more than once")

    quake = scenario.earthquake
    if not (
        0 <= quake.epicenterX <= map_def.widthMeters
        and 0 <= quake.epicenterY <= map_def.heightMeters
    ):
        problems.append("Earthquake epicentre is outside the map")

    node_ids = {n.nodeId for n in map_def.nodes}
    for unit in sorted(scenario.units, key=lambda u: u.unitId):
        if unit.nodeId not in node_ids:
            problems.append(f"Unit {unit.unitId} is on unknown node {unit.nodeId}")
    incidents = sorted(scenario.incidents, key=lambda i: i.incidentId)
    for incident in incidents:
        if incident.nodeId not in node_ids:
            problems.append(f"Incident {incident.incidentId} is on unknown node {incident.nodeId}")
    if problems:
        return tuple(problems)  # reachability needs every node to exist

    graph = RoadGraph.from_map(map_def)
    states = _initial_states(map_def)
    unit_nodes = sorted({u.nodeId for u in scenario.units})
    incident_nodes = sorted({i.nodeId for i in incidents})
    hospital_nodes = sorted(
        {f.nodeId for f in map_def.facilities if f.facilityType is FacilityType.HOSPITAL}
    )
    from_units = travel_ticks_matrix(graph, states, unit_nodes, incident_nodes, _ANY_TICK_SECONDS)
    to_hospitals = travel_ticks_matrix(
        graph, states, incident_nodes, hospital_nodes, _ANY_TICK_SECONDS
    )

    for incident in incidents:
        node = incident.nodeId
        if all(from_units[(u, node)] is None for u in unit_nodes):
            problems.append(f"Incident {incident.incidentId} cannot be reached by any unit")
        if all(to_hospitals[(node, h)] is None for h in hospital_nodes):
            problems.append(f"Incident {incident.incidentId} cannot reach any hospital")

    return tuple(problems)
