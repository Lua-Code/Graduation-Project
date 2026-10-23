from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from drsim.shared.enums import (
    CommandSource,
    CommandStatus,
    CommandType,
    ErrorCode,
    IncidentStatus,
    RunStatus,
    UnitStatus,
    VictimStatus,
)

type NonEmptyId = Annotated[str, Field(min_length=1)]
type NonNegativeInt = Annotated[int, Field(ge=0)]
type PositiveInt = Annotated[int, Field(gt=0)]
type NonNegativeFloat = Annotated[float, Field(ge=0)]
type Scalar = str | int | float | bool | None


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class EarthquakeConfig(ContractModel):
    magnitude: float = Field(ge=1.0, le=10.0)
    epicenterX: NonNegativeInt
    epicenterY: NonNegativeInt
    initialDamageScale: float = Field(default=1.0, ge=0.0, le=1.0)


class ScenarioConfig(ContractModel):
    schemaVersion: Literal["1.0"] = "1.0"
    scenarioId: NonEmptyId
    seed: NonNegativeInt
    mapId: NonEmptyId
    tickDurationSeconds: PositiveInt = 1
    maxTicks: PositiveInt = 3600
    earthquake: EarthquakeConfig


class AssignmentPayload(ContractModel):
    unitId: NonEmptyId
    incidentId: NonEmptyId


class UnassignmentPayload(ContractModel):
    unitId: NonEmptyId


type CommandPayload = AssignmentPayload | UnassignmentPayload


class SimulationCommand(ContractModel):
    commandId: NonEmptyId
    runId: NonEmptyId
    source: CommandSource
    type: CommandType
    payload: CommandPayload

    @model_validator(mode="after")
    def validatePayloadMatchesType(self) -> "SimulationCommand":
        assignmentTypes = {
            CommandType.ASSIGN_UNIT,
            CommandType.REASSIGN_UNIT,
        }

        if self.type in assignmentTypes:
            if not isinstance(self.payload, AssignmentPayload):
                raise ValueError(
                    "Assignment and reassignment require unitId and incidentId"
                )

        elif self.type == CommandType.UNASSIGN_UNIT:
            if not isinstance(self.payload, UnassignmentPayload):
                raise ValueError(
                    "Unassignment requires unitId only"
                )

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
                raise ValueError(
                    "Applied commands require appliedAtTick"
                )

            if self.reasonCode is not None:
                raise ValueError(
                    "Applied commands cannot have a rejection reason"
                )

        if self.status in {
            CommandStatus.REJECTED,
            CommandStatus.EXPIRED,
            CommandStatus.FAILED,
        }:
            if self.reasonCode is None:
                raise ValueError(
                    "Rejected, expired and failed commands require reasonCode"
                )

        return self


class UnitSummary(ContractModel):
    unitId: NonEmptyId
    unitType: NonEmptyId
    status: UnitStatus
    x: float
    y: float
    assignedIncidentId: NonEmptyId | None = None


class IncidentSummary(ContractModel):
    incidentId: NonEmptyId
    x: float
    y: float
    status: IncidentStatus
    priority: NonNegativeInt


class VictimSummary(ContractModel):
    victimId: NonEmptyId
    incidentId: NonEmptyId
    status: VictimStatus
    health: float = Field(ge=0.0, le=100.0)


class SimulationEventSummary(ContractModel):
    eventId: NonEmptyId
    tick: NonNegativeInt
    type: NonEmptyId
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