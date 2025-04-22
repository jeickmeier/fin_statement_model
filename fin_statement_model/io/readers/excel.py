"""Data reader for Excel files."""

import logging
import os
from typing import Optional, ClassVar, Any

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.base import DataReader
from fin_statement_model.io.registry import register_reader
from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)


@register_reader("excel")
class ExcelReader(DataReader):
    """Reads financial statement data from an Excel file into a Graph.

    Expects data in a tabular format where rows typically represent items
    and columns represent periods, or vice-versa.
    Requires specifying sheet name, period identification, and item identification.
    """

    # Default field mappings (can be overridden in __init__)
    DEFAULT_INCOME_STATEMENT_MAPPING: ClassVar[dict[str, str]] = {
        "Revenue": "revenue",
        "Cost of Revenue": "cost_of_goods_sold",
        "Gross Profit": "gross_profit",
        # ... (Add other defaults as needed)
    }
    DEFAULT_BALANCE_SHEET_MAPPING: ClassVar[dict[str, str]] = {
        "Cash & Cash Equivalents": "cash_and_cash_equivalents",
        # ... (Add other defaults as needed)
    }
    DEFAULT_CASH_FLOW_MAPPING: ClassVar[dict[str, str]] = {
        "Net Income": "net_income",
        # ... (Add other defaults as needed)
    }

    # Default mappings from expected columns to potential Excel column names
    _REQUIRED_COLUMNS: ClassVar[dict[str, list[str]]] = {
        "item": ["Item", "Metric", "Account", "Financial Statement Line Item"],
    }
    # Optional config: mapping periods in file to standard internal names
    _OPTIONAL_COLUMNS: ClassVar[dict[str, list[str]]] = {
        "description": ["Description"],
    }
    # Default item name mapping
    _DEFAULT_MAPPING: ClassVar[dict[str, str]] = {}

    def __init__(self, column_mapping: Optional[dict[str, str]] = None, **kwargs: dict[str, Any]):
        """Initialize the ExcelReader.

        Args:
            column_mapping: Optional dictionary to map item names from the
                Excel file to canonical node names within the graph.
                Format: {'statement_type': {'Excel Name': 'canonical_name', ...}}
                Example: {'income_statement': {'Total Revenue': 'revenue'}}
                If None, default mappings might be applied based on statement_type
                kwarg in read().
            **kwargs: Additional keyword arguments forwarded to the base
                `DataReader` initializer. These may include reader-specific
                configuration options or metadata required by parent classes.
        """
        super().__init__(**kwargs)
        self.mapping_config = column_mapping or {}
        # Combine provided config with defaults if needed, or handle defaults in read()

    def _get_mapping(self, statement_type: Optional[str]) -> dict[str, str]:
        """Get the appropriate mapping based on statement type."""
        mapping = {}
        # Start with defaults based on type
        if statement_type == "income_statement":
            mapping.update(self.DEFAULT_INCOME_STATEMENT_MAPPING)
        elif statement_type == "balance_sheet":
            mapping.update(self.DEFAULT_BALANCE_SHEET_MAPPING)
        elif statement_type == "cash_flow":
            mapping.update(self.DEFAULT_CASH_FLOW_MAPPING)

        # Layer user-provided config on top
        if statement_type and statement_type in self.mapping_config:
            mapping.update(self.mapping_config[statement_type])
        elif None in self.mapping_config:  # Allow a default user mapping
            mapping.update(self.mapping_config[None])

        return mapping

    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        """Read data from an Excel file sheet into a new Graph.

        Args:
            source (str): Path to the Excel file.
            **kwargs: Required keyword arguments:
                sheet_name (str): Name of the sheet containing the data.
                periods_row (int): 1-based index of the row containing period headers.
                items_col (int): 1-based index of the column containing item names.
            Optional keyword arguments:
                statement_type (str): Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
                                     Used to select default mappings if mapping_config is not exhaustive.
                header_row (int): 1-based index for pandas header reading (defaults to periods_row).
                                  Use if data headers differ from period headers.
                nrows (int): Number of rows to read from the sheet.
                skiprows (int): Number of rows to skip at the beginning.
                mapping_config (dict): Overrides the mapping config provided at init.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the file cannot be read, sheet/row/col are invalid, or required kwargs missing.
        """
        file_path = source
        logger.info(f"Starting import from Excel file: {file_path}")

        # --- Validate Inputs ---
        if not os.path.exists(file_path):
            raise ReadError(
                f"File not found: {file_path}",
                source=file_path,
                reader_type="ExcelReader",
            )
        if not file_path.endswith((".xls", ".xlsx", ".xlsm")):
            raise ReadError(
                f"Not a valid Excel file extension: {file_path}",
                source=file_path,
                reader_type="ExcelReader",
            )

        sheet_name = kwargs.get("sheet_name")
        periods_row_0idx = (
            kwargs.get("periods_row") - 1 if kwargs.get("periods_row") else None
        )  # 0-based for pandas
        items_col_0idx = (
            kwargs.get("items_col") - 1 if kwargs.get("items_col") else None
        )  # 0-based for pandas
        header_row_0idx = (
            kwargs.get("header_row") - 1 if kwargs.get("header_row") else periods_row_0idx
        )

        if sheet_name is None or periods_row_0idx is None or items_col_0idx is None:
            raise ReadError(
                "Missing required arguments: 'sheet_name', 'periods_row', 'items_col' must be provided.",
                source=file_path,
                reader_type="ExcelReader",
            )

        statement_type = kwargs.get("statement_type")
        nrows = kwargs.get("nrows")
        skiprows = kwargs.get("skiprows")

        # Override mapping config if provided in kwargs
        current_mapping_config = kwargs.get("mapping_config", self.mapping_config)
        if not isinstance(current_mapping_config, dict):
            raise ReadError(
                "Invalid mapping_config provided.",
                source=file_path,
                reader_type="ExcelReader",
            )
        self.mapping_config = current_mapping_config  # Update instance mapping if overridden
        mapping = self._get_mapping(statement_type)
        logger.debug(f"Using mapping for statement type '{statement_type}': {mapping}")

        # --- Read Excel Data ---
        try:
            # Read the sheet, potentially skipping rows and limiting rows read
            # Use header_row_0idx to correctly identify column headers
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=header_row_0idx,
                skiprows=skiprows,  # skiprows is applied *before* header selection
                nrows=nrows,
            )

            # Identify the actual period columns based on the periods_row
            # Read the periods row separately if header is different
            if header_row_0idx != periods_row_0idx:
                periods_df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=None,
                    skiprows=periods_row_0idx,
                    nrows=1,
                )
                period_headers = periods_df.iloc[0].astype(str).tolist()
            else:
                # Periods are in the main header row read by pandas
                period_headers = df.columns.astype(str).tolist()

            # Find the item column name from the initial read
            if items_col_0idx >= len(df.columns):
                raise ReadError(
                    f"items_col index ({items_col_0idx + 1}) is out of bounds for sheet '{sheet_name}'. Found columns: {df.columns.tolist()}",
                    source=file_path,
                    reader_type="ExcelReader",
                )
            # item_column_name = df.columns[items_col_0idx] # This variable is assigned but never used.

            # Filter period headers: exclude the item column header itself
            # Assuming periods start *after* the item column typically
            graph_periods = [p for i, p in enumerate(period_headers) if i > items_col_0idx and p]
            if not graph_periods:
                raise ReadError(
                    f"Could not identify period columns in row {periods_row_0idx + 1} after column {items_col_0idx + 1} in sheet '{sheet_name}'. Headers found: {period_headers}",
                    source=file_path,
                    reader_type="ExcelReader",
                )
            logger.info(f"Identified periods: {graph_periods}")

            # Create graph
            graph = Graph(periods=graph_periods)

            # --- Populate Graph ---
            validation_errors = []
            nodes_added = 0
            for index, row in df.iterrows():
                item_name_excel = row.iloc[
                    items_col_0idx
                ]  # Get item name using the identified column
                if pd.isna(item_name_excel) or not item_name_excel:
                    # logger.debug(f"Skipping row {index + (skiprows or 0) + (header_row_0idx or 0) + 1}: Empty item name.")
                    continue

                item_name_excel = str(item_name_excel).strip()
                node_name = mapping.get(
                    item_name_excel, item_name_excel
                )  # Use mapping or fallback to original name

                # Get values for the identified periods
                period_values: dict[str, float] = {}
                for period in graph_periods:
                    try:
                        # Find the corresponding column in the DataFrame using the period header
                        # This assumes the period headers read initially match the df columns
                        if period in df.columns:
                            value = row[period]
                            if pd.isna(value):
                                # Keep NaN or skip? For now, skip. Could represent as None or NaN later.
                                # logger.debug(f"NaN value for {node_name} period {period}")
                                continue
                            elif isinstance(value, (int, float)):
                                period_values[period] = float(value)
                            else:
                                # Attempt conversion, log warning if fails
                                try:
                                    period_values[period] = float(value)
                                    logger.warning(
                                        f"Converted non-numeric value '{value}' to float for node '{node_name}' period '{period}'"
                                    )
                                except (ValueError, TypeError):
                                    validation_errors.append(
                                        f"Row {index}: Non-numeric value '{value}' for node '{node_name}' (from '{item_name_excel}') period '{period}'"
                                    )
                        else:
                            # This shouldn't happen if period_headers came from df.columns
                            logger.warning(
                                f"Period header '{period}' not found in DataFrame columns for row {index}."
                            )
                    except KeyError:
                        validation_errors.append(
                            f"Row {index}: Column for period '{period}' not found for node '{node_name}'"
                        )
                    except Exception as e:
                        validation_errors.append(
                            f"Row {index}: Error processing value for node '{node_name}' period '{period}': {e}"
                        )

                if period_values:
                    if graph.has_node(node_name):
                        logger.warning(
                            f"Node '{node_name}' (from Excel item '{item_name_excel}') already exists. Overwriting data is not standard for readers. Consider unique names or merging logic."
                        )
                        # Get existing node and update? Or raise error? For now, log warning.
                        # existing_node = graph.get_node(node_name)
                        # if isinstance(existing_node, FinancialStatementItemNode):
                        #     existing_node.values.update(period_values)
                    else:
                        # Create and add new node
                        new_node = FinancialStatementItemNode(name=node_name, values=period_values)
                        graph.add_node(new_node)
                        nodes_added += 1
                # else: No valid values for this item in the specified periods

            if validation_errors:
                raise ReadError(
                    f"Validation errors occurred while reading {file_path} sheet '{sheet_name}': {'; '.join(validation_errors)}",
                    source=file_path,
                    reader_type="ExcelReader",
                )

            logger.info(
                f"Successfully created graph with {nodes_added} nodes from {file_path} sheet '{sheet_name}'."
            )
            return graph

        except FileNotFoundError:
            raise ReadError(
                f"File not found: {file_path}",
                source=file_path,
                reader_type="ExcelReader",
            )
        except ValueError as ve:
            # Pandas raises ValueError for bad sheet names etc.
            raise ReadError(
                f"Error reading Excel file: {ve}",
                source=file_path,
                reader_type="ExcelReader",
                original_error=ve,
            )
        except KeyError as ke:
            # Raised if essential columns (like item column after mapping) are missing
            raise ReadError(
                f"Missing expected column/item: {ke}. Check items_col ({items_col_0idx + 1}) and sheet structure.",
                source=file_path,
                reader_type="ExcelReader",
                original_error=ke,
            )
        except Exception as e:
            logger.error(
                f"Failed to read Excel file {file_path} sheet '{sheet_name}': {e}",
                exc_info=True,
            )
            raise ReadError(
                message=f"Failed to process Excel file: {e}",
                source=file_path,
                reader_type="ExcelReader",
                original_error=e,
            ) from e
