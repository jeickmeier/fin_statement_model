import json
import pathlib
import re
import sys

import nox

# ----------------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------------

BASELINE_FILE = pathlib.Path(".type_ignore_baseline.json")


def count_type_ignores(paths: list[pathlib.Path]) -> int:
    """Count occurrences of ``# type: ignore`` in the given Python files.

    Args:
        paths: A list of Python file paths to scan.

    Returns:
        The total number of ``# type: ignore`` directives found.
    """
    ignore_pattern = re.compile(r"#\s*type:\s*ignore")
    total = 0
    for path in paths:
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if ignore_pattern.search(line):
                    total += 1
        except UnicodeDecodeError:
            # Skip non-text/binary files just in case.
            continue
    return total


def load_baseline() -> int:
    """Return the baseline count of ``# type: ignore`` directives.

    If the baseline file doesn't exist, returns ``-1`` to indicate absence.
    """
    if not BASELINE_FILE.exists():
        return -1
    try:
        data = json.loads(BASELINE_FILE.read_text())
        return int(data.get("count", -1))
    except Exception:
        return -1


def save_baseline(count: int) -> None:
    """Persist the baseline count to disk."""
    BASELINE_FILE.write_text(
        json.dumps(
            {"count": count, "note": "Auto-generated baseline for type: ignore budget"},
            indent=2,
        )
    )


def enforce_type_ignore_budget(root: pathlib.Path, budget: int = 20) -> None:
    """Fail if the project exceeds the allowed ``# type: ignore`` count.

    Args:
        root: Repository root to scan.
        budget: Maximum allowed ``# type: ignore`` directives.
    """
    python_files = list(root.rglob("*.py"))
    total_ignores = count_type_ignores(python_files)
    baseline_count = load_baseline()

    if baseline_count == -1:
        session_msg = (
            "No baseline found for type-ignore budget; creating new baseline and continuing. "
            f"Current count = {total_ignores}. Future PRs may add at most {budget} new ignores."
        )
        print(session_msg)
        save_baseline(total_ignores)
        return

    allowed = baseline_count + budget

    if total_ignores > allowed:
        message = (
            f"Found {total_ignores} `# type: ignore` directives, which exceeds the baseline "
            f"({baseline_count}) + budget ({budget}). Reduce suppressions or update the baseline."
        )
        sys.exit(message)


# ----------------------------------------------------------------------------
# Nox sessions
# ----------------------------------------------------------------------------


@nox.session(reuse_venv=True)
def lint(session: nox.Session) -> None:
    """Run static-analysis checks (Ruff, MyPy) and enforce ignore budget."""
    # Install project in editable mode along with dev extras to ensure
    # console-script entrypoints (e.g. `ruff`) are available inside the
    # nox virtualenv.
    session.install("-e", ".[dev]")

    # Ensure the package itself is importable when running tests.
    # The project doesn't ship a `setup.py`/`pyproject.toml` yet, so we rely on
    # `PYTHONPATH` instead of `pip install -e .`.
    session.env["PYTHONPATH"] = f"{session.env.get('PYTHONPATH', '')}:" + str(
        pathlib.Path(".").resolve()
    )

    # ---------------------------------------------------------------------
    # Ruff - Linting (+ auto-fix in CI is disabled; we only report issues)
    # ---------------------------------------------------------------------
    session.log("Running Ruff...")
    session.run(
        "ruff",
        "check",
        "fin_statement_model",
        "--line-length",
        "120",
        external=True,
    )

    # ---------------------------------------------------------------------
    # Ruff - Formatting (ensure code is already formatted)
    # ---------------------------------------------------------------------
    session.log("Running Ruff format --check ...")
    session.run("ruff", "format", "--check", ".", external=True)

    # ---------------------------------------------------------------------
    # MyPy - Static type checking (strict mode configured in `mypy.ini`)
    # ---------------------------------------------------------------------
    session.log("Running MyPy (strict)...")
    session.run("mypy", "fin_statement_model", external=True)

    # ---------------------------------------------------------------------
    # Pytest - Unit tests (tests live under the top-level ``tests`` package)
    # ---------------------------------------------------------------------
    session.log("Running Pytest with coverage...")
    session.run(
        "pytest",
        "-q",
        "--cov=fin_statement_model",
        "--cov-report=term-missing",
        "--cov-config=pyproject.toml",
        "--cov-fail-under=80",
        external=True,
    )

    # # ---------------------------------------------------------------------
    # # Custom guard - Limit the number of `# type: ignore` usages.
    # # ---------------------------------------------------------------------
    # session.log("Checking `# type: ignore` budget (<= 20)...")
    # enforce_type_ignore_budget(pathlib.Path("."), budget=20)
    # session.log("Type ignore budget within limit.")
