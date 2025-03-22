"""
Base adapter interface for financial data sources.

This module defines the base interface that all financial data source adapters must implement,
providing a consistent way to integrate different data sources into the financial statement model.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union
from pathlib import Path

from ..core.financial_statement import FinancialStatementGraph


class DataSourceAdapter(ABC):
    """
    Abstract base class for all financial data source adapters.
    
    This class defines the interface that all adapter implementations must follow.
    By implementing this interface, new data sources can be easily integrated into
    the financial statement model system.
    
    Each adapter should handle:
    1. Connection to the specific data source
    2. Authentication if required
    3. Fetching raw data
    4. Converting raw data to the standardized format
    5. Creating a FinancialStatementGraph from the data
    """
    
    @abstractmethod
    def fetch_statement(self, identifier: str, period_type: str, limit: int, 
                      statement_type: str) -> Dict:
        """
        Fetch raw financial statement data from the source.
        
        Args:
            identifier: Identifier for the entity (e.g., ticker symbol, company ID)
            period_type: Type of time period (e.g., 'FY' for fiscal year, 'QTR' for quarter)
            limit: Maximum number of periods to fetch
            statement_type: Type of financial statement (e.g., 'income_statement', 'balance_sheet')
            
        Returns:
            Dict: Raw financial statement data
            
        Raises:
            ValueError: If there's an issue with the parameters or connection
        """
        pass
    
    @abstractmethod
    def create_statement_graph(self, identifier: str, period_type: str, limit: int, 
                             statement_type: str) -> FinancialStatementGraph:
        """
        Create a FinancialStatementGraph from the source data.
        
        Args:
            identifier: Identifier for the entity (e.g., ticker symbol, company ID)
            period_type: Type of time period (e.g., 'FY' for fiscal year, 'QTR' for quarter)
            limit: Maximum number of periods to fetch
            statement_type: Type of financial statement (e.g., 'income_statement', 'balance_sheet')
            
        Returns:
            FinancialStatementGraph: Graph containing the financial statement data
            
        Raises:
            ValueError: If there's an issue creating the graph from the data
        """
        pass
    
    @abstractmethod
    def get_field_mapping(self, statement_type: str) -> Dict[str, str]:
        """
        Get the mapping of source field names to standardized node names.
        
        Args:
            statement_type: Type of financial statement (e.g., 'income_statement', 'balance_sheet')
            
        Returns:
            Dict[str, str]: Mapping of source field names to standardized node names
        """
        pass


class FileDataSourceAdapter(DataSourceAdapter):
    """
    Base class for file-based data source adapters (e.g., Excel, CSV).
    
    This class extends the base adapter interface with common functionality for file-based sources.
    """
    
    @abstractmethod
    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validate that the file exists and has the expected format.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file is valid, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        pass
    
    @abstractmethod
    def extract_periods(self, data: Any) -> List[str]:
        """
        Extract time periods from the file data.
        
        Args:
            data: Raw data extracted from the file
            
        Returns:
            List[str]: List of time period identifiers
        """
        pass


class APIDataSourceAdapter(DataSourceAdapter):
    """
    Base class for API-based data source adapters (e.g., FMP, Alpha Vantage).
    
    This class extends the base adapter interface with common functionality for API-based sources.
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the API.
        
        Returns:
            bool: True if authentication was successful, False otherwise
            
        Raises:
            ValueError: If authentication fails
        """
        pass
    
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """
        Validate that the API response is valid.
        
        Args:
            response: Raw API response
            
        Returns:
            bool: True if the response is valid, False otherwise
            
        Raises:
            ValueError: If the response is invalid
        """
        pass 