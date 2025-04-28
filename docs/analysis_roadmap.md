Okay, incorporating your feedback and priorities, here's an updated feature list and a proposed implementation roadmap.

**Updated Feature List (Reflecting Priorities):**

**I. Comprehensive Ratio Analysis Engine:**
    1.  **(HIGH Priority)** **Build Out Standard Ratio Library:** Implement a wide range of standard financial ratios (Liquidity, Leverage, Coverage, Profitability, Efficiency, Valuation, Cash Flow) as built-in metrics/calculations. This is the core need identified.
    2.  **(Medium Priority)** Ratio Calculation Nodes: Allow ratios themselves to be nodes in the graph.
    3.  **(Medium Priority)** Custom Ratio Definition: Easy way for users to define their own ratios.
    4.  **(Medium Priority)** Handling of Averaging: Logic for using average balance sheet figures in ratios.

**II. Comparative and Trend Analysis Tools:**
    1.  **(HIGH Priority)** **Common Size Statement Generation:** Add functionality to generate common size statements.
    2.  **(HIGH Priority)** **Peer Group Analysis Module (Foundation):**
        *   Load/manage multiple company graphs.
        *   Calculate ratios across graphs.
        *   Basic comparison/ranking features (needed for Comps analysis in V).
    3.  **(HIGH Priority)** **Generalized Trend Analysis:**
        *   Generalize `YoYGrowthNode` for arbitrary period-over-period changes (e.g., QoQ, MoM).
        *   Implement robust CAGR calculation nodes/functions.

**III. Enhanced Forecasting and Scenario Management:**
    1.  **(HIGH Priority)** **Scenario Manager:** Implement capability for discrete scenarios (Base, Best, Worst) and Monte Carlo analysis (leveraging `StatisticalGrowthForecastNode`).
    2.  **(HIGH Priority)** **Sensitivity Analysis Tools:** Implement systematic ways to test input assumption impacts.
    3.  **(HIGH Priority)** **Integration with Macro Forecasts:** Allow linking internal forecasts to external data inputs.

**IV. Standard Valuation Model Implementations:**
    1.  **(HIGH Priority)** **Dividend Discount Model (DDM):** Implement constant growth and potentially multi-stage DDM nodes/functions.
    2.  **(HIGH Priority)** **Discounted Cash Flow (DCF) Support:** Nodes/functions for FCFF, FCFE, WACC, PV calculations, Terminal Value.
    3.  **(HIGH Priority - Links to II.2)** **Comparable Company Analysis (Comps) Helpers:** Tools to extract and compare multiples using the Peer Group module.

**V. Specific Analysis Modules & Features (High Priority based on "Examples" request):**
    1.  **Du Pont Analysis:** Implement the ROE breakdown.
    2.  **Financial Flexibility Analysis:** Dedicated functions/reports based on CF statement analysis (like Exhibit 4.10).
    3.  **M&A / Restructuring Engine (Basic):** Initial tools for combining graphs and handling basic pro forma adjustments (links to Chapter 10).
    4.  **Debt Schedule / LBO Helpers (Basic):** Basic modeling for debt paydown and LBO cash flow structures (links to Chapter 4).
    5.  **Fraud Detection Models (Optional Extension - Medium Priority):** Implement Beneish M-Score, Altman Z-Score calculations.

**VI. Data Handling and Integration Enhancements:**
    1.  **(HIGH Priority)** **SEC EDGAR Integration:** Tools to parse XBRL data from SEC filings.
    2.  **(In Progress)** Mapping Configuration Helpers: Continue improving source-to-canonical name mapping.
    3.  **(Low Priority)** Database Reader/Writer.
    4.  **(Low Priority)** Expanded API Readers.

**VII. User Experience and Visualization:**
    1.  **(HIGH Priority)** **Finish Standard Formatters:** Complete robust HTML and Markdown formatters.
    2.  **(HIGH Priority)** **Basic Plotting Integration:** Add functions for common charts (trends, ratio comparisons).
    3.  **(HIGH Priority)** **Reporting Engine / Tear Sheets:** Ability to combine tables (formatted statements/ratios) and charts into basic reports or "tear sheets".
    4.  **(Medium Priority)** Enhanced Jupyter Integration.

**Implementation Roadmap:**

