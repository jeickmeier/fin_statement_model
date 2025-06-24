# Fin Statement Model
[![CI](https://github.com/jeickmeier/fin_statement_model/actions/workflows/ci.yml/badge.svg)](https://github.com/jeickmeier/fin_statement_model/actions/workflows/ci.yml)

A pre-alpha Python library for building, analysing, and forecasting financial statements using a node-based graph engine.

## Key Features
- **Node-based graph core** – model relationships between financial statement items and compute complex metrics efficiently.
- **Rich metric registry** – 200+ built-in calculations covering profitability, liquidity, leverage, coverage, valuation, and more.
- **Forecasting framework** – project future periods with average growth, historical growth, or custom methods.
- **Scenario adjustments** – layer scenario-specific adjustments on top of base data for powerful what-if analysis.
- **Pre-processing transformers** – clean, normalise, and convert period data before it enters the graph.
- **Flexible data ingestion** – load data from CSV, Excel, pandas `DataFrame`, JSON/dict, or external APIs.
- **Centralised configuration** – override behaviour at runtime via `fin_statement_model.config` without touching code.
- **Type-safe & tested** – fully type-annotated with strict `mypy` settings and ≥ 80 % test coverage enforced in CI.

## Installation
Fin Statement Model targets **Python 3.12+**. Until it is published on PyPI you can install the latest snapshot directly from GitHub:

```bash
# Using pip
pip install "fin_statement_model@git+https://github.com/jeickmeier/fin_statement_model.git"

# Or with uv (recommended)
uv pip install "git+https://github.com/jeickmeier/fin_statement_model.git"
```

Working on the project itself? Clone the repo and install dev dependencies:

```bash
git clone https://github.com/jeickmeier/fin_statement_model.git
cd fin_statement_model
uv pip install -r requirements-dev.txt  # runtime + dev packages

# Or use the bundled nox sessions
uv pip install nox
nox  # runs lint, type-check, and tests
```

## Repository Layout
```text
fin_statement_model/
 │
 ├── config/            # Runtime & environment configuration helpers
 ├── core/              # Core domain logic (graph, calculations, metrics, nodes)
 │   ├── graph/         # Graph data structure and calculation engine
 │   ├── adjustments/   # Scenario adjustments and analytics helpers
 │   ├── calculations/  # Calculation registry & helpers
 │   └── metrics/       # Metric definitions and data models
 ├── forecasting/       # Forecast methods and batch forecaster
 ├── io/                # Data import/export (CSV, Excel, DataFrame, Graph)
 ├── preprocessing/     # ETL-style transformers (normalisation, period conversion …)
 ├── statements/        # Statement templates, orchestration utilities, formatters
 └── utils/             # Small generic utilities
```

Other notable directories:

* `docs/` – Generated API documentation (MkDocs + pdoc)
* `examples/` – Notebooks & scripts demonstrating common workflows
* `tests/` – Pytest suite (≥ 80 % coverage)
* `scripts/` – One-off helper scripts

## Quickstart
```python
from fin_statement_model.io.formats import csv_reader
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.calculations import CalculationRegistry

# Load long-format CSV data
data = csv_reader.read_long("my_financials.csv")

# Build a graph from the records
graph = Graph.from_records(data)

# Register default calculations
CalculationRegistry.register_defaults()

# Calculate trailing 12-month EBITDA margin
ebitda_margin = graph.calculate("EBITDA_MARGIN_TTM")
print(ebitda_margin.series.tail())
```

Explore the [`examples/`](examples/) directory for full scripts and notebooks.

## Contributing
Contributions are welcome! If you plan a large change, open an issue first to discuss your ideas.

1. Run `nox` locally (lint, type-check, tests).
2. Add/adjust unit tests for new behaviour.
3. Keep docstrings and API reference up to date.

## License
Fin Statement Model is released under the MIT License. See the [`LICENSE`](LICENSE) file for details.
