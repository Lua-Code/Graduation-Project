import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from drsim.shared.enums import (
    CommandSource,
    CommandStatus,
    CommandType,
    ErrorCode,
    RecommendationStatus,
)
from drsim.shared.schemas import (
    CommandResult,
    MapDefinition,
    Recommendation,
    ScenarioConfig,
    SimulationCommand,
)
from drsim.simulation.world.loader import (
    ScenarioLoadError,
    load_map,
    load_scenario,
    load_scenario_with_map,
)

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "scenarios"


def roundtrip(model):
    return type(model).model_validate_json(model.model_dump_json())


# ---------- commands ----------

COMMAND_CASES = [
    (CommandType.ASSIGN_UNIT, {"unitId": "u1", "incidentId": "i1"}),
    (CommandType.CANCEL_ASSIGNMENT, {"unitId": "u1"}),
    (CommandType.REROUTE_UNIT, {"unitId": "u1"}),
    (CommandType.APPROVE_RECOMMENDATION, {"recommendationId": "r1"}),
    (CommandType.REJECT_RECOMMENDATION, {"recommendationId": "r1"}),
    (CommandType.PAUSE, {}),
    (CommandType.RESUME, {}),
]


@pytest.mark.parametrize("cmd_type,payload", COMMAND_CASES)
def test_command_roundtrip(cmd_type, payload):
    cmd = SimulationCommand(
        commandId="c1",
        runId="run1",
        source=CommandSource.OPERATOR,
        type=cmd_type,
        payload=payload,
    )
    assert roundtrip(cmd) == cmd


@pytest.mark.parametrize(
    "cmd_type,payload",
    [
        (CommandType.ASSIGN_UNIT, {"unitId": "u1"}),  # missing incident
        (CommandType.CANCEL_ASSIGNMENT, {"unitId": "u1", "incidentId": "i1"}),  # wrong payload
        (CommandType.APPROVE_RECOMMENDATION, {"unitId": "u1"}),
        (CommandType.PAUSE, {"unitId": "u1"}),
    ],
)
def test_command_payload_mismatch_rejected(cmd_type, payload):
    with pytest.raises(ValidationError):
        SimulationCommand(
            commandId="c1",
            runId="run1",
            source=CommandSource.OPERATOR,
            type=cmd_type,
            payload=payload,
        )


def test_command_rejects_empty_ids_and_extra_fields():
    with pytest.raises(ValidationError):
        SimulationCommand(
            commandId="",
            runId="run1",
            source=CommandSource.OPERATOR,
            type=CommandType.PAUSE,
            payload={},
        )
    with pytest.raises(ValidationError):
        SimulationCommand(
            commandId="c1",
            runId="run1",
            source=CommandSource.OPERATOR,
            type=CommandType.PAUSE,
            payload={},
            extra="x",
        )


# ---------- command results ----------


def test_result_applied_requires_tick():
    with pytest.raises(ValidationError):
        CommandResult(commandId="c1", status=CommandStatus.APPLIED)


def test_result_applied_cannot_have_reason():
    with pytest.raises(ValidationError):
        CommandResult(
            commandId="c1",
            status=CommandStatus.APPLIED,
            appliedAtTick=3,
            reasonCode=ErrorCode.UNIT_UNAVAILABLE,
        )


@pytest.mark.parametrize(
    "status",
    [
        CommandStatus.REJECTED,
        CommandStatus.EXPIRED,
        CommandStatus.FAILED,
    ],
)
def test_result_failures_require_reason(status):
    with pytest.raises(ValidationError):
        CommandResult(commandId="c1", status=status)


def test_result_tick_only_when_applied():
    with pytest.raises(ValidationError):
        CommandResult(
            commandId="c1",
            status=CommandStatus.REJECTED,
            appliedAtTick=2,
            reasonCode=ErrorCode.UNIT_UNAVAILABLE,
        )


def test_result_valid_cases_roundtrip():
    applied = CommandResult(commandId="c1", status=CommandStatus.APPLIED, appliedAtTick=5)
    rejected = CommandResult(
        commandId="c2",
        status=CommandStatus.REJECTED,
        reasonCode=ErrorCode.UNIT_UNAVAILABLE,
        reasonMessage="busy",
    )
    assert roundtrip(applied) == applied
    assert roundtrip(rejected) == rejected


# ---------- scenario config ----------


def _scenario(**overrides):
    data = {
        "scenarioId": "s1",
        "seed": 1,
        "mapId": "m1",
        "earthquake": {"magnitude": 6.0, "epicenterX": 10, "epicenterY": 10},
    }
    data.update(overrides)
    return data


