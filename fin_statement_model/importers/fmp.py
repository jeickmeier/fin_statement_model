"""
Financial Modeling Prep API adapter.

This module provides an adapter for fetching financial data from the Financial Modeling Prep API
and converting it to a format compatible with the financial statement model.
"""

import requests
from typing import Dict, List, Any
import pandas as pd
import logging

from .adapter_base import APIDataSourceAdapter
from ..core.financial_statement import FinancialStatementGraph

# Configure logging
logger = logging.getLogger(__name__)


class FMPAdapter(APIDataSourceAdapter):
    """
    Financial Modeling Prep API adapter for fetching financial statement data
    and converting it to FinancialStatementGraph format.

    This adapter implements the APIDataSourceAdapter interface, providing a consistent
    way to fetch and process financial data from the FMP API.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the FMP adapter.

        Args:
            api_key: FMP API key. If None, the adapter will attempt to use an environment variable.
        """
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # Auto-authenticate if API key is provided
        if self.api_key:
            self.authenticate()

        # Initialize mapping dictionaries
        self._init_field_mappings()

    def _init_field_mappings(self) -> None:
        """Initialize the field mapping dictionaries for different statement types."""
        # Income statement mappings
        self.income_statement_field_mapping = {
            "revenue": "revenue",
            "costOfRevenue": "cost_of_goods_sold",
            "grossProfit": "gross_profit",
            "grossProfitRatio": "gross_profit_ratio",
            "researchAndDevelopmentExpenses": "research_and_development_expenses",
            "generalAndAdministrativeExpenses": "general_and_administrative_expenses",
            "sellingAndMarketingExpenses": "selling_and_marketing_expenses",
            "sellingGeneralAndAdministrativeExpenses": "selling_general_and_administrative_expenses",
            "otherExpenses": "other_interest_expenses",
            "operatingExpenses": "operating_expenses",
            "operatingIncome": "operating_income",
            "interestIncome": "interest_income",
            "interestExpense": "interest_expense",
            "incomeBeforeTax": "income_before_tax",
            "incomeTaxExpense": "tax_expense",
            #"netIncome": "net_income",
            #"depreciationAndAmortization": "depreciation_and_amortization",
            "ebitda": "ebitda",
            "eps": "eps",
            "epsDiluted": "eps_diluted",
        }

        # Balance sheet mappings
        self.balance_sheet_field_mapping = {
            "cashAndCashEquivalents": "cash_and_cash_equivalents",
            "shortTermInvestments": "short_term_investments",
            "netReceivables": "net_receivables",
            "accountsReceivables": "accounts_receivables",
            "otherReceivables": "other_receivables",
            #"inventory": "inventory",
            "prepaids": "prepaids",
            "otherCurrentAssets": "other_current_assets",
            "totalCurrentAssets": "total_current_assets",
            "propertyPlantEquipmentNet": "property_plant_equipment_net",
            "goodwill": "goodwill",
            "intangibleAssets": "intangible_assets",
            "goodwillAndIntangibleAssets": "goodwill_and_intangible_assets",
            "longTermInvestments": "long_term_investments",
            "taxAssets": "tax_assets",
            "otherNonCurrentAssets": "other_non_current_assets",
            "totalNonCurrentAssets": "total_non_current_assets",
            "otherAssets": "other_assets",
            "totalAssets": "total_assets",
            "totalPayables": "total_payables",
            #"accountPayables": "account_payables",
            "otherPayables": "other_payables",
            "accruedExpenses": "accrued_expenses",
            "shortTermDebt": "short_term_debt",
            "capitalLeaseObligationsCurrent": "capital_lease_obligations_current",
            "taxPayables": "tax_payables",
            "deferredRevenue": "deferred_revenue",
            "otherCurrentLiabilities": "other_current_liabilities",
            "totalCurrentLiabilities": "total_current_liabilities",
            "longTermDebt": "long_term_debt",
            "deferredRevenueNonCurrent": "deferred_revenue_non_current",
            "deferredTaxLiabilitiesNonCurrent": "deferred_tax_liabilities_non_current",
            "otherNonCurrentLiabilities": "other_non_current_liabilities",
            "totalNonCurrentLiabilities": "total_non_current_liabilities",
            "otherLiabilities": "other_liabilities",
            "capitalLeaseObligations": "capital_lease_obligations",
            "totalLiabilities": "total_liabilities",
            "treasuryStock": "treasury_stock",
            "preferredStock": "preferred_stock",
            "commonStock": "common_stock",
            "retainedEarnings": "retained_earnings",
            "additionalPaidInCapital": "additional_paid_in_capital",
            "accumulatedOtherComprehensiveIncomeLoss": "accumulated_other_comprehensive_income_loss",
            "otherTotalStockholdersEquity": "other_total_stockholders_equity",
            "totalStockholdersEquity": "total_stockholders_equity",
            "totalEquity": "total_equity",
            "totalLiabilitiesAndStockholdersEquity": "total_liabilities_and_stockholders_equity",
        }

        # Cash flow mappings
        self.cash_flow_field_mapping = {
            "netIncome": "net_income",
            "depreciationAndAmortization": "depreciation_and_amortization",
            "stockBasedCompensation": "stock_based_compensation",
            "changeInWorkingCapital": "change_in_working_capital",
            "accountsReceivables": "accounts_receivables",
            "inventory": "inventory",
            "accountsPayables": "account_payables",
            "otherWorkingCapital": "other_working_capital",
            "otherNonCashItems": "other_non_cash_items",
            # "netCashProvidedByOperatingActivities": "operating_cash_flow",
            "investmentsInPropertyPlantAndEquipment": "investments_in_property_plant_and_equipment",
            "acquisitionsNet": "acquisitions_net",
            "purchasesOfInvestments": "purchases_of_investments",
            "salesMaturitiesOfInvestments": "sales_maturities_of_investments",
            "otherInvestingActivites": "other_investing_activities",
            "netCashUsedForInvestingActivites": "investing_cash_flow",
            "debtRepayment": "debt_repayment",
            "commonStockIssued": "common_stock_issued",
            "commonStockRepurchased": "common_stock_repurchased",
            "dividendsPaid": "dividends_paid",
            "otherFinancingActivites": "other_financing_activities",
            "netCashUsedProvidedByFinancingActivities": "financing_cash_flow",
            "effectOfForexChangesOnCash": "effect_of_forex_changes_on_cash",
            "netChangeInCash": "net_change_in_cash",
            "cashAtEndOfPeriod": "cash_at_end_of_period",
            "cashAtBeginningOfPeriod": "cash_at_beginning_of_period",
            "operatingCashFlow": "operating_cash_flow",
            "capitalExpenditure": "capital_expenditure",
            "freeCashFlow": "free_cash_flow",
        }

    def authenticate(self) -> bool:
        """
        Authenticate with the FMP API.

        Returns:
            bool: True if authentication was successful, False otherwise

        Raises:
            ValueError: If no API key is provided and none can be found in environment variables
        """
        if not self.api_key:
            # Try to get from environment variable
            import os

            self.api_key = os.environ.get("FMP_API_KEY")

            if not self.api_key:
                raise ValueError(
                    "No API key provided. Please provide an API key or set the FMP_API_KEY environment variable."
                )

        # Test the API key with a simple request
        try:
            url = f"{self.base_url}/stock/list?apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.error(
                    f"Authentication failed with status code {response.status_code}"
                )
                return False

            logger.info("Successfully authenticated with FMP API")
            return True

        except Exception as e:
            logger.error(f"Error authenticating with FMP API: {e}")
            return False

    def validate_response(self, response: Any) -> bool:
        """
        Validate that the API response is valid.

        Args:
            response: Raw API response

        Returns:
            bool: True if the response is valid, False otherwise
        """
        if not isinstance(response, list):
            logger.error("Expected list response from FMP API")
            return False

        if len(response) == 0:
            logger.warning("Empty response from FMP API")
            return False

        # Check if response has expected fields
        first_item = response[0]
        expected_fields = ["date"]
        for field in expected_fields:
            if field not in first_item:
                logger.error(f"Response missing expected field: {field}")
                return False

        return True

    def fetch_statement(
        self,
        identifier: str,
        period_type: str = "FY",
        limit: int = 50,
        statement_type: str = "income_statement",
    ) -> Dict:
        """
        Fetch financial statement data from FMP API.

        Args:
            identifier: Ticker symbol (e.g., 'AAPL')
            period_type: 'FY' for fiscal year or 'QTR' for quarter
            limit: Maximum number of periods to fetch
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')

        Returns:
            Dict: Raw financial statement data from FMP

        Raises:
            ValueError: If the statement type is invalid
            ValueError: If the API request fails
        """
        # Validate statement type
        valid_statement_types = ["income_statement", "balance_sheet", "cash_flow"]
        if statement_type not in valid_statement_types:
            raise ValueError(
                f"Invalid statement type: {statement_type}. Valid types are: {valid_statement_types}"
            )

        # Map statement type to API endpoint
        endpoint_mapping = {
            "income_statement": "income-statement",
            "balance_sheet": "balance-sheet-statement",
            "cash_flow": "cash-flow-statement",
        }

        # Build the API URL
        endpoint = endpoint_mapping[statement_type]
        url = f"{self.base_url}/{endpoint}/{identifier}?apikey={self.api_key}&period={period_type}&limit={limit}"

        logger.debug(f"Fetching {statement_type} for {identifier} from FMP API")

        try:
            # Make the API request
            response = requests.get(url, timeout=10)

            # Check for success
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch data: HTTP {response.status_code}")

            # Parse the response
            data = response.json()

            # Validate the response
            if not self.validate_response(data):
                raise ValueError("Invalid response from FMP API")

            logger.debug(
                f"Successfully fetched {len(data)} periods of {statement_type} data for {identifier}"
            )
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from FMP API: {e}")
            raise ValueError(f"Error fetching data from FMP API: {e}")
        except Exception as e:
            logger.error(f"Error fetching data from FMP API: {e}")
            raise ValueError(f"Error fetching data from FMP API: {e}")

    def get_field_mapping(self, statement_type: str) -> Dict[str, str]:
        """
        Get the mapping of FMP field names to standardized node names.

        Args:
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')

        Returns:
            Dict[str, str]: Mapping of FMP field names to standardized node names

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
        identifier: str,
        statement_type: str = "income_statement",
        period_type: str = "FY",
        limit: int = 50,
    ) -> FinancialStatementGraph:
        """
        Create a FinancialStatementGraph from FMP financial statement data.

        Args:
            identifier: Ticker symbol (e.g., 'AAPL')
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            period_type: 'FY' for fiscal year or 'QTR' for quarter
            limit: Maximum number of periods to fetch

        Returns:
            FinancialStatementGraph: Graph containing the financial statement data

        Raises:
            ValueError: If there's an issue fetching or processing the data
        """
        try:
            # Fetch raw data
            data = self.fetch_statement(identifier, period_type, limit, statement_type)

            # Get the field mapping for this statement type
            mapping = self.get_field_mapping(statement_type)

            # Extract periods
            periods = []
            for statement in data:
                date = statement["date"]  # type: ignore
                if period_type == "FY":
                    period_label = f"FY{date[:4]}"
                else:
                    quarter = pd.Timestamp(date).quarter
                    period_label = f"{date[:4]}Q{quarter}"
                periods.append(period_label)
            periods = sorted(list(set(periods)))

            # Initialize graph
            fsg = FinancialStatementGraph(periods=periods)

            # Process each mapped field
            for fmp_field, node_name in mapping.items():
                values = {}
                for statement in data:
                    date = statement["date"]  # type: ignore
                    if period_type == "FY":
                        period_label = f"FY{date[:4]}"
                    else:
                        quarter = pd.Timestamp(date).quarter
                        period_label = f"{date[:4]}Q{quarter}"

                    if fmp_field in statement:
                        value = statement[fmp_field]  # type: ignore
                        if value is not None:
                            values[period_label] = float(value)

                if values:  # Only add node if we have values
                    fsg.add_financial_statement_item(node_name, values)

            # Add common calculations based on statement type
            self._add_common_calculations(fsg, statement_type)

            logger.info(
                f"Created {statement_type} graph for {identifier} with {len(fsg.graph.nodes)} nodes"
            )
            return fsg

        except Exception as e:
            logger.error(f"Error creating statement graph for {identifier}: {e}")
            raise ValueError(f"Error creating statement graph for {identifier}: {e}")

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

                self._try_add_calculation(
                    fsg,
                    "total_current_assets",
                    [
                        "cash_and_cash_equivalents",
                        "short_term_investments",
                        "net_receivables",
                        "accounts_receivables",
                        "other_receivables",
                        "inventory",
                        "prepaids",
                        "other_current_assets",
                    ],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_non_current_assets",
                    [
                        "property_plant_equipment_net",
                        "goodwill",
                        "intangible_assets",
                        "goodwill_and_intangible_assets",
                        "long_term_investments",
                        "tax_assets",
                        "other_non_current_assets",
                    ],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_assets",
                    ["total_current_assets", "total_non_current_assets"],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_current_liabilities",
                    [
                        "account_payables",
                        "short_term_debt",
                        "deferred_revenue",
                        "tax_payables",
                        "accrued_expenses",
                        "other_current_liabilities",
                    ],
                    "addition",
                )

                self._try_add_calculation(
                    fsg,
                    "total_non_current_liabilities",
                    [
                        "long_term_debt",
                        "deferred_revenue_non_current",
                        "deferred_tax_liabilities_non_current",
                        "other_non_current_liabilities",
                    ],
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
                    "total_equity",
                    [
                        "common_stock",
                        "retained_earnings",
                        "treasury_stock",
                        "additional_paid_in_capital",
                        "accumulated_other_comprehensive_income_loss",
                    ],
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

    def create_all_statements_graph(
        self,
        identifier: str,
        period_type: str = "FY",
        limit: int = 50,
    ) -> FinancialStatementGraph:
        """
        Create a FinancialStatementGraph containing all financial statements (income, balance sheet, and cash flow).

        Args:
            identifier: Ticker symbol (e.g., 'AAPL')
            period_type: 'FY' for fiscal year or 'QTR' for quarter
            limit: Maximum number of periods to fetch

        Returns:
            FinancialStatementGraph: Graph containing all financial statement data

        Raises:
            ValueError: If there's an issue fetching or processing the data
        """
        try:
            # Create individual statement graphs
            income_graph = self.create_statement_graph(
                identifier, "income_statement", period_type, limit
            )
            balance_graph = self.create_statement_graph(
                identifier, "balance_sheet", period_type, limit
            )
            cash_flow_graph = self.create_statement_graph(
                identifier, "cash_flow", period_type, limit
            )

            # Get the periods from any of the graphs (they should all have the same periods)
            periods = income_graph.graph._periods

            # Create a new combined graph
            combined_graph = FinancialStatementGraph(periods=periods)

            # Add all nodes from each graph to the combined graph
            for graph in [income_graph, balance_graph, cash_flow_graph]:
                for node_name, node in graph.graph.nodes.items():
                    if hasattr(node, 'values'):
                        combined_graph.add_financial_statement_item(
                            node_name, node.values
                        )

            # Add cross-statement calculations
            self._add_cross_statement_calculations(combined_graph)

            logger.info(
                f"Created combined financial statements graph for {identifier} with {len(combined_graph.graph.nodes)} nodes"
            )
            return combined_graph

        except Exception as e:
            logger.error(f"Error creating combined statements graph for {identifier}: {e}")
            raise ValueError(f"Error creating combined statements graph for {identifier}: {e}")

    def _add_cross_statement_calculations(self, fsg: FinancialStatementGraph) -> None:
        """
        Add calculations that combine items from different financial statements.

        Args:
            fsg: Financial statement graph to add calculations to
        """
        try:
            # Return on Assets (ROA)
            self._try_add_calculation(
                fsg,
                "return_on_assets",
                ["net_income", "total_assets"],
                "division"
            )

            # Return on Equity (ROE)
            self._try_add_calculation(
                fsg,
                "return_on_equity",
                ["net_income", "total_equity"],
                "division"
            )

            # Asset Turnover
            self._try_add_calculation(
                fsg,
                "asset_turnover",
                ["revenue", "total_assets"],
                "division"
            )

            # Operating Cash Flow Ratio
            self._try_add_calculation(
                fsg,
                "operating_cash_flow_ratio",
                ["operating_cash_flow", "total_current_liabilities"],
                "division"
            )

            # Free Cash Flow to Revenue
            self._try_add_calculation(
                fsg,
                "free_cash_flow_to_revenue",
                ["free_cash_flow", "revenue"],
                "division"
            )

        except Exception as e:
            logger.warning(f"Error adding cross-statement calculations: {e}")
