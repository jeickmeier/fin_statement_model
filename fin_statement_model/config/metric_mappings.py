"""
Standard metric names and their common aliases for financial statement mapping.
This configuration assists in mapping various naming conventions to standardized metrics.
"""

import json
from pathlib import Path
from typing import Dict, List


class MetricMappingConfig:
    """Manages metric mappings combining static and dynamic configurations."""

    def __init__(self):
        self._static_mappings = STATIC_METRIC_ALIASES
        self._dynamic_mappings = {}
        self._dynamic_file = Path(__file__).parent / "dynamic_mappings.json"
        self.load_dynamic_mappings()

    @property
    def mappings(self) -> Dict[str, List[str]]:
        """Returns combined static and dynamic mappings."""
        combined = self._static_mappings.copy()
        for metric, aliases in self._dynamic_mappings.items():
            if metric in combined:
                # Merge aliases, keeping unique values
                combined[metric] = list(set(combined[metric] + aliases))
            else:
                combined[metric] = aliases
        return combined

    def load_dynamic_mappings(self) -> None:
        """Load dynamic mappings from JSON file if it exists."""
        try:
            if self._dynamic_file.exists():
                with open(self._dynamic_file, "r") as f:
                    self._dynamic_mappings = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load dynamic mappings: {e}")
            self._dynamic_mappings = {}

    def save_dynamic_mappings(self, new_mappings: Dict[str, List[str]]) -> None:
        """Save new mappings to dynamic mappings file."""
        try:
            # Merge new mappings with existing dynamic mappings
            for metric, aliases in new_mappings.items():
                if metric in self._dynamic_mappings:
                    self._dynamic_mappings[metric] = list(
                        set(self._dynamic_mappings[metric] + aliases)
                    )
                else:
                    self._dynamic_mappings[metric] = aliases

            # Save to file
            with open(self._dynamic_file, "w") as f:
                json.dump(self._dynamic_mappings, f, indent=4)
        except Exception as e:
            raise RuntimeError(f"Failed to save dynamic mappings: {e}")


# Static mappings definition
STATIC_METRIC_ALIASES = {
    # Revenue related
    "revenue": [
        "sales",
        "net sales",
        "total revenue",
        "gross revenue",
        "operating revenue",
        "net revenue",
        "turnover",
    ],
    # Cost related
    "cost_of_goods_sold": [
        "cogs",
        "cost of sales",
        "cost of revenue",
        "direct costs",
        "cost of products",
        "cost of services",
    ],
    # Operating expenses
    "operating_expenses": [
        "opex",
        "operating costs",
        "total operating expenses",
        "operational expenses",
        "selling general and administrative",
        "sga",
        "operating expense",
    ],
    # Interest related
    "interest_expense": [
        "interest costs",
        "financing costs",
        "interest charges",
        "debt expense",
    ],
    "interest_income": ["interest earned", "interest revenue", "investment income"],
    # Tax related
    "tax_expense": [
        "income tax",
        "income tax expense",
        "tax provision",
        "income taxes",
        "tax charge",
    ],
    # Asset related
    "total_assets": ["assets", "total assets", "assets total", "gross assets"],
    "current_assets": [
        "total current assets",
        "current assets total",
        "short term assets",
    ],
    # Liability related
    "current_liabilities": [
        "total current liabilities",
        "short term liabilities",
        "current obligations",
    ],
    # Equity related
    "total_equity": [
        "shareholders equity",
        "stockholders equity",
        "net worth",
        "book value",
        "total shareholders equity",
    ],
    # Working capital components
    "inventory": ["inventories", "stock", "merchandise inventory", "goods inventory"],
    "accounts_receivable": ["ar", "trade receivables", "receivables", "debtors"],
    "accounts_payable": ["ap", "trade payables", "payables", "creditors"],
    # Cash related
    "cash": [
        "cash and cash equivalents",
        "cash & equivalents",
        "cash and equivalents",
        "cash & cash equivalents",
    ],
    "operating_cash_flow": [
        "cash from operations",
        "operating activities",
        "net cash from operations",
        "ocf",
    ],
    # Debt related
    "total_debt": [
        "debt",
        "total borrowings",
        "financial liabilities",
        "interest bearing debt",
    ],
    # Fixed assets
    "net_fixed_assets": [
        "property plant and equipment",
        "ppe",
        "fixed assets",
        "tangible assets",
    ],
    # Market related
    "market_capitalization": ["market cap", "market value", "market worth"],
    "enterprise_value": ["ev", "firm value", "total enterprise value"],
    # Share related
    "shares_outstanding": [
        "outstanding shares",
        "common shares outstanding",
        "number of shares",
    ],
    "share_price": ["stock price", "price per share", "market price"],
    # Capital expenditure
    "capex": [
        "capital expenditure",
        "capital spending",
        "capital investments",
        "capital expenditures",
    ],
    # Depreciation and Amortization
    "depreciation_and_amortization": [
        "d&a",
        "depreciation & amortization",
        "depreciation and amortisation",
        "depreciation amortization",
    ],
    # Working capital
    "working_capital": [
        "net working capital",
        "operating working capital",
        "working cap",
    ],
    # Dividend related
    "dividends": [
        "dividend payments",
        "total dividends",
        "dividend payout",
        "cash dividends",
    ],
    # Growth metrics
    "revenue_previous": [
        "prior year revenue",
        "last year revenue",
        "previous period revenue",
    ],
    "net_income_previous": [
        "prior year net income",
        "last year net income",
        "previous period net income",
    ],
}

# Initialize the mapping configuration
mapping_config = MetricMappingConfig()
