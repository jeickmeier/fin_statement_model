"""Tests for the fin_statement_model.core.metrics.registry module."""

import tempfile
from pathlib import Path
import logging
import pytest

from fin_statement_model.core.metrics.registry import MetricRegistry
from fin_statement_model.core.errors import ConfigurationError


# Test fixtures
@pytest.fixture
def valid_metric_yaml() -> str:
    """Return a valid metric YAML content."""
    return """---
name: Test Metric
description: A test metric for unit testing
inputs:
  - input1
  - input2
formula: "input1 + input2"
tags: [test, unit_test]
units: currency
"""


@pytest.fixture
def invalid_metric_yaml_missing_field() -> str:
    """Return an invalid metric YAML content missing a required field."""
    return """---
name: Test Metric
description: A test metric for unit testing
inputs:
  - input1
  - input2
# Missing formula field
tags: [test, unit_test]
units: currency
"""


@pytest.fixture
def invalid_metric_yaml_wrong_type() -> str:
    """Return an invalid metric YAML with wrong type for a field."""
    return """---
name: Test Metric
description: A test metric for unit testing
inputs: "This should be a list, not a string"
formula: "input1 + input2"
tags: [test, unit_test]
units: currency
"""


@pytest.fixture
def invalid_yaml_syntax() -> str:
    """Return a YAML with invalid syntax."""
    return """---
name: Test Metric
description: A test metric for unit testing
inputs:
  - input1
  - input2
formula: "input1 + input2
tags: [test, unit_test]  # Missing closing quote in formula
units: currency
"""


@pytest.fixture
def invalid_non_dict_yaml() -> str:
    """Return a YAML that doesn't parse to a dictionary."""
    return """---
- this
- is
- a
- list
- not
- a
- dictionary
"""


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


