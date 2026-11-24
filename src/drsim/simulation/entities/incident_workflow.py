from dataclasses import replace

from drsim.shared.enums import EventType, VictimStatus
from drsim.shared.schemas import Scalar
from drsim.simulation.entities.incident_models import (
    DomainEvent,
    IncidentRules,
    InvalidTransitionError,
    Victim,
    VictimTransition,
)
from drsim.simulation.entities.incident_rules import TERMINAL_STATUSES, health_state


def advance_rescue(
    victim: Victim, rescue_unit_on_scene: bool, rules: IncidentRules
) -> VictimTransition:
    """Workflow phase. Counts rescue ticks while a rescue unit is on scene.

    TRAPPED -> AWAITING_TRANSPORT after rules.rescue_duration_ticks. Completing the
    rescue creates a transport request (a separate task assigned via the normal validator).
    Never changes health.
    """
    if victim.status != VictimStatus.TRAPPED:
        raise InvalidTransitionError(victim.victim_id, victim.status, "advance rescue")
    if not rescue_unit_on_scene:
        return VictimTransition(victim)

    progress = victim.rescue_progress_ticks + 1
    if progress < rules.rescue_duration_ticks:
        return VictimTransition(replace(victim, rescue_progress_ticks=progress))

    incident_data: dict[str, Scalar] = {"incidentId": victim.incident_id}
    freed = replace(
        victim,
        status=VictimStatus.AWAITING_TRANSPORT,
        rescue_progress_ticks=progress,
    )
    return VictimTransition(
        freed,
        (
            DomainEvent(EventType.RESCUE_COMPLETED, victim.victim_id, incident_data),
            DomainEvent(EventType.TRANSPORT_REQUESTED, victim.victim_id, incident_data),
        ),
    )


def start_transport(victim: Victim, hospital_id: str) -> VictimTransition:
    """AWAITING_TRANSPORT -> IN_TRANSIT when a transport unit loads the victim."""
    if victim.status != VictimStatus.AWAITING_TRANSPORT:
        raise InvalidTransitionError(victim.victim_id, victim.status, "start transport")
    return VictimTransition(
        replace(victim, status=VictimStatus.IN_TRANSIT, destination_hospital_id=hospital_id)
    )


def complete_transport(victim: Victim) -> VictimTransition:
    """IN_TRANSIT -> AT_HOSPITAL (terminal). Emits exactly one VICTIM_DELIVERED."""
    if victim.status != VictimStatus.IN_TRANSIT:
        raise InvalidTransitionError(victim.victim_id, victim.status, "complete transport")
    return VictimTransition(
        replace(victim, status=VictimStatus.AT_HOSPITAL),
        (
            DomainEvent(
                EventType.VICTIM_DELIVERED,
                victim.victim_id,
                {"hospitalId": victim.destination_hospital_id},
            ),
        ),
    )


def update_health(victim: Victim, rules: IncidentRules) -> VictimTransition:
    """Health phase. The ONLY function that changes health.

    Terminal victims are unchanged, so death and delivery never produce duplicate events.
    """
    if victim.status in TERMINAL_STATUSES:
        return VictimTransition(victim)

    rate = rules.deterioration_per_tick[victim.severity]
    if victim.status == VictimStatus.IN_TRANSIT:
        rate *= rules.transit_deterioration_factor
    new_health = max(0.0, round(victim.health - rate, 6))

    before = health_state(victim.health, rules)
    after = health_state(new_health, rules)

    if new_health <= 0.0:
        dead = replace(victim, health=0.0, status=VictimStatus.DEAD)
        return VictimTransition(
            dead,
            (
                DomainEvent(
                    EventType.VICTIM_DIED, victim.victim_id, {"incidentId": victim.incident_id}
                ),
            ),
        )

    updated = replace(victim, health=new_health)
    if after != before:
        return VictimTransition(
            updated,
            (
                DomainEvent(
                    EventType.VICTIM_HEALTH_CHANGED,
                    victim.victim_id,
                    {"from": before.value, "to": after.value},
                ),
            ),
        )
    return VictimTransition(updated)
