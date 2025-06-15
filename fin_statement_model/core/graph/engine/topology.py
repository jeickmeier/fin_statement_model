"""Graph topology helpers – pure algorithms, no side-effects."""

from __future__ import annotations

from collections import deque
from typing import Mapping, Sequence

from fin_statement_model.core.graph.domain import Node

__all__: list[str] = ["CycleError", "toposort"]


class CycleError(RuntimeError):
    """Raised when the node dependency graph contains a directed cycle."""

    def __init__(self, cycle: Sequence[str]):
        super().__init__("Cycle detected: " + " -> ".join(cycle))
        self.cycle: Sequence[str] = cycle


def toposort(nodes: Mapping[str, Node]) -> tuple[str, ...]:
    """Return nodes in topological order (dependencies first).

    The algorithm implements a variant of **Kahn's algorithm** and runs in
    *O(|V| + |E|)* time.  A :class:`CycleError` is raised if the graph contains
    a cycle.

    Parameters
    ----------
    nodes:
        Mapping ``code → Node`` where *inputs* are stored on each node.
    """

    # Build indegree map and adjacency list ----------------------------
    indegree: dict[str, int] = {code: 0 for code in nodes}
    adj: dict[str, list[str]] = {code: [] for code in nodes}

    for node in nodes.values():
        for dep in node.inputs:
            if dep not in nodes:
                # Missing dependency is treated as *zero indegree* here – the
                # builder will validate existence separately.
                indegree.setdefault(dep, 0)
                adj.setdefault(dep, [])
            adj[dep].append(node.code)
            indegree[node.code] += 1

    # Kahn --------------------------------------------------------------
    queue: deque[str] = deque([c for c, deg in indegree.items() if deg == 0])
    order: list[str] = []

    while queue:
        n = queue.popleft()
        order.append(n)
        for succ in adj.get(n, []):
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)

    if len(order) != len(indegree):  # cycle!
        # Recover cycle via DFS (simplified) ----------------------------
        visited: set[str] = set(order)
        cycle_start = next(code for code in indegree if code not in visited)
        cycle: list[str] = []
        current = cycle_start
        while True:
            cycle.append(current)
            # follow first dependency that leads to unmet indegree>0
            next_nodes = [succ for succ in adj[current] if succ not in visited]
            if not next_nodes:
                break
            current = next_nodes[0]
            if current == cycle_start:
                break
        raise CycleError(cycle)

    return tuple(order)
