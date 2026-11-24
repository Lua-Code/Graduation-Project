"""Seeded earthquake road damage, materialised into a fixed schedule (Module B).

ILLUSTRATIVE RULE, NOT PHYSICS. These parameters are not calibrated to real
earthquakes. They exist to produce controlled, repeatable road closures for comparing
dispatch strategies.

How it works (rule version ``RULE_VERSION``):

1. Affected radius = ``radius_meters_per_magnitude * (magnitude - min_damaging_magnitude)``.
   Below ``min_damaging_magnitude`` no road is damaged.
2. For each edge, ``closeness = 1 - distance / radius`` (0 outside the radius), where
   distance is the shortest distance from the epicentre to the road segment.
3. Damage probability = ``initialDamageScale * closeness``. One uniform draw ``u``
   decides the tick-0 outcome:
   ``u < p * blocked_share`` -> BLOCKED, otherwise ``u < p`` -> DEGRADED, else no damage.
4. A road that is DEGRADED at tick 0 may collapse to BLOCKED later, with probability
   ``secondary_collapse_probability``, at a tick drawn uniformly from
   ``[secondary_collapse_min_tick, secondary_collapse_max_tick]``.

Determinism (D3, D8):

* All randomness happens once, when the schedule is generated. Ticks only read it.
* The generator uses its own RNG derived from the scenario seed and a fixed label, so
  adding victims or other random draws elsewhere never changes road damage.
* Edges are processed in sorted edge-ID order and every edge consumes exactly three
  draws, whatever its outcome. Changing one edge's outcome never shifts another's draws.
* Damage only ever worsens a road (OPEN < DEGRADED < BLOCKED); it never repairs one.

The engine owns ``SimulationState.edge_states``. ``road_changes_at`` only returns the
changes due at a tick; the engine applies them in the hazard phase (tick phase 5) and
records an ``EDGE_STATE_CHANGED`` event for each one.
"""

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from drsim.shared.enums import EdgeState
from drsim.shared.schemas import MapDefinition, MapEdge, ScenarioConfig

RULE_VERSION = "road-damage-1.0"

_RNG_LABEL = "road-damage"

_SEVERITY = {EdgeState.OPEN: 0, EdgeState.DEGRADED: 1, EdgeState.BLOCKED: 2}


class DamageCause(StrEnum):
    INITIAL_DAMAGE = "initial_damage"
    SECONDARY_COLLAPSE = "secondary_collapse"


