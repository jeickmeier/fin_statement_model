from __future__ import annotations

import pytest

from fin_statement_model.core.node_factory.deserialisers import (
    _get_forecast_node_cls,
    create_from_dict,
)
from fin_statement_model.core.errors import ConfigurationError


def test_get_forecast_node_cls_errors(monkeypatch):
    # Missing key
    with pytest.raises(ConfigurationError):
        _get_forecast_node_cls({})

    # Unknown forecast type
    with pytest.raises(ConfigurationError):
        _get_forecast_node_cls({"forecast_type": "not_registered"})


def test_create_from_dict_error_paths(monkeypatch):
    # Non-dict input
    with pytest.raises(TypeError):
        create_from_dict("not a dict")  # type: ignore[arg-type]

    # Missing 'type'
    with pytest.raises(ConfigurationError):
        create_from_dict({})

    # Unknown node type
    with pytest.raises(ConfigurationError):
        create_from_dict({"type": "mystery"})
