"""
Excel file adapter.

This module provides an adapter for importing financial data from Excel files
and converting it to a format compatible with the financial statement model.
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Optional

from .adapter_base import FileDataSourceAdapter
from ..core.financial_statement import FinancialStatementGraph

# Configure logging
logger = logging.getLogger(__name__)


class ExcelAdapter(FileDataSourceAdapter):
    """
    Excel adapter for importing financial statement data from Excel files
    and converting it to FinancialStatementGraph format.

    This adapter implements the FileDataSourceAdapter interface, providing a consistent
    way to import and process financial data from Excel files.
    """

    def __init__(self, mapping_config: Optional[Dict] = None):
        """
        Initialize the Excel adapter.

        Args:
            mapping_config: Optional mapping configuration to override default field mappings.
                           If None, default mappings will be used.
        """
        self.file_path = None
        self.sheet_name = None
        self.period_column = None
        self.data = None

        # Initialize mapping with defaults or provided config
        self._init_field_mappings(mapping_config)

    def _init_field_mappings(self, mapping_config: Optional[Dict] = None) -> None:
        """Initialize the field mapping dictionaries for different statement types."""
        # Default field mappings (can be overridden)
        self.income_statement_field_mapping = {
            "Revenue": "revenue",
            "Cost of Revenue": "cost_of_goods_sold",
            "Gross Profit": "gross_profit",
            "R&D Expenses": "research_and_development_expenses",
            "G&A Expenses": "general_and_administrative_expenses",
            "S&M Expenses": "selling_and_marketing_expenses",
            "SG&A": "selling_general_and_administrative_expenses",
            "Operating Expenses": "operating_expenses",
            "Operating Income": "operating_income",
            "Interest Income": "interest_income",
            "Interest Expense": "interest_expense",
            "Income Before Tax": "income_before_tax",
            "Tax Expense": "tax_expense",
            "Net Income": "net_income",
            "Depreciation & Amortization": "depreciation_and_amortization",
            "EBITDA": "ebitda",
            "EPS": "eps",
            "EPS Diluted": "eps_diluted",
        }

        self.balance_sheet_field_mapping = {
            "Cash & Cash Equivalents": "cash_and_cash_equivalents",
            "Short-term Investments": "short_term_investments",
            "Accounts Receivable": "accounts_receivables",
            "Inventory": "inventory",
            "Other Current Assets": "other_current_assets",
            "Total Current Assets": "total_current_assets",
            "Property, Plant & Equipment": "property_plant_equipment_net",
            "Goodwill": "goodwill",
            "Intangible Assets": "intangible_assets",
            "Long-term Investments": "long_term_investments",
            "Other Non-Current Assets": "other_non_current_assets",
            "Total Non-Current Assets": "total_non_current_assets",
            "Total Assets": "total_assets",
            "Accounts Payable": "account_payables",
            "Short-term Debt": "short_term_debt",
            "Deferred Revenue": "deferred_revenue",
            "Other Current Liabilities": "other_current_liabilities",
            "Total Current Liabilities": "total_current_liabilities",
            "Long-term Debt": "long_term_debt",
            "Other Non-Current Liabilities": "other_non_current_liabilities",
            "Total Non-Current Liabilities": "total_non_current_liabilities",
            "Total Liabilities": "total_liabilities",
            "Common Stock": "common_stock",
            "Retained Earnings": "retained_earnings",
            "Treasury Stock": "treasury_stock",
            "Additional Paid-in Capital": "additional_paid_in_capital",
            "Total Stockholders' Equity": "total_stockholders_equity",
            "Total Equity": "total_equity",
            "Total Liabilities & Equity": "total_liabilities_and_stockholders_equity",
        }

        self.cash_flow_field_mapping = {
            "Net Income": "net_income",
            "Depreciation & Amortization": "depreciation_and_amortization",
            "Change in Working Capital": "change_in_working_capital",
            "Operating Cash Flow": "operating_cash_flow",
            "Capital Expenditures": "capital_expenditure",
            "Acquisitions": "acquisitions_net",
            "Investing Cash Flow": "investing_cash_flow",
            "Debt Repayment": "debt_repayment",
            "Stock Issuance": "common_stock_issued",
            "Stock Repurchase": "common_stock_repurchased",
            "Dividends Paid": "dividends_paid",
            "Financing Cash Flow": "financing_cash_flow",
            "Net Change in Cash": "net_change_in_cash",
            "Free Cash Flow": "free_cash_flow",
        }

        # Override with provided mapping config if any
        if mapping_config:
            if "income_statement" in mapping_config:
                self.income_statement_field_mapping.update(
                    mapping_config["income_statement"]
                )
            if "balance_sheet" in mapping_config:
                self.balance_sheet_field_mapping.update(mapping_config["balance_sheet"])
            if "cash_flow" in mapping_config:
                self.cash_flow_field_mapping.update(mapping_config["cash_flow"])

    def validate_file(self, file_path: str) -> bool:
        """
        Validate that the provided file is a valid Excel file with required structure.

        Args:
            file_path: Path to the Excel file to validate

        Returns:
            bool: True if the file is valid, False otherwise

        Raises:
            ValueError: If the file is not a valid Excel file
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise ValueError(f"File not found: {file_path}")

        if not file_path.endswith((".xls", ".xlsx", ".xlsm")):
            logger.error(f"Not an Excel file: {file_path}")
            raise ValueError(f"Not an Excel file: {file_path}")

        try:
            # Try to read the file
            pd.ExcelFile(file_path)
            logger.info(f"Successfully validated Excel file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error validating Excel file: {e}")
            raise ValueError(f"Error validating Excel file: {e}")

    def extract_time_periods(
        self, file_path: str, sheet_name: str, period_column: str
    ) -> List[str]:
        """
        Extract time periods from the Excel file.

        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet containing the data
            period_column: Name of the column containing period identifiers

        Returns:
            List[str]: List of period identifiers

        Raises:
            ValueError: If periods cannot be extracted
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            if period_column not in df.columns:
                raise ValueError(f"Period column '{period_column}' not found in sheet")

            periods = sorted(df[period_column].unique().tolist())
            logger.info(f"Extracted {len(periods)} time periods from Excel file")
            return periods

        except Exception as e:
            logger.error(f"Error extracting time periods: {e}")
            raise ValueError(f"Error extracting time periods: {e}")

    def fetch_statement(
        self,
        file_path: str,
        sheet_name: str,
        period_column: str,
        statement_type: str = "income_statement",
    ) -> Dict:
        """
        Fetch financial statement data from Excel file.

        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet containing the data
            period_column: Name of the column containing period identifiers
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')

        Returns:
            Dict: Raw financial statement data

        Raises:
            ValueError: If the statement type is invalid
            ValueError: If the data cannot be read from the Excel file
        """
        # Validate statement type
        valid_statement_types = ["income_statement", "balance_sheet", "cash_flow"]
        if statement_type not in valid_statement_types:
            raise ValueError(
                f"Invalid statement type: {statement_type}. Valid types are: {valid_statement_types}"
            )

        # Validate file
        self.validate_file(file_path)

        # Store parameters for reuse
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.period_column = period_column

        try:
            # Read data
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            # Store data for reuse
            self.data = df

            # Convert to dict format similar to API response
            data_dict = {}
            for _, row in df.iterrows():
                item_name = row.get("Item", None)
                if item_name:
                    data_dict[item_name] = {
                        period: row.get(period, None)
                        for period in df.columns
                        if period != "Item" and period != period_column
                    }

            logger.info(f"Successfully fetched {statement_type} data from Excel file")
            return data_dict

        except Exception as e:
            logger.error(f"Error fetching data from Excel file: {e}")
            raise ValueError(f"Error fetching data from Excel file: {e}")

    def get_field_mapping(self, statement_type: str) -> Dict[str, str]:
        """
        Get the mapping of Excel field names to standardized node names.

        Args:
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')

        Returns:
            Dict[str, str]: Mapping of Excel field names to standardized node names

        Raises:
            ValueError: If the statement type is invalid
        """
        if statement_type == "income_statement":
            return self.income_statement_field_mapping
        elif statement_type == "balance_sheet":
            return self.balance_sheet_field_mapping
        elif statement_type == "cash_flow":
            return self.cash_flow_field_mapping
        else:
            raise ValueError(f"Invalid statement type: {statement_type}")

    def create_statement_graph(
        self,
        file_path: str,
        sheet_name: str,
        period_column: str,
        statement_type: str = "income_statement",
    ) -> FinancialStatementGraph:
        """
        Create a FinancialStatementGraph from Excel financial statement data.

        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet containing the data
            period_column: Name of the column containing period identifiers
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')

        Returns:
            FinancialStatementGraph: Graph containing the financial statement data

        Raises:
            ValueError: If there's an issue fetching or processing the data
        """
        try:
            # Fetch raw data
            data = self.fetch_statement(
                file_path, sheet_name, period_column, statement_type
            )

            # Get the field mapping for this statement type
            mapping = self.get_field_mapping(statement_type)

            # Extract periods from the Excel file
            periods = self.extract_time_periods(file_path, sheet_name, period_column)

            # Initialize graph
            fsg = FinancialStatementGraph(periods=periods)

            # Process each mapped field
            for excel_field, node_name in mapping.items():
                values = {}

                if excel_field in data:
                    field_data = data[excel_field]
                    for period, value in field_data.items():
                        if value is not None and not pd.isna(value):
                            values[period] = float(value)

                if values:  # Only add node if we have values
                    fsg.add_financial_statement_item(node_name, values)

            # Add common calculations based on statement type
            self._add_common_calculations(fsg, statement_type)

            logger.info(
                f"Created {statement_type} graph with {len(fsg.graph.nodes)} nodes from Excel file"
            )
            return fsg

        except Exception as e:
            logger.error(f"Error creating statement graph from Excel: {e}")
            raise ValueError(f"Error creating statement graph from Excel: {e}")

    def _add_common_calculations(
        self, fsg: FinancialStatementGraph, statement_type: str
    ) -> None:
        """
        Add common calculations to the financial statement graph based on statement type.

        Args:
            fsg: Financial statement graph to add calculations to
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
        """
        try:
            if statement_type == "income_statement":
                # Add income statement calculations if nodes exist
                self._try_add_calculation(
                    fsg,
                    "gross_profit",
                    ["revenue", "cost_of_goods_sold"],
                    "subtraction",
                )
                self._try_add_calculation(
                    fsg,
                    "operating_expenses",
                    [
                        "research_and_development_expenses",
                        "general_and_administrative_expenses",
                        "selling_and_marketing_expenses",
                        "selling_general_and_administrative_expenses",
                    ],
                    "addition",
                )
                self._try_add_calculation(
                    fsg,
                    "operating_income",
                    ["gross_profit", "operating_expenses"],
                    "subtraction",
                )
                self._try_add_calculation(fsg, "ebit", ["operating_income"], "addition")
                self._try_add_calculation(
                    fsg, "ebitda", ["ebit", "depreciation_and_amortization"], "addition"
                )
                self._try_add_calculation(
                    fsg, "net_income_margin", ["net_income", "revenue"], "division"
                )

            elif statement_type == "balance_sheet":
                # Add balance sheet calculations if nodes exist
                self._try_add_calculation(
                    fsg,
                    "cash_and_short_term_investments",
                    ["cash_and_cash_equivalents", "short_term_investments"],
                    "addition",
                )

                # Additional calculations based on available nodes
                self._try_add_calculation(
                    fsg,
                    "total_assets",
                    ["total_current_assets", "total_non_current_assets"],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_liabilities",
                    ["total_current_liabilities", "total_non_current_liabilities"],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_liabilities_and_equity",
                    ["total_liabilities", "total_equity"],
                    "addition",
                )

            elif statement_type == "cash_flow":
                # Add cash flow calculations if nodes exist
                self._try_add_calculation(
                    fsg,
                    "free_cash_flow",
                    ["operating_cash_flow", "capital_expenditure"],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_cash_flow",
                    [
                        "operating_cash_flow",
                        "investing_cash_flow",
                        "financing_cash_flow",
                    ],
                    "addition",
                )

        except Exception as e:
            logger.warning(f"Error adding common calculations to {statement_type}: {e}")

    def _try_add_calculation(
        self,
        fsg: FinancialStatementGraph,
        name: str,
        inputs: List[str],
        operation_type: str,
    ) -> bool:
        """
        Try to add a calculation to the graph, handling missing inputs gracefully.

        Args:
            fsg: Financial statement graph to add calculation to
            name: Name of the calculation node
            inputs: List of input node names
            operation_type: Type of operation ('addition', 'subtraction', 'multiplication', 'division')

        Returns:
            bool: True if the calculation was added, False otherwise
        """
        # Check if all inputs exist
        available_inputs = []
        for input_name in inputs:
            if input_name in fsg.graph.nodes:
                available_inputs.append(input_name)

        # If we have at least one input, add the calculation
        if available_inputs:
            try:
                fsg.add_calculation(name, available_inputs, operation_type)
                return True
            except Exception as e:
                logger.debug(f"Error adding calculation {name}: {e}")
                return False

        return False