This roadmap prioritizes building the core analytical capabilities requested and integrating key data sources first.

**Phase 1: Core Analysis Foundation (Immediate Focus)**

*   **Goal:** Establish the essential ratio calculations, basic comparisons, and output formatting needed for most analyses.
*   **Features:**
    *   **I.1 (Partial):** Implement the most critical ratios (Key Liquidity, Leverage, Coverage, Profitability, basic Turnover). Focus on getting the calculation logic correct within the existing metric/calculation node framework.
    *   **II.1:** Implement Common Size Statement generation (likely as a function operating on a graph or DataFrame).
    *   **II.3 (Partial):** Generalize YoY node for QoQ/MoM. Implement CAGR node/function.
    *   **VII.1:** Finalize and stabilize the HTML and Markdown formatters based on the `StatementStructure`.
    *   **VI.4:** Continue refining mapping configuration helpers (as noted "in progress").

**Phase 2: Expanding Analysis & Basic Valuation (Near-Term)**

*   **Goal:** Add standard valuation models, peer comparison foundations, and more ratios.
*   **Features:**
    *   **I.1 (Continued):** Implement the remaining standard ratios from the library list.
    *   **II.2 (Foundation):** Implement the ability to load and manage multiple graphs. Add basic functions to calculate a specific ratio across all loaded graphs.
    *   **IV.1:** Implement DDM node/function.
    *   **IV.2 (Partial):** Implement FCFF/FCFE calculation nodes (requires careful definition based on graph items). Implement basic PV/discounting nodes.
    *   **V.1:** Implement Du Pont Analysis node/function.
    *   **V.2:** Implement Financial Flexibility report/function generating key metrics.
    *   **VII.2:** Add basic plotting functions (e.g., plot_trend(graph, node_id), plot_ratio_comparison(graphs, ratio_id)).

**Phase 3: Advanced Forecasting, Valuation & Integration (Mid-Term)**

*   **Goal:** Introduce scenario management, sensitivity analysis, DCF completion, and SEC integration.
*   **Features:**
    *   **III.1:** Implement Scenario Manager for discrete scenarios and link to statistical nodes for Monte Carlo.
    *   **III.2:** Implement Sensitivity Analysis tools.
    *   **III.3:** Add framework for linking forecasts to external macro data nodes.
    *   **IV.2 (Completion):** Implement WACC and Terminal Value calculations for full DCF.
    *   **IV.3:** Build Comps analysis tools leveraging the Peer Group module from Phase 2.
    *   **VI.1:** Implement SEC EDGAR XBRL reader (this is complex and may span phases).
    *   **VII.3:** Develop basic Reporting Engine/Tear Sheet generation combining tables and charts.

**Phase 4: Specialized Modules & Refinements (Longer-Term)**

*   **Goal:** Add more specialized analysis modules, refine existing features, and improve data IO.
*   **Features:**
    *   **V.3:** Basic M&A pro forma combination tools.
    *   **V.4:** Basic LBO/Debt Schedule modeling helpers.
    *   **V.5:** Implement Fraud Detection models (Beneish, Altman).
    *   **I.2, I.3, I.4:** Add Ratio Nodes, Custom Ratio definitions, Average Balance Sheet handling.
    *   **II.2 (Advanced):** Add advanced peer analysis features (median/quartile calculation, ranking).
    *   **VI.3, VI.4:** Lower priority Database IO and other API readers.
    *   **VII.4:** Enhanced Jupyter integration.
    *   Ongoing documentation, examples, testing, and performance optimization across all phases.

**Key Considerations:**

*   **Dependencies:** Many features depend on the Ratio Library (I.1) and the core Graph/Node structure. Valuation (IV) depends heavily on Forecasting (III) and Ratios (I). Peer Analysis (II.2) is needed for Comps (IV.3).
*   **Complexity:** SEC EDGAR integration (VI.1) is technically challenging. Scenario Management (III.1) and M&A/LBO helpers (V.3, V.4) can also become quite complex.
*   **User Feedback:** This roadmap should be flexible and adapt based on user feedback and evolving needs as the library grows.
*   **Documentation & Examples:** Crucial throughout. The request for "examples" for features in IV/V means implementing the *functionality* and then providing clear documentation and usage examples.

This roadmap provides a structured approach to building out the library's capabilities to match the breadth of analysis described in the PDF, prioritizing the most fundamental and requested features first.



