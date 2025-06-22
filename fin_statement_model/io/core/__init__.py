"""Core IO components including base classes, registry, and utilities."""

from .base import DataReader, DataWriter
from .facade import read_data, write_data
from .mixins import (
    FileBasedReader,
    ConfigurationMixin,
    DataFrameBasedWriter,
    ValueExtractionMixin,
    ValidationResultCollector,
    handle_read_errors,
    handle_write_errors,
)
from .registry import (
    HandlerRegistry,
    get_reader,
    get_writer,
    list_readers,
    list_writers,
    register_reader,
    register_writer,
)

__all__ = [
    # Base classes
    "DataReader",
    "DataWriter",
    # Mixins and utilities
    "ConfigurationMixin",
    "DataFrameBasedWriter",
    "FileBasedReader",
    "handle_read_errors",
    "handle_write_errors",
    # Registry
    "HandlerRegistry",
    "ValidationResultCollector",
    "ValueExtractionMixin",
    "get_reader",
    "get_writer",
    "list_readers",
    "list_writers",
    "register_reader",
    "register_writer",
    # Facade functions
    "read_data",
    "write_data",
]
