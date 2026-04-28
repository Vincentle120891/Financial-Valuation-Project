#!/usr/bin/env python3
"""
DuPont Analysis Model - Full Implementation
Matches: MID RETAILER FINANCIAL ANALYSIS specification
"""

import pandas as pd
import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DATA = {
    "company_name": "Mid Retailer Inc.",
    "currency": "USD",
    "years": [1, 2, 3, 4, 5, 6, 7, 8],
    "revenue": [112640, 116199, 118719, 129025, 141576, 152703, 166761, 195929],
    "cogs_gross": [-98458, -101065, -102901, -111882, -123152, -132886, -144939, -170684],
    "depreciation_in_cogs": [1029, 1127, 1255, 1370, 1437, 1492, 1645, 1781],
    "sga": [-10899, -11445, -12068, -12950, -13876, -14994, -16332, -18461],
    "other_opex": [-63, -65, -78, -82, -68, -86, -55, -76],
    "depreciation_explicit": [-1029, -1127, -1255, -1370, -1437, -1492, -1645, -1781],
    "interest_expense": [-113, -124, -133, -134, -159, -150, -160, -171],
    "interest_income": [90, 104, 80, 62, 121, 178, 92, 143],
    "tax_current": [-1109, -1195, -1243, -1325, -1263, -1061, -1308, -1601],
    "tax_other": [-30, -32, -26, -35, -45, -45, -57, -72],
    "cash": [7315, 6419, 4729, 5779, 7259, 9444, 13305, 12175],
    "ar_component1": [1148, 1224, 1252, 1432, 1669, 1535, 1550, 1803],
    "ar_component2": [669, 748, 268, 272, 321, 1111, 1023, 1312],
    "inventory": [8456, 8908, 8969, 9834, 11040, 11395, 12242, 14215],
    "ppe_component1": [15436, 16141, 17945, 18161, 19681, 20890, 24595, 26382],
    "ppe_component2": [0, 0, 0, 869, 860, 1025, 2841, 3381],
    "accounts_payable": [14412, 15257, 14475, 17409, 19836, 21538, 24749, 28642],
    "revolver": [0, 1283, 1100, 86, 90, 1699, 95, 799],
    "long_term_debt": [6309, 6283, 5509, 8074, 8105, 6920, 12428, 12263],
    "common_equity": [4845, 4099, 4393, 4790, 4912, 4985, 5405, 5898],
    "retained_earnings": [7458, 6518, 7686, 5988, 7887, 10258, 12879, 11666],
    "capex": [-3773, -3572, -2623, -5482, -2950, -2950, -7487, -9300],
    "dividends": [-584, 0, 0, 0, 0, 0, 0, 0],
    "beginning_cash": [4644, 5738, 4801, 3379, 4546, 6055, 8384, 12277],
}

