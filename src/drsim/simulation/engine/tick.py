from drsim.simulation.state import SimulationState


def load_scheduled_events(state: SimulationState) -> None: ...
def apply_operator_commands(state: SimulationState) -> None: ...
def apply_automated_commands(state: SimulationState) -> None: ...
def apply_hazards(state: SimulationState) -> None: ...
def update_movement(state: SimulationState) -> None: ...
def update_workflows(state: SimulationState) -> None: ...
def update_victim_health(state: SimulationState) -> None: ...
def check_end_condition(state: SimulationState) -> None: ...


# Fixed phase order
PHASES = (
    load_scheduled_events,  # 1-2
    apply_operator_commands,  # 3
    apply_automated_commands,  # 4
    apply_hazards,  # 5
    update_movement,  # 6
    update_workflows,  # 7
    update_victim_health,  # 8
    check_end_condition,  # 9
)


def step(state: SimulationState) -> None:
    """Process the current tick, then advance.

    Phases run against `state.tick` (the first call processes tick 0);
    the counter increments at the end. Simulated time = tick * 10 s.
    """
    for phase in PHASES:
        phase(state)
    state.tick += 1  # simulated time = tick * tickDurationSeconds (10 s)
