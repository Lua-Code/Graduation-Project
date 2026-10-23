# Disaster Response Simulator

A browser-based, 2D disaster-response simulator focused on a reproducible earthquake-response scenario and human-in-the-loop decision support.

## Project status

**Stage:** Repository foundation. The simulation engine and application services have not been implemented yet.

## Technology direction

- **Simulation and decision logic:** Python, packaged under `src/drsim/`
- **Frontend:** React, TypeScript, and Phaser (in `frontend/`)
- **API/integration:** FastAPI is the planned backend framework
- **Optimization:** OR-Tools is the planned optimization library
- **Development:** GitHub Actions, pytest, Ruff, mypy, and import-linter

These are project directions, not claims that the corresponding features already exist.

## Setup

Use Python 3.12. From the repository root, create and activate a virtual environment.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the package import:

```bash
python -c "import drsim.simulation; print('Import OK')"
```

## Checks

Run the commands from the repository root:

```bash
python -m pytest
ruff check .
mypy src
lint-imports
```

If you have GNU Make installed, shortcuts are available:

```bash
make test
make lint
make typecheck
make imports
make check
```

`make up` is intentionally a placeholder until the backend and frontend services are runnable. On Windows, you can run the individual Python commands above without installing Make.

## Architecture and dependency rules

The Python code is one installable package. `src/` is the package source root.

- `drsim.simulation` owns simulation state and rules: engine, world, hazards, entities, routing, commands, and shared command validation.
- `drsim.ai` may depend on `drsim.simulation`.
- `drsim.evaluation` may depend on `drsim.simulation` and `drsim.ai`.
- `drsim.backend` orchestrates the other layers through defined interfaces.
- **The simulation layer must never import AI, backend, or evaluation.**
- Frontend code communicates with the backend through API contracts; simulation rules do not belong in the frontend or backend.

These boundaries are checked by `import-linter` in local development and CI.

## First vertical slice

The first end-to-end milestone is expected to:

1. Load a seeded synthetic earthquake scenario.
2. Advance the simulation by 10 fixed ticks.
3. Validate and apply a command through the shared simulation command path.
4. Produce a small outcome summary and deterministic result hash.
5. Repeat the same run and verify that the hash matches.

That behavior is not implemented in this starter scaffold yet.

## Repository layout

```text
src/drsim/       Python application package
frontend/        React + TypeScript + Phaser application (to be initialized)
scenarios/       Versioned synthetic scenario definitions
contracts/       API and shared data contracts
tests/           Unit, determinism, and integration tests
docs/adr/        Architecture Decision Records
docker/          Container-related files
.github/         CI workflow and future CODEOWNERS file
```

## Team workflow

- Work on a feature branch; avoid committing directly to `main`.
- Keep pull requests focused and request review before merging.
- Preserve agreed module boundaries. Discuss architecture changes before reorganizing directories.
- Do not commit `.env`, secrets, large generated simulation outputs, or local virtual environments.
- Module ownership and `.github/CODEOWNERS` should be filled in after the team agrees on owners.

## Current limitations

No simulation logic, API endpoints, frontend screens, Docker services, or database integration are implemented yet.