Okay, let's break down the features from the prioritized roadmap into more detailed implementation steps and considerations.

**Roadmap Phase 1: Core Analysis Foundation**

1.  **I.1 (Partial): Build Out Standard Ratio Library (Critical Ratios)**
    *   **Goal:** Implement essential liquidity, leverage, coverage, and profitability ratios.
    *   **Implementation:** Define YAML files in `fin_statement_model/core/metrics/builtin/` for each ratio.
        *   **Liquidity:**
            *   `current_ratio.yaml`: Formula: `current_assets / current_liabilities`. Inputs: `current_assets`, `current_liabilities`.
            *   `quick_ratio.yaml`: Formula: `(cash_and_equivalents + short_term_investments + accounts_receivable) / current_liabilities`. Inputs: `cash_and_equivalents`, `short_term_investments`, `accounts_receivable`, `current_liabilities`. (Requires these base nodes).
        *   **Leverage:**
            *   `debt_to_equity.yaml`: Formula: `total_debt / total_equity`. Inputs: `total_debt`, `total_equity`. (Need `total_debt` node).
            *   `debt_to_capital.yaml`: Formula: `total_debt / (total_debt + total_equity)`. Inputs: `total_debt`, `total_equity`.
        *   **Coverage:**
            *   `times_interest_earned.yaml`: Formula: `ebit / interest_expense`. Inputs: `ebit`, `interest_expense`. (Need `ebit` node).
            *   `ebitda_coverage.yaml`: Formula: `ebitda / interest_expense`. Inputs: `ebitda`, `interest_expense`. (Need `ebitda` node).
        *   **Profitability:**
            *   `gross_margin.yaml`: Formula: `gross_profit / revenue`. Inputs: `gross_profit`, `revenue`. (Need `gross_profit` node).
            *   `operating_margin.yaml`: Formula: `operating_income / revenue`. Inputs: `operating_income`, `revenue`.
            *   `net_margin.yaml`: Formula: `net_income / revenue`. Inputs: `net_income`, `revenue`.
        *   **Return:**
            *   `return_on_equity.yaml` (Basic): Formula: `net_income / total_equity`. Inputs: `net_income`, `total_equity`. (Address averaging later).
            *   `return_on_assets.yaml` (Basic): Formula: `net_income / total_assets`. Inputs: `net_income`, `total_assets`. (Address averaging later).
    *   **Testing:** Ensure formulas are correct, inputs are standard, and edge cases (zero denominators) are handled gracefully (likely return NaN or Inf in `FormulaCalculationNode`).

2.  **II.1: Common Size Statement Generation**
    *   **Goal:** Create functions to convert statement DataFrames to common size.
    *   **Implementation:**
        *   Create a utility function `create_common_size_df(df, base_item_id)`.
        *   Input: DataFrame generated by `StatementFormatter`, `base_item_id` (e.g., 'revenue', 'total_assets').
        *   Logic: Locate the row for `base_item_id`. Divide all numeric period columns by the values in the base item row. Handle potential zero base values (result in NaN/Inf). Multiply by 100 for percentage.
        *   Integrate: Potentially add an option to `StatementFormatter.generate_dataframe` or `create_statement_dataframe` to return common size directly.
    *   **Testing:** Test with IS (% Revenue) and BS (% Assets). Verify correct percentages and handling of zero base values.

3.  **II.3 (Partial): Generalized Trend Analysis**
    *   **Goal:** Enhance period-over-period calculations and add CAGR.
    *   **Implementation:**
        *   Modify `YoYGrowthNode`: Add `periods_back: int = 1` parameter to `__init__`. Update `calculate` to fetch value from `periods_back` ago instead of fixed `prior_period`. Rename class to `PeriodOverPeriodGrowthNode`? Or keep `YoYGrowthNode` and add `QoQGrowthNode` etc. inheriting/using similar logic? *Decision:* Modify `YoYGrowthNode` with `periods_back` for flexibility.
        *   Create `CAGRNode(Node)`:
            *   `__init__(self, name, input_node, start_period, end_period)`
            *   `calculate()`: Fetches `start_value`, `end_value`. Calculates `num_years` based on period strings (requires robust period parsing or assumption about format). Formula: `(end_value / start_value) ** (1 / num_years) - 1`. Handle zero/negative start values.
    *   **Testing:** Test `PeriodOverPeriodGrowthNode` with `periods_back=1` (YoY), `periods_back=4` (QoQ for quarterly). Test `CAGRNode` with various start/end periods.

