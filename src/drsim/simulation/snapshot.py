from drsim.shared.schemas import (
    IncidentSummary,
    SimulationSnapshot,
    UnitSummary,
    VictimSummary,
)
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
            IncidentSummary(
                incidentId=i.id,
                incidentType=i.type,
                status=i.status,
                x=pos[i.node_id][0],
                y=pos[i.node_id][1],
                priority=i.priority,
            )
            for i in sorted(state.incidents.values(), key=lambda i: i.id)
        ),
        victims=tuple(
            VictimSummary(
                victimId=v.id,
                incidentId=v.incident_id,
                status=v.status,
                healthState=v.health,
                health=v.health_points,
            )
            for v in sorted(state.victims.values(), key=lambda v: v.id)
        ),
    )
