from __future__ import annotations

"""Unit-tests for the *handle_read_errors* and *handle_write_errors* decorators.

These decorators are a thin but critical abstraction that normalise arbitrary
exceptions into the IO-specific *ReadError* / *WriteError* hierarchy.  To keep
things self-contained, we define dummy reader/writer classes locally.
"""

from typing import Any

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.exceptions import ReadError, WriteError
from fin_statement_model.io.core.mixins import handle_read_errors, handle_write_errors
from fin_statement_model.io.core.base import DataReader, DataWriter


class _BoomReader(DataReader):
    """Reader that always explodes (simulates FileNotFoundError)."""

    @handle_read_errors()
    def read(self, source: Any, **_kw: Any):  # type: ignore[override]
        raise FileNotFoundError("nope")


class _BoomWriter(DataWriter):
    """Writer that always explodes (simulates generic crash)."""

    @handle_write_errors()
    def write(self, graph: Graph, target: Any, **_kw: Any):  # type: ignore[override]
        raise RuntimeError("kaboom")


def test_handle_read_errors_wrapper() -> None:
    """The decorated reader should translate FileNotFoundError → ReadError."""
    reader = _BoomReader()
    with pytest.raises(ReadError):
        reader.read("missing.csv")


def test_handle_write_errors_wrapper() -> None:  # noqa: D401
    """The decorated writer should translate generic Exception → WriteError."""
    g = Graph(periods=["2023"])
    writer = _BoomWriter()
    with pytest.raises(WriteError):
        writer.write(g, target="ignored")
