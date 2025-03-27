"""
Export management functionality for the Financial Statement Model.

This module provides the ExportManager class which is responsible for
exporting financial data from the graph to various formats.
"""

from pathlib import Path
from typing import List, Union, Optional
import pandas as pd
import json

from ..core.graph import Graph


class ExportManager:
    """
    Manages exporting financial data from the graph to various formats.

    The ExportManager is responsible for:
    - Exporting data to Excel, CSV, and other file formats
    - Generating reports and visualizations
    - Converting graph data to standard financial statement formats
    - Customizing output based on user requirements

    It provides a unified interface for all data export operations.
    """

    def __init__(self):
        """Initialize the ExportManager."""
        pass

    def to_dataframe(
        self,
        graph: Graph,
        recalculate: bool = True,
        node_names: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Convert the financial statement graph into a pandas DataFrame.

        Args:
            graph: The graph to export
            recalculate: Whether to recalculate all nodes before exporting
            node_names: Optional list of specific node names to include (includes all if None)

        Returns:
            pd.DataFrame: DataFrame with financial statement items as rows and periods as columns

        Example:
            df = exporter.to_dataframe(graph, recalculate=True)
        """
        # Get all periods from the graph
        periods = sorted(graph.periods)

        # Recalculate all nodes if requested
        if recalculate:
            for period in periods:
                graph.recalculate_all(period)

        # Determine which nodes to include
        if node_names is None:
            nodes_to_export = list(graph.nodes.keys())
        else:
            nodes_to_export = [name for name in node_names if name in graph.nodes]

        # Initialize data dictionary
        data = {}

        # Iterate through selected nodes
        for node_name in nodes_to_export:
            values = []
            for period in periods:
                try:
                    value = graph.calculate(node_name, period)
                    values.append(value)
                except (ValueError, KeyError):
                    values.append(None)
            data[node_name] = values

        # Create DataFrame
        df = pd.DataFrame(data).T
        df.columns = periods

        return df

    def to_excel(
        self,
        graph: Graph,
        file_path: Union[str, Path],
        sheet_name: str = "Financial Statement",
        include_header: bool = True,
    ) -> None:
        """
        Export financial statement data to an Excel file.

        Args:
            graph: The graph to export
            file_path: Path to save the Excel file
            sheet_name: Name of the worksheet
            include_header: Whether to include headers in the Excel file

        Raises:
            ValueError: If there is an error exporting to Excel

        Example:
            exporter.to_excel(graph, "financial_statement.xlsx")
        """
        # Convert to DataFrame
        df = self.to_dataframe(graph)

        # Ensure file_path is a Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Export to Excel
        try:
            df.to_excel(file_path, sheet_name=sheet_name, header=include_header)
        except Exception as e:
            raise ValueError(f"Error exporting to Excel: {e}")

    def to_csv(
        self, graph: Graph, file_path: Union[str, Path], include_header: bool = True
    ) -> None:
        """
        Export financial statement data to a CSV file.

        Args:
            graph: The graph to export
            file_path: Path to save the CSV file
            include_header: Whether to include headers in the CSV file

        Raises:
            ValueError: If there is an error exporting to CSV

        Example:
            exporter.to_csv(graph, "financial_statement.csv")
        """
        # Convert to DataFrame
        df = self.to_dataframe(graph)

        # Ensure file_path is a Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Export to CSV
        try:
            df.to_csv(file_path, header=include_header)
        except Exception as e:
            raise ValueError(f"Error exporting to CSV: {e}")

    def to_json(
        self,
        graph: Graph,
        file_path: Optional[Union[str, Path]] = None,
        pretty_print: bool = True,
        include_calculation_nodes: bool = True,
    ) -> Union[str, None]:
        """
        Export financial statement data to JSON.

        Args:
            graph: The graph to export
            file_path: Optional path to save the JSON file (returns string if None)
            pretty_print: Whether to format the JSON with indentation
            include_calculation_nodes: Whether to include calculation nodes or only raw items

        Returns:
            str: JSON string if file_path is None, otherwise None

        Raises:
            ValueError: If there is an error exporting to JSON

        Example:
            json_str = exporter.to_json(graph, pretty_print=True)
            # or
            exporter.to_json(graph, "financial_statement.json")
        """
        # Convert data to a suitable format for JSON
        data = {"periods": graph.periods, "items": {}}

        # Process nodes
        for node_name, node in graph.nodes.items():
            # Skip calculation nodes if requested
            if (
                not include_calculation_nodes
                and hasattr(node, "inputs")
                and node.inputs
            ):
                continue

            # Include node values
            values = {}
            for period in graph.periods:
                try:
                    value = graph.calculate(node_name, period)
                    values[period] = value
                except (ValueError, KeyError):
                    # Skip periods with no value
                    continue

            # Add node to data
            data["items"][node_name] = values

            # Add metadata for calculation nodes
            if hasattr(node, "inputs") and node.inputs:
                data["items"][node_name]["_calculation"] = {
                    "inputs": [input_node.name for input_node in node.inputs],
                    "type": node.__class__.__name__,
                }

        # Convert to JSON
        indent = 4 if pretty_print else None
        json_str = json.dumps(data, indent=indent)

        # Write to file if path provided
        if file_path is not None:
            # Ensure file_path is a Path object
            if isinstance(file_path, str):
                file_path = Path(file_path)

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            try:
                with open(file_path, "w") as f:
                    f.write(json_str)
                return None
            except Exception as e:
                raise ValueError(f"Error exporting to JSON file: {e}")

        return json_str

    def to_html(
        self,
        graph: Graph,
        file_path: Optional[Union[str, Path]] = None,
        include_styles: bool = True,
        title: str = "Financial Statement",
    ) -> Union[str, None]:
        """
        Export financial statement data to HTML format.

        Args:
            graph: The graph to export
            file_path: Optional path to save the HTML file (returns HTML string if None)
            include_styles: Whether to include basic CSS styling
            title: Title for the HTML document

        Returns:
            str: HTML string if file_path is None, otherwise None

        Example:
            html_str = exporter.to_html(graph)
            # or
            exporter.to_html(graph, "financial_statement.html")
        """
        # Convert to DataFrame
        df = self.to_dataframe(graph)

        # Create HTML
        html = f"<html><head><title>{title}</title>"

        # Add styles if requested
        if include_styles:
            html += """
            <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { padding: 8px; text-align: right; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                tr:hover { background-color: #e6f7ff; }
                .header-row { font-weight: bold; }
                .item-name { text-align: left; font-weight: bold; }
            </style>
            """

        html += "</head><body>"
        html += f"<h1>{title}</h1>"

        # Convert DataFrame to HTML table
        table_html = df.to_html(classes="financial-statement")
        html += table_html

        html += "</body></html>"

        # Write to file if path provided
        if file_path is not None:
            # Ensure file_path is a Path object
            if isinstance(file_path, str):
                file_path = Path(file_path)

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            try:
                with open(file_path, "w") as f:
                    f.write(html)
                return None
            except Exception as e:
                raise ValueError(f"Error exporting to HTML file: {e}")

        return html
