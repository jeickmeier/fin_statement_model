# Template Registry & Engine (TRE)

The Template Registry & Engine provides a complete solution for creating, storing, and managing reusable financial statement templates. Templates encapsulate graph structures, forecasting configurations, and preprocessing pipelines in a portable format.

## Features

- **Local Storage**: Templates stored securely in your home directory with filesystem-based registry
- **Built-in Templates**: Pre-configured templates for common financial models (LBO, real estate, etc.)
- **Template Comparison**: Structural and value-based diffing between templates
- **Forecasting Integration**: Declarative forecast specifications embedded in templates
- **Preprocessing Pipelines**: Automated data transformation workflows
- **Version Management**: Semantic versioning with automatic increment

## Quick Start

### Install Built-in Templates

```python
from fin_statement_model.templates import install_builtin_templates, TemplateRegistry

# Install built-in templates (idempotent)
install_builtin_templates()

# List available templates
templates = TemplateRegistry.list()
print(templates)  # ['lbo.standard_v1', 'real_estate_lending_v3']
```

### Use a Template

```python
# Instantiate a template as a working graph
graph = TemplateRegistry.instantiate('lbo.standard_v1')

# Calculate values
revenue_2024 = graph.calculate('Revenue', '2024')
print(f"2024 Revenue: ${revenue_2024:,.0f}")

# Access graph structure
print(f"Graph has {len(graph.nodes)} nodes and {len(graph.periods)} periods")
```

### Register Custom Templates

```python
# Register your own graph as a template
template_id = TemplateRegistry.register_graph(
    my_graph,
    name="custom.model",
    meta={"category": "custom", "description": "My custom financial model"}
)
print(f"Registered as: {template_id}")
```

## Advanced Usage

### Template Customization

```python
# Instantiate with customizations
customized_graph = TemplateRegistry.instantiate(
    'lbo.standard_v1',
    periods=['2029', '2030'],                    # Add extra periods
    rename_map={'Revenue': 'TotalRevenue'}       # Rename nodes
)

# Verify customizations
print(customized_graph.periods)  # Includes 2029, 2030
print('TotalRevenue' in customized_graph.nodes)  # True
```

### Template Comparison

```python
# Compare templates
diff_result = TemplateRegistry.diff('lbo.standard_v1', 'custom.model_v1')

# Analyze structural changes
structure = diff_result.structure
print(f"Added nodes: {structure.added_nodes}")
print(f"Removed nodes: {structure.removed_nodes}")
print(f"Changed nodes: {list(structure.changed_nodes.keys())}")

# Analyze value changes
if diff_result.values:
    values = diff_result.values
    print(f"Changed cells: {len(values.changed_cells)}")
    print(f"Max delta: ${values.max_delta:,.2f}")
```

### Templates with Forecasting

```python
from fin_statement_model.templates.models import ForecastSpec

# Create forecast specification
forecast_spec = ForecastSpec(
    periods=["2027", "2028"],
    node_configs={
        "Revenue": {"method": "simple", "config": 0.1},
        "COGS": {"method": "historical_growth", "config": {"aggregation": "mean"}}
    }
)

# Register template with forecasting
template_id = TemplateRegistry.register_graph(
    my_graph,
    name="forecast.model",
    forecast=forecast_spec
)

# Forecasting is applied automatically during instantiation
graph = TemplateRegistry.instantiate(template_id)
```

### Templates with Preprocessing

```python
from fin_statement_model.templates.models import PreprocessingSpec, PreprocessingStep

# Create preprocessing pipeline
preprocessing = PreprocessingSpec(pipeline=[
    PreprocessingStep(
        name="time_series",
        params={"transformation_type": "yoy", "periods": 1, "as_percent": True}
    ),
    PreprocessingStep(
        name="normalization", 
        params={"method": "min_max", "feature_range": (0, 1)}
    )
])

# Register template with preprocessing
template_id = TemplateRegistry.register_graph(
    my_graph,
    name="processed.model",
    preprocessing=preprocessing
)
```

## Built-in Templates

### LBO Standard (lbo.standard_v1)
- **Description**: Minimal 3-node LBO model with Revenue, COGS, and calculated metrics
- **Nodes**: Revenue, COGS, GrossProfit, GrossProfitMargin
- **Periods**: 2024-2028
- **Features**: Includes adjustments and forecasting configuration

### Real Estate Lending (real_estate_lending_v3)
- **Description**: Construction loan waterfall with interest calculations
- **Nodes**: LoanDraw, InterestRate, InterestExpense, InterestExpenseRate
- **Periods**: 2024-2027
- **Features**: Formula-based calculations for construction financing

## Registry Storage

Templates are stored in your home directory with secure permissions:

```
~/.fin_statement_model/templates/
├── index.json                    # Fast lookup index
└── store/                        # Template storage
    ├── lbo.standard/
    │   ├── v1/
    │   │   └── bundle.json       # Template bundle
    │   └── v2/
    │       └── bundle.json
    └── real_estate_lending/
        └── v3/
            └── bundle.json
```

## Configuration

Set the `FSM_TEMPLATES_PATH` environment variable to customize the registry location:

```bash
export FSM_TEMPLATES_PATH=/path/to/custom/templates
```

## Security

- Registry directory created with 0700 permissions (user-only access)
- Template bundles stored with 0600 permissions (user read/write only)
- SHA-256 checksums verify template integrity on load

## API Reference

### Core Classes

- **`TemplateRegistry`**: Main interface for template storage and retrieval
- **`TemplateBundle`**: Serializable container for complete template specifications
- **`TemplateMeta`**: Template metadata (name, version, description, tags)
- **`ForecastSpec`**: Declarative forecasting configuration
- **`PreprocessingSpec`**: Data transformation pipeline definition
- **`DiffResult`**: Template comparison results

### Key Functions

- **`install_builtin_templates()`**: Install pre-packaged templates
- **`TemplateRegistry.list()`**: List available templates
- **`TemplateRegistry.register_graph()`**: Store a graph as a template
- **`TemplateRegistry.get()`**: Retrieve template bundle
- **`TemplateRegistry.instantiate()`**: Create working graph from template
- **`TemplateRegistry.diff()`**: Compare two templates
- **`TemplateRegistry.delete()`**: Remove template permanently

## Examples

See the `examples/` directory for comprehensive usage examples and the built-in template JSON files in `builtin/data/` for template structure references.