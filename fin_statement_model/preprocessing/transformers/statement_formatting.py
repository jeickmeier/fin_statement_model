"""Financial data transformer for the Financial Statement Model.

This module provides the StatementFormattingTransformer for formatting financial statements:
adding subtotals, applying sign conventions, and reordering line items.
"""

import pandas as pd
import yaml
import importlib.resources
from typing import Optional, Union, ClassVar
import logging

from fin_statement_model.preprocessing.base_transformer import DataTransformer
from fin_statement_model.preprocessing.types import StatementFormattingConfig
from fin_statement_model.preprocessing.enums import StatementType

# Configure logging
logger = logging.getLogger(__name__)

class StatementFormattingTransformer(DataTransformer):
    """Transformer for formatting financial statements.

    This transformer can:
    - Add subtotals and totals
    - Reorder line items according to standard formats
    - Apply sign conventions (negative expenses, etc.)
    """

    # Load standard orderings from YAML configuration
    DEFAULT_ORDERS: ClassVar[dict[str, list[str]]] = {}

    @classmethod
    def _load_standard_orders(cls) -> None:
        """Load standard order configurations from YAML file into DEFAULT_ORDERS."""
        # Load the YAML from the preprocessing config directory
        try:
            # Use importlib.resources for robust package data loading
            yaml_content = importlib.resources.files("fin_statement_model.preprocessing.config").joinpath("statement_standard_orders.yaml").read_text(encoding="utf-8")
            cls.DEFAULT_ORDERS = yaml.safe_load(yaml_content)
        except FileNotFoundError:
            logger.error("Default statement order file not found.", exc_info=True)
            # Keep DEFAULT_ORDERS as empty dict if file is missing
        except Exception as e:
            logger.error(f"Error loading default statement order file: {e}", exc_info=True)
            # Keep DEFAULT_ORDERS as empty dict on other errors

    def __init__(
        self,
        statement_type: Union[str, StatementType] = StatementType.INCOME_STATEMENT,
        add_subtotals: bool = True,
        apply_sign_convention: bool = True,
        config: Optional[StatementFormattingConfig] = None,
    ):
        """Initialize the statement formatting transformer.

        Args:
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            add_subtotals: Whether to add standard subtotals
            apply_sign_convention: Whether to apply standard sign conventions
            config: Additional configuration options
        """
        super().__init__(config)
        # Normalize enum to string
        if isinstance(statement_type, StatementType):
            stype = statement_type.value
        else:
            stype = statement_type
        if stype not in [t.value for t in StatementType]:
            raise ValueError(
                f"Invalid statement type: {stype}. Must be one of {[t.value for t in StatementType]}"
            )
        self.statement_type = stype
        self.add_subtotals = add_subtotals
        self.apply_sign_convention = apply_sign_convention

        # Define standard orderings for different statement types
        self.item_order = self._get_standard_order()

    def _get_standard_order(self) -> list[str]:
        """Get the standard ordering of items for the current statement type."""
        return list(self.DEFAULT_ORDERS.get(self.statement_type, []))

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Format a financial statement DataFrame.

        Args:
            data: DataFrame containing financial statement data

        Returns:
            Formatted DataFrame
        """
        result = data.copy()

        if self.apply_sign_convention:
            result = self._apply_sign_convention(result)

        if self.add_subtotals:
            result = self._add_subtotals(result)

        result = self._reorder_items(result)

        return result

    def _apply_sign_convention(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard sign conventions to line items."""
        result = df.copy()
        negative_items: list[str] = []

        if self.statement_type == "income_statement":
            negative_items = [
                "cost_of_goods_sold",
                "operating_expenses",
                "interest_expense",
                "income_tax",
            ]

        elif self.statement_type == "cash_flow":
            negative_items = [
                "capital_expenditures",
                "investments",
                "debt_repayment",
                "dividends",
                "share_repurchases",
            ]

        for item in negative_items:
            if item in result.index:
                result.loc[item] = (
                    result.loc[item] * -1 if result.loc[item].mean() > 0 else result.loc[item]
                )

        return result

    def _add_subtotals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add standard subtotals to the statement."""
        result = df.copy()

        if self.statement_type == "income_statement":
            if (
                "revenue" in result.index
                and "cost_of_goods_sold" in result.index
                and "gross_profit" not in result.index
            ):
                result.loc["gross_profit"] = (
                    result.loc["revenue"] + result.loc["cost_of_goods_sold"]
                )

            if (
                "gross_profit" in result.index
                and "operating_expenses" in result.index
                and "operating_income" not in result.index
            ):
                result.loc["operating_income"] = (
                    result.loc["gross_profit"] + result.loc["operating_expenses"]
                )

            if (
                "operating_income" in result.index
                and "interest_expense" in result.index
                and "income_before_taxes" not in result.index
            ):
                result.loc["income_before_taxes"] = (
                    result.loc["operating_income"] + result.loc["interest_expense"]
                )

            if (
                "income_before_taxes" in result.index
                and "income_tax" in result.index
                and "net_income" not in result.index
            ):
                result.loc["net_income"] = (
                    result.loc["income_before_taxes"] + result.loc["income_tax"]
                )

        elif self.statement_type == "balance_sheet":
            current_assets = [
                "cash_and_equivalents",
                "short_term_investments",
                "accounts_receivable",
                "inventory",
            ]
            if (
                any(item in result.index for item in current_assets)
                and "current_assets" not in result.index
            ):
                result.loc["current_assets"] = sum(
                    result.loc[item] for item in current_assets if item in result.index
                )

            if (
                "current_assets" in result.index
                and "property_plant_equipment" in result.index
                and "total_assets" not in result.index
            ):
                result.loc["total_assets"] = (
                    result.loc["current_assets"] + result.loc["property_plant_equipment"]
                )

            current_liabilities = ["accounts_payable", "short_term_debt"]
            if (
                any(item in result.index for item in current_liabilities)
                and "current_liabilities" not in result.index
            ):
                result.loc["current_liabilities"] = sum(
                    result.loc[item] for item in current_liabilities if item in result.index
                )

            if (
                "current_liabilities" in result.index
                and "long_term_debt" in result.index
                and "total_liabilities" not in result.index
            ):
                result.loc["total_liabilities"] = (
                    result.loc["current_liabilities"] + result.loc["long_term_debt"]
                )

            equity_items = ["common_stock", "retained_earnings"]
            if (
                any(item in result.index for item in equity_items)
                and "total_equity" not in result.index
            ):
                result.loc["total_equity"] = sum(
                    result.loc[item] for item in equity_items if item in result.index
                )  # pragma: no cover

            if (
                "total_liabilities" in result.index
                and "total_equity" in result.index
                and "total_liabilities_and_equity" not in result.index
            ):
                result.loc["total_liabilities_and_equity"] = (
                    result.loc["total_liabilities"] + result.loc["total_equity"]
                )  # pragma: no cover

        elif self.statement_type == "cash_flow":
            operating_items = [
                "net_income",
                "depreciation_amortization",
                "changes_in_working_capital",
            ]
            if (
                any(item in result.index for item in operating_items)
                and "cash_from_operating_activities" not in result.index
            ):
                result.loc["cash_from_operating_activities"] = sum(
                    result.loc[item] for item in operating_items if item in result.index
                )

            investing_items = ["capital_expenditures", "investments"]
            if (
                any(item in result.index for item in investing_items)
                and "cash_from_investing_activities" not in result.index
            ):
                result.loc["cash_from_investing_activities"] = sum(
                    result.loc[item] for item in investing_items if item in result.index
                )

            financing_items = [
                "debt_issuance",
                "debt_repayment",
                "dividends",
                "share_repurchases",
            ]
            if (
                any(item in result.index for item in financing_items)
                and "cash_from_financing_activities" not in result.index
            ):
                result.loc["cash_from_financing_activities"] = sum(
                    result.loc[item] for item in financing_items if item in result.index
                )

            cash_flow_categories = [
                "cash_from_operating_activities",
                "cash_from_investing_activities",
                "cash_from_financing_activities",
            ]
            if (
                any(item in result.index for item in cash_flow_categories)
                and "net_change_in_cash" not in result.index
            ):
                result.loc["net_change_in_cash"] = sum(
                    result.loc[item] for item in cash_flow_categories if item in result.index
                )

        return result

    def _reorder_items(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorder the DataFrame according to standard financial statement ordering."""
        ordered_items = [item for item in self.item_order if item in df.index]
        ordered_items.extend([item for item in df.index if item not in self.item_order])
        return df.loc[ordered_items]

# After class definition, load standard orders
StatementFormattingTransformer._load_standard_orders()
