"""Unit tests for the errors module.

This module contains test cases for all custom exceptions defined in the
Financial Statement Model.
"""

import pytest
from fin_statement_model.core.errors import (
    FinancialModelError,
    ConfigurationError,
    CalculationError,
    NodeError,
    GraphError,
    DataValidationError,
    CircularDependencyError,
    PeriodError,
    StatementError,
    StrategyError,
    ImportError,
    ExportError,
    TransformationError
)


class TestFinancialModelError:
    """Test cases for the base FinancialModelError class."""

    def test_base_error(self):
        """Test basic error message handling."""
        error = FinancialModelError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"


class TestConfigurationError:
    """Test cases for ConfigurationError."""

    def test_basic_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"

    def test_error_with_config_path(self):
        """Test error with config path."""
        error = ConfigurationError("Invalid YAML", config_path="config.yaml")
        assert str(error) == "Invalid YAML in config.yaml"

    def test_error_with_errors_list(self):
        """Test error with list of errors."""
        errors = ["Missing required field: name", "Invalid type for field: value"]
        error = ConfigurationError("Configuration validation failed", errors=errors)
        assert str(error) == "Configuration validation failed: Missing required field: name; Invalid type for field: value"

    def test_error_with_both_config_path_and_errors(self):
        """Test error with both config path and errors list."""
        errors = ["Missing required field: name"]
        error = ConfigurationError("Invalid config", config_path="config.yaml", errors=errors)
        assert str(error) == "Invalid config in config.yaml: Missing required field: name"


class TestCalculationError:
    """Test cases for CalculationError."""

    def test_basic_error(self):
        """Test basic calculation error."""
        error = CalculationError("Division by zero")
        assert str(error) == "Division by zero"

    def test_error_with_node_id(self):
        """Test error with node ID."""
        error = CalculationError("Failed to calculate", node_id="profit")
        assert str(error) == "Failed to calculate for node 'profit'"

    def test_error_with_period(self):
        """Test error with period."""
        error = CalculationError("Missing data", period="2022")
        assert str(error) == "Missing data for period '2022'"

    def test_error_with_node_and_period(self):
        """Test error with both node ID and period."""
        error = CalculationError("Calculation failed", node_id="profit", period="2022")
        assert str(error) == "Calculation failed for node 'profit' and period '2022'"

    def test_error_with_details(self):
        """Test error with additional details."""
        details = {"error": "Division by zero", "context": "profit calculation"}
        error = CalculationError("Calculation failed", details=details)
        assert error.details == details


class TestNodeError:
    """Test cases for NodeError."""

    def test_basic_error(self):
        """Test basic node error."""
        error = NodeError("Node not found")
        assert str(error) == "Node not found"

    def test_error_with_node_id(self):
        """Test error with node ID."""
        error = NodeError("Node not found", node_id="revenue")
        assert str(error) == "Node not found for node 'revenue'"


class TestGraphError:
    """Test cases for GraphError."""

    def test_basic_error(self):
        """Test basic graph error."""
        error = GraphError("Invalid graph structure")
        assert str(error) == "Invalid graph structure"

    def test_error_with_nodes(self):
        """Test error with list of nodes."""
        nodes = ["revenue", "expenses", "profit"]
        error = GraphError("Circular dependency", nodes=nodes)
        assert str(error) == "Circular dependency involving nodes: revenue, expenses, profit"


class TestDataValidationError:
    """Test cases for DataValidationError."""

    def test_basic_error(self):
        """Test basic validation error."""
        error = DataValidationError("Invalid data format")
        assert str(error) == "Invalid data format"

    def test_error_with_validation_errors(self):
        """Test error with validation errors list."""
        errors = ["Missing required field", "Invalid value type"]
        error = DataValidationError("Data validation failed", validation_errors=errors)
        assert str(error) == "Data validation failed: Missing required field; Invalid value type"


class TestCircularDependencyError:
    """Test cases for CircularDependencyError."""

    def test_basic_error(self):
        """Test basic circular dependency error."""
        error = CircularDependencyError()
        assert str(error) == "Circular dependency detected"

    def test_error_with_cycle(self):
        """Test error with cycle information."""
        cycle = ["revenue", "profit", "margin", "revenue"]
        error = CircularDependencyError(cycle=cycle)
        assert str(error) == "Circular dependency detected: revenue -> profit -> margin -> revenue"
        assert error.cycle == cycle


