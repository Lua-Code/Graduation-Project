from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandSource(StrEnum):
    OPERATOR = "operator"
    STRATEGY = "strategy"
    SYSTEM = "system"


class CommandType(StrEnum):
    ASSIGN_UNIT = "assign_unit"
    CANCEL_ASSIGNMENT = "cancel_assignment"
    REROUTE_UNIT = "reroute_unit"
    APPROVE_RECOMMENDATION = "approve_recommendation"
    REJECT_RECOMMENDATION = "reject_recommendation"
    PAUSE = "pause"
    RESUME = "resume"


class CommandStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    APPLIED = "applied"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class UnitType(StrEnum):
    FIRE = "fire"
    AMBULANCE = "ambulance"
    RESCUE = "rescue"


class UnitStatus(StrEnum):
    AVAILABLE = "available"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    TRANSPORTING = "transporting"
    RETURNING = "returning"
    UNAVAILABLE = "unavailable"


class VictimHealth(StrEnum):
    STABLE = "stable"
    INJURED = "injured"
    CRITICAL = "critical"
    DEAD = "dead"


class VictimStatus(StrEnum):
    TRAPPED = "trapped"
    AWAITING_TRANSPORT = "awaiting_transport"
    IN_TRANSIT = "in_transit"
    AT_HOSPITAL = "at_hospital"
    DEAD = "dead"


class IncidentType(StrEnum):
    BUILDING_COLLAPSE = (
        "building_collapse"  # for now only one type of incident, but can be extended in the future
    )


class IncidentStatus(StrEnum):  # derived, never set directly
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    FAILED = "failed"


class RescueTaskStatus(StrEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class EdgeState(StrEnum):
    OPEN = "open"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class FacilityType(StrEnum):
    HOSPITAL = "hospital"
    FIRE_STATION = "fire_station"
    RESCUE_CENTER = "rescue_center"


class RecommendationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ErrorCode(StrEnum):  # DECISION: extend as needed, not covering all, add more as we go
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    RUN_NOT_ACTIVE = "RUN_NOT_ACTIVE"
    DUPLICATE_COMMAND_ID = "DUPLICATE_COMMAND_ID"
    UNIT_NOT_FOUND = "UNIT_NOT_FOUND"
    UNIT_UNAVAILABLE = "UNIT_UNAVAILABLE"
    INCIDENT_NOT_FOUND = "INCIDENT_NOT_FOUND"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    ROUTE_INFEASIBLE = "ROUTE_INFEASIBLE"
    ASSIGNMENT_CONFLICT = "ASSIGNMENT_CONFLICT"
    STALE_RECOMMENDATION = "STALE_RECOMMENDATION"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"


class EventType(StrEnum):
    RUN_CREATED = "run_created"
    RUN_STARTED = "run_started"
    RUN_PAUSED = "run_paused"
    RUN_RESUMED = "run_resumed"
    RECOMMENDATION_CREATED = "recommendation_created"
    RECOMMENDATION_RESOLVED = "recommendation_resolved"
    TICK_ADVANCED = "tick_advanced"
    COMMAND_APPLIED = "command_applied"
    COMMAND_REJECTED = "command_rejected"
    EDGE_STATE_CHANGED = "edge_state_changed"
    INCIDENT_CREATED = "incident_created"
    VICTIM_HEALTH_CHANGED = "victim_health_changed"
    VICTIM_DIED = "victim_died"
    ASSIGNMENT_CHANGED = "assignment_changed"
    UNIT_MOVED = "unit_moved"
    RESCUE_COMPLETED = "rescue_completed"
    TRANSPORT_REQUESTED = "transport_requested"
    VICTIM_DELIVERED = "victim_delivered"
    RUN_ENDED = "run_ended"
