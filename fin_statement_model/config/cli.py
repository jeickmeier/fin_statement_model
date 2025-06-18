"""Command-line interface for fin_statement_model configuration.

This lightweight CLI lets users inspect and mutate runtime configuration
without writing Python code.

Usage (once installed as `fsm-config` entry-point):

    $ fsm-config show logging.level
    WARNING

    $ fsm-config set logging.level DEBUG
    Updated logging.level → DEBUG
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from .helpers import cfg
from .manager import get_config, update_config, _config_manager

app = typer.Typer(help="Configuration management commands for fin_statement_model")


@app.command()
def show(
    path: Optional[str] = typer.Argument(None, help="Config dotted path to show")
) -> None:  # noqa: D401
    """Display configuration values.

    If *path* is omitted, the full configuration is printed in YAML format.
    """

    if path is None:
        typer.echo(get_config().to_yaml())
    else:
        try:
            value = cfg(path, strict=True)
            typer.echo(json.dumps(value, indent=2, default=str))
        except Exception as exc:  # noqa: BLE001
            typer.secho(str(exc), err=True, fg=typer.colors.RED)
            raise typer.Exit(1) from exc


@app.command()
def set(
    path: str = typer.Argument(..., help="Config dotted path to set"),
    value: str = typer.Argument(..., help="New value (JSON encoded if complex)"),
) -> None:  # noqa: D401
    """Set a configuration value at *path*.

    The *value* is interpreted as JSON. For simple scalars you may pass raw
    strings without quotes, e.g. `DEBUG`.
    """
    try:
        parsed: Any
        try:
            parsed = json.loads(value)
        except Exception:
            # Fallback to raw string
            parsed = value

        segments = path.split(".")
        current: dict[str, Any] = {}
        nested = current
        for seg in segments[:-1]:
            nested = nested.setdefault(seg, {})
        nested[segments[-1]] = parsed

        update_config(current)
        typer.echo(f"Updated {path} → {parsed}")
    except Exception as exc:  # noqa: BLE001
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc


@app.command()
def save(
    path: Optional[Path] = typer.Option(None, help="Path to save configuration")
) -> None:  # noqa: D401
    """Persist current configuration to *path* (or default user config)."""
    try:
        _config_manager.save(path)
        typer.echo("Configuration saved ✅")
    except Exception as exc:  # noqa: BLE001
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc


@app.command()
def reload() -> None:  # noqa: D401
    """Reload configuration from all sources (discard runtime overrides)."""
    # Clear cached config and overrides
    _config_manager._runtime_overrides.clear()
    _config_manager._config = None
    typer.echo("Configuration reloaded")


def run() -> None:
    """Entry-point for `python -m fin_statement_model.config.cli`."""
    app()


if __name__ == "__main__":  # pragma: no cover
    run()
