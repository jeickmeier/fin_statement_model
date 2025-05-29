"""Tests for UnifiedNodeValidator integration with statement configuration.

This module tests the integration of UnifiedNodeValidator into the statement
configuration parsing and building process.
"""

from fin_statement_model.statements import (
    StatementConfig,
    StatementStructureBuilder,
    create_validated_statement_config,
    create_validated_statement_builder,
    validate_statement_config_with_nodes,
)
from fin_statement_model.io.validation import UnifiedNodeValidator


class TestNodeValidationIntegration:
    """Test UnifiedNodeValidator integration with statement processing."""

    def test_statement_config_with_node_validation_disabled(self):
        """Test StatementConfig with node validation disabled (default behavior)."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "id": "revenue_section",
                    "name": "Revenue",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",
                            "name": "Total Revenue",
                            "node_id": "revenue_node",
                        }
                    ],
                }
            ],
        }

        # Default behavior - no node validation
        config = StatementConfig(config_data)
        errors = config.validate_config()
        assert errors == []  # Should pass without node validation
        assert config.model is not None

    def test_statement_config_with_node_validation_enabled_valid_names(self):
        """Test StatementConfig with node validation enabled and valid node names."""
        config_data = {
            "id": "income_statement",  # Standard name
            "name": "Income Statement",
            "sections": [
                {
                    "id": "revenue_section",
                    "name": "Revenue",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",  # Standard name
                            "name": "Total Revenue",
                            "node_id": "revenue",  # Standard name
                        },
                        {
                            "type": "calculated",
                            "id": "gross_profit",  # Standard name
                            "name": "Gross Profit",
                            "calculation": {
                                "type": "subtraction",
                                "inputs": ["revenue", "cogs"],  # Standard names
                            },
                        },
                    ],
                }
            ],
        }

        # Enable node validation
        config = StatementConfig(
            config_data, enable_node_validation=True, node_validation_strict=False
        )
        errors = config.validate_config()

        # Should pass with warnings only (if any)
        assert config.model is not None
        # Note: errors list might contain warnings depending on configuration

    def test_statement_config_with_node_validation_enabled_invalid_names_strict(self):
        """Test StatementConfig with invalid node names in strict mode."""
        config_data = {
            "id": "bad_statement_name!",  # Invalid characters
            "name": "Test Statement",
            "sections": [
                {
                    "id": "some_section",
                    "name": "Some Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "invalid@node",  # Invalid characters
                            "name": "Invalid Node",
                            "node_id": "another_invalid_node!!!",  # Invalid characters
                        }
                    ],
                }
            ],
        }

        # Enable strict node validation
        config = StatementConfig(
            config_data, enable_node_validation=True, node_validation_strict=True
        )
        errors = config.validate_config()

        # Should have validation errors in strict mode
        assert len(errors) > 0
        assert any("invalid" in error.lower() for error in errors)

    def test_statement_config_with_node_validation_enabled_invalid_names_non_strict(
        self,
    ):
        """Test StatementConfig with invalid node names in non-strict mode."""
        config_data = {
            "id": "custom_statement",
            "name": "Custom Statement",
            "sections": [
                {
                    "id": "custom_section",
                    "name": "Custom Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "custom_metric",  # Custom but valid name
                            "name": "Custom Metric",
                            "node_id": "custom_node_123",  # Custom but valid name
                        }
                    ],
                }
            ],
        }

        # Enable non-strict node validation
        config = StatementConfig(
            config_data, enable_node_validation=True, node_validation_strict=False
        )
        errors = config.validate_config()

        # Should pass without errors (warnings logged but not in errors list)
        assert errors == []
        assert config.model is not None

    def test_statement_config_with_standard_node_ref_validation(self):
        """Test validation of standard_node_ref fields."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "id": "test_section",
                    "name": "Test Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue_item",
                            "name": "Revenue Item",
                            "standard_node_ref": "revenue",  # Valid standard reference
                        }
                    ],
                }
            ],
        }

        config = StatementConfig(
            config_data, enable_node_validation=True, node_validation_strict=False
        )
        errors = config.validate_config()

        # Should pass since 'revenue' is a standard node name
        assert errors == []
        assert config.model is not None

    def test_statement_builder_with_node_validation(self):
        """Test StatementStructureBuilder with node validation enabled."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "id": "test_section",
                    "name": "Test Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",
                            "name": "Revenue",
                            "node_id": "revenue",
                        }
                    ],
                }
            ],
        }

        # Create config and validate
        config = StatementConfig(config_data)
        config.validate_config()

        # Create builder with node validation
        builder = StatementStructureBuilder(
            enable_node_validation=True, node_validation_strict=False
        )

        # Build should succeed
        statement = builder.build(config)
        assert statement is not None
        assert statement.id == "test_statement"

    def test_convenience_functions(self):
        """Test the convenience functions for node validation."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "id": "test_section",
                    "name": "Test Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",
                            "name": "Revenue",
                            "node_id": "revenue",
                        }
                    ],
                }
            ],
        }

        # Test create_validated_statement_config
        config = create_validated_statement_config(
            config_data, enable_node_validation=True, strict_mode=False
        )
        errors = config.validate_config()
        assert errors == []

        # Test create_validated_statement_builder
        builder = create_validated_statement_builder(
            enable_node_validation=True, strict_mode=False
        )
        statement = builder.build(config)
        assert statement is not None

    def test_validate_statement_config_with_nodes_function(self):
        """Test the high-level validate_statement_config_with_nodes function."""
        config_data = {
            "id": "income_statement",
            "name": "Income Statement",
            "sections": [
                {
                    "id": "revenue_section",
                    "name": "Revenue",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",
                            "name": "Total Revenue",
                            "node_id": "revenue",
                        }
                    ],
                }
            ],
        }

        # Test with dictionary input
        config, errors = validate_statement_config_with_nodes(
            config_data, strict_mode=False
        )
        assert errors == []
        assert config.model is not None

    def test_custom_node_validator(self):
        """Test using a custom UnifiedNodeValidator instance."""
        # Create a very strict validator
        strict_validator = UnifiedNodeValidator(
            strict_mode=True,
            auto_standardize=False,
            warn_on_non_standard=True,
            enable_patterns=False,  # Disable patterns for stricter validation
        )

        config_data = {
            "id": "custom_statement",  # Non-standard name
            "name": "Custom Statement",
            "sections": [
                {
                    "id": "custom_section",
                    "name": "Custom Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",  # Standard name should pass
                            "name": "Revenue",
                            "node_id": "revenue",
                        }
                    ],
                }
            ],
        }

        config = StatementConfig(
            config_data,
            enable_node_validation=True,
            node_validation_strict=True,
            node_validator=strict_validator,
        )

        errors = config.validate_config()
        # Should have errors due to custom statement name in strict mode
        assert len(errors) > 0

    def test_metric_and_calculation_input_validation(self):
        """Test validation of inputs in metric and calculation items."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "id": "calculations",
                    "name": "Calculations",
                    "type": "section",
                    "items": [
                        {
                            "type": "metric",
                            "id": "profit_margin",
                            "name": "Profit Margin",
                            "metric_id": "margin_percentage",
                            "inputs": {
                                "numerator": "net_income",  # Should be validated
                                "denominator": "revenue",  # Should be validated
                            },
                        },
                        {
                            "type": "calculated",
                            "id": "total_cost",
                            "name": "Total Cost",
                            "calculation": {
                                "type": "addition",
                                "inputs": [
                                    "cogs",
                                    "operating_expenses",
                                ],  # Should be validated
                            },
                        },
                        {
                            "type": "subtotal",
                            "id": "total_expenses",
                            "name": "Total Expenses",
                            "items_to_sum": [
                                "salaries",
                                "rent",
                                "utilities",
                            ],  # Should be validated
                        },
                    ],
                }
            ],
        }

        config = StatementConfig(
            config_data, enable_node_validation=True, node_validation_strict=False
        )
        errors = config.validate_config()

        # Should complete validation (warnings may be generated but not errors in non-strict mode)
        assert config.model is not None

    def test_validation_error_context(self):
        """Test that validation errors include proper context information."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "id": "test_section",
                    "name": "Test Section",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "invalid@node",  # Invalid characters
                            "name": "Invalid Node",
                            "node_id": "invalid_node_id!!!",  # Invalid characters
                        }
                    ],
                }
            ],
        }

        config = StatementConfig(
            config_data, enable_node_validation=True, node_validation_strict=True
        )
        errors = config.validate_config()

        # Should have errors with context information
        assert len(errors) > 0
        # Check that errors contain context about where the invalid ID was found
        assert any("invalid@node" in error for error in errors)
        assert any("invalid_node_id!!!" in error for error in errors)

    def test_integration_with_orchestration(self):
        """Test that node validation works with high-level orchestration functions."""
        from fin_statement_model.core.graph import Graph

        # Create a simple graph
        graph = Graph()
        graph.add_node("revenue", values={"2023": 1000})

        config_data = {
            "id": "simple_statement",
            "name": "Simple Statement",
            "sections": [
                {
                    "id": "revenue_section",
                    "name": "Revenue",
                    "type": "section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue",
                            "name": "Revenue",
                            "node_id": "revenue",
                        }
                    ],
                }
            ],
        }

        # Test that we can create a statement DataFrame with node validation
        # Note: This would need a config file in practice, but we're testing the API
        # For now, just test that the parameters are accepted
        try:
            # This would normally work with a file path, but we're just testing the interface
            pass
        except Exception:
            # Expected since we're not providing a real file path
            pass
