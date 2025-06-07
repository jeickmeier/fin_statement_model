"""Tests for MappingAwareMixin functionality."""

from unittest.mock import Mock, patch
from typing import Optional

from fin_statement_model.io.core.mixins import (
    MappingAwareMixin,
    ConfigurableReaderMixin,
)


class TestMappingAwareMixin:
    """Test the MappingAwareMixin functionality."""

    def setup_method(self):
        """Set up test fixtures."""

        # Create a test class that combines both mixins
        class TestReader(ConfigurableReaderMixin, MappingAwareMixin):
            def __init__(self, cfg=None):
                super().__init__()
                self.cfg = cfg

            @classmethod
            def _get_default_mapping_path(cls) -> Optional[str]:
                return "test_mappings.yaml"

        self.TestReader = TestReader
        # Clear the cache before each test
        MappingAwareMixin._default_mappings_cache.clear()

    def test_get_default_mapping_path_returns_none_by_default(self):
        """Test that _get_default_mapping_path returns None by default."""

        class DefaultReader(MappingAwareMixin):
            pass

        assert DefaultReader._get_default_mapping_path() is None

    def test_get_mapping_no_config_no_defaults(self):
        """Test _get_mapping with no user config and no defaults."""

        class NoDefaultsReader(ConfigurableReaderMixin, MappingAwareMixin):
            def __init__(self):
                super().__init__()
                self.cfg = None

            @classmethod
            def _get_default_mapping_path(cls) -> Optional[str]:
                return None

        reader = NoDefaultsReader()
        mapping = reader._get_mapping()
        assert mapping == {}

    def test_get_mapping_with_user_config_only(self):
        """Test _get_mapping with user config but no defaults."""

        class MockConfig:
            mapping_config = {"Revenue": "revenue", "Cost": "cost"}

        class NoDefaultsReader(ConfigurableReaderMixin, MappingAwareMixin):
            def __init__(self, cfg):
                super().__init__()
                self.cfg = cfg

            @classmethod
            def _get_default_mapping_path(cls) -> Optional[str]:
                return None

        reader = NoDefaultsReader(MockConfig())
        mapping = reader._get_mapping()
        assert mapping == {"Revenue": "revenue", "Cost": "cost"}

    @patch("importlib.resources.files")
    def test_load_default_mappings_success(self, mock_files):
        """Test successful loading of default mappings."""
        # Mock the YAML content
        yaml_content = """
        income_statement:
          Revenue: revenue
          COGS: cogs
        balance_sheet:
          Cash: cash
          Debt: debt
        """

        # Mock the file reading chain
        mock_file = Mock()
        mock_file.read_text.return_value = yaml_content
        mock_files.return_value.joinpath.return_value = mock_file

        reader = self.TestReader()
        mappings = reader._load_default_mappings()

        expected = {
            "income_statement": {"Revenue": "revenue", "COGS": "cogs"},
            "balance_sheet": {"Cash": "cash", "Debt": "debt"},
        }
        assert mappings == expected

    @patch("importlib.resources.files")
    def test_load_default_mappings_file_not_found(self, mock_files):
        """Test handling of missing default mapping file."""
        mock_files.return_value.joinpath.return_value.read_text.side_effect = (
            FileNotFoundError()
        )

        reader = self.TestReader()
        mappings = reader._load_default_mappings()

        assert mappings == {}
        # Check that it's cached
        assert self.TestReader._default_mappings_cache["TestReader"] == {}

    @patch("importlib.resources.files")
    def test_load_default_mappings_caching(self, mock_files):
        """Test that default mappings are cached."""
        yaml_content = "test: mapping"
        mock_file = Mock()
        mock_file.read_text.return_value = yaml_content
        mock_files.return_value.joinpath.return_value = mock_file

        reader1 = self.TestReader()
        reader2 = self.TestReader()

        # First call should load from file
        mappings1 = reader1._load_default_mappings()
        # Second call should use cache
        mappings2 = reader2._load_default_mappings()

        assert mappings1 == mappings2
        # File should only be read once
        mock_file.read_text.assert_called_once()

    @patch("importlib.resources.files")
    def test_get_mapping_with_defaults_and_user_config(self, mock_files):
        """Test _get_mapping with both defaults and user config."""
        # Mock default mappings
        yaml_content = """
        null:
          Revenue: revenue
          Cost: cost
        income_statement:
          EBIT: operating_income
        """
        mock_file = Mock()
        mock_file.read_text.return_value = yaml_content
        mock_files.return_value.joinpath.return_value = mock_file

        # Mock user config
        class MockConfig:
            mapping_config = {
                None: {"Revenue": "total_revenue"},  # Override default
                "income_statement": {"Net Income": "net_income"},  # Add new mapping
            }

        reader = self.TestReader(MockConfig())
        mapping = reader._get_mapping("income_statement")

        # Should have defaults + user overrides for income_statement context
        expected = {
            "Revenue": "total_revenue",  # User override
            "Cost": "cost",  # From defaults
            "EBIT": "operating_income",  # From defaults for income_statement
            "Net Income": "net_income",  # From user config for income_statement
        }
        assert mapping == expected

    @patch("importlib.resources.files")
    def test_get_mapping_with_context_key(self, mock_files):
        """Test _get_mapping with specific context key."""
        yaml_content = """
        null:
          Revenue: revenue
        balance_sheet:
          Cash: cash_and_equivalents
        """
        mock_file = Mock()
        mock_file.read_text.return_value = yaml_content
        mock_files.return_value.joinpath.return_value = mock_file

        reader = self.TestReader()
        mapping = reader._get_mapping("balance_sheet")

        expected = {"Revenue": "revenue", "Cash": "cash_and_equivalents"}
        assert mapping == expected

    def test_apply_mapping_with_existing_mapping(self):
        """Test _apply_mapping with existing mapping."""
        reader = self.TestReader()
        mapping = {"Revenue": "revenue", "Cost of Sales": "cogs"}

        result = reader._apply_mapping("Revenue", mapping)
        assert result == "revenue"

        result = reader._apply_mapping("Cost of Sales", mapping)
        assert result == "cogs"

    def test_apply_mapping_with_no_mapping(self):
        """Test _apply_mapping when no mapping exists."""
        reader = self.TestReader()
        mapping = {"Revenue": "revenue"}

        result = reader._apply_mapping("Unknown Item", mapping)
        assert result == "Unknown Item"  # Should return original

    def test_apply_mapping_empty_mapping(self):
        """Test _apply_mapping with empty mapping."""
        reader = self.TestReader()
        mapping = {}

        result = reader._apply_mapping("Any Item", mapping)
        assert result == "Any Item"

    @patch("importlib.resources.files")
    def test_get_mapping_invalid_yaml(self, mock_files):
        """Test handling of invalid YAML in default mappings."""
        # Mock invalid YAML content
        mock_file = Mock()
        mock_file.read_text.return_value = "invalid: yaml: content: ["
        mock_files.return_value.joinpath.return_value = mock_file

        reader = self.TestReader()
        mappings = reader._load_default_mappings()

        # Should return empty dict on YAML parsing error
        assert mappings == {}

    def test_get_mapping_no_cfg_attribute(self):
        """Test _get_mapping when reader has no cfg attribute."""

        class NoCfgReader(MappingAwareMixin):
            @classmethod
            def _get_default_mapping_path(cls) -> Optional[str]:
                return None

            def get_config_value(self, key: str, default=None):
                return default

        reader = NoCfgReader()
        mapping = reader._get_mapping()
        assert mapping == {}

    @patch("importlib.resources.files")
    def test_different_readers_have_separate_caches(self, mock_files):
        """Test that different reader classes have separate cache entries."""

        class Reader1(MappingAwareMixin):
            @classmethod
            def _get_default_mapping_path(cls) -> Optional[str]:
                return "reader1.yaml"

        class Reader2(MappingAwareMixin):
            @classmethod
            def _get_default_mapping_path(cls) -> Optional[str]:
                return "reader2.yaml"

        # Mock different YAML content for each reader
        def mock_read_text(encoding=None):
            if "reader1.yaml" in str(mock_files.return_value.joinpath.call_args):
                return "reader1: mapping1"
            else:
                return "reader2: mapping2"

        mock_file = Mock()
        mock_file.read_text.side_effect = mock_read_text
        mock_files.return_value.joinpath.return_value = mock_file

        mappings1 = Reader1._load_default_mappings()
        mappings2 = Reader2._load_default_mappings()

        assert "Reader1" in MappingAwareMixin._default_mappings_cache
        assert "Reader2" in MappingAwareMixin._default_mappings_cache
        assert mappings1 != mappings2
