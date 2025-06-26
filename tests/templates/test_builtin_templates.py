import os
from pathlib import Path

import pytest

from fin_statement_model.templates.builtin import install_builtin_templates
from fin_statement_model.templates.registry import TemplateRegistry


@pytest.mark.usefixtures("tmp_path")
def test_install_builtin_templates_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """install_builtin_templates should populate the registry and be idempotent."""
    # Redirect registry storage to an isolated temp directory so the test does not
    # pollute the real user environment.
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    # First call – installs templates
    install_builtin_templates()
    first_listing = set(TemplateRegistry.list())

    # Sanity check: at least one built-in template should be present.
    assert first_listing, "Expected at least one built-in template to be installed."

    # Second call – must not raise and must not duplicate entries
    install_builtin_templates()
    second_listing = set(TemplateRegistry.list())

    assert first_listing == second_listing, "install_builtin_templates should be idempotent."

    # Force re-install should overwrite without duplicating
    install_builtin_templates(force=True)
    third_listing = set(TemplateRegistry.list())

    assert third_listing == second_listing, "Force re-install should yield the same template IDs." 