@dataclass(frozen=True)
class RoadDamageRule:
    """Configurable parameters for the illustrative road-damage rule.

    Defaults are PROVISIONAL and need team confirmation. Record the rule with every
    experiment so results stay interpretable.
    """

    version: str = RULE_VERSION
    min_damaging_magnitude: float = 4.0
    radius_meters_per_magnitude: float = 300.0
    blocked_share: float = 0.4
    secondary_collapse_probability: float = 0.25
    secondary_collapse_min_tick: int = 30  # 5 minutes at 10 s per tick
    secondary_collapse_max_tick: int = 180  # 30 minutes at 10 s per tick

    def __post_init__(self) -> None:
        if self.radius_meters_per_magnitude <= 0:
            raise ValueError("radius_meters_per_magnitude must be positive")
        for name in ("blocked_share", "secondary_collapse_probability"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if not 1 <= self.secondary_collapse_min_tick <= self.secondary_collapse_max_tick:
            raise ValueError("secondary collapse ticks must satisfy 1 <= min_tick <= max_tick")

    def affected_radius_meters(self, magnitude: float) -> float:
        return max(0.0, magnitude - self.min_damaging_magnitude) * self.radius_meters_per_magnitude


DEFAULT_RULE = RoadDamageRule()


@dataclass(frozen=True, order=True)
class RoadDamageEvent:
    """One scheduled change: at ``tick``, ``edge_id`` becomes ``new_state``."""

    tick: int
    edge_id: str
    new_state: EdgeState
    cause: DamageCause


@dataclass(frozen=True)
class RoadDamageSchedule:
    """All road damage for one run, sorted by (tick, edge_id)."""

    rule_version: str
    events: tuple[RoadDamageEvent, ...]

    def events_at(self, tick: int) -> tuple[RoadDamageEvent, ...]:
        return tuple(e for e in self.events if e.tick == tick)


@dataclass(frozen=True)
class EdgeStateChange:
    """A change the engine should apply to ``SimulationState.edge_states``."""

    edge_id: str
    old_state: EdgeState
    new_state: EdgeState
    cause: DamageCause


def _distance_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def edge_closeness(
    edge: MapEdge,
    node_pos: Mapping[str, tuple[float, float]],
    epicenter: tuple[float, float],
    radius_meters: float,
) -> float:
    """1.0 at the epicentre, falling linearly to 0.0 at ``radius_meters`` and beyond."""
    if radius_meters <= 0:
        return 0.0
    ax, ay = node_pos[edge.sourceNodeId]
    bx, by = node_pos[edge.targetNodeId]
    distance = _distance_to_segment(*epicenter, ax, ay, bx, by)
    return max(0.0, 1.0 - distance / radius_meters)


def _worse(a: EdgeState, b: EdgeState) -> bool:
    return _SEVERITY[a] > _SEVERITY[b]


def generate_road_damage_schedule(
    scenario: ScenarioConfig,
    map_def: MapDefinition,
    rule: RoadDamageRule = DEFAULT_RULE,
) -> RoadDamageSchedule:
    """Materialise the scenario's earthquake road damage into a fixed schedule.

    Call once when the scenario is loaded. The same scenario, map and rule always
    produce the same schedule.
    """
    quake = scenario.earthquake
    radius = rule.affected_radius_meters(quake.magnitude)
    epicenter = (quake.epicenterX, quake.epicenterY)
    node_pos = {n.nodeId: (n.x, n.y) for n in map_def.nodes}

    # String seeds are hashed with SHA-512 by ``random``, so this does not depend on
    # PYTHONHASHSEED.
    rng = random.Random(f"{scenario.seed}:{_RNG_LABEL}")

    events: list[RoadDamageEvent] = []
    for edge in sorted(map_def.edges, key=lambda e: e.edgeId):
        # Always draw three values so every edge uses the same slice of the stream.
        u_damage = rng.random()
        u_collapse = rng.random()
        collapse_tick = rng.randint(
            rule.secondary_collapse_min_tick, rule.secondary_collapse_max_tick
        )

        p = quake.initialDamageScale * edge_closeness(edge, node_pos, epicenter, radius)
        if u_damage < p * rule.blocked_share:
            drawn = EdgeState.BLOCKED
        elif u_damage < p:
            drawn = EdgeState.DEGRADED
        else:
            continue

        state_after_tick0 = edge.state
        if _worse(drawn, edge.state):
            events.append(RoadDamageEvent(0, edge.edgeId, drawn, DamageCause.INITIAL_DAMAGE))
            state_after_tick0 = drawn

        if (
            state_after_tick0 is EdgeState.DEGRADED
            and u_collapse < rule.secondary_collapse_probability
        ):
            events.append(
                RoadDamageEvent(
                    collapse_tick,
                    edge.edgeId,
                    EdgeState.BLOCKED,
                    DamageCause.SECONDARY_COLLAPSE,
                )
            )

    return RoadDamageSchedule(rule_version=rule.version, events=tuple(sorted(events)))


def road_changes_at(
    schedule: RoadDamageSchedule,
    edge_states: Mapping[str, EdgeState],
    tick: int,
) -> tuple[EdgeStateChange, ...]:
    """Changes due at ``tick`` for the hazard phase, in stable edge-ID order.

    Pure: does not modify ``edge_states``. An event that would not worsen the road's
    current state is skipped, so damage never repairs a road.
    """
    changes: list[EdgeStateChange] = []
    for event in schedule.events_at(tick):
        current = edge_states[event.edge_id]
        if _worse(event.new_state, current):
            changes.append(EdgeStateChange(event.edge_id, current, event.new_state, event.cause))
    return tuple(changes)
