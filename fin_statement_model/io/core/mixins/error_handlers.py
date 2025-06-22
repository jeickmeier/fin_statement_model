"""Error-handling decorators extracted from the legacy *mixins.py* module.

These decorators should be applied to `read()` and `write()` implementations
of concrete readers/writers to standardise exception conversion into
:class:`fin_statement_model.io.exceptions.ReadError` / `WriteError`.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from fin_statement_model.io.exceptions import ReadError, WriteError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_read_errors(source_attr: str = "source") -> Callable[[F], F]:
    """Decorator that wraps *reader* methods and converts generic exceptions.

    On failure it raises :class:`ReadError` enriched with context; otherwise
    it returns the wrapped function's result unmodified.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self: Any, source: Any, **kwargs: Any) -> Any:  # noqa: ANN001
            try:
                return func(self, source, **kwargs)
            except ReadError:
                raise  # Re-raise as-is so callers can pattern-match
            except FileNotFoundError as e:
                err = ReadError(
                    f"File not found: {source}",
                    source=str(source),
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )
                raise err.with_traceback(e.__traceback__) from e
            except ValueError as e:
                err = ReadError(
                    f"Invalid value encountered: {e}",
                    source=str(source),
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )
                raise err.with_traceback(e.__traceback__) from e
            except (
                Exception
            ) as e:  # noqa: BLE001 – We really want to catch *everything* here.
                logger.error("Failed to read from %s: %s", source, e, exc_info=True)
                err = ReadError(
                    f"Failed to process source: {e}",
                    source=str(source),
                    reader_type=self.__class__.__name__,
                    original_error=e,
                )
                raise err.with_traceback(e.__traceback__) from e

        return wrapper  # type: ignore[return-value]

    return decorator


def handle_write_errors(target_attr: str = "target") -> Callable[[F], F]:
    """Decorator that wraps *writer* methods and converts generic exceptions."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(
            self: Any, graph: Any, target: Any = None, **kwargs: Any
        ) -> Any:  # noqa: ANN001
            try:
                return func(self, graph, target, **kwargs)
            except WriteError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to write to %s: %s", target, e, exc_info=True)
                err = WriteError(
                    f"Failed to write data: {e}",
                    target=str(target) if target else "unknown",
                    writer_type=self.__class__.__name__,
                    original_error=e,
                )
                raise err.with_traceback(e.__traceback__) from e

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = [
    "handle_read_errors",
    "handle_write_errors",
]
