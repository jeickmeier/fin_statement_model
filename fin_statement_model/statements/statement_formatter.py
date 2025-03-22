"""
Statement formatter for Financial Statement Model.

This module provides utilities for formatting financial statement data, 
including converting statements to DataFrames or HTML.
"""
import logging
from typing import Dict, List, Any, Union, Set, Optional
import pandas as pd

from ..core.errors import DataValidationError
from .statement_structure import (
    StatementStructure, 
    Section, 
    LineItem, 
    CalculatedLineItem, 
    SubtotalLineItem,
    StatementItem
)

# Configure logging
logger = logging.getLogger(__name__)


class StatementFormatter:
    """
    Formats financial statement data into various representations.
    
    This class handles the conversion of financial statement data into
    DataFrames, HTML, and other formats. It also provides utilities for
    validating calculations and checking dependencies.
    """
    
    def __init__(self, statement: StatementStructure):
        """
        Initialize a statement formatter.
        
        Args:
            statement: The statement structure to format
        """
        self.statement = statement
    
    def generate_dataframe(
        self, 
        data: Dict[str, Dict[str, float]], 
        apply_sign_convention: bool = True,
        include_empty_items: bool = False
    ) -> pd.DataFrame:
        """
        Generate a DataFrame representation of the statement.
        
        Args:
            data: Dictionary mapping node IDs to period values
            apply_sign_convention: Whether to apply sign conventions
            include_empty_items: Whether to include items with no data
            
        Returns:
            pd.DataFrame: DataFrame representation of the statement
            
        Raises:
            DataValidationError: If the data is invalid for the statement
        """
        # Validate data
        try:
            self.validate_calculations(data)
        except DataValidationError:
            # Re-raise any validation errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating calculations: {e}")
            raise DataValidationError(
                message="Statement data validation failed",
                validation_errors=[f"Unexpected error: {str(e)}"]
            ) from e
        
        # Get all periods from the data
        periods = set()
        for node_id, values in data.items():
            periods.update(values.keys())
        periods = sorted(periods)
        
        # Create DataFrame columns
        columns = ["Item", "Name"]
        columns.extend(periods)
        
        # Create rows
        rows = []
        try:
            self._generate_dataframe_rows(
                self.statement, 
                data, 
                rows, 
                periods, 
                0, 
                apply_sign_convention, 
                include_empty_items
            )
        except Exception as e: # pragma: no cover
            logger.error(f"Error generating DataFrame rows: {e}")
            raise DataValidationError(
                message="Failed to generate DataFrame",
                validation_errors=[f"Error generating rows: {str(e)}"]
            ) from e
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=columns)
        return df
    
    def _generate_dataframe_rows(
        self, 
        item: Union[StatementStructure, Section, StatementItem], 
        data: Dict[str, Dict[str, float]], 
        rows: List[List[Any]], 
        periods: List[str], 
        level: int, 
        apply_sign_convention: bool = True,
        include_empty_items: bool = False
    ) -> None:
        """
        Recursively generate rows for the DataFrame.
        
        Args:
            item: The statement structure item to generate rows for
            data: Dictionary mapping node IDs to period values
            rows: List of rows to append to
            periods: List of periods to include
            level: Current nesting level
            apply_sign_convention: Whether to apply sign conventions
            include_empty_items: Whether to include items with no data
        """
        # Add section or statement header
        if isinstance(item, (StatementStructure, Section)):
            # Add header row
            indent = " " * (level * 2)
            row = [f"{indent}{item.id}", item.name]
            
            # Add empty values for periods
            row.extend([""] * len(periods))
            rows.append(row)
            
            # Add nested items
            for child in item.items:
                self._generate_dataframe_rows(
                    child, 
                    data, 
                    rows, 
                    periods, 
                    level + 1, 
                    apply_sign_convention, 
                    include_empty_items
                )
        
        # Add line item
        elif isinstance(item, LineItem):
            # Skip empty items if not including them
            has_data = False
            if isinstance(item, (CalculatedLineItem, SubtotalLineItem)):
                # For calculated items, check if the item's ID is a node in the data
                has_data = item.id in data
            else:
                # For regular items, check if the node_id is in the data
                has_data = item.node_id in data
            
            if not has_data and not include_empty_items:
                return
            
            # Add line item row
            indent = " " * (level * 2)
            row = [f"{indent}{item.id}", item.name]
            
            # Add values for each period
            for period in periods:
                value = None
                
                # Get value based on item type
                if isinstance(item, (CalculatedLineItem, SubtotalLineItem)):
                    # For calculated items, use the item's ID
                    if item.id in data and period in data[item.id]:
                        value = data[item.id][period]
                else:
                    # For regular items, use the node_id
                    if item.node_id in data and period in data[item.node_id]:
                        value = data[item.node_id][period]
                
                # Apply sign convention if enabled
                if value is not None and apply_sign_convention and item.sign_convention == -1:
                    value = -value
                
                # Format the value
                if value is None:
                    row.append("")
                elif pd.isna(value):
                    row.append("NaN") # pragma: no cover
                else:
                    row.append(value)
            
            rows.append(row)
    
    def format_html(
        self, 
        data: Dict[str, Dict[str, float]], 
        apply_sign_convention: bool = True,
        include_empty_items: bool = False,
        css_styles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate an HTML representation of the statement.
        
        Args:
            data: Dictionary mapping node IDs to period values
            apply_sign_convention: Whether to apply sign conventions
            include_empty_items: Whether to include items with no data
            css_styles: Custom CSS styles for the HTML
            
        Returns:
            str: HTML representation of the statement
            
        Raises:
            DataValidationError: If the data is invalid for the statement
        """
        try:
            # Generate DataFrame
            df = self.generate_dataframe(
                data, 
                apply_sign_convention=apply_sign_convention,
                include_empty_items=include_empty_items
            )
            
            # Define default CSS styles
            default_styles = {
                "table": "border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;",
                "th": "background-color: #f2f2f2; border: 1px solid #ddd; padding: 8px; text-align: left;",
                "td": "border: 1px solid #ddd; padding: 8px;",
                "tr:nth-child(even)": "background-color: #f9f9f9;",
                "tr:hover": "background-color: #f2f2f2;",
                ".header": "font-weight: bold; background-color: #e6e6e6;",
                ".section": "font-weight: bold;",
                ".subtotal": "font-weight: bold; border-top: 2px solid #ddd;",
                ".total": "font-weight: bold; border-top: 2px solid #000; border-bottom: 2px solid #000;"
            }
            
            # Merge with custom styles
            styles = default_styles
            if css_styles:
                styles.update(css_styles)
            
            # Generate CSS
            css = "\n".join([f"{selector} {{ {style} }}" for selector, style in styles.items()])
            
            # Convert DataFrame to HTML
            html = df.to_html(index=False, na_rep="")
            
            # Add CSS and title
            html = f"""
            <style>
            {css}
            </style>
            <h2>{self.statement.name}</h2>
            {html}
            """
            
            return html
            
        except Exception as e: # pragma: no cover
            if isinstance(e, DataValidationError): 
                # Re-raise DataValidationError
                raise 
            else:
                # Wrap other exceptions
                logger.error(f"Error formatting statement as HTML: {e}")
                raise DataValidationError(
                    message="Failed to format statement as HTML",
                    validation_errors=[f"Formatting error: {str(e)}"]
                ) from e
    
    def get_calculation_dependencies(self) -> Dict[str, Set[str]]:
        """
        Get the calculation dependencies for the statement.
        
        Returns:
            Dict[str, Set[str]]: Dictionary mapping item IDs to sets of dependency IDs
        """
        dependencies = {}
        
        # Get all calculation items
        calc_items = self.statement.get_calculation_items()
        
        # Build dependency map
        for item in calc_items:
            if isinstance(item, (CalculatedLineItem, SubtotalLineItem)):
                dependencies[item.id] = set(item.input_ids)
        
        return dependencies
    
    def validate_calculations(self, data: Dict[str, Dict[str, float]]) -> None:
        """
        Validate that all calculation dependencies are satisfied.
        
        Args:
            data: Dictionary mapping node IDs to period values
            
        Raises:
            DataValidationError: If any dependencies are not satisfied
        """
        # Get dependencies
        dependencies = self.get_calculation_dependencies()
        
        # Check each calculation item
        errors = []
        
        for item_id, deps in dependencies.items():
            # Check if the calculation result is in the data
            if item_id not in data:
                errors.append(f"Calculation result '{item_id}' is missing from data")
                continue
            
            # Check if all dependencies are in the data
            missing_deps = []
            for dep_id in deps:
                if dep_id not in data:
                    missing_deps.append(dep_id)
            
            if missing_deps:
                errors.append(
                    f"Missing dependencies for calculation '{item_id}': {', '.join(missing_deps)}"
                )
        
        # Raise exception if there are errors
        if errors:
            raise DataValidationError(
                message="Statement calculation validation failed",
                validation_errors=errors
            ) 