class TestPeriodError:
    """Test cases for PeriodError."""

    def test_basic_error(self):
        """Test basic period error."""
        error = PeriodError("Invalid period")
        assert str(error) == "Invalid period"

    def test_error_with_period(self):
        """Test error with specific period."""
        error = PeriodError("Period not found", period="2023")
        assert str(error) == "Period not found for period '2023'"

    def test_error_with_available_periods(self):
        """Test error with available periods."""
        available = ["2021", "2022"]
        error = PeriodError("Period not found", period="2023", available_periods=available)
        assert str(error) == "Period not found for period '2023'. Available periods: 2021, 2022"


class TestStatementError:
    """Test cases for StatementError."""

    def test_basic_error(self):
        """Test basic statement error."""
        error = StatementError("Invalid statement")
        assert str(error) == "Invalid statement"

    def test_error_with_statement_id(self):
        """Test error with statement ID."""
        error = StatementError("Statement not found", statement_id="income_statement")
        assert str(error) == "Statement not found for statement 'income_statement'"


class TestStrategyError:
    """Test cases for StrategyError."""

    def test_basic_error(self):
        """Test basic strategy error."""
        error = StrategyError("Invalid strategy")
        assert str(error) == "Invalid strategy"

    def test_error_with_strategy_type(self):
        """Test error with strategy type."""
        error = StrategyError("Strategy not found", strategy_type="addition")
        assert str(error) == "Strategy not found for strategy type 'addition'"

    def test_error_with_node_id(self):
        """Test error with node ID."""
        error = StrategyError("Strategy failed", node_id="profit")
        assert str(error) == "Strategy failed for node 'profit'"

    def test_error_with_both_strategy_type_and_node(self):
        """Test error with both strategy type and node ID."""
        error = StrategyError("Strategy failed", strategy_type="addition", node_id="profit")
        assert str(error) == "Strategy failed for strategy type 'addition' in node 'profit'"


class TestImportError:
    """Test cases for ImportError."""

    def test_basic_error(self):
        """Test basic import error."""
        error = ImportError("Import failed")
        assert str(error) == "Import failed"

    def test_error_with_source(self):
        """Test error with source."""
        error = ImportError("File not found", source="data.csv")
        assert str(error) == "File not found from source 'data.csv'"

    def test_error_with_adapter(self):
        """Test error with adapter."""
        error = ImportError("Adapter error", adapter="csv_adapter")
        assert str(error) == "Adapter error using adapter 'csv_adapter'"

    def test_error_with_original_error(self):
        """Test error with original error."""
        original = ValueError("File not found")
        error = ImportError("Import failed", original_error=original)
        assert str(error) == "Import failed: File not found"


class TestExportError:
    """Test cases for ExportError."""

    def test_basic_error(self):
        """Test basic export error."""
        error = ExportError("Export failed")
        assert str(error) == "Export failed"

    def test_error_with_target(self):
        """Test error with target."""
        error = ExportError("File not found", target="output.csv")
        assert str(error) == "File not found to target 'output.csv'"

    def test_error_with_format_type(self):
        """Test error with format type."""
        error = ExportError("Format error", format_type="csv")
        assert str(error) == "Format error in format 'csv'"

    def test_error_with_original_error(self):
        """Test error with original error."""
        original = ValueError("Permission denied")
        error = ExportError("Export failed", original_error=original)
        assert str(error) == "Export failed: Permission denied"


class TestTransformationError:
    """Test cases for TransformationError."""

    def test_basic_error(self):
        """Test basic transformation error."""
        error = TransformationError("Transformation failed")
        assert str(error) == "Transformation failed"

    def test_error_with_transformer_type(self):
        """Test error with transformer type."""
        error = TransformationError("Invalid transformer", transformer_type="normalize")
        assert str(error) == "Invalid transformer in transformer 'normalize'"

    def test_error_with_parameters(self):
        """Test error with parameters."""
        params = {"method": "zscore", "axis": 0}
        error = TransformationError("Invalid parameters", transformer_type="normalize", parameters=params)
        assert str(error) == "Invalid parameters in transformer 'normalize' with parameters: method=zscore, axis=0" 