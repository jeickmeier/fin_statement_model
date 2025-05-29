"""Graph population functionality for financial statements.

This package handles the conversion of statement structures into graph nodes:
- ID resolution between statement items and graph nodes
- Processing different item types (metrics, calculations, subtotals)
- Managing dependencies and retry logic
"""

from .id_resolver import IDResolver
from .item_processors import (
    CalculatedItemProcessor,
    ItemProcessor,
    ItemProcessorManager,
    MetricItemProcessor,
    ProcessorResult,
    SubtotalItemProcessor,
)
from .populator import populate_graph_from_statement

__all__ = [
    "CalculatedItemProcessor",
    # ID Resolution
    "IDResolver",
    # Item Processors
    "ItemProcessor",
    "ItemProcessorManager",
    "MetricItemProcessor",
    "ProcessorResult",
    "SubtotalItemProcessor",
    # Main Function
    "populate_graph_from_statement",
]
