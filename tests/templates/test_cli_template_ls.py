from __future__ import annotations

"""CLI tests for `fsm template ls`."""

from pathlib import Path

from click.testing import CliRunner

from fin_statement_model.cli import fsm
from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


def test_template_ls_cli(tmp_path: Path, monkeypatch) -> None:  # noqa: D401
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    # Register a dummy template so output is deterministic
    TemplateRegistry.register_graph(Graph(), name="cli.template", version="v1")

    runner = CliRunner()
    result = runner.invoke(fsm, ["template", "ls", "--plain"])
    assert result.exit_code == 0
    assert "cli.template_v1" in result.output.strip().split("\n") 