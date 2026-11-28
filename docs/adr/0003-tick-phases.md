# ADR-0003: Tick phase order and tick-0 semantics

- Status: Proposed
- Date: 2026-11-28
- Deciders: Kevin, Sayed
- Relates to: KAN-15, integration guide §6, ScenarioConfig `scheduledEvents`

## Context
The integration guide §6 defines a 10-step tick. The engine needs one fixed,
deterministic order, and a rule for which tick the first step processes.
Road damage is generated once at scenario load and stored as scheduled events.

## Decision
1. One simulated tick is 10 s. Simulated time = `tick * 10`.
2. `step(state)` runs the phases below against `state.tick`, then increments
   `state.tick`. The first call processes tick 0, so a snapshot taken before
   the first step shows the intact map.
3. Phase order (guide steps in brackets):
   1. `load_scheduled_events` [1-2]: apply events with `tick == state.tick`,
      in `(tick, orderKey)` order
   2. `apply_operator_commands` [3]
   3. `apply_automated_commands` [4]
   4. `apply_hazards` [5]
   5. `update_movement` [6]
   6. `update_workflows` [7]
   7. `update_victim_health` [8]
   8. `check_end_condition` [9]
   Guide step 10 (publish snapshot) happens outside the tick.
4. Ownership rule:
   - Events materialized at scenario load, including road damage, belong to
     `load_scheduled_events`. They use no RNG at tick time.
   - `apply_hazards` is for effects computed from live state during the run.
     It is an empty placeholder in the MVP.
5. Scheduled events run before commands, so commands see the post-event world.
6. No wall-clock time is used anywhere in the engine.

## Consequences
- One code path for all scheduled events, ordered by `(tick, orderKey)`.
- Off-by-one: after step N, `state.tick == N` but tick N-1 was processed.
  Event ticks are validated `< maxTicks`, so every event is processed.
- Road damage docs must say "applied in the scheduled-events phase", not
  "tick phase 5".
- `load_scheduled_events` stays a placeholder until the loader materializes
  the schedule (B2).
- Replay of commands is untested until `commands/` exists.

## Alternatives considered
- Apply tick-0 damage at initialization: two paths for the same events, and
  tick-0 events bypass the ordering rule. Rejected.
- Road damage in `apply_hazards`: it is pre-generated, so it behaves as a
  scheduled event. Rejected.