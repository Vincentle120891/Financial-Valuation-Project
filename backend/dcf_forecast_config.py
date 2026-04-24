"""
DCF Forecast Configuration with Peer Benchmarking & AI Suggestions
Retrieves 5+ peers, generates 6-period forecasts, and provides data-driven suggestions
based on historical trends (5Y) and peer comparisons.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
import json
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


@dataclass
class ForecastAssumptions:
    """6-period forecast arrays: [FY+1, FY+2, FY+3, FY+4, FY+5, Terminal]"""
    revenue_growth: List[float] = field(default_factory=lambda: [0.0] * 6)
    ebitda_margin: List[float] = field(default_factory=lambda: [0.0] * 6)
    depreciation_pct_of_revenue: List[float] = field(default_factory=lambda: [0.0] * 6)
    capex_pct_of_revenue: List[float] = field(default_factory=lambda: [0.0] * 6)
    working_capital_days: List[float] = field(default_factory=lambda: [0.0] * 6)
    tax_rate: List[float] = field(default_factory=lambda: [0.25] * 6)
    
    def validate_length(self) -> bool:
        """Ensure all arrays have exactly 6 elements"""
        arrays = [
            self.revenue_growth, self.ebitda_margin, 
            self.depreciation_pct_of_revenue, self.capex_pct_of_revenue,
            self.working_capital_days, self.tax_rate
        ]
        return all(len(arr) == 6 for arr in arrays)
    
    def set_terminal_from_average(self, start_idx: int = 2):
        """Set terminal value as average of years 3-5 if not explicitly set"""
        if self.revenue_growth[5] == 0.0:
            self.revenue_growth[5] = np.mean(self.revenue_growth[start_idx:5])
        if self.ebitda_margin[5] == 0.0:
            self.ebitda_margin[5] = np.mean(self.ebitda_margin[start_idx:5])
        if self.depreciation_pct_of_revenue[5] == 0.0:
            self.depreciation_pct_of_revenue[5] = np.mean(self.depreciation_pct_of_revenue[start_idx:5])
        if self.capex_pct_of_revenue[5] == 0.0:
            self.capex_pct_of_revenue[5] = np.mean(self.capex_pct_of_revenue[start_idx:5])
        if self.working_capital_days[5] == 0.0:
            self.working_capital_days[5] = np.mean(self.working_capital_days[start_idx:5])


@dataclass
class HistoricalTrendAnalysis:
    """5-year historical trend analysis for benchmarking"""
    revenue_cagr_5y: float = 0.0
    revenue_volatility: float = 0.0
    ebitda_margin_avg_5y: float = 0.0
    ebitda_margin_trend: float = 0.0  # slope of linear regression
    capex_intensity_avg_5y: float = 0.0
    wc_days_avg_5y: float = 0.0
    tax_rate_avg_5y: float = 0.0
    years_analyzed: int = 0
    
    @classmethod
    def from_financials(cls, financials: pd.DataFrame, cash_flow: pd.DataFrame, balance_sheet: pd.DataFrame) -> 'HistoricalTrendAnalysis':
        """Calculate 5-year historical trends from financial data"""
        instance = cls()
        
        try:
            # Revenue CAGR
            if 'Total Revenue' in financials.index and len(financials.columns) >= 5:
                revenues = financials.loc['Total Revenue'].dropna().values[:5]
                if len(revenues) >= 2:
                    n = len(revenues) - 1
                    instance.revenue_cagr_5y = (revenues[-1] / revenues[0]) ** (1/n) - 1
                    instance.revenue_volatility = np.std(np.diff(revenues) / revenues[:-1]) if n > 1 else 0.0
            
            # EBITDA Margin trends
            if 'Ebitda' in financials.index and 'Total Revenue' in financials.index:
                ebitda = financials.loc['Ebitda'].dropna().values[:5]
                revenue = financials.loc['Total Revenue'].dropna().values[:5]
                min_len = min(len(ebitda), len(revenue))
                if min_len >= 2:
                    margins = ebitda[:min_len] / revenue[:min_len]
                    instance.ebitda_margin_avg_5y = np.mean(margins)
                    # Linear trend (slope)
                    x = np.arange(len(margins))
                    if len(x) > 1:
                        instance.ebitda_margin_trend = np.polyfit(x, margins, 1)[0]
            
            # Capex intensity
            if 'Capital Expenditure' in cash_flow.index and 'Total Revenue' in financials.index:
                capex = -cash_flow.loc['Capital Expenditure'].dropna().values[:5]  # Make positive
                revenue = financials.loc['Total Revenue'].dropna().values[:5]
                min_len = min(len(capex), len(revenue))
                if min_len >= 1:
                    instance.capex_intensity_avg_5y = np.mean(capex[:min_len] / revenue[:min_len])
            
            # Working Capital Days
            if balance_sheet is not None and 'Total Revenue' in financials.index:
                ar_days_list = []
                inv_days_list = []
                ap_days_list = []
                
                for col in balance_sheet.columns[:5]:
                    try:
                        ar = balance_sheet.loc['Accounts Receivable', col] if 'Accounts Receivable' in balance_sheet.index else 0
                        inv = balance_sheet.loc['Inventory', col] if 'Inventory' in balance_sheet.index else 0
                        ap = balance_sheet.loc['Accounts Payable', col] if 'Accounts Payable' in balance_sheet.index else 0
                        rev = financials.loc['Total Revenue', col] if 'Total Revenue' in financials.index else 1
                        cogs = financials.loc['Cost Of Revenue', col] if 'Cost Of Revenue' in financials.index else rev * 0.7
                        
                        ar_days_list.append((ar / rev) * 365)
                        inv_days_list.append((inv / cogs) * 365)
                        ap_days_list.append((ap / cogs) * 365)
                    except:
                        continue
                
                if ar_days_list and inv_days_list and ap_days_list:
                    wc_days = [ar + inv - ap for ar, inv, ap in zip(ar_days_list, inv_days_list, ap_days_list)]
                    instance.wc_days_avg_5y = np.mean(wc_days)
            
            # Tax rate
            if 'Tax Provision' in financials.index and 'Pretax Income' in financials.index:
                tax = financials.loc['Tax Provision'].dropna().values[:5]
                ebt = financials.loc['Pretax Income'].dropna().values[:5]
                min_len = min(len(tax), len(ebt))
                if min_len >= 1:
                    valid_rates = [t/e for t, e in zip(tax[:min_len], ebt[:min_len]) if e != 0]
                    if valid_rates:
                        instance.tax_rate_avg_5y = np.mean(valid_rates)
            
            instance.years_analyzed = min_len if 'min_len' in locals() else 0
            
        except Exception as e:
            print(f"Warning: Error calculating historical trends: {e}")
        
        return instance


@dataclass
class PeerBenchmarkData:
    """Peer company comparison data"""
    ticker: str
    revenue_growth_1y: float
    revenue_growth_3y_cagr: float
    ebitda_margin: float
    capex_intensity: float
    wc_days: float
    ev_ebitda: float
    market_cap: float


@dataclass
class PeerBenchmarkAnalysis:
    """Aggregated peer benchmark statistics"""
    peer_count: int = 0
    revenue_growth_median: float = 0.0
    revenue_growth_mean: float = 0.0
    ebitda_margin_median: float = 0.0
    ebitda_margin_mean: float = 0.0
    capex_intensity_median: float = 0.0
    wc_days_median: float = 0.0
    ev_ebitda_median: float = 0.0
    peer_tickers: List[str] = field(default_factory=list)
    
    def generate_suggestion(self, metric: str, target_value: float) -> Dict[str, Any]:
        """Generate suggestion based on peer comparison"""
        suggestions = {
            'metric': metric,
            'target_value': target_value,
            'peer_median': getattr(self, f'{metric}_median', 0),
            'peer_mean': getattr(self, f'{metric}_mean', 0),
            'percentile_rank': 0.0,
            'recommendation': '',
            'confidence': 'medium'
        }
        
        peer_median = suggestions['peer_median']
        if peer_median == 0:
            suggestions['recommendation'] = "Insufficient peer data for comparison"
            return suggestions
        
        # Calculate percentile rank (simplified)
        diff_pct = (target_value - peer_median) / abs(peer_median) if peer_median != 0 else 0
        suggestions['percentile_rank'] = min(max(0.5 + diff_pct / 2, 0), 1)
        
        # Generate recommendation
        if metric == 'revenue_growth':
            if target_value > peer_median * 1.2:
                suggestions['recommendation'] = "Growth assumption is aggressive vs peers. Consider validating with management guidance."
                suggestions['confidence'] = 'low'
            elif target_value < peer_median * 0.8:
                suggestions['recommendation'] = "Growth assumption is conservative. May indicate market share loss or sector headwinds."
            else:
                suggestions['recommendation'] = "Growth assumption is in line with peer median."
                suggestions['confidence'] = 'high'
        
        elif metric == 'ebitda_margin':
            if target_value > peer_median + 0.05:
                suggestions['recommendation'] = "Margin assumption is significantly above peers. Verify operational efficiency drivers."
                suggestions['confidence'] = 'low'
            elif target_value < peer_median - 0.05:
                suggestions['recommendation'] = "Margin assumption below peers. Check for restructuring opportunities or cost pressures."
            else:
                suggestions['recommendation'] = "Margin assumption is reasonable relative to peer group."
                suggestions['confidence'] = 'high'
        
        elif metric == 'capex_intensity':
            if target_value > peer_median * 1.3:
                suggestions['recommendation'] = "High CapEx intensity. Ensure alignment with growth strategy and ROIC expectations."
            elif target_value < peer_median * 0.7:
                suggestions['recommendation'] = "Low CapEx intensity. May indicate underinvestment risk or mature business model."
            else:
                suggestions['recommendation'] = "CapEx intensity is within normal peer range."
        
        return suggestions


@dataclass
class DCFForecastConfiguration:
    """Complete DCF forecast configuration with peer benchmarking"""
    valuation_date: date
    currency: str
    ticker: str
    company_name: str
    
    # Historical financials (3 years)
    historical_fy_minus_3: Dict[str, Optional[float]] = field(default_factory=dict)
    historical_fy_minus_2: Dict[str, Optional[float]] = field(default_factory=dict)
    historical_fy_minus_1: Dict[str, Optional[float]] = field(default_factory=dict)
    
    # Base period balances
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    current_stock_price: float = 0.0
    
    # Forecast assumptions (6 periods)
    forecast_assumptions: ForecastAssumptions = field(default_factory=ForecastAssumptions)
    
    # Historical trend analysis (5 years)
    historical_trends: HistoricalTrendAnalysis = field(default_factory=HistoricalTrendAnalysis)
    
    # Peer benchmarking
    peer_benchmarks: PeerBenchmarkAnalysis = field(default_factory=PeerBenchmarkAnalysis)
    peer_details: List[PeerBenchmarkData] = field(default_factory=list)
    
    # Suggestions generated from analysis
    forecast_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    
    def generate_all_suggestions(self) -> List[Dict[str, Any]]:
        """Generate comprehensive suggestions based on historical trends and peer comparisons"""
        suggestions = []
        
        # Revenue growth suggestions
        if self.historical_trends.revenue_cagr_5y != 0:
            suggestions.append({
                'driver': 'revenue_growth',
                'historical_cagr_5y': self.historical_trends.revenue_cagr_5y,
                'forecast_fy1': self.forecast_assumptions.revenue_growth[0],
                'analysis': f"Historical 5Y CAGR: {self.historical_trends.revenue_cagr_5y:.1%}. "
                           f"FY+1 forecast: {self.forecast_assumptions.revenue_growth[0]:.1%}. "
                           f"{'Acceleration' if self.forecast_assumptions.revenue_growth[0] > self.historical_trends.revenue_cagr_5y else 'Deceleration'} expected.",
                'risk_flag': abs(self.forecast_assumptions.revenue_growth[0] - self.historical_trends.revenue_cagr_5y) > 0.1
            })
        
        # Peer comparison suggestions
        metrics_to_check = ['revenue_growth', 'ebitda_margin', 'capex_intensity']
        for metric in metrics_to_check:
            if self.peer_benchmarks.peer_count > 0:
                target_val = 0
                if metric == 'revenue_growth':
                    target_val = self.forecast_assumptions.revenue_growth[0]
                elif metric == 'ebitda_margin':
                    target_val = self.forecast_assumptions.ebitda_margin[0]
                elif metric == 'capex_intensity':
                    target_val = self.forecast_assumptions.capex_pct_of_revenue[0]
                
                suggestion = self.peer_benchmarks.generate_suggestion(metric, target_val)
                if suggestion['recommendation']:
                    suggestions.append(suggestion)
        
        # Terminal value sanity check
        term_growth = self.forecast_assumptions.revenue_growth[5]
        if term_growth > 0.05:  # > 5% terminal growth is aggressive
            suggestions.append({
                'driver': 'terminal_growth',
                'value': term_growth,
                'warning': f"Terminal growth rate of {term_growth:.1%} exceeds typical long-term GDP growth. Consider capping at 2-4%.",
                'severity': 'high'
            })
        
        self.forecast_suggestions = suggestions
        return suggestions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'metadata': {
                'valuation_date': self.valuation_date.isoformat(),
                'currency': self.currency,
                'ticker': self.ticker,
                'company_name': self.company_name
            },
            'historical_financials': {
                'fy_minus_3': self.historical_fy_minus_3,
                'fy_minus_2': self.historical_fy_minus_2,
                'fy_minus_1': self.historical_fy_minus_1
            },
            'base_period_balances': {
                'net_debt': self.net_debt,
                'shares_outstanding': self.shares_outstanding,
                'current_stock_price': self.current_stock_price
            },
            'forecast_assumptions': {
                'revenue_growth': self.forecast_assumptions.revenue_growth,
                'ebitda_margin': self.forecast_assumptions.ebitda_margin,
                'depreciation_pct_of_revenue': self.forecast_assumptions.depreciation_pct_of_revenue,
                'capex_pct_of_revenue': self.forecast_assumptions.capex_pct_of_revenue,
                'working_capital_days': self.forecast_assumptions.working_capital_days,
                'tax_rate': self.forecast_assumptions.tax_rate
            },
            'historical_trend_analysis': asdict(self.historical_trends),
            'peer_benchmark_analysis': asdict(self.peer_benchmarks),
            'peer_details': [asdict(p) for p in self.peer_details],
            'forecast_suggestions': self.forecast_suggestions
        }


def find_peers(ticker: str, min_peers: int = 5, sector: str = None) -> List[str]:
    """
    Find at least 5 peer companies based on sector/industry.
    Uses yfinance industry classification and market cap filtering.
    """
    if yf is None:
        raise ImportError("yfinance required. Install with: pip install yfinance")
    
    try:
        target = yf.Ticker(ticker)
        info = target.info
        
        # Get industry/sector
        target_industry = info.get('industry', '')
        target_sector = info.get('sector', '')
        target_market_cap = info.get('marketCap', 0)
        
        if not target_industry and not target_sector:
            # Fallback: use predefined peer groups for common sectors
            default_peers = {
                'AAPL': ['MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'INTC'],
                'MSFT': ['AAPL', 'GOOGL', 'AMZN', 'META', 'ORCL', 'CRM'],
                'GOOGL': ['META', 'AMZN', 'MSFT', 'NFLX', 'DIS', 'SNAP'],
                'AMZN': ['WMT', 'EBAY', 'SHOP', 'BABA', 'JD', 'MELI'],
                'JPM': ['BAC', 'WFC', 'C', 'GS', 'MS', 'USB'],
                'JNJ': ['PFE', 'MRK', 'ABBV', 'LLY', 'BMY', 'GILD'],
                'XOM': ['CVX', 'COP', 'SLB', 'EOG', 'MPC', 'VLO'],
            }
            return default_peers.get(ticker, [])
        
        # Search for peers in same industry
        # This is simplified - in production, you'd use a more sophisticated peer selection
        search_query = target_industry if target_industry else target_sector
        
        # Common peer mapping by industry (production would use a database)
        industry_peers = {
            'Software—Application': ['CRM', 'ADBE', 'NOW', 'INTU', 'WDAY', 'TEAM'],
            'Software—Infrastructure': ['ORCL', 'IBM', 'SAP', 'SNOW', 'MDB', 'NET'],
            'Internet Content & Information': ['META', 'NFLX', 'DIS', 'PARA', 'WBD', 'SPOT'],
            'Electronic Gaming & Multimedia': ['EA', 'TTWO', 'RBLX', 'U', 'PLTK', 'ZNGA'],
            'Semiconductors': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN'],
            'Drug Manufacturers—General': ['PFE', 'MRK', 'ABBV', 'LLY', 'BMY', 'GILD'],
            'Banks—Diversified': ['BAC', 'WFC', 'C', 'GS', 'MS', 'USB'],
            'Oil & Gas Integrated': ['CVX', 'COP', 'SLB', 'EOG', 'MPC', 'VLO'],
            'Auto Manufacturers': ['F', 'GM', 'TSLA', 'RIVN', 'LCID', 'NIO'],
            'Retail—Apparel': ['NKE', 'LULU', 'GPS', 'ANF', 'URBN', 'AEO'],
        }
        
        peers = []
        for industry, peer_list in industry_peers.items():
            if target_industry in industry or (sector and sector in industry):
                peers = peer_list
                break
        
        # If no matches, return generic peers based on market cap
        if not peers:
            if target_market_cap > 100e9:
                peers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA']
            elif target_market_cap > 10e9:
                peers = ['NFLX', 'ADBE', 'CRM', 'INTC', 'AMD', 'QCOM']
            else:
                peers = ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO']
        
        # Remove self and ensure minimum count
        peers = [p for p in peers if p != ticker][:max(min_peers, len(peers))]
        
        return peers
    
    except Exception as e:
        print(f"Error finding peers for {ticker}: {e}")
        return []


def fetch_peer_data(tickers: List[str]) -> List[PeerBenchmarkData]:
    """Fetch benchmark data for peer companies"""
    peer_data = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            financials = stock.financials
            cash_flow = stock.cashflow
            
            # Calculate metrics
            revenue = financials.loc['Total Revenue'] if 'Total Revenue' in financials.index else pd.Series([0])
            ebitda = financials.loc['Ebitda'] if 'Ebitda' in financials.index else pd.Series([0])
            capex = -cash_flow.loc['Capital Expenditure'] if 'Capital Expenditure' in cash_flow.index else pd.Series([0])
            
            # Growth rates
            if len(revenue) >= 2:
                growth_1y = (revenue.iloc[0] / revenue.iloc[1] - 1) if revenue.iloc[1] != 0 else 0
                growth_3y = (revenue.iloc[0] / revenue.iloc[-1]) ** (1/min(3, len(revenue)-1)) - 1 if len(revenue) > 1 and revenue.iloc[-1] != 0 else 0
            else:
                growth_1y = 0
                growth_3y = 0
            
            # Margins and intensities
            latest_rev = revenue.iloc[0] if len(revenue) > 0 else 1
            latest_ebitda = ebitda.iloc[0] if len(ebitda) > 0 else 0
            latest_capex = capex.iloc[0] if len(capex) > 0 else 0
            
            ebitda_margin = latest_ebitda / latest_rev if latest_rev != 0 else 0
            capex_intensity = latest_capex / latest_rev if latest_rev != 0 else 0
            
            # WC days (simplified)
            wc_days = 45.0  # Default fallback
            
            # EV/EBITDA
            market_cap = info.get('marketCap', 0)
            enterprise_value = market_cap + info.get('totalDebt', 0) - info.get('totalCash', 0)
            ev_ebitda = enterprise_value / latest_ebitda if latest_ebitda != 0 else 0
            
            peer_data.append(PeerBenchmarkData(
                ticker=ticker,
                revenue_growth_1y=growth_1y,
                revenue_growth_3y_cagr=growth_3y,
                ebitda_margin=ebitda_margin,
                capex_intensity=capex_intensity,
                wc_days=wc_days,
                ev_ebitda=ev_ebitda,
                market_cap=market_cap
            ))
        
        except Exception as e:
            print(f"Warning: Could not fetch data for peer {ticker}: {e}")
            continue
    
    return peer_data


def calculate_peer_benchmarks(peer_data: List[PeerBenchmarkData]) -> PeerBenchmarkAnalysis:
    """Calculate aggregate peer benchmark statistics"""
    if not peer_data:
        return PeerBenchmarkAnalysis()
    
    growth_values = [p.revenue_growth_1y for p in peer_data]
    margin_values = [p.ebitda_margin for p in peer_data]
    capex_values = [p.capex_intensity for p in peer_data]
    wc_values = [p.wc_days for p in peer_data]
    ev_ebitda_values = [p.ev_ebitda for p in peer_data]
    
    return PeerBenchmarkAnalysis(
        peer_count=len(peer_data),
        revenue_growth_median=float(np.median(growth_values)),
        revenue_growth_mean=float(np.mean(growth_values)),
        ebitda_margin_median=float(np.median(margin_values)),
        ebitda_margin_mean=float(np.mean(margin_values)),
        capex_intensity_median=float(np.median(capex_values)),
        wc_days_median=float(np.median(wc_values)),
        ev_ebitda_median=float(np.median(ev_ebitda_values)),
        peer_tickers=[p.ticker for p in peer_data]
    )


def fetch_dcf_forecast_config(
    ticker: str, 
    min_peers: int = 5,
    use_ai_suggestions: bool = True
) -> DCFForecastConfiguration:
    """
    Complete DCF forecast configuration fetcher with:
    - 3 years historical financials
    - 6-period forecast arrays (5Y + terminal)
    - 5+ peer benchmarking
    - Data-driven suggestions
    """
    if yf is None:
        raise ImportError("yfinance required. Install with: pip install yfinance")
    
    # Fetch target company data
    stock = yf.Ticker(ticker)
    info = stock.info
    financials = stock.financials
    cash_flow = stock.cashflow
    balance_sheet = stock.balance_sheet
    
    # Get valuation date (latest financial report date)
    valuation_date = financials.columns[0].to_pydatetime().date() if len(financials.columns) > 0 else date.today()
    
    # Extract 3 years of historical data
    def extract_year_data(year_idx: int) -> Dict[str, Optional[float]]:
        if year_idx >= len(financials.columns):
            return {}
        
        col = financials.columns[year_idx]
        cf_col = cash_flow.columns[year_idx] if year_idx < len(cash_flow.columns) else None
        bs_col = balance_sheet.columns[year_idx] if year_idx < len(balance_sheet.columns) else None
        
        data = {
            'revenue': float(financials.loc['Total Revenue', col]) if 'Total Revenue' in financials.index else None,
            'cogs': float(financials.loc['Cost Of Revenue', col]) if 'Cost Of Revenue' in financials.index else None,
            'gross_profit': None,  # Calculated below
            'sga': float(financials.loc['Operating Expense', col]) if 'Operating Expense' in financials.index else None,
            'other_opex': None,
            'ebitda': float(financials.loc['Ebitda', col]) if 'Ebitda' in financials.index else None,
            'depreciation': None,
            'ebit': float(financials.loc['Operating Income', col]) if 'Operating Income' in financials.index else None,
            'interest_expense': float(financials.loc['Interest Expense', col]) if 'Interest Expense' in financials.index else None,
            'ebt': float(financials.loc['Pretax Income', col]) if 'Pretax Income' in financials.index else None,
            'current_tax': None,
            'deferred_tax': None,
            'total_tax': float(financials.loc['Tax Provision', col]) if 'Tax Provision' in financials.index else None,
            'net_income': float(financials.loc['Net Income', col]) if 'Net Income' in financials.index else None,
            'accounts_receivable': float(balance_sheet.loc['Accounts Receivable', bs_col]) if bs_col is not None and 'Accounts Receivable' in balance_sheet.index else None,
            'inventory': float(balance_sheet.loc['Inventory', bs_col]) if bs_col is not None and 'Inventory' in balance_sheet.index else None,
            'accounts_payable': float(balance_sheet.loc['Accounts Payable', bs_col]) if bs_col is not None and 'Accounts Payable' in balance_sheet.index else None,
            'net_working_capital': None,
            'capital_expenditure': float(-cash_flow.loc['Capital Expenditure', cf_col]) if cf_col is not None and 'Capital Expenditure' in cash_flow.index else None,
        }
        
        # Calculate derived fields
        if data['revenue'] and data['cogs']:
            data['gross_profit'] = data['revenue'] - data['cogs']
        
        if data['accounts_receivable'] and data['inventory'] and data['accounts_payable']:
            data['net_working_capital'] = data['accounts_receivable'] + data['inventory'] - data['accounts_payable']
        
        return data
    
    hist_fy_minus_1 = extract_year_data(0)
    hist_fy_minus_2 = extract_year_data(1) if len(financials.columns) > 1 else {}
    hist_fy_minus_3 = extract_year_data(2) if len(financials.columns) > 2 else {}
    
    # Base period balances
    net_debt = info.get('totalDebt', 0) - info.get('totalCash', 0)
    shares_outstanding = info.get('sharesOutstanding', 0)
    current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
    
    # Calculate 5-year historical trends
    historical_trends = HistoricalTrendAnalysis.from_financials(financials, cash_flow, balance_sheet)
    
    # Find and analyze peers
    peer_tickers = find_peers(ticker, min_peers=min_peers)
    peer_data = fetch_peer_data(peer_tickers)
    peer_benchmarks = calculate_peer_benchmarks(peer_data)
    
    # Initialize forecast assumptions with historical averages as starting point
    forecast = ForecastAssumptions()
    
    # Set initial forecasts based on historical trends
    if historical_trends.revenue_cagr_5y != 0:
        forecast.revenue_growth = [historical_trends.revenue_cagr_5y] * 5 + [min(historical_trends.revenue_cagr_5y, 0.03)]
    
    if historical_trends.ebitda_margin_avg_5y != 0:
        forecast.ebitda_margin = [historical_trends.ebitda_margin_avg_5y] * 6
    
    if historical_trends.capex_intensity_avg_5y != 0:
        forecast.capex_pct_of_revenue = [historical_trends.capex_intensity_avg_5y] * 6
    
    if historical_trends.wc_days_avg_5y != 0:
        forecast.working_capital_days = [historical_trends.wc_days_avg_5y] * 6
    
    if historical_trends.tax_rate_avg_5y != 0:
        forecast.tax_rate = [historical_trends.tax_rate_avg_5y] * 6
    
    # Create configuration object
    config = DCFForecastConfiguration(
        valuation_date=valuation_date,
        currency=info.get('currency', 'USD'),
        ticker=ticker,
        company_name=info.get('longName', ticker),
        historical_fy_minus_1=hist_fy_minus_1,
        historical_fy_minus_2=hist_fy_minus_2,
        historical_fy_minus_3=hist_fy_minus_3,
        net_debt=net_debt,
        shares_outstanding=shares_outstanding,
        current_stock_price=current_price,
        forecast_assumptions=forecast,
        historical_trends=historical_trends,
        peer_benchmarks=peer_benchmarks,
        peer_details=peer_data
    )
    
    # Generate suggestions
    if use_ai_suggestions:
        config.generate_all_suggestions()
    
    return config


# Example usage
if __name__ == "__main__":
    # Fetch complete DCF forecast configuration
    config = fetch_dcf_forecast_config("AAPL", min_peers=5)
    
    # Print summary
    print(f"\n=== DCF Forecast Configuration for {config.ticker} ===")
    print(f"Valuation Date: {config.valuation_date}")
    print(f"Currency: {config.currency}")
    print(f"\nHistorical Trends (5Y):")
    print(f"  Revenue CAGR: {config.historical_trends.revenue_cagr_5y:.1%}")
    print(f"  EBITDA Margin Avg: {config.historical_trends.ebitda_margin_avg_5y:.1%}")
    print(f"  Capex Intensity: {config.historical_trends.capex_intensity_avg_5y:.1%}")
    
    print(f"\nPeer Benchmark ({config.peer_benchmarks.peer_count} peers):")
    print(f"  Peers: {', '.join(config.peer_benchmarks.peer_tickers)}")
    print(f"  Median Revenue Growth: {config.peer_benchmarks.revenue_growth_median:.1%}")
    print(f"  Median EBITDA Margin: {config.peer_benchmarks.ebitda_margin_median:.1%}")
    
    print(f"\nForecast Assumptions (6 periods: FY+1 to Terminal):")
    print(f"  Revenue Growth: {[f'{x:.1%}' for x in config.forecast_assumptions.revenue_growth]}")
    print(f"  EBITDA Margin: {[f'{x:.1%}' for x in config.forecast_assumptions.ebitda_margin]}")
    
    print(f"\nSuggestions:")
    for suggestion in config.forecast_suggestions:
        print(f"  - {suggestion}")
    
    # Export to JSON
    # with open('dcf_forecast_config.json', 'w') as f:
    #     json.dump(config.to_dict(), f, indent=2)
