from pathlib import Path

from pydantic import ValidationError

from drsim.shared.schemas import MapDefinition, ScenarioConfig


class ScenarioLoadError(Exception):
    pass


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScenarioLoadError(f"Cannot read {path}: {exc}") from exc


def load_map(path: str | Path) -> MapDefinition:
    path = Path(path)
    try:
        return MapDefinition.model_validate_json(_read(path))
    except ValidationError as exc:
        raise ScenarioLoadError(f"Invalid map {path}: {exc}") from exc


def load_scenario(path: str | Path) -> ScenarioConfig:
    path = Path(path)
    try:
        return ScenarioConfig.model_validate_json(_read(path))
    except ValidationError as exc:
        raise ScenarioLoadError(f"Invalid scenario {path}: {exc}") from exc


def load_scenario_with_map(scenario_path: str | Path, maps_dir: str | Path) -> tuple[ScenarioConfig, MapDefinition]:
    scenario = load_scenario(scenario_path)
    map_def = load_map(Path(maps_dir) / f"{scenario.mapId.replace('-', '_')}.json")

    if map_def.mapId != scenario.mapId:
        raise ScenarioLoadError(f"Scenario expects map {scenario.mapId}, file contains {map_def.mapId}")

    epicenter_ok = (0 <= scenario.earthquake.epicenterX <= map_def.widthMeters and 0 <= scenario.earthquake.epicenterY <= map_def.heightMeters)
    if not epicenter_ok:
        raise ScenarioLoadError("Earthquake epicenter is outside the map bounds")

    return scenario, map_def