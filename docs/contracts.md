
# Shared Contracts

## Purpose

These contracts define the data exchanged between the simulation engine, API, AI/optimization modules, and frontend.

The goal is to agree on the shape of the data before the team builds modules independently.

## Current Contract Models

### ScenarioConfig

Defines the initial configuration for a simulation scenario.

Key fields:
- `schemaVersion`: version of the scenario format
- `scenarioId`: unique scenario identifier
- `seed`: random seed used for reproducible runs
- `mapId`: identifier of the map used by the scenario
- `tickDurationSeconds`: simulated duration of one tick
- `maxTicks`: maximum number of ticks
- `earthquake`: earthquake-specific configuration

The current MVP uses a synthetic earthquake scenario.

### SimulationCommand

Represents a requested change to a running simulation.

Key fields:
- `commandId`: unique identifier for the command
- `runId`: simulation run receiving the command
- `source`: `operator`, `ai`, or `system`
- `type`: requested operation
- `payload`: data required for that operation

Currently supported command types:
- `assign_unit`
- `unassign_unit`
- `reassign_unit`

Assignment and reassignment require both `unitId` and `incidentId`. Unassignment requires `unitId`.

A valid schema does not guarantee that a command can be executed. The engine must still check the current simulation state, including unit availability and incident status.

### CommandResult

Describes the outcome or current status of a command.

Key fields:
- `commandId`: command being reported
- `status`: command processing status
- `appliedAtTick`: tick where the command was applied, when applicable
- `reasonCode`: machine-readable reason for rejection or failure
- `reasonMessage`: readable explanation

An applied command must include `appliedAtTick`. Rejected, expired, and failed commands must include a reason code.

### SimulationSnapshot

Represents a read-only view of the simulation at a particular tick.

It contains:
- Run ID, tick, simulated time, and run status
- Unit summaries
- Incident summaries
- Victim summaries
- Recent simulation events

The snapshot is intended for consumers such as the frontend and monitoring tools. Consumers should not directly modify the engine's canonical state.

## Shared Rules

- IDs are non-empty strings.
- Tick counts and elapsed simulated time cannot be negative.
- Unit, incident, and victim status values use the shared enums.
- Contract models reject unexpected fields.
- Contract models are immutable after creation.
- Serialized field names use camelCase.
- Schema validation checks data shape; engine validation checks whether an operation is valid in the current simulation state.

## Current Limitations

- The scenario schema currently defines an earthquake configuration only.
- The example coordinates are synthetic map coordinates, not latitude and longitude.
- Victim health is an illustrative simulation value, not a clinical assessment.
- Routing feasibility and resource capability must be checked by the engine; the schemas alone cannot establish them.
- The current contracts do not yet define the complete lifecycle of AI recommendations or approval decisions.

## Decisions to Confirm With the Team

1. Are the command types and command payloads sufficient for the first vertical slice?
2. Should reassignment be a separate command or an assignment operation that replaces an existing assignment?
3. Which unit types, incident types, and capabilities belong in the MVP?
4. Should snapshots contain all entities or support partial/delta updates later?
5. Which fields are mandatory in the first vertical slice, and which can be deferred?
6. What Python version and dependency-management approach will the repository standardize on?

## Contract Change Process

When changing a shared contract:

1. Update the Pydantic model.
2. Update or add a contract test.
3. Update the example JSON files.
4. Update this document.
5. Mention the change in the pull request so dependent modules can adapt.