class TestMetricRegistry:
    """Test cases for the MetricRegistry class."""

    def test_init(self) -> None:
        """Test initialization of the registry."""
        registry = MetricRegistry()
        assert len(registry) == 0
        assert registry.list_metrics() == []

    def test_load_metrics_from_directory_valid(
        self, temp_dir: Path, valid_metric_yaml: str
    ) -> None:
        """Test loading valid metric from a directory."""
        # Create a directory with only a valid metric file
        valid_path = temp_dir / "valid_metric.yaml"
        with open(valid_path, "w") as f:
            f.write(valid_metric_yaml)

        registry = MetricRegistry()
        count = registry.load_metrics_from_directory(temp_dir)
        assert count == 1
        assert len(registry) == 1
        assert "valid_metric" in registry.list_metrics()

        metric = registry.get("valid_metric")
        assert metric["name"] == "Test Metric"
        assert metric["formula"] == "input1 + input2"
        assert len(metric["inputs"]) == 2

    def test_load_metrics_nonexistent_directory(self) -> None:
        """Test loading metrics from a nonexistent directory."""
        registry = MetricRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_metrics_from_directory("/nonexistent/directory")

    def test_load_metrics_invalid_missing_field(
        self, temp_dir: Path, invalid_metric_yaml_missing_field: str
    ) -> None:
        """Test loading a metric with missing required field."""
        # Create a directory with only the invalid file
        invalid_file = temp_dir / "invalid_missing.yaml"
        with open(invalid_file, "w") as f:
            f.write(invalid_metric_yaml_missing_field)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "Missing required fields: ['formula']" in error_msg

    def test_load_metrics_invalid_type(
        self, temp_dir: Path, invalid_metric_yaml_wrong_type: str
    ) -> None:
        """Test loading a metric with wrong type for a field."""
        # Create a directory with only the invalid type file
        invalid_file = temp_dir / "invalid_type.yaml"
        with open(invalid_file, "w") as f:
            f.write(invalid_metric_yaml_wrong_type)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "'inputs' field must be a list" in error_msg

    def test_load_metrics_invalid_yaml_syntax(
        self, temp_dir: Path, invalid_yaml_syntax: str
    ) -> None:
        """Test loading a metric with invalid YAML syntax."""
        # Create a directory with only the invalid syntax file
        invalid_file = temp_dir / "invalid_syntax.yaml"
        with open(invalid_file, "w") as f:
            f.write(invalid_yaml_syntax)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        assert "Invalid YAML syntax" in str(excinfo.value)

    def test_load_metrics_invalid_non_dict(
        self, temp_dir: Path, invalid_non_dict_yaml: str
    ) -> None:
        """Test loading a YAML file that doesn't parse to a dictionary."""
        invalid_file = temp_dir / "non_dict.yaml"
        with open(invalid_file, "w") as f:
            f.write(invalid_non_dict_yaml)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "YAML content must be a dictionary" in error_msg

    def test_get_nonexistent_metric(self) -> None:
        """Test getting a metric that doesn't exist."""
        registry = MetricRegistry()
        with pytest.raises(KeyError) as excinfo:
            registry.get("nonexistent_metric")

        assert "not found" in str(excinfo.value)
        assert "Available:" in str(excinfo.value)

    def test_contains(self, temp_dir: Path, valid_metric_yaml: str) -> None:
        """Test the __contains__ method."""
        # Create a valid metric file
        valid_path = temp_dir / "valid_metric.yaml"
        with open(valid_path, "w") as f:
            f.write(valid_metric_yaml)

        registry = MetricRegistry()
        registry.load_metrics_from_directory(temp_dir)

        assert "valid_metric" in registry
        assert "nonexistent_metric" not in registry

    def test_list_metrics_sorted(self, temp_dir: Path) -> None:
        """Test that list_metrics returns a sorted list."""
        # Create metrics to test sorting
        with open(temp_dir / "aaa_metric.yaml", "w") as f:
            f.write("""---
name: AAA Metric
description: Test sorting
inputs: []
formula: "0"
""")

        with open(temp_dir / "zzz_metric.yaml", "w") as f:
            f.write("""---
name: ZZZ Metric 
description: Test sorting
inputs: []
formula: "0"
""")

        with open(temp_dir / "mmm_metric.yaml", "w") as f:
            f.write("""---
name: MMM Metric
description: Test sorting
inputs: []
formula: "0"
""")

        registry = MetricRegistry()
        registry.load_metrics_from_directory(temp_dir)

        metric_list = registry.list_metrics()
        assert len(metric_list) == 3
        # Should be sorted alphabetically
        assert metric_list[0] == "aaa_metric"
        assert metric_list[1] == "mmm_metric"
        assert metric_list[2] == "zzz_metric"

    def test_validate_name_field_type(self, temp_dir: Path, valid_metric_yaml: str) -> None:
        """Test validation of name field type."""
        test_file = temp_dir / "test_name_type.yaml"

        import yaml

        data = yaml.safe_load(valid_metric_yaml)
        data["name"] = 123  # Invalid type
        with open(test_file, "w") as f:
            yaml.dump(data, f)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "'name' field must be a string" in error_msg

    def test_validate_description_field_type(self, temp_dir: Path, valid_metric_yaml: str) -> None:
        """Test validation of description field type."""
        test_file = temp_dir / "test_description_type.yaml"

        import yaml

        data = yaml.safe_load(valid_metric_yaml)
        data["description"] = ["not", "a", "string"]  # Invalid type
        with open(test_file, "w") as f:
            yaml.dump(data, f)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "'description' field must be a string" in error_msg

    def test_validate_formula_field_type(self, temp_dir: Path, valid_metric_yaml: str) -> None:
        """Test validation of formula field type."""
        test_file = temp_dir / "test_formula_type.yaml"

        import yaml

        data = yaml.safe_load(valid_metric_yaml)
        data["formula"] = {"not": "a string"}  # Invalid type
        with open(test_file, "w") as f:
            yaml.dump(data, f)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "'formula' field must be a string" in error_msg

    def test_validate_inputs_field_type(self, temp_dir: Path, valid_metric_yaml: str) -> None:
        """Test validation of inputs field type."""
        test_file = temp_dir / "test_inputs_type.yaml"

        import yaml

        data = yaml.safe_load(valid_metric_yaml)
        data["inputs"] = "not a list"  # Invalid type
        with open(test_file, "w") as f:
            yaml.dump(data, f)

        registry = MetricRegistry()
        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Invalid metric structure" in error_msg
        assert "'inputs' field must be a list" in error_msg

    def test_no_yaml_dependency(self, monkeypatch) -> None:
        """Test behavior when PyYAML is not installed."""
        registry = MetricRegistry()

        # Simulate PyYAML not being installed
        monkeypatch.setattr("fin_statement_model.core.metrics.registry.HAS_YAML", False)

        with pytest.raises(ImportError) as excinfo:
            registry.load_metrics_from_directory("some/directory")

        assert "PyYAML is required" in str(excinfo.value)

    def test_load_metrics_skips_non_yaml_files(
        self, temp_dir: Path, valid_metric_yaml: str
    ) -> None:
        """Test that non-YAML files are skipped during loading."""
        # Create a valid metric file
        valid_path = temp_dir / "valid_metric.yaml"
        with open(valid_path, "w") as f:
            f.write(valid_metric_yaml)

        # Create a non-YAML file that should be skipped
        with open(temp_dir / "not_a_metric.txt", "w") as f:
            f.write("This is not a YAML file")

        registry = MetricRegistry()
        count = registry.load_metrics_from_directory(temp_dir)

        # Only the YAML file should be loaded
        assert count == 1
        assert len(registry) == 1
        assert "valid_metric" in registry
        assert "not_a_metric" not in registry

    def test_unexpected_exceptions(
        self, temp_dir: Path, valid_metric_yaml: str, monkeypatch
    ) -> None:
        """Test handling of unexpected exceptions during metric loading."""
        # Create a valid metric file
        valid_path = temp_dir / "valid_metric.yaml"
        with open(valid_path, "w") as f:
            f.write(valid_metric_yaml)

        # Mock the open function to raise an unexpected exception
        def mock_open(*args, **kwargs):
            raise RuntimeError("Simulated unexpected error")

        registry = MetricRegistry()
        monkeypatch.setattr("builtins.open", mock_open)

        with pytest.raises(ConfigurationError) as excinfo:
            registry.load_metrics_from_directory(temp_dir)

        error_msg = str(excinfo.value)
        assert "Failed to load metric" in error_msg
        assert "Simulated unexpected error" in error_msg
        # Check path if needed
        # assert str(valid_path) in error_msg

    def test_overwrite_existing_metric(
        self, temp_dir: Path, valid_metric_yaml: str, caplog
    ) -> None:
        """Test overwriting an existing metric."""
        # Create a metric file
        metric_path = temp_dir / "test_metric.yaml"
        with open(metric_path, "w") as f:
            f.write(valid_metric_yaml)

        registry = MetricRegistry()

        # First load
        registry.load_metrics_from_directory(temp_dir)
        assert len(registry) == 1

        # Modify the metric
        import yaml

        data = yaml.safe_load(valid_metric_yaml)
        data["description"] = "Updated description"
        with open(metric_path, "w") as f:
            yaml.dump(data, f)

        # Configure logging capture
        caplog.set_level(logging.WARNING)

        # Second load should log a warning about overwriting
        registry.load_metrics_from_directory(temp_dir)

        # Check the log contains a warning about overwriting
        assert any("Overwriting existing metric" in message for message in caplog.messages)
