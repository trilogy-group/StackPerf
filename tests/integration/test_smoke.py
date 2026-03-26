"""Integration smoke tests."""


def test_all_top_level_packages_import() -> None:
    """Verify all top-level packages import without errors."""
    import api
    import benchmark_core
    import cli
    import collectors
    import reporting

    assert benchmark_core is not None
    assert cli is not None
    assert collectors is not None
    assert reporting is not None
    assert api is not None
