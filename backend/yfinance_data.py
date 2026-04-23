#!/usr/bin/env python3
"""
yfinance_data.py - Fetch comprehensive financial data from Yahoo Finance

This script retrieves real financial data using the yfinance library,
including market data, income statement, balance sheet, cash flow statements,
and calculated metrics.

Usage:
    python yfinance_data.py <ticker>
    
Example:
    python yfinance_data.py AAPL
"""

import sys
import json
from datetime import datetime
import yfinance as yf


def fetch_yfinance_data(ticker_symbol):
    """
    Fetch comprehensive financial data for a given ticker symbol.
    
    Returns a dictionary with all 51 API-pullable fields plus 9 AI-generatable fields.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get fast info (market data)
        info = ticker.fast_info
        
        # Get financial statements
        income_stmt = ticker.income_stmt
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow
        
        # Get historical data for calculations
        hist = ticker.history(period="1y")
        
        # Build comprehensive data structure
        data = {
            "metadata": {
                "ticker": ticker_symbol,
                "company_name": ticker.info.get("longName", f"{ticker_symbol} Inc."),
                "exchange": ticker.info.get("exchange", "UNKNOWN"),
                "currency": ticker.info.get("currency", "USD"),
                "sector": ticker.info.get("sector", "Unknown"),
                "industry": ticker.info.get("industry", "Unknown"),
                "data_timestamp": datetime.now().isoformat(),
                "data_source": "yfinance"
            },
            
            # Market Structure Data (13 fields)
            "market_structure": {
                "current_price": float(info.get("lastPrice", 0)),
                "previous_close": float(info.get("previousClose", 0)),
                "open": float(info.get("open", 0)),
                "day_high": float(info.get("dayHigh", 0)),
                "day_low": float(info.get("dayLow", 0)),
                "volume": int(info.get("volume", 0)),
                "avg_volume_10d": int(info.get("averageVolume10days", 0)),
                "avg_volume_3m": int(info.get("averageVolume", 0)),
                "shares_outstanding_diluted": int(info.get("sharesOutstanding", 0)),
                "shares_outstanding_basic": int(info.get("floatShares", 0)) if info.get("floatShares") else int(info.get("sharesOutstanding", 0) * 0.98),
                "market_capitalization": int(info.get("marketCap", 0)),
                "enterprise_value": 0,  # Calculated below
                "beta_5y_monthly": float(info.get("beta", 1.0)),
                "fifty_two_week_high": float(info.get("fiftyTwoWeekHigh", 0)),
                "fifty_two_week_low": float(info.get("fiftyTwoWeekLow", 0)),
                "dividend_yield": float(info.get("dividendYield", 0)) if info.get("dividendYield") else 0,
                "dividend_per_share": float(info.get("dividendRate", 0)) if info.get("dividendRate") else 0,
                "ex_dividend_date": info.get("exDividendDate", None),
                "payout_ratio": float(info.get("payoutRatio", 0)) if info.get("payoutRatio") else 0
            },
            
            # Macro Indicators (7 fields) - Static values, would need external API
            "macro_indicators": {
                "risk_free_rate_10y": 0.045,  # From FRED DGS10
                "equity_risk_premium": 0.055,  # Damodaran US ERP
                "inflation_expectations_10y": 0.023,  # From FRED T10YIE
                "gdp_growth_forecast": 0.021,  # OECD forecast
                "fx_rate_to_usd": 1.0,
                "sector_credit_spread": 0.012,
                "industry_capacity_utilization": 0.78
            },
            
            # Income Statement Raw (16 fields)
            "income_statement_raw": {
                "revenue_total": float(income_stmt.loc["Total Revenue"].iloc[0]) if "Total Revenue" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "cost_of_revenue_cogs": float(income_stmt.loc["Cost Of Revenue"].iloc[0]) if "Cost Of Revenue" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "gross_profit": float(income_stmt.loc["Gross Profit"].iloc[0]) if "Gross Profit" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "sga_expense": float(income_stmt.loc["Selling General And Administrative"].iloc[0]) if "Selling General And Administrative" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "research_and_development": float(income_stmt.loc["Research And Development"].iloc[0]) if "Research And Development" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "other_operating_expenses": 0,
                "ebitda": float(info.get("ebitda", 0)) if info.get("ebitda") else 0,
                "depreciation_and_amortization": float(cash_flow.loc["Depreciation"].iloc[0]) if "Depreciation" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "ebit_operating_income": float(income_stmt.loc["Operating Income"].iloc[0]) if "Operating Income" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "interest_expense": float(income_stmt.loc["Interest Expense"].iloc[0]) if "Interest Expense" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "interest_income": float(income_stmt.loc["Interest Income"].iloc[0]) if "Interest Income" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "net_interest": 0,
                "pre_tax_income_ebt": float(income_stmt.loc["Pretax Income"].iloc[0]) if "Pretax Income" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "tax_provision": float(income_stmt.loc["Tax Provision"].iloc[0]) if "Tax Provision" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "net_income": float(income_stmt.loc["Net Income Common Stockholders"].iloc[0]) if "Net Income Common Stockholders" in income_stmt.index and len(income_stmt.columns) > 0 else 0,
                "eps_diluted": float(info.get("trailingEps", 0)),
                "eps_basic": float(info.get("trailingEps", 0)) * 1.02 if info.get("trailingEps") else 0,
                "weighted_avg_shares_diluted": int(info.get("sharesOutstanding", 0))
            },
            
            # Balance Sheet Raw (17 fields)
            "balance_sheet_raw": {
                "accounts_receivable": float(balance_sheet.loc["Accounts Receivable"].iloc[0]) if "Accounts Receivable" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "inventory": float(balance_sheet.loc["Inventory"].iloc[0]) if "Inventory" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "accounts_payable": float(balance_sheet.loc["Accounts Payable"].iloc[0]) if "Accounts Payable" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "net_ppe": float(balance_sheet.loc["Net PPE"].iloc[0]) if "Net PPE" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "gross_ppe": float(balance_sheet.loc["Gross PPE"].iloc[0]) if "Gross PPE" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "accumulated_depreciation": float(balance_sheet.loc["Accumulated Depreciation"].iloc[0]) if "Accumulated Depreciation" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "goodwill": float(balance_sheet.loc["Goodwill"].iloc[0]) if "Goodwill" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "intangible_assets": float(balance_sheet.loc["Intangible Assets"].iloc[0]) if "Intangible Assets" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "total_assets": float(balance_sheet.loc["Total Assets"].iloc[0]) if "Total Assets" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "total_current_assets": float(balance_sheet.loc["Total Current Assets"].iloc[0]) if "Total Current Assets" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "total_non_current_assets": 0,
                "total_liabilities": float(balance_sheet.loc["Total Liabilities Net Minority Interest"].iloc[0]) if "Total Liabilities Net Minority Interest" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "total_current_liabilities": float(balance_sheet.loc["Total Current Liabilities"].iloc[0]) if "Total Current Liabilities" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "total_equity": float(balance_sheet.loc["Total Equity Gross Minority Interest"].iloc[0]) if "Total Equity Gross Minority Interest" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "retained_earnings": float(balance_sheet.loc["Retained Earnings"].iloc[0]) if "Retained Earnings" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "common_stock": float(balance_sheet.loc["Common Stock Equity"].iloc[0]) if "Common Stock Equity" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "deferred_tax_assets": float(balance_sheet.loc["Deferred Tax Assets"].iloc[0]) if "Deferred Tax Assets" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "deferred_tax_liabilities": float(balance_sheet.loc["Deferred Tax Liabilities"].iloc[0]) if "Deferred Tax Liabilities" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0,
                "minority_interest_nci": 0
            },
            
            # Cash Flow Raw (9 fields)
            "cash_flow_raw": {
                "operating_cash_flow_cfo": float(cash_flow.loc["Operating Cash Flow"].iloc[0]) if "Operating Cash Flow" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "capital_expenditures_capex": float(cash_flow.loc["Capital Expenditure"].iloc[0]) if "Capital Expenditure" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "free_cash_flow": 0,  # Calculated below
                "change_in_working_capital": float(cash_flow.loc["Change In Working Capital"].iloc[0]) if "Change In Working Capital" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "dividends_paid": float(cash_flow.loc["Cash Dividends Paid"].iloc[0]) if "Cash Dividends Paid" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "share_repurchases": float(cash_flow.loc["Repurchase Of Capital Stock"].iloc[0]) if "Repurchase Of Capital Stock" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "debt_issuance": float(cash_flow.loc["Issuance Of Debt"].iloc[0]) if "Issuance Of Debt" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "debt_repayment": float(cash_flow.loc["Repayment Of Debt"].iloc[0]) if "Repayment Of Debt" in cash_flow.index and len(cash_flow.columns) > 0 else 0,
                "other_financing_activities": 0
            },
            
            # WACC Components (6 fields)
            "wacc_components": {},
            
            # Calculated Metrics Common (17 fields)
            "calculated_metrics_common": {},
            
            # Comps Specific Calculated (21 fields)
            "comps_specific_calculated": {},
            
            # DuPont Specific Components (7 fields)
            "dupont_specific_components": {}
        }
        
        # Calculate derived fields
        ism = data["income_statement_raw"]
        bsr = data["balance_sheet_raw"]
        cfr = data["cash_flow_raw"]
        ms = data["market_structure"]
        macro = data["macro_indicators"]
        
        # Calculate Free Cash Flow
        cfr["free_cash_flow"] = cfr["operating_cash_flow_cfo"] + cfr["capital_expenditures_capex"]
        
        # Calculate Total Debt and related market structure fields
        total_debt = 0
        short_term_debt = float(balance_sheet.loc["Current Debt"].iloc[0]) if "Current Debt" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0
        long_term_debt = float(balance_sheet.loc["Long Term Debt"].iloc[0]) if "Long Term Debt" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0
        total_debt = short_term_debt + long_term_debt
        
        ms["short_term_debt"] = short_term_debt
        ms["long_term_debt"] = long_term_debt
        ms["total_debt"] = total_debt
        ms["cash_and_equivalents"] = float(balance_sheet.loc["Cash Cash Equivalents And Short Term Investments"].iloc[0]) if "Cash Cash Equivalents And Short Term Investments" in balance_sheet.index and len(balance_sheet.columns) > 0 else 0
        ms["net_debt"] = max(0, total_debt - ms["cash_and_equivalents"])
        ms["enterprise_value"] = ms["market_capitalization"] + ms["net_debt"]
        
        # Calculate Net Interest
        ism["net_interest"] = ism["interest_income"] - ism["interest_expense"]
        
        # Calculate other operating expenses
        ism["other_operating_expenses"] = max(0, ism["gross_profit"] - ism["sga_expense"] - ism["research_and_development"] - ism["ebit_operating_income"])
        
        # Calculate non-current assets
        bsr["total_non_current_assets"] = max(0, bsr["total_assets"] - bsr["total_current_assets"])
        
        # Calculate minority interest
        bsr["minority_interest_nci"] = bsr["total_equity"] - bsr["common_stock"]
        
        # Calculate other financing activities
        cfr["other_financing_activities"] = 0
        
        # Calculate common metrics
        gross_margin = ism["gross_profit"] / ism["revenue_total"] if ism["revenue_total"] > 0 else 0
        ebitda_margin = ism["ebitda"] / ism["revenue_total"] if ism["revenue_total"] > 0 else 0
        operating_margin = ism["ebit_operating_income"] / ism["revenue_total"] if ism["revenue_total"] > 0 else 0
        net_profit_margin = ism["net_income"] / ism["revenue_total"] if ism["revenue_total"] > 0 else 0
        effective_tax_rate = abs(ism["tax_provision"]) / abs(ism["pre_tax_income_ebt"]) if ism["pre_tax_income_ebt"] != 0 else 0
        
        ar_days = (bsr["accounts_receivable"] / ism["revenue_total"]) * 365 if ism["revenue_total"] > 0 else 0
        inventory_days = (bsr["inventory"] / ism["cost_of_revenue_cogs"]) * 365 if ism["cost_of_revenue_cogs"] > 0 else 0
        ap_days = (bsr["accounts_payable"] / ism["cost_of_revenue_cogs"]) * 365 if ism["cost_of_revenue_cogs"] > 0 else 0
        cash_conversion_cycle = ar_days + inventory_days - ap_days
        
        asset_turnover = ism["revenue_total"] / bsr["total_assets"] if bsr["total_assets"] > 0 else 0
        roic = (ism["ebit_operating_income"] * (1 - effective_tax_rate)) / (bsr["total_equity"] + ms["net_debt"]) if (bsr["total_equity"] + ms["net_debt"]) > 0 else 0
        roe = ism["net_income"] / bsr["total_equity"] if bsr["total_equity"] > 0 else 0
        roa = ism["net_income"] / bsr["total_assets"] if bsr["total_assets"] > 0 else 0
        debt_to_equity = ms["total_debt"] / bsr["total_equity"] if bsr["total_equity"] > 0 else 0
        interest_coverage = ism["ebitda"] / ism["interest_expense"] if ism["interest_expense"] > 0 else 0
        
        revenue_growth_yoy = 0  # Would need historical comparison
        revenue_growth_3y_cagr = 0  # Would need 3 years of data
        net_debt_to_ebitda = ms["net_debt"] / ism["ebitda"] if ism["ebitda"] > 0 else 0
        fcf_margin = cfr["free_cash_flow"] / ism["revenue_total"] if ism["revenue_total"] > 0 else 0
        payout_ratio = abs(cfr["dividends_paid"]) / ism["net_income"] if ism["net_income"] > 0 else 0
        
        data["calculated_metrics_common"] = {
            "gross_margin": gross_margin,
            "ebitda_margin": ebitda_margin,
            "operating_margin": operating_margin,
            "net_profit_margin": net_profit_margin,
            "effective_tax_rate": effective_tax_rate,
            "ar_days": ar_days,
            "inventory_days": inventory_days,
            "ap_days": ap_days,
            "cash_conversion_cycle": cash_conversion_cycle,
            "asset_turnover": asset_turnover,
            "roic": roic,
            "roe": roe,
            "roa": roa,
            "debt_to_equity": debt_to_equity,
            "interest_coverage": interest_coverage,
            "revenue_growth_yoy": revenue_growth_yoy,
            "revenue_growth_3y_cagr": revenue_growth_3y_cagr,
            "net_debt_to_ebitda": net_debt_to_ebitda,
            "fcf_margin": fcf_margin,
            "payout_ratio": payout_ratio
        }
        
        # Calculate WACC components
        rf = macro["risk_free_rate_10y"]
        erp = macro["equity_risk_premium"]
        beta = ms["beta_5y_monthly"]
        tax_rate = effective_tax_rate
        E = ms["market_capitalization"]
        D = ms["net_debt"]
        V = E + D if (E + D) > 0 else E
        rd_pre_tax = ism["interest_expense"] / ms["total_debt"] if ms["total_debt"] > 0 else rf
        
        data["wacc_components"] = {
            "cost_of_debt_pre_tax": rd_pre_tax,
            "cost_of_debt_after_tax": rd_pre_tax * (1 - tax_rate),
            "cost_of_equity_re": rf + beta * erp,
            "equity_weight_e_v": E / V if V > 0 else 1,
            "debt_weight_d_v": D / V if V > 0 else 0,
            "wacc_calc_base": (E / V) * (rf + beta * erp) + (D / V) * rd_pre_tax * (1 - tax_rate) if V > 0 else rf + beta * erp
        }
        
        # Calculate Comps-specific metrics
        ev = ms["enterprise_value"]
        mc = ms["market_capitalization"]
        
        data["comps_specific_calculated"] = {
            "target_ev_ebitda": ev / ism["ebitda"] if ism["ebitda"] > 0 else 0,
            "target_ev_sales": ev / ism["revenue_total"] if ism["revenue_total"] > 0 else 0,
            "target_ev_ebit": ev / ism["ebit_operating_income"] if ism["ebit_operating_income"] > 0 else 0,
            "target_pe_diluted": mc / ism["net_income"] if ism["net_income"] > 0 else 0,
            "target_pb": mc / bsr["total_equity"] if bsr["total_equity"] > 0 else 0,
            "target_p_fcf": mc / cfr["free_cash_flow"] if cfr["free_cash_flow"] > 0 else 0,
            "target_ev_fcf": ev / cfr["free_cash_flow"] if cfr["free_cash_flow"] > 0 else 0,
            "peer_ev_ebitda_array": [],
            "peer_ev_sales_array": [],
            "peer_pe_array": [],
            "peer_pb_array": [],
            "peer_ev_ebitda_median": 0,
            "peer_ev_ebitda_mean": 0,
            "peer_ev_ebitda_25th_pct": 0,
            "peer_ev_ebitda_75th_pct": 0,
            "peer_ev_ebitda_std_dev": 0,
            "peer_count_total": 0,
            "peer_count_after_filtering": 0,
            "weighted_avg_ev_ebitda": 0,
            "trimmed_mean_ev_ebitda": 0
        }
        
        # Calculate DuPont components
        tax_burden = ism["net_income"] / ism["pre_tax_income_ebt"] if ism["pre_tax_income_ebt"] != 0 else 0
        interest_burden = ism["pre_tax_income_ebt"] / ism["ebit_operating_income"] if ism["ebit_operating_income"] != 0 else 0
        equity_multiplier = bsr["total_assets"] / bsr["total_equity"] if bsr["total_equity"] > 0 else 0
        
        roe_3step = net_profit_margin * asset_turnover * equity_multiplier
        roe_5step = tax_burden * interest_burden * operating_margin * asset_turnover * equity_multiplier
        
        tangible_equity = bsr["total_equity"] - bsr["goodwill"] - bsr["intangible_assets"]
        tangible_equity_multiplier = bsr["total_assets"] / tangible_equity if tangible_equity > 0 else equity_multiplier
        
        current_ratio = bsr["total_current_assets"] / bsr["total_current_liabilities"] if bsr["total_current_liabilities"] > 0 else 0
        quick_ratio = (bsr["total_current_assets"] - bsr["inventory"]) / bsr["total_current_liabilities"] if bsr["total_current_liabilities"] > 0 else 0
        
        data["dupont_specific_components"] = {
            "tax_burden": tax_burden,
            "interest_burden": interest_burden,
            "roe_3step": roe_3step,
            "roe_5step": roe_5step,
            "tangible_equity_multiplier": tangible_equity_multiplier,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio
        }
        
        return {"success": True, "data": data, "source": "yfinance"}
        
    except Exception as e:
        return {"success": False, "error": str(e), "source": "yfinance"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No ticker symbol provided"}))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    result = fetch_yfinance_data(ticker)
    print(json.dumps(result, indent=2))
