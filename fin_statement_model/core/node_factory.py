# pylint: disable=deprecated-module
"""Legacy shim – NodeFactory has moved to ``core/node_factory/`` package.

This file remains temporarily to avoid breaking user imports during the
modular-factory refactor.  All logic has been removed; it re-exports
:class:`~fin_statement_model.core.node_factory.NodeFactory` and raises a
:class:`DeprecationWarning` once on import.

The shim will be deleted in a future minor release.
"""

from __future__ import annotations

import warnings

from fin_statement_model.core.node_factory import NodeFactory  # type: ignore  # pylint: disable=wrong-import-position

warnings.warn(
    "`fin_statement_model.core.node_factory` internals have moved.  Importing "
    "this module is deprecated and will be removed in a future version.  "
    "Please update any direct references to the new modular sub-package if "
    "needed.",
    DeprecationWarning,
    stacklevel=2,
)

__all__: list[str] = ["NodeFactory"]
