"""Tests for collision-safe, idempotent transformer registration."""

from __future__ import annotations

import pytest

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.transformer_service import TransformerFactory


class DummyTransformer(DataTransformer):
    def _transform_impl(self, data):  # pragma: no cover
        return data

    def validate_input(self, data):  # pragma: no cover
        return True


def test_idempotent_registration():
    # First registration should succeed
    TransformerFactory.register_transformer("dummy", DummyTransformer)
    # Second registration with same class and name is a no-op
    TransformerFactory.register_transformer("dummy", DummyTransformer)


def test_collision_registration_raises():
    class OtherTransformer(DummyTransformer):
        pass

    with pytest.raises(Exception):
        TransformerFactory.register_transformer("dummy", OtherTransformer)
