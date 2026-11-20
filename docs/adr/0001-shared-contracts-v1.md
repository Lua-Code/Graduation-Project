# ADR-0001: Shared contracts v1

- Status: Accepted
- Date: 2026-11-20
- Deciders: Kevin
- Jira: KAN-1

## Context
Every module imports the shared enums and schemas. Changes after the
22 Nov checkpoint would break the whole team, so the contract is frozen early.

## Decision
| Topic | Decision |
|---|---|
| Location | `drsim/shared/enums.py`, `drsim/shared/schemas.py`; `shared` imports no other drsim module |
| Coordinates | metres, origin top-left, y increases downward |
| IDs | non-empty strings, generated deterministically by the engine |
| Priority | int 1 to 5, higher = more urgent |
| Tick | `tickDurationSeconds` default 10, `maxTicks` default 3600 |
| Command timing | validated, queued, applied at the next tick boundary |
| Terminal condition | all incidents resolved or failed, or `maxTicks` reached |
| Victim death | `VictimHealth.DEAD` is the only death value; `VictimStatus.DEAD` mirrors it |
| Enum values | snake_case strings (`StrEnum`); `ErrorCode` values are UPPER_SNAKE |
| Field naming | camelCase in contract models, matching the OpenAPI and TypeScript output |
| Immutability | all contract models are frozen and reject extra fields |
| Versioning | `schemaVersion: "1.0"` on config, map, snapshot, recommendation |
| Changes | enum or schema changes go through a PR reviewed by the epic owners |

## Options considered
- Integer IDs: rejected, since they are harder to keep deterministic across runs.
- Immediate command application: rejected, since it breaks tick determinism.
- snake_case fields: rejected, since the frontend would need a conversion layer.

## Consequences
- Good: one source of truth, and TypeScript types can be generated from it.
- Bad: camelCase fields look unidiomatic in Python.
- Follow-up: contract tests (below) guard against accidental breakage.