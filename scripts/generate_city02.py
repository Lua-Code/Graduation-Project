"""Generate the synthetic-city-02 map and its earthquake scenario variants.

Run from the repository root:

    python scripts/generate_city02.py

The JSON files in ``scenarios/`` are the source of truth and are committed. This script
documents how they were made and rewrites them identically; edit it instead of
hand-editing the generated files. ``tests/unit/test_scenario_catalog.py`` fails if the
committed files and this script disagree.
"""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "scenarios"
MAPS_DIR = SCENARIOS_DIR / "maps"

MAP_ID = "synthetic-city-02"
GRID = 6  # 6 x 6 nodes
SPACING_METERS = 500
MARGIN_METERS = 250
SIZE_METERS = 2 * MARGIN_METERS + (GRID - 1) * SPACING_METERS  # 3000
ARTERIAL_SPEED = 16.7  # 60 km/h
LOCAL_SPEED = 11.1  # 40 km/h
ARTERIAL_LINES = {1, 4}  # rows (for east-west roads) and columns (north-south roads)


def _node_id(row: int, col: int) -> str:
    return f"n{row}{col}"


def build_map() -> dict[str, Any]:
    nodes = [
        {
            "nodeId": _node_id(r, c),
            "x": MARGIN_METERS + c * SPACING_METERS,
            "y": MARGIN_METERS + r * SPACING_METERS,
        }
        for r in range(GRID)
        for c in range(GRID)
    ]

    edges = []
    for r in range(GRID):
        for c in range(GRID - 1):  # east-west road from (r, c) to (r, c+1)
            speed = ARTERIAL_SPEED if r in ARTERIAL_LINES else LOCAL_SPEED
            edges.append(_edge(f"h{r}{c}", _node_id(r, c), _node_id(r, c + 1), speed))
    for r in range(GRID - 1):
        for c in range(GRID):  # north-south road from (r, c) to (r+1, c)
            speed = ARTERIAL_SPEED if c in ARTERIAL_LINES else LOCAL_SPEED
            edges.append(_edge(f"v{r}{c}", _node_id(r, c), _node_id(r + 1, c), speed))

    half = SIZE_METERS // 2
    return {
        "schemaVersion": "1.0",
        "mapId": MAP_ID,
        "widthMeters": SIZE_METERS,
        "heightMeters": SIZE_METERS,
        "nodes": nodes,
        "edges": edges,
        "facilities": [
            {"facilityId": "h1", "facilityType": "hospital", "nodeId": "n11", "capacity": 40},
            {"facilityId": "h2", "facilityType": "hospital", "nodeId": "n44", "capacity": 40},
            {"facilityId": "fs1", "facilityType": "fire_station", "nodeId": "n00", "capacity": 6},
            {"facilityId": "fs2", "facilityType": "fire_station", "nodeId": "n55", "capacity": 6},
            {"facilityId": "rc1", "facilityType": "rescue_center", "nodeId": "n05", "capacity": 6},
        ],
        "zones": [
            _zone("z1", "North-west district", 0, 0, half, half),
            _zone("z2", "North-east district", half, 0, SIZE_METERS, half),
            _zone("z3", "South-west district", 0, half, half, SIZE_METERS),
            _zone("z4", "South-east district", half, half, SIZE_METERS, SIZE_METERS),
        ],
    }


def _edge(edge_id: str, source: str, target: str, speed: float) -> dict[str, Any]:
    return {
        "edgeId": edge_id,
        "sourceNodeId": source,
        "targetNodeId": target,
        "lengthMeters": SPACING_METERS,
        "speedMetersPerSecond": speed,
        "state": "open",
    }


def _zone(zone_id: str, name: str, x0: int, y0: int, x1: int, y1: int) -> dict[str, Any]:
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return {"zoneId": zone_id, "name": name, "polygon": [{"x": x, "y": y} for x, y in corners]}


