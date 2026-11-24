import pytest

from drsim.shared.enums import (
    ErrorCode,
    EventType,
    IncidentStatus,
    IncidentType,
    VictimHealth,
    VictimStatus,
)
from drsim.simulation.entities.incident_models import (
    Incident,
    IncidentRules,
    InvalidTransitionError,
    Severity,
    Victim,
)
from drsim.simulation.entities.incident_rules import (
    compute_incident_priority,
    compute_priority,
    derive_incident_status,
    health_state,
    initial_health,
    priority_sort_key,
    severity_from_priority,
    to_incident_summary,
    to_victim_summary,
)
from drsim.simulation.entities.incident_workflow import (
    advance_rescue,
    complete_transport,
    start_transport,
    update_health,
)

RULES = IncidentRules(rescue_duration_ticks=3)


def make_victim(severity=Severity.SERIOUS, **kw) -> Victim:
    return Victim(
        victim_id=kw.pop("victim_id", "v1"),
        incident_id=kw.pop("incident_id", "i1"),
        severity=severity,
        health=kw.pop("health", initial_health(severity, RULES)),
        **kw,
    )


def event_types(transition) -> list[EventType]:
    return [e.type for e in transition.events]


# ---------- full lifecycle ----------


def test_full_lifecycle_separate_rescue_and_transport():
    v = make_victim()
    assert v.status == VictimStatus.TRAPPED

    # no unit on scene: nothing progresses
    t = advance_rescue(v, rescue_unit_on_scene=False, rules=RULES)
    assert t.victim.rescue_progress_ticks == 0 and not t.events

    # rescue takes rescue_duration_ticks on scene
    for _ in range(2):
        t = advance_rescue(v, True, RULES)
        v = t.victim
        assert v.status == VictimStatus.TRAPPED and not t.events
    t = advance_rescue(v, True, RULES)
    v = t.victim
    assert v.status == VictimStatus.AWAITING_TRANSPORT
    assert event_types(t) == [EventType.RESCUE_COMPLETED, EventType.TRANSPORT_REQUESTED]

    # transport is a separate stage
    v = start_transport(v, "hospital-1").victim
    assert v.status == VictimStatus.IN_TRANSIT and v.destination_hospital_id == "hospital-1"

    t = complete_transport(v)
    assert t.victim.status == VictimStatus.AT_HOSPITAL
    assert event_types(t) == [EventType.VICTIM_DELIVERED]


# ---------- illegal transitions ----------


@pytest.mark.parametrize(
    "action",
    [
        lambda v: start_transport(v, "h1"),  # still trapped
        lambda v: complete_transport(v),  # not in transit
    ],
)
def test_illegal_transitions_from_trapped(action):
    with pytest.raises(InvalidTransitionError) as exc:
        action(make_victim())
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


def test_cannot_rescue_after_rescued_or_terminal():
    for status in (VictimStatus.AWAITING_TRANSPORT, VictimStatus.AT_HOSPITAL, VictimStatus.DEAD):
        with pytest.raises(InvalidTransitionError):
            advance_rescue(make_victim(status=status), True, RULES)


def test_cannot_deliver_twice():
    v = make_victim(status=VictimStatus.IN_TRANSIT, destination_hospital_id="h1")
    v = complete_transport(v).victim
    with pytest.raises(InvalidTransitionError):
        complete_transport(v)


# ---------- health ----------


def test_health_deteriorates_by_severity_rate():
    v = make_victim(Severity.CRITICAL)
    after = update_health(v, RULES).victim
    assert after.health == pytest.approx(v.health - RULES.deterioration_per_tick[Severity.CRITICAL])


def test_health_deteriorates_slower_in_transit():
    trapped = update_health(make_victim(), RULES).victim
    transit = update_health(make_victim(status=VictimStatus.IN_TRANSIT), RULES).victim
    assert transit.health > trapped.health


def test_workflow_functions_never_change_health():
    v = make_victim()
    assert advance_rescue(v, True, RULES).victim.health == v.health
    freed = make_victim(status=VictimStatus.AWAITING_TRANSPORT)
    assert start_transport(freed, "h1").victim.health == v.health


def test_death_is_terminal_and_emitted_once():
    v = make_victim(Severity.CRITICAL, health=0.3)
    t = update_health(v, RULES)
    assert t.victim.status == VictimStatus.DEAD and t.victim.health == 0.0
    assert event_types(t) == [EventType.VICTIM_DIED]

    again = update_health(t.victim, RULES)
    assert again.victim == t.victim and not again.events


def test_delivered_victim_no_longer_deteriorates():
    v = make_victim(status=VictimStatus.AT_HOSPITAL)
    t = update_health(v, RULES)
    assert t.victim == v and not t.events


