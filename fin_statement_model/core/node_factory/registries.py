"""Decorator-based registries used by the modular :pymod:`core.node_factory`.

The three public registries are:

* ``CalculationAliasRegistry``   – maps *alias strings* ("addition") to
  :class:`~fin_statement_model.core.calculations.calculation.Calculation`
  subclasses.
* ``NodeTypeRegistry``           – maps the value of ``node_dict['type']`` to
  concrete node classes.
* ``ForecastTypeRegistry``       – maps forecast‐type identifiers ("simple",
  "curve", …) to subclasses of
  :class:`fin_statement_model.core.nodes.forecast_nodes.ForecastNode`.

Each registry exposes a decorator helper so classes can self-register:

>>> from fin_statement_model.core.node_factory.registries import calc_alias
>>> @calc_alias("addition")
... class AdditionCalculation(Calculation):
...     ...

This keeps ``node_factory`` free from hard-coded look-up tables and allows
extensions to register their own classes at import time without touching core
code.

Examples:
    >>> 'addition' in CalculationAliasRegistry
    True
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Generic, List, TypeVar

logger = logging.getLogger(__name__)

# Generic type variable for objects stored in a registry
_T = TypeVar("_T", bound=object)


class _BaseRegistry(Dict[str, _T], Generic[_T]):
    """A thin dict wrapper adding validation and decorator helpers.

    This registry is used to map string keys to classes or callables, with support for
    decorator-based registration and validation.

    Args:
        name: The name of the registry (for error messages).

    Example:
        >>> reg = _BaseRegistry(name='TestRegistry')
        >>> reg.register('foo', int)
        >>> reg.get('foo')
        <class 'int'>
        >>> @reg.decorator('bar')
        ... class Bar:
        ...     pass
        >>> reg.get('bar').__name__ == 'Bar'
        True
    """

    def __init__(self, *, name: str) -> None:  # noqa: D401
        super().__init__()
        self._name = name

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def register(
        self, key: str, obj: _T, *, overwrite: bool = False
    ) -> None:  # noqa: D401
        """Register an object under a key.

        Args:
            key: Alias string or identifier.
            obj: Class or callable to map.
            overwrite: Whether to overwrite an existing entry.

        Raises:
            KeyError: If the key is already registered and overwrite is False.
        """
        if not overwrite and key in self:
            raise KeyError(
                f"{self._name}: key '{key}' already registered to {self[key]}."
            )
        logger.debug("%s: registering key '%s' → %s", self._name, key, obj)
        self[key] = obj

    def decorator(self, key: str) -> Callable[[_T], _T]:  # noqa: D401
        """Return a class decorator that registers the decorated object.

        Args:
            key: The key to register the class under.

        Returns:
            Callable: A decorator that registers the class.

        Example:
            >>> reg = _BaseRegistry(name='TestRegistry')
            >>> @reg.decorator('foo')
            ... class Foo:
            ...     pass
            >>> reg.get('foo').__name__ == 'Foo'
            True
        """

        def _decorator(obj: _T) -> _T:  # noqa: D401
            self.register(key, obj, overwrite=True)
            return obj

        return _decorator

    # Convenience wrappers ---------------------------------------------------
    def get(self, key: str) -> _T:  # type: ignore[override]
        """Get the object registered under key.

        Args:
            key: The key to look up.

        Returns:
            The registered object.

        Raises:
            KeyError: If the key is not found.
        """
        try:
            return super().__getitem__(key)
        except KeyError:  # pragma: no cover
            raise KeyError(
                f"{self._name}: unknown key '{key}'. Available: {sorted(self.keys())}"  # noqa: E501
            ) from None

    def list(self) -> List[str]:  # noqa: D401
        """Return a sorted list of registered keys.

        Returns:
            List[str]: Sorted list of keys.
        """

        return sorted(self.keys())

    # Hide mutating dict API methods to discourage direct use ---------------
    def __delitem__(self, __key: str) -> None:  # noqa: D401
        """Prevent deletion of registry items at runtime.

        Raises:
            RuntimeError: Always raised to prevent deletion.
        """
        raise RuntimeError("Registry items cannot be deleted at runtime.")


# ---------------------------------------------------------------------------
# Concrete registries – created eagerly so decorators work at import time
# ---------------------------------------------------------------------------

CalculationAliasRegistry: _BaseRegistry[Any] = _BaseRegistry(
    name="CalculationAliasRegistry"
)
NodeTypeRegistry: _BaseRegistry[Any] = _BaseRegistry(name="NodeTypeRegistry")
ForecastTypeRegistry: _BaseRegistry[Any] = _BaseRegistry(name="ForecastTypeRegistry")

# ---------------------------------------------------------------------------
# Decorator helpers re-exported for convenience
# ---------------------------------------------------------------------------
calc_alias: Callable[[str], Callable[[Any], Any]] = CalculationAliasRegistry.decorator
node_type: Callable[[str], Callable[[Any], Any]] = NodeTypeRegistry.decorator
forecast_type: Callable[[str], Callable[[Any], Any]] = ForecastTypeRegistry.decorator

__all__: list[str] = [
    "CalculationAliasRegistry",
    "NodeTypeRegistry",
    "ForecastTypeRegistry",
    "calc_alias",
    "node_type",
    "forecast_type",
]
