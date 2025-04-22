import os

# List of Python files to concatenate (obtained from the find command)
file_paths = [
    "fin_statement_model/logging_config.py",
    "fin_statement_model/core/metrics/registry.py",
    "fin_statement_model/core/metrics/__init__.py",
    "fin_statement_model/core/nodes/stats_nodes.py",
    "fin_statement_model/core/nodes/__init__.py",
    "fin_statement_model/core/nodes/calculation_nodes.py",
    "fin_statement_model/core/nodes/forecast_nodes.py",
    "fin_statement_model/core/nodes/metric_node.py",
    "fin_statement_model/core/nodes/item_node.py",
    "fin_statement_model/core/nodes/base.py",
    "fin_statement_model/core/strategies/registry.py",
    "fin_statement_model/core/strategies/__init__.py",
    "fin_statement_model/core/strategies/strategy.py",
    "fin_statement_model/core/node_factory.py",
    "fin_statement_model/core/graph/manipulation.py",
    "fin_statement_model/core/graph/traversal.py",
    "fin_statement_model/core/graph/graph.py",
    "fin_statement_model/core/graph/forecast_mixin.py",
    "fin_statement_model/core/graph/__init__.py",
    "fin_statement_model/core/__init__.py",
    "fin_statement_model/core/calculation_engine.py",
    "fin_statement_model/core/errors.py",
    "fin_statement_model/core/data_manager.py",
    "fin_statement_model/io/writers/dataframe.py",
    "fin_statement_model/io/writers/__init__.py",
    "fin_statement_model/io/writers/excel.py",
    "fin_statement_model/io/writers/dict.py",
    "fin_statement_model/io/registry.py",
    "fin_statement_model/io/__init__.py",
    "fin_statement_model/io/utils.py",
    "fin_statement_model/io/exceptions.py",
    "fin_statement_model/io/readers/fmp.py",
    "fin_statement_model/io/readers/dataframe.py",
    "fin_statement_model/io/readers/__init__.py",
    "fin_statement_model/io/readers/excel.py",
    "fin_statement_model/io/readers/csv.py",
    "fin_statement_model/io/readers/dict.py",
    "fin_statement_model/io/base.py",
    "fin_statement_model/__init__.py",
    "fin_statement_model/extensions/llm/__init__.py",
    "fin_statement_model/extensions/llm/llm_client.py",
    "fin_statement_model/extensions/__init__.py",
    "fin_statement_model/statements/formatter.py",
    "fin_statement_model/statements/importer/cell_importer.py",
    "fin_statement_model/statements/importer/__init__.py",
    "fin_statement_model/statements/mixins/metrics_mixin.py",
    "fin_statement_model/statements/mixins/forecast_mixin.py",
    "fin_statement_model/statements/mixins/__init__.py",
    "fin_statement_model/statements/mixins/analysis_mixin.py",
    "fin_statement_model/statements/mixins/merge_mixin.py",
    "fin_statement_model/statements/config/config.py",
    "fin_statement_model/statements/config/loader.py",
    "fin_statement_model/statements/config/mappings/__init__.py",
    "fin_statement_model/statements/graph/financial_graph.py",
    "fin_statement_model/statements/__init__.py",
    "fin_statement_model/statements/factory.py",
    "fin_statement_model/statements/formatter/formatter.py",
    "fin_statement_model/statements/formatter/__init__.py",
    "fin_statement_model/statements/errors.py",
    "fin_statement_model/statements/structure/containers.py",
    "fin_statement_model/statements/structure/__init__.py",
    "fin_statement_model/statements/structure/items.py",
    "fin_statement_model/statements/manager.py",
    "fin_statement_model/statements/services/calculation_service.py",
    "fin_statement_model/statements/services/data_service.py",
    "fin_statement_model/statements/services/__init__.py",
    "fin_statement_model/statements/services/format_service.py",
    "fin_statement_model/statements/services/export_service.py",
    "fin_statement_model/statements/services/formatting_service.py",
    "fin_statement_model/preprocessing/transformer_factory.py",
    "fin_statement_model/preprocessing/transforms.py",
    "fin_statement_model/preprocessing/enums.py",
    "fin_statement_model/preprocessing/__init__.py",
    "fin_statement_model/preprocessing/types.py",
    "fin_statement_model/preprocessing/base_transformer.py",
    "fin_statement_model/preprocessing/transformers/period_conversion.py",
    "fin_statement_model/preprocessing/transformers/time_series.py",
    "fin_statement_model/preprocessing/transformers/__init__.py",
    "fin_statement_model/preprocessing/transformers/statement_formatting.py",
    "fin_statement_model/preprocessing/transformers/normalization.py",
    "fin_statement_model/preprocessing/transformation_service.py",
]

output_filename = "concatenated_code.txt"
workspace_root = os.path.dirname(__file__) # Assumes script is in workspace root

all_content = []

for file_path in file_paths:
    full_path = os.path.join(workspace_root, file_path)
    all_content.append(f"# --- START FILE: {file_path} ---\n")
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
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
    with open(output_full_path, 'w', encoding='utf-8') as outfile:
        outfile.write("".join(all_content))
    print(f"Successfully concatenated {len(file_paths)} files into {output_filename}")
except Exception as e:
    print(f"Error writing to output file {output_filename}: {e}") 