def test_core_packages_import():
    import drsim.ai
    import drsim.backend
    import drsim.evaluation
    import drsim.simulation

    assert drsim.simulation is not None
    assert drsim.ai is not None
    assert drsim.backend is not None
    assert drsim.evaluation is not None
