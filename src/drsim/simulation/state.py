import random
from dataclasses import dataclass, field

from drsim.shared.enums import EdgeState, RunStatus
from drsim.shared.schemas import MapDefinition, MapFacility, ScenarioConfig, SimulationCommand
from drsim.simulation.entities.incident_models import DEFAULT_RULES, Incident, Victim
from drsim.simulation.entities.incident_rules import initial_health, severity_from_priority
from drsim.simulation.entities.units import UnitState


@dataclass
class SimulationState:
    run_id: str
    scenario: ScenarioConfig
    map_def: MapDefinition
    node_pos: dict[str, tuple[float, float]]
    rng: random.Random
    tick: int = 0
    status: RunStatus = RunStatus.CREATED
    units: dict[str, UnitState] = field(default_factory=dict)
    incidents: dict[str, Incident] = field(default_factory=dict)
    victims: dict[str, Victim] = field(default_factory=dict)
    facilities: dict[str, MapFacility] = field(default_factory=dict)
    edge_states: dict[str, EdgeState] = field(default_factory=dict)
    command_queue: list[SimulationCommand] = field(default_factory=list)
    seen_command_ids: set[str] = field(default_factory=set)


def initialize_state(
    run_id: str, scenario: ScenarioConfig, map_def: MapDefinition
) -> SimulationState:
    rng = random.Random(scenario.seed)

    state = SimulationState(
        run_id=run_id,
        scenario=scenario,
        map_def=map_def,
        node_pos={node.nodeId: (node.x, node.y) for node in map_def.nodes},
        rng=rng,
        edge_states={e.edgeId: e.state for e in map_def.edges},
    )

    state.facilities = {f.facilityId: f for f in map_def.facilities}

    for u in scenario.units:
        state.units[u.unitId] = UnitState(id=u.unitId, type=u.unitType, node_id=u.nodeId)

    for spec in sorted(scenario.incidents, key=lambda i: i.incidentId):
        severity = severity_from_priority(spec.priority)
        victim_ids: list[str] = []

        for n in range(1, spec.victimCount + 1):
            vid = f"{spec.incidentId}-v{n:03d}"
            state.victims[vid] = Victim(
                victim_id=vid,
                incident_id=spec.incidentId,
                severity=severity,
                health=initial_health(severity, DEFAULT_RULES),
            )
            victim_ids.append(vid)

        state.incidents[spec.incidentId] = Incident(
            incident_id=spec.incidentId,
            incident_type=spec.incidentType,
            node_id=spec.nodeId,
            created_tick=0,
            victim_ids=tuple(victim_ids),
        )

    return state