"""Script to concatenate all source files for documentation purposes."""

import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define the paths to include
include_paths = [
    "fin_statement_model",
    "tests",
    "examples",
]

# Define patterns to exclude
exclude_patterns = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".pytest_cache",
    "*.egg-info",
]


def concatenate_files(output_filename="concatenated_code.txt"):
    """Concatenate all Python files in the specified directories."""
    file_paths = []

    # Collect all Python files
    for path_str in include_paths:
        path = Path(path_str)
        if path.exists():
            for py_file in path.rglob("*.py"):
                # Check if file should be excluded
                if not any(pattern in str(py_file) for pattern in exclude_patterns):
                    file_paths.append(py_file)

    # Sort file paths for consistent output
    file_paths.sort()

    # Write to output file
    with open(output_filename, "w", encoding="utf-8") as output_file:
        for file_path in file_paths:
            output_file.write(f"\n{'=' * 80}\n")
            output_file.write(f"File: {file_path}\n")
            output_file.write(f"{'=' * 80}\n\n")

            try:
                with open(file_path, "r", encoding="utf-8") as input_file:
                    content = input_file.read()
                    output_file.write(content)
                    output_file.write("\n\n")
            except FileNotFoundError:
                full_path = Path.cwd() / file_path
                logger.warning(f"File not found at {full_path}")
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file {full_path} as UTF-8")
            except Exception as e:
                logger.warning(f"Error reading file {full_path}: {e}")

    try:
        # Verify the output file was created
        output_path = Path(output_filename)
        if output_path.exists():
            logger.info(
                f"Successfully concatenated {len(file_paths)} files into {output_filename}"
            )
    except Exception as e:
        logger.error(f"Error writing to output file {output_filename}: {e}")


if __name__ == "__main__":
    concatenate_files()
