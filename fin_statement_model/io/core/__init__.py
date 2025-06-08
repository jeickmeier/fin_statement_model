"""Core IO components including base classes, registry, and utilities."""

from .base import DataReader, DataWriter
from .facade import read_data, write_data
from .mixins import (
    FileBasedReader,
    ConfigurationMixin,
    DataFrameBasedWriter,
    ValueExtractionMixin,
    BatchProcessingMixin,
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
    # Mixins and utilities
    "BatchProcessingMixin",
    "ConfigurationMixin",
    "DataFrameBasedWriter",
    # Base classes
    "DataReader",
    "DataWriter",
    "FileBasedReader",
    # Registry
    "HandlerRegistry",
    "ValidationResultCollector",
    "ValueExtractionMixin",
    "get_reader",
    "get_writer",
    "handle_read_errors",
    "handle_write_errors",
    "list_readers",
    "list_writers",
    # Facade functions
    "read_data",
    "register_reader",
    "register_writer",
    "write_data",
]
