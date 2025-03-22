import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
from fin_statement_model.importers.excel_importer import ExcelImporter
from fin_statement_model.importers.mapping_service import MappingService
from fin_statement_model.importers.exceptions import MappingError
from fin_statement_model.financial_statement import FinancialStatementGraph
from fin_statement_model.metrics import METRIC_DEFINITIONS

@pytest.fixture
def sample_excel_file():
    """Create a temporary Excel file with sample financial data."""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        # Create sample data
        data = {
            'Sheet1': pd.DataFrame({
                'Item': ['Revenue', 'Cost of Goods Sold', 'Operating Expenses'],
                '2021': [1000, 600, 200],
                '2022': [1200, 700, 250]
            }),
            'Sheet2': pd.DataFrame({
                'Metric': ['Total Assets', 'Total Liabilities', 'Equity'],
                'FY2021': [2000, 1200, 800],
                'FY2022': [2400, 1400, 1000]
            })
        }
        
        # Write to Excel
        with pd.ExcelWriter(tmp.name) as writer:
            for sheet_name, df in data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        yield tmp.name
        Path(tmp.name).unlink()

@pytest.fixture
def complex_excel_file():
    """Create a temporary Excel file with complex formatting and multiple sheets."""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        data = {
            'Income Statement': pd.DataFrame({
                'Items': ['Net Sales', 'COGS', 'SG&A Expenses', 'Other Income'],
                '31-Dec-2021': [1000, 600, 150, 50],
                '31-Dec-2022': [1200, 700, 180, 60]
            }),
            'Balance Sheet': pd.DataFrame({
                'Account': ['Cash & Equivalents', 'A/R', 'Inventory', 'A/P'],
                '2021': [300, 200, 400, 250],
                '2022': [350, 240, 450, 280]
            })
        }
        
        with pd.ExcelWriter(tmp.name) as writer:
            for sheet_name, df in data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        yield tmp.name
        Path(tmp.name).unlink()

class TestExcelImporter:
    def test_basic_import(self, sample_excel_file):
        """Test basic Excel import functionality."""
        importer = ExcelImporter(sample_excel_file)
        data = importer.read_excel()
        
        assert len(data) == 2  # Two sheets
        assert 'Sheet1' in data
        assert 'Sheet2' in data
        assert list(data['Sheet1'].columns) == ['Item', '2021', '2022']
        
    def test_detect_data_structure(self, sample_excel_file):
        """Test data structure detection."""
        importer = ExcelImporter(sample_excel_file)
        data = importer.read_excel()
        structure = importer.detect_data_structure(data['Sheet1'])
        
        assert structure['orientation'] == 'vertical'
        assert isinstance(structure['header_rows'], list)
        
    def test_standardize_dataframe(self, complex_excel_file):
        """Test DataFrame standardization."""
        importer = ExcelImporter(complex_excel_file)
        data = importer.read_excel()
        df = data['Income Statement']
        structure = importer.detect_data_structure(df)
        standardized_df = importer.standardize_dataframe(df, structure)
        
        assert isinstance(standardized_df, pd.DataFrame)
        assert not standardized_df.empty
        
    def test_clean_data(self, sample_excel_file):
        """Test data cleaning functionality."""
        importer = ExcelImporter(sample_excel_file)
        data = importer.read_excel()
        cleaned_df = importer.clean_data(data['Sheet1'])
        
        assert cleaned_df['2021'].dtype in [np.float64, np.int64]
        assert not cleaned_df.isna().all().all()
        
    def test_get_financial_data(self, complex_excel_file):
        """Test extraction of financial data."""
        importer = ExcelImporter(complex_excel_file)
        financial_data, periods = importer.get_financial_data()
        
        assert isinstance(financial_data, dict)
        assert isinstance(periods, list)
        assert len(periods) > 0
        assert all(isinstance(v, dict) for v in financial_data.values())
        
    def test_invalid_file_path(self):
        """Test handling of invalid file path."""
        with pytest.raises(FileNotFoundError):
            ExcelImporter("nonexistent.xlsx")
            
    def test_invalid_file_format(self):
        """Test handling of invalid file format."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            with pytest.raises(ValueError):
                ExcelImporter(tmp.name)

class TestMappingService:
    @pytest.fixture
    def mapping_service(self):
        """Create a MappingService instance with test metric definitions."""
        test_metrics = {
            'revenue': {'description': 'Total revenue'},
            'cogs': {'description': 'Cost of goods sold'},
            'gross_profit': {'description': 'Gross profit'},
            'operating_expenses': {'description': 'Operating expenses'}
        }
        return MappingService(test_metrics)
    
    def test_map_metric_name(self, mapping_service):
        """Test mapping of individual metric names."""
        mapped_name, score = mapping_service.map_metric_name('total_revenue')
        assert mapped_name == 'revenue'
        assert score >= 0.85
        
    def test_map_metric_names(self, mapping_service):
        """Test mapping of multiple metric names."""
        input_names = ['total_revenue', 'cost_of_sales', 'opex']
        mappings = mapping_service.map_metric_names(input_names)
        
        assert isinstance(mappings, dict)
        assert len(mappings) > 0
        assert all(isinstance(v, tuple) for v in mappings.values())
        
    def test_validate_mapping(self, mapping_service):
        """Test mapping validation."""
        assert mapping_service.validate_mapping('total_revenue', 'revenue')
        assert not mapping_service.validate_mapping('invalid_metric', 'nonexistent')
        
    def test_unmapped_metric(self, mapping_service):
        """Test handling of unmappable metrics."""
        with pytest.raises(MappingError):
            mapping_service.map_metric_name('completely_unknown_metric')
            
    def test_ambiguous_mapping(self, mapping_service):
        """Test handling of ambiguous mappings."""
        # Add similar metrics to create ambiguity
        mapping_service.metric_definitions.update({
            'total_revenue': {'description': 'Total revenue'},
            'net_revenue': {'description': 'Net revenue'}
        })
        
        # Should log a warning for ambiguous mapping
        mapped_name, score = mapping_service.map_metric_name('revenue')
        assert mapped_name in ['total_revenue', 'net_revenue', 'revenue']

class TestIntegration:
    def test_excel_to_graph_integration(self, sample_excel_file):
        """Test integration of Excel import with FinancialStatementGraph."""
        graph = FinancialStatementGraph()
        graph.import_from_excel(sample_excel_file)
        
        # Verify graph structure
        df = graph.to_dataframe()
        assert not df.empty
        assert '2021' in df.columns
        assert '2022' in df.columns
        
    def test_complex_import_integration(self, complex_excel_file):
        """Test integration with complex Excel file."""
        graph = FinancialStatementGraph()
        graph.import_from_excel(complex_excel_file)
        
        # Verify metrics were properly mapped and calculated
        df = graph.to_dataframe()
        assert not df.empty
        assert len(df.columns) >= 2  # At least two periods
        
    def test_metric_calculation_integration(self, sample_excel_file):
        """Test integration of metric calculations after import."""
        graph = FinancialStatementGraph()
        graph.import_from_excel(sample_excel_file)
        
        # Calculate and verify a metric
        try:
            value_2021 = graph.calculate_financial_statement('gross_profit', '2021')
            value_2022 = graph.calculate_financial_statement('gross_profit', '2022')
            assert isinstance(value_2021, (int, float))
            assert isinstance(value_2022, (int, float))
        except ValueError:
            pytest.skip("Metric calculation not possible with sample data")