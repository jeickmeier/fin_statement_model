from __future__ import annotations

"""Tests for the new Pydantic-v2 runtime models (models_v2)."""

from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter

from fin_statement_model.statements.structure import models_v2 as m_v2


SAMPLE_YAML = """
id: income_statement
name: Income Statement
sections:
  - id: operating_results
    name: Operating Results
    type: section
    items:
      - id: revenue
        name: Revenue
        type: line_item
        node_id: revenue
      - id: cost_of_goods_sold
        name: Cost of Goods Sold
        type: line_item
        node_id: cost_of_goods_sold
      - id: gross_profit
        name: Gross Profit
        type: calculated
        calculation:
          type: subtraction
          inputs:
            - revenue
            - cost_of_goods_sold
"""


def _normalize(mapping: dict) -> dict:
    """Recursively sort lists-of-dicts so dict equality becomes order-insensitive."""

    if isinstance(mapping, dict):
        return {k: _normalize(v) for k, v in mapping.items()}
    if isinstance(mapping, list):
        return sorted((_normalize(i) for i in mapping), key=lambda x: str(x))
    return mapping


# ---------------------------------------------------------------------------
# Round-trip YAML → model_validate → model_dump integrity test
# ---------------------------------------------------------------------------

def test_round_trip_integrity(tmp_path: Path) -> None:  # noqa: D401
    original_dict = yaml.safe_load(SAMPLE_YAML)
    model = m_v2.StatementStructure.model_validate(original_dict)

    # When dumping, use aliases and *exclude_none* so the output is as close
    # as possible to the original source.
    dumped = model.model_dump(by_alias=True, exclude_none=True, exclude={"all_item_ids"})

    assert _normalize(dumped) == _normalize(original_dict)


# ---------------------------------------------------------------------------
# Discriminator handling
# ---------------------------------------------------------------------------

def test_discriminator_deserialization() -> None:  # noqa: D401
    adapter = TypeAdapter(m_v2.StatementItem)

    samples = [
        ({"id": "x", "name": "Line", "type": "line_item", "node_id": "Revenue"}, m_v2.LineItem),
        (
            {
                "id": "c",
                "name": "Calc",
                "type": "calculated",
                "calculation": {"type": "addition", "inputs": ["a", "b"]},
            },
            m_v2.CalculatedLineItem,
        ),
        (
            {
                "id": "s",
                "name": "Sub",
                "type": "subtotal",
                "items_to_sum": ["a", "b"],
            },
            m_v2.SubtotalLineItem,
        ),
        (
            {
                "id": "m",
                "name": "Metric",
                "type": "metric",
                "metric_id": "return_on_assets",
                "inputs": {"net_income": "ni", "total_assets": "ta"},
            },
            m_v2.MetricLineItem,
        ),
    ]

    for payload, expected_type in samples:
        obj = adapter.validate_python(payload)
        assert isinstance(obj, expected_type), f"Expected {expected_type}, got {type(obj)}"


# ---------------------------------------------------------------------------
# Immutability enforcement
# ---------------------------------------------------------------------------

def test_model_immutability() -> None:  # noqa: D401
    model = m_v2.StatementStructure.model_validate(yaml.safe_load(SAMPLE_YAML))

    with pytest.raises((TypeError, ValueError, Exception)) as exc:
        # Depending on pydantic internals this may raise TypeError or ValidationError.
        model.name = "New Name"  # type: ignore[misc]
    # Sanity-check that the raised error indicates immutability.
    assert "frozen" in str(exc.value).lower() 