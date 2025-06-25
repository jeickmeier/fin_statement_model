"""Command-line interface entry point for the *fin-statement-model* toolkit.

Currently exposes a single sub-command:

    $ fsm template ls

which prints a table of registered template bundles.
"""

from __future__ import annotations

import click

from fin_statement_model.templates.registry import TemplateRegistry

__all__: list[str] = ["fsm"]


@click.group()
def fsm() -> None:
    """Finance Statement Model command-line tool."""


@fsm.group()
def template() -> None:
    """Template Registry commands."""


@template.command("ls")
@click.option("--plain", is_flag=True, help="Print as plain list (one id per line).")
def list_templates(plain: bool) -> None:
    """List all registered template identifiers."""
    ids = TemplateRegistry.list()
    if plain or not ids:
        click.echo("\n".join(ids))
        return

    # Build simple aligned table
    header = ("TEMPLATE ID",)
    rows: list[tuple[str]] = [(ident,) for ident in ids]
    col_width = max(len(header[0]), *(len(r[0]) for r in rows))
    click.echo(f"{header[0]:<{col_width}}")
    click.echo("-" * col_width)
    for row in rows:
        click.echo(f"{row[0]:<{col_width}}")


# ---------------------------------------------------------------------------
# Support `python -m fin_statement_model.cli` execution without console script
# ---------------------------------------------------------------------------


def _module_main() -> None:  # pragma: no cover - executed manually
    """Run :pyfunc:`fsm` if invoked as a module (``python -m ...``)."""
    # Click does not support being called with argv injection in older versions.
    fsm(standalone_mode=False)


if __name__ == "__main__":  # pragma: no cover
    _module_main()
