from drsim.shared.enums import IncidentStatus, VictimHealth, VictimStatus
from drsim.shared.schemas import IncidentSummary, VictimSummary
from drsim.simulation.entities.incident_models import (
    Incident,
    IncidentRules,
    Severity,
    Victim,
)

TERMINAL_STATUSES = frozenset({VictimStatus.AT_HOSPITAL, VictimStatus.DEAD})

_URGENCY_BUMP = {
    VictimHealth.STABLE: 0,
    VictimHealth.INJURED: 1,
    VictimHealth.CRITICAL: 2,
}


def initial_health(severity: Severity, rules: IncidentRules) -> float:
    return rules.initial_health_by_severity[severity]


def health_state(health: float, rules: IncidentRules) -> VictimHealth:
    if health <= 0:
        return VictimHealth.DEAD
    if health >= rules.stable_from:
        return VictimHealth.STABLE
    if health >= rules.injured_from:
        return VictimHealth.INJURED
    return VictimHealth.CRITICAL


def compute_priority(victim: Victim, rules: IncidentRules) -> int:
    """Priority 1-5 (higher = more urgent); 0 when nothing is actionable.

    Simulator rule, not medical advice: severity (1-3) + urgency bump from health (0-2).
    """
    if victim.status in TERMINAL_STATUSES:
        return 0
    return int(victim.severity) + _URGENCY_BUMP[health_state(victim.health, rules)]


def priority_sort_key(priority: int, created_tick: int, incident_id: str) -> tuple[int, int, str]:
    """Sort ascending: higher priority first, then earlier creation, then smaller ID."""
    return (-priority, created_tick, incident_id)


def derive_incident_status(victim: Victim, has_active_assignment: bool) -> IncidentStatus:
    """Incident status is never stored; it is derived from the victim and assignments."""
    if victim.status == VictimStatus.AT_HOSPITAL:
        return IncidentStatus.RESOLVED
    if victim.status == VictimStatus.DEAD:
        return IncidentStatus.FAILED
    if has_active_assignment or victim.rescue_progress_ticks > 0 or (
        victim.status == VictimStatus.IN_TRANSIT
    ):
        return IncidentStatus.IN_PROGRESS
    return IncidentStatus.OPEN


def to_victim_summary(victim: Victim, rules: IncidentRules) -> VictimSummary:
    return VictimSummary(
        victimId=victim.victim_id,
        incidentId=victim.incident_id,
        status=victim.status,
        healthState=health_state(victim.health, rules),
        health=victim.health,
    )


def to_incident_summary(
    incident: Incident,
    victim: Victim,
    has_active_assignment: bool,
    rules: IncidentRules,
) -> IncidentSummary:
    return IncidentSummary(
        incidentId=incident.incident_id,
        incidentType=incident.incident_type,
        x=incident.x,
        y=incident.y,
        status=derive_incident_status(victim, has_active_assignment),
        priority=compute_priority(victim, rules),
    )
