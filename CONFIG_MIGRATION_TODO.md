# Config Migration Project - Remaining Tasks

## Project Overview

This document tracks the remaining tasks for migrating hard-coded defaults to configuration-based defaults throughout the fin_statement_model library.

### What Was Completed (Phases 1-3)

#### Phase 1: Discovery & Gap Analysis ✅
- Created audit scripts to find all config keys and hard-coded values
- Found 198 hard-coded values across 48 source files
- Identified 72 functions needing config integration

#### Phase 2: Implementation Infrastructure ✅
- Created `fin_statement_model/config/utils.py` with helper functions:
  - `cfg()` - Get config values by dotted path
  - `cfg_or_param()` - Use parameter or config default
  - `get_typed_config()` - Type-safe config access
  - Convenience functions like `default_periods()`, `api_timeout()`
- Created `fin_statement_model/config/decorators.py` with migration decorators:
  - `uses_config_default()` - Single parameter replacement
  - `migrate_to_config()` - Multiple parameters
  - `config_aware_init()` - Class initialization
  - `warn_hardcoded_default()` - Migration warnings
- Created 45 comprehensive unit tests - all passing

#### Phase 3: Refactor Modules ✅
**Task 7: Adjust public APIs** ✅
- Updated `Section`, `StatementStructure`, `LineItem`, and related classes to use config defaults for `display_scale_factor`
- Updated retry handler functions to use config defaults for `max_attempts`

**Task 8: Review dataclasses/constructors** ✅
- Verified dataclasses use appropriate config defaults
- Updated `RetryConfig` to use config default for `max_attempts`

**Task 9: Replace module constants** ✅
- Found minimal module-level constants duplicating config values
- Most constants are appropriately used for different purposes

**Task 10: Verify layer hierarchy** ✅
- Confirmed all config imports respect the layer hierarchy
- Config module is at library root level, accessible to all sub-packages

**Additional Updates Completed:**
- Fixed `0.0` → `forecasting.default_growth_rate` in:
  - `core/nodes/forecast_nodes.py` (multiple occurrences)
  - `forecasting/forecaster.py` (2 occurrences)
- Fixed `1.0` → `display.scale_factor` in:
  - `statements/formatting/formatter.py`
- Fixed `3` → `api.api_retry_count` in:
  - `extensions/llm/llm_client.py`
- Fixed `"simple"` → `forecasting.default_method` in:
  - `forecasting/forecaster.py`
- Fixed `"parentheses"` → `display.contra_display_style` in:
  - `statements/formatting/formatter.py`
- Fixed `","` → `io.default_csv_delimiter` in:
  - `io/formats/csv/reader.py`
- Fixed `30` → `api.api_timeout` in:
  - `extensions/llm/llm_client.py`
  - `io/formats/api/fmp.py` (2 occurrences)

## Remaining Tasks

### Phase 4: Tests & Validation

#### Task 11: Update unit tests for config
**Priority: High**
- Update test files to use config values instead of hard-coded defaults
- Add test fixtures that use `cfg()` or `get_config()`
- Ensure tests don't break when config values change
- Files needing updates (from audit):
  - 36 test files identified as HIGH RISK
  - Focus on tests that assert specific default values

**Steps:**
1. Create shared test fixtures for common config values
2. Update test assertions to use config values
3. Add tests for config overrides
4. Ensure backward compatibility

#### Task 12: Write integration tests
**Priority: Medium**
- Test config changes propagate correctly through the system
- Test runtime config updates work as expected
- Test environment variable overrides
- Test config file loading

**Test scenarios:**
1. Config changes affect calculation results
2. Display formatting respects config values
3. API retry/timeout behavior follows config
4. Forecast defaults use config values

#### Task 13: Document migration patterns
**Priority: High**
- Create developer guide for using config system
- Document best practices for adding new config values
- Create migration guide for external users
- Update API documentation

**Documentation needed:**
1. `docs/developer/configuration.md` - How to use the config system
2. `docs/migration/config_migration_guide.md` - For users upgrading
3. Update docstrings in affected modules
4. Add config examples to README

### Phase 5: Tooling & CI

#### Task 14: Add pre-commit checks
**Priority: Medium**
- Create custom pre-commit hook to detect hard-coded values
- Add to `.pre-commit-config.yaml`
- Check for common patterns: `= 0.0`, `= "simple"`, etc.

**Implementation:**
1. Write Python script to scan for hard-coded defaults
2. Configure as pre-commit hook
3. Add exceptions list for legitimate uses
4. Document in contributing guide

#### Task 15: CI validation for config usage
**Priority: Low**
- Add GitHub Actions workflow to check config usage
- Run on pull requests
- Generate report of potential hard-coded values

#### Task 16: Config validation tooling
**Priority: Medium**
- Create tool to validate config files
- Check for missing required values
- Validate types and ranges
- Support for config file generation

**Features:**
1. `python -m fin_statement_model.config validate <config_file>`
2. `python -m fin_statement_model.config generate-template`
3. Schema validation using Pydantic models

#### Task 17: Performance optimization
**Priority: Low**
- Profile config access patterns
- Add caching if needed
- Optimize hot paths
- Consider lazy loading for large configs

### Phase 6: Future Guardrails

#### Task 18: Establish config governance
**Priority: Medium**
- Define process for adding new config values
- Create config naming conventions
- Document config deprecation process
- Set up config review checklist

**Deliverables:**
1. Config governance document
2. Pull request template updates
3. Config review checklist
4. Deprecation policy

#### Task 19: Monitor and iterate
**Priority: Ongoing**
- Track config usage metrics
- Gather developer feedback
- Identify pain points
- Plan future improvements

**Metrics to track:**
1. Most/least used config values
2. Config-related bugs/issues
3. Developer satisfaction
4. Performance impact

## Migration Checklist

Before considering the migration complete:

- [ ] All hard-coded values replaced (where appropriate)
- [ ] All tests passing with config values
- [ ] Documentation updated
- [ ] Pre-commit hooks in place
- [ ] CI checks implemented
- [ ] Performance validated
- [ ] Developer guide published
- [ ] Migration guide for users
- [ ] Config governance established
- [ ] Team trained on new patterns

## Notes for Future Reference

### Config Keys Reference
Total config keys: 51 (see `scripts/config_audit/config_inventory.json`)

### Most Impactful Changes
1. `forecasting.default_growth_rate` - 30 usages
2. `display.scale_factor` - 24 usages  
3. `api.api_retry_count` - 13 usages
4. `forecasting.default_periods` - 8 usages
5. `forecasting.default_method` - 6 usages

### Migration Patterns Used
1. Direct replacement: `cfg("config.path")`
2. Parameter defaults: `cfg_or_param("config.path", param)`
3. Dataclass fields: `field(default_factory=lambda: cfg("config.path"))`
4. Fallback patterns: `value or cfg("config.path", default)`

### Lessons Learned
- Some hard-coded values are legitimate (e.g., mathematical constants)
- Context matters - not all 0.0 values are growth rates
- Test files need special consideration to avoid circular dependencies
- Performance impact is minimal for config access
- Type safety is important - use `get_typed_config()` where possible

*Last updated: 2025-05-29*
*Phases 1-3 completed by: Assistant + joneickmeier* 