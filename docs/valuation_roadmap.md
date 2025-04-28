Below is a roadmap of the **highest-impact additions** you could make to `fin_statement_model` so that it can reproduce the full valuation workflow laid-out in *Valuation: Measuring and Managing the Value of Companies* (6e, McKinsey).  I group the recommendations by feature area, cite the relevant book sections, and show where they would fit in the current codebase.

---

### 1. Economic-statement builder (Invested Capital / NOPLAT)
* **What to add**
  * `EconomicStatementBuilder` service that ingests GAAP/IFRS raw statements, classifies lines as *operating* vs *non-operating*, and produces:
    * Economic balance sheet (Invested Capital = OA – OL)  
    * Economic income statement (NOPLAT, operating taxes)
* **Why**
  * Chapters 9 & Appendix B insist every valuation start from Invested Capital and NOPLAT (see Exhibits 9.1 – 9.3) .
* **Where in code**
  * New sub-package `fin_statement_model/economic/…`
  * Provide node factories (`InvestedCapitalNode`, `NOPLATNode`) so they slot straight into the existing `Graph` .

---

### 2. Free-Cash-Flow engine
* **What to add**
  * `FreeCashFlowNode` that derives FCF from NOPLAT and net investment buckets (working capital, cap-ex, leases, goodwill, other LT items) exactly as Exhibit 9.14 specifies .
* **Why**
  * FCF is the starting point for enterprise DCF, APV, CCF and economic-profit models (Ch. 8).

---

### 3. Cost-of-Capital & Capital-Structure module
* **What to add**
  * `CostOfCapitalCalculator`:
    * Bottom-up β (lever/unlever), country risk premium, synthetic rating curve for kd.
    * Handles target vs current weights (Ch. 13) .
  * `CapitalStructureScenario` object to test alternative leverage / credit-spread cases.
* **Why**
  * WACC is used in DCF, while ku is required in APV and CCF.

---

### 4. Valuation engines
| Engine | Chapter | Key tasks |
|--------|---------|-----------|
| `EnterpriseDCFModel` | 8 | discount FCF at WACC; choose CV method (key-driver, convergence, exit multiple)  |
| `EconomicProfitModel` | 8, App. A/B | value = Invested Capital + PV(EconomicProfit)  |
| `APVModel` | 8 | value = unlevered PV + PV(ITS)  |
| `CapitalCashFlowModel` | 8 | discount FCF+ITS at ku  |
| `EquityDCFModel` | 8 | discount CFE at ke; reconcile to enterprise value |

All inherit from a common `BaseValuationModel` that plugs into your `Graph` and re-uses the FCF & WACC nodes.

---

### 5. Continuing-Value toolbox
* **Functions** for: key-driver formula, aggressive-growth, convergence, economic-profit CV, market multiple cross-check (Ch. 12) .
* Integrate with engines so CV method is a strategy pattern.

---

### 6. Scenario & Sensitivity framework
* **ScenarioManager**: stores multiple sets of driver assumptions (ROIC, growth, WACC, tax, FX).
* **Tornado / spider plot generator**: one-line call to show ΔValue vs ± variations in any node (Ch. 15).
* **Monte-Carlo plug-in** for stochastic DCF if desired.

---

### 7. Value-driver analytics
* `ROICDecompositionNode` (NOPLAT margin × capital turnover) and `ValueDriverTree` that links ROIC & growth to value (Chapter 2’s key formula) .
* `TRSDecomposer` to reconcile market TSR into dividend yield, growth and re-rating.

---

### 8. Multiples & Peer benchmarking
* `PeerSet` abstraction with EV/EBITDA, EV/NOPLAT, P/E, and custom operating multiples (Ch. 16) .
* Auto-adjust peers for leases, minorities, pension deficits.

---

### 9. Real-option / Flexibility valuation
* `RealOptionModel` using binomial or decision-tree wrappers around the base DCF (Ch. 35) .

---

### 10. Tax, leases, pensions and other advanced adjustments
* Parsers for lease liabilities (ASC 842 / IFRS 16), retirement obligations, deferred-tax splitting (operating vs non-operating) as outlined in Chapters 18-20 .
* Provide helper nodes so forecasts converge automatically to the reorganised statements.

---

### 11. Data & Reporting extensions
* **Market-data adaptors** (e.g., SQLAlchemy / yfinance / Bloomberg BQuant) feeding β, spreads, and peer multiples.
* **LLM-aided narrative**: reuse your existing `LLMClient` to auto-draft valuation memos and risk summaries.
* **ReportBuilder**: export full valuation deck to Markdown / PDF.

---

## How to phase the work

1. **Foundations** – Economic-statement builder, FCF node, WACC calculator (enables DCF end-to-end).
2. **Valuation engines & CV toolbox** – start with Enterprise DCF + Economic-Profit.
3. **Scenario / sensitivity layer** – drives insight, low coupling.
4. **Advanced topics** – APV, CCF, real options, lease- & pension-adjustments.
5. **UX polish** – peer benchmarking, reporting, LLM narratives.

Each step can be delivered as an optional extension package (your design already allows lazy-loading extras) so core graph remains lean.

Implementing these modules will let your library cover **all** of the analytical steps the book walks through—from reorganising financials to estimating value per share—while re-using the elegant node/graph architecture you already have.