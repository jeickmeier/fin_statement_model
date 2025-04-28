| Description                        |     2021 (H) |     2022 (H) |     2023 (H) |     2024 (F) |     2025 (F) |     2026 (F) |     2027 (F) |     2028 (F) |
| ---------------------------------- | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
|     Cash and Cash Equivalents      |        90.00 |       100.00 |       120.00 |       126.00 |       132.30 |       138.92 |       145.86 |       153.15 |
|     Accounts Receivable            |       180.00 |       200.00 |       250.00 |       295.14 |       348.43 |       411.34 |       485.61 |       573.29 |
| **    Total Current Assets**       |   **270.00** |   **300.00** |   **370.00** |   **421.14** |   **480.73** |   **550.25** |   **631.47** |   **726.44** |
|     Property, Plant & Equipment    |       480.00 |       500.00 |       550.00 |       561.00 |       572.22 |       583.66 |       595.34 |       607.24 |
|     Total Assets                   |       750.00 |       800.00 |       920.00 |       982.14 |     1,052.95 |     1,133.92 |     1,226.81 |     1,333.69 |
|         Accounts Payable           |       140.00 |       150.00 |       180.00 |       187.20 |       192.82 |       198.60 |       202.57 |       206.62 |
|         Long-Term Debt             |       290.00 |       300.00 |       320.00 |       320.00 |       320.00 |       320.00 |       320.00 |       320.00 |
| **        Total Liabilities**      |   **430.00** |   **450.00** |   **500.00** |   **507.20** |   **512.82** |   **518.60** |   **522.57** |   **526.62** |
|         Common Stock               |       100.00 |       100.00 |       100.00 |       100.00 |       100.00 |       100.00 |       100.00 |       100.00 |
|         Retained Earnings          |     1,602.00 |     1,790.00 |     2,160.00 |     2,381.98 |     2,614.82 |     2,864.48 |     3,141.52 |     3,438.82 |
| **        Total Equity**           | **1,702.00** | **1,890.00** | **2,260.00** | **2,481.98** | **2,714.82** | **2,964.48** | **3,241.52** | **3,538.82** |
| **    Total Liabilities & Equity** | **2,132.00** | **2,340.00** | **2,760.00** | **2,989.18** | **3,227.64** | **3,483.08** | **3,764.09** | **4,065.44** |
|     Revenue                        |       900.00 |     1,000.00 |     1,200.00 |     1,320.00 |     1,438.80 |     1,553.90 |     1,662.68 |     1,762.44 |
|     Cost of Goods Sold             |       350.00 |       400.00 |       500.00 |       598.21 |       715.72 |       856.31 |     1,024.51 |     1,225.76 |
|     Gross Profit                   |     1,250.00 |     1,400.00 |     1,700.00 |     1,918.21 |     2,154.52 |     2,410.21 |     2,687.19 |     2,988.19 |
|     Operating Expenses             |       280.00 |       300.00 |       350.00 |       359.39 |       363.66 |       368.26 |       382.94 |       399.35 |
|     Net Income                     |     1,530.00 |     1,700.00 |     2,050.00 |     2,277.61 |     2,518.18 |     2,778.48 |     3,070.13 |     3,387.54 |

## Forecast Notes
- **core.cash**: Forecasted using method 'simple' (e.g., fixed growth rate: 5.0%).
- **core.accounts_receivable**: Forecasted using method 'historical_growth' (based on average historical growth).
- **core.ppe**: Forecasted using method 'simple' (e.g., fixed growth rate: 2.0%).
- **core.accounts_payable**: Forecasted using method 'curve' (e.g., specific growth rates: [4.0%, 3.0%, 3.0%, 2.0%, 2.0%]).
- **core.debt**: Forecasted using method 'simple' (e.g., fixed growth rate: 0.0%).
- **core.common_stock**: Forecasted using method 'simple' (e.g., fixed growth rate: 0.0%).
- **core.prior_retained_earnings**: Forecasted using method 'simple' (e.g., fixed growth rate: 0.0%).
- **core.dividends**: Forecasted using method 'historical_growth' (based on average historical growth).
- **core.revenue**: Forecasted using method 'curve' (e.g., specific growth rates: [10.0%, 9.0%, 8.0%, 7.0%, 6.0%]).
- **core.cogs**: Forecasted using method 'historical_growth' (based on average historical growth).
- **core.opex**: Forecasted using method 'statistical' (using 'normal' distribution with params: mean=0.030, std=0.015).

## Adjustment Notes (Matching Filter)
- **core.opex** (2024, Scenario: default, Prio: -10): Replacement adjustment of -400.00. Reason: Revised forecast for OPEX in 2024 based on restructuring.. Tags: [forecast_revision, restructuring]. (ID: 302d6e29-d7c7-4ef5-aac8-9b44c3a46886)
- **core.revenue** (2023, Scenario: default, Prio: 0): Additive adjustment of 75.00. Reason: Late recognized revenue for 2023.. Tags: [manual, revenue_recognition]. (ID: 0fb36129-3114-4485-817a-07553700f366)