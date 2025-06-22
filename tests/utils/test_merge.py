import pytest

from fin_statement_model.utils.merge import deep_merge


class DummyCfg:
    """Simple object to mimic a Pydantic-less config container."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DummyPydanticModel:
    """Mimic a very small subset of a Pydantic model for testing."""

    def __init__(self, **data):
        self._data = data

    def model_dump(self):  # noqa: D401 (docstring not required for test helper)
        return self._data


@pytest.mark.parametrize(
    "base, update, expected",
    [
        ({"a": 1}, {"a": 2}, {"a": 2}),
        (
            {"a": {"b": 1}},
            {"a": {"c": 2}},
            {"a": {"b": 1, "c": 2}},
        ),
        (
            {"lst": [1, 2]},
            {"lst": [2, 3]},
            {"lst": [1, 2, 3]},
        ),
        (
            {"lst": [1, 2]},
            {"lst": "overwrite"},
            {"lst": "overwrite"},
        ),
        (
            {"nested": {"lst": ["x"]}},
            {"nested": {"lst": ["x", "y"]}},
            {"nested": {"lst": ["x", "y"]}},
        ),
    ],
)
def test_deep_merge(base, update, expected):
    """deep_merge should handle overwrite, deep dicts and list concat."""
    result = deep_merge(base, update)
    assert result == expected
    # Ensure original objects not mutated
    assert base != result  # base should remain unchanged


def test_merge_configurations():
    """ConfigurationMixin.merge_configurations must delegate to deep_merge."""
    from fin_statement_model.io.core.mixins.configuration import ConfigurationMixin

    mixin = ConfigurationMixin()

    cfg1 = {"a": 1, "b": {"c": 1}, "lst": [1]}
    cfg2 = DummyCfg(a=2, b={"d": 3}, lst=[2, 3])
    cfg3 = DummyPydanticModel(extra=42)

    merged = mixin.merge_configurations(cfg1, cfg2, cfg3)

    expected = {
        "a": 2,
        "b": {"c": 1, "d": 3},
        "lst": [1, 2, 3],
        "extra": 42,
    }
    assert merged == expected
