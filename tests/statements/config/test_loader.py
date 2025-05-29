"""Tests for statement configuration loading functionality.

This module tests the loading of statement configurations from files and directories,
including validation and error handling.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from fin_statement_model.statements.orchestration.loader import (
    load_build_register_statements,
)
from fin_statement_model.statements.structure.builder import StatementStructureBuilder
from fin_statement_model.statements.registry import StatementRegistry
from fin_statement_model.core.errors import ConfigurationError


class TestLoadBuildRegisterStatements:
    """Test the load_build_register_statements function."""

    def test_load_single_file_success(self):
        """Test loading a single valid configuration file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "id": "test_statement",
                "name": "Test Statement",
                "sections": [],
            }
            json.dump(config_data, f)
            config_path = f.name

        try:
            registry = StatementRegistry()
            builder = StatementStructureBuilder()

            # Mock the IO functions
            with patch(
                "fin_statement_model.statements.orchestration.loader.read_statement_config_from_path"
            ) as mock_read:
                mock_read.return_value = config_data

                loaded_ids = load_build_register_statements(
                    config_path, registry, builder
                )

                assert loaded_ids == ["test_statement"]
                assert registry.get("test_statement") is not None
        finally:
            Path(config_path).unlink()

    def test_load_directory_success(self):
        """Test loading multiple configurations from a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test config files
            configs = {
                "stmt1": {"id": "statement_1", "name": "Statement 1", "sections": []},
                "stmt2": {"id": "statement_2", "name": "Statement 2", "sections": []},
            }

            registry = StatementRegistry()
            builder = StatementStructureBuilder()

            # Mock the IO functions
            with patch(
                "fin_statement_model.statements.orchestration.loader.read_statement_configs_from_directory"
            ) as mock_read:
                mock_read.return_value = configs

                loaded_ids = load_build_register_statements(temp_dir, registry, builder)

                assert set(loaded_ids) == {"statement_1", "statement_2"}
                assert registry.get("statement_1") is not None
                assert registry.get("statement_2") is not None

    def test_file_not_found(self):
        """Test handling of non-existent file."""
        registry = StatementRegistry()
        builder = StatementStructureBuilder()

        with pytest.raises(ConfigurationError) as exc_info:
            load_build_register_statements("/non/existent/path.yaml", registry, builder)

        assert "Failed to read config" in str(exc_info.value)

    def test_validation_error(self):
        """Test handling of validation errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Invalid config - missing required fields
            config_data = {
                "id": "test_statement"
                # Missing 'name' and 'sections'
            }
            json.dump(config_data, f)
            config_path = f.name

        try:
            registry = StatementRegistry()
            builder = StatementStructureBuilder()

            with patch(
                "fin_statement_model.statements.orchestration.loader.read_statement_config_from_path"
            ) as mock_read:
                mock_read.return_value = config_data

                # Should not raise but log warning
                loaded_ids = load_build_register_statements(
                    config_path, registry, builder
                )

                # No statements should be loaded due to validation error
                assert loaded_ids == []
        finally:
            Path(config_path).unlink()

    def test_duplicate_registration(self):
        """Test handling of duplicate statement IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configs = {
                "stmt1": {"id": "duplicate_id", "name": "Statement 1", "sections": []},
                "stmt2": {
                    "id": "duplicate_id",  # Same ID
                    "name": "Statement 2",
                    "sections": [],
                },
            }

            registry = StatementRegistry()
            builder = StatementStructureBuilder()

            with patch(
                "fin_statement_model.statements.orchestration.loader.read_statement_configs_from_directory"
            ) as mock_read:
                mock_read.return_value = configs

                loaded_ids = load_build_register_statements(temp_dir, registry, builder)

                # Only one should be loaded due to duplicate ID
                assert len(loaded_ids) == 1
                assert loaded_ids[0] == "duplicate_id"

    def test_empty_directory(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = StatementRegistry()
            builder = StatementStructureBuilder()

            with patch(
                "fin_statement_model.statements.orchestration.loader.read_statement_configs_from_directory"
            ) as mock_read:
                mock_read.return_value = {}

                loaded_ids = load_build_register_statements(temp_dir, registry, builder)

                assert loaded_ids == []
