"""Tests for adjustment helper functions."""

import pytest
from typing import Union

from fin_statement_model.core.adjustments.helpers import tag_matches


@pytest.mark.parametrize(
    ("target_tags", "prefixes", "expected"),
    [
        ({"A/B", "C"}, {"A"}, True),  # Prefix match
        ({"A/B", "C"}, {"A/B"}, True),  # Exact match
        ({"A/B", "C"}, {"A/"}, True),  # Prefix match with slash
        ({"A/B", "C"}, {"B"}, False),  # No match (not prefix)
        ({"A/B", "C"}, {"D"}, False),  # No match
        (set(), {"A"}, False),  # No target tags
        ({"A/B"}, set(), False),  # No prefixes
        (set(), set(), False),  # Both empty
        ({"Revenue/US", "Revenue/EU"}, {"Revenue"}, True),
        ({"Revenue/US", "COGS/EU"}, {"Revenue"}, True),
        ({"Revenue/US", "COGS/EU"}, {"COGS"}, True),
        ({"Revenue/US", "COGS/EU"}, {"Expenses"}, False),
        ({"TAG"}, {"TAG"}, True),  # Exact match single tag
        ({"TAG"}, {"T"}, True),  # Prefix match single tag
        ({"TAG1"}, {"TAG2"}, False),  # No match single tags
    ],
)
def test_tag_matches(
    target_tags: set[str], prefixes: Union[str, set[str]], expected: bool
) -> None:
    """Test the tag_matches function with various inputs."""
    assert tag_matches(target_tags, prefixes) == expected
