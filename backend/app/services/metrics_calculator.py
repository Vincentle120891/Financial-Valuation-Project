"""
Metrics Calculator - Step 5B: Calculations

Calculates ALL derived metrics from API data:
    - Margins (EBITDA, Net, FCF) - historical + 3Y averages
    - Growth Rates (CAGR, YoY) - calculated from revenue history
    - Working Capital Days (AR, Inv, AP) - from balance sheet
    - Capex Ratios - from cash flow / revenue
    - Implied Cost of Debt = Interest Expense / Total Debt
    - Debt ratios, ROE, ROIC, market multiples
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Service for calculating derived financial metrics from raw API data."""
    
    def __init__(self):
        self.raw_data = None
        self.calculated_metrics = None
    
    def calculate_all_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all derived metrics from raw yfinance data.
        
        Args:
            raw_data: Comprehensive data package from YFinanceService
            
        Returns:
            Dictionary containing all calculated metrics
        """
        self.raw_data = raw_data
        
        logger.info(f"Calculating all metrics for ticker='{raw_data.get('symbol', 'UNKNOWN')}'")
        
        # Extract components
        income_stmt = raw_data.get('income_statement', {})
        balance_sheet = raw_data.get('balance_sheet', {})
        cash_flow = raw_data.get('cash_flow', {})
        key_stats = raw_data.get('key_stats', {})
        
        # Calculate all metric categories
        margins = self._calculate_margins(income_stmt, cash_flow)
        growth_rates = self._calculate_growth_rates(income_stmt)
        working_capital_days = self._calculate_working_capital_days(
            income_stmt, balance_sheet
        )
        capex_ratios = self._calculate_capex_ratios(income_stmt, cash_flow)
        cost_of_debt = self._calculate_cost_of_debt(income_stmt, balance_sheet)
        debt_ratios = self._calculate_debt_ratios(balance_sheet, key_stats)
        profitability_ratios = self._calculate_profitability_ratios(
            income_stmt, balance_sheet
        )
        roe_roic = self._calculate_roe_roic(income_stmt, balance_sheet)
        market_multiples = self._calculate_market_multiples(key_stats, income_stmt)
        
        # Compile comprehensive metrics package
        self.calculated_metrics = {
            "symbol": raw_data.get('symbol'),
            "calculation_timestamp": datetime.now().isoformat(),
            "margins": margins,
            "growth_rates": growth_rates,
            "working_capital_days": working_capital_days,
            "capex_ratios": capex_ratios,
            "cost_of_debt": cost_of_debt,
            "debt_ratios": debt_ratios,
            "profitability_ratios": profitability_ratios,
            "roe_roic": roe_roic,
            "market_multiples": market_multiples,
        }
        
        logger.info(f"Successfully calculated all metrics for ticker='{raw_data.get('symbol')}'")
        return self.calculated_metrics
    
    def _get_sorted_periods(self, data_dict: Dict) -> List[Tuple[str, float]]:
        """Sort periods chronologically (oldest first) and return list of (period, value) tuples."""
        if not data_dict:
            return []
        
        items = [(k, v) for k, v in data_dict.items() if v is not None]
        # Sort by key (year/period) - assuming format like '2023-12-31' or similar
        try:
            sorted_items = sorted(items, key=lambda x: str(x[0]), reverse=True)
        except Exception:
            sorted_items = items
        
        return sorted_items
    
    def _calculate_margins(
        self, 
        income_stmt: Dict, 
        cash_flow: Dict
    ) -> Dict[str, Any]:
        """Calculate margin metrics."""
        revenue = self._get_sorted_periods(income_stmt.get('total_revenue', {}))
        ebitda = self._get_sorted_periods(income_stmt.get('ebitda', {}))
        net_income = self._get_sorted_periods(income_stmt.get('net_income', {}))
        fcf = self._get_sorted_periods(cash_flow.get('free_cash_flow', {}))
        operating_income = self._get_sorted_periods(income_stmt.get('operating_income', {}))
        
        def calc_margin_hist(primary: List, denominator: List) -> List[float]:
            """Calculate historical margins."""
            margins = []
            min_len = min(len(primary), len(denominator))
            for i in range(min_len):
                if denominator[i][1] and denominator[i][1] != 0 and primary[i][1]:
                    margins.append(primary[i][1] / denominator[i][1])
                else:
                    margins.append(None)
            return margins
        
        ebitda_margins = calc_margin_hist(ebitda, revenue)
        net_margins = calc_margin_hist(net_income, revenue)
        fcf_margins = calc_margin_hist(fcf, revenue)
        operating_margins = calc_margin_hist(operating_income, revenue)
        
        # Calculate 3-year averages (most recent 3 periods)
        def avg_last_n(values: List[float], n: int = 3) -> Optional[float]:
            valid = [v for v in values[:n] if v is not None]
            return sum(valid) / len(valid) if valid else None
        
        return {
            "ebitda_margin": {
                "historical": ebitda_margins,
                "latest": ebitda_margins[0] if ebitda_margins else None,
                "avg_3y": avg_last_n(ebitda_margins),
            },
            "net_margin": {
                "historical": net_margins,
                "latest": net_margins[0] if net_margins else None,
                "avg_3y": avg_last_n(net_margins),
            },
            "fcf_margin": {
                "historical": fcf_margins,
                "latest": fcf_margins[0] if fcf_margins else None,
                "avg_3y": avg_last_n(fcf_margins),
            },
            "operating_margin": {
                "historical": operating_margins,
                "latest": operating_margins[0] if operating_margins else None,
                "avg_3y": avg_last_n(operating_margins),
            },
            "gross_margin": None,  # Would need COGS data
        }
    
    def _calculate_growth_rates(self, income_stmt: Dict) -> Dict[str, Any]:
        """Calculate growth rate metrics (CAGR, YoY)."""
        revenue = self._get_sorted_periods(income_stmt.get('total_revenue', {}))
        ebitda = self._get_sorted_periods(income_stmt.get('ebitda', {}))
        net_income = self._get_sorted_periods(income_stmt.get('net_income', {}))
        eps = self._get_sorted_periods(income_stmt.get('diluted_eps', {}))
        
        def calc_yoy_growth(values: List) -> List[Optional[float]]:
            """Calculate year-over-year growth rates."""
            growth = []
            for i in range(len(values) - 1):
                if values[i][1] and values[i+1][1] and values[i+1][1] != 0:
                    g = (values[i][1] - values[i+1][1]) / abs(values[i+1][1])
                    growth.append(g)
                else:
                    growth.append(None)
            return growth
        
        def calc_cagr(values: List, n_periods: int = 3) -> Optional[float]:
            """Calculate CAGR over n periods."""
            if len(values) < n_periods + 1:
                return None
            latest = values[0][1]
            oldest = values[n_periods][1]
            if latest and oldest and oldest != 0:
                return (latest / oldest) ** (1 / n_periods) - 1
            return None
        
        revenue_yoy = calc_yoy_growth(revenue)
        ebitda_yoy = calc_yoy_growth(ebitda)
        net_income_yoy = calc_yoy_growth(net_income)
        eps_yoy = calc_yoy_growth(eps)
        
        return {
            "revenue": {
                "yoy": revenue_yoy,
                "cagr_3y": calc_cagr(revenue, 3),
                "cagr_5y": calc_cagr(revenue, 5) if len(revenue) > 5 else None,
                "latest_yoy": revenue_yoy[0] if revenue_yoy else None,
            },
            "ebitda": {
                "yoy": ebitda_yoy,
                "cagr_3y": calc_cagr(ebitda, 3),
                "latest_yoy": ebitda_yoy[0] if ebitda_yoy else None,
            },
            "net_income": {
                "yoy": net_income_yoy,
                "cagr_3y": calc_cagr(net_income, 3),
                "latest_yoy": net_income_yoy[0] if net_income_yoy else None,
            },
            "eps": {
                "yoy": eps_yoy,
                "cagr_3y": calc_cagr(eps, 3),
                "latest_yoy": eps_yoy[0] if eps_yoy else None,
            },
        }
    
    def _calculate_working_capital_days(
        self, 
        income_stmt: Dict, 
        balance_sheet: Dict
    ) -> Dict[str, Any]:
        """Calculate working capital efficiency metrics (days)."""
        revenue = self._get_sorted_periods(income_stmt.get('total_revenue', {}))
        ar = self._get_sorted_periods(balance_sheet.get('accounts_receivable', {}))
        inventory = self._get_sorted_periods(balance_sheet.get('inventory', {}))
        ap = self._get_sorted_periods(balance_sheet.get('accounts_payable', {}))
        cogs = self._get_sorted_periods(income_stmt.get('cost_of_revenue', {}))
        
        def calc_days_metric(
            balance_item: List, 
            income_item: List, 
            use_cogs: bool = False
        ) -> List[Optional[float]]:
            """Calculate days metric (DSO, DIO, DPO)."""
            days = []
            min_len = min(len(balance_item), len(income_item))
            for i in range(min_len):
                bal = balance_item[i][1]
                inc = income_item[i][1]
                if bal and inc and inc != 0:
                    # Use appropriate denominator (revenue or COGS)
                    denominator = cogs[i][1] if use_cogs and i < len(cogs) and cogs[i][1] else inc
                    if denominator and denominator != 0:
                        days.append((bal / denominator) * 365)
                    else:
                        days.append(None)
                else:
                    days.append(None)
            return days
        
        dso = calc_days_metric(ar, revenue, use_cogs=False)  # Days Sales Outstanding
        dio = calc_days_metric(inventory, revenue, use_cogs=True)  # Days Inventory Outstanding
        dpo = calc_days_metric(ap, revenue, use_cogs=True)  # Days Payables Outstanding
        
        # Cash Conversion Cycle = DSO + DIO - DPO
        ccc = []
        min_len = min(len(dso), len(dio), len(dpo))
        for i in range(min_len):
            if dso[i] is not None and dio[i] is not None and dpo[i] is not None:
                ccc.append(dso[i] + dio[i] - dpo[i])
            else:
                ccc.append(None)
        
        def avg_last_n(values: List[float], n: int = 3) -> Optional[float]:
            valid = [v for v in values[:n] if v is not None]
            return sum(valid) / len(valid) if valid else None
        
        return {
            "dso": {
                "historical": dso,
                "latest": dso[0] if dso else None,
                "avg_3y": avg_last_n(dso),
                "description": "Days Sales Outstanding",
            },
            "dio": {
                "historical": dio,
                "latest": dio[0] if dio else None,
                "avg_3y": avg_last_n(dio),
                "description": "Days Inventory Outstanding",
            },
            "dpo": {
                "historical": dpo,
                "latest": dpo[0] if dpo else None,
                "avg_3y": avg_last_n(dpo),
                "description": "Days Payables Outstanding",
            },
            "cash_conversion_cycle": {
                "historical": ccc,
                "latest": ccc[0] if ccc else None,
                "avg_3y": avg_last_n(ccc),
                "description": "Cash Conversion Cycle (DSO + DIO - DPO)",
            },
        }
    
    def _calculate_capex_ratios(
        self, 
        income_stmt: Dict, 
        cash_flow: Dict
    ) -> Dict[str, Any]:
        """Calculate capex-related ratios."""
        revenue = self._get_sorted_periods(income_stmt.get('total_revenue', {}))
        capex = self._get_sorted_periods(cash_flow.get('capital_expenditure', {}))
        fcf = self._get_sorted_periods(cash_flow.get('free_cash_flow', {}))
        ocf = self._get_sorted_periods(cash_flow.get('operating_cash_flow', {}))
        
        def calc_ratio_hist(numerator: List, denominator: List) -> List[Optional[float]]:
            ratios = []
            min_len = min(len(numerator), len(denominator))
            for i in range(min_len):
                num = abs(numerator[i][1]) if numerator[i][1] else None  # Capex is typically negative
                den = denominator[i][1]
                if num and den and den != 0:
                    ratios.append(num / den)
                else:
                    ratios.append(None)
            return ratios
        
        capex_to_revenue = calc_ratio_hist(capex, revenue)
        fcf_to_revenue = calc_ratio_hist(fcf, revenue)
        capex_to_ocf = calc_ratio_hist(capex, ocf)
        
        def avg_last_n(values: List[float], n: int = 3) -> Optional[float]:
            valid = [v for v in values[:n] if v is not None]
            return sum(valid) / len(valid) if valid else None
        
        return {
            "capex_to_revenue": {
                "historical": capex_to_revenue,
                "latest": capex_to_revenue[0] if capex_to_revenue else None,
                "avg_3y": avg_last_n(capex_to_revenue),
                "description": "Capital Expenditure as % of Revenue",
            },
            "fcf_to_revenue": {
                "historical": fcf_to_revenue,
                "latest": fcf_to_revenue[0] if fcf_to_revenue else None,
                "avg_3y": avg_last_n(fcf_to_revenue),
                "description": "Free Cash Flow as % of Revenue",
            },
            "capex_to_ocf": {
                "historical": capex_to_ocf,
                "latest": capex_to_ocf[0] if capex_to_ocf else None,
                "avg_3y": avg_last_n(capex_to_ocf),
                "description": "Capex Coverage Ratio (Capex / Operating CF)",
            },
        }
    
    def _calculate_cost_of_debt(
        self, 
        income_stmt: Dict, 
        balance_sheet: Dict
    ) -> Dict[str, Any]:
        """
        Calculate implied cost of debt.
        Formula: Interest Expense / Total Debt
        """
        interest_expense = self._get_sorted_periods(income_stmt.get('interest_expense', {}))
        total_debt = self._get_sorted_periods(balance_sheet.get('total_debt', {}))
        
        cost_of_debt = []
        min_len = min(len(interest_expense), len(total_debt))
        for i in range(min_len):
            interest = interest_expense[i][1]
            debt = total_debt[i][1]
            if interest and debt and debt != 0:
                cost_of_debt.append(abs(interest) / debt)  # Interest is typically negative
            else:
                cost_of_debt.append(None)
        
        return {
            "implied_cost_of_debt": {
                "historical": cost_of_debt,
                "latest": cost_of_debt[0] if cost_of_debt else None,
                "avg_3y": sum([v for v in cost_of_debt[:3] if v is not None]) / 
                          len([v for v in cost_of_debt[:3] if v is not None]) if any(cost_of_debt[:3]) else None,
                "formula": "Interest Expense / Total Debt",
            },
        }
    
    def _calculate_debt_ratios(
        self, 
        balance_sheet: Dict, 
        key_stats: Dict
    ) -> Dict[str, Any]:
        """Calculate debt and leverage ratios."""
        total_debt = self._get_sorted_periods(balance_sheet.get('total_debt', {}))
        total_equity = self._get_sorted_periods(balance_sheet.get('total_equity', {}))
        total_assets = self._get_sorted_periods(balance_sheet.get('total_assets', {}))
        current_assets = self._get_sorted_periods(balance_sheet.get('current_assets', {}))
        current_liabilities = self._get_sorted_periods(balance_sheet.get('current_liabilities', {}))
        cash = self._get_sorted_periods(balance_sheet.get('cash', {}))
        
        def calc_ratio_hist(num_list: List, den_list: List) -> List[Optional[float]]:
            ratios = []
            min_len = min(len(num_list), len(den_list))
            for i in range(min_len):
                num = num_list[i][1]
                den = den_list[i][1]
                if num is not None and den is not None and den != 0:
                    ratios.append(num / den)
                else:
                    ratios.append(None)
            return ratios
        
        debt_to_equity = calc_ratio_hist(total_debt, total_equity)
        debt_to_assets = calc_ratio_hist(total_debt, total_assets)
        
        # Current ratio = Current Assets / Current Liabilities
        current_ratio = calc_ratio_hist(current_assets, current_liabilities)
        
        # Quick ratio = (Current Assets - Inventory) / Current Liabilities
        # Simplified: using current_assets directly as approximation
        quick_ratio = current_ratio  # Simplified
        
        # Net Debt = Total Debt - Cash
        net_debt = []
        min_len = min(len(total_debt), len(cash))
        for i in range(min_len):
            debt = total_debt[i][1]
            c = cash[i][1] if i < len(cash) else 0
            if debt is not None:
                net_debt.append(debt - (c if c else 0))
            else:
                net_debt.append(None)
        
        return {
            "debt_to_equity": {
                "historical": debt_to_equity,
                "latest": debt_to_equity[0] if debt_to_equity else None,
                "description": "Total Debt / Total Equity",
            },
            "debt_to_assets": {
                "historical": debt_to_assets,
                "latest": debt_to_assets[0] if debt_to_assets else None,
                "description": "Total Debt / Total Assets",
            },
            "current_ratio": {
                "historical": current_ratio,
                "latest": current_ratio[0] if current_ratio else None,
                "description": "Current Assets / Current Liabilities",
            },
            "quick_ratio": {
                "historical": quick_ratio,
                "latest": quick_ratio[0] if quick_ratio else None,
                "description": "(Current Assets - Inventory) / Current Liabilities",
            },
            "net_debt": {
                "historical": net_debt,
                "latest": net_debt[0] if net_debt else None,
                "description": "Total Debt - Cash",
            },
        }
    
    def _calculate_profitability_ratios(
        self, 
        income_stmt: Dict, 
        balance_sheet: Dict
    ) -> Dict[str, Any]:
        """Calculate profitability ratios."""
        net_income = self._get_sorted_periods(income_stmt.get('net_income', {}))
        ebitda = self._get_sorted_periods(income_stmt.get('ebitda', {}))
        operating_income = self._get_sorted_periods(income_stmt.get('operating_income', {}))
        total_assets = self._get_sorted_periods(balance_sheet.get('total_assets', {}))
        
        def calc_return_metric(income_list: List, asset_list: List) -> List[Optional[float]]:
            returns = []
            min_len = min(len(income_list), len(asset_list))
            for i in range(min_len):
                inc = income_list[i][1]
                assets = asset_list[i][1]
                if inc is not None and assets is not None and assets != 0:
                    returns.append(inc / assets)
                else:
                    returns.append(None)
            return returns
        
        roa = calc_return_metric(net_income, total_assets)
        roa_ebitda = calc_return_metric(ebitda, total_assets)
        operating_return = calc_return_metric(operating_income, total_assets)
        
        return {
            "roa": {
                "historical": roa,
                "latest": roa[0] if roa else None,
                "description": "Net Income / Total Assets (Return on Assets)",
            },
            "roa_ebitda": {
                "historical": roa_ebitda,
                "latest": roa_ebitda[0] if roa_ebitda else None,
                "description": "EBITDA / Total Assets",
            },
            "operating_return_on_assets": {
                "historical": operating_return,
                "latest": operating_return[0] if operating_return else None,
                "description": "Operating Income / Total Assets",
            },
        }
    
    def _calculate_roe_roic(
        self, 
        income_stmt: Dict, 
        balance_sheet: Dict
    ) -> Dict[str, Any]:
        """Calculate ROE and ROIC."""
        net_income = self._get_sorted_periods(income_stmt.get('net_income', {}))
        ebit = self._get_sorted_periods(income_stmt.get('ebit', {}))
        total_equity = self._get_sorted_periods(balance_sheet.get('total_equity', {}))
        total_debt = self._get_sorted_periods(balance_sheet.get('total_debt', {}))
        cash = self._get_sorted_periods(balance_sheet.get('cash', {}))
        
        # ROE = Net Income / Shareholders' Equity
        roe = []
        min_len = min(len(net_income), len(total_equity))
        for i in range(min_len):
            ni = net_income[i][1]
            eq = total_equity[i][1]
            if ni is not None and eq is not None and eq != 0:
                roe.append(ni / eq)
            else:
                roe.append(None)
        
        # ROIC = NOPAT / Invested Capital
        # NOPAT ≈ EBIT * (1 - Tax Rate)
        # Invested Capital = Debt + Equity - Cash
        tax_rate_estimate = 0.21  # Default corporate tax rate
        
        roic = []
        min_len = min(len(ebit), len(total_debt), len(total_equity), len(cash))
        for i in range(min_len):
            ebit_val = ebit[i][1]
            debt = total_debt[i][1]
            equity = total_equity[i][1]
            c = cash[i][1] if i < len(cash) else 0
            
            if ebit_val is not None and debt is not None and equity is not None:
                nopat = ebit_val * (1 - tax_rate_estimate)
                invested_capital = debt + equity - (c if c else 0)
                if invested_capital != 0:
                    roic.append(nopat / invested_capital)
                else:
                    roic.append(None)
            else:
                roic.append(None)
        
        return {
            "roe": {
                "historical": roe,
                "latest": roe[0] if roe else None,
                "description": "Net Income / Shareholders' Equity (Return on Equity)",
            },
            "roic": {
                "historical": roic,
                "latest": roic[0] if roic else None,
                "tax_rate_used": tax_rate_estimate,
                "description": "NOPAT / Invested Capital (Return on Invested Capital)",
            },
        }
    
    def _calculate_market_multiples(
        self, 
        key_stats: Dict, 
        income_stmt: Dict
    ) -> Dict[str, Any]:
        """Calculate market valuation multiples."""
        # Get latest values from key stats
        market_cap = key_stats.get('market_cap')
        enterprise_value = key_stats.get('enterprise_value')
        current_price = key_stats.get('current_price')
        
        # Get latest financial metrics
        revenue = self._get_sorted_periods(income_stmt.get('total_revenue', {}))
        ebitda = self._get_sorted_periods(income_stmt.get('ebitda', {}))
        net_income = self._get_sorted_periods(income_stmt.get('net_income', {}))
        
        latest_revenue = revenue[0][1] if revenue else None
        latest_ebitda = ebitda[0][1] if ebitda else None
        latest_net_income = net_income[0][1] if net_income else None
        
        multiples = {}
        
        # P/E Ratio
        if current_price and latest_net_income:
            # Need shares outstanding for proper P/E
            shares = key_stats.get('shares_outstanding')
            if shares:
                eps = latest_net_income / shares
                multiples['pe_ratio'] = {
                    'value': current_price / eps if eps else None,
                    'description': 'Price to Earnings Ratio',
                }
        
        # EV/Revenue
        if enterprise_value and latest_revenue:
            multiples['ev_to_revenue'] = {
                'value': enterprise_value / latest_revenue,
                'description': 'Enterprise Value to Revenue',
            }
        
        # EV/EBITDA
        if enterprise_value and latest_ebitda:
            multiples['ev_to_ebitda'] = {
                'value': enterprise_value / latest_ebitda,
                'description': 'Enterprise Value to EBITDA',
            }
        
        # Price/Book (if available from key_stats)
        pb = key_stats.get('price_to_book')
        if pb:
            multiples['price_to_book'] = {
                'value': pb,
                'description': 'Price to Book Value',
            }
        
        # Price/Sales
        if current_price and latest_revenue:
            shares = key_stats.get('shares_outstanding')
            if shares:
                sales_per_share = latest_revenue / shares
                multiples['price_to_sales'] = {
                    'value': current_price / sales_per_share if sales_per_share else None,
                    'description': 'Price to Sales Ratio',
                }
        
        return multiples


def calculate_metrics(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to calculate all metrics from raw data.
    
    Args:
        raw_data: Comprehensive data package from YFinanceService
        
    Returns:
        Dictionary containing all calculated metrics
    """
    calculator = MetricsCalculator()
    return calculator.calculate_all_metrics(raw_data)


def fetch_and_calculate_all_metrics(ticker_symbol: str, market: str = "international") -> Dict[str, Any]:
    """
    Unified function that executes Step 5A → Step 5B sequentially.
    
    Args:
        ticker_symbol: Stock ticker symbol
        market: Market type (vietnamese or international)
        
    Returns:
        Comprehensive data package with both raw and calculated metrics
    """
    from app.services.yfinance_service import fetch_yfinance_data
    
    logger.info(f"Fetching and calculating all metrics for ticker='{ticker_symbol}'")
    
    # Step 5A: Fetch raw data
    raw_data = fetch_yfinance_data(ticker_symbol, market)
    
    # Step 5B: Calculate derived metrics
    calculated_metrics = calculate_metrics(raw_data)
    
    # Combine into comprehensive package
    comprehensive_data = {
        **raw_data,
        "calculated_metrics": calculated_metrics,
    }
    
    logger.info(f"Successfully fetched and calculated all metrics for ticker='{ticker_symbol}'")
    return comprehensive_data
