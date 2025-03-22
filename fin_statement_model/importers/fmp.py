import requests
from typing import Dict
import pandas as pd
from ..financial_statement import FinancialStatementGraph

class FMPAdapter:
    """
    Financial Modeling Prep API adapter for fetching financial statement data
    and converting it to FinancialStatementGraph format.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the FMP adapter with an API key.
        
        Args:
            api_key (str): FMP API key
        """
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/stable"
        
        # Mapping of FMP field names to standardized node names
        self.income_statement_field_mapping = {
            # Income Statement mappings
            "revenue": "revenue",
            "costOfRevenue": "cost_of_goods_sold",

            "researchAndDevelopmentExpenses": "research_and_development_expenses",
            "generalAndAdministrativeExpenses": "general_and_administrative_expenses",
            "sellingAndMarketingExpenses": "selling_and_marketing_expenses",
            "sellingGeneralAndAdministrativeExpenses": "selling_general_and_administrative_expenses",

            "otherExpenses": "other_interest_expenses",
            "interestIncome": "interest_income",
            "interestExpense": "interest_expense",

            "incomeTaxExpense": "tax_expense",
            "depreciationAndAmortization": "depreciation_and_amortization",
        }

        self.balance_sheet_field_mapping = {
            # Balance Sheet mappings
            "cashAndCashEquivalents": "cash_and_cash_equivalents",
            "shortTermInvestments": "short_term_investments", 

            "netReceivables": "net_receivables",
            "accountsReceivables": "accounts_receivables",
            "otherReceivables": "other_receivables",
            "inventory": "inventory",
            "prepaids": "prepaids",
            "otherCurrentAssets": "other_current_assets",

            "propertyPlantEquipmentNet": "property_plant_equipment_net",
            "goodwill": "goodwill",
            "intangibleAssets": "intangible_assets",
            "goodwillAndIntangibleAssets": "goodwill_and_intangible_assets",
            "longTermInvestments": "long_term_investments",
            "taxAssets": "tax_assets",
            "otherNonCurrentAssets": "other_non_current_assets", 

            "otherAssets": "other_assets",

            "totalPayables": "total_payables",
            "accountPayables": "account_payables",
            "otherPayables": "other_payables",
            "accruedExpenses": "accrued_expenses",
            "shortTermDebt": "short_term_debt",
            "capitalLeaseObligationsCurrent": "capital_lease_obligations_current",
            "taxPayables": "tax_payables",
            "deferredRevenue": "deferred_revenue",
            "otherCurrentLiabilities": "other_current_liabilities",
            "longTermDebt": "long_term_debt",
            "deferredRevenueNonCurrent": "deferred_revenue_non_current",
            "deferredTaxLiabilitiesNonCurrent": "deferred_tax_liabilities_non_current",
            "otherNonCurrentLiabilities": "other_non_current_liabilities",
            "otherLiabilities": "other_liabilities",
            "capitalLeaseObligations": "capital_lease_obligations",

            "treasuryStock": "treasury_stock",
            "preferredStock": "preferred_stock", 
            "commonStock": "common_stock",
            "retainedEarnings": "retained_earnings",
            "additionalPaidInCapital": "additional_paid_in_capital",
            "accumulatedOtherComprehensiveIncomeLoss": "accumulated_other_comprehensive_income_loss",
            "otherTotalStockholdersEquity": "other_total_stockholders_equity"
        }

        self.cash_flow_field_mapping = {
            # Cash Flow mappings
            "operatingCashFlow": "operating_cash_flow",
            "investingCashFlow": "investing_cash_flow",
            "financingCashFlow": "financing_cash_flow",
        }


    def fetch_statement(self, ticker: str, period: str = 'FY', limit: int = 50, statement_type: str = 'income_statement') -> Dict:
        """
        Fetch financial statement data from FMP API.
        
        Args:
            ticker (str): Company ticker symbol (e.g., 'AAPL')
            period (str): 'FY' or 'QTR'
            limit (int): Maximum number of periods to fetch
            
        Returns:
            Dict: Raw financial statement data from FMP
        """
        if statement_type == 'income_statement':
            url = f"{self.base_url}/income-statement?apikey={self.api_key}&symbol={ticker}&period={period}"
        elif statement_type == 'balance_sheet':
            url = f"{self.base_url}/balance-sheet-statement?apikey={self.api_key}&symbol={ticker}&period={period}"
        elif statement_type == 'cash_flow':
            url = f"{self.base_url}/cash-flow-statement?apikey={self.api_key}&symbol={ticker}&period={period}"
        else:
            raise ValueError(f"Invalid statement type: {statement_type}")
        
        #print(url)
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")
            
        return response.json()
    
    def create_statement_graph(self, 
                                      ticker: str, 
                                      period: str = 'FY', 
                                      limit: int = 50,
                                      statement_type: str = 'income_statement') -> FinancialStatementGraph:
        """
        Create a FinancialStatementGraph from FMP financial statement data.
        
        Args:
            ticker (str): Company ticker symbol (e.g., 'AAPL')
            period (str): 'FY' or 'QTR'
            limit (int): Maximum number of periods to fetch
            
        Returns:
            FinancialStatementGraph: Graph containing the financial statement data
        """
        # Fetch raw data
        if statement_type == 'income_statement':
            data = self.fetch_statement(ticker, period, limit, statement_type='income_statement')
            mapping = self.income_statement_field_mapping
        elif statement_type == 'balance_sheet':
            data = self.fetch_statement(ticker, period, limit, statement_type='balance_sheet')
            mapping = self.balance_sheet_field_mapping
        elif statement_type == 'cash_flow':
            data = self.fetch_statement(ticker, period, limit, statement_type='cash_flow')
            mapping = self.cash_flow_field_mapping
        
        # Extract periods
        periods = []
        for statement in data:
            date = statement['date']
            if period == 'FY':
                period_label = f"FY{date[:4]}"
            else:
                quarter = pd.Timestamp(date).quarter
                period_label = f"{date[:4]}Q{quarter}"
            periods.append(period_label)
        periods = sorted(list(set(periods)))
        
        # Initialize graph
        fsg = FinancialStatementGraph(periods=periods)
        
        # Process each mapped field
        for fmp_field, node_name in mapping.items():
            values = {}
            for statement in data:
                date = statement['date']
                if period == 'FY':
                    period_label = f"FY{date[:4]}"
                else:
                    quarter = pd.Timestamp(date).quarter
                    period_label = f"{date[:4]}Q{quarter}"
                    
                if fmp_field in statement:
                    value = statement[fmp_field]
                    if value is not None:
                        values[period_label] = float(value)
            
            if values:  # Only add node if we have values
                fsg.add_financial_statement_item(node_name, values)
        
        # Add common calculations and metrics
        if statement_type == 'income_statement':
            try:
                fsg.add_calculation("operating_expenses", ["research_and_development_expenses", "general_and_administrative_expenses","selling_and_marketing_expenses","selling_general_and_administrative_expenses"], "addition")      
            except Exception as e:
                print(f"Error adding operating expenses: {e}", data)
                print(fsg)
        elif statement_type == 'balance_sheet':
            try:
                fsg.add_calculation("cash_and_short_term_investments", ["cash_and_cash_equivalents", "short_term_investments"], "addition")
                fsg.add_calculation("total_current_assets", ["cash_and_cash_equivalents", "short_term_investments", "net_receivables","accounts_receivables","other_receivables", "inventory", "prepaids", "other_current_assets"], "addition")
                fsg.add_calculation("total_non_current_assets", ["property_plant_equipment_net", "goodwill", "intangible_assets", "goodwill_and_intangible_assets", "long_term_investments", "tax_assets", "other_non_current_assets"], "addition")
                fsg.add_calculation("total_assets", ["total_current_assets", "total_non_current_assets"], "addition")

            except Exception as e:
                print(f"Error adding total liabilities: {e}", data)
                print(fsg)
        
        return fsg
