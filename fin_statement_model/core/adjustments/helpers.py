"""Helper functions for the adjustments module."""


def tag_matches(target_tags: set[str], prefixes: set[str]) -> bool:
    """Check if any target tag starts with any of the given prefixes.

    Allows for hierarchical matching: a prefix "A/B" matches tag "A/B/C".
    A simple prefix "A" matches tag "A/B".

    Args:
        target_tags: The set of tags on an adjustment.
        prefixes: The set of prefixes to check against (e.g., from a filter).

    Returns:
        True if at least one tag in target_tags starts with at least one
        prefix in prefixes, False otherwise.

    Examples:
        >>> tag_matches({'A/B/C', 'X'}, {'A/B'})
        True
        >>> tag_matches({'A/B/C'}, {'D'})
        False
    """
    if not prefixes:  # Optimization: if no prefixes specified, it can't match
        return False
    if not target_tags:  # Optimization: if no tags exist, it can't match
        return False

    # Check if any combination of tag and prefix matches
    return any(t.startswith(p) for t in target_tags for p in prefixes)