4.  **VII.1: Finish Standard Formatters (HTML/Markdown)**
    *   **Goal:** Ensure robust and configurable HTML and Markdown output.
    *   **Implementation:**
        *   Refine `MarkdownWriter._get_statement_items` and `_StructureProcessor` to correctly handle all item types (LineItem, Calculated, Subtotal, Metric, Section) and indentation.
        *   Create `HTMLWriter` class, potentially reusing `_StructureProcessor` but outputting HTML table tags (`<table>`, `<tr>`, `<td>`, `<th>`) instead of Markdown syntax.
        *   Add configuration options (passed via `writer_kwargs`) for number formatting (precision, commas), sign convention application, indentation style, and potentially basic CSS classes for HTML.
        *   Ensure subtotals are calculated correctly *before* formatting.
    *   **Testing:** Test with complex statement structures (nested sections, various item types). Verify formatting options work as expected. Check output validity (valid Markdown, valid HTML).

5.  **VI.4: Mapping Configuration Helpers**
    *   **Goal:** Improve usability of mapping source names to canonical names.
    *   **Implementation:**
        *   Enhance `normalize_mapping` if needed (current version seems okay).
        *   *Potential:* Create a utility function `suggest_mappings(source_columns, known_canonical_names)` using fuzzy matching (e.g., `fuzzywuzzy` library - adds dependency) or simple heuristics (lowercase, remove spaces/punctuation).
        *   *Potential:* Add validation within readers to check if required canonical nodes (based on statement config) can be produced from the source data using the provided mapping.
    *   **Testing:** Test mapping normalization with various config structures. Test suggestion utility if implemented.

**Roadmap Phase 2: Expanding Analysis & Basic Valuation**

1.  **I.1 (Continued): Implement Remaining Ratios**
    *   **Goal:** Add efficiency, remaining return, basic cash flow, and basic valuation ratios.
    *   **Implementation:** More YAML metric definitions.
        *   **Efficiency:** `asset_turnover`, `receivables_turnover`, `days_sales_outstanding`, `inventory_turnover`, `days_inventory_held`, `payables_turnover`, `days_payables_outstanding`. (Requires careful handling of average balances - see I.4).
        *   **Return:** `return_on_capital` (Needs clear definition of Capital - e.g., Debt + Equity).
        *   **Cash Flow:** `cf_ops_to_debt`, `free_cash_flow` (Define FCF clearly, e.g., CFO - Capex), `fcf_to_debt`. (Requires `cf_ops`, `capex` nodes).
        *   **Valuation:** `price_to_book` (Requires `market_cap`, `book_value_equity`), `dividend_yield` (Requires `dividends_per_share`, `market_price`). (Requires nodes for market data).
    *   **Testing:** Verify formulas, input requirements, edge cases.

2.  **II.2 (Peer Group - Foundation):**
    *   **Goal:** Basic infrastructure for comparing multiple companies.
    *   **Implementation:**
        *   `PeerGroup` class: `__init__(self, graphs: dict[str, Graph])`. Stores graphs keyed by ticker/ID.
        *   Method `calculate_metric(self, metric_id: str) -> pd.DataFrame`: Iterates graphs, calls `graph.calculate(metric_id, period)` for all periods, returns a DataFrame (index=ticker, columns=periods). Handles missing nodes/errors gracefully (e.g., fill with NaN).
        *   Method `get_node_dataframe(self, node_id: str) -> pd.DataFrame`: Similar to above but fetches data for a specific node across all graphs/periods.
    *   **Testing:** Test with 2-3 sample graphs. Verify DataFrame output structure and error handling.

3.  **IV.1 (DDM):**
    *   **Goal:** Implement Dividend Discount Model valuation.
    *   **Implementation:**
        *   Create `DDMNode(Node)`:
            *   `__init__(self, name, dividend_node, k_node, g_node)` where inputs are other `Node` instances.
            *   `calculate(period)`: Fetches D0 = `dividend_node.calculate(period)`, k = `k_node.calculate(period)`, g = `g_node.calculate(period)`. Calculates P = (D0 * (1+g)) / (k-g). Handle k<=g error.
        *   *Alternative:* Function `calculate_ddm(graph, div_id, k_id, g_id, period)`.
    *   **Testing:** Test with various inputs, including k<=g case.

4.  **IV.2 (DCF - Partial):**
    *   **Goal:** Calculate FCFF/FCFE and basic Present Value.
    *   **Implementation:**
        *   Define metrics `fcff.yaml` and `fcfe.yaml`. Formulas require EBIT, Tax Rate, Depreciation, Capex, Change in Working Capital. Ensure these base nodes exist or can be calculated.
        *   Create `PresentValueNode(Node)`:
            *   `__init__(self, name, cash_flow_node, discount_rate_node)`
            *   `calculate(period)`: This is tricky. A single PV node usually calculates the PV of a *stream*. Maybe better as a function `calculate_npv(graph, cf_node_id, rate_node_id, periods_list)`.
    *   **Testing:** Verify FCFF/FCFE formulas. Test NPV function with sample cash flows.

5.  **V.1 (Du Pont):**
    *   **Goal:** Break down ROE.
    *   **Implementation:**
        *   Function `calculate_dupont(graph, period) -> dict`: Calculates Net Margin (`net_income`/`revenue`), Asset Turnover (`revenue`/`average_total_assets`), Financial Leverage (`average_total_assets`/`average_total_equity`), and ROE. Returns a dictionary.
        *   Requires nodes for `net_income`, `revenue`, `total_assets`, `total_equity`. Needs logic to calculate *average* assets/equity (see I.4).
    *   **Testing:** Verify component calculations and the final ROE identity.

6.  **V.2 (Fin Flexibility):**
    *   **Goal:** Report key flexibility metrics.
    *   **Implementation:**
        *   Function `generate_flexibility_report(graph, periods) -> pd.DataFrame`: Calculates metrics like CFO, Capex, Dividends, FCF, CFO/Capex, Dividend Coverage (FCF/Dividends or CFO/Dividends) for the specified periods.
        *   Requires nodes for `cf_ops`, `capex`, `dividends`.
    *   **Testing:** Verify calculations and output format.

7.  **VII.2 (Plotting - Basic):**
    *   **Goal:** Simple visualization functions.
    *   **Implementation:**
        *   Use Matplotlib/Seaborn.
        *   `plot_trend(graph, node_id, periods)`: Fetches data, plots line chart.
        *   `plot_peer_comparison(peer_group, metric_id, period)`: Fetches data via `peer_group.calculate_metric`, creates bar chart or box plot.
    *   **Testing:** Test with sample data, ensure basic plots are generated correctly.

**Roadmap Phase 3: Advanced Forecasting, Valuation & Integration**

1.  **III.1 (Scenario Mgr):**
    *   **Goal:** Manage discrete scenarios and enable Monte Carlo.
    *   **Implementation:**
        *   `ScenarioManager` class: Stores scenarios as dicts: `{'ScenarioName': {'node_id': {'period': value_override or forecast_config_override}}}`.
        *   Method `run_scenario(graph, scenario_name)`: Creates a *copy* of the graph, applies overrides, recalculates, returns the modified graph or key results.
        *   Monte Carlo: Loop `n` times, in each loop apply overrides based on `StatisticalGrowthForecastNode` (or similar probabilistic inputs), run scenario, store results, aggregate statistics.
    *   **Testing:** Test applying overrides, verify scenario results differ. Test basic Monte Carlo loop.

2.  **III.2 (Sensitivity):**
    *   **Goal:** Systematically test input impacts.
    *   **Implementation:**
        *   Function `run_sensitivity(graph, input_node_id, output_node_ids, period, input_range)`: Loops through `input_range`, uses `graph.set_value` (on a copy of the graph!) for the input node/period, recalculates, stores output node values. Returns results (e.g., DataFrame).
    *   **Testing:** Test with simple graph, verify output changes correctly based on input variation.

3.  **III.3 (Macro Links):**
    *   **Goal:** Link forecasts to external economic variables.
    *   **Implementation:**
        *   Allow `CustomGrowthForecastNode`'s function to accept the `graph` object itself, allowing it to query other nodes (e.g., `graph.calculate('gdp_growth', period)`).
        *   Alternatively, modify `CalculationNode` or create a new node type that explicitly takes other nodes as parameters for its calculation logic (beyond just direct value inputs).
    *   **Testing:** Create a simple model where one forecast depends on another node representing a macro variable.

