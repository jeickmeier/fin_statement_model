"""Tests for fin_statement_model.utils.dicts.deep_merge."""

from __future__ import annotations

from fin_statement_model.utils.dicts import deep_merge


def test_deep_merge_nested_override() -> None:
    base = {"outer": {"inner": 1, "unchanged": 2}, "keep": 3}
    update = {"outer": {"inner": 42}, "added": "x"}
    merged = deep_merge(base, update)

    assert merged["outer"]["inner"] == 42  # override
    assert merged["outer"]["unchanged"] == 2  # preserved
    assert merged["keep"] == 3  # preserved
    assert merged["added"] == "x"  # new key


def test_deep_merge_copy_true_does_not_mutate_inputs() -> None:
    base = {"a": 1}
    update = {"b": 2}
    result = deep_merge(base, update)

    assert result is not base
    assert result == {"a": 1, "b": 2}
    # Ensure originals unchanged
    assert base == {"a": 1}
    assert update == {"b": 2}


def test_deep_merge_inplace() -> None:
    base: dict[str, int | dict[str, int]] = {"level1": {"x": 10}}
    update = {"level1": {"y": 20}}

    result = deep_merge(base, update, copy=False)

    # When copy=False we expect the same object back
    assert result is base
    # Both keys now present
    assert result["level1"]["x"] == 10
    assert result["level1"]["y"] == 20