class DuPontAnalyzer:
    def __init__(self, ticker: Optional[str] = None):
        self.ticker = ticker.upper() if ticker else None
        self.data: Dict = {}
        self.results: Dict = {}
        
    def load_default_data(self) -> bool:
        try:
            self.data = DEFAULT_DATA.copy()
            self.data["source"] = "default_specification"
            n = len(self.data["years"])
            
            # Income Statement
            self.data["net_cogs"] = [self.data["cogs_gross"][i] + self.data["depreciation_in_cogs"][i] for i in range(n)]
            self.data["gross_profit"] = [self.data["revenue"][i] + self.data["net_cogs"][i] for i in range(n)]
            self.data["ebitda"] = [self.data["gross_profit"][i] + self.data["sga"][i] + self.data["other_opex"][i] for i in range(n)]
            self.data["ebit"] = [self.data["ebitda"][i] + self.data["depreciation_explicit"][i] for i in range(n)]
            self.data["ebt"] = [self.data["ebit"][i] + self.data["interest_expense"][i] + self.data["interest_income"][i] for i in range(n)]
            self.data["tax_total"] = [self.data["tax_current"][i] + self.data["tax_other"][i] for i in range(n)]
            self.data["net_income"] = [self.data["ebt"][i] + self.data["tax_total"][i] for i in range(n)]
            
            # Balance Sheet
            self.data["ar"] = [self.data["ar_component1"][i] + self.data["ar_component2"][i] for i in range(n)]
            self.data["current_assets"] = [self.data["cash"][i] + self.data["ar"][i] + self.data["inventory"][i] for i in range(n)]
            self.data["ppe"] = [self.data["ppe_component1"][i] + self.data["ppe_component2"][i] for i in range(n)]
            self.data["total_assets"] = [self.data["current_assets"][i] + self.data["ppe"][i] for i in range(n)]
            self.data["current_liabilities"] = [self.data["accounts_payable"][i] + self.data["revolver"][i] for i in range(n)]
            self.data["total_liabilities"] = [self.data["current_liabilities"][i] + self.data["long_term_debt"][i] for i in range(n)]
            self.data["total_equity"] = [self.data["common_equity"][i] + self.data["retained_earnings"][i] for i in range(n)]
            
            # Supplemental
            self.data["effective_tax_rate"] = [-self.data["tax_total"][i] / self.data["ebt"][i] if self.data["ebt"][i] != 0 else 0 for i in range(n)]
            self.data["nopat"] = [self.data["ebit"][i] * (1 - self.data["effective_tax_rate"][i]) for i in range(n)]
            self.data["interest_bearing_debt"] = [self.data["revolver"][i] + self.data["long_term_debt"][i] for i in range(n)]
            self.data["net_debt"] = [self.data["interest_bearing_debt"][i] - self.data["cash"][i] for i in range(n)]
            self.data["invested_capital"] = [self.data["net_debt"][i] + self.data["total_equity"][i] for i in range(n)]
            self.data["net_assets"] = [(self.data["current_assets"][i] - self.data["cash"][i]) + self.data["ppe"][i] - self.data["accounts_payable"][i] for i in range(n)]
            
            logger.info("Loaded default Mid Retailer dataset (8 years)")
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def calculate_ratios(self):
        n = len(self.data["years"])
        results = {"Year": self.data["years"]}
        
        # Profitability
        results["ROE"] = [self.data["net_income"][i] / self.data["total_equity"][i] if self.data["total_equity"][i] != 0 else 0 for i in range(n)]
        results["ROA"] = [self.data["net_income"][i] / self.data["total_assets"][i] if self.data["total_assets"][i] != 0 else 0 for i in range(n)]
        results["ROIC"] = [self.data["nopat"][i] / self.data["invested_capital"][i] if self.data["invested_capital"][i] != 0 else 0 for i in range(n)]
        results["Gross_Margin"] = [self.data["gross_profit"][i] / self.data["revenue"][i] for i in range(n)]
        results["EBITDA_Margin"] = [self.data["ebitda"][i] / self.data["revenue"][i] for i in range(n)]
        results["EBIT_Margin"] = [self.data["ebit"][i] / self.data["revenue"][i] for i in range(n)]
        results["Net_Profit_Margin"] = [self.data["net_income"][i] / self.data["revenue"][i] for i in range(n)]
        
        # DuPont Components
        results["Tax_Burden"] = [self.data["net_income"][i] / self.data["ebt"][i] if self.data["ebt"][i] != 0 else 0 for i in range(n)]
        results["Interest_Burden"] = [self.data["ebt"][i] / self.data["ebit"][i] if self.data["ebit"][i] != 0 else 0 for i in range(n)]
        results["Asset_Turnover"] = [self.data["revenue"][i] / self.data["total_assets"][i] for i in range(n)]
        results["Assets_to_Equity"] = [self.data["total_assets"][i] / self.data["total_equity"][i] for i in range(n)]
        
        # Working Capital
        cogs_pos = [-self.data["net_cogs"][i] for i in range(n)]
        results["DSO"] = [(self.data["ar"][i] * 365) / self.data["revenue"][i] for i in range(n)]
        results["DIO"] = [(self.data["inventory"][i] * 365) / cogs_pos[i] for i in range(n)]
        results["DPO"] = [(self.data["accounts_payable"][i] * 365) / cogs_pos[i] for i in range(n)]
        results["CCC"] = [results["DSO"][i] + results["DIO"][i] - results["DPO"][i] for i in range(n)]
        
        # Leverage
        results["Debt_to_Equity"] = [self.data["interest_bearing_debt"][i] / self.data["total_equity"][i] for i in range(n)]
        results["Net_Debt_to_EBITDA"] = [self.data["net_debt"][i] / self.data["ebitda"][i] for i in range(n)]
        results["Current_Ratio"] = [self.data["current_assets"][i] / self.data["current_liabilities"][i] for i in range(n)]
        results["Interest_Coverage"] = [self.data["ebitda"][i] / (-self.data["interest_expense"][i]) for i in range(n)]
        
        # DuPont Checks
        results["ROE_3Step"] = [results["Net_Profit_Margin"][i] * results["Asset_Turnover"][i] * results["Assets_to_Equity"][i] for i in range(n)]
        results["ROE_3Step_Check"] = ["OK" if abs(results["ROE_3Step"][i] - results["ROE"][i]) < 0.0001 else "Error" for i in range(n)]
        results["ROE_5Step"] = [results["Tax_Burden"][i] * results["Interest_Burden"][i] * results["EBIT_Margin"][i] * results["Asset_Turnover"][i] * results["Assets_to_Equity"][i] for i in range(n)]
        results["ROE_5Step_Check"] = ["OK" if abs(results["ROE_5Step"][i] - results["ROE"][i]) < 0.0001 else "Error" for i in range(n)]
        
        # CAGR
        def cagr(start, end, periods):
            if start <= 0 or end <= 0: return 0
            return (end/start)**(1/periods) - 1
        results["ROE_CAGR"] = cagr(results["ROE"][0], results["ROE"][-1], n-1)
        results["Revenue_CAGR"] = cagr(self.data["revenue"][0], self.data["revenue"][-1], n-1)
        
        self.results = results
        return results

    def print_report(self):
        if not self.results:
            print("No data.")
            return
        r = self.results
        print("\n" + "="*80)
        print(f"DUPONT ANALYSIS: {self.data.get('company_name', 'Unknown')}")
        print("="*80)
        print(f"\nPeriod: Years {r['Year'][0]} - {r['Year'][-1]} (8 years)")
        print("\nLATEST YEAR (Year 8):")
        print(f"  ROE (Direct):     {r['ROE'][-1]:.2%}")
        print(f"  ROE (3-Step):     {r['ROE_3Step'][-1]:.2%} [{r['ROE_3Step_Check'][-1]}]")
        print(f"    = Net Margin    {r['Net_Profit_Margin'][-1]:.2%} × Asset Turnover {r['Asset_Turnover'][-1]:.3f} × Leverage {r['Assets_to_Equity'][-1]:.3f}")
        print(f"  ROE (5-Step):     {r['ROE_5Step'][-1]:.2%} [{r['ROE_5Step_Check'][-1]}]")
        print(f"    = Tax Burden {r['Tax_Burden'][-1]:.3f} × Int Burden {r['Interest_Burden'][-1]:.3f} × EBIT Margin {r['EBIT_Margin'][-1]:.2%} × AT × FL")
        print(f"\nCAGR: ROE {r['ROE_CAGR']:.2%} | Revenue {r['Revenue_CAGR']:.2%}")
        print("\n8-YEAR HISTORY:")
        df = pd.DataFrame({"Year": r["Year"], "ROE": r["ROE"], "Net_Margin": r["Net_Profit_Margin"], "Asset_Turnover": r["Asset_Turnover"], "Leverage": r["Assets_to_Equity"], "ROIC": r["ROIC"], "CCC": r["CCC"]})
        df.set_index("Year", inplace=True)
        for c in ["ROE", "Net_Margin", "ROIC"]: df[c] = df[c].apply(lambda x: f"{x:.2%}")
        for c in ["Asset_Turnover", "Leverage"]: df[c] = df[c].apply(lambda x: f"{x:.3f}")
        df["CCC"] = df["CCC"].apply(lambda x: f"{x:.1f}")
        print(df.to_string())
        print("\n" + "="*80 + "\n")

def run_analysis(ticker: Optional[str] = None) -> Optional[DuPontAnalyzer]:
    a = DuPontAnalyzer(ticker)
    if a.load_default_data():
        a.calculate_ratios()
        a.print_report()
        return a
    return None

if __name__ == "__main__":
    import sys
    t = sys.argv[1].upper() if len(sys.argv) > 1 else None
    run_analysis(t)
