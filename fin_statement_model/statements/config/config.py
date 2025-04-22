"""Statement configuration handling for Financial Statement Model.

This module provides utilities for loading and parsing statement configuration files,
which define the structure of financial statements including sections and line items.
"""

import json
import yaml
import logging
from typing import Any, Union, Optional
from pathlib import Path

# Use absolute imports
from fin_statement_model.statements.errors import ConfigurationError
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
)

# Configure logging
logger = logging.getLogger(__name__)


class StatementConfig:
    """Manages configuration for financial statement structures.

    This class handles loading, parsing, and validating statement configuration files,
    and building StatementStructure objects from these configurations.
    """

    def __init__(
        self,
        config_data: Optional[dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ):
        """Initialize a statement configuration.

        Args:
            config_data: Optional dictionary containing the configuration data
            config_path: Optional path to a configuration file (JSON or YAML)

        If both config_data and config_path are provided, config_data takes precedence.

        Raises:
            ConfigurationError: If the configuration file is invalid or cannot be loaded
        """
        self.config_data = {}
        self.config_path = config_path

        if config_data:
            self.config_data = config_data
        elif config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        """Load configuration from a file.

        Args:
            config_path: Path to the configuration file (JSON or YAML)

        Raises:
            ConfigurationError: If the file cannot be loaded or parsed
        """
        self.config_path = config_path
        path = Path(config_path)

        if not path.exists():
            raise ConfigurationError(
                message="Configuration file not found", config_path=config_path
            )

        extension = path.suffix.lower()

        try:
            if extension == ".json":
                with open(path) as f:
                    self.config_data = json.load(f)
            elif extension in [".yaml", ".yml"]:
                with open(path) as f:
                    self.config_data = yaml.safe_load(f)
            else:
                raise ConfigurationError(
                    message="Unsupported file extension",
                    config_path=config_path,
                    errors=[f"Use .json, .yaml, or .yml instead of {extension}"],
                )

            logger.info(f"Loaded statement configuration from {config_path}")
        except json.JSONDecodeError as e:
            logger.exception(f"Error parsing JSON configuration file {config_path}")
            raise ConfigurationError(
                message="Invalid JSON format",
                config_path=config_path,
                errors=[f"JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}"],
            ) from e
        except yaml.YAMLError as e:
            logger.exception(f"Error parsing YAML configuration file {config_path}")
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                error_detail = (
                    f"YAML parse error at line {mark.line + 1}, column {mark.column + 1}: "
                    f"{e.problem}"
                )
            else:
                error_detail = str(e)
            raise ConfigurationError(
                message="Invalid YAML format",
                config_path=config_path,
                errors=[error_detail],
            ) from e
        except Exception as e:
            logger.exception(f"Unexpected error loading configuration from {config_path}")
            raise ConfigurationError(
                message="Failed to load configuration",
                config_path=config_path,
                errors=[str(e)],
            ) from e

    def validate_config(self) -> list[str]:
        """Validate the configuration data.

        Returns:
            List[str]: List of validation errors, or empty list if valid
        """
        errors = []

        # Check for required top-level fields
        required_fields = ["id", "name", "sections"]
        errors.extend(
            [
                f"Missing required field: {field}"
                for field in required_fields
                if field not in self.config_data
            ]
        )

        # Check for sections
        if "sections" in self.config_data:
            # Validate each section
            sections = self.config_data.get("sections", [])
            if not isinstance(sections, list):
                errors.append("'sections' must be a list")
            else:
                for i, section in enumerate(sections):
                    section_errors = self._validate_section(section, i)
                    errors.extend(section_errors)

        return errors

    def _validate_section(self, section: dict[str, Any], index: int) -> list[str]:
        """Validate a section configuration.

        Args:
            section: Section configuration dictionary
            index: Index of the section in the sections list

        Returns:
            List[str]: List of validation errors, or empty list if valid
        """
        errors = []

        # Check if section is a dictionary
        if not isinstance(section, dict):
            return [f"Section[{index}]: Must be a dictionary"]

        # Check for required section fields
        required_fields = ["id", "name"]
        errors.extend(
            [
                f"Section[{index}]: Missing required field: {field}"
                for field in required_fields
                if field not in section
            ]
        )

        # Validate section ID format
        section_id = section.get("id", "")
        if not section_id:
            errors.append(f"Section[{index}]: ID cannot be empty")
        elif not isinstance(section_id, str):
            errors.append(f"Section[{index}]: ID must be a string")
        elif " " in section_id:
            errors.append(f"Section[{index}]: ID '{section_id}' should not contain spaces")

        # Validate items
        if "items" in section:
            # Validate each item
            items = section.get("items", [])
            if not isinstance(items, list):
                errors.append(f"Section[{index}]: 'items' must be a list")
            else:
                for j, item in enumerate(items):
                    item_errors = self._validate_item(item, index, j)
                    errors.extend(item_errors)

        # Validate subsections if present
        if "subsections" in section:
            subsections = section.get("subsections", [])
            if not isinstance(subsections, list):
                errors.append(f"Section[{index}]: 'subsections' must be a list")
            else:
                for j, subsection in enumerate(subsections):
                    subsection_errors = self._validate_section(subsection, f"{index}.{j}")
                    errors.extend(subsection_errors)

        return errors

    def _validate_item(self, item: dict[str, Any], section_idx: int, item_idx: int) -> list[str]:
        """Validate an item configuration.

        Args:
            item: Item configuration dictionary
            section_idx: Index of the parent section
            item_idx: Index of the item within the section

        Returns:
            List[str]: List of validation errors, or empty list if valid
        """
        errors = []

        # Check if item is a dictionary
        if not isinstance(item, dict):
            return [f"Section[{section_idx}].Item[{item_idx}]: Must be a dictionary"]

        # Check for required item fields
        required_fields = ["id", "name"]
        errors.extend(
            [
                f"Section[{section_idx}].Item[{item_idx}]: Missing required field: {field}"
                for field in required_fields
                if field not in item
            ]
        )

        # Validate item ID format
        item_id = item.get("id", "")
        if not item_id:
            errors.append(f"Section[{section_idx}].Item[{item_idx}]: ID cannot be empty")
        elif not isinstance(item_id, str):
            errors.append(f"Section[{section_idx}].Item[{item_idx}]: ID must be a string")
        elif " " in item_id:
            errors.append(
                f"Section[{section_idx}].Item[{item_idx}]: ID '{item_id}' should not contain spaces"
            )

        # Validate based on item type
        item_type = item.get("type", "line_item")

        if item_type == "section":
            # This is a nested section
            if "items" not in item:
                errors.append(
                    f"Section[{section_idx}].Item[{item_idx}]: Nested section missing 'items' field"
                )
            else:
                nested_items = item.get("items", [])
                if not isinstance(nested_items, list):
                    errors.append(
                        f"Section[{section_idx}].Item[{item_idx}]: 'items' must be a list"
                    )
                else:
                    for k, nested_item in enumerate(nested_items):
                        nested_errors = self._validate_item(
                            nested_item, f"{section_idx}.{item_idx}", k
                        )
                        errors.extend(nested_errors)

        elif item_type == "line_item":
            # Basic line item should have a node_id
            if "node_id" not in item:
                errors.append(
                    f"Section[{section_idx}].Item[{item_idx}]: Line item missing 'node_id' field"
                )

        elif item_type == "calculated":
            if "calculation" not in item:
                errors.append(
                    f"Section[{section_idx}].Item[{item_idx}]: Calculated item missing 'calculation' field"
                )
            else:
                calculation = item.get("calculation", {})
                if not isinstance(calculation, dict):
                    errors.append(
                        f"Section[{section_idx}].Item[{item_idx}]: 'calculation' must be a dictionary"
                    )
                else:
                    # Validate calculation
                    if "type" not in calculation:
                        errors.append(
                            f"Section[{section_idx}].Item[{item_idx}]: Calculation missing 'type' field"
                        )
                    if "inputs" not in calculation:
                        errors.append(
                            f"Section[{section_idx}].Item[{item_idx}]: Calculation missing 'inputs' field"
                        )
                    elif not isinstance(calculation.get("inputs", []), list):
                        errors.append(
                            f"Section[{section_idx}].Item[{item_idx}]: 'inputs' must be a list"
                        )

        elif item_type == "subtotal":
            # Check for calculation with addition type
            if "calculation" in item:
                calculation = item.get("calculation", {})
                if calculation.get("type") != "addition":
                    errors.append(
                        f"Section[{section_idx}].Item[{item_idx}]: Subtotal calculation type must be 'addition'"
                    )
            elif "items_to_sum" not in item:
                errors.append(
                    f"Section[{section_idx}].Item[{item_idx}]: Subtotal item missing 'items_to_sum' field"
                )
            elif not isinstance(item.get("items_to_sum", []), list):
                errors.append(
                    f"Section[{section_idx}].Item[{item_idx}]: 'items_to_sum' must be a list"
                )

        else:
            errors.append(
                f"Section[{section_idx}].Item[{item_idx}]: Unknown item type: {item_type}"
            )

        return errors

    def build_statement_structure(self) -> StatementStructure:
        """Build a StatementStructure object from the configuration.

        Returns:
            StatementStructure: The constructed statement structure

        Raises:
            ConfigurationError: If the configuration is invalid
        """
        # Validate the configuration
        errors = self.validate_config()
        if errors:
            error_msg = "Configuration validation failed"
            logger.error(f"{error_msg}: {'; '.join(errors)}")
            raise ConfigurationError(message=error_msg, config_path=self.config_path, errors=errors)

        try:
            # Create the statement structure
            statement = StatementStructure(
                id=self.config_data["id"],
                name=self.config_data["name"],
                description=self.config_data.get("description", ""),
                metadata=self.config_data.get("metadata", {}),
            )

            # Build sections
            sections = self.config_data.get("sections", [])
            for section_config in sections:
                section = self._build_section(section_config)
                statement.add_section(section)

            return statement
        except Exception as e:
            logger.exception("Error building statement structure")
            raise ConfigurationError(
                message="Failed to build statement structure",
                config_path=self.config_path,
                errors=[str(e)],
            ) from e
        else:
            return statement

    def _build_section(self, section_config: dict[str, Any]) -> Section:
        """Build a Section object from a section configuration.

        Args:
            section_config: Section configuration dictionary

        Returns:
            Section: The constructed section

        Raises:
            ConfigurationError: If the section configuration is invalid
        """
        try:
            # Create the section
            section = Section(
                id=section_config["id"],
                name=section_config["name"],
                description=section_config.get("description", ""),
                metadata=section_config.get("metadata", {}),
            )

            # Add items
            items = section_config.get("items", [])
            for item_config in items:
                item = self._build_item(item_config)
                section.add_item(item)

            # Add subsections
            subsections = section_config.get("subsections", [])
            for subsection_config in subsections:
                subsection = self._build_section(subsection_config)
                section.add_item(subsection)

            # Add subtotal if specified
            subtotal_config = section_config.get("subtotal")
            if subtotal_config:
                section.subtotal = self._build_subtotal(subtotal_config)

            return section
        except KeyError as e:
            section_id = section_config.get("id", "unknown")
            raise ConfigurationError(
                message=f"Missing required field '{e.args[0]}'",
                errors=[f"Section '{section_id}' is missing required field: {e.args[0]}"],
            ) from e
        except Exception as e:
            section_id = section_config.get("id", "unknown")
            raise ConfigurationError(
                message="Failed to build section",
                errors=[f"Error in section '{section_id}': {e!s}"],
            ) from e
        else:
            return section

    def _build_item(
        self, item_config: dict[str, Any]
    ) -> Union[LineItem, CalculatedLineItem, SubtotalLineItem, Section]:
        """Build a LineItem object from an item configuration.

        Args:
            item_config: Item configuration dictionary

        Returns:
            Union[LineItem, CalculatedLineItem, SubtotalLineItem, Section]:
                The constructed item

        Raises:
            ConfigurationError: If the item configuration is invalid
        """
        try:
            item_type = item_config.get("type", "line_item")

            if item_type == "section":
                # Handle nested section
                return self._build_section(item_config)

            elif item_type == "line_item":
                return LineItem(
                    id=item_config["id"],
                    name=item_config["name"],
                    node_id=item_config.get("node_id"),
                    description=item_config.get("description", ""),
                    sign_convention=item_config.get("sign_convention", 1),
                    metadata=item_config.get("metadata", {}),
                )

            elif item_type == "calculated":
                return CalculatedLineItem(
                    id=item_config["id"],
                    name=item_config["name"],
                    calculation=item_config["calculation"],
                    description=item_config.get("description", ""),
                    sign_convention=item_config.get("sign_convention", 1),
                    metadata=item_config.get("metadata", {}),
                )

            elif item_type == "subtotal":
                return self._build_subtotal(item_config)

            else:
                raise ConfigurationError(
                    message=f"Unknown item type: {item_type}",
                    errors=[
                        f"Item '{item_config.get('id', 'unknown')}' has invalid type: {item_type}"
                    ],
                )
        except KeyError as e:
            item_id = item_config.get("id", "unknown")
            raise ConfigurationError(
                message=f"Missing required field '{e.args[0]}'",
                errors=[f"Item '{item_id}' is missing required field: {e.args[0]}"],
            ) from e
        except Exception as e:
            item_id = item_config.get("id", "unknown")
            raise ConfigurationError(
                message="Failed to build item",
                errors=[f"Error in item '{item_id}': {e!s}"],
            ) from e

    def _build_subtotal(self, subtotal_config: dict[str, Any]) -> SubtotalLineItem:
        """Build a SubtotalLineItem object from a subtotal configuration.

        Args:
            subtotal_config: Subtotal configuration dictionary

        Returns:
            SubtotalLineItem: The constructed subtotal line item

        Raises:
            ConfigurationError: If the subtotal configuration is invalid
        """
        try:
            # Get items to sum
            items_to_sum = []

            if "calculation" in subtotal_config:
                # If using calculation format
                calculation = subtotal_config.get("calculation", {})
                items_to_sum = calculation.get("inputs", [])
            elif "item_ids" in subtotal_config:
                # If using item_ids format
                items_to_sum = subtotal_config.get("item_ids", [])
            else:
                # If using items_to_sum format
                items_to_sum = subtotal_config.get("items_to_sum", [])

            # Create subtotal
            return SubtotalLineItem(
                id=subtotal_config["id"],
                name=subtotal_config["name"],
                item_ids=items_to_sum,
                description=subtotal_config.get("description", ""),
                sign_convention=subtotal_config.get("sign_convention", 1),
                metadata=subtotal_config.get("metadata", {}),
            )
        except KeyError as e:
            subtotal_id = subtotal_config.get("id", "unknown")
            raise ConfigurationError(
                message=f"Missing required field '{e.args[0]}'",
                errors=[f"Subtotal '{subtotal_id}' is missing required field: {e.args[0]}"],
            ) from e
        except Exception as e:
            subtotal_id = subtotal_config.get("id", "unknown")
            raise ConfigurationError(
                message="Failed to build subtotal",
                errors=[f"Error in subtotal '{subtotal_id}': {e!s}"],
            ) from e


def load_statement_config(config_path: str) -> StatementStructure:
    """Load and build a statement structure from a configuration file.

    Args:
        config_path: Path to the configuration file (JSON or YAML)

    Returns:
        StatementStructure: The constructed statement structure

    Raises:
        ConfigurationError: If the configuration file cannot be loaded or is invalid
    """
    try:
        config = StatementConfig(config_path=config_path)
        return config.build_statement_structure()
    except Exception as e:
        if isinstance(e, ConfigurationError):
            # Re-raise ConfigurationError
            raise
        else:
            # Wrap other exceptions
            logger.exception("Unexpected error loading statement configuration")
            raise ConfigurationError(
                message="Failed to load statement configuration",
                config_path=config_path,
                errors=[str(e)],
            ) from e
