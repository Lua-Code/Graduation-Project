from dataclasses import dataclass, field
from enum import IntEnum

from drsim.shared.enums import (
    ErrorCode,
    EventType,
    IncidentType,
    VictimStatus,
)
from drsim.shared.schemas import Scalar


class Severity(IntEnum):
    """Illustrative injury severity. TEAM CONFIRMATION REQUIRED."""

    MINOR = 1
    SERIOUS = 2
    CRITICAL = 3


@dataclass(frozen=True)
class IncidentRules:
    """Versioned, configurable rules. All numbers are illustrative, not clinical.

    TEAM CONFIRMATION REQUIRED for every default below.
    """

    rule_version: str = "1.0"
    # Health points lost per tick, by severity.
    deterioration_per_tick: dict[Severity, float] = field(
        default_factory=lambda: {
            Severity.MINOR: 0.05,
            Severity.SERIOUS: 0.2,
            Severity.CRITICAL: 0.5,
        }
    )
    # Multiplier on deterioration while IN_TRANSIT (patient is being treated).
    transit_deterioration_factor: float = 0.5
    initial_health_by_severity: dict[Severity, float] = field(
        default_factory=lambda: {
            Severity.MINOR: 90.0,
            Severity.SERIOUS: 70.0,
            Severity.CRITICAL: 50.0,
        }
    )
    # Health state thresholds: >= stable_from is STABLE, >= injured_from is INJURED,
    # > 0 is CRITICAL, 0 is DEAD.
    stable_from: float = 70.0
    injured_from: float = 30.0
    # Ticks a rescue unit must spend on scene before the victim is freed.
    rescue_duration_ticks: int = 6


@dataclass(frozen=True)
class Incident:
    """One incident has exactly one victim in the MVP. No stored status (derived)."""

    incident_id: str
    incident_type: IncidentType
    node_id: str  # routing uses the road node; x/y are display-only
    x: float
    y: float
    created_tick: int
    victim_id: str


@dataclass(frozen=True)
class Victim:
    victim_id: str
    incident_id: str
    severity: Severity
    health: float  # 0-100, illustrative
    status: VictimStatus = VictimStatus.TRAPPED
    rescue_progress_ticks: int = 0
    destination_hospital_id: str | None = None


@dataclass(frozen=True)
class DomainEvent:
    """Event produced by a rule. The engine assigns eventId and tick."""

    type: EventType
    entity_id: str
    data: dict[str, Scalar] = field(default_factory=dict)


@dataclass(frozen=True)
class VictimTransition:
    victim: Victim
    events: tuple[DomainEvent, ...] = ()


class InvalidTransitionError(Exception):
    """Raised when a transition is illegal from the victim's current status."""

    code = ErrorCode.INVALID_STATE_TRANSITION

    def __init__(self, victim_id: str, status: VictimStatus, action: str) -> None:
        super().__init__(f"Cannot {action} for victim {victim_id} in status {status.value}")
        self.victim_id = victim_id
        self.status = status
        self.action = action
