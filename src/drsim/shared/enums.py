from enum import StrEnum


class CommandSource(StrEnum):
    OPERATOR = "operator"
    AI = "ai"
    SYSTEM = "system"


class CommandType(StrEnum):
    ASSIGN_UNIT = "assign_unit"
    UNASSIGN_UNIT = "unassign_unit"
    REASSIGN_UNIT = "reassign_unit"


class CommandStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    APPLIED = "applied"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class UnitStatus(StrEnum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    WORKING = "working"
    TRANSPORTING = "transporting"
    OUT_OF_SERVICE = "out_of_service"


class IncidentStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class VictimStatus(StrEnum):
    WAITING_FOR_RESCUE = "waiting_for_rescue"
    BEING_RESCUED = "being_rescued"
    WAITING_FOR_TRANSPORT = "waiting_for_transport"
    BEING_TRANSPORTED = "being_transported"
    AT_HOSPITAL = "at_hospital"
    DECEASED = "deceased"


class ErrorCode(StrEnum):
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    RUN_NOT_ACTIVE = "RUN_NOT_ACTIVE"
    INVALID_COMMAND_TYPE = "INVALID_COMMAND_TYPE"
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