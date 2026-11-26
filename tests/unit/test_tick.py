import time

from drsim.simulation.engine import tick
from drsim.simulation.snapshot import build_snapshot
from tests.unit.test_state_init import _state


def test_each_tick_advances_exactly_10_seconds():
    s = _state()
    for n in range(1, 4):
        tick.step(s)
        assert s.tick == n
        assert build_snapshot(s).simulationTimeSeconds == n * 10


def test_phases_run_in_documented_order(monkeypatch):
    calls = []
    names = [f.__name__ for f in tick.PHASES]
    fakes = tuple((lambda st, n=n: calls.append(n)) for n in names)
    monkeypatch.setattr(tick, "PHASES", fakes)
    tick.step(_state())
    assert (
        calls
        == names
        == [
            "load_scheduled_events",
            "apply_operator_commands",
            "apply_automated_commands",
            "apply_hazards",
            "update_movement",
            "update_workflows",
            "update_victim_health",
            "check_end_condition",
        ]
    )


def test_same_input_same_progression():
    a, b = _state(), _state()
    for _ in range(50):
        tick.step(a)
        tick.step(b)
        assert build_snapshot(a) == build_snapshot(b)
        assert a.rng.getstate() == b.rng.getstate()


def test_wall_clock_does_not_matter(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("wall clock used")

    for fn in ("time", "monotonic", "perf_counter", "sleep"):
        monkeypatch.setattr(time, fn, boom)
    tick.step(_state())
