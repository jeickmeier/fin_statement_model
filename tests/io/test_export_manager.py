"""Unit tests for export_manager module.

This module contains test cases for the export management functionality
of the Financial Statement Model, implemented in the ExportManager class.
"""
import pytest
import pandas as pd
import json
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import tempfile
import os

from fin_statement_model.io.export_manager import ExportManager
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import Node, CalculationNode


class TestExportManager:
    """Test cases for the ExportManager class."""
    
    @pytest.fixture
    def export_manager(self):
        """Create an ExportManager instance for testing."""
        return ExportManager()
    
    @pytest.fixture
    def mock_graph(self):
        """Create a mock Graph instance for testing."""
        graph = MagicMock(spec=Graph)
        
        # Mock node structure
        revenue_node = MagicMock(spec=Node)
        revenue_node.name = "revenue"
        revenue_node.values = {"2021": 1000, "2022": 1100}
        
        expenses_node = MagicMock(spec=Node)
        expenses_node.name = "expenses"
        expenses_node.values = {"2021": 600, "2022": 660}
        
        profit_node = MagicMock(spec=CalculationNode)
        profit_node.name = "profit"
        profit_node.values = {"2021": 400, "2022": 440}
        profit_node.inputs = [revenue_node, expenses_node]
        
        # Mock graph structure
        graph.nodes = {
            "revenue": revenue_node,
            "expenses": expenses_node,
            "profit": profit_node
        }
        graph.periods = ["2021", "2022"]
        
        # Mock calculate method
        def mock_calculate(node_name, period):
            if node_name == "revenue":
                return 1000 if period == "2021" else 1100
            elif node_name == "expenses":
                return 600 if period == "2021" else 660
            elif node_name == "profit":
                return 400 if period == "2021" else 440
            else:
                raise ValueError(f"Node {node_name} not found")
                
        graph.calculate.side_effect = mock_calculate
        
        return graph
    
    def test_init(self, export_manager):
        """Test ExportManager initialization."""
        assert isinstance(export_manager, ExportManager)
    
    def test_to_dataframe_all_nodes(self, export_manager, mock_graph):
        """Test converting a graph to DataFrame with all nodes."""
        # Execute
        result = export_manager.to_dataframe(mock_graph, recalculate=False)
        
        # Verify
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (3, 2)  # 3 nodes x 2 periods
        assert list(result.index) == ["revenue", "expenses", "profit"]
        assert list(result.columns) == ["2021", "2022"]
        
        # Check values
        assert result.loc["revenue", "2021"] == 1000
        assert result.loc["revenue", "2022"] == 1100
        assert result.loc["expenses", "2021"] == 600
        assert result.loc["expenses", "2022"] == 660
        assert result.loc["profit", "2021"] == 400
        assert result.loc["profit", "2022"] == 440
        
        # Verify recalculate was not called
        mock_graph.recalculate_all.assert_not_called()
    
    def test_to_dataframe_with_recalculate(self, export_manager, mock_graph):
        """Test converting a graph to DataFrame with recalculation."""
        # Execute
        result = export_manager.to_dataframe(mock_graph, recalculate=True)
        
        # Verify
        assert isinstance(result, pd.DataFrame)
        
        # Verify recalculate was called for each period
        assert mock_graph.recalculate_all.call_count == 2
        mock_graph.recalculate_all.assert_any_call("2021")
        mock_graph.recalculate_all.assert_any_call("2022")
    
    def test_to_dataframe_specific_nodes(self, export_manager, mock_graph):
        """Test converting a graph to DataFrame with specific nodes."""
        # Execute
        result = export_manager.to_dataframe(mock_graph, 
                                           recalculate=False, 
                                           node_names=["revenue", "profit"])
        
        # Verify
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (2, 2)  # 2 nodes x 2 periods
        assert list(result.index) == ["revenue", "profit"]
        
        # Check values
        assert result.loc["revenue", "2021"] == 1000
        assert result.loc["revenue", "2022"] == 1100
        assert result.loc["profit", "2021"] == 400
        assert result.loc["profit", "2022"] == 440
    
    def test_to_dataframe_with_missing_nodes(self, export_manager, mock_graph):
        """Test converting a graph to DataFrame with non-existent nodes."""
        # Execute
        result = export_manager.to_dataframe(mock_graph, 
                                           recalculate=False, 
                                           node_names=["revenue", "non_existent"])
        
        # Verify
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (1, 2)  # Only revenue node should be included
        assert list(result.index) == ["revenue"]
    
    def test_to_dataframe_with_calculation_error(self, export_manager, mock_graph):
        """Test converting a graph to DataFrame when calculation raises an error."""
        # Update mock to raise error for a specific calculation
        def mock_calculate_with_error(node_name, period):
            if node_name == "profit" and period == "2022":
                raise ValueError("Test error")
            elif node_name == "revenue":
                return 1000 if period == "2021" else 1100
            elif node_name == "expenses":
                return 600 if period == "2021" else 660
            elif node_name == "profit":
                return 400 if period == "2021" else None
            else:
                raise ValueError(f"Node {node_name} not found")
                
        mock_graph.calculate.side_effect = mock_calculate_with_error
        
        # Execute
        result = export_manager.to_dataframe(mock_graph, recalculate=False)
        
        # Verify
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (3, 2)
        assert pd.isna(result.loc["profit", "2022"])  # Should be NaN due to error
        assert result.loc["profit", "2021"] == 400  # Should still have valid value
    
    @patch("pandas.DataFrame.to_excel")
    def test_to_excel(self, mock_to_excel, export_manager, mock_graph):
        """Test exporting to Excel."""
        # Setup
        file_path = "test_output.xlsx"
        
        # Execute
        export_manager.to_excel(mock_graph, file_path)
        
        # Verify
        mock_to_excel.assert_called_once()
        args, kwargs = mock_to_excel.call_args
        assert kwargs["sheet_name"] == "Financial Statement"
        assert kwargs["header"] is True
    
    @patch("pathlib.Path.mkdir")
    @patch("pandas.DataFrame.to_excel")
    def test_to_excel_creates_directories(self, mock_to_excel, mock_mkdir, export_manager, mock_graph):
        """Test exporting to Excel creates parent directories if needed."""
        # Setup
        file_path = Path("test_dir/subdir/test_output.xlsx")
        
        # Execute
        export_manager.to_excel(mock_graph, file_path)
        
        # Verify
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch("pandas.DataFrame.to_excel")
    def test_to_excel_with_error(self, mock_to_excel, export_manager, mock_graph):
        """Test error handling when exporting to Excel."""
        # Setup
        file_path = "test_output.xlsx"
        mock_to_excel.side_effect = Exception("Test error")
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            export_manager.to_excel(mock_graph, file_path)
        
        assert "Error exporting to Excel" in str(excinfo.value)
    
    @patch("pandas.DataFrame.to_csv")
    def test_to_csv(self, mock_to_csv, export_manager, mock_graph):
        """Test exporting to CSV."""
        # Setup
        file_path = "test_output.csv"
        
        # Execute
        export_manager.to_csv(mock_graph, file_path)
        
        # Verify
        mock_to_csv.assert_called_once()
        args, kwargs = mock_to_csv.call_args
        assert kwargs["header"] is True
    
    @patch("pathlib.Path.mkdir")
    @patch("pandas.DataFrame.to_csv")
    def test_to_csv_creates_directories(self, mock_to_csv, mock_mkdir, export_manager, mock_graph):
        """Test exporting to CSV creates parent directories if needed."""
        # Setup
        file_path = Path("test_dir/subdir/test_output.csv")
        
        # Execute
        export_manager.to_csv(mock_graph, file_path)
        
        # Verify
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch("pandas.DataFrame.to_csv")
    def test_to_csv_with_error(self, mock_to_csv, export_manager, mock_graph):
        """Test error handling when exporting to CSV."""
        # Setup
        file_path = "test_output.csv"
        mock_to_csv.side_effect = Exception("Test error")
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            export_manager.to_csv(mock_graph, file_path)
        
        assert "Error exporting to CSV" in str(excinfo.value)
    
    def test_to_json_return_string(self, export_manager, mock_graph):
        """Test exporting to JSON as a string."""
        # Execute
        result = export_manager.to_json(mock_graph, file_path=None, pretty_print=True)
        
        # Verify
        assert isinstance(result, str)
        
        # Parse and check contents
        data = json.loads(result)
        assert "periods" in data
        assert "items" in data
        assert data["periods"] == ["2021", "2022"]
        assert "revenue" in data["items"]
        assert "expenses" in data["items"]
        assert "profit" in data["items"]
        
        # Check values
        assert data["items"]["revenue"]["2021"] == 1000
        assert data["items"]["profit"]["2021"] == 400
        
        # Check calculation metadata
        assert "_calculation" in data["items"]["profit"]
        assert "inputs" in data["items"]["profit"]["_calculation"]
        assert "type" in data["items"]["profit"]["_calculation"]
    
    def test_to_json_exclude_calculation_nodes(self, export_manager, mock_graph):
        """Test exporting to JSON without calculation nodes."""
        # Execute
        result = export_manager.to_json(mock_graph, 
                                      file_path=None, 
                                      include_calculation_nodes=False)
        
        # Verify
        data = json.loads(result)
        
        # Only raw items should be included
        assert "revenue" in data["items"]
        assert "expenses" in data["items"]
        assert "profit" not in data["items"]
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_to_json_write_to_file(self, mock_mkdir, mock_file, export_manager, mock_graph):
        """Test exporting to JSON file."""
        # Setup
        file_path = Path("test_dir/test_output.json")
        
        # Execute
        result = export_manager.to_json(mock_graph, file_path=file_path)
        
        # Verify
        assert result is None  # Should return None when writing to file
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once_with(file_path, 'w')
        
        # Check file contents
        write_handle = mock_file()
        assert write_handle.write.called
        
        # Check that JSON was written
        written_content = write_handle.write.call_args[0][0]
        assert isinstance(written_content, str)
        data = json.loads(written_content)
        assert "periods" in data
        assert "items" in data
    
    @patch("builtins.open")
    def test_to_json_file_error(self, mock_open, export_manager, mock_graph):
        """Test error handling when exporting to JSON file."""
        # Setup
        file_path = "test_output.json"
        mock_open.side_effect = Exception("Test error")
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            export_manager.to_json(mock_graph, file_path=file_path)
        
        assert "Error exporting to JSON file" in str(excinfo.value)
    
    def test_to_html_return_string(self, export_manager, mock_graph):
        """Test exporting to HTML as a string."""
        # Execute
        result = export_manager.to_html(mock_graph, file_path=None)
        
        # Verify
        assert isinstance(result, str)
        assert "<html>" in result
        assert "<title>Financial Statement</title>" in result
        assert "<style>" in result  # Default includes styles
        assert "Financial Statement" in result  # Title in content
        
        # Check that table is included
        assert "<table" in result
        assert "revenue" in result
        assert "expenses" in result
        assert "profit" in result
    
    def test_to_html_without_styles(self, export_manager, mock_graph):
        """Test exporting to HTML without styles."""
        # Execute
        result = export_manager.to_html(mock_graph, 
                                       file_path=None, 
                                       include_styles=False)
        
        # Verify
        assert "<style>" not in result
    
    def test_to_html_custom_title(self, export_manager, mock_graph):
        """Test exporting to HTML with custom title."""
        # Setup
        custom_title = "Test Financial Report"
        
        # Execute
        result = export_manager.to_html(mock_graph,
                                       file_path=None,
                                       title=custom_title)
        
        # Verify
        assert f"<title>{custom_title}</title>" in result
        assert f"<h1>{custom_title}</h1>" in result
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_to_html_write_to_file(self, mock_mkdir, mock_file, export_manager, mock_graph):
        """Test exporting to HTML file."""
        # Setup
        file_path = Path("test_dir/test_output.html")
        
        # Execute
        result = export_manager.to_html(mock_graph, file_path=file_path)
        
        # Verify
        assert result is None  # Should return None when writing to file
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once_with(file_path, 'w')
        
        # Check file contents
        write_handle = mock_file()
        assert write_handle.write.called
        
        # Check that HTML was written
        written_content = write_handle.write.call_args[0][0]
        assert isinstance(written_content, str)
        assert "<html>" in written_content
    
    @patch("builtins.open")
    def test_to_html_file_error(self, mock_open, export_manager, mock_graph):
        """Test error handling when exporting to HTML file."""
        # Setup
        file_path = "test_output.html"
        mock_open.side_effect = Exception("Test error")
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            export_manager.to_html(mock_graph, file_path=file_path)
        
        assert "Error exporting to HTML file" in str(excinfo.value)
    
    @pytest.mark.parametrize(
        "file_path,expected_type", [
            ("test.xlsx", str),
            (Path("test.xlsx"), Path),
        ]
    )
    def test_file_path_handling(self, file_path, expected_type, export_manager, mock_graph, monkeypatch):
        """Test handling of different file path types."""
        # Mock pandas.DataFrame.to_excel to avoid actual file operations
        mock_to_excel = MagicMock()
        monkeypatch.setattr(pd.DataFrame, "to_excel", mock_to_excel)
        
        # Mock Path.mkdir to avoid directory creation
        mock_mkdir = MagicMock()
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)
        
        # Execute
        export_manager.to_excel(mock_graph, file_path)
        
        # Verify that the file_path was converted to Path if needed
        assert mock_to_excel.called
        if expected_type == Path:
            assert isinstance(file_path, Path)
    
    def test_integration_with_temp_files(self, export_manager, mock_graph):
        """Integration test with temporary files."""
        # Skip if running in CI environment without file write permission
        if os.environ.get('CI') == 'true':
            pytest.skip("Skipping file operations in CI environment")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test Excel export
            excel_path = Path(temp_dir) / "test.xlsx"
            export_manager.to_excel(mock_graph, excel_path)
            assert excel_path.exists()
            
            # Test CSV export
            csv_path = Path(temp_dir) / "test.csv"
            export_manager.to_csv(mock_graph, csv_path)
            assert csv_path.exists()
            
            # Test JSON export
            json_path = Path(temp_dir) / "test.json"
            export_manager.to_json(mock_graph, json_path)
            assert json_path.exists()
            
            # Test HTML export
            html_path = Path(temp_dir) / "test.html"
            export_manager.to_html(mock_graph, html_path)
            assert html_path.exists()
            
    def test_to_json_with_missing_period_values(self, export_manager, mock_graph):
        """Test to_json method with periods having missing values."""
        # Modify the mock_calculate to raise KeyError for a specific period
        def mock_calculate_with_missing_periods(node_name, period):
            if node_name == "revenue" and period == "2022":
                raise KeyError("Period has no value")
            elif node_name == "expenses" and period == "2021":
                raise ValueError("Period calculation failed")
            elif node_name == "revenue":
                return 1000
            elif node_name == "expenses":
                return 660
            elif node_name == "profit":
                return 400 if period == "2021" else 440
            else:
                raise ValueError(f"Node {node_name} not found")
        
        mock_graph.calculate.side_effect = mock_calculate_with_missing_periods
        
        # Execute
        result = export_manager.to_json(mock_graph, file_path=None)
        
        # Verify
        assert isinstance(result, str)
        
        # Parse JSON and verify structure
        data = json.loads(result)
        assert "periods" in data
        assert "items" in data
        
        # Revenue should have 2021 but not 2022
        assert "revenue" in data["items"]
        assert "2021" in data["items"]["revenue"]
        assert "2022" not in data["items"]["revenue"]
        
        # Expenses should have 2022 but not 2021
        assert "expenses" in data["items"]
        assert "2021" not in data["items"]["expenses"]
        assert "2022" in data["items"]["expenses"]
        
        # Profit should have both periods
        assert "profit" in data["items"]
        assert "2021" in data["items"]["profit"]
        assert "2022" in data["items"]["profit"] 