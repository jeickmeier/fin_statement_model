"""Abstract base classes for data readers and writers.

This module defines the fundamental contracts for all I/O operations in the
financial statement model library. It provides two abstract base classes:

- `DataReader`: Defines the interface for all classes that read data from
  various sources (e.g., files, APIs) and populate a `Graph` object.
- `DataWriter`: Defines the interface for all classes that write data from a
  `Graph` object to various destinations.

These classes ensure that all I/O handlers adhere to a consistent, predictable
API, centered around the `read()` and `write()` methods.
"""

from abc import ABC, abstractmethod
from typing import Any

# Use absolute import based on project structure
from fin_statement_model.core.graph import Graph


class DataReader(ABC):
    """Abstract base class for all data readers.

    This ABC defines the contract for all reader classes in the I/O subpackage.
    Any class that reads data from an external source (like a file or API) and
    transforms it into a `Graph` object should inherit from `DataReader`.

    Subclasses must implement the `read` method.
    """

    @abstractmethod
    def read(self, source: Any, **kwargs: dict[str, Any]) -> Graph:
        """Read data from the specified source and return a Graph.

        Args:
            source: The data source. Type depends on the reader implementation
                (e.g., file path `str`, ticker `str`, `pd.DataFrame`, `dict`).
            **kwargs: Additional format-specific options for reading.

        Returns:
            A Graph object populated with the data from the source.

        Raises:
            ReadError: If an error occurs during the reading process.
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError


class DataWriter(ABC):
    """Abstract base class for all data writers.

    This ABC defines the contract for all writer classes in the I/O subpackage.
    Any class that serializes a `Graph` object into an external format (like a
    file or a dictionary) should inherit from `DataWriter`.

    Subclasses must implement the `write` method.
    """

    @abstractmethod
    def write(self, graph: Graph, target: Any, **kwargs: dict[str, Any]) -> object:
        """Write data from the Graph object to the specified target.

        Args:
            graph: The Graph object containing the data to write.
            target: The destination target. Type depends on the writer implementation
                (e.g., file path `str`, or ignored if the writer returns an object).
            **kwargs: Additional format-specific options for writing.

        Raises:
            WriteError: If an error occurs during the writing process.
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError
