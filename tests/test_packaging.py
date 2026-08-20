from pathlib import Path

import benchmark_radar


def test_tests_import_this_checkouts_source():
    """Guard against a worktree silently testing another checkout's code.

    The venv has the repo installed as an editable package, so without
    `pythonpath = ["src"]` in pyproject.toml a bare `pytest` run inside a git
    worktree imports benchmark_radar from whichever checkout was pip-installed.
    The suite then passes while measuring source the branch never touched.
    """
    imported = Path(benchmark_radar.__file__).resolve()
    expected = (Path(__file__).parent.parent / "src" / "benchmark_radar" / "__init__.py").resolve()
    assert imported == expected, f"tests import {imported}, expected {expected}"
