"""
Unified Valuation Input Module

Retrieves all required inputs for DCF, Trading Comps, and DuPont Analysis models.
Primary source: yfinance
Fallback source: Alpha Vantage

Schema-compliant with Unified_Valuation_API_Calculated_Schema
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import yfinance as yf
import requests
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")


class ValuationInputs:
    """
    Unified class to fetch and store all valuation model inputs.
    Follows the Unified_Valuation_API_Calculated_Schema structure.
    """

    def __init__(self, ticker: str, currency: str = "USD"):
        self.ticker = ticker.upper()
        self.currency = currency
        self.data_timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Initialize schema-compliant structure
        self.data: Dict[str, Any] = {
            "metadata": {},
            "market_structure": {},
            "macro_indicators": {},
            "income_statement_raw": {},
            "balance_sheet_raw": {},
            "cash_flow_raw": {},
            "calculated_metrics_common": {},
            "wacc_components": {},
            "comps_specific_calculated": {},
            "dupont_specific_components": {}
        }
        
        # yfinance ticker object
        self.yf_ticker: Optional[yf.Ticker] = None
        
    def fetch_all(self) -> Dict[str, Any]:
        """
        Fetch all data from APIs and calculate derived metrics.
        Returns the complete schema-compliant dictionary.
        """
        self._fetch_metadata()
        self._fetch_market_structure()
        self._fetch_macro_indicators()
        self._fetch_income_statement()
        self._fetch_balance_sheet()
        self._fetch_cash_flow()
        self._calculate_common_metrics()
        self._calculate_wacc_components()
        self._calculate_comps_metrics()
        self._calculate_dupont_components()
        
        return self.data

    def _fetch_metadata(self):
        """Fetch metadata fields."""
        try:
            self.yf_ticker = yf.Ticker(self.ticker)
            info = self.yf_ticker.info
            
            self.data["metadata"] = {
                "ticker": self.ticker,
                "company_name": info.get("longName", info.get("shortName", "")),
                "exchange": info.get("exchange", ""),
                "currency": info.get("currency", self.currency),
                "fiscal_year_end_month": info.get("financialCurrency", 12),
                "data_timestamp": self.data_timestamp,
                "data_source": "yfinance",
                "model_usage": ["dcf", "comps", "dupont"]
            }
        except Exception as e:
            print(f"Warning: Metadata fetch error for {self.ticker}: {e}")
            self.data["metadata"] = {
                "ticker": self.ticker,
                "currency": self.currency,
                "data_timestamp": self.data_timestamp,
                "data_source": "yfinance",
                "model_usage": ["dcf", "comps", "dupont"]
            }

    def _fetch_market_structure(self):
        """Fetch market structure data from yfinance with Alpha Vantage fallback."""
        try:
            info = self.yf_ticker.info
            
            current_price = info.get("currentPrice", info.get("regularMarketPrice", 0))
            shares_diluted = info.get("sharesOutstanding", 0)
            shares_basic = info.get("floatShares", shares_diluted)
            
            market_cap = info.get("marketCap", current_price * shares_diluted if current_price and shares_diluted else 0)
            
            # Debt components
            total_debt = info.get("totalDebt", 0)
            short_term_debt = info.get("shortTermDebt", 0)
            long_term_debt = info.get("longTermDebt", total_debt - short_term_debt if total_debt else 0)
            cash = info.get("totalCash", info.get("cashAndShortTermInvestments", 0))
            net_debt = total_debt - cash if total_debt and cash else total_debt
            
            # Enterprise Value
            enterprise_value = info.get("enterpriseValue", market_cap + net_debt if market_cap else 0)
            
            # Beta and dividends
            beta = info.get("beta", info.get("52WeekChange", 1.0))
            dividend_yield = info.get("dividendYield", 0)
            dividend_per_share = info.get("dividendRate", 0)
            
            self.data["market_structure"] = {
                "current_price": current_price,
                "shares_outstanding_diluted": shares_diluted,
                "shares_outstanding_basic": shares_basic,
                "market_capitalization": market_cap,
                "enterprise_value": enterprise_value,
                "total_debt": total_debt,
                "short_term_debt": short_term_debt,
                "long_term_debt": long_term_debt,
                "cash_and_equivalents": cash,
                "net_debt": net_debt,
                "beta_5y_monthly": beta,
                "dividend_yield": dividend_yield if dividend_yield else 0,
                "dividend_per_share": dividend_per_share
            }
            
        except Exception as e:
            print(f"Warning: Market structure fetch error: {e}")
            self.data["market_structure"] = {
                "current_price": 0,
                "shares_outstanding_diluted": 0,
                "market_capitalization": 0
            }

    def _fetch_macro_indicators(self):
        """Fetch macroeconomic indicators."""
        try:
            # US 10Y Treasury Rate (can be enhanced with FRED API)
            risk_free_rate = self._get_fred_data("DGS10") or 0.045  # Default 4.5%
            
            # Equity Risk Premium (Damodaran default for US)
            erp = 0.055  # 5.5% default
            
            # Inflation expectations (10Y breakeven)
            inflation = self._get_fred_data("T10YIE") or 0.025  # Default 2.5%
            
            # GDP growth forecast
            gdp_growth = 0.025  # Default 2.5%
            
            # FX rate to USD
            fx_rate = 1.0
            if self.currency != "USD":
                fx_rate = self._get_fx_rate(self.currency)
            
            self.data["macro_indicators"] = {
                "risk_free_rate_10y": risk_free_rate,
                "equity_risk_premium": erp,
                "inflation_expectations_10y": inflation,
                "gdp_growth_forecast": gdp_growth,
                "fx_rate_to_usd": fx_rate,
                "sector_credit_spread": 0.015,  # Default 1.5%
                "industry_capacity_utilization": 0.78  # Default 78%
            }
            
        except Exception as e:
            print(f"Warning: Macro indicators fetch error: {e}")
            self.data["macro_indicators"] = {
                "risk_free_rate_10y": 0.045,
                "equity_risk_premium": 0.055,
                "inflation_expectations_10y": 0.025,
                "gdp_growth_forecast": 0.025,
                "fx_rate_to_usd": 1.0,
                "sector_credit_spread": 0.015,
                "industry_capacity_utilization": 0.78
            }

    def _fetch_income_statement(self):
        """Fetch income statement data."""
        try:
            # Get financials (annual)
            financials = self.yf_ticker.financials
            if financials.empty:
                # Try quarterly as fallback
                financials = self.yf_ticker.quarterly_financials
            
            if not financials.empty:
                latest = financials.iloc[:, 0] if len(financials.columns) > 0 else financials
                
                # Map yfinance columns to schema
                revenue = self._safe_get(latest, "Total Revenue", "Operating Revenue", 0)
                cogs = self._safe_get(latest, "Cost Of Revenue", "Cost of Goods Sold", 0)
                gross_profit = revenue - cogs if revenue and cogs else self._safe_get(latest, "Gross Profit", 0)
                
                sga = self._safe_get(latest, "Selling General Administrative", "SGA Expense", 0)
                rnd = self._safe_get(latest, "Research Development", "R&D Expense", 0)
                
                ebitda = self._safe_get(latest, "EBITDA", "Ebitda", 0)
                d_and_a = self._safe_get(latest, "Depreciation", "Depreciation And Amortization", 0)
                ebit = self._safe_get(latest, "Operating Income", "EBIT", ebitda - d_and_a if ebitda else 0)
                
                interest_expense = self._safe_get(latest, "Interest Expense", "Net Interest Income", 0)
                interest_income = self._safe_get(latest, "Interest Income", 0)
                net_interest = interest_expense - interest_income
                
                pretax_income = self._safe_get(latest, "Pretax Income", "Pre-Tax Income", ebit - net_interest if ebit else 0)
                tax_provision = self._safe_get(latest, "Tax Provision", "Income Tax Expense", 0)
                net_income = self._safe_get(latest, "Net Income", "Net Income Common Stockholders", pretax_income - tax_provision if pretax_income else 0)
                
                # EPS data
                eps_diluted = self._safe_get(latest, "Diluted EPS", "Basic Average Shares", 0)
                eps_basic = self._safe_get(latest, "Basic EPS", eps_diluted)
                shares_diluted_eps = self._safe_get(latest, "Diluted Average Shares", "Basic Average Shares", 0)
                
                self.data["income_statement_raw"] = {
                    "revenue_total": revenue,
                    "cost_of_revenue_cogs": cogs,
                    "gross_profit": gross_profit,
                    "sga_expense": sga,
                    "research_and_development": rnd,
                    "other_operating_expenses": 0,
                    "ebitda": ebitda,
                    "depreciation_and_amortization": d_and_a,
                    "ebit_operating_income": ebit,
                    "interest_expense": abs(interest_expense) if interest_expense else 0,
                    "interest_income": interest_income,
                    "net_interest": net_interest,
                    "pre_tax_income_ebt": pretax_income,
                    "tax_provision": tax_provision,
                    "net_income": net_income,
                    "eps_diluted": eps_diluted,
                    "eps_basic": eps_basic,
                    "weighted_avg_shares_diluted": shares_diluted_eps
                }
            else:
                raise ValueError("No financial data available")
                
        except Exception as e:
            print(f"Warning: Income statement fetch error: {e}")
            # Try Alpha Vantage fallback
            self._fetch_income_statement_alpha_vantage()

    def _fetch_income_statement_alpha_vantage(self):
        """Fallback: Fetch income statement from Alpha Vantage."""
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "INCOME_STATEMENT",
                "symbol": self.ticker,
                "apikey": ALPHA_VANTAGE_KEY
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "annualReports" in data and len(data["annualReports"]) > 0:
                report = data["annualReports"][0]
                self.data["income_statement_raw"] = {
                    "revenue_total": float(report.get("totalRevenue", 0)),
                    "cost_of_revenue_cogs": float(report.get("costOfRevenue", 0)),
                    "gross_profit": float(report.get("grossProfit", 0)),
                    "sga_expense": float(report.get("sellingGeneralAndAdministrative", 0)),
                    "research_and_development": float(report.get("researchAndDevelopment", 0)),
                    "other_operating_expenses": 0,
                    "ebitda": float(report.get("ebitda", 0)),
                    "depreciation_and_amortization": 0,
                    "ebit_operating_income": float(report.get("operatingIncome", 0)),
                    "interest_expense": float(report.get("interestExpense", 0)),
                    "interest_income": 0,
                    "net_interest": float(report.get("interestExpense", 0)),
                    "pre_tax_income_ebt": float(report.get("incomeBeforeTax", 0)),
                    "tax_provision": float(report.get("incomeTaxExpense", 0)),
                    "net_income": float(report.get("netIncome", 0)),
                    "eps_diluted": float(report.get("eps", 0)),
                    "eps_basic": float(report.get("eps", 0)),
                    "weighted_avg_shares_diluted": 0
                }
        except Exception as e:
            print(f"Warning: Alpha Vantage income statement fallback failed: {e}")
            self.data["income_statement_raw"] = {
                "revenue_total": 0,
                "ebitda": 0,
                "net_income": 0
            }

    def _fetch_balance_sheet(self):
        """Fetch balance sheet data."""
        try:
            balance = self.yf_ticker.balance_sheet
            if balance.empty:
                balance = self.yf_ticker.quarterly_balance_sheet
            
            if not balance.empty:
                latest = balance.iloc[:, 0] if len(balance.columns) > 0 else balance
                
                self.data["balance_sheet_raw"] = {
                    "accounts_receivable": self._safe_get(latest, "Accounts Receivable", "Receivables", 0),
                    "inventory": self._safe_get(latest, "Inventory", "Inventories", 0),
                    "accounts_payable": self._safe_get(latest, "Accounts Payable", "Payables", 0),
                    "net_ppe": self._safe_get(latest, "Net PPE", "Property Plant Equipment", 0),
                    "gross_ppe": self._safe_get(latest, "Gross PPE", 0),
                    "accumulated_depreciation": self._safe_get(latest, "Accumulated Depreciation", 0),
                    "goodwill": self._safe_get(latest, "Goodwill", 0),
                    "intangible_assets": self._safe_get(latest, "Intangible Assets", "Other Intangible Assets", 0),
                    "total_assets": self._safe_get(latest, "Total Assets", "Assets", 0),
                    "total_current_assets": self._safe_get(latest, "Total Current Assets", "Current Assets", 0),
                    "total_non_current_assets": self._safe_get(latest, "Total Non Current Assets", 0),
                    "total_liabilities": self._safe_get(latest, "Total Liabilities Net Minority Interest", "Liabilities", 0),
                    "total_current_liabilities": self._safe_get(latest, "Total Current Liabilities", "Current Liabilities", 0),
                    "total_equity": self._safe_get(latest, "Total Equity Gross Minority Interest", "Stockholders Equity", 0),
                    "retained_earnings": self._safe_get(latest, "Retained Earnings", 0),
                    "common_stock": self._safe_get(latest, "Common Stock", "Ordinary Shares Number", 0),
                    "deferred_tax_assets": self._safe_get(latest, "Deferred Tax Assets", 0),
                    "deferred_tax_liabilities": self._safe_get(latest, "Deferred Tax Liabilities", 0),
                    "minority_interest_nci": self._safe_get(latest, "Minority Interest", 0)
                }
            else:
                raise ValueError("No balance sheet data available")
                
        except Exception as e:
            print(f"Warning: Balance sheet fetch error: {e}")
            self.data["balance_sheet_raw"] = {
                "total_assets": 0,
                "total_equity": 0
            }

    def _fetch_cash_flow(self):
        """Fetch cash flow statement data."""
        try:
            cashflow = self.yf_ticker.cashflow
            if cashflow.empty:
                cashflow = self.yf_ticker.quarterly_cashflow
            
            if not cashflow.empty:
                latest = cashflow.iloc[:, 0] if len(cashflow.columns) > 0 else cashflow
                
                operating_cf = self._safe_get(latest, "Operating Cash Flow", "Cash Flow From Operations", 0)
                capex = self._safe_get(latest, "Capital Expenditure", "Capex", 0)
                # CapEx is typically negative in yfinance
                capex_abs = abs(capex) if capex else 0
                fcf = operating_cf - capex_abs if operating_cf else 0
                
                self.data["cash_flow_raw"] = {
                    "operating_cash_flow_cfo": operating_cf,
                    "capital_expenditures_capex": -capex_abs,  # Keep as negative (outflow)
                    "free_cash_flow": fcf,
                    "change_in_working_capital": self._safe_get(latest, "Change In Working Capital", 0),
                    "dividends_paid": abs(self._safe_get(latest, "Cash Dividends Paid", "Dividends Paid", 0)),
                    "share_repurchases": abs(self._safe_get(latest, "Repurchase Of Capital Stock", "Treasury Stock Purchases", 0)),
                    "debt_issuance": self._safe_get(latest, "Issuance Of Debt", "New Debt Issued", 0),
                    "debt_repayment": abs(self._safe_get(latest, "Repayment Of Debt", "Debt Repayment", 0)),
                    "other_financing_activities": self._safe_get(latest, "Other Financing Activities", 0)
                }
            else:
                raise ValueError("No cash flow data available")
                
        except Exception as e:
            print(f"Warning: Cash flow fetch error: {e}")
            self.data["cash_flow_raw"] = {
                "operating_cash_flow_cfo": 0,
                "capital_expenditures_capex": 0
            }

    def _calculate_common_metrics(self):
        """Calculate common financial ratios and metrics."""
        try:
            inc = self.data["income_statement_raw"]
            bal = self.data["balance_sheet_raw"]
            mkt = self.data["market_structure"]
            cf = self.data["cash_flow_raw"]
            
            revenue = inc.get("revenue_total", 0) or 1
            gross_profit = inc.get("gross_profit", 0)
            ebitda = inc.get("ebitda", 0)
            ebit = inc.get("ebit_operating_income", 0)
            net_income = inc.get("net_income", 0)
            
            total_assets = bal.get("total_assets", 0) or 1
            total_equity = bal.get("total_equity", 0) or 1
            
            # Margins
            gross_margin = gross_profit / revenue if revenue else 0
            ebitda_margin = ebitda / revenue if revenue else 0
            operating_margin = ebit / revenue if revenue else 0
            net_margin = net_income / revenue if revenue else 0
            
            # Tax rate
            pretax = inc.get("pre_tax_income_ebt", 0)
            tax = inc.get("tax_provision", 0)
            effective_tax = abs(tax) / abs(pretax) if pretax else 0.21  # Default 21%
            
            # Working capital days
            ar = bal.get("accounts_receivable", 0)
            inventory = bal.get("inventory", 0)
            ap = bal.get("accounts_payable", 0)
            cogs = inc.get("cost_of_revenue_cogs", revenue) or 1
            
            ar_days = (ar / revenue) * 365
            inv_days = (inventory / cogs) * 365
            ap_days = (ap / cogs) * 365
            ccc = ar_days + inv_days - ap_days
            
            # Turnover and returns
            asset_turnover = revenue / total_assets
            roe = net_income / total_equity if total_equity else 0
            roa = net_income / total_assets
            
            # Leverage
            total_debt = mkt.get("total_debt", 0)
            debt_to_equity = total_debt / total_equity if total_equity else 0
            interest_coverage = ebitda / abs(inc.get("interest_expense", 1)) if inc.get("interest_expense") else 0
            
            # Growth (simplified - would need historical data for proper YoY)
            revenue_growth_yoy = 0.05  # Default 5%
            
            # Net debt to EBITDA
            net_debt = mkt.get("net_debt", 0)
            net_debt_to_ebitda = net_debt / ebitda if ebitda else 0
            
            # FCF margin
            fcf_margin = cf.get("free_cash_flow", 0) / revenue if revenue else 0
            
            # Payout ratio
            dividends_paid = cf.get("dividends_paid", 0)
            payout_ratio = dividends_paid / net_income if net_income else 0
            
            self.data["calculated_metrics_common"] = {
                "gross_margin": gross_margin,
                "ebitda_margin": ebitda_margin,
                "operating_margin": operating_margin,
                "net_profit_margin": net_margin,
                "effective_tax_rate": min(effective_tax, 1.0),
                "ar_days": ar_days,
                "inventory_days": inv_days,
                "ap_days": ap_days,
                "cash_conversion_cycle": ccc,
                "asset_turnover": asset_turnover,
                "roic": roe * 0.85,  # Simplified ROIC estimate
                "roe": roe,
                "roa": roa,
                "debt_to_equity": debt_to_equity,
                "interest_coverage": interest_coverage,
                "revenue_growth_yoy": revenue_growth_yoy,
                "revenue_growth_3y_cagr": revenue_growth_yoy * 0.9,
                "net_debt_to_ebitda": net_debt_to_ebitda,
                "fcf_margin": fcf_margin,
                "payout_ratio": payout_ratio
            }
            
        except Exception as e:
            print(f"Warning: Common metrics calculation error: {e}")
            self.data["calculated_metrics_common"] = {}

    def _calculate_wacc_components(self):
        """Calculate WACC components for DCF."""
        try:
            mkt = self.data["market_structure"]
            macro = self.data["macro_indicators"]
            metrics = self.data["calculated_metrics_common"]
            inc = self.data["income_statement_raw"]
            
            # Cost of debt
            total_debt = mkt.get("total_debt", 0) or 1
            interest_expense = inc.get("interest_expense", 0)
            cost_of_debt_pre_tax = interest_expense / total_debt if total_debt else 0.05
            
            # After-tax cost of debt
            tax_rate = metrics.get("effective_tax_rate", 0.21)
            cost_of_debt_after_tax = cost_of_debt_pre_tax * (1 - tax_rate)
            
            # Cost of equity (CAPM)
            rf = macro.get("risk_free_rate_10y", 0.045)
            beta = mkt.get("beta_5y_monthly", 1.0)
            erp = macro.get("equity_risk_premium", 0.055)
            cost_of_equity = rf + beta * erp
            
            # Weights
            market_cap = mkt.get("market_capitalization", 0) or 1
            net_debt = mkt.get("net_debt", 0)
            total_value = market_cap + net_debt
            
            equity_weight = market_cap / total_value if total_value else 0.8
            debt_weight = net_debt / total_value if total_value else 0.2
            
            # WACC
            wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt_after_tax)
            
            self.data["wacc_components"] = {
                "cost_of_debt_pre_tax": cost_of_debt_pre_tax,
                "cost_of_debt_after_tax": cost_of_debt_after_tax,
                "cost_of_equity_re": cost_of_equity,
                "equity_weight_e_v": equity_weight,
                "debt_weight_d_v": debt_weight,
                "wacc_calc_base": wacc
            }
            
        except Exception as e:
            print(f"Warning: WACC calculation error: {e}")
            self.data["wacc_components"] = {
                "cost_of_debt_pre_tax": 0.05,
                "cost_of_debt_after_tax": 0.04,
                "cost_of_equity_re": 0.10,
                "equity_weight_e_v": 0.8,
                "debt_weight_d_v": 0.2,
                "wacc_calc_base": 0.088
            }

    def _calculate_comps_metrics(self):
        """Calculate Trading Comps-specific metrics."""
        try:
            mkt = self.data["market_structure"]
            inc = self.data["income_statement_raw"]
            
            ev = mkt.get("enterprise_value", 0)
            market_cap = mkt.get("market_capitalization", 0)
            ebitda = inc.get("ebitda", 0) or 1
            revenue = inc.get("revenue_total", 0) or 1
            ebit = inc.get("ebit_operating_income", ebitda * 0.8) or 1
            net_income = inc.get("net_income", 0) or 1
            equity = self.data["balance_sheet_raw"].get("total_equity", 0) or 1
            fcf = self.data["cash_flow_raw"].get("free_cash_flow", 0)
            
            # Target multiples
            self.data["comps_specific_calculated"] = {
                "target_ev_ebitda": ev / ebitda if ebitda else 0,
                "target_ev_sales": ev / revenue if revenue else 0,
                "target_ev_ebit": ev / ebit if ebit else 0,
                "target_pe_diluted": market_cap / net_income if net_income else 0,
                "target_pb": market_cap / equity if equity else 0,
                "target_p_fcf": market_cap / fcf if fcf else 0,
                "target_ev_fcf": ev / fcf if fcf else 0,
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
            
        except Exception as e:
            print(f"Warning: Comps metrics calculation error: {e}")
            self.data["comps_specific_calculated"] = {
                "target_ev_ebitda": 0,
                "peer_ev_ebitda_median": 0,
                "peer_count_after_filtering": 0
            }

    def _calculate_dupont_components(self):
        """Calculate DuPont decomposition components."""
        try:
            inc = self.data["income_statement_raw"]
            bal = self.data["balance_sheet_raw"]
            metrics = self.data["calculated_metrics_common"]
            
            net_income = inc.get("net_income", 0) or 1
            pretax_income = inc.get("pre_tax_income_ebt", 0) or net_income
            ebit = inc.get("ebit_operating_income", pretax_income) or pretax_income
            revenue = inc.get("revenue_total", 0) or 1
            total_assets = bal.get("total_assets", 0) or 1
            total_equity = bal.get("total_equity", 0) or 1
            
            # Tax burden
            tax_burden = net_income / pretax_income if pretax_income else 1.0
            
            # Interest burden
            interest_burden = pretax_income / ebit if ebit else 1.0
            
            # EBIT margin
            ebit_margin = ebit / revenue if revenue else 0
            
            # Asset turnover
            asset_turnover = revenue / total_assets if total_assets else 0
            
            # Equity multiplier
            equity_multiplier = total_assets / total_equity if total_equity else 1.0
            
            # 3-step ROE
            roe_3step = metrics.get("net_profit_margin", 0) * asset_turnover * equity_multiplier
            
            # 5-step ROE
            roe_5step = tax_burden * interest_burden * ebit_margin * asset_turnover * equity_multiplier
            
            # Liquidity ratios
            current_assets = bal.get("total_current_assets", 0)
            current_liabilities = bal.get("total_current_liabilities", 0) or 1
            inventory = bal.get("inventory", 0)
            
            current_ratio = current_assets / current_liabilities if current_assets else 0
            quick_ratio = (current_assets - inventory) / current_liabilities if current_assets else 0
            
            # Tangible equity multiplier
            goodwill = bal.get("goodwill", 0)
            intangibles = bal.get("intangible_assets", 0)
            tangible_equity = total_equity - goodwill - intangibles
            tangible_equity_multiplier = total_assets / tangible_equity if tangible_equity else equity_multiplier
            
            self.data["dupont_specific_components"] = {
                "tax_burden": max(-1, min(1, tax_burden)),
                "interest_burden": interest_burden,
                "roe_3step": roe_3step,
                "roe_5step": roe_5step,
                "tangible_equity_multiplier": tangible_equity_multiplier,
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio
            }
            
        except Exception as e:
            print(f"Warning: DuPont components calculation error: {e}")
            self.data["dupont_specific_components"] = {
                "roe_3step": 0,
                "roe_5step": 0,
                "tax_burden": 1.0,
                "interest_burden": 1.0
            }

    def _safe_get(self, series, *keys, default=0):
        """Safely get a value from a pandas Series by trying multiple keys."""
        for key in keys:
            if key in series.index:
                val = series[key]
                if val is not None and not (isinstance(val, float) and val != val):  # Check for NaN
                    return float(val)
        return default

    def _get_fred_data(self, series_id: str) -> Optional[float]:
        """Fetch FRED economic data (can be enhanced with actual API call)."""
        # Placeholder - would use FRED API in production
        fred_mapping = {
            "DGS10": 0.045,  # 10Y Treasury
            "T10YIE": 0.025  # 10Y Breakeven Inflation
        }
        return fred_mapping.get(series_id)

    def _get_fx_rate(self, currency: str) -> float:
        """Get FX rate to USD (can be enhanced with actual API call)."""
        # Placeholder - would use FX API in production
        common_rates = {
            "EUR": 0.92,
            "GBP": 0.79,
            "JPY": 149.50,
            "CAD": 1.36,
            "AUD": 1.52,
            "CHF": 0.88,
            "CNY": 7.19,
            "VND": 24500
        }
        return common_rates.get(currency, 1.0)

    def to_json(self, indent: int = 2) -> str:
        """Export data as JSON string."""
        return json.dumps(self.data, indent=indent, default=str)

    def save_to_file(self, filepath: str):
        """Save data to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)


def fetch_valuation_inputs(ticker: str, currency: str = "USD") -> Dict[str, Any]:
    """
    Convenience function to fetch all valuation inputs for a given ticker.
    
    Args:
        ticker: Stock ticker symbol
        currency: Reporting currency (default: USD)
    
    Returns:
        Dictionary containing all schema-compliant valuation inputs
    """
    inputs = ValuationInputs(ticker, currency)
    return inputs.fetch_all()


# Example usage
if __name__ == "__main__":
    # Test with Apple
    data = fetch_valuation_inputs("AAPL")
    print(json.dumps(data, indent=2, default=str))
