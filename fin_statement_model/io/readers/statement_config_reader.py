"""Reader functions for statement configuration files.

Handles locating, reading, and parsing JSON/YAML configuration files
into raw Python dictionaries.
"""

import json
import yaml
import logging
import importlib.resources
import importlib.util # Needed for checking resource type
from typing import Any, Optional

from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)

__all__ = [
    "list_available_builtin_configs",
    "read_builtin_statement_config",
    "read_statement_config_from_path",
    "read_statement_configs_from_directory",
]

def read_statement_config_from_path(config_path: str) -> dict[str, Any]:
    """Reads and parses a statement configuration file from a given path.

    Supports JSON and YAML formats.

    Args:
        config_path: Absolute or relative path to the configuration file.

    Returns:
        The parsed configuration data as a dictionary.

    Raises:
        ReadError: If the file is not found, has an unsupported extension,
                   or cannot be parsed.
    """
    path = Path(config_path)

    if not path.exists() or not path.is_file():
        raise ReadError(
            message="Configuration file not found or is not a file",
            target=config_path,
        )

    extension = path.suffix.lower()
    config_data = {}

    try:
        with open(path, encoding="utf-8") as f:
            if extension == ".json":
                config_data = json.load(f)
            elif extension in [".yaml", ".yml"]:
                config_data = yaml.safe_load(f)
            else:
                raise ReadError(
                    message="Unsupported file extension for statement config",
                    target=config_path,
                    details=f"Use .json, .yaml, or .yml instead of {extension}",
                )
        logger.debug(f"Successfully read and parsed config file: {config_path}")
        return config_data

    except json.JSONDecodeError as e:
        logger.exception(f"Error parsing JSON configuration file {config_path}")
        raise ReadError(
            message="Invalid JSON format in configuration file",
            target=config_path,
            original_error=e,
            details=f"JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}",
        ) from e
    except yaml.YAMLError as e:
        logger.exception(f"Error parsing YAML configuration file {config_path}")
        details = str(e)
        if hasattr(e, "problem_mark"):
            mark = e.problem_mark
            if mark:
                details = (
                    f"YAML parse error near line {mark.line + 1}, column {mark.column + 1}: "
                    f"{getattr(e, 'problem', '')}"
                )
        raise ReadError(
            message="Invalid YAML format in configuration file",
            target=config_path,
            original_error=e,
            details=details,
        ) from e
    except OSError as e:
        logger.exception(f"IO Error reading configuration file {config_path}")
        raise ReadError(
            message="Failed to read configuration file",
            target=config_path,
            original_error=e,
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error loading configuration from {config_path}")
        raise ReadError(
            message="Unexpected error loading configuration file",
            target=config_path,
            original_error=e,
        ) from e


def read_statement_configs_from_directory(directory_path: str) -> dict[str, dict[str, Any]]:
    """Reads all statement configs (JSON/YAML) from a directory.

    Args:
        directory_path: Path to the directory containing configuration files.

    Returns:
        A dictionary mapping statement identifiers (filename stem) to their
        parsed configuration data (dict).

    Raises:
        ReadError: If the directory doesn't exist or isn't accessible, or if
                   any individual file fails to read/parse (errors are logged
                   but reading continues for other files unless none succeed).
        FileNotFoundError: If the directory_path does not exist.
    """
    path = Path(directory_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration directory not found: {directory_path}")
    if not path.is_dir():
        raise ReadError(
            message="Provided path is not a directory",
            target=directory_path,
        )

    configs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    config_files = list(path.glob("*.json")) + list(path.glob("*.y*ml"))

    if not config_files:
        logger.warning(f"No configuration files (.json, .yaml, .yml) found in {directory_path}")
        return {}

    for file_path in config_files:
        file_path_str = str(file_path)
        try:
            config_data = read_statement_config_from_path(file_path_str)
            statement_id = file_path.stem # Use filename without extension as ID
            if statement_id in configs:
                logger.warning(
                    f"Duplicate statement ID '{statement_id}' found. Overwriting config from {file_path_str}."
                )
            configs[statement_id] = config_data
            logger.debug(f"Successfully loaded statement config '{statement_id}' from {file_path.name}")
        except ReadError as e:
            logger.exception(f"Failed to read/parse config file {file_path.name}:")
            errors.append(f"{file_path.name}: {e.message}")
        except Exception as e:
            logger.exception(f"Unexpected error processing file {file_path.name}")
            errors.append(f"{file_path.name}: Unexpected error - {e!s}")

    # Decision: Raise error only if NO files could be read successfully?
    # Or just log errors and return what was successful?
    # Current approach: Log errors, return successful ones.
    # If no configs loaded AND errors occurred, maybe raise an aggregate error.
    if not configs and errors:
        raise ReadError(
            message=f"Failed to load any valid configurations from directory {directory_path}",
            target=directory_path,
            details="\n".join(errors)
        )
    elif errors:
        # Log that some files failed if others succeeded
        logger.warning(f"Encountered errors while loading configs from {directory_path}: {len(errors)} file(s) failed.")

    return configs


def _get_builtin_config_package() -> str:
    """Return the package path string for built-in statement configurations.

    Direct return, assuming a fixed location within the package structure.
    Environment variable override is removed as importlib.resources relies on package structure.
    """
    return "fin_statement_model.statements.config.mappings"

def list_available_builtin_configs() -> list[str]:
    """List the names of all built-in statement configuration mappings available.

    Returns:
        List[str]: List of mapping names (filename without extension).
    """
    package_path = _get_builtin_config_package()
    try:
        resource_path = importlib.resources.files(package_path)
        # Check if the resource exists and is a container (directory)
        if not resource_path.is_dir():
            logger.warning(f"Built-in config package path is not a directory: {package_path}")
            return []

        names = [
            res.name.split('.')[0] # Get filename stem
            for res in resource_path.iterdir()
            if res.is_file() and res.suffix.lower() in (".yaml", ".yml", ".json")
        ]
        return sorted(names)
    except (ModuleNotFoundError, FileNotFoundError): # Handle case where package/path doesn't exist
        logger.warning(f"Built-in config package path not found: {package_path}")
        return []

def read_builtin_statement_config(name: str) -> dict[str, Any]:
    """Reads and parses a built-in statement configuration by name.

    Searches for <name>.yaml, <name>.yml, or <name>.json in the built-in
    mappings directory.

    Args:
        name: The name of the built-in configuration (filename without extension).

    Returns:
        The parsed configuration data as a dictionary.

    Raises:
        ReadError: If no matching configuration file is found or if reading/parsing fails.
    """
    package_path = _get_builtin_config_package()
    found_resource_name: Optional[str] = None
    resource_content: Optional[str] = None
    file_extension: Optional[str] = None

    for ext in (".yaml", ".yml", ".json"):
        resource_name = f"{name}{ext}"
        try:
            resource_path = importlib.resources.files(package_path).joinpath(resource_name)
            if resource_path.is_file():
                resource_content = resource_path.read_text(encoding="utf-8")
                found_resource_name = resource_name
                file_extension = ext
                break
        except (FileNotFoundError, ModuleNotFoundError):
            continue # Try next extension or handle package not found below
        except Exception as e:
            # Catch other potential errors during resource access
            logger.exception(f"Error accessing resource {resource_name} in {package_path}")
            raise ReadError(
                message=f"Error accessing built-in config resource '{name}'",
                target=f"{package_path}/{resource_name}",
                original_error=e,
            ) from e

    if resource_content is not None and found_resource_name is not None and file_extension is not None:
        logger.debug(f"Found and read built-in config '{name}' from resource: {package_path}/{found_resource_name}")
        try:
            if file_extension == ".json":
                config_data = json.loads(resource_content)
            else: # .yaml or .yml
                config_data = yaml.safe_load(resource_content)
            return config_data
        except json.JSONDecodeError as e:
            logger.exception(f"Error parsing JSON for built-in config '{name}'")
            raise ReadError(
                message="Invalid JSON format in built-in configuration",
                target=f"{package_path}/{found_resource_name}",
                original_error=e,
            ) from e
        except yaml.YAMLError as e:
            logger.exception(f"Error parsing YAML for built-in config '{name}'")
            raise ReadError(
                message="Invalid YAML format in built-in configuration",
                target=f"{package_path}/{found_resource_name}",
                original_error=e,
            ) from e
    else:
        logger.warning(f"Built-in statement config '{name}' not found in package {package_path}")
        raise ReadError(
            message=f"Built-in statement config '{name}' not found",
            target=package_path,
            details=f"No resource found for '{name}' with .yaml, .yml, or .json extension.",
        )