def test_scenario_defaults_and_roundtrip():
    s = ScenarioConfig(**_scenario())
    assert s.tickDurationSeconds == 10 and s.maxTicks == 3600
    assert roundtrip(s) == s


@pytest.mark.parametrize(
    "override",
    [
        {"maxTicks": 0},
        {"tickDurationSeconds": 0},
        {"seed": -1},
        {"scenarioId": ""},
        {"unknownField": 1},
        {"earthquake": {"magnitude": 11.0, "epicenterX": 0, "epicenterY": 0}},
        {"earthquake": {"magnitude": 6.0, "epicenterX": -1, "epicenterY": 0}},
        {
            "earthquake": {
                "magnitude": 6.0,
                "epicenterX": 0,
                "epicenterY": 0,
                "initialDamageScale": 1.5,
            }
        },
    ],
)
def test_scenario_invalid(override):
    with pytest.raises(ValidationError):
        ScenarioConfig(**_scenario(**override))


# ---------- map ----------


def _map():
    return {
        "mapId": "m1",
        "widthMeters": 1000,
        "heightMeters": 1000,
        "nodes": [{"nodeId": "a", "x": 0, "y": 0}, {"nodeId": "b", "x": 500, "y": 500}],
        "edges": [
            {
                "edgeId": "e1",
                "sourceNodeId": "a",
                "targetNodeId": "b",
                "lengthMeters": 700,
                "speedMetersPerSecond": 10,
                "state": "open",
            }
        ],
        "facilities": [
            {"facilityId": "h1", "facilityType": "hospital", "nodeId": "b", "capacity": 10}
        ],
        "zones": [
            {
                "zoneId": "z1",
                "name": "Zone 1",
                "polygon": [{"x": 0, "y": 0}, {"x": 0, "y": 100}, {"x": 100, "y": 100}],
            }
        ],
    }


def test_map_valid_roundtrip():
    m = MapDefinition(**_map())
    assert roundtrip(m) == m


def _mutate(fn):
    data = copy.deepcopy(_map())
    fn(data)
    return data


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["nodes"].append({"nodeId": "a", "x": 1, "y": 1}),  # duplicate node
        lambda d: d["edges"].append(copy.deepcopy(d["edges"][0])),  # duplicate edge
        lambda d: d["edges"][0].update(targetNodeId="zzz"),  # unknown node
        lambda d: d["edges"][0].update(targetNodeId="a"),  # self loop
        lambda d: d["edges"][0].update(lengthMeters=0),  # zero length
        lambda d: d["facilities"][0].update(nodeId="zzz"),  # bad facility node
        lambda d: d["nodes"][0].update(x=5000),  # out of bounds
        lambda d: d.update(nodes=d["nodes"][:1]),  # too few nodes
        lambda d: d["facilities"][0].update(capacity=-1),  # negative capacity
    ],
)
def test_map_invalid(mutation):
    with pytest.raises(ValidationError):
        MapDefinition(**_mutate(mutation))


# ---------- recommendation ----------


def _rec(**overrides):
    data = {
        "recommendationId": "r1",
        "runId": "run1",
        "strategyId": "baseline",
        "createdAtTick": 10,
        "assignments": [{"unitId": "u1", "incidentId": "i1"}],
    }
    data.update(overrides)
    return data


def test_recommendation_valid():
    r = Recommendation(**_rec(expiresAtTick=20))
    assert r.status == RecommendationStatus.PENDING
    assert roundtrip(r) == r


@pytest.mark.parametrize(
    "override",
    [
        {"assignments": []},
        {"expiresAtTick": 5},
        {"createdAtTick": -1},
        {"strategyId": ""},
    ],
)
def test_recommendation_invalid(override):
    with pytest.raises(ValidationError):
        Recommendation(**_rec(**override))


# ---------- example files + loader ----------


def test_example_files_load_together():
    scenario, map_def = load_scenario_with_map(
        SCENARIOS / "earthquake_small.json", SCENARIOS / "maps"
    )
    assert scenario.mapId == map_def.mapId
    assert any(f.facilityType.value == "hospital" for f in map_def.facilities)


def test_loader_rejects_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"mapId": "x"}', encoding="utf-8")
    with pytest.raises(ScenarioLoadError):
        load_map(bad)


def test_loader_missing_file():
    with pytest.raises(ScenarioLoadError):
        load_scenario("does_not_exist.json")


def test_loader_rejects_epicenter_outside_map(tmp_path):
    data = (SCENARIOS / "earthquake_small.json").read_text(encoding="utf-8")
    moved = tmp_path / "scenario.json"
    moved.write_text(data.replace('"epicenterX": 1000', '"epicenterX": 99999'), encoding="utf-8")
    with pytest.raises(ScenarioLoadError):
        load_scenario_with_map(moved, SCENARIOS / "maps")
