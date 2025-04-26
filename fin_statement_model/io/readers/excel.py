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
from fin_statement_model.io.readers.base import MappingConfig, normalize_mapping
from fin_statement_model.io.config.models import ExcelReaderConfig

logger = logging.getLogger(__name__)


@register_reader("excel")
class ExcelReader(DataReader):
    """Reads financial statement data from an Excel file into a Graph.

    Expects data in a tabular format where rows typically represent items
    and columns represent periods, or vice-versa.
    Requires specifying sheet name, period identification, and item identification.

    Configuration (sheet_name, items_col, periods_row, mapping_config) is passed
    via an `ExcelReaderConfig` object during initialization (typically by the `read_data` facade).
    Method-specific options (`statement_type`, `header_row`, `nrows`, `skiprows`)
    are passed as keyword arguments to the `read()` method.
    """

    def __init__(self, cfg: ExcelReaderConfig) -> None:
        """Initialize the ExcelReader with validated configuration.

        Args:
            cfg: A validated `ExcelReaderConfig` instance containing parameters like
                 `source`, `sheet_name`, `items_col`, `periods_row`, and `mapping_config`.
        """
        self.cfg = cfg

    def _get_mapping(
        self,
        statement_type: Optional[str],
    ) -> dict[str, str]:
        """Get the appropriate mapping based on statement type and the stored config."""
        # Use the mapping config stored in the validated Pydantic config object
        config = self.cfg.mapping_config
        # Normalize and overlay user-provided mappings
        mapping = normalize_mapping(config, context_key=statement_type)
        return mapping

    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        """Read data from an Excel file sheet into a new Graph based on instance config.

        Args:
            source (str): Path to the Excel file.
            **kwargs: Optional runtime keyword arguments:
                statement_type (str, optional): Type of statement ('income_statement', 'balance_sheet', 'cash_flow').
                    Used to select a scope within the `mapping_config` provided during initialization.
                header_row (int, optional): 1-based index for pandas header reading.
                    Defaults to `self.cfg.periods_row` if not provided.
                nrows (int, optional): Number of rows to read from the sheet.
                skiprows (int, optional): Number of rows to skip at the beginning.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the file cannot be read or the configuration is invalid.
            AssertionError: If the reader was not initialized with a configuration.
        """
        assert self.cfg is not None, "ExcelReader must be initialized with a valid configuration."
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

        # Use configuration directly from self.cfg
        sheet_name = self.cfg.sheet_name
        periods_row = self.cfg.periods_row
        items_col = self.cfg.items_col

        # Convert to 0-based indices for pandas
        periods_row_0idx = periods_row - 1 if periods_row else None
        items_col_0idx = items_col - 1 if items_col else None
        # Get header_row from kwargs, default to configured periods_row
        header_row = kwargs.get("header_row", self.cfg.periods_row)
        header_row_0idx = header_row - 1 if header_row else periods_row_0idx

        if sheet_name is None or periods_row_0idx is None or items_col_0idx is None:
            raise ReadError(
                "Configuration is missing required arguments: 'sheet_name', 'periods_row', 'items_col'.",
                source=file_path,
                reader_type="ExcelReader",
            )

        # Runtime options from kwargs
        statement_type = kwargs.get("statement_type")
        nrows = kwargs.get("nrows")
        skiprows = kwargs.get("skiprows")

        # Determine mapping based on config and runtime statement_type
        try:
            mapping = self._get_mapping(statement_type)
        except TypeError as te:
            raise ReadError(
                "Invalid mapping_config provided.",
                source=file_path,
                reader_type="ExcelReader",
                original_error=te,
            )
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
