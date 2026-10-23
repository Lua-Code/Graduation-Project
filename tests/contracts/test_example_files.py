import json
from pathlib import Path

from drsim.shared.schemas import (
    CommandResult,
    ScenarioConfig,
    SimulationCommand,
    SimulationSnapshot,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def loadExample(filename: str) -> dict:
    examplePath = EXAMPLES_DIR / filename

    with examplePath.open(encoding="utf-8") as file:
        return json.load(file)


def test_example_scenario_matches_contract():
    scenario = ScenarioConfig.model_validate(
        loadExample("scenario.json")
    )

    assert scenario.scenarioId == "earthquake-demo-01"


def test_example_command_matches_contract():
    command = SimulationCommand.model_validate(
        loadExample("assign_command.json")
    )

    assert command.commandId == "cmd-001"


def test_example_result_matches_contract():
    result = CommandResult.model_validate(
        loadExample("command_result.json")
    )

    assert result.appliedAtTick == 12


def test_example_snapshot_matches_contract():
    snapshot = SimulationSnapshot.model_validate(
        loadExample("snapshot.json")
    )

    assert snapshot.tick == 12
    assert len(snapshot.units) == 1
    assert len(snapshot.incidents) == 1
    assert len(snapshot.victims) == 1
