"""
Import Manager for the Financial Statement Model.

This module provides functionality for importing financial data from various sources
into FinancialStatementGraph objects.
"""

import pandas as pd
import logging
from typing import Dict, Optional, List, Type

from ..core.financial_statement import FinancialStatementGraph
from ..importers.adapter_factory import AdapterFactory
from ..importers.adapter_registry import AdapterRegistry
from ..importers.adapter_base import DataSourceAdapter

# Configure logging
logger = logging.getLogger(__name__)


class ImportManager:
    """
    Manages the import of financial data from various sources.

    This class provides a unified interface for importing financial data from different
    sources such as APIs, Excel files, CSV files, and databases. It uses adapters to
    handle the specific details of each data source.
    """

    def __init__(self):
        """Initialize the ImportManager."""
        self.adapter_factory = AdapterFactory()
        self.adapter_registry = AdapterRegistry()

        # Discover available adapters
        self.adapter_factory.discover_adapters("fin_statement_model.importers")

        logger.info(
            f"ImportManager initialized with {len(self.adapter_factory.list_adapters())} available adapters"
        )

    def get_adapter(self, adapter_type: str, **kwargs) -> DataSourceAdapter:
        """
        Get or create an adapter of the specified type with the given configuration.

        Args:
            adapter_type: Type of adapter to get (e.g., 'FMPAdapter', 'ExcelAdapter')
            **kwargs: Configuration parameters for the adapter

        Returns:
            DataSourceAdapter: The requested adapter instance

        Raises:
            ValueError: If the adapter type is not registered
        """
        try:
            # Create adapter configuration hash for registry lookup
            config_hash = str(sorted([(k, v) for k, v in kwargs.items()]))
            adapter_key = f"{adapter_type}_{config_hash}"

            # Try to get existing adapter from registry
            adapter = self.adapter_registry.get(adapter_key)

            # If not found, create a new one and register it
            if not adapter:
                adapter = self.adapter_factory.create_adapter(adapter_type, **kwargs)
                self.adapter_registry.register(adapter_key, adapter)

            return adapter

        except Exception as e:
            logger.error(f"Error getting adapter {adapter_type}: {e}")
            raise ValueError(f"Error getting adapter {adapter_type}: {e}")

    def import_from_api(
        self,
        source: str,
        identifier: str,
        period_type: str = "FY",
        limit: int = 10,
        statement_type: str = "income_statement",
        **kwargs,
    ) -> FinancialStatementGraph:
        """
        Import financial data from an API source.

        Args:
            source: API source name (e.g., 'FMP' for Financial Modeling Prep)
            identifier: Identifier for the data (e.g., ticker symbol like 'AAPL')
            period_type: Period type ('FY' for fiscal year, 'QTR' for quarter)
            limit: Maximum number of periods to import
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            **kwargs: Additional parameters for the adapter

        Returns:
            FinancialStatementGraph: Graph containing the imported financial data

        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Map source name to adapter type
            adapter_type_map = {
                "FMP": "FMPAdapter",
                "Yahoo": "YahooFinanceAdapter",
                "Alpha": "AlphaVantageAdapter",
                # Add more mappings as needed
            }

            adapter_type = adapter_type_map.get(source)
            if not adapter_type:
                raise ValueError(f"Unknown API source: {source}")

            # Get the appropriate adapter
            adapter = self.get_adapter(adapter_type, **kwargs)

            # Import data using the adapter
            graph = adapter.create_statement_graph(
                identifier=identifier,
                period_type=period_type,
                limit=limit,
                statement_type=statement_type,
            )

            logger.info(
                f"Imported {statement_type} data for {identifier} from {source} API"
            )
            return graph

        except Exception as e:
            logger.error(f"Error importing data from API {source}: {e}")
            raise ValueError(f"Error importing data from API {source}: {e}")

    def import_from_excel(
        self,
        file_path: str,
        sheet_name: str,
        period_column: str,
        statement_type: str = "income_statement",
        mapping_config: Optional[Dict] = None,
    ) -> FinancialStatementGraph:
        """
        Import financial data from an Excel file.

        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet containing the data
            period_column: Name of the column containing period identifiers
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            mapping_config: Optional mapping configuration to override default field mappings

        Returns:
            FinancialStatementGraph: Graph containing the imported financial data

        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get the Excel adapter
            adapter = self.get_adapter("ExcelAdapter", mapping_config=mapping_config)

            # Import data using the adapter
            graph = adapter.create_statement_graph(
                file_path=file_path,
                sheet_name=sheet_name,
                period_column=period_column,
                statement_type=statement_type,
            )

            logger.info(f"Imported {statement_type} data from Excel file: {file_path}")
            return graph

        except Exception as e:
            logger.error(f"Error importing data from Excel file {file_path}: {e}")
            raise ValueError(f"Error importing data from Excel file {file_path}: {e}")

    def import_from_csv(
        self,
        file_path: str,
        date_column: str,
        value_column: str,
        item_column: str,
        statement_type: str = "income_statement",
        mapping_config: Optional[Dict] = None,
    ) -> FinancialStatementGraph:
        """
        Import financial data from a CSV file.

        Args:
            file_path: Path to the CSV file
            date_column: Name of the column containing dates
            value_column: Name of the column containing values
            item_column: Name of the column containing item names
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            mapping_config: Optional mapping configuration to override default field mappings

        Returns:
            FinancialStatementGraph: Graph containing the imported financial data

        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get the CSV adapter
            adapter = self.get_adapter("CSVAdapter", mapping_config=mapping_config)

            # Import data using the adapter
            graph = adapter.create_statement_graph(
                file_path=file_path,
                date_column=date_column,
                value_column=value_column,
                item_column=item_column,
                statement_type=statement_type,
            )

            logger.info(f"Imported {statement_type} data from CSV file: {file_path}")
            return graph

        except Exception as e:
            logger.error(f"Error importing data from CSV file {file_path}: {e}")
            raise ValueError(f"Error importing data from CSV file {file_path}: {e}")

    def import_from_dataframe(
        self,
        df: pd.DataFrame,
        mapping_config: Optional[Dict] = None,
        statement_type: str = "income_statement",
    ) -> FinancialStatementGraph:
        """
        Import financial data from a pandas DataFrame.

        Args:
            df: DataFrame containing the financial data
            mapping_config: Optional mapping configuration to override default field mappings
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')

        Returns:
            FinancialStatementGraph: Graph containing the imported financial data

        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get the DataFrame adapter
            adapter = self.get_adapter(
                "DataFrameAdapter", mapping_config=mapping_config
            )

            # Import data using the adapter
            graph = adapter.create_statement_graph(df=df, statement_type=statement_type)

            logger.info(
                f"Imported {statement_type} data from DataFrame with {len(df)} rows"
            )
            return graph

        except Exception as e:
            logger.error(f"Error importing data from DataFrame: {e}")
            raise ValueError(f"Error importing data from DataFrame: {e}")

    def register_custom_adapter(
        self, adapter_type: str, adapter_class: Type[DataSourceAdapter]
    ) -> None:
        """
        Register a custom adapter with the factory.

        Args:
            adapter_type: Name for the adapter type
            adapter_class: Class for the adapter

        Raises:
            ValueError: If there's an error registering the adapter
        """
        try:
            self.adapter_factory.register_adapter(adapter_type, adapter_class)
            logger.info(f"Registered custom adapter: {adapter_type}")

        except Exception as e:
            logger.error(f"Error registering custom adapter {adapter_type}: {e}")
            raise ValueError(f"Error registering custom adapter {adapter_type}: {e}")

    def list_available_adapters(self) -> List[str]:
        """
        List all available adapter types.

        Returns:
            List[str]: List of available adapter type names
        """
        return self.adapter_factory.list_adapters()

    def get_adapter_instances(self) -> List[str]:
        """
        List all active adapter instances in the registry.

        Returns:
            List[str]: List of registered adapter keys
        """
        return self.adapter_registry.list_instances()
