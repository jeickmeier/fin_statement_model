"""Template Registry & Engine (TRE) public API.

See the *User Guide → Statement Templates* (`docs/registry_templates.md`) for a hands-on
walk-through of typical usage patterns.
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
