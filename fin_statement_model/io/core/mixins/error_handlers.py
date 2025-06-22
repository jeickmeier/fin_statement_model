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


def handle_read_errors() -> Callable[[F], F]:
    """Create a decorator to wrap reader methods and convert generic exceptions.

    This decorator is designed to be applied to the `read` method of any `DataReader`
    subclass. It catches common exceptions that may occur during a read operation—such
    as `FileNotFoundError` or `ValueError`—and re-raises them as a `ReadError`,
    enriching them with contextual information like the source and reader type.

    This standardization allows callers to handle all read-related failures by
    catching a single, specific exception type.

    Returns:
        A decorator that can be applied to a reader's `read` method.

    Example:
        ```python
        # class MyReader(DataReader):
        #     @handle_read_errors()
        #     def read(self, source: str, **kwargs) -> Graph:
        #         # ... implementation that might raise FileNotFoundError, etc.
        #         if not os.path.exists(source):
        #             raise FileNotFoundError(f"Can't find {source}")
        #         return Graph()
        #
        # # Calling MyReader().read("bad_path.txt") will raise a ReadError.
        ```
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


def handle_write_errors() -> Callable[[F], F]:
    """Create a decorator to wrap writer methods and convert generic exceptions.

    This decorator is designed to be applied to the `write` method of any `DataWriter`
    subclass. It catches generic `Exception` instances that may occur during a write
    operation and re-raises them as a `WriteError`, enriching them with context
    such as the target and writer type.

    This standardization allows callers to handle all write-related failures by
    catching a single, specific exception type.

    Returns:
        A decorator that can be applied to a writer's `write` method.

    Example:
        ```python
        # class MyWriter(DataWriter):
        #     @handle_write_errors()
        #     def write(self, graph: Graph, target: str, **kwargs):
        #         # ... implementation that might raise IOError, etc.
        #         with open(target, 'w') as f: # This could fail
        #             f.write("data")
        #
        # # Calling MyWriter().write(g, "/no_permission/file.txt") will raise WriteError.
        ```
    """

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
