# I/O Core Components

This package contains the foundational building blocks of the I/O subsystem. It is not typically used directly by end-users, but provides the core abstractions and utilities that all readers and writers are built upon.

## Key Components

- **`base.py`**: Defines the abstract base classes `DataReader` and `DataWriter`, which establish the fundamental `read()` and `write()` contracts for all I/O handlers.

- **`facade.py`**: Contains the high-level `read_data` and `write_data` functions, which are the primary public entry points for the entire I/O package.

- **`registry.py`**: Implements the `HandlerRegistry` system. This is the heart of the I/O framework's extensibility, allowing new formats to be registered with decorators (`@register_reader`, `@register_writer`) and associated with a Pydantic configuration schema.

- **`mixins/`**: This sub-package provides a collection of reusable components (mixin classes) that offer shared functionality to I/O handlers:
    - `ConfigurationMixin`: Manages access to Pydantic configuration objects, runtime overrides, and environment variable fallbacks.
    - `MappingAwareMixin`: Adds support for mapping source data names (e.g., from an API or file) to the library's canonical node names using YAML configuration files.
    - `ValidationMixin`: Provides a suite of helpers for validating data during the read process (e.g., checking for required columns, validating numeric values).
    - `FileBasedReader`: A base class for readers that ingest data from the filesystem, providing helpers for file existence and extension checks.
    - `error_handlers.py`: Contains the `@handle_read_errors` and `@handle_write_errors` decorators, which standardize exception handling by converting generic exceptions into specific `ReadError` or `WriteError` types. 