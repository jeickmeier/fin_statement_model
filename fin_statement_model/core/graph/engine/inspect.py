"""Pure graph-inspection helpers (no side-effects).

All functions operate on an immutable :class:`fin_statement_model.core.graph.engine.state.GraphState`.
They are intentionally **stateless** and have no external dependencies.
"""

from __future__ import annotations

from collections import deque
from typing import List, Set

from fin_statement_model.core.graph.engine.state import GraphState

__all__: list[str] = [
    "dependencies",
    "successors",
    "predecessors",
    "breadth_first",
    "detect_cycles",
]


def dependencies(state: GraphState, code: str) -> List[str]:
    """Return the direct dependency codes of *code*."""
    return sorted(state[code].inputs)


def successors(state: GraphState, code: str) -> List[str]:
    """Return direct successor nodes (nodes that list *code* in their inputs)."""
    succ: list[str] = []
    for other, node in state.nodes.items():
        if code in node.inputs:
            succ.append(other)
    return sorted(succ)


def predecessors(state: GraphState, code: str) -> List[str]:
    """Alias for :func:`dependencies`."""
    return dependencies(state, code)


def breadth_first(
    state: GraphState, start: str, *, direction: str = "successors"
) -> List[List[str]]:
    if direction not in ("successors", "predecessors"):
        raise ValueError("direction must be 'successors' or 'predecessors'")
    visit_func = successors if direction == "successors" else predecessors

    visited: Set[str] = {start}
    queue: deque[str] = deque([start])
    levels: list[list[str]] = []

    while queue:
        level_size = len(queue)
        level: list[str] = []
        for _ in range(level_size):
            node = queue.popleft()
            level.append(node)
            for nbr in visit_func(state, node):
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)
        levels.append(level)
    return levels


def detect_cycles(
    state: GraphState,
) -> List[List[str]]:  # pragma: no cover – simple impl
    from fin_statement_model.core.graph.engine.topology import CycleError, toposort

    try:
        toposort(state.nodes)
        return []
    except CycleError as err:
        return [list(err.cycle)]
