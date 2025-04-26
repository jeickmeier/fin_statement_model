# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - UNRELEASED

### Added

- Introduced Pydantic configuration models for IO writers: `ExcelWriterConfig`, `DataFrameWriterConfig`, and `DictWriterConfig` in `fin_statement_model.io.config.models`.
- Writer classes now support initialization via Pydantic config objects and store the config in `self.cfg`.
- Added Pydantic-based validation in `get_writer` to enforce schema correctness and raise `WriteError` on invalid parameters.
- Updated `write_data` facade to pass `target` as an init argument for Pydantic validation of writer config.

### Changed

- `get_writer` dispatch logic now mirrors `get_reader`, including configuration validation and error wrapping with `WriteError`.
- Writer classes (`ExcelWriter`, `DataFrameWriter`, `DictWriter`) have an `__init__` accepting a config object and merge this config with per-call overrides in `write()`.

### Fixed

- No public API changes; backwards compatibility maintained for callers using `write_data` with keyword arguments. 