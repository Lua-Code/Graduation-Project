import pytest
from pydantic import ValidationError

from drsim.shared.enums import (
    CommandSource,
    CommandStatus,
    CommandType,
    ErrorCode,
)
from drsim.shared.schemas import (
    AssignmentPayload,
    CommandResult,
    SimulationCommand,
    SimulationSnapshot,
)


def test_assignment_command_accepts_matching_payload() -> None:
    command = SimulationCommand(
        commandId="cmd_001",
        runId="run_001",
        source=CommandSource.OPERATOR,
        type=CommandType.ASSIGN_UNIT,
        payload=AssignmentPayload(
            unitId="unit_001",
            incidentId="incident_001",
        ),
    )

    assert command.commandId == "cmd_001"


def test_assignment_command_rejects_unassignment_payload() -> None:
    with pytest.raises(ValidationError):
        SimulationCommand(
            commandId="cmd_002",
            runId="run_001",
            source=CommandSource.OPERATOR,
            type=CommandType.ASSIGN_UNIT,
            payload={"unitId": "unit_001"},
        )


def test_applied_command_requires_tick() -> None:
    with pytest.raises(ValidationError):
        CommandResult(
            commandId="cmd_003",
            status=CommandStatus.APPLIED,
        )


def test_rejected_command_requires_reason() -> None:
    with pytest.raises(ValidationError):
        CommandResult(
            commandId="cmd_004",
            status=CommandStatus.REJECTED,
        )


def test_rejected_command_accepts_stable_error_code() -> None:
    result = CommandResult(
        commandId="cmd_005",
        status=CommandStatus.REJECTED,
        reasonCode=ErrorCode.UNIT_UNAVAILABLE,
        reasonMessage="Unit is not available",
    )

    assert result.reasonCode == ErrorCode.UNIT_UNAVAILABLE


def test_snapshot_serializes_using_contract_field_names() -> None:
    snapshot = SimulationSnapshot(
        runId="run_001",
        tick=0,
        simulationTimeSeconds=0,
        status="created",
    )

    data = snapshot.model_dump(mode="json")

    assert "runId" in data
    assert "simulationTimeSeconds" in data
    assert "run_id" not in data