"""Helper class for rendering StatementStructure to markdown format.

Moved from `io.formats.markdown.renderer`.
"""

from __future__ import annotations

import logging
from typing import Optional, Union

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.structure import (
    Section,
    StatementItem,
    StatementItemType,
    StatementStructure,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    MetricLineItem,
)
from fin_statement_model.io.formats.markdown.models import MarkdownStatementItem
from fin_statement_model.core.nodes import standard_node_registry

logger = logging.getLogger(__name__)


class MarkdownStatementRenderer:
    """Render StatementStructure to markdown items list."""

    def __init__(self, graph: Graph, indent_spaces: int = 4):
        self.graph = graph
        self.indent_spaces = indent_spaces
        self.periods = sorted(list(graph.periods))

    def render_structure(
        self,
        structure: StatementStructure,
        historical_periods: Optional[set[str]] = None,
        forecast_periods: Optional[set[str]] = None,
    ) -> list[MarkdownStatementItem]:
        items: list[MarkdownStatementItem] = []
        for section in structure.sections:
            items.extend(self._render_section(section, level=0))
        return items

    def _render_section(
        self, section: Section, level: int
    ) -> list[MarkdownStatementItem]:
        items: list[MarkdownStatementItem] = []
        for item in section.items:
            if isinstance(item, Section):
                items.extend(self._render_section(item, level + 1))
            else:
                rendered = self._render_item(item, level + 1)
                if rendered:
                    items.append(rendered)
        if hasattr(section, "subtotal") and section.subtotal:
            subtotal_rendered = self._render_item(section.subtotal, level + 1)
            if subtotal_rendered:
                items.append(subtotal_rendered)
        return items

    def _render_item(
        self, item: StatementItem, level: int
    ) -> Optional[MarkdownStatementItem]:
        try:
            values = self._extract_values(item)
            return MarkdownStatementItem(
                name=item.name,
                values=values,
                level=level,
                is_subtotal=(item.item_type == StatementItemType.SUBTOTAL),
                sign_convention=getattr(item, "sign_convention", 1),
                display_format=item.display_format,
                units=item.units,
                display_scale_factor=item.display_scale_factor,
                is_contra=item.is_contra,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to render item %s: %s", item.id, e)
            return None

    def _extract_values(
        self, item: StatementItem
    ) -> dict[str, Union[float, int, str, None]]:
        values: dict[str, Union[float, int, str, None]] = {}
        node_id = self._get_node_id(item)
        if not node_id:
            logger.warning("Could not determine node ID for item: %s", item.id)
            return {p: None for p in self.periods}
        try:
            node = self.graph.get_node(node_id)
            if node is None:
                logger.warning("Node '%s' returned None for item: %s", node_id, item.id)
                return {p: None for p in self.periods}
            for period in self.periods:
                raw_val = None
                if isinstance(
                    item, (CalculatedLineItem, SubtotalLineItem, MetricLineItem)
                ):
                    try:
                        raw_val = self.graph.calculate(node_id, period)
                    except Exception:
                        raw_val = "CALC_ERR"
                elif isinstance(item, LineItem):
                    raw_val = node.calculate(period)
                values[period] = self._apply_formatting(raw_val, item)
        except KeyError:
            logger.warning(
                "Node '%s' not found in graph for item: %s", node_id, item.id
            )
            values = {p: None for p in self.periods}
        except Exception as e:  # noqa: BLE001
            logger.warning("Error extracting values for item %s: %s", item.id, e)
            values = {p: "ERROR" for p in self.periods}
        return values

    def _get_node_id(self, item: StatementItem) -> Optional[str]:
        if isinstance(item, LineItem):
            if item.node_id:
                return item.node_id
            if item.standard_node_ref:
                return item.get_resolved_node_id(standard_node_registry)
            return None
        if isinstance(item, (CalculatedLineItem, SubtotalLineItem, MetricLineItem)):
            return item.id
        return None

    def _apply_formatting(
        self, raw_val: Union[float, int, str, None], item: StatementItem
    ) -> Union[float, int, str, None]:
        if raw_val is None or isinstance(raw_val, str):
            return raw_val
        if isinstance(raw_val, (int, float)):
            signed = raw_val * getattr(item, "sign_convention", 1)
            scaled = signed * item.display_scale_factor
            return scaled
        return raw_val
