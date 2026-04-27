#!/usr/bin/env python3
"""
DuPont Analysis Model - 8 Year Trend Analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DuPontAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.data = {}
        
    def fetch_data(self, years=8):
        try:
            info = self.stock.info
            self.data["company_name"] = info.get("longName", self.ticker)
            self.data["currency"] = info.get("currency", "USD")
            
            income_stmt = self.stock.financials
            balance_sheet = self.stock.balance_sheet
            cash_flow = self.stock.cashflow
            
            if income_stmt.empty or balance_sheet.empty:
                return False
            
            dates = income_stmt.columns[:years]
            self.data["years"] = [d.year for d in reversed(dates)]
            
            def get_item(stmt, names, default=0):
                for n in names:
                    if n in stmt.index:
                        s = stmt.loc[n]
                        return [float(s[d]) if pd.notna(s.get(d)) else default for d in reversed(dates)]
                return [default] * len(dates)
            
            self.data["revenue"] = get_item(income_stmt, ["Total Revenue", "Revenue"])
            self.data["net_income"] = get_item(income_stmt, ["Net Income Common Stockholders", "Net Income"])
            self.data["ebit"] = get_item(income_stmt, ["Operating Income", "EBIT"])
            self.data["ebt"] = get_item(income_stmt, ["Pretax Income", "Income Before Tax"])
            self.data["total_assets"] = get_item(balance_sheet, ["Total Assets"])
            self.data["total_equity"] = get_item(balance_sheet, ["Total Stockholders Equity", "Equity"])
            self.data["long_term_debt"] = get_item(balance_sheet, ["Long Term Debt"], 0)
            self.data["short_term_debt"] = get_item(balance_sheet, ["Short Term Debt"], 0)
            self.data["current_assets"] = get_item(balance_sheet, ["Current Assets"])
            self.data["current_liabilities"] = get_item(balance_sheet, ["Current Liabilities"])
            
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    
    def calculate(self):
        n = len(self.data["years"])
        results = {"Year": self.data["years"]}
        
        roe_3step, net_margin, asset_turn, fin_lev = [], [], [], []
        roe_5step, tax_burden, int_burden, op_margin = [], [], [], []
        roa_list, gross_margin, dte_ratio = [], [], []
        
        for i in range(n):
            rev = self.data["revenue"][i] or 1
            ni = self.data["net_income"][i] or 0
            assets = self.data["total_assets"][i] or 1
            equity = self.data["total_equity"][i] or 1
            ebit = self.data["ebit"][i] or 1
            ebt = self.data["ebt"][i] or 1
            
            avg_assets = (assets + self.data["total_assets"][i-1])/2 if i > 0 else assets
            avg_equity = (equity + self.data["total_equity"][i-1])/2 if i > 0 else equity
            if avg_assets == 0: avg_assets = 1
            if avg_equity == 0: avg_equity = 1
            
            nm = ni/rev
            at = rev/avg_assets
            fl = avg_assets/avg_equity
            roe3 = nm * at * fl
            
            tb = ni/ebt if ebt != 0 else 0
            ib = ebt/ebit if ebit != 0 else 0
            om = ebit/rev
            roe5 = tb * ib * om * at * fl
            
            roe_3step.append(roe3)
            net_margin.append(nm)
            asset_turn.append(at)
            fin_lev.append(fl)
            roe_5step.append(roe5)
            tax_burden.append(tb)
            int_burden.append(ib)
            op_margin.append(om)
            roa_list.append(ni/avg_assets)
        
        # CAGR calc
        def cagr(start, end, periods):
            if start <= 0 or end <= 0: return 0
            return (end/start)**(1/periods) - 1
        
        periods = self.data["years"][-1] - self.data["years"][0] or 1
        roe_cagr = cagr(roe_3step[0], roe_3step[-1], periods)
        rev_cagr = cagr(self.data["revenue"][0], self.data["revenue"][-1], periods)
        
        results["ROE_3Step"] = roe_3step
        results["Net_Margin"] = net_margin
        results["Asset_Turnover"] = asset_turn
        results["Fin_Leverage"] = fin_lev
        results["ROE_5Step"] = roe_5step
        results["Tax_Burden"] = tax_burden
        results["Int_Burden"] = int_burden
        results["Op_Margin"] = op_margin
        results["ROA"] = roa_list
        results["ROE_CAGR"] = roe_cagr
        results["Rev_CAGR"] = rev_cagr
        
        self.results = results
        return results
    
    def print_report(self):
        if not self.results:
            print("No data. Run fetch and calculate first.")
            return
        
        r = self.results
        print("\n" + "="*70)
        print(f"DUPONT ANALYSIS: {self.ticker} - {self.data.get('company_name','')}")
        print("="*70)
        print(f"\nPeriod: {r['Year'][0]} - {r['Year'][-1]} ({len(r['Year'])} years)")
        
        print("\nLATEST YEAR METRICS:")
        print(f"  ROE (3-Step): {r['ROE_3Step'][-1]:.2%}")
        print(f"  = Net Margin ({r['Net_Margin'][-1]:.2%}) x Asset Turnover ({r['Asset_Turnover'][-1]:.3f}) x Leverage ({r['Fin_Leverage'][-1]:.3f})")
        
        print(f"\nROE (5-Step): {r['ROE_5Step'][-1]:.2%}")
        print(f"  = Tax Burden ({r['Tax_Burden'][-1]:.3f}) x Int Burden ({r['Int_Burden'][-1]:.3f}) x Op Margin ({r['Op_Margin'][-1]:.2%}) x AT x FL")
        
        print(f"\nTRENDS:")
        print(f"  ROE CAGR: {r['ROE_CAGR']:.2%}")
        print(f"  Revenue CAGR: {r['Rev_CAGR']:.2%}")
        
        print("\nHISTORICAL DATA:")
        df = pd.DataFrame(r)
        df.set_index("Year", inplace=True)
        cols = ["ROE_3Step", "Net_Margin", "Asset_Turnover", "Fin_Leverage", "ROE_5Step", "Op_Margin", "ROA"]
        for c in cols:
            if c in df.columns:
                df[c] = df[c].apply(lambda x: f"{x:.2%}" if "Margin" in c or "ROE" in c or "ROA" in c or "Burden" in c else f"{x:.3f}")
        print(df[cols].to_string())
        print("\n" + "="*70)


def run_analysis(ticker, years=8):
    a = DuPontAnalyzer(ticker)
    if a.fetch_data(years):
        a.calculate()
        a.print_report()
        return a
    return None


if __name__ == "__main__":
    import sys
    t = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
    run_analysis(t)
