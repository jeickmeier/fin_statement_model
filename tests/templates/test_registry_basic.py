from __future__ import annotations

"""Tests for the initial TemplateRegistry implementation (PR-2)."""

import os
import stat
from pathlib import Path

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


@pytest.fixture()
def tmp_registry_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:  # noqa: D401
    """Create an isolated registry root under *tmp_path* and patch env var."""
    root = tmp_path / "registry"
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(root))
    return root


def _file_mode(path: Path) -> int:
    """Return POSIX mode bits of *path* (e.g. ``0o600``)."""
    return stat.S_IMODE(path.stat().st_mode)


def test_register_and_list(tmp_registry_dir: Path) -> None:  # noqa: D401
    graph = Graph()
    template_id = TemplateRegistry.register_graph(
        graph,
        name="test.template",
        version="v1",
        meta={"description": "dummy", "category": "test"},
    )

    assert template_id == "test.template_v1"
    assert TemplateRegistry.list() == [template_id]

    bundle = TemplateRegistry.get(template_id)
    assert bundle.meta.name == "test.template"
    assert bundle.meta.version == "v1"

    # Check bundle path + permissions
    expected_path = (
        tmp_registry_dir
        / "store"
        / "test"
        / "template"
        / "v1"
        / "bundle.json"
    )
    assert expected_path.exists()
    assert _file_mode(expected_path) == 0o600 