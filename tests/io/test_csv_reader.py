"""Tests for the CSV reader."""

import pytest
import pandas as pd

from fin_statement_model.io.readers.csv import CsvReader
from fin_statement_model.io.config.models import CsvReaderConfig
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.core.graph import Graph


class TestCsvReader:
    """Test the CSV reader functionality."""

    def test_read_csv_success(self, tmp_path):
        """Test successful CSV reading."""
        # Create a test CSV file
        csv_file = tmp_path / "test_data.csv"
        data = {
            "item": ["revenue", "cost_of_goods_sold", "gross_profit"],
            "period": ["2023", "2023", "2023"],
            "value": [1000, 600, 400],
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)

        # Create reader with config
        config = CsvReaderConfig(
            source=str(csv_file), format_type="csv", delimiter=",", header_row=1
        )
        reader = CsvReader(config)

        # Read the file
        graph = reader.read(str(csv_file), item_col="item", period_col="period", value_col="value")

        # Verify results
        assert isinstance(graph, Graph)
        assert len(graph.nodes) == 3
        assert graph.has_node("revenue")
        assert graph.has_node("cost_of_goods_sold")
        assert graph.has_node("gross_profit")
        assert graph.periods == ["2023"]

        # Check values
        revenue_node = graph.get_node("revenue")
        assert revenue_node.get_value("2023") == 1000

    def test_read_csv_with_mapping(self, tmp_path):
        """Test CSV reading with name mapping."""
        # Create a test CSV file
        csv_file = tmp_path / "test_data.csv"
        data = {
            "item": ["Sales", "COGS", "GP"],
            "period": ["2023", "2023", "2023"],
            "value": [1000, 600, 400],
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)

        # Create reader with mapping config
        config = CsvReaderConfig(
            source=str(csv_file),
            format_type="csv",
            delimiter=",",
            header_row=1,
            mapping_config={
                "Sales": "revenue",
                "COGS": "cost_of_goods_sold",
                "GP": "gross_profit",
            },
        )
        reader = CsvReader(config)

        # Read the file
        graph = reader.read(str(csv_file), item_col="item", period_col="period", value_col="value")

        # Verify mapped names
        assert graph.has_node("revenue")
        assert graph.has_node("cost_of_goods_sold")
        assert graph.has_node("gross_profit")
        assert not graph.has_node("Sales")
        assert not graph.has_node("COGS")

    def test_read_csv_missing_file(self):
        """Test error handling for missing file."""
        config = CsvReaderConfig(source="nonexistent.csv", format_type="csv")
        reader = CsvReader(config)

        with pytest.raises(ReadError) as exc_info:
            reader.read(
                "nonexistent.csv",
                item_col="item",
                period_col="period",
                value_col="value",
            )

        assert "File not found" in str(exc_info.value)

    def test_read_csv_invalid_extension(self, tmp_path):
        """Test error handling for invalid file extension."""
        # Create a file with wrong extension
        wrong_file = tmp_path / "data.xlsx"
        wrong_file.write_text("dummy")

        config = CsvReaderConfig(source=str(wrong_file), format_type="csv")
        reader = CsvReader(config)

        with pytest.raises(ReadError) as exc_info:
            reader.read(str(wrong_file), item_col="item", period_col="period", value_col="value")

        assert "Invalid file extension" in str(exc_info.value)

    def test_read_csv_missing_columns(self, tmp_path):
        """Test error handling for missing required columns."""
        # Create a CSV file missing required columns
        csv_file = tmp_path / "test_data.csv"
        data = {
            "name": ["revenue", "cost"],  # Wrong column name
            "date": ["2023", "2023"],  # Wrong column name
            "amount": [1000, 600],  # Wrong column name
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)

        config = CsvReaderConfig(source=str(csv_file), format_type="csv")
        reader = CsvReader(config)

        with pytest.raises(ReadError) as exc_info:
            reader.read(str(csv_file), item_col="item", period_col="period", value_col="value")

        assert "Missing required columns" in str(exc_info.value)

    def test_read_csv_invalid_values(self, tmp_path):
        """Test handling of non-numeric values."""
        # Create a CSV file with invalid values
        csv_file = tmp_path / "test_data.csv"
        data = {
            "item": ["revenue", "cost", "profit"],
            "period": ["2023", "2023", "2023"],
            "value": [1000, "invalid", 400],
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)

        config = CsvReaderConfig(source=str(csv_file), format_type="csv")
        reader = CsvReader(config)

        with pytest.raises(ReadError) as exc_info:
            reader.read(str(csv_file), item_col="item", period_col="period", value_col="value")

        assert "Validation errors occurred" in str(exc_info.value)
        assert "Non-numeric value" in str(exc_info.value)

    def test_read_csv_multiple_periods(self, tmp_path):
        """Test reading CSV with multiple periods."""
        # Create a CSV file with multiple periods
        csv_file = tmp_path / "test_data.csv"
        data = {
            "item": ["revenue", "revenue", "cost", "cost"],
            "period": ["2022", "2023", "2022", "2023"],
            "value": [900, 1000, 500, 600],
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)

        config = CsvReaderConfig(source=str(csv_file), format_type="csv")
        reader = CsvReader(config)

        graph = reader.read(str(csv_file), item_col="item", period_col="period", value_col="value")

        # Verify periods
        assert sorted(graph.periods) == ["2022", "2023"]

        # Verify values
        revenue_node = graph.get_node("revenue")
        assert revenue_node.get_value("2022") == 900
        assert revenue_node.get_value("2023") == 1000

        cost_node = graph.get_node("cost")
        assert cost_node.get_value("2022") == 500
        assert cost_node.get_value("2023") == 600
