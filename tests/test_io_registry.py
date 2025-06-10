import pytest

from fin_statement_model.io.core.registry import register_writer, get_writer, _writer_registry
from fin_statement_model.io.exceptions import UnsupportedWriterError
from fin_statement_model.io.formats.markdown.writer import MarkdownWriter


def test_register_writer_without_schema_raises():
    with pytest.raises(ValueError) as exc:
        @register_writer("noschema")
        class NoSchemaWriter:
            pass
    assert "Schema required for writer 'noschema'; legacy schema-less mode removed." in str(exc.value)


def test_get_writer_without_schema_raises():
    # Simulate legacy writer registration without schema
    class FakeWriter:
        def __init__(self, cfg):
            pass
    _writer_registry._registry["fake"] = FakeWriter
    _writer_registry._schema_map.pop("fake", None)

    with pytest.raises(UnsupportedWriterError) as exc:
        get_writer("fake", target="t")
    assert "Writer 'fake' requires a Pydantic schema; legacy schema-less mode removed." in str(exc.value)


def test_get_writer_markdown_returns_instance():
    writer = get_writer("markdown")
    assert isinstance(writer, MarkdownWriter) 