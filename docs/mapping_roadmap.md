Yes, integrating LLM calls into this mapping functionality offers **significant potential benefits for semi-automatically setting up new mappings**, but it comes with important caveats, primarily the need for **human review and confirmation**.

Here's a breakdown of the benefits and how you might integrate it:

**Potential Benefits:**

1.  **Accelerated Setup:** For a new data source (Excel file, API response), manually mapping dozens or hundreds of unique item names to your canonical set can be tedious and time-consuming. An LLM can analyze the source names and suggest mappings much faster.
2.  **Handling Variations:** LLMs have been trained on vast amounts of text, including financial documents. They can often recognize less common variations or slightly different phrasings (e.g., "Earnings Before Interest and Tax" vs. "EBIT" vs. "Operating Income/(Loss)") and map them correctly to your canonical `operating_income`.
3.  **Discovering Unmapped Items:** The LLM can quickly identify source items that don't seem to fit any of your existing canonical names, highlighting areas needing manual attention or potential additions to your canonical list.
4.  **User Experience:** Offering a "Suggest Mappings" feature can significantly improve the user experience when onboarding a new data source.

**How to Integrate (Focusing on Suggestion):**

The most practical integration point is as an **optional helper tool** during the configuration phase, rather than a fully automated step within `read_data`.

1.  **Triggering Mechanism:**
    *   A CLI command: `fin-model suggest-mapping --source-file data.xlsx --sheet "Income" --output-mapping suggested_mappings.yaml`
    *   A dedicated function: `fin_statement_model.io.mapping.suggest_mappings_for_source(source, source_type, existing_canonical_names)`
    *   Potentially an interactive mode within a setup script.

