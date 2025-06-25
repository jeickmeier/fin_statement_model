"""Command-line interface entry point for the *fin-statement-model* toolkit.

Currently exposes a single sub-command:

    $ fsm template ls

which prints a table of registered template bundles.
"""

from __future__ import annotations

# Standard library
import json
from typing import TYPE_CHECKING

# Third-party
import click

from fin_statement_model.templates.registry import TemplateRegistry

# Type-checking imports ------------------------------------------------------
if TYPE_CHECKING:  # pragma: no cover
    from fin_statement_model.templates.models import DiffResult

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
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_periods(spec: str | None) -> list[str] | None:
    """Parse *spec* into an explicit period list.

    Supported syntaxes:
    1. Comma-separated list  -> "2023,2024" → ["2023", "2024"].
    2. Inclusive range A:B   -> "2023:2025" → ["2023", "2024", "2025"].

    Returns None when *spec* is None.
    """
    if spec is None:
        return None

    spec = spec.strip()
    if not spec:
        raise click.BadParameter("Period specification cannot be empty.")

    if ":" in spec:
        try:
            start_s, end_s = spec.split(":", 1)
            start, end = int(start_s), int(end_s)
        except ValueError as exc:  # pragma: no cover
            raise click.BadParameter("Invalid range syntax for --periods. Use YYYY:YYYY.") from exc
        if end < start:
            raise click.BadParameter("End year must be >= start year in --periods range.")
        return [str(y) for y in range(start, end + 1)]

    # Comma-separated list
    return [part.strip() for part in spec.split(",") if part.strip()]


def _parse_rename(pairs: tuple[str, ...] | None) -> dict[str, str] | None:
    """Convert multiple --rename "old=new" pairs to a mapping."""
    if not pairs:
        return None
    mapping: dict[str, str] = {}
    for p in pairs:
        if "=" not in p:
            raise click.BadParameter("--rename must be in the form OLD=NEW")
        old, new = p.split("=", 1)
        if not old or not new:
            raise click.BadParameter("--rename entries cannot be empty")
        mapping[old] = new
    return mapping or None


# ---------------------------------------------------------------------------
# `fsm template apply` command
# ---------------------------------------------------------------------------


@template.command("apply")
@click.argument("template_id", type=str)
@click.option("--periods", "period_spec", type=str, default=None, help="Extra periods to append (e.g. 2024:2028).")
@click.option(
    "--rename",
    "rename_pairs",
    multiple=True,
    help="Rename nodes OLD=NEW (can be repeated).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(
        [
            "graph_definition_dict",
            "dict",
            "dataframe",
            "excel",
            "csv",
            "markdown",
            "json",
        ],
        case_sensitive=False,
    ),
    default="graph_definition_dict",
    show_default=True,
    help="Output format handled by IO writers.",
)
@click.option("--output", "output_target", type=str, default=None, help="File path to write (defaults to STDOUT).")
@click.option("--quiet", is_flag=True, help="Suppress success message.")
@click.pass_context
def apply_template(
    ctx: click.Context,
    template_id: str,
    period_spec: str | None,
    rename_pairs: tuple[str, ...],
    output_format: str,
    output_target: str | None,
    quiet: bool,
) -> None:
    """Instantiate a template and write it via the IO facade."""
    from fin_statement_model.io import write_data

    periods: list[str] | None = _parse_periods(period_spec)
    rename_map = _parse_rename(rename_pairs)

    # Instantiate graph ------------------------------------------------------
    try:
        graph = TemplateRegistry.instantiate(template_id, periods=periods, rename_map=rename_map)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    # Write output -----------------------------------------------------------
    try:
        result = write_data(output_format, graph, output_target)
    except Exception as exc:
        raise click.ClickException(f"Failed to write data: {exc}") from exc

    # Persist manually when writer returns mapping and target path provided
    if output_target is not None and output_format in {"graph_definition_dict", "dict", "json"}:
        from pathlib import Path

        Path(output_target).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    # STDOUT handling --------------------------------------------------------
    if output_target is None:
        # For dictionary-like writers, pretty-print JSON; else str(result)
        if output_format in {"graph_definition_dict", "dict", "json"}:
            click.echo(json.dumps(result, indent=2, sort_keys=True))
        else:
            # Some writers return str/df just echo representation.
            click.echo(str(result))

    if not quiet:
        click.echo(f"Template instantiated -> {output_target or 'stdout'}")

    ctx.exit(0)


