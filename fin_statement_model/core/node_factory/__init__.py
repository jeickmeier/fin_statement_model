"""
NodeFactory façade for fin_statement_model.core.

This module provides the public entry-point for node creation, deserialization, and custom node helpers.
It re-exports the NodeFactory class, which statically aggregates builder, deserializer, and helper functions
from internal submodules. Downstream code should import NodeFactory from this module or from
fin_statement_model.core directly.

Example:
    >>> from fin_statement_model.core.node_factory import NodeFactory
    >>> node = NodeFactory.create_financial_statement_item('Revenue', {'2022': 100.0, '2023': 120.0})
    >>> node
    <FinancialStatementItemNode name='Revenue'>
"""

from __future__ import annotations

import logging

from fin_statement_model.core.node_factory import builders as _builders
from fin_statement_model.core.node_factory import deserialisers as _deser
from fin_statement_model.core.node_factory import custom_helpers as _custom
from fin_statement_model.core.node_factory.registries import (
    CalculationAliasRegistry,
    NodeTypeRegistry,
    ForecastTypeRegistry,
)

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "NodeFactory",
    "CalculationAliasRegistry",
    "NodeTypeRegistry",
    "ForecastTypeRegistry",
]


class NodeFactory:  # pylint: disable=too-few-public-methods
    """Static aggregation of builder, deserializer, and helper functions for node creation.

    This class exposes static methods for creating financial statement items, calculation nodes, forecast nodes,
    and for deserializing nodes from dictionaries. It also provides access to custom node creation helpers and
    legacy calculation method mappings.

    All methods are static and simply delegate to the underlying functional helpers. This allows both service-object
    and functional usage patterns.

    Example:
        >>> from fin_statement_model.core.node_factory import NodeFactory
        >>> node = NodeFactory.create_financial_statement_item('COGS', {'2022': 50.0})
        >>> node
        <FinancialStatementItemNode name='COGS'>
    """

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    create_financial_statement_item = staticmethod(
        _builders.create_financial_statement_item
    )
    create_calculation_node = staticmethod(_builders.create_calculation_node)
    create_forecast_node = staticmethod(_builders.create_forecast_node)

    # ------------------------------------------------------------------
    # Deserialisation
    # ------------------------------------------------------------------
    create_from_dict = staticmethod(_deser.create_from_dict)

    # ------------------------------------------------------------------
    # Custom helper
    # ------------------------------------------------------------------
    _create_custom_node_from_callable = staticmethod(
        _custom._create_custom_node_from_callable  # pylint: disable=protected-access
    )

    # ------------------------------------------------------------------
    # Legacy attribute mapping used by existing code
    # ------------------------------------------------------------------
    _calculation_methods: dict[str, str] = {
        alias: cls.__name__ for alias, cls in CalculationAliasRegistry.items()
    }


# Log once on import so users know modular factory is active
logger.debug("Modular NodeFactory initialised (helpers wired).")
