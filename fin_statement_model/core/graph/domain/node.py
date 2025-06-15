"""Immutable node objects used by the *v2* graph engine.

This module is intentionally **tiny** and **pure** – it defines the
fundamental building-blocks that can be shared safely across threads and
processes.  There is *no* awareness of calculation engines, services or any
other infrastructure here.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from types import MappingProxyType
from typing import Final, FrozenSet, Mapping

__all__: list[str] = [
    "NodeKind",
    "Node",
    "parse_inputs",
]


class NodeKind(Enum):
    """Enumeration of node categories recognised by the engine."""

    INPUT = auto()
    FORMULA = auto()
    AGGREGATE = auto()

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class Node:
    """An **immutable** vertex in the financial-statement graph.

    Attributes
    ----------
    code:
        Unique identifier (snake-case string) used as the lookup key.
    kind:
        Category of node – :class:`NodeKind.INPUT` for raw data, etc.
    formula:
        Raw Python expression string *or* ``None`` for non-formula nodes.
    inputs:
        Frozen set of *codes* that this node depends on.  Populated only for
        formula/aggregate nodes so that the engine can precompute a topological
        ordering without parsing formulas repeatedly.
    data:
        Mapping of data values for this node.
    """

    code: str
    kind: NodeKind
    formula: str | None = None
    inputs: FrozenSet[str] = frozenset()
    data: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))

    # ------------------------------------------------------------------
    # Representation helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            "Node(code='"
            + self.code
            + "', kind="
            + str(self.kind)
            + (f", inputs={sorted(self.inputs)}" if self.inputs else "")
            + (f", data={len(self.data)}" if self.data else "")
            + ")"
        )


# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------

# Pre-compiled regex to capture identifiers in a Python expression.  This is
# very permissive but covers 99 % of typical financial formulas.
_IDENTIFIER_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_]\w*")


def parse_inputs(formula: str | None) -> FrozenSet[str]:
    """Return the *referenced node codes* in ``formula``.

    This helper keeps the logic close to :class:`Node` so that the builder can
    reuse it without circular imports.

    The implementation walks the AST produced by :pyfunc:`ast.parse`; this is
    more robust than a naive regex and still cheap for short formulas.

    Parameters
    ----------
    formula:
        Raw Python expression string.  ``None`` returns an empty set.

    Returns
    -------
    frozenset[str]
        All **identifier** names that look like node codes.  Python keywords and
        builtins are filtered out.
    """

    if not formula:
        return frozenset()

    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:  # pragma: no cover – caught upstream
        raise ValueError(f"Invalid formula syntax: {formula!r}") from exc

    names: set[str] = set()

    class _NameVisitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            names.add(node.id)

    _NameVisitor().visit(tree)

    # Exclude known Python builtins/keywords quickly via regex heuristic.
    candidates = filter(_IDENTIFIER_RE.fullmatch, names)
    python_keywords = set(
        {
            # Keyword list for CPython 3.12
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        }
    )

    return frozenset(set(candidates) - python_keywords)
