"""Base classes for data readers and writers."""

from abc import ABC, abstractmethod
from typing import Any

# Use absolute import based on project structure
from fin_statement_model.core.graph import Graph


class DataReader(ABC):
    """Abstract base class for all data readers.

    Defines the interface for classes that read data from various sources
    and typically populate or return a Graph object.
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

    Defines the interface for classes that write graph data to various targets.
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
