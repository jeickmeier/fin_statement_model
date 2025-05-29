"""Test graph serialization and deserialization functionality."""

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.node_factory import NodeFactory
from fin_statement_model.io.specialized.graph import (
    GraphDefinitionWriter,
    GraphDefinitionReader,
)


class TestGraphSerialization:
    """Test serialization and deserialization of graph definitions."""

    def test_complete_graph_serialization(self):
        """Test serialization and deserialization of a complete graph with various node types."""
        # Create a graph with various node types
        periods = ["2021", "2022", "2023", "2024", "2025"]
        graph = Graph(periods=periods)

        # Add financial statement items
        graph.add_financial_statement_item(
            "Revenue", {"2021": 1000, "2022": 1100, "2023": 1200}
        )
        graph.add_financial_statement_item(
            "COGS", {"2021": 600, "2022": 650, "2023": 700}
        )
        graph.add_financial_statement_item(
            "OpEx", {"2021": 200, "2022": 220, "2023": 240}
        )

        # Add calculation nodes
        graph.add_calculation(
            name="TotalExpenses",
            input_names=["COGS", "OpEx"],
            operation_type="addition",
        )

        graph.add_calculation(
            name="GrossProfit",
            input_names=["Revenue", "COGS"],
            operation_type="subtraction",
        )

        # Add weighted average calculation
        graph.add_calculation(
            name="WeightedMetric",
            input_names=["Revenue", "COGS"],
            operation_type="weighted_average",
            weights=[0.7, 0.3],
        )

        # Add formula calculation
        graph.add_calculation(
            name="ProfitMargin",
            input_names=["GrossProfit", "Revenue"],
            operation_type="formula",
            formula="gross_profit / revenue * 100",
            formula_variable_names=["gross_profit", "revenue"],
        )

        # Add forecast nodes
        revenue_node = graph.nodes["Revenue"]

        simple_forecast = NodeFactory.create_forecast_node(
            name="RevenueForecast_Simple",
            base_node=revenue_node,
            base_period="2023",
            forecast_periods=["2024", "2025"],
            forecast_type="simple",
            growth_params=0.1,
        )
        graph.add_node(simple_forecast)

        curve_forecast = NodeFactory.create_forecast_node(
            name="RevenueForecast_Curve",
            base_node=revenue_node,
            base_period="2023",
            forecast_periods=["2024", "2025"],
            forecast_type="curve",
            growth_params=[0.08, 0.06],
        )
        graph.add_node(curve_forecast)

        # Serialize the graph
        writer = GraphDefinitionWriter()
        graph_dict = writer.write(graph)

        # Verify serialization structure
        assert "periods" in graph_dict
        assert "nodes" in graph_dict
        assert "adjustments" in graph_dict
        assert len(graph_dict["nodes"]) == 9

        # Deserialize the graph
        reader = GraphDefinitionReader()
        new_graph = reader.read(graph_dict)

        # Verify deserialized graph
        assert len(new_graph.nodes) == 9
        assert set(new_graph.periods) == set(periods)

        # Test calculations match
        test_periods = ["2022", "2023"]
        for period in test_periods:
            # Test basic calculations
            assert graph.nodes["TotalExpenses"].calculate(period) == new_graph.nodes[
                "TotalExpenses"
            ].calculate(period)
            assert graph.nodes["GrossProfit"].calculate(period) == new_graph.nodes[
                "GrossProfit"
            ].calculate(period)

            # Test weighted average
            assert graph.nodes["WeightedMetric"].calculate(period) == new_graph.nodes[
                "WeightedMetric"
            ].calculate(period)

            # Test formula calculation
            assert (
                abs(
                    graph.nodes["ProfitMargin"].calculate(period)
                    - new_graph.nodes["ProfitMargin"].calculate(period)
                )
                < 0.001
            )

        # Test forecast nodes
        for period in ["2024", "2025"]:
            assert graph.nodes["RevenueForecast_Simple"].calculate(
                period
            ) == new_graph.nodes["RevenueForecast_Simple"].calculate(period)
            assert graph.nodes["RevenueForecast_Curve"].calculate(
                period
            ) == new_graph.nodes["RevenueForecast_Curve"].calculate(period)

    def test_calculation_args_serialization(self):
        """Test that calculation arguments are properly serialized and deserialized."""
        graph = Graph(periods=["2021", "2022"])

        # Add nodes with calculation arguments
        graph.add_financial_statement_item("A", {"2021": 100, "2022": 110})
        graph.add_financial_statement_item("B", {"2021": 50, "2022": 55})

        # Weighted average with custom weights
        graph.add_calculation(
            name="WeightedAvg",
            input_names=["A", "B"],
            operation_type="weighted_average",
            weights=[0.6, 0.4],
        )

        # Serialize and deserialize
        writer = GraphDefinitionWriter()
        graph_dict = writer.write(graph)

        # Check that weights are serialized
        weighted_node_def = graph_dict["nodes"]["WeightedAvg"]
        assert "calculation_args" in weighted_node_def
        assert weighted_node_def["calculation_args"]["weights"] == [0.6, 0.4]

        # Deserialize and verify calculation works
        reader = GraphDefinitionReader()
        new_graph = reader.read(graph_dict)

        # Verify weighted average calculation
        # Expected: 2021: 100*0.6 + 50*0.4 = 80
        # Expected: 2022: 110*0.6 + 55*0.4 = 88
        assert new_graph.nodes["WeightedAvg"].calculate("2021") == 80.0
        assert new_graph.nodes["WeightedAvg"].calculate("2022") == 88.0

    def test_forecast_node_serialization(self):
        """Test serialization of different forecast node types."""
        graph = Graph(periods=["2021", "2022", "2023", "2024"])
        graph.add_financial_statement_item(
            "Sales", {"2021": 100, "2022": 110, "2023": 120}
        )

        sales_node = graph.nodes["Sales"]

        # Test different forecast types
        forecast_configs = [
            ("simple", 0.1),
            ("curve", [0.12]),  # Only one forecast period, so only one growth rate
            ("average", None),
            ("historical_growth", None),
        ]

        for forecast_type, growth_params in forecast_configs:
            forecast = NodeFactory.create_forecast_node(
                name=f"Forecast_{forecast_type}",
                base_node=sales_node,
                base_period="2023",
                forecast_periods=["2024"],
                forecast_type=forecast_type,
                growth_params=growth_params,
            )
            graph.add_node(forecast)

        # Serialize
        writer = GraphDefinitionWriter()
        graph_dict = writer.write(graph)

        # Verify forecast nodes are serialized
        assert (
            len([n for n in graph_dict["nodes"].values() if n["type"] == "forecast"])
            == 4
        )

        # Deserialize
        reader = GraphDefinitionReader()
        new_graph = reader.read(graph_dict)

        # Verify all forecast nodes exist
        assert "Forecast_simple" in new_graph.nodes
        assert "Forecast_curve" in new_graph.nodes
        assert "Forecast_average" in new_graph.nodes
        assert "Forecast_historical_growth" in new_graph.nodes
