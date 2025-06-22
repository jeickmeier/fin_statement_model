# IO Package – Backlog Todo List

This list captures **deferred / nice-to-have** improvements that were
identified during the Phase-1-to-3 refactor but intentionally postponed.

Legend:  
- [ ] = not started  
- [~] = in progress  
- [x] = completed / merged into `main`

---
## 1. Chained Mapping Support (`MappingAwareMixin`)

- [ ] Add optional `project_mapping_loader: Callable[[], MappingConfig]` class
      attribute. When provided, the mixin should call it once and cache the
      project-level mapping.  
- [ ] Merge precedence: *default* < *project* < *instance* (`mapping_config`).  
- [ ] Update unit tests to cover precedence and immutability of cached mappings.

## 2. Diagnostics CLI (`fsm-io doctor`)

- [ ] New CLI entry-point in `fin_statement_model.cli.doctor`.  
- [ ] Use `rich` for pretty printing (add optional dependency).  
- [ ] Report:
  - Registered readers/writers and associated schema names.  
  - Available optional dependencies (e.g. `openpyxl`, `pyarrow`).  
  - Detected ENV variables (`FMP_API_KEY` etc.) – mask values.  
  - File-extension coverage per reader.
- [ ] Add integration test that runs `fsm-io doctor --json` pipeable output.

## 3. Async FMP Bulk Fetcher

- [ ] Create `AsyncFmpReader` in `io.formats.fmp_reader_async`.  
- [ ] Use `httpx.AsyncClient` with connection pooling + rate-limit sleep.  
- [ ] Public API: `read_batch(tickers: list[str], **kwargs) -> Graph` that
      merges results for multiple tickers.  
- [ ] Implement simple concurrency (e.g. gather) with max parallel param.  
- [ ] Guard behind extra `aio` optional dependency in `pyproject.toml`.
- [ ] Add integration test hitting FMP mock server.

---
### Owner / Contact
`@io-maintainers` – feel free to extend this backlog. Remember to update the
status boxes as tasks progress. 