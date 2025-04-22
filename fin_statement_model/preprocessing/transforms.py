"""Delegate data transformation pipeline to TransformationService.

This module provides `apply_transformation_pipeline` to run transformer sequences.
"""

from __future__ import annotations

from typing import Any
import logging


from .transformation_service import TransformationService
from .types import TabularData


logger = logging.getLogger(__name__)

__all__ = ["apply_transformation_pipeline"]


def apply_transformation_pipeline(
    data: TabularData,  # type: ignore
    transformers_config: list[dict[str, Any]],
) -> TabularData:  # type: ignore
    """Apply a sequence of transformations to data using TransformationService.

    Each config dictionary must contain a 'name' key and transformer-specific parameters.

    Args:
        data: Input data (DataFrame or dict) to transform
        transformers_config: List of transformer configuration dicts

    Returns:
        Transformed data (same type as input)
    """
    logger.debug("Applying transformer pipeline: %s", transformers_config)
    service = TransformationService()
    return service.apply_transformation_pipeline(data, transformers_config)
