# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - UNRELEASED

### Config Module Refactor
- Remove legacy decorators (`uses_config_default`, `migrate_to_config`, `warn_hardcoded_default`) and associated tests
- Introduce `config/_traversal.py` with `walk_model()` to centralize Pydantic model traversal
- Refactor `list_all_config_paths`, `generate_env_mappings`, `get_field_type_info`, and `ParamMapper._search_model_recursive` to use `walk_model`
- Unify `list_config_paths()` to delegate to `list_all_config_paths()` with prefix filtering
- Extract `DEFAULT_MAPPINGS` constant for `ParamMapper` and simplify `clear_custom_mappings()`
- Add `parse_env_value()` helper and refactor `ConfigManager._load_from_env` to use it
- Remove unused imports and dead code from `/config` modules

