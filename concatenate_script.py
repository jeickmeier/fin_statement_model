"""Concatenate all Python files in the fin_statement_model directory into a single file."""

import os

# Determine workspace root (assumes script is in workspace root)
workspace_root = os.path.dirname(__file__)

# Dynamically discover all Python files in the fin_statement_model directory
file_paths = []
for dirpath, dirnames, filenames in os.walk(os.path.join(workspace_root, "fin_statement_model")):
    # Skip __pycache__ and hidden directories
    dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
    for filename in filenames:
        if filename.endswith(".py"):
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, workspace_root)
            file_paths.append(rel_path)

# Sort file paths for consistent order
file_paths.sort()

output_filename = "concatenated_code.txt"

all_content = []

for file_path in file_paths:
    full_path = os.path.join(workspace_root, file_path)
    all_content.append(f"# --- START FILE: {file_path} ---\n")
    try:
        with open(full_path, encoding="utf-8") as f:
            all_content.append(f.read())
    except FileNotFoundError:
        all_content.append(f"# Error: File not found at {full_path}\n")
        print(f"Warning: File not found at {full_path}")
    except UnicodeDecodeError:
        all_content.append(f"# Error: Could not decode file {full_path} as UTF-8\n")
        print(f"Warning: Could not decode file {full_path} as UTF-8")
    except Exception as e:
        all_content.append(f"# Error reading file {full_path}: {e}\n")
        print(f"Warning: Error reading file {full_path}: {e}")
    all_content.append(f"\n# --- END FILE: {file_path} ---\n\n")

output_full_path = os.path.join(workspace_root, output_filename)
try:
    with open(output_full_path, "w", encoding="utf-8") as outfile:
        outfile.write("".join(all_content))
    print(f"Successfully concatenated {len(file_paths)} files into {output_filename}")
except Exception as e:
    print(f"Error writing to output file {output_filename}: {e}")