2.  **Workflow:**
    *   **Extract Source Names:** The tool reads the source (e.g., column headers from Excel/CSV, keys from FMP API response for a sample period) to get a list of unique source item names.
    *   **Get Canonical Names:** Retrieve the list of predefined canonical names your library uses (e.g., `revenue`, `cogs`, etc.). You might store these in a central place or derive them from your default mapping config.
    *   **Prepare LLM Prompt:** Construct a prompt for the LLM. This is crucial:
        *   **Task:** Clearly state the goal: "Map the following source financial statement item names to the most appropriate canonical name from the provided list. Use financial accounting knowledge."
        *   **Input:** Provide the list of extracted `source_names`.
        *   **Target:** Provide the list of `canonical_names`. Optionally include brief descriptions for clarity (e.g., "cogs: Cost of Goods Sold or Cost of Revenue").
        *   **Output Format:** Explicitly request the output in a structured format, like JSON: `{"Source Name 1": "canonical_name_a", "Source Name 2": "canonical_name_b", "Unmappable Source Name": null}`. Instruct it to use `null` or a specific token (like `__UNMAPPED__`) for items it cannot confidently map.
        *   **Context (Optional):** You could provide context like the statement type (Income, Balance Sheet, Cash Flow) if known, which might help the LLM.
        *   **Few-Shot Examples (Optional):** Include 1-3 examples of correct mappings in the prompt.
    *   **Call LLM:** Use your `LLMClient` to send the prompt and receive the structured response (e.g., JSON).
    *   **Parse Response:** Parse the LLM's JSON output.
    *   **Present for Review:** Display the suggested mappings to the user in a clear format (e.g., a table showing Source | Suggested Canonical | Action). Highlight items the LLM couldn't map.
    *   **User Confirmation/Editing:** Allow the user to:
        *   Confirm correct suggestions.
        *   Correct wrong suggestions (selecting from the canonical list).
        *   Manually map items the LLM missed.
        *   Mark source items to be ignored.
    *   **Save Mapping:** Save the user-confirmed/edited mappings into the appropriate format (e.g., append/update a user's `mapping_config.yaml` file under the relevant context key).

**Implementation Considerations:**

*   **LLM Client:** You already have `LLMClient` and `LLMConfig`. This can be reused.
*   **Human-in-the-Loop is Essential:** **Do not** fully automate this. LLMs can make mistakes, especially with ambiguous terms or company-specific jargon. The output *must* be reviewed and confirmed by a human user who understands the data source and the target canonical model.
*   **Cost and Latency:** LLM calls have associated costs and latency. This makes it more suitable for an offline configuration step than a real-time part of data loading.
*   **Error Handling:** Handle potential LLM API errors, timeouts, and malformed responses gracefully.
*   **Prompt Engineering:** Iteratively refine the prompt to get the most accurate and consistently formatted results.
*   **Security/Privacy:** Be mindful that source item names are being sent to a third-party API. While generally not highly sensitive, it's a consideration.

**Alternative (Non-LLM):**

*   **Fuzzy Matching:** Use libraries like `fuzzywuzzy` or `thefuzz` to suggest mappings based on string similarity. This is much faster and cheaper but less semantically aware than an LLM. It might map "Gross Profit" to "Gross Profit Margin" based purely on text overlap, which an LLM is less likely to do.

**Conclusion:**

Yes, there's a clear benefit in using LLMs to **semi-automate** the creation of mappings. It acts as a powerful suggestion engine, drastically reducing manual effort for the initial setup. However, due to the critical need for accuracy in financial modeling, the LLM's output **must** be treated as suggestions requiring human validation and confirmation before being used in the actual data loading process. Implementing this as an optional, interactive configuration helper tool is the most practical approach.


Okay, this is a very common and important requirement for building a robust financial modeling library. Handling variations in item names is crucial for usability and reducing configuration duplication.

Here's a breakdown of how you can implement a flexible mapping system within your `fin_statement_model` library, integrating it primarily at the data reading stage:

**1. Define the Mapping Configuration Structure**

The core idea is to have a configuration that defines how source names map to your internal canonical names. A nested dictionary structure stored in YAML or JSON is ideal, allowing for both default mappings and context-specific overrides.

*   **Canonical Names:** Define a consistent set of internal names for all core financial items (e.g., `revenue`, `cogs`, `gross_profit`, `cash`, `accounts_receivable`, `total_assets`). These are the names your metrics, statement definitions (YAMLs), and internal calculations will rely on.
*   **Mapping Structure:** Use a dictionary where keys represent the *context* and values are dictionaries mapping *source names* to *canonical names*.
    *   A special key (e.g., `None` or `"default"`) can hold mappings that apply universally unless overridden by a specific context.
    *   Context keys could be:
        *   Data source type (e.g., `"fmp"`, `"excel"`, `"csv"`)
        *   Specific sheet names (e.g., `"Sheet1"`, `"Income Statement"`)
        *   Statement types (e.g., `"income_statement"`, `"balance_sheet"`) - useful if the same source provides multiple statements.
        *   Potentially even company tickers or custom identifiers.

**Example `mapping_config.yaml`:**

```yaml
# Default mappings (apply everywhere unless overridden)
# Use null or a specific key like "__default__"
null:
  Revenue: revenue
  REV: revenue
  Total Revenue: revenue
  Sales: revenue
  Cost of Goods Sold: cogs
  COGS: cogs
  Cost Of Revenue: cogs
  Gross Profit: gross_profit
  GP: gross_profit
  SGA: sg_and_a
  SG&A: sg_and_a
  Selling, General & Administrative: sg_and_a
  Operating Income: operating_income
  EBIT: operating_income # Example: Map EBIT to operating_income internally
  Net Income: net_income
  # ... more common defaults

# Context-specific mappings (e.g., for FMP API)
fmp:
  revenue: revenue # FMP might already use lowercase
  costOfRevenue: cogs
  grossProfit: gross_profit
  sellingGeneralAndAdministrativeExpenses: sg_and_a
  operatingIncome: operating_income
  netIncome: net_income
  # ... FMP specific fields

# Context for a specific Excel sheet
"Income Statement Sheet":
  "Turnover": revenue
  "Cost of Sales": cogs
  "Gross Margin": gross_profit # Different name for GP

# Context for another source type
"internal_db":
  "SALES_REV": revenue
  "COST_GOODS": cogs
```

**2. Create a Mapping Utility Function**

A helper function is needed to process this configuration structure and return a *flat* mapping dictionary relevant for a specific context.

```python
# fin_statement_model/io/readers/base.py (or a dedicated mapping_utils.py)
from typing import Optional, Union, Dict, Any

# Define the type alias for clarity
MappingConfig = Union[
    Dict[str, str], # Simple flat mapping (optional support)
    Dict[Optional[str], Dict[str, str]] # Nested mapping with None/default key
]

def normalize_mapping(
    mapping_config: MappingConfig = None,
    context_key: Optional[str] = None
) -> Dict[str, str]:
    """Turn a potentially scoped MappingConfig into a unified flat dict.

    Applies default mappings (key=None) and overlays context-specific mappings.

    Args:
        mapping_config: The mapping configuration object.
        context_key: Optional key (e.g., sheet name, statement type, source type)
                     to select a specific mapping scope to overlay on defaults.

    Returns:
        A flat dictionary mapping source names to canonical names for the given context.

    Raises:
        TypeError: If the provided mapping_config is not of a supported structure
                   or doesn't contain the required default mapping (under None key
                   if using the nested structure).
    """
    if mapping_config is None:
        return {}

    if not isinstance(mapping_config, dict):
        raise TypeError(
            f"mapping_config must be a dict, got {type(mapping_config).__name__}"
        )

    # Check if it's the nested structure (presence of None key is a good indicator)
    # We'll mandate the None key for the nested structure to define defaults.
    if None not in mapping_config:
         # Could potentially support flat dict as input here, treating it as the default
         # if isinstance(next(iter(mapping_config.values()), None), str):
         #     # Assume it's a flat dict, treat as default
         #     return mapping_config.copy()
         # else:
             raise TypeError(
                 "Nested mapping_config must include a default mapping under the None key."
             )

    # Start with the default mapping
    default_map = mapping_config.get(None, {})
    if not isinstance(default_map, dict):
        raise TypeError(
            "Default mapping (under None key) must be a dict[str, str]."
        )

    # Create the result, starting with a copy of the defaults
    result: Dict[str, str] = default_map.copy()

    # If a context key is provided, overlay the specific mapping
    if context_key and context_key in mapping_config:
        scoped_map = mapping_config[context_key]
        if not isinstance(scoped_map, dict):
            raise TypeError(
                f"Scoped mapping for key '{context_key}' must be a dict[str, str]."
            )
        # Update the result, overriding defaults where keys clash
        result.update(scoped_map)

    return result

```

**3. Integrate Mapping into IO Readers**

The best place to apply this mapping is within your `DataReader` implementations (`ExcelReader`, `FmpReader`, `CsvReader`, etc.).

*   **Configuration:** Add `mapping_config: Optional[MappingConfig]` to the Pydantic `ReaderConfig` models (e.g., `ExcelReaderConfig`, `FmpReaderConfig`).
*   **Initialization:** The reader's `__init__` method will receive the validated config object (`cfg`) containing the `mapping_config`.
*   **`read()` Method:**
    1.  Inside the `read` method, determine the relevant `context_key` for the current operation (e.g., `sheet_name` for Excel, `statement_type` for FMP, maybe `None` for CSV unless specified otherwise).
    2.  Call `normalize_mapping(self.cfg.mapping_config, context_key=context)` to get the effective flat mapping dictionary for this specific read operation.
    3.  When processing the source data (iterating rows in Excel/CSV, processing API response fields):
        *   Get the `source_name` (e.g., column header, API field name).
        *   Look up the canonical name: `canonical_name = mapping.get(source_name, source_name)` (fallback to the original name if no mapping exists).
        *   Use this `canonical_name` when creating `FinancialStatementItemNode` instances or adding data to the `Graph`.

**Example Integration in `ExcelReader.read`:**

```python
# fin_statement_model/io/readers/excel.py

# ... (imports) ...
from .base import normalize_mapping # Import the utility

# ... (ExcelReader class definition) ...

    def __init__(self, cfg: ExcelReaderConfig) -> None:
        self.cfg = cfg

    # ... (_get_mapping removed, use normalize_mapping directly) ...

    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        assert self.cfg is not None, "ExcelReader must be initialized with a valid configuration."
        file_path = source
        logger.info(f"Starting import from Excel file: {file_path}")

        # --- Configuration & Context ---
        sheet_name = self.cfg.sheet_name # Get sheet_name from config
        # Determine context key (could be sheet_name or statement_type if provided)
        context_key = kwargs.get("statement_type", sheet_name) # Prioritize statement_type if given

        # --- Get Effective Mapping ---
        try:
            # Use the mapping config stored in the validated Pydantic config
            mapping = normalize_mapping(self.cfg.mapping_config, context_key=context_key)
            logger.debug(f"Using effective mapping for context '{context_key}': {mapping}")
        except TypeError as te:
            raise ReadError(
                "Invalid mapping_config structure provided.",
                source=file_path,
                reader_type="ExcelReader",
                original_error=te,
            )

        # ... (rest of the reading logic: pandas read, identify periods/items) ...

        # --- Populate Graph (Inside the loop processing rows) ---
        for index, row in df.iterrows():
            item_name_excel = row.iloc[items_col_0idx] # Get raw name from Excel
            if pd.isna(item_name_excel) or not item_name_excel:
                continue

            item_name_excel_str = str(item_name_excel).strip()

            # <<< APPLY MAPPING HERE >>>
            node_name = mapping.get(item_name_excel_str, item_name_excel_str)
            # <<< Use 'node_name' (canonical) from now on >>>

            period_values: dict[str, float] = {}
            # ... (loop through periods, get values) ...

            if period_values:
                if graph.has_node(node_name): # Check using canonical name
                    logger.warning(
                        f"Node '{node_name}' (from Excel item '{item_name_excel_str}') already exists. Overwriting data is not standard for readers."
                    )
                    # Handle update/overwrite policy if needed
                else:
                    # Create node using the canonical name
                    new_node = FinancialStatementItemNode(name=node_name, values=period_values)
                    graph.add_node(new_node)
                    nodes_added += 1
            # ... (rest of the loop) ...

        # ... (error handling and return graph) ...

```

**4. Loading Default Mappings (Optional but Recommended)**

You can ship default mappings with your library.

*   Create YAML files (like the example above) in a dedicated config directory within your package (e.g., `fin_statement_model/io/readers/config/`).
*   Use `importlib.resources` within the relevant reader classes (like `FmpReader`) to load these default YAMLs.
*   Modify the logic that gets the mapping: Load the defaults first, then load the user-provided `mapping_config` from `self.cfg`, and merge them (user config overrides defaults) before calling `normalize_mapping`. Or, adjust `normalize_mapping` to accept a base default map. *Simpler approach:* The `_get_mapping` method within the reader can handle loading defaults and merging with the user config before returning the final map to be used.

**Example in `FmpReader`:**

```python
# fin_statement_model/io/readers/fmp.py
import yaml
import importlib.resources
from typing import ClassVar
# ... other imports ...

class FmpReader(DataReader):
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    DEFAULT_MAPPINGS: ClassVar[dict] = {} # Loaded at class level

    @classmethod
    def _load_default_mappings(cls):
        try:
            # Use importlib.resources for robust package data loading
            yaml_content = importlib.resources.files(
                "fin_statement_model.io.readers.config" # Adjust package path
            ).joinpath("fmp_default_mappings.yaml").read_text(encoding="utf-8")
            cls.DEFAULT_MAPPINGS = yaml.safe_load(yaml_content) or {}
            logger.info("Loaded default FMP mappings.")
        except Exception as e:
            logger.error(f"Failed to load default FMP mappings: {e}", exc_info=True)
            cls.DEFAULT_MAPPINGS = {} # Ensure it's a dict

    def __init__(self, cfg: FmpReaderConfig) -> None:
        self.cfg = cfg
        if not FmpReader.DEFAULT_MAPPINGS: # Load if not already loaded
            FmpReader._load_default_mappings()

    def _get_mapping(self, statement_type: Optional[str]) -> dict[str, str]:
        """Get the effective mapping, layering defaults, user config, and context."""
        # 1. Start with base defaults (if any exist for the statement type)
        # The DEFAULT_MAPPINGS structure should match MappingConfig (nested)
        base_defaults = normalize_mapping(self.DEFAULT_MAPPINGS, context_key=statement_type)

        # 2. Get user-specific mapping (already includes default + context overlay)
        user_mapping = normalize_mapping(self.cfg.mapping_config, context_key=statement_type)

        # 3. Merge: User mapping overrides base defaults
        final_mapping = base_defaults.copy()
        final_mapping.update(user_mapping)
        return final_mapping

    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        # ... (validation) ...
        ticker = source
        statement_type = self.cfg.statement_type # Get from config

        # --- Get Effective Mapping ---
        try:
            # Use the internal method that handles defaults + user config
            mapping = self._get_mapping(statement_type)
            logger.debug(f"Using effective mapping for {ticker} {statement_type}: {mapping}")
        except TypeError as te:
            # ... (error handling) ...

        # ... (API call logic) ...

        # --- Process Data and Populate Graph ---
        try:
            # ... (loop through API data) ...
            for period_data in api_data:
                # ...
                for api_field, value in period_data.items():
                    # <<< APPLY MAPPING HERE >>>
                    node_name = mapping.get(api_field, api_field) # Fallback to original
                    # <<< Use 'node_name' (canonical) >>>

                    # ... (store value in all_item_data using node_name as key) ...

            # ... (create nodes using canonical node_name) ...
            for node_name, period_values in all_item_data.items():
                 # ... create FinancialStatementItemNode(name=node_name, ...) ...

        # ... (error handling and return graph) ...

# Load defaults when the class is defined
# FmpReader._load_default_mappings() # Moved loading to __init__ to ensure it happens

```

**5. Update Facade Function (`read_data`)**

Ensure the main `read_data` function in `fin_statement_model/io/__init__.py` correctly passes the `mapping_config` (and potentially other relevant context like `statement_type`) from its `**kwargs` into the Pydantic validation and subsequently to the reader's constructor via the validated `cfg` object. Your current implementation using `schema.model_validate({**kwargs, "format_type": format_type})` should handle this correctly if `mapping_config` is part of the `kwargs`.

**Benefits of this Approach:**

*   **Centralized Logic:** Mapping is handled consistently within the readers.
*   **Flexibility:** Supports default mappings and context-specific overrides.
*   **User Configuration:** Users can easily provide their own YAML/JSON mapping files.
*   **Maintainability:** Canonical names simplify internal logic (metrics, statement definitions).
*   **Reduced Duplication:** Avoids creating separate metric/statement definitions for minor name variations.
*   **Robustness:** Uses Pydantic for configuration validation and `importlib.resources` for reliable default loading.

This setup provides a powerful and flexible way to handle the common problem of inconsistent naming in financial data sources. Remember to document the mapping configuration format and how users can provide their own mappings.