from drsim.shared.schemas import SimulationSnapshot, UnitSummary
from drsim.simulation.entities.incident_models import DEFAULT_RULES
from drsim.simulation.entities.incident_rules import to_incident_summary, to_victim_summary
from drsim.simulation.state import SimulationState


def build_snapshot(state: SimulationState) -> SimulationSnapshot:
    pos = state.node_pos

    return SimulationSnapshot(
        runId=state.run_id,
        tick=state.tick,
        simulationTimeSeconds=state.tick * state.scenario.tickDurationSeconds,
        status=state.status,
        units=tuple(
            UnitSummary(
                unitId=u.id,
                unitType=u.type,
                status=u.status,
                x=pos[u.node_id][0],
                y=pos[u.node_id][1],
                assignedIncidentId=u.assigned_incident_id,
            )
            for u in sorted(state.units.values(), key=lambda u: u.id)
        ),
        incidents=tuple(
            to_incident_summary(
                inc,
                [state.victims[v] for v in inc.victim_ids],
                *pos[inc.node_id],
                any(u.assigned_incident_id == inc.incident_id for u in state.units.values()),
                DEFAULT_RULES,
            )
            for inc in (state.incidents[k] for k in sorted(state.incidents))
        ),
        victims=tuple(
            to_victim_summary(state.victims[k], DEFAULT_RULES) for k in sorted(state.victims)
        ),
    )