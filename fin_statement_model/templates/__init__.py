"""Template Registry & Engine (TRE) - Financial Statement Templates.

The Template Registry & Engine provides a complete solution for creating, storing,
and managing reusable financial statement templates. Templates encapsulate graph
structures, forecasting configurations, and preprocessing pipelines in a portable format.

Key Features:
    - **Template Storage**: Local filesystem-backed registry with JSON serialization
    - **Built-in Templates**: Pre-configured templates for common financial models (LBO, real estate, etc.)
    - **Template Comparison**: Structural and value-based diffing between templates
    - **Forecasting Integration**: Declarative forecast specifications embedded in templates
    - **Preprocessing Pipelines**: Automated data transformation workflows
    - **Version Management**: Semantic versioning with automatic increment

Basic Usage:
    >>> from fin_statement_model.templates import TemplateRegistry, install_builtin_templates
    >>>
    >>> # Install built-in templates
    >>> install_builtin_templates()
    >>>
    >>> # List available templates
    >>> templates = TemplateRegistry.list()
    >>> print(templates)  # ['lbo.standard_v1', 'real_estate_lending_v3']
    >>>
    >>> # Instantiate a template as a working graph
    >>> graph = TemplateRegistry.instantiate("lbo.standard_v1")
    >>> print(f"Graph has {len(graph.nodes)} nodes and {len(graph.periods)} periods")

Advanced Usage:
    >>> # Register a custom template
    >>> template_id = TemplateRegistry.register_graph(
    ...     my_graph, name="custom.model", meta={"category": "custom", "description": "My custom model"}
    ... )
    >>>
    >>> # Compare templates
    >>> diff_result = TemplateRegistry.diff("lbo.standard_v1", template_id)
    >>> print(f"Added nodes: {diff_result.structure.added_nodes}")
    >>>
    >>> # Instantiate with customizations
    >>> customized_graph = TemplateRegistry.instantiate(
    ...     "lbo.standard_v1", periods=["2029", "2030"], rename_map={"Revenue": "TopLineRevenue"}
    ... )

See Also:
    - User Guide → Statement Templates: `docs/registry_templates.md`
    - Built-in template data: `fin_statement_model.templates.builtin.data`
"""

from fin_statement_model.templates.builtin import install_builtin_templates
from fin_statement_model.templates.models import DiffResult, TemplateBundle, TemplateMeta
from fin_statement_model.templates.registry import TemplateRegistry

__all__ = [
    "DiffResult",
    "TemplateBundle",
    "TemplateMeta",
    "TemplateRegistry",
    "install_builtin_templates",
]
