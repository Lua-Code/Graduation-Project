# ADR-0002: Degraded roads take twice as long

- Status: Accepted
- Date: 2026-11-24
- Deciders: Kevin, Sayed
- PR: road graph, tick travel times and deterministic routing

## Context
`EdgeState` has three values: `open`, `degraded` and `blocked`. Blocked roads are
impassable, but nothing defined how much a degraded road slows a vehicle. Routing,
movement and every allocation strategy need the same answer, or they would estimate
different travel times for the same road.

## Decision
| Topic | Decision |
|---|---|
| Multiplier | By default, a `degraded` edge takes **2×** the travel time of the same edge when `open` |
| Where | Default: `DEFAULT_DEGRADED_TRAVEL_MULTIPLIER = 2.0` in `drsim/shared/schemas.py` |
| Configuration | Each scenario may override it with `ScenarioConfig.degradedTravelMultiplier` (must be > 1 and finite). Routing functions in `drsim/simulation/world/graph.py` take it as the keyword argument `degraded_multiplier` |
| Rounding | Multiply the time in seconds first, then round up to whole ticks (minimum 1), as for any edge (D14) |
| Example | 800 m at 13.9 m/s: open = 57.6 s = 6 ticks; degraded = 115.1 s = 12 ticks |
| Scope | Applies to every caller: engine movement, dispatch reachability and AI travel-time estimates. All callers in one run must pass the scenario's value |

## Options considered
- Treat degraded as open (1×): rejected, since damage would then have no effect short of a full closure.
- A per-edge damage factor: rejected for the MVP; it adds schema fields and damage-rule detail the first slice does not need.
- 1.5× or 3×: no evidence favours one value; 2× is simple to explain and clearly different from open.

## Consequences
- Good: one value per scenario, applied through `edge_travel_ticks`, so all modules agree on travel time.
- Good: the multiplier is a scenario field, so it is recorded with the scenario and can be varied in experiments without code changes.
- Bad: a caller that forgets to pass the scenario's value silently uses the default.
- Good: routes avoid degraded roads when a faster open route exists, which makes damage visible in strategy behaviour.
- Bad: the value is illustrative, not calibrated to real road damage.
- Follow-up: if the evaluation shows strategy rankings are sensitive to the multiplier, test it as a sensitivity parameter like the victim-health rates.
