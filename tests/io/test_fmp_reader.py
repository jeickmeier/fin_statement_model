"""Unit-test happy path for FmpReader using mocked requests."""

from __future__ import annotations

from typing import Any

import pytest

from fin_statement_model.io.formats.fmp_reader import FmpReader
from fin_statement_model.io.config.models import FmpReaderConfig


class _DummyResponse:
    def __init__(self, json_payload: Any, status_code: int = 200):
        self._payload = json_payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP Error")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Prevent real HTTP calls in FmpReader tests."""
    import requests

    def _blocked(*_a, **_kw):  # noqa: ANN001
        raise RuntimeError("Network access blocked in tests")

    monkeypatch.setattr(requests, "get", _blocked)


def test_fmp_reader_happy(monkeypatch):
    """FmpReader should parse mocked API response into graph."""
    # Prepare fake API payload
    payload = [
        {"date": "2022", "revenue": 100.0},
        {"date": "2023", "revenue": 120.0},
    ]

    # Monkeypatch requests.get to return dummy response only for our call
    import requests

    def _fake_get(*_a, **_kw):  # noqa: ANN001
        return _DummyResponse(payload)

    monkeypatch.setattr(requests, "get", _fake_get)

    # Also bypass API-key validation
    monkeypatch.setattr(FmpReader, "_cached_validate_key", lambda *_a, **_kw: None)

    cfg = FmpReaderConfig(
        source="unused",
        format_type="fmp",
        statement_type="income_statement",
        period_type="FY",
        limit=2,
        api_key="dummy",
        mapping_config=None,
    )
    reader = FmpReader(cfg)

    graph = reader.read("AAPL")

    assert set(graph.periods) == {"2022", "2023"}
    node = graph.get_node("revenue")
    assert node is not None
    assert node.calculate("2023") == 120.0
