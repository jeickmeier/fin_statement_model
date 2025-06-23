# Quick Start

```python
from fin_statement_model import Statement, parse_fin_statement

stmt = parse_fin_statement("...some input…")
print(stmt.total_assets)