# Every variant uses the same units, incidents and seed, so a comparison between two
# variants changes only the earthquake (or the multiplier), nothing else.
SEED = 101

UNITS = [
    ("unit-001", "ambulance", "n11"),
    ("unit-002", "ambulance", "n11"),
    ("unit-003", "ambulance", "n44"),
    ("unit-004", "ambulance", "n44"),
    ("unit-005", "fire", "n00"),
    ("unit-006", "fire", "n55"),
    ("unit-007", "fire", "n00"),
    ("unit-008", "rescue", "n05"),
    ("unit-009", "rescue", "n05"),
    ("unit-010", "rescue", "n55"),
]

# (incidentId, nodeId, priority, victimCount)
INCIDENTS = [
    ("inc-001", "n22", 5, 4),
    ("inc-002", "n23", 4, 3),
    ("inc-003", "n32", 5, 2),
    ("inc-004", "n33", 3, 2),
    ("inc-005", "n13", 2, 1),
    ("inc-006", "n41", 3, 3),
    ("inc-007", "n25", 1, 1),
    ("inc-008", "n50", 4, 2),
]

CENTRE = SIZE_METERS / 2

# file stem -> (scenarioId, magnitude, epicentre x, epicentre y, degraded multiplier)
VARIANTS: dict[str, tuple[str, float, float, float, float | None]] = {
    "earthquake_city02_moderate": ("earthquake-city02-moderate", 5.5, CENTRE, CENTRE, None),
    "earthquake_city02_severe": ("earthquake-city02-severe", 7.5, CENTRE, CENTRE, None),
    "earthquake_city02_offcentre": ("earthquake-city02-offcentre", 7.0, 500, 2500, None),
    "earthquake_city02_severe_slow_roads": (
        "earthquake-city02-severe-slow-roads",
        7.5,
        CENTRE,
        CENTRE,
        3.0,
    ),
}


def build_scenario(
    scenario_id: str, magnitude: float, x: float, y: float, multiplier: float | None
) -> dict[str, Any]:
    scenario: dict[str, Any] = {
        "schemaVersion": "1.0",
        "scenarioId": scenario_id,
        "seed": SEED,
        "mapId": MAP_ID,
        "tickDurationSeconds": 10,
        "maxTicks": 3600,
    }
    if multiplier is not None:
        scenario["degradedTravelMultiplier"] = multiplier
    scenario["earthquake"] = {
        "magnitude": magnitude,
        "epicenterX": x,
        "epicenterY": y,
        "initialDamageScale": 1.0,
    }
    scenario["units"] = [
        {"unitId": uid, "unitType": utype, "nodeId": node} for uid, utype, node in UNITS
    ]
    scenario["incidents"] = [
        {
            "incidentId": iid,
            "incidentType": "building_collapse",
            "nodeId": node,
            "priority": priority,
            "victimCount": victims,
        }
        for iid, node, priority, victims in INCIDENTS
    ]
    return scenario


def _dumps(data: dict[str, Any]) -> str:
    """Indented JSON with each list item (node, edge, unit, ...) on one line."""
    lines = ["{"]
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        if isinstance(value, list):
            lines.append(f"  {json.dumps(key)}: [")
            for j, item in enumerate(value):
                item_comma = "," if j < len(value) - 1 else ""
                lines.append(f"    {json.dumps(item)}{item_comma}")
            lines.append(f"  ]{comma}")
        else:
            lines.append(f"  {json.dumps(key)}: {json.dumps(value)}{comma}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def generated_files() -> dict[Path, str]:
    """Every file this script writes, mapped to its exact contents."""
    files = {MAPS_DIR / "synthetic_city_02.json": _dumps(build_map())}
    for stem, params in VARIANTS.items():
        files[SCENARIOS_DIR / f"{stem}.json"] = _dumps(build_scenario(*params))
    return files


def main() -> None:
    for path, text in generated_files().items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
