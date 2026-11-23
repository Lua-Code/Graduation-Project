from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# PLEASE LEARN ABOUT PYDANTIC: https://docs.pydantic.dev/latest/usage/models/
from drsim.shared.enums import (
    CommandSource,
    CommandStatus,
    CommandType,
    EdgeState,
    ErrorCode,
    EventType,
    FacilityType,
    IncidentStatus,
    IncidentType,
    RecommendationStatus,
    RunStatus,
    UnitStatus,
    UnitType,
    VictimHealth,
    VictimStatus,
)

type NonEmptyId = Annotated[str, Field(min_length=1)]
type NonNegativeInt = Annotated[int, Field(ge=0)]
type PositiveInt = Annotated[int, Field(gt=0)]
type NonNegativeFloat = Annotated[float, Field(ge=0)]
type Scalar = str | int | float | bool | None


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------- scenario ----------


class UnitSpec(ContractModel):
    unitId: NonEmptyId
    unitType: UnitType
    nodeId: NonEmptyId


class IncidentSpec(ContractModel):
    incidentId: NonEmptyId
    incidentType: IncidentType
    nodeId: NonEmptyId
    priority: int = Field(ge=1, le=5)
    victimCount: PositiveInt


class EarthquakeConfig(ContractModel):
    magnitude: float = Field(ge=1.0, le=10.0)
    epicenterX: NonNegativeFloat
    epicenterY: NonNegativeFloat
    initialDamageScale: float = Field(default=1.0, ge=0.0, le=1.0)


class ScenarioConfig(ContractModel):
    schemaVersion: Literal["1.0"] = "1.0"
    scenarioId: NonEmptyId
    seed: NonNegativeInt
    mapId: NonEmptyId
    tickDurationSeconds: PositiveInt = 10
    maxTicks: PositiveInt = 3600
    earthquake: EarthquakeConfig
    units: tuple[UnitSpec, ...] = Field(min_length=1)
    incidents: tuple[IncidentSpec, ...] = Field(min_length=1)


# ---------- command payloads ----------


class AssignmentPayload(ContractModel):  # ASSIGN_UNIT
    unitId: NonEmptyId
    incidentId: NonEmptyId


class UnitPayload(ContractModel):  # CANCEL_ASSIGNMENT, REROUTE_UNIT
    unitId: NonEmptyId


class RecommendationPayload(ContractModel):  # APPROVE / REJECT_RECOMMENDATION
    recommendationId: NonEmptyId


class EmptyPayload(ContractModel):  # PAUSE, RESUME
    pass


type CommandPayload = AssignmentPayload | UnitPayload | RecommendationPayload | EmptyPayload

PAYLOAD_BY_COMMAND_TYPE: dict[CommandType, type[ContractModel]] = {
    CommandType.ASSIGN_UNIT: AssignmentPayload,
    CommandType.CANCEL_ASSIGNMENT: UnitPayload,
    CommandType.REROUTE_UNIT: UnitPayload,
    CommandType.APPROVE_RECOMMENDATION: RecommendationPayload,
    CommandType.REJECT_RECOMMENDATION: RecommendationPayload,
    CommandType.PAUSE: EmptyPayload,
    CommandType.RESUME: EmptyPayload,
}


class SimulationCommand(ContractModel):
    commandId: NonEmptyId
    runId: NonEmptyId
    source: CommandSource
    type: CommandType
    payload: CommandPayload

    @model_validator(mode="after")
    def validatePayloadMatchesType(self) -> "SimulationCommand":
        expected = PAYLOAD_BY_COMMAND_TYPE[self.type]
        if type(self.payload) is not expected:
            raise ValueError(f"{self.type.value} requires {expected.__name__}")
        return self


class CommandResult(ContractModel):
    commandId: NonEmptyId
    status: CommandStatus
    appliedAtTick: NonNegativeInt | None = None
    reasonCode: ErrorCode | None = None
    reasonMessage: str | None = None

    @model_validator(mode="after")
    def validateResultFields(self) -> "CommandResult":
        if self.status == CommandStatus.APPLIED:
            if self.appliedAtTick is None:
                raise ValueError("Applied commands require appliedAtTick")
            if self.reasonCode is not None:
                raise ValueError("Applied commands cannot have a reasonCode")
        else:
            if self.appliedAtTick is not None:
                raise ValueError("Only applied commands can have appliedAtTick")

        if (
            self.status
            in {
                CommandStatus.REJECTED,
                CommandStatus.EXPIRED,
                CommandStatus.FAILED,
            }
            and self.reasonCode is None
        ):
            raise ValueError("Rejected, expired and failed commands require reasonCode")

        return self


# ---------- recommendation ----------
class RecommendedAssignment(ContractModel):
    unitId: NonEmptyId
    incidentId: NonEmptyId
    estimatedArrivalTicks: NonNegativeFloat | None = None
    score: float | None = None


class Recommendation(ContractModel):
    SchemaVersion: Literal["1.0"] = "1.0"
    recommendationId: NonEmptyId
    runId: NonEmptyId
    strategyId: NonEmptyId
    createdAtTick: NonNegativeInt
    expiresAtTick: NonNegativeInt | None = None
    status: RecommendationStatus = RecommendationStatus.PENDING
    assignments: tuple[RecommendedAssignment, ...] = Field(min_length=1)
    rationale: str | None = None

    @model_validator(mode="after")
    def validateExpiry(self) -> "Recommendation":
        if self.expiresAtTick is not None and self.expiresAtTick <= self.createdAtTick:
            raise ValueError("expiresAtTick must be greater than createdAtTick")
        return self


# ---------- snapshot ----------


class UnitSummary(ContractModel):
    unitId: NonEmptyId
    unitType: UnitType
    status: UnitStatus
    x: float
    y: float
    assignedIncidentId: NonEmptyId | None = None


class IncidentSummary(ContractModel):
    incidentId: NonEmptyId
    incidentType: IncidentType
    x: float
    y: float
    status: IncidentStatus
    priority: NonNegativeInt


class VictimSummary(ContractModel):
    victimId: NonEmptyId
    incidentId: NonEmptyId
    status: VictimStatus
    healthState: VictimHealth
    health: float = Field(ge=0.0, le=100.0)


class SimulationEventSummary(ContractModel):
    eventId: NonEmptyId
    tick: NonNegativeInt
    type: EventType
    entityId: NonEmptyId | None = None
    data: dict[str, Scalar] = Field(default_factory=dict)


class SimulationSnapshot(ContractModel):
    schemaVersion: Literal["1.0"] = "1.0"
    runId: NonEmptyId
    tick: NonNegativeInt
    simulationTimeSeconds: NonNegativeFloat
    status: RunStatus
    units: tuple[UnitSummary, ...] = ()
    incidents: tuple[IncidentSummary, ...] = ()
    victims: tuple[VictimSummary, ...] = ()
    recentEvents: tuple[SimulationEventSummary, ...] = ()
    pendingRecommendations: tuple[Recommendation, ...] = ()


# ---------- map (static) ----------
class Point(ContractModel):
    x: float
    y: float


class MapNode(ContractModel):
    nodeId: NonEmptyId
    x: float
    y: float


class MapEdge(ContractModel):
    edgeId: NonEmptyId
    sourceNodeId: NonEmptyId
    targetNodeId: NonEmptyId
    lengthMeters: float = Field(gt=0.0)
    speedMetersPerSecond: float = Field(gt=0.0)
    bidirectional: bool = True
    state: EdgeState

    @model_validator(mode="after")
    def validateEndPoints(self) -> "MapEdge":
        if self.sourceNodeId == self.targetNodeId:
            raise ValueError("sourceNodeId and targetNodeId cannot be the same")
        return self


class MapFacility(ContractModel):
    facilityId: NonEmptyId
    facilityType: FacilityType
    nodeId: NonEmptyId
    capacity: NonNegativeInt


class MapZone(ContractModel):
    zoneId: NonEmptyId
    name: str
    polygon: tuple[Point, ...] = Field(min_length=3)


def _requireUnique(ids: list[str], label: str) -> None:
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label} must be unique, but duplicates were found")


class MapDefinition(ContractModel):
    schemaVersion: Literal["1.0"] = "1.0"
    mapId: NonEmptyId
    widthMeters: float = Field(gt=0.0)
    heightMeters: float = Field(gt=0.0)
    nodes: tuple[MapNode, ...] = Field(min_length=2)
    edges: tuple[MapEdge, ...] = Field(min_length=1)
    facilities: tuple[MapFacility, ...] = ()
    zones: tuple[MapZone, ...] = ()

    @model_validator(mode="after")
    def validateReferences(self) -> "MapDefinition":
        _requireUnique([n.nodeId for n in self.nodes], "nodeId")
        _requireUnique([e.edgeId for e in self.edges], "edgeId")
        _requireUnique([f.facilityId for f in self.facilities], "facilityId")
        _requireUnique([z.zoneId for z in self.zones], "zoneId")

        nodeIds = {n.nodeId for n in self.nodes}

        for n in self.nodes:
            if not (0 <= n.x <= self.widthMeters and 0 <= n.y <= self.heightMeters):
                raise ValueError(f"Node {n.nodeId} is outside map bounds")

        for e in self.edges:
            if e.sourceNodeId not in nodeIds or e.targetNodeId not in nodeIds:
                raise ValueError(f"Edge {e.edgeId} references an unknown node")

        for f in self.facilities:
            if f.nodeId not in nodeIds:
                raise ValueError(f"Facility {f.facilityId} references an unknown node")

        return self
