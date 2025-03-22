from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Union, Optional, Any
import pandas as pd
import numpy as np
import logging

from .graph import Graph
from .data_manager import DataManager
from .calculation_engine import CalculationEngine
from .node_factory import NodeFactory
from ..transformations.transformation_service import TransformationService
from .nodes import (Node)


# Configure logging
logger = logging.getLogger(__name__)

class FinancialStatementGraph:
    """
    A graph specialized for financial statements.
    A graph-based representation of financial statements and calculations.

    This class provides functionality to:
    - Add raw financial statement items (like revenue, expenses, etc.) with their values
    - Define calculations between financial items (addition, subtraction, multiplication, division)
    - Calculate derived metrics for specific time periods
    
    The graph structure ensures proper dependency management and calculation order.
    Each node in the graph represents either a raw financial statement item or a calculation.

    Example:
        fsg = FinancialStatementGraph()
        fsg.add_financial_statement_item("revenue", {"2022": 1000.0})
        fsg.add_financial_statement_item("expenses", {"2022": 600.0})
        fsg.add_calculation("profit", ["revenue", "expenses"], "subtraction")
        profit_2022 = fsg.calculate_financial_statement("profit", "2022")  # Returns 400.0
    """
    def __init__(self, periods: Optional[List[str]] = None):
        """
        Initialize a financial statement graph.
        
        Args:
            periods: Optional list of time periods for the financial statement
                     (e.g., ['FY2019', 'FY2020', 'FY2021'])
        """
        self.graph = Graph(periods or [])
        
        # Initialize specialized components
        self._data_manager = DataManager(self.graph)
        self._calculation_engine = CalculationEngine(self.graph)
        
        # Import at runtime to avoid circular imports
        from ..io.import_manager import ImportManager
        from ..io.export_manager import ExportManager
        
        self._importer = ImportManager()
        self._exporter = ExportManager()
        self._transformation_service = TransformationService()
        
        logger.info(f"FinancialStatementGraph initialized with {len(periods or [])} periods")

    def add_financial_statement_item(self, name: str, values: Dict[str, float]) -> str:
        """
        Add a financial statement item to the graph.
        
        Args:
            name: Name of the financial statement item
            values: Dictionary mapping periods to values
            
        Returns:
            str: Name of the added financial statement item
            
        Raises:
            ValueError: If the name is invalid or already exists
            
        Example:
            fsg.add_financial_statement_item("revenue", {"FY2020": 100000, "FY2021": 120000})
        """
        return self._data_manager.add_item(name, values)

    def add_calculation(self, name: str, inputs: List[str], calculation_type: str) -> str:
        """
        Add a calculation node to the graph.
        
        Args:
            name: Name of the calculation
            inputs: List of input node names
            calculation_type: Type of calculation ('addition', 'subtraction', 'multiplication', 'division')
            
        Returns:
            str: Name of the added calculation
            
        Raises:
            ValueError: If the name is invalid or already exists
            ValueError: If any input node does not exist
            ValueError: If the calculation type is invalid
            
        Example:
            fsg.add_calculation("gross_profit", ["revenue", "cost_of_goods_sold"], "subtraction")
        """
        return self._calculation_engine.add_calculation(name, inputs, calculation_type)

    def calculate_financial_statement(self, node_name: Optional[str] = None, period: Optional[str] = None) -> Dict:
        """
        Calculate the financial statement or a specific node value.
        
        Args:
            node_name: Optional name of the node to calculate (calculates all if None)
            period: Optional specific period to calculate (calculates all periods if None)
            
        Returns:
            Dict: Dictionary of calculated values
            
        Raises:
            ValueError: If the node_name does not exist
            ValueError: If the period does not exist
            
        Example:
            values = fsg.calculate_financial_statement("gross_profit", "FY2021")
        """
        return self._calculation_engine.calculate(node_name, period)
    
    def recalculate_all(self) -> None:
        """
        Recalculate all calculation nodes in the graph for all periods.
        
        This ensures all derived values are up-to-date after making changes to input values.
        
        Example:
            fsg.recalculate_all()
        """
        # First, copy forward any values that might be missing
        self._data_manager.copy_forward_values(self.graph.periods)
        
        # Then recalculate all calculation nodes
        self._calculation_engine.recalculate_all(self.graph.periods)

    def to_dataframe(self, recalculate: bool = True) -> pd.DataFrame:
        """
        Convert the financial statement graph to a pandas DataFrame.
        
        Args:
            recalculate: Whether to recalculate all values before converting
            
        Returns:
            pd.DataFrame: DataFrame representation of the financial statement
            
        Example:
            df = fsg.to_dataframe()
        """
        return self._exporter.to_dataframe(self.graph, recalculate)

    def create_forecast(self, forecast_periods: List[str], growth_rates: Optional[Dict[str, Union[float, List[float], Dict[str, Any]]]] = None, 
                     method: Union[str, Dict[str, str]] = 'simple', **kwargs) -> None:
        """
        Create forecasts for financial statement items.
        
        Args:
            forecast_periods: List of future periods to forecast
            growth_rates: Dict mapping node names to either:
                - A single float for simple growth rate (e.g., 0.05 for 5% growth)
                - A list of floats for curve growth rates (must match forecast_periods length)
                - A dict for statistical growth with keys:
                    - 'distribution': Name of the distribution ('normal', 'uniform', 'lognormal', etc.)
                    - 'params': Dict of distribution parameters (e.g., {'mean': 0.05, 'std': 0.02})
            method: Either a string for the default method, or a dict mapping node names to methods:
                - 'simple': Uses single growth rate for all periods
                - 'curve': Uses different growth rates for each period
                - 'statistical': Uses random growth rates from specified distribution
                - 'average': Uses historical average (no growth)
                - 'historical_growth': Uses average historical growth rate
            **kwargs: Additional method-specific parameters
                
        Raises:
            ValueError: If invalid parameters are provided
            
        Example:
            # Simple growth rate (5% growth for all periods)
            fsg.create_forecast(['FY2023', 'FY2024'], {'revenue': 0.05})
            
            # Curve growth rates (different rate for each period)
            fsg.create_forecast(['FY2023', 'FY2024', 'FY2025'], 
                               {'revenue': [0.05, 0.06, 0.07]})
            
            # Statistical growth with normal distribution
            fsg.create_forecast(['FY2023', 'FY2024', 'FY2025'],
                               {'revenue': {
                                   'distribution': 'normal',
                                   'params': {'mean': 0.05, 'std': 0.02}
                               }},
                               method='statistical')
            
            # Different methods for different items
            fsg.create_forecast(['FY2023', 'FY2024', 'FY2025'],
                               {'revenue': [0.05, 0.06, 0.07],
                                'expenses': 0.04},
                               method={'revenue': 'curve', 'expenses': 'simple'})
        """
        try:
            # Get historical periods
            historical_periods = self.get_historical_periods()
            
            if not historical_periods:
                raise ValueError("No historical periods found for forecasting")
            
            if not forecast_periods:
                raise ValueError("No forecast periods provided")
            
            # Process growth rates
            if growth_rates is None:
                growth_rates = {}
            
            # Convert method to dict if it's a string
            if isinstance(method, str):
                method = {node_name: method for node_name in growth_rates.keys()}
            
            # Apply forecasting only to specified nodes
            for node_name, growth_rate in growth_rates.items():
                node = self.graph.get_node(node_name)
                if node is None:
                    raise ValueError(f"Node {node_name} not found in graph")
                
                # Get the method for this node
                node_method = method.get(node_name, 'simple')
                
                # Process growth rate based on method
                if node_method == 'simple':
                    # For simple method, convert list to fixed rate if needed
                    if isinstance(growth_rate, list):
                        growth_rate = growth_rate[0]  # Use first rate
                elif node_method == 'curve':
                    # For curve method, convert fixed rate to list if needed
                    if not isinstance(growth_rate, list):
                        growth_rate = [growth_rate] * len(forecast_periods)
                elif node_method == 'statistical':
                    # For statistical method, ensure we have distribution parameters
                    if not isinstance(growth_rate, dict) or 'distribution' not in growth_rate:
                        raise ValueError(f"Statistical method requires distribution parameters for {node_name}")
                elif node_method == 'average':
                    # For average method, growth rate is ignored
                    growth_rate = 0.0  # pragma: no cover
                elif node_method == 'historical_growth':
                    # For historical growth method, growth rate is ignored as it's calculated from history
                    growth_rate = 0.0
                else:
                    raise ValueError(f"Invalid forecasting method: {node_method}")
                
                # Apply the selected forecasting method
                self._forecast_node(node, historical_periods, forecast_periods, growth_rate, node_method)
            
            # Recalculate all nodes to ensure derived values are up-to-date
            self.recalculate_all()
            
            logger.info(f"Created forecast for {len(forecast_periods)} periods")
            
        except Exception as e:
            logger.error(f"Error creating forecast: {e}")
            raise ValueError(f"Error creating forecast: {e}")
    
    def _forecast_node(self, node, historical_periods, forecast_periods, growth_rate, method, **kwargs):
        """Forecast a node using the specified method."""
        # Get the last historical period to use as base
        base_period = historical_periods[-1]
        historical_values = [node.calculate(period) for period in historical_periods]
        
        logger.debug(f"Forecasting node {node.name}:")
        logger.debug(f"  Base period: {base_period}")
        logger.debug(f"  Historical values: {historical_values}")
        logger.debug(f"  Growth rate: {growth_rate}")
        logger.debug(f"  Method: {method}")
        
        # Map method to forecast type
        method_to_type = {
            'simple': 'fixed',
            'curve': 'curve',
            'statistical': 'statistical',
            'average': 'average',
            'historical_growth': 'historical_growth'
        }
        forecast_type = method_to_type.get(method)
        if forecast_type is None:
            raise ValueError(f"Invalid forecasting method: {method}")
        
        # Process growth parameters based on method
        if method == 'simple':
            # Simple constant growth rate
            growth_params = float(growth_rate)  # Ensure it's a float
            logger.debug(f"  Using fixed growth rate: {growth_params}")
            
        elif method == 'curve':
            # Varying growth rates for each period
            # Validate growth rates list length matches forecast periods
            if len(growth_rate) != len(forecast_periods):
                raise ValueError(f"Growth rates list for {node.name} must match the number of forecast periods")
            
            growth_params = [float(rate) for rate in growth_rate]  # Ensure all are floats
            logger.debug(f"  Using curve growth rates: {growth_params}")
            
        elif method == 'statistical':
            # Statistical method using specified distribution
            # Extract distribution parameters
            distribution = growth_rate['distribution']
            params = growth_rate['params']
            
            # Create appropriate distribution function
            if distribution == 'normal':
                def generate_growth_rate():
                    return np.random.normal(params['mean'], params['std'])
            elif distribution == 'uniform':
                def generate_growth_rate():
                    return np.random.uniform(params['low'], params['high'])
            elif distribution == 'lognormal':
                def generate_growth_rate():
                    return np.random.lognormal(params['mean'], params['sigma'])
            else:
                raise ValueError(f"Unsupported distribution type: {distribution}")
            
            growth_params = generate_growth_rate
            logger.debug(f"  Using statistical growth with {distribution} distribution")
            
        elif method == 'average':
            # Use the average of historical values (no growth)
            avg_value = sum(historical_values) / len(historical_values)
            logger.debug(f"  Using average value: {avg_value}")
            growth_params = avg_value
            
        elif method == 'historical_growth':
            # For historical growth method, growth rate is ignored as it's calculated from history
            growth_params = 0.0
            
        else:
            raise ValueError(f"Invalid forecasting method: {method}")  # pragma: no cover
        
        # Create forecast node using NodeFactory
        forecast_node = NodeFactory.create_forecast_node(
            name=node.name,  # Use the node's name
            base_node=node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            forecast_type=forecast_type,
            growth_params=growth_params
        )
        
        # Copy historical values to the forecast node
        if hasattr(node, 'values'):
            forecast_node.values = node.values.copy()
        
        # Replace the original node with the forecast node in the graph
        self.graph.replace_node(node.name, forecast_node)
        
        # Ensure the graph knows about these periods
        for period in forecast_periods:
            if period not in self.graph._periods:
                self.graph._periods.add(period)
    
    def export_to_excel(self, file_path: Union[str, Path], sheet_name: str = 'Financial Statement',
                      include_nodes: Optional[List[str]] = None, format_options: Optional[Dict] = None) -> None:
        """
        Export the financial statement to an Excel file.
        
        Args:
            file_path: Path to the output Excel file
            sheet_name: Name of the sheet to create
            include_nodes: Optional list of node names to include (includes all if None)
            format_options: Optional formatting options for the Excel file
            
        Raises:
            ValueError: If there's an error exporting the data
            
        Example:
            fsg.export_to_excel("financial_statement.xlsx", include_nodes=["revenue", "expenses", "profit"])
        """
        self._exporter.to_excel(
            self.graph, file_path, sheet_name, include_nodes, format_options
        )
    
    def import_from_api(self, source: str, identifier: str, period_type: str = 'FY', 
                       limit: int = 10, statement_type: str = 'income_statement', **kwargs):
        """
        Import financial data from an API source.
        
        Args:
            source (str): API source name (e.g., 'FMP' for Financial Modeling Prep)
            identifier (str): Identifier for the data (e.g., ticker symbol)
            period_type (str): 'FY' for fiscal year or 'QTR' for quarter
            limit (int): Maximum number of periods to import
            statement_type (str): Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            **kwargs: Additional parameters for the specific API adapter
            
        Returns:
            Self to allow method chaining
            
        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get new graph from the import manager
            imported_graph = self._importer.import_from_api(
                source=source,
                identifier=identifier,
                period_type=period_type,
                limit=limit,
                statement_type=statement_type,
                **kwargs
            )
            
            # Merge the imported graph with the current graph
            self._merge_graph(imported_graph)
            
            return self
            
        except Exception as e:
            raise ValueError(f"Error importing from API {source}: {e}")
    
    def import_from_excel(self, file_path: str, sheet_name: str, period_column: str,
                        statement_type: str = 'income_statement', mapping_config=None):
        """
        Import financial data from an Excel file.
        
        Args:
            file_path (str): Path to the Excel file
            sheet_name (str): Name of the sheet containing the data
            period_column (str): Name of the column containing period identifiers
            statement_type (str): Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            mapping_config (dict, optional): Optional mapping configuration to override default field mappings
            
        Returns:
            Self to allow method chaining
            
        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get new graph from the import manager
            imported_graph = self._importer.import_from_excel(
                file_path=file_path,
                sheet_name=sheet_name,
                period_column=period_column,
                statement_type=statement_type,
                mapping_config=mapping_config
            )
            
            # Merge the imported graph with the current graph
            self._merge_graph(imported_graph)
            
            return self
            
        except Exception as e:
            raise ValueError(f"Error importing from Excel file {file_path}: {e}")
    
    def import_from_csv(self, file_path: str, date_column: str, value_column: str, 
                      item_column: str, statement_type: str = 'income_statement',
                      mapping_config=None):
        """
        Import financial data from a CSV file.
        
        Args:
            file_path (str): Path to the CSV file
            date_column (str): Name of the column containing dates
            value_column (str): Name of the column containing values
            item_column (str): Name of the column containing item names
            statement_type (str): Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            mapping_config (dict, optional): Optional mapping configuration to override default field mappings
            
        Returns:
            Self to allow method chaining
            
        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get new graph from the import manager
            imported_graph = self._importer.import_from_csv(
                file_path=file_path,
                date_column=date_column,
                value_column=value_column,
                item_column=item_column,
                statement_type=statement_type,
                mapping_config=mapping_config
            )
            
            # Merge the imported graph with the current graph
            self._merge_graph(imported_graph)
            
            return self
            
        except Exception as e:
            raise ValueError(f"Error importing from CSV file {file_path}: {e}")
    
    def import_from_dataframe(self, df: pd.DataFrame, statement_type: str = 'income_statement',
                            mapping_config=None):
        """
        Import financial data from a pandas DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame containing the financial data
            statement_type (str): Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            mapping_config (dict, optional): Optional mapping configuration to override default field mappings
            
        Returns:
            Self to allow method chaining
            
        Raises:
            ValueError: If there's an error importing the data
        """
        try:
            # Get new graph from the import manager
            imported_graph = self._importer.import_from_dataframe(
                df=df,
                statement_type=statement_type,
                mapping_config=mapping_config
            )
            
            # Merge the imported graph with the current graph
            self._merge_graph(imported_graph)
            
            return self
            
        except Exception as e:
            raise ValueError(f"Error importing from DataFrame: {e}")
    
    def _merge_graph(self, other_graph):
        """
        Merge another FinancialStatementGraph into this one.
        
        Args:
            other_graph (FinancialStatementGraph): Graph to merge into this one
            
        Returns:
            None
        """
        # Update periods
        for period in other_graph.graph.periods:
            if period not in self.graph.periods:
                self.graph.periods.append(period)
        self.graph.periods.sort()
        
        # Merge nodes
        for node_name, node in other_graph.graph.nodes.items():
            existing_node = self.graph.get_node(node_name)
            if existing_node is not None:
                # Update existing node with new values
                if hasattr(node, 'values'):
                    for period, value in node.values.items():
                        existing_node.values[period] = value
                self.graph.add_node(existing_node)  # Re-add to update
            else:
                # Add new node
                self.graph.add_node(node)
    
    def add_metric(self, metric_name: str, node_name: str = None):
        """
        Add a financial metric calculation node to the graph.
        
        Args:
            metric_name: The name of the metric from the METRIC_DEFINITIONS
            node_name: Optional custom name for the node (defaults to metric_name)
            
        Raises:
            ValueError: If the metric_name is not found in METRIC_DEFINITIONS
            ValueError: If any required input nodes are missing from the graph
            
        Example:
            fsg.add_metric("gross_profit_margin")
        """
        self._calculation_engine.add_metric(metric_name, node_name)
    
    def to_excel(self, file_path: Union[str, Path], sheet_name: str = 'Financial Statement') -> None:
        """
        Export financial statement data to an Excel file.
        
        Args:
            file_path: Path to the output Excel file
            sheet_name: Name of the sheet to create
            
        Raises:
            ValueError: If there's an error exporting the data
            
        Example:
            fsg.to_excel("financial_statement.xlsx")
        """
        self.export_to_excel(file_path, sheet_name)

    def normalize_data(self, normalization_type: str = 'percent_of', reference: Optional[str] = None,
                     scale_factor: Optional[float] = None) -> pd.DataFrame:
        """
        Normalize the financial statement data.
        
        Args:
            normalization_type: Type of normalization to apply
                - 'percent_of': Normalize as percentage of reference item
                - 'minmax': Scale values to range [0,1]
                - 'standard': Apply (x - mean) / std
                - 'scale_by': Multiply by scale factor
            reference: Reference item for 'percent_of' normalization
            scale_factor: Scale factor for 'scale_by' normalization
            
        Returns:
            DataFrame with normalized data
            
        Example:
            # Normalize all values as percentage of revenue
            normalized_df = fsg.normalize_data('percent_of', 'revenue')
        """
        df = self.to_dataframe()
        return self._transformation_service.normalize_data(
            df, normalization_type, reference, scale_factor
        )
    
    def analyze_time_series(self, transformation_type: str = 'growth_rate', 
                          periods: int = 1, window_size: int = 3) -> pd.DataFrame:
        """
        Apply time series transformations to the financial data.
        
        Args:
            transformation_type: Type of transformation to apply
                - 'growth_rate': Calculate period-to-period growth
                - 'moving_avg': Calculate moving average
                - 'cagr': Compound annual growth rate
                - 'yoy': Year-over-year comparison
                - 'qoq': Quarter-over-quarter comparison
            periods: Number of periods for calculations
            window_size: Window size for moving averages
            
        Returns:
            DataFrame with time series analysis
            
        Example:
            # Calculate year-over-year growth rates
            growth_df = fsg.analyze_time_series('yoy')
        """
        df = self.to_dataframe()
        return self._transformation_service.transform_time_series(
            df, transformation_type, periods, window_size
        )
    
    def convert_periods(self, conversion_type: str, aggregation: str = 'sum') -> pd.DataFrame:
        """
        Convert data between different period types.
        
        Args:
            conversion_type: Type of period conversion
                - 'quarterly_to_annual': Convert quarterly to annual data
                - 'monthly_to_quarterly': Convert monthly to quarterly data
                - 'monthly_to_annual': Convert monthly to annual data
                - 'annual_to_ttm': Convert annual to trailing twelve months
            aggregation: How to aggregate data ('sum', 'mean', 'last', etc.)
            
        Returns:
            DataFrame with converted periods
            
        Example:
            # Convert quarterly data to annual
            annual_df = fsg.convert_periods('quarterly_to_annual')
        """
        df = self.to_dataframe()
        return self._transformation_service.convert_periods(df, conversion_type, aggregation)
    
    def format_statement(self, statement_type: str = 'income_statement',
                       add_subtotals: bool = True, apply_sign_convention: bool = True) -> pd.DataFrame:
        """
        Format the financial statement according to standard conventions.
        
        Args:
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            add_subtotals: Whether to add standard subtotals
            apply_sign_convention: Whether to apply standard sign conventions
            
        Returns:
            DataFrame with formatted financial statement
            
        Example:
            # Format as income statement with subtotals
            formatted_df = fsg.format_statement('income_statement')
        """
        df = self.to_dataframe()
        return self._transformation_service.format_statement(
            df, statement_type, add_subtotals, apply_sign_convention
        )
    
    def apply_transformations(self, transformers_config: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply a sequence of transformations to the financial statement data.
        
        Args:
            transformers_config: List of transformer configurations
                Each dict should have:
                - 'name': Name of the transformer
                - Additional configuration parameters
                
        Returns:
            DataFrame with transformed data
            
        Example:
            config = [
                {'name': 'period_conversion', 'conversion_type': 'quarterly_to_annual'},
                {'name': 'normalization', 'normalization_type': 'percent_of', 'reference': 'revenue'}
            ]
            transformed_df = fsg.apply_transformations(config)
        """
        df = self.to_dataframe()
        return self._transformation_service.apply_transformation_pipeline(df, transformers_config)

    def get_historical_periods(self) -> List[str]:
        """
        Get the list of historical periods in the graph.
        
        This method returns all periods in the graph that have actual data,
        as opposed to forecast periods.
        
        Returns:
            List[str]: List of historical periods in chronological order
        """
        # Get all periods from the graph
        all_periods = list(self.graph._periods)
        
        if not all_periods:
            return []  # pragma: no cover
        
        # Filter to find only historical periods (those with actual data)
        historical_periods = []
        
        # Check FinancialStatementItemNodes to identify periods with actual data
        for node in self.get_financial_statement_items():
            for period in node.values:
                if (period in all_periods and 
                    period not in historical_periods and 
                    node.values[period] != 0.0):  # Assuming zero values might be placeholders
                    historical_periods.append(period)
        
        # If no historical periods found, check if any periods have actual data
        if not historical_periods:
            for node in self.graph.nodes.values():
                if hasattr(node, 'values'):
                    for period in node.values:
                        if (period in all_periods and 
                            period not in historical_periods and 
                            node.values[period] != 0.0):  # Assuming zero values might be placeholders
                            historical_periods.append(period)
        
        # Sort chronologically
        return sorted(historical_periods)
    
    def get_financial_statement_items(self) -> List[Node]:
        """
        Get all financial statement item nodes (leaf nodes) from the graph.
        
        Returns:
            List[Node]: List of FinancialStatementItemNode instances
        """
        from .nodes import FinancialStatementItemNode
        return [
            node for node in self.graph.nodes.values() 
            if isinstance(node, FinancialStatementItemNode)
        ]
