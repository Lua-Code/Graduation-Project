from collections.abc import Sequence

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


# Modification #1: helper function to convert priority(int) to severity(Severity)
def severity_from_priority(priority: int) -> Severity:
    if priority >= 5:
        return Severity.CRITICAL
    return Severity.SERIOUS if priority >= 3 else Severity.MINOR


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


# Modification #2: Adapted to use Sequence of victims instead of a victim
def derive_incident_status(
    victims: Sequence[Victim], has_active_assignment: bool
) -> IncidentStatus:
    if not victims:
        raise ValueError("Incident must have at least one victim")
    if all(v.status in TERMINAL_STATUSES for v in victims):
        if any(v.status == VictimStatus.DEAD for v in victims):
            return IncidentStatus.FAILED
        return IncidentStatus.RESOLVED
    if has_active_assignment or any(
        v.rescue_progress_ticks > 0 or v.status == VictimStatus.IN_TRANSIT for v in victims
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


# Modificaiton 3: Uses sequence of victims and the incident rules to return an incident priority
def compute_incident_priority(victims: Sequence[Victim], rules: IncidentRules) -> int:
    return max(compute_priority(v, rules) for v in victims)


# Modifcaiton 4: again just adapted to use Sequence of victims
def to_incident_summary(
    incident: Incident,
    victims: Sequence[Victim],
    x: float,
    y: float,
    has_active_assignment: bool,
    rules: IncidentRules,
) -> IncidentSummary:
    return IncidentSummary(
        incidentId=incident.incident_id,
        incidentType=incident.incident_type,
        x=x,
        y=y,
        status=derive_incident_status(victims, has_active_assignment),
        priority=compute_incident_priority(victims, rules),
    )
