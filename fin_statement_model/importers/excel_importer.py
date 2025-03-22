import pandas as pd
import numpy as np
from typing import Dict, List, Union, Tuple
from pathlib import Path
import re
from datetime import datetime

class ExcelImporter:
    """
    A class to handle importing financial data from Excel files.
    
    This class provides functionality to:
    - Read Excel files with multiple worksheets
    - Extract financial data regardless of format variations
    - Clean and validate the extracted data
    - Prepare data for mapping to standard financial statement items
    
    Attributes:
        file_path (Path): Path to the Excel file
        sheet_names (List[str]): List of sheet names to process
        date_format (str): Expected format for date columns
    """
    
    def __init__(self, file_path: Union[str, Path], sheet_names: List[str] = None, 
                 date_format: str = "%Y-%m-%d"):
        """
        Initialize the ExcelImporter with file path and optional parameters.
        
        Args:
            file_path: Path to the Excel file
            sheet_names: Optional list of specific sheets to process. If None, processes all sheets.
            date_format: Format string for parsing date columns
        
        Raises:
            FileNotFoundError: If the specified Excel file doesn't exist
            ValueError: If the file is not a valid Excel file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        if self.file_path.suffix not in ['.xlsx', '.xls', '.xlsm']:
            raise ValueError(f"Invalid file format. Expected Excel file, got: {self.file_path.suffix}")
                
        self.sheet_names = sheet_names
        self.date_format = date_format
        
        self._read_excel()

    
    def _read_excel(self) -> Dict[str, pd.DataFrame]:
        """
        Read the Excel file and return data from all relevant sheets.
        
        Returns:
            Dict mapping sheet names to their corresponding DataFrames
        
        Raises:
            ValueError: If no valid data is found in the Excel file
        """
        try:
            if self.sheet_names:
                sheets_dict = pd.read_excel(self.file_path, sheet_name=self.sheet_names)
            else:
                sheets_dict = pd.read_excel(self.file_path, sheet_name=None)
            
            if not sheets_dict:
                raise ValueError("No data found in Excel file")
            
            self._data = sheets_dict
        
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {str(e)}")
    
    def detect_data_structure(self, df: pd.DataFrame) -> Dict[str, Union[str, List[int]]]:
        """
        Analyze the structure of a DataFrame to determine its layout.
        
        Args:
            df: DataFrame to analyze
        
        Returns:
            Dict containing:
                'orientation': 'vertical' or 'horizontal'
                'header_rows': List of row indices containing headers
                'data_start': Index where actual data begins
        """
        structure = {
            'orientation': 'vertical',
            'header_rows': [],
            'data_start': 0
        }
        
        # Check for date-like columns (vertical orientation)
        date_cols = []
        for col in df.columns:
            if isinstance(col, (datetime, pd.Timestamp)) or (
                isinstance(col, str) and bool(re.search(r'\d{4}', col))
            ):
                date_cols.append(col)
        
        if date_cols:
            structure['orientation'] = 'vertical'
            return structure
        
        # Look for date-like values in first column (horizontal orientation)
        first_col = df.iloc[:, 0]
        date_rows = []
        for idx, val in enumerate(first_col):
            if isinstance(val, (datetime, pd.Timestamp)) or (
                isinstance(val, str) and bool(re.search(r'\d{4}', str(val)))
            ):
                date_rows.append(idx)
        
        if date_rows:
            structure['orientation'] = 'horizontal'
            structure['header_rows'] = list(range(min(date_rows)))
            structure['data_start'] = min(date_rows)
        
        return structure
    
    def standardize_dataframe(self, df: pd.DataFrame, 
                            structure: Dict[str, Union[str, List[int]]]) -> pd.DataFrame:
        """
        Convert DataFrame to a standardized format with items as rows and periods as columns.
        
        Args:
            df: Input DataFrame
            structure: Data structure information from detect_data_structure()
        
        Returns:
            Standardized DataFrame
        """
        if structure['orientation'] == 'horizontal':
            # Transpose if data is in horizontal format
            header_rows = structure['header_rows']
            data_start = structure['data_start']
            
            # Extract headers
            headers = df.iloc[header_rows].fillna(method='ffill', axis=1)
            header_names = ['_'.join(str(x) for x in col).strip('_') 
                          for col in zip(*headers.values)]
            
            # Extract data
            data = df.iloc[data_start:]
            data.columns = header_names
            
            # Set index from first column
            data = data.set_index(data.columns[0])
            
            return data.T
        
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare the data for further processing.
        
        Performs the following operations:
        - Removes empty rows and columns
        - Standardizes column names
        - Converts numeric values
        - Handles missing values
        
        Args:
            df: DataFrame to clean
        
        Returns:
            Cleaned DataFrame
        """
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Standardize column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Convert numeric values
        for col in df.columns:
            # Skip date columns
            if isinstance(col, (datetime, pd.Timestamp)):
                continue
                
            # Convert string numbers (handle parentheses for negative values)
            if df[col].dtype == object:
                df[col] = df[col].apply(lambda x: self._convert_to_number(x))
        
        return df
    
    def _convert_to_number(self, value: Union[str, float, int]) -> float:
        """
        Convert various number formats to float.
        
        Handles:
        - Parentheses for negative numbers: (100) -> -100
        - Currency symbols: $100 -> 100
        - Thousands separators: 1,000 -> 1000
        - Percentage values: 10% -> 0.1
        
        Args:
            value: Value to convert
        
        Returns:
            Converted float value or np.nan if conversion fails
        """
        if pd.isna(value):
            return np.nan
        
        if isinstance(value, (int, float)):
            return float(value)
        
        try:
            # Remove currency symbols and thousands separators
            value = str(value).strip()
            value = re.sub(r'[,$]', '', value)
            
            # Handle parentheses (negative numbers)
            if value.startswith('(') and value.endswith(')'):
                value = '-' + value[1:-1]
            
            # Handle percentages
            if value.endswith('%'):
                return float(value.rstrip('%')) / 100
            
            return float(value)
        except (ValueError, TypeError):
            return np.nan
    
    def extract_periods(self, df: pd.DataFrame) -> List[str]:
        """
        Extract and standardize period identifiers from the DataFrame.
        
        Args:
            df: DataFrame containing financial data
        
        Returns:
            List of standardized period identifiers
        """
        periods = []
        for col in df.columns:
            if isinstance(col, (datetime, pd.Timestamp)):
                # Convert datetime to string format
                periods.append(col.strftime('%Y-%m-%d'))
            elif isinstance(col, str):
                # Extract year from string (e.g., "FY2022", "2022", "Dec 2022")
                year_match = re.search(r'\d{4}', col)
                if year_match:
                    periods.append(year_match.group(0))
        
        return sorted(list(set(periods)))
    
    def get_financial_data(self) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
        """
        Process the Excel file and return financial data in a format ready for FinancialStatementGraph.
        
        Returns:
            Tuple containing:
            - Dict mapping item names to their period values
            - List of standardized period identifiers
        
        Raises:
            ValueError: If no valid financial data is found
        """
        if self._data is None:
            self.read_excel()
        
        all_items = {}
        all_periods = set()
        
        for sheet_name, df in self._data.items():
            # Detect structure and standardize
            structure = self.detect_data_structure(df)
            df = self.standardize_dataframe(df, structure)
            
            # Clean the data
            df = self.clean_data(df)
            
            # Extract periods
            periods = self.extract_periods(df)
            all_periods.update(periods)
            
            # Extract items and their values
            for idx, row in df.iterrows():
                item_name = str(idx).strip()
                if item_name:
                    values = {}
                    for col, val in row.items():
                        if isinstance(col, (datetime, pd.Timestamp)):
                            period = col.strftime('%Y-%m-%d')
                        else:
                            year_match = re.search(r'\d{4}', str(col))
                            if year_match:
                                period = year_match.group(0)
                            else:
                                continue
                        
                        if not pd.isna(val):
                            values[period] = float(val)
                    
                    if values:
                        all_items[item_name] = values
        
        if not all_items:
            raise ValueError("No valid financial data found in Excel file")
        
        return all_items, sorted(list(all_periods))
