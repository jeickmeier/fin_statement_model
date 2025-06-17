"""Calculation‐related public helpers (metrics, custom calculations, etc.)."""

from __future__ import annotations

from typing import Any, Callable, Optional

__all__: list[str] = ["CalcOpsMixin"]


class CalcOpsMixin:
    """Thin façade methods delegating to the internal :class:`CalculationEngine`."""

    # ---------------------------------------------------------------------
    # Calculation node helpers
    # ---------------------------------------------------------------------
    def add_calculation(
        self,
        name: str,
        input_names: list[str],
        operation_type: str,
        formula_variable_names: Optional[list[str]] = None,
        **calculation_kwargs: Any,
    ) -> Any:
        return self._calc_engine.add_calculation(  # type: ignore[attr-defined]
            name,
            input_names,
            operation_type,
            formula_variable_names=formula_variable_names,
            **calculation_kwargs,
        )

    def add_metric(
        self,
        metric_name: str,
        node_name: Optional[str] = None,
        *,
        input_node_map: Optional[dict[str, str]] = None,
    ) -> Any:
        return self._calc_engine.add_metric(  # type: ignore[attr-defined]
            metric_name,
            node_name,
            input_node_map=input_node_map,
        )

    def add_custom_calculation(
        self,
        name: str,
        calculation_func: Callable[..., float],
        inputs: Optional[list[str]] = None,
        description: str = "",
    ) -> Any:
        return self._calc_engine.add_custom_calculation(  # type: ignore[attr-defined]
            name,
            calculation_func,
            inputs,
            description,
        )

    def ensure_signed_nodes(
        self, base_node_ids: list[str], *, suffix: str = "_signed"
    ) -> Any:
        return self._calc_engine.ensure_signed_nodes(  # type: ignore[attr-defined]
            base_node_ids, suffix=suffix
        )

    def change_calculation_method(
        self,
        node_name: str,
        new_method_key: str,
        **kwargs: dict[str, Any],
    ) -> None:
        self._calc_engine.change_calculation_method(  # type: ignore[attr-defined]
            node_name,
            new_method_key,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Calculation execution / cache interaction
    # ------------------------------------------------------------------
    def calculate(self, node_name: str, period: str) -> Any:
        return self._calc_engine.calculate(node_name, period)  # type: ignore[attr-defined]

    def recalculate_all(self, periods: Optional[list[str]] = None) -> None:
        self._calc_engine.recalc_all(periods)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Metric inspection helpers
    # ------------------------------------------------------------------
    def get_metric(self, metric_id: str) -> Any:
        return self._calc_engine.get_metric(metric_id)  # type: ignore[attr-defined]

    def get_available_metrics(self) -> Any:
        return self._calc_engine.get_available_metrics()  # type: ignore[attr-defined]

    def get_metric_info(self, metric_id: str) -> Any:
        return self._calc_engine.get_metric_info(metric_id)  # type: ignore[attr-defined]