# ---------------------------------------------------------------------------
# `fsm template diff` command
# ---------------------------------------------------------------------------


def _render_markdown_diff(diff_res: DiffResult, *, limit: int = 20) -> str:
    """Return a Markdown table summary of *diff_res*."""
    lines: list[str] = []
    struct = diff_res.structure
    lines.append("### Structural changes")
    lines.append("")
    lines.append(f"* **Added nodes**: {len(struct.added_nodes)}")
    lines.append(f"* **Removed nodes**: {len(struct.removed_nodes)}")
    lines.append(f"* **Changed nodes**: {len(struct.changed_nodes)}")

    if struct.added_nodes:
        lines.append("")
        lines.append("#### Added")
        lines.extend([f"- `{n}`" for n in struct.added_nodes[:limit]])
        if len(struct.added_nodes) > limit:
            lines.append(f"_... {len(struct.added_nodes) - limit} more_")

    if struct.removed_nodes:
        lines.append("")
        lines.append("#### Removed")
        lines.extend([f"- `{n}`" for n in struct.removed_nodes[:limit]])
        if len(struct.removed_nodes) > limit:
            lines.append(f"_... {len(struct.removed_nodes) - limit} more_")

    if struct.changed_nodes:
        lines.append("")
        lines.append("#### Changed")
        lines.extend([f"- `{n}` - {desc}" for n, desc in list(struct.changed_nodes.items())[:limit]])
        if len(struct.changed_nodes) > limit:
            lines.append(f"_... {len(struct.changed_nodes) - limit} more_")

    if diff_res.values is not None:
        val = diff_res.values
        lines.append("")
        lines.append("### Value changes")
        lines.append("")
        lines.append(f"Changed cells: **{len(val.changed_cells)}** | Max Δ = **{val.max_delta}**")
        if val.changed_cells:
            lines.append("")
            lines.append("| Node | Period | Δ |")
            lines.append("|------|--------|---|")
            for cell_key, delta in list(val.changed_cells.items())[:limit]:
                node_id, period = cell_key.split("|", 1)
                lines.append(f"| {node_id} | {period} | {delta:.4g} |")
            if len(val.changed_cells) > limit:
                lines.append(f"| ... | ... | _{len(val.changed_cells) - limit} more_ |")

    return "\n".join(lines)


@template.command("diff")
@click.argument("template_a", type=str)
@click.argument("template_b", type=str)
@click.option("--no-values", "include_values", flag_value=False, default=True, help="Skip value comparison.")
@click.option("--periods", "period_spec", type=str, default=None, help="Restrict value comparison to given periods.")
@click.option("--atol", type=float, default=1e-9, show_default=True, help="Absolute tolerance for value deltas.")
@click.option(
    "--format",
    "out_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Output format.",
)
@click.option("--summary", is_flag=True, help="Print 1-liner summary and exit code reflects diff presence.")
@click.pass_context
def diff_templates(
    ctx: click.Context,
    template_a: str,
    template_b: str,
    include_values: bool,
    period_spec: str | None,
    atol: float,
    out_format: str,
    summary: bool,
) -> None:
    """Show structure / value differences between two templates."""
    periods = _parse_periods(period_spec)

    try:
        diff_res = TemplateRegistry.diff(
            template_a,
            template_b,
            include_values=include_values,
            periods=periods,
            atol=atol,
        )
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(str(exc)) from exc

    # Determine diff presence ------------------------------------------------
    has_struct = any([
        diff_res.structure.added_nodes,
        diff_res.structure.removed_nodes,
        diff_res.structure.changed_nodes,
    ])
    has_vals = diff_res.values is not None and bool(diff_res.values.changed_cells)
    diff_present = has_struct or has_vals

    if summary:
        msg = "DIFF" if diff_present else "NO-DIFF"
        click.echo(msg)
        ctx.exit(1 if diff_present else 0)

    # Full output ------------------------------------------------------------
    if out_format == "json":
        click.echo(json.dumps(diff_res.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        click.echo(_render_markdown_diff(diff_res))

    ctx.exit(1 if diff_present else 0)


# ---------------------------------------------------------------------------
# Support `python -m fin_statement_model.cli` execution without console script
# ---------------------------------------------------------------------------


def _module_main() -> None:  # pragma: no cover - executed manually
    """Run :pyfunc:`fsm` if invoked as a module (``python -m ...``)."""
    # Click does not support being called with argv injection in older versions.
    fsm(standalone_mode=False)


if __name__ == "__main__":  # pragma: no cover
    _module_main()
