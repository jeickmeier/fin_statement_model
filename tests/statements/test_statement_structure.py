"""Unit tests for the statement_structure module.

This module contains tests for the statement structure classes which form
the foundation of the Financial Statement Model's statement representation.
"""
import pytest
from unittest.mock import Mock, patch

from fin_statement_model.statements.statement_structure import (
    StatementItemType,
    StatementItem,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    Section,
    StatementStructure
)
from fin_statement_model.core.errors import StatementError


class TestStatementItemType:
    """Tests for the StatementItemType enum."""
    
    def test_item_types(self):
        """Test enum values."""
        assert StatementItemType.SECTION.value == "section"
        assert StatementItemType.LINE_ITEM.value == "line_item"
        assert StatementItemType.SUBTOTAL.value == "subtotal"
        assert StatementItemType.CALCULATED.value == "calculated"


class TestLineItem:
    """Tests for the LineItem class."""
    
    def test_init_valid(self):
        """Test initialization with valid parameters."""
        item = LineItem(
            id="revenue",
            name="Total Revenue",
            node_id="revenue_node",
            description="Revenue from all sources",
            sign_convention=1,
            metadata={"source": "sales data"}
        )
        
        assert item.id == "revenue"
        assert item.name == "Total Revenue"
        assert item.node_id == "revenue_node"
        assert item.description == "Revenue from all sources"
        assert item.sign_convention == 1
        assert item.metadata == {"source": "sales data"}
        assert item.item_type == StatementItemType.LINE_ITEM
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        item = LineItem(
            id="revenue",
            name="Total Revenue",
            node_id="revenue_node"
        )
        
        assert item.id == "revenue"
        assert item.name == "Total Revenue"
        assert item.node_id == "revenue_node"
        assert item.description == ""
        assert item.sign_convention == 1
        assert item.metadata == {}
    
    def test_init_invalid_id(self):
        """Test initialization with invalid ID."""
        with pytest.raises(StatementError) as excinfo:
            LineItem(id="", name="Invalid", node_id="test")
        
        assert "Invalid line item ID" in str(excinfo.value)
        
        with pytest.raises(StatementError) as excinfo:
            LineItem(id=None, name="Invalid", node_id="test")
        
        assert "Invalid line item ID" in str(excinfo.value)
    
    def test_init_invalid_name(self):
        """Test initialization with invalid name."""
        with pytest.raises(StatementError) as excinfo:
            LineItem(id="test", name="", node_id="test")
        
        assert "Invalid line item name" in str(excinfo.value)
        
        with pytest.raises(StatementError) as excinfo:
            LineItem(id="test", name=None, node_id="test")
        
        assert "Invalid line item name" in str(excinfo.value)
    
    def test_init_invalid_node_id(self):
        """Test initialization with invalid node ID."""
        with pytest.raises(StatementError) as excinfo:
            LineItem(id="test", name="Test", node_id=123)
        
        assert "Invalid node ID" in str(excinfo.value)
    
    def test_init_invalid_sign_convention(self):
        """Test initialization with invalid sign convention."""
        # Test for sign convention 0
        try:
            LineItem(id="test", name="Test", node_id="test", sign_convention=0)
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid sign convention for line item" in str(e)
        
        # Test for sign convention 2
        try:
            LineItem(id="test", name="Test", node_id="test", sign_convention=2)
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid sign convention for line item" in str(e)


class TestCalculatedLineItem:
    """Tests for the CalculatedLineItem class."""
    
    def test_init_valid(self):
        """Test initialization with valid parameters."""
        item = CalculatedLineItem(
            id="gross_profit",
            name="Gross Profit",
            calculation={
                "type": "addition",
                "inputs": ["revenue", "cogs"],
                "parameters": {"invert_second": True}
            },
            description="Gross profit calculation",
            sign_convention=1,
            metadata={"category": "profitability"}
        )
        
        assert item.id == "gross_profit"
        assert item.name == "Gross Profit"
        assert item.node_id == "gross_profit"  # Uses ID as node_id
        assert item.description == "Gross profit calculation"
        assert item.sign_convention == 1
        assert item.metadata == {"category": "profitability"}
        assert item.item_type == StatementItemType.CALCULATED
        assert item.calculation_type == "addition"
        assert item.input_ids == ["revenue", "cogs"]
        assert item.parameters == {"invert_second": True}
    
    def test_init_minimal_calculation(self):
        """Test initialization with minimal calculation parameters."""
        item = CalculatedLineItem(
            id="gross_profit",
            name="Gross Profit",
            calculation={
                "type": "addition",
                "inputs": ["revenue", "cogs"]
            }
        )
        
        assert item.calculation_type == "addition"
        assert item.input_ids == ["revenue", "cogs"]
        assert item.parameters == {}
    
    def test_init_invalid_calculation_type(self):
        """Test initialization with invalid calculation type."""
        try:
            CalculatedLineItem(
                id="test",
                name="Test",
                calculation={
                    "inputs": ["revenue", "cogs"]
                    # Missing 'type'
                }
            )
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Missing calculation type" in str(e)
    
    def test_init_invalid_calculation_inputs(self):
        """Test initialization with invalid calculation inputs."""
        try:
            CalculatedLineItem(
                id="test",
                name="Test",
                calculation={
                    "type": "addition"
                    # Missing 'inputs'
                }
            )
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Missing calculation inputs" in str(e)
        
        try:
            CalculatedLineItem(
                id="test",
                name="Test",
                calculation={
                    "type": "addition",
                    "inputs": "revenue"  # Not a list
                }
            )
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Calculation inputs must be a list" in str(e)
    
    def test_init_invalid_calculation(self):
        """Test initialization with invalid calculation."""
        try:
            CalculatedLineItem(
                id="test",
                name="Test",
                calculation="invalid"  # Not a dict
            )
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid calculation specification" in str(e)


class TestSubtotalLineItem:
    """Tests for the SubtotalLineItem class."""
    
    def test_init_valid(self):
        """Test initialization with valid parameters."""
        item = SubtotalLineItem(
            id="total_expenses",
            name="Total Expenses",
            item_ids=["salaries", "rent", "utilities"],
            description="Total of all expenses",
            sign_convention=-1,
            metadata={"group": "expenses"}
        )
        
        assert item.id == "total_expenses"
        assert item.name == "Total Expenses"
        assert item.description == "Total of all expenses"
        assert item.sign_convention == -1
        assert item.metadata == {"group": "expenses"}
        assert item.item_type == StatementItemType.SUBTOTAL
        assert item.item_ids == ["salaries", "rent", "utilities"]
        assert item.calculation_type == "addition"
        assert item.input_ids == ["salaries", "rent", "utilities"]
    
    def test_init_invalid_item_ids(self):
        """Test initialization with invalid item IDs."""
        with pytest.raises(StatementError) as excinfo:
            SubtotalLineItem(
                id="total",
                name="Total",
                item_ids=None  # Not a list
            )
        
        assert "Invalid or empty item IDs" in str(excinfo.value)
        
        with pytest.raises(StatementError) as excinfo:
            SubtotalLineItem(
                id="total",
                name="Total",
                item_ids=[]  # Empty list
            )
        
        assert "Invalid or empty item IDs" in str(excinfo.value)


class TestSection:
    """Tests for the Section class."""
    
    def test_init_valid(self):
        """Test initialization with valid parameters."""
        section = Section(
            id="revenue_section",
            name="Revenue",
            description="Revenue items",
            metadata={"order": 1}
        )
        
        assert section.id == "revenue_section"
        assert section.name == "Revenue"
        assert section.description == "Revenue items"
        assert section.metadata == {"order": 1}
        assert section.items == []
        assert section.item_type == StatementItemType.SECTION
    
    def test_init_invalid_id(self):
        """Test initialization with invalid ID."""
        try:
            Section(id="", name="Invalid")
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid section ID" in str(e)
        
        try:
            Section(id=None, name="Invalid")
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid section ID" in str(e)
    
    def test_init_invalid_name(self):
        """Test initialization with invalid name."""
        try:
            Section(id="test", name="")
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid section name" in str(e)
        
        try:
            Section(id="test", name=None)
            pytest.fail("Expected StatementError was not raised")
        except StatementError as e:
            assert "Invalid section name" in str(e)
    
    def test_add_item(self):
        """Test adding items to a section."""
        section = Section(id="test_section", name="Test Section")
        item1 = LineItem(id="item1", name="Item 1", node_id="node1")
        item2 = LineItem(id="item2", name="Item 2", node_id="node2")
        
        section.add_item(item1)
        section.add_item(item2)
        
        assert len(section.items) == 2
        assert section.items[0] == item1
        assert section.items[1] == item2
    
    def test_add_item_duplicate(self):
        """Test adding an item with a duplicate ID."""
        section = Section(id="test_section", name="Test Section")
        item1 = LineItem(id="item1", name="Item 1", node_id="node1")
        item2 = LineItem(id="item1", name="Duplicate ID", node_id="node2")
        
        section.add_item(item1)
        
        with pytest.raises(StatementError) as excinfo:
            section.add_item(item2)
        
        assert "Duplicate item ID" in str(excinfo.value)
        assert "item1" in str(excinfo.value)
        assert "test_section" in str(excinfo.value)
    
    def test_find_item_by_id_direct(self):
        """Test finding an item directly in a section."""
        section = Section(id="test_section", name="Test Section")
        item1 = LineItem(id="item1", name="Item 1", node_id="node1")
        item2 = LineItem(id="item2", name="Item 2", node_id="node2")
        
        section.add_item(item1)
        section.add_item(item2)
        
        found = section.find_item_by_id("item1")
        assert found == item1
        
        found = section.find_item_by_id("item2")
        assert found == item2
        
        # Section matches its own ID
        found = section.find_item_by_id("test_section")
        assert found == section
        
        # Non-existent ID
        found = section.find_item_by_id("nonexistent")
        assert found is None
    
    def test_find_item_by_id_nested(self):
        """Test finding an item in a nested subsection."""
        parent = Section(id="parent", name="Parent Section")
        child = Section(id="child", name="Child Section")
        item = LineItem(id="item", name="Test Item", node_id="node")
        
        child.add_item(item)
        parent.add_item(child)
        
        found = parent.find_item_by_id("item")
        assert found == item


class TestStatementStructure:
    """Tests for the StatementStructure class."""
    
    @pytest.fixture
    def sample_statement(self):
        """Fixture providing a sample statement structure."""
        statement = StatementStructure(
            id="income_statement",
            name="Income Statement",
            description="Test income statement",
            metadata={"period": "annual"}
        )
        
        # Create sections
        revenue_section = Section(
            id="revenue_section",
            name="Revenue"
        )
        
        expense_section = Section(
            id="expense_section",
            name="Expenses"
        )
        
        profit_section = Section(
            id="profit_section",
            name="Profit"
        )
        
        # Create line items
        revenue_item = LineItem(
            id="revenue",
            name="Total Revenue",
            node_id="revenue"
        )
        
        cogs_item = LineItem(
            id="cogs",
            name="Cost of Goods Sold",
            node_id="cogs",
            sign_convention=-1
        )
        
        opex_item = LineItem(
            id="opex",
            name="Operating Expenses",
            node_id="opex",
            sign_convention=-1
        )
        
        # Create subtotal
        expenses_subtotal = SubtotalLineItem(
            id="total_expenses",
            name="Total Expenses",
            item_ids=["cogs", "opex"]
        )
        
        # Create calculated items
        gross_profit = CalculatedLineItem(
            id="gross_profit",
            name="Gross Profit",
            calculation={
                "type": "addition",
                "inputs": ["revenue", "cogs"]
            }
        )
        
        operating_profit = CalculatedLineItem(
            id="operating_profit",
            name="Operating Profit",
            calculation={
                "type": "addition",
                "inputs": ["gross_profit", "opex"]
            }
        )
        
        # Build structure
        revenue_section.add_item(revenue_item)
        expense_section.add_item(cogs_item)
        expense_section.add_item(opex_item)
        expense_section.add_item(expenses_subtotal)
        profit_section.add_item(gross_profit)
        profit_section.add_item(operating_profit)
        
        statement.add_section(revenue_section)
        statement.add_section(expense_section)
        statement.add_section(profit_section)
        
        return statement
    
    def test_init_valid(self):
        """Test initialization with valid parameters."""
        statement = StatementStructure(
            id="income_statement",
            name="Income Statement",
            description="Annual income statement",
            metadata={"period": "annual"}
        )
        
        assert statement.id == "income_statement"
        assert statement.name == "Income Statement"
        assert statement.description == "Annual income statement"
        assert statement.metadata == {"period": "annual"}
        assert statement.sections == []
    
    def test_init_invalid_id(self):
        """Test initialization with invalid ID."""
        with pytest.raises(StatementError) as excinfo:
            StatementStructure(id="", name="Invalid")
        
        assert "Invalid statement ID" in str(excinfo.value)
        
        with pytest.raises(StatementError) as excinfo:
            StatementStructure(id=None, name="Invalid")
        
        assert "Invalid statement ID" in str(excinfo.value)
    
    def test_init_invalid_name(self):
        """Test initialization with invalid name."""
        with pytest.raises(StatementError) as excinfo:
            StatementStructure(id="test", name="")
        
        assert "Invalid statement name" in str(excinfo.value)
        
        with pytest.raises(StatementError) as excinfo:
            StatementStructure(id="test", name=None)
        
        assert "Invalid statement name" in str(excinfo.value)
    
    def test_add_section(self):
        """Test adding sections to a statement."""
        statement = StatementStructure(id="test", name="Test Statement")
        section1 = Section(id="section1", name="Section 1")
        section2 = Section(id="section2", name="Section 2")
        
        statement.add_section(section1)
        statement.add_section(section2)
        
        assert len(statement.sections) == 2
        assert statement.sections[0] == section1
        assert statement.sections[1] == section2
    
    def test_add_section_duplicate_id(self):
        """Test adding a section with a duplicate ID."""
        statement = StatementStructure(id="test", name="Test Statement")
        section1 = Section(id="section1", name="Section 1")
        section2 = Section(id="section1", name="Duplicate ID")
        
        statement.add_section(section1)
        
        with pytest.raises(StatementError) as excinfo:
            statement.add_section(section2)
        
        assert "Duplicate section ID" in str(excinfo.value)
        assert "section1" in str(excinfo.value)
        assert "test" in str(excinfo.value)
    
    def test_find_item_by_id(self, sample_statement):
        """Test finding an item by ID."""
        # Find a section
        revenue_section = sample_statement.find_item_by_id("revenue_section")
        assert revenue_section.name == "Revenue"
        
        # Find a line item
        revenue = sample_statement.find_item_by_id("revenue")
        assert revenue.name == "Total Revenue"
        
        # Find a calculated item
        gross_profit = sample_statement.find_item_by_id("gross_profit")
        assert gross_profit.name == "Gross Profit"
        
        # Non-existent ID
        nonexistent = sample_statement.find_item_by_id("nonexistent")
        assert nonexistent is None
    
    def test_find_item(self, sample_statement):
        """Test the find_item alias method."""
        # Verify that find_item is an alias for find_item_by_id
        revenue = sample_statement.find_item("revenue")
        assert revenue.name == "Total Revenue"
        
        # Should match the behavior of find_item_by_id
        assert sample_statement.find_item("nonexistent") is None
    
    def test_get_all_items(self, sample_statement):
        """Test getting all items in a statement."""
        all_items = sample_statement.get_all_items()
        
        # Should include all sections and items
        assert len(all_items) == 9  # 3 sections + 6 items
        
        # Verify sections are included
        section_ids = [item.id for item in all_items if item.item_type == StatementItemType.SECTION]
        assert set(section_ids) == {"revenue_section", "expense_section", "profit_section"}
        
        # Verify line items are included
        line_item_ids = [item.id for item in all_items if item.item_type == StatementItemType.LINE_ITEM]
        assert set(line_item_ids) == {"revenue", "cogs", "opex"}
        
        # Verify calculated items are included
        calc_item_ids = [item.id for item in all_items if item.item_type == StatementItemType.CALCULATED]
        assert "gross_profit" in calc_item_ids
        assert "operating_profit" in calc_item_ids
        
        # Verify subtotal items are included
        subtotal_ids = [item.id for item in all_items if item.item_type == StatementItemType.SUBTOTAL]
        assert subtotal_ids == ["total_expenses"]
    
    def test_get_items_by_type(self, sample_statement):
        """Test getting items by type."""
        # Get sections
        sections = sample_statement.get_items_by_type(StatementItemType.SECTION)
        assert len(sections) == 3
        assert all(item.item_type == StatementItemType.SECTION for item in sections)
        
        # Get line items
        line_items = sample_statement.get_items_by_type(StatementItemType.LINE_ITEM)
        assert len(line_items) == 3
        assert all(item.item_type == StatementItemType.LINE_ITEM for item in line_items)
        
        # Get calculated items
        calc_items = sample_statement.get_items_by_type(StatementItemType.CALCULATED)
        assert len(calc_items) == 2
        assert all(item.item_type == StatementItemType.CALCULATED for item in calc_items)
        
        # Get subtotal items
        subtotal_items = sample_statement.get_items_by_type(StatementItemType.SUBTOTAL)
        assert len(subtotal_items) == 1
        assert all(item.item_type == StatementItemType.SUBTOTAL for item in subtotal_items)
    
    def test_get_calculation_items(self, sample_statement):
        """Test getting all calculation items."""
        calc_items = sample_statement.get_calculation_items()
        
        # Should include both calculated and subtotal items
        assert len(calc_items) == 3
        
        # Verify specific items are included
        calc_ids = [item.id for item in calc_items]
        assert set(calc_ids) == {"gross_profit", "operating_profit", "total_expenses"}
        
        # Verify they are all instances of CalculatedLineItem
        assert all(isinstance(item, CalculatedLineItem) for item in calc_items) 