from drsim.simulation.state import SimulationState


def apply_commands(state: SimulationState) -> None: ...
def update_world(state: SimulationState) -> None: ...
def update_units(state: SimulationState) -> None: ...
def update_victims(state: SimulationState) -> None: ...
def check_end_condition(state: SimulationState) -> None: ...


# Fixed phase order
PHASES = (
    apply_commands,
    update_world,
    update_units,
    update_victims,
    check_end_condition,
)


def step(state: SimulationState) -> None:
    for phase in PHASES:
        phase(state)
    state.tick += 1  # simulated time = tick * tickDurationSeconds (10 s)