4.  **IV.2 (DCF - Completion):**
    *   **Goal:** Add WACC and Terminal Value for full DCF.
    *   **Implementation:**
        *   `WACCNode(Node)`: Takes nodes for Cost of Equity (could be complex itself, maybe start with constant), Cost of Debt, Tax Rate, Market Value of Equity, Market Value of Debt as inputs. Calculates WACC.
        *   `TerminalValueNode(Node)`: Takes final projected CF node, long-term growth rate node (g), WACC node. Calculates TV = CF * (1+g) / (WACC-g). Add Exit Multiple method option.
        *   Update `calculate_npv` function or create `DCFValuationNode` to incorporate TV.
    *   **Testing:** Verify WACC and TV formulas. Test full DCF calculation.

5.  **IV.3 (Comps):**
    *   **Goal:** Facilitate comparable company analysis.
    *   **Implementation:**
        *   Add `calculate_ev(graph, period)` function (Market Cap + Total Debt - Cash). Requires `market_cap`, `total_debt`, `cash_and_equivalents` nodes.
        *   Enhance `PeerGroup` with `get_multiples_dataframe(multiples_list, period)`: Calculates requested multiples (e.g., P/E, EV/EBITDA) for all companies for a given period.
    *   **Testing:** Verify EV calculation. Test multiple extraction across peer group.

6.  **VI.1 (EDGAR):**
    *   **Goal:** Read data directly from SEC XBRL filings.
    *   **Implementation:**
        *   Choose an XBRL parsing library.
        *   Create `EdgarReader(DataReader)`: Takes ticker/CIK, filing type (10-K, 10-Q), period. Fetches filing, parses XBRL.
        *   Develop a robust mapping from common US-GAAP XBRL tags to the library's canonical node names. This is the hardest part.
    *   **Testing:** Test with various companies and filing types. Validate extracted data against reported financials. This is a significant undertaking.

7.  **VII.3 (Reporting/Tear Sheets):**
    *   **Goal:** Generate combined text, table, chart reports.
    *   **Implementation:**
        *   Define a simple report structure (e.g., list of components: text block, table (DataFrame), chart (plot function reference)).
        *   Create `ReportGenerator` class: Takes the structure, data (graph, peer group), and generates output (start with HTML or Markdown). Use `StatementFormatter` for tables, plotting functions for charts.
    *   **Testing:** Generate sample reports with different components.

**Roadmap Phase 4: Specialized Modules & Refinements**

*   **V.3 (M&A - Basic):** Implement `merge_graphs_proforma` function focusing on adding balance sheets, income statements, basic goodwill, and debt adjustments. Defer complex fair value/intangible logic initially.
*   **V.4 (LBO - Basic):** Create functions to model a simple debt waterfall: `calculate_debt_schedule(graph, initial_debt, interest_rate_node, cfo_node, mandatory_repay_node, sweep_percent_node, periods)`.
*   **V.5 (Fraud Models):** Implement `calculate_beneish_m_score(graph, period)` and `calculate_altman_z_score(graph, period)` functions, requiring specific ratio inputs calculated beforehand.
*   **I.2, I.3, I.4 (Ratio Enhancements):** Refactor key ratios into `CalculationNode` subclasses if performance/complexity warrants. Add `CustomRatioNode`. Modify base ratio calculations/metrics to accept an `averaging_method` parameter ('end_of_period', 'simple_average').
*   **II.2 (Peer Group - Advanced):** Add `get_peer_stats` (calculating mean, median, quartiles for a metric across the group) and `rank_companies` methods to `PeerGroup`.
*   **VI.3, VI.4 (IO):** Implement `SqlReader`/`Writer` using SQLAlchemy. Add wrappers for other desired APIs (e.g., AlphaVantage, Polygon).
*   **VII.4 (Jupyter):** Implement `_repr_html_` for `Graph` (showing summary stats), `StatementStructure` (showing outline), and potentially DataFrames generated by the library.

This detailed plan provides concrete steps for each feature, clarifies implementation choices, and highlights dependencies, forming a solid basis for development.