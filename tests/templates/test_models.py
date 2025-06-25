from __future__ import annotations

"""Tests for Template Registry & Engine domain models."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from fin_statement_model.templates.models import (
    DiffResult,
    StructureDiff,
    TemplateBundle,
    TemplateMeta,
    ValuesDiff,
)
from fin_statement_model.templates.models import _calculate_sha256_checksum as calc_checksum


@pytest.fixture()
def sample_graph_dict() -> dict[str, object]:
    """Return a minimal graph-definition mapping suitable for tests."""
    return {
        "nodes": [
            {"id": "n1", "value": 1},
            {"id": "n2", "value": 2},
        ],
        "edges": [["n1", "n2"]],
    }


def test_template_bundle_round_trip(sample_graph_dict: dict[str, object]) -> None:
    """Ensure `TemplateBundle` round-trips through model_dump / model_validate."""
    meta = TemplateMeta(name="lbo", version="v1", category="lbo")
    checksum = calc_checksum(sample_graph_dict)
    bundle = TemplateBundle(meta=meta, graph_dict=sample_graph_dict, checksum=checksum)

    serialised = bundle.model_dump()
    deserialised = TemplateBundle.model_validate(serialised)

    assert deserialised == bundle


def test_checksum_validation_error(sample_graph_dict: dict[str, object]) -> None:
    """Checksum mismatch should raise a `ValidationError`."""
    meta = TemplateMeta(name="lbo", version="v1", category="lbo")
    good_checksum = calc_checksum(sample_graph_dict)

    # Tamper with graph but keep the original checksum ⇒ should fail.
    tampered_graph = {**sample_graph_dict, "extra": True}

    with pytest.raises(ValidationError):
        TemplateBundle(meta=meta, graph_dict=tampered_graph, checksum=good_checksum)


def test_immutability(sample_graph_dict: dict[str, object]) -> None:
    """Attempting to mutate a frozen model must raise `TypeError`."""
    meta = TemplateMeta(name="lbo", version="v1", category="lbo")
    bundle = TemplateBundle(
        meta=meta,
        graph_dict=sample_graph_dict,
        checksum=calc_checksum(sample_graph_dict),
    )

    with pytest.raises((TypeError, ValidationError)):
        bundle.meta.name = "changed"  # type: ignore[misc]


def test_diff_result_basic() -> None:
    """Basic instantiation and JSON round-trip for `DiffResult`."""
    structure = StructureDiff(added_nodes=["n3"], removed_nodes=["n1"], changed_nodes={"n2": "formula"})
    values = ValuesDiff(changed_cells={"n2|2025": 0.1}, max_delta=0.1)

    diff = DiffResult(structure=structure, values=values)

    # Ensure serialisation round-trips
    dumped = diff.model_dump()
    restored = DiffResult.model_validate(dumped)

    assert restored == diff 