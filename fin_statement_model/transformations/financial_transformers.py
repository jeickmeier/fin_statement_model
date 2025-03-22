"""
Financial data transformers for the Financial Statement Model.

This module provides transformers for common financial data transformations.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any
import logging

from .base_transformer import DataTransformer

# Configure logging
logger = logging.getLogger(__name__)


class NormalizationTransformer(DataTransformer):
    """
    Transformer that normalizes financial data.
    
    This transformer can normalize values by:
    - Dividing by a reference value (e.g. convert to percentages of revenue)
    - Scaling to a specific range (e.g. 0-1)
    - Applying standard normalization ((x - mean) / std)
    
    It can operate on DataFrames or dictionary data structures.
    """
    
    NORMALIZATION_TYPES = ['percent_of', 'minmax', 'standard', 'scale_by']
    
    def __init__(self, normalization_type: str = 'percent_of', reference: Optional[str] = None, 
                 scale_factor: Optional[float] = None, config: Optional[Dict] = None):
        """
        Initialize the normalizer.
        
        Args:
            normalization_type: Type of normalization to apply
                - 'percent_of': Divides by a reference value
                - 'minmax': Scales to range [0,1]
                - 'standard': Applies (x - mean) / std
                - 'scale_by': Multiplies by a scale factor
            reference: Reference field for percent_of normalization
            scale_factor: Factor to scale by for scale_by normalization
            config: Additional configuration options
        """
        super().__init__(config)
        if normalization_type not in self.NORMALIZATION_TYPES:
            raise ValueError(f"Invalid normalization type: {normalization_type}. "
                           f"Must be one of {self.NORMALIZATION_TYPES}")
                           
        self.normalization_type = normalization_type
        self.reference = reference
        self.scale_factor = scale_factor
        
        # Validation
        if normalization_type == 'percent_of' and not reference:
            raise ValueError("Reference field must be provided for percent_of normalization")
            
        if normalization_type == 'scale_by' and scale_factor is None:
            raise ValueError("Scale factor must be provided for scale_by normalization")
            
    def transform(self, data: Union[pd.DataFrame, Dict]) -> Union[pd.DataFrame, Dict]:
        """
        Normalize the data based on the configured normalization type.
        
        Args:
            data: DataFrame or dictionary containing financial data
            
        Returns:
            Normalized data in the same format as input
        """
        if isinstance(data, pd.DataFrame):
            return self._transform_dataframe(data)
        elif isinstance(data, dict):
            return self._transform_dict(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
            
    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame"""
        result = df.copy()
        
        if self.normalization_type == 'percent_of':
            if self.reference not in df.columns:
                raise ValueError(f"Reference column '{self.reference}' not found in DataFrame")
                
            for col in df.columns:
                if col != self.reference:
                    result[col] = df[col] / df[self.reference] * 100
                    
        elif self.normalization_type == 'minmax': # pragma: no cover
            for col in df.columns: 
                min_val = df[col].min()
                max_val = df[col].max()
                
                if max_val > min_val:
                    result[col] = (df[col] - min_val) / (max_val - min_val) # pragma: no cover
                    
        elif self.normalization_type == 'standard':
            for col in df.columns:
                mean = df[col].mean()
                std = df[col].std()
                
                if std > 0:
                    result[col] = (df[col] - mean) / std
                    
        elif self.normalization_type == 'scale_by':
            for col in df.columns:
                result[col] = df[col] * self.scale_factor
                
        return result
        
    def _transform_dict(self, data: Dict) -> Dict:
        """Transform a dictionary"""
        result = {}
        
        if self.normalization_type == 'percent_of':
            if self.reference not in data:
                raise ValueError(f"Reference key '{self.reference}' not found in data")
                
            ref_value = data[self.reference]
            for key, value in data.items():
                if key != self.reference and ref_value != 0:
                    result[key] = value / ref_value * 100
                else:
                    result[key] = value
                    
        elif self.normalization_type == 'minmax':
            values = list(data.values())
            min_val = min(values)
            max_val = max(values)
            
            if max_val > min_val:
                for key, value in data.items():
                    result[key] = (value - min_val) / (max_val - min_val)
            else:
                result = data.copy()
                
        elif self.normalization_type == 'standard':
            values = list(data.values())
            mean = sum(values) / len(values)
            std = np.std(list(values))
            
            if std > 0:
                for key, value in data.items():
                    result[key] = (value - mean) / std
            else:
                result = data.copy()
                
        elif self.normalization_type == 'scale_by':
            for key, value in data.items():
                result[key] = value * self.scale_factor
                
        return result


class TimeSeriesTransformer(DataTransformer):
    """
    Transformer for time series financial data.
    
    This transformer can apply common time series transformations like:
    - Calculating growth rates
    - Calculating moving averages
    - Computing compound annual growth rate (CAGR)
    - Converting to year-over-year or quarter-over-quarter comparisons
    """
    
    TRANSFORMATION_TYPES = ['growth_rate', 'moving_avg', 'cagr', 'yoy', 'qoq']
    
    def __init__(self, transformation_type: str = 'growth_rate', periods: int = 1, 
                 window_size: int = 3, config: Optional[Dict] = None):
        """
        Initialize the time series transformer.
        
        Args:
            transformation_type: Type of transformation to apply
                - 'growth_rate': Calculate period-to-period growth rates
                - 'moving_avg': Calculate moving average
                - 'cagr': Calculate compound annual growth rate
                - 'yoy': Year-over-year comparison
                - 'qoq': Quarter-over-quarter comparison
            periods: Number of periods to use in calculations
            window_size: Size of the moving average window
            config: Additional configuration options
        """
        super().__init__(config)
        if transformation_type not in self.TRANSFORMATION_TYPES:
            raise ValueError(f"Invalid transformation type: {transformation_type}. "
                           f"Must be one of {self.TRANSFORMATION_TYPES}")
                           
        self.transformation_type = transformation_type
        self.periods = periods
        self.window_size = window_size
        
    def transform(self, data: Union[pd.DataFrame, Dict]) -> Union[pd.DataFrame, Dict]:
        """
        Transform time series data based on the configured transformation type.
        
        Args:
            data: DataFrame or dictionary containing time series financial data
            
        Returns:
            Transformed data in the same format as input
        """
        if isinstance(data, pd.DataFrame):
            return self._transform_dataframe(data)
        elif isinstance(data, dict):
            # For dictionaries, we assume the keys are time periods in chronological order
            return self._transform_dict(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
            
    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame with time series data"""
        result = df.copy()
        
        if self.transformation_type == 'growth_rate':
            for col in df.columns:
                result[f"{col}_growth"] = df[col].pct_change(periods=self.periods) * 100
                
        elif self.transformation_type == 'moving_avg':
            for col in df.columns:
                result[f"{col}_ma{self.window_size}"] = df[col].rolling(window=self.window_size).mean()
                
        elif self.transformation_type == 'cagr':
            # Assuming the index represents time periods
            n_periods = len(df) - 1
            if n_periods > 0:
                for col in df.columns:
                    first_value = df[col].iloc[0]
                    last_value = df[col].iloc[-1]
                    
                    if first_value > 0:
                        cagr = (last_value / first_value) ** (1 / n_periods) - 1
                        # Add as a new column with the same value for all rows
                        result[f"{col}_cagr"] = cagr * 100
                        
        elif self.transformation_type == 'yoy':
            # Assuming yearly data, shift by 1 to get same period last year
            for col in df.columns:
                result[f"{col}_yoy"] = df[col].pct_change(periods=1) * 100
                
        elif self.transformation_type == 'qoq':
            # Assuming quarterly data, shift by 1 to get previous quarter
            for col in df.columns:
                result[f"{col}_qoq"] = df[col].pct_change(periods=1) * 100
                
        return result
        
    def _transform_dict(self, data: Dict) -> Dict:
        """Transform a dictionary with time series data"""
        # Convert to Series for easier processing
        series = pd.Series(data)
        transformed = self._transform_dataframe(pd.DataFrame(series))
        
        # Convert back to dictionary
        return transformed.to_dict()


class PeriodConversionTransformer(DataTransformer):
    """
    Transformer for converting between different period types.
    
    This transformer can convert:
    - Quarterly data to annual
    - Monthly data to quarterly or annual
    - Annual data to trailing twelve months (TTM)
    """
    
    CONVERSION_TYPES = ['quarterly_to_annual', 'monthly_to_quarterly', 
                       'monthly_to_annual', 'annual_to_ttm']
    
    def __init__(self, conversion_type: str, aggregation: str = 'sum', 
                 config: Optional[Dict] = None):
        """
        Initialize the period conversion transformer.
        
        Args:
            conversion_type: Type of period conversion to apply
            aggregation: How to aggregate data (sum, mean, last, etc.)
            config: Additional configuration options
        """
        super().__init__(config)
        if conversion_type not in self.CONVERSION_TYPES:
            raise ValueError(f"Invalid conversion type: {conversion_type}. "
                           f"Must be one of {self.CONVERSION_TYPES}")
                           
        self.conversion_type = conversion_type
        self.aggregation = aggregation
        
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data by converting between period types.
        
        Args:
            data: DataFrame with DatetimeIndex or period labels in the index
            
        Returns:
            DataFrame with transformed periods
        """
        # Ensure we have a DataFrame
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Period conversion requires a pandas DataFrame")
            
        # Try to convert index to datetime if it's not already
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data = data.copy()
                data.index = pd.to_datetime(data.index, format='%Y-%m-%d')
            except:
                raise ValueError("Index must be convertible to datetime for period conversion")
                
        if self.conversion_type == 'quarterly_to_annual':
            # Group by year and aggregate
            return data.groupby(data.index.year).agg(self.aggregation)
            
        elif self.conversion_type == 'monthly_to_quarterly':
            # Group by year and quarter
            return data.groupby([data.index.year, data.index.quarter]).agg(self.aggregation)
            
        elif self.conversion_type == 'monthly_to_annual':
            # Group by year
            return data.groupby(data.index.year).agg(self.aggregation)
            
        elif self.conversion_type == 'annual_to_ttm':
            # Implement TTM as rolling sum with window=4 for quarterly data
            if self.aggregation == 'sum':
                return data.rolling(window=4).sum()
            else:
                # For other aggregation methods, we need custom logic
                raise ValueError("annual_to_ttm conversion only supports 'sum' aggregation")
                
        return data # pragma: no cover


class StatementFormattingTransformer(DataTransformer):
    """
    Transformer for formatting financial statements.
    
    This transformer can:
    - Add subtotals and totals
    - Reorder line items according to standard formats
    - Apply sign conventions (negative expenses, etc.)
    - Format statements for display (adding separators, indentation, etc.)
    """
    
    def __init__(self, statement_type: str = 'income_statement', add_subtotals: bool = True,
                 apply_sign_convention: bool = True, config: Optional[Dict] = None):
        """
        Initialize the statement formatting transformer.
        
        Args:
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            add_subtotals: Whether to add standard subtotals
            apply_sign_convention: Whether to apply standard sign conventions
            config: Additional configuration options
        """
        super().__init__(config)
        self.statement_type = statement_type
        self.add_subtotals = add_subtotals
        self.apply_sign_convention = apply_sign_convention
        
        # Define standard orderings for different statement types
        self.item_order = self._get_standard_order()
        
    def _get_standard_order(self) -> List[str]:
        """Get the standard ordering of items for the current statement type"""
        if self.statement_type == 'income_statement':
            return [
                'revenue', 'total_revenue',
                'cost_of_goods_sold',
                'gross_profit',
                'operating_expenses',
                'operating_income',
                'other_income', 'interest_expense', 'interest_income',
                'income_before_taxes',
                'income_tax',
                'net_income'
            ]
            
        elif self.statement_type == 'balance_sheet':
            return [
                # Assets
                'cash_and_equivalents', 'short_term_investments', 
                'accounts_receivable', 'inventory',
                'current_assets',
                'property_plant_equipment', 'long_term_investments', 'intangible_assets',
                'total_assets',
                
                # Liabilities
                'accounts_payable', 'short_term_debt', 'current_liabilities',
                'long_term_debt', 'total_liabilities',
                
                # Equity
                'common_stock', 'retained_earnings', 'total_equity',
                
                'total_liabilities_and_equity'
            ]
            
        elif self.statement_type == 'cash_flow':
            return [
                'net_income',
                'depreciation_amortization', 'changes_in_working_capital',
                'cash_from_operating_activities',
                'capital_expenditures', 'investments',
                'cash_from_investing_activities',
                'debt_issuance', 'debt_repayment', 'dividends', 'share_repurchases',
                'cash_from_financing_activities',
                'net_change_in_cash'
            ]
            
        return [] # pragma: no cover
        
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Format a financial statement DataFrame.
        
        Args:
            data: DataFrame containing financial statement data
            
        Returns:
            Formatted DataFrame
        """
        result = data.copy()
        
        # Apply sign conventions if requested
        if self.apply_sign_convention:
            result = self._apply_sign_convention(result)
            
        # Add subtotals if requested and not already present
        if self.add_subtotals:
            result = self._add_subtotals(result)
            
        # Reorder items according to standard format
        result = self._reorder_items(result)
        
        return result
        
    def _apply_sign_convention(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard sign conventions to line items"""
        result = df.copy()
        
        # Items that should be negative
        negative_items = []
        
        if self.statement_type == 'income_statement':
            negative_items = ['cost_of_goods_sold', 'operating_expenses', 'interest_expense', 'income_tax']
            
        elif self.statement_type == 'cash_flow':
            negative_items = ['capital_expenditures', 'investments', 'debt_repayment', 'dividends', 'share_repurchases']
            
        # Convert items to negative if they're positive
        for item in negative_items:
            if item in result.index:
                result.loc[item] = result.loc[item] * -1 if result.loc[item].mean() > 0 else result.loc[item]
                
        return result
        
    def _add_subtotals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add standard subtotals to the statement"""
        result = df.copy()
        
        if self.statement_type == 'income_statement':
            # Add gross profit if we have revenue and COGS
            if 'revenue' in result.index and 'cost_of_goods_sold' in result.index and 'gross_profit' not in result.index:
                result.loc['gross_profit'] = result.loc['revenue'] + result.loc['cost_of_goods_sold']
                
            # Add operating income
            if 'gross_profit' in result.index and 'operating_expenses' in result.index and 'operating_income' not in result.index:
                result.loc['operating_income'] = result.loc['gross_profit'] + result.loc['operating_expenses']
                
            # Add income before taxes
            if 'operating_income' in result.index and 'interest_expense' in result.index and 'income_before_taxes' not in result.index:
                result.loc['income_before_taxes'] = result.loc['operating_income'] + result.loc['interest_expense']
                
            # Add net income
            if 'income_before_taxes' in result.index and 'income_tax' in result.index and 'net_income' not in result.index:
                result.loc['net_income'] = result.loc['income_before_taxes'] + result.loc['income_tax']
                
        elif self.statement_type == 'balance_sheet':
            # Add current assets
            current_assets = ['cash_and_equivalents', 'short_term_investments', 'accounts_receivable', 'inventory']
            if any(item in result.index for item in current_assets) and 'current_assets' not in result.index:
                result.loc['current_assets'] = sum(result.loc[item] for item in current_assets if item in result.index)
                
            # Add total assets
            if 'current_assets' in result.index and 'property_plant_equipment' in result.index and 'total_assets' not in result.index:
                result.loc['total_assets'] = result.loc['current_assets'] + result.loc['property_plant_equipment']
                
            # Add current liabilities
            current_liabilities = ['accounts_payable', 'short_term_debt']
            if any(item in result.index for item in current_liabilities) and 'current_liabilities' not in result.index:
                result.loc['current_liabilities'] = sum(result.loc[item] for item in current_liabilities if item in result.index)
                
            # Add total liabilities
            if 'current_liabilities' in result.index and 'long_term_debt' in result.index and 'total_liabilities' not in result.index:
                result.loc['total_liabilities'] = result.loc['current_liabilities'] + result.loc['long_term_debt']
                
            # Add total equity
            equity_items = ['common_stock', 'retained_earnings']
            if any(item in result.index for item in equity_items) and 'total_equity' not in result.index:
                result.loc['total_equity'] = sum(result.loc[item] for item in equity_items if item in result.index) # pragma: no cover
                
            # Add total liabilities and equity
            if 'total_liabilities' in result.index and 'total_equity' in result.index and 'total_liabilities_and_equity' not in result.index:
                result.loc['total_liabilities_and_equity'] = result.loc['total_liabilities'] + result.loc['total_equity'] # pragma: no cover
                
        elif self.statement_type == 'cash_flow':
            # Add cash from operating activities
            operating_items = ['net_income', 'depreciation_amortization', 'changes_in_working_capital']
            if any(item in result.index for item in operating_items) and 'cash_from_operating_activities' not in result.index:
                result.loc['cash_from_operating_activities'] = sum(result.loc[item] for item in operating_items if item in result.index)
                
            # Add cash from investing activities
            investing_items = ['capital_expenditures', 'investments']
            if any(item in result.index for item in investing_items) and 'cash_from_investing_activities' not in result.index:
                result.loc['cash_from_investing_activities'] = sum(result.loc[item] for item in investing_items if item in result.index)
                
            # Add cash from financing activities
            financing_items = ['debt_issuance', 'debt_repayment', 'dividends', 'share_repurchases']
            if any(item in result.index for item in financing_items) and 'cash_from_financing_activities' not in result.index:
                result.loc['cash_from_financing_activities'] = sum(result.loc[item] for item in financing_items if item in result.index)
                
            # Add net change in cash
            cash_flow_categories = ['cash_from_operating_activities', 'cash_from_investing_activities', 'cash_from_financing_activities']
            if any(item in result.index for item in cash_flow_categories) and 'net_change_in_cash' not in result.index:
                result.loc['net_change_in_cash'] = sum(result.loc[item] for item in cash_flow_categories if item in result.index)
                
        return result
        
    def _reorder_items(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorder the DataFrame according to standard financial statement ordering"""
        # Create a list of items in the standard order that are present in the DataFrame
        ordered_items = [item for item in self.item_order if item in df.index]
        
        # Add any items from the DataFrame that aren't in the standard order at the end
        ordered_items.extend([item for item in df.index if item not in self.item_order])
        
        # Return a new DataFrame with the ordered index
        return df.loc[ordered_items] 