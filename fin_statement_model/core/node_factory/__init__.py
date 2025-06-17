"""
Modular NodeFactory façade – public entry-point used by *core*.

This file re-exports :class:`NodeFactory` that composes thin builder/
serialiser helpers from the internal sub-modules.  Down-stream code imports
``NodeFactory`` from ``fin_statement_model.core`` or
``fin_statement_model.core.node_factory`` and remains unaffected.
"""

from __future__ import annotations

import logging

from fin_statement_model.core.node_factory import builders as _builders
from fin_statement_model.core.node_factory import deserialisers as _deser
from fin_statement_model.core.node_factory import custom_helpers as _custom
from fin_statement_model.core.node_factory.registries import CalculationAliasRegistry

logger = logging.getLogger(__name__)

__all__: list[str] = ["NodeFactory"]


class NodeFactory:  # pylint: disable=too-few-public-methods
    """Public aggregation of builder + helper functions.

    The class is intentionally *static* – all methods are simple pass-throughs
    to the underlying functional helpers.  Using `staticmethod` avoids the need
    to instantiate the factory, preserving backward-compatibility with legacy
    code that treated it as a *service object* (i.e., via ``self._node_factory``)
    but also allows direct functional use.
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
