"""Import smoke tests for each top-level package."""



def test_import_stackperf() -> None:
    """Test that the main package can be imported."""
    import stackperf

    assert stackperf.__version__ == "0.1.0"


def test_import_benchmark_core() -> None:
    """Test that benchmark_core module can be imported."""
    from stackperf import benchmark_core

    assert benchmark_core is not None


def test_import_cli() -> None:
    """Test that cli module can be imported."""
    from stackperf import cli

    assert cli is not None


def test_import_collectors() -> None:
    """Test that collectors module can be imported."""
    from stackperf import collectors

    assert collectors is not None


def test_import_reporting() -> None:
    """Test that reporting module can be imported."""
    from stackperf import reporting

    assert reporting is not None


def test_import_api() -> None:
    """Test that api module can be imported."""
    from stackperf import api

    assert api is not None