def test_health_state_change_emits_event():
    v = make_victim(Severity.CRITICAL, health=70.2)  # STABLE, drops below 70 next tick
    t = update_health(v, RULES)
    assert event_types(t) == [EventType.VICTIM_HEALTH_CHANGED]
    assert t.events[0].data == {"from": "stable", "to": "injured"}


def test_health_state_thresholds():
    assert health_state(100, RULES) == VictimHealth.STABLE
    assert health_state(70, RULES) == VictimHealth.STABLE
    assert health_state(69.9, RULES) == VictimHealth.INJURED
    assert health_state(30, RULES) == VictimHealth.INJURED
    assert health_state(29.9, RULES) == VictimHealth.CRITICAL
    assert health_state(0, RULES) == VictimHealth.DEAD


# ---------- priority and derived status ----------


def test_priority_range_and_terminal_zero():
    best = compute_priority(make_victim(Severity.CRITICAL, health=10), RULES)
    worst = compute_priority(make_victim(Severity.MINOR, health=100), RULES)
    assert (worst, best) == (1, 5)
    assert compute_priority(make_victim(status=VictimStatus.AT_HOSPITAL), RULES) == 0
    assert compute_priority(make_victim(status=VictimStatus.DEAD), RULES) == 0


def test_priority_tie_break_is_stable():
    items = [(3, 5, "b"), (3, 5, "a"), (3, 2, "z"), (5, 9, "y")]
    ordered = sorted(items, key=lambda i: priority_sort_key(*i))
    assert ordered == [(5, 9, "y"), (3, 2, "z"), (3, 5, "a"), (3, 5, "b")]


def test_severity_from_priority_mapping():
    assert severity_from_priority(5) == Severity.CRITICAL
    assert severity_from_priority(4) == Severity.SERIOUS
    assert severity_from_priority(3) == Severity.SERIOUS
    assert severity_from_priority(2) == Severity.MINOR
    assert severity_from_priority(1) == Severity.MINOR


def test_derived_incident_status():
    v = make_victim()
    assert derive_incident_status([v], False) == IncidentStatus.OPEN
    assert derive_incident_status([v], True) == IncidentStatus.IN_PROGRESS
    in_transit = make_victim(status=VictimStatus.IN_TRANSIT)
    assert derive_incident_status([in_transit], False) == IncidentStatus.IN_PROGRESS
    delivered = make_victim(status=VictimStatus.AT_HOSPITAL)
    assert derive_incident_status([delivered], True) == IncidentStatus.RESOLVED
    dead = make_victim(status=VictimStatus.DEAD)
    assert derive_incident_status([dead], True) == IncidentStatus.FAILED


def test_incident_with_multiple_victims_derives_status_and_priority():
    a = make_victim(Severity.MINOR, victim_id="a")
    b = make_victim(Severity.CRITICAL, victim_id="b", health=10)
    assert derive_incident_status([a, b], False) == IncidentStatus.OPEN
    assert compute_incident_priority([a, b], RULES) == 5

    delivered = make_victim(victim_id="a", status=VictimStatus.AT_HOSPITAL)
    assert derive_incident_status([delivered, b], False) == IncidentStatus.OPEN

    dead = make_victim(victim_id="b", status=VictimStatus.DEAD)
    assert derive_incident_status([delivered, dead], False) == IncidentStatus.FAILED

    delivered_b = make_victim(victim_id="b", status=VictimStatus.AT_HOSPITAL)
    assert derive_incident_status([delivered, delivered_b], False) == IncidentStatus.RESOLVED
    assert compute_incident_priority([delivered, delivered_b], RULES) == 0


def test_incident_without_victims_is_rejected():
    with pytest.raises(ValueError):
        Incident("i1", IncidentType.BUILDING_COLLAPSE, "n1", 0, ())
    with pytest.raises(ValueError):
        derive_incident_status([], False)


# ---------- contract mapping ----------


def test_summaries_validate_against_shared_contracts():
    incident = Incident("i1", IncidentType.BUILDING_COLLAPSE, "n1", 0, ("v1",))
    v = make_victim()
    vs = to_victim_summary(v, RULES)
    inc = to_incident_summary(incident, [v], 10.0, 12.0, False, RULES)
    assert vs.status == VictimStatus.TRAPPED and vs.healthState == VictimHealth.STABLE
    assert inc.status == IncidentStatus.OPEN and inc.priority == compute_priority(v, RULES)
    assert (inc.x, inc.y) == (10.0, 12.0)


# ---------- determinism ----------


def run_to_end() -> list:
    v = make_victim(Severity.CRITICAL)
    trace = []
    for _ in range(3):
        v = advance_rescue(v, True, RULES).victim
        v = update_health(v, RULES).victim
        trace.append(v)
    v = start_transport(v, "h1").victim
    for _ in range(4):
        v = update_health(v, RULES).victim
        trace.append(v)
    trace.append(complete_transport(v).victim)
    return trace


def test_same_input_same_trace():
    assert run_to_end() == run_to_end()
