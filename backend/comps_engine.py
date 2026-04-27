"""
Comparable Company Analysis (Trading Comps) & Precedent Transaction Model
Complete implementation matching Excel specification with:
- Trading Comps: EV/EBITDA and P/E multiples for LTM, FY2023, FY2024
- Transaction Comps: Precedent M&A deal multiples
- Implied share price calculations using Min/Average/Max multiples
- Football field chart data generation
All figures can be in any currency (USD, GBP, etc.)
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import statistics
from .ai_engine import suggest_peer_companies


# ============================================================================
# DATA CLASSES - TRADING COMPS
# ============================================================================

@dataclass
class TargetCompanyData:
    """
    Input data for the target company being valued.
    Matches Excel "Trading Comps" sheet rows 58-82.
    """
    ticker: str
    company_name: str
    market_cap: float  # Equity value (GBP mm or USD mm)
    enterprise_value: float  # EV (GBP mm or USD mm)

    # EBITDA metrics (all in same currency units as market cap)
    ebitda_ltm: float
    ebitda_fy2023: float  # Next fiscal year estimate
    ebitda_fy2024: float  # Year after estimate

    # EPS metrics (per share, same currency as stock price)
    eps_ltm: float
    eps_fy2023: float
    eps_fy2024: float

    # Capital structure
    net_debt: float
    shares_outstanding: float  # In millions
    current_stock_price: float  # Per share

    # Metadata
    currency: str = "GBP"
    analysis_date: str = ""


@dataclass
class PeerCompanyData:
    """
    Input data for each peer company.
    Matches Excel "TSCO" sheet structure with LTM and forward estimates.
    """
    ticker: str
    company_name: str

    # Valuation metrics
    market_cap: float
    enterprise_value: float
    share_price: float
    shares_outstanding: float

    # EBITDA metrics
    ebitda_ltm: float
    ebitda_fy2023: float
    ebitda_fy2024: float

    # EPS metrics
    eps_ltm: float
    eps_fy2023: float
    eps_fy2024: float

    # Optional metadata
    industry: str = ""
    sector: str = ""
    selection_reason: str = "Industry peer"
    is_primary_comparable: bool = False  # Like TSCO in Excel


@dataclass
class PeerMultiples:
    """Calculated multiples for a single peer company."""
    ticker: str
    company_name: str
    is_primary: bool

    # EV/EBITDA multiples
    ev_ebitda_ltm: Optional[float]
    ev_ebitda_fy23: Optional[float]
    ev_ebitda_fy24: Optional[float]

    # P/E multiples
    pe_ltm: Optional[float]
    pe_fy23: Optional[float]
    pe_fy24: Optional[float]


@dataclass
class MultipleStatistics:
    """
    Summary statistics for a specific multiple.
    Matches Excel rows 30-33 (Average, Median, Max, Min).
    """
    average: float
    median: float
    maximum: float
    minimum: float
    count: int
    std_dev: float = 0.0


@dataclass
class ImpliedSharePriceResult:
    """
    Implied share price from applying a multiple to target metrics.
    Matches Excel rows 64-82 for Average/Max/Min calculations.
    """
    scenario: str  # "Average", "Maximum", "Minimum"
    multiple_type: str  # "ev_ebitda" or "pe"
    period: str  # "LTM", "FY2023", "FY2024"
    multiple_value: float
    implied_enterprise_value: float
    implied_equity_value: float
    implied_share_price: float
    current_share_price: float
    premium_discount_pct: float  # (Implied - Current) / Current


# ============================================================================
# DATA CLASSES - TRANSACTION COMPS
# ============================================================================

@dataclass
class PrecedentTransaction:
    """
    Input data for a precedent M&A transaction.
    Matches Excel "transaction comps" sheet rows 15-24.
    """
    announcement_date: str
    target_name: str
    acquirer_name: str
    transaction_value: float  # Enterprise Value of the deal
    target_ebitda_ltm: float
    target_ebitda_fy2022: float  # Next fiscal year at time of deal
    target_ebitda_fy2023: float  # Year after
    status: str = "Completed"
    is_primary: bool = False


@dataclass
class TransactionMultiple:
    """Calculated transaction multiples."""
    announcement_date: str
    target_name: str
    acquirer_name: str
    ev_ebitda_ltm: Optional[float]
    ev_ebitda_fy22: Optional[float]
    ev_ebitda_fy23: Optional[float]
    is_primary: bool


@dataclass
class TransactionCompsOutputs:
    """
    Complete Transaction Comps output.
    Matches Excel "transaction comps" sheet.
    """
    transactions: List[Dict] = field(default_factory=list)

    # Statistics by period
    ltm_stats: Optional[MultipleStatistics] = None
    fy2022_stats: Optional[MultipleStatistics] = None
    fy2023_stats: Optional[MultipleStatistics] = None

    # Counts
    transaction_count: int = 0

    # Metadata
    analysis_date: str = ""
    currency: str = "GBP"

    def to_dict(self) -> Dict:
        return {
            "transactions": self.transactions,
            "statistics": {
                "ltm": self.ltm_stats.to_dict() if self.ltm_stats else None,
                "fy2022": self.fy2022_stats.to_dict() if self.fy2022_stats else None,
                "fy2023": self.fy2023_stats.to_dict() if self.fy2023_stats else None
            },
            "transaction_count": self.transaction_count,
            "metadata": {
                "analysis_date": self.analysis_date,
                "currency": self.currency
            }
        }


# ============================================================================
# MAIN OUTPUT CLASS
# ============================================================================

@dataclass
class TradingCompsOutputs:
    """
    Complete Trading Comps output matching Excel specification.
    Includes all multiples, statistics, and implied valuations.
    """

    # Target company multiples (for reference)
    target_ebitda_ltm: float = 0.0
    target_ebitda_fy23: float = 0.0
    target_ebitda_fy24: float = 0.0
    target_eps_ltm: float = 0.0
    target_eps_fy23: float = 0.0
    target_eps_fy24: float = 0.0

    # Peer multiples list
    peer_multiples: List[Dict] = field(default_factory=list)

    # Statistics by multiple type (rows 30-33 in Excel)
    ev_ebitda_ltm_stats: Optional[MultipleStatistics] = None
    ev_ebitda_fy23_stats: Optional[MultipleStatistics] = None
    ev_ebitda_fy24_stats: Optional[MultipleStatistics] = None
    pe_ltm_stats: Optional[MultipleStatistics] = None
    pe_fy23_stats: Optional[MultipleStatistics] = None
    pe_fy24_stats: Optional[MultipleStatistics] = None

    # Implied share prices by scenario (rows 64-82 in Excel)
    # AVERAGE scenario
    avg_ev_ebitda_ltm_price: float = 0.0
    avg_ev_ebitda_fy23_price: float = 0.0
    avg_ev_ebitda_fy24_price: float = 0.0
    avg_pe_ltm_price: float = 0.0
    avg_pe_fy23_price: float = 0.0
    avg_pe_fy24_price: float = 0.0

    # MAXIMUM scenario
    max_ev_ebitda_ltm_price: float = 0.0
    max_ev_ebitda_fy23_price: float = 0.0
    max_ev_ebitda_fy24_price: float = 0.0
    max_pe_ltm_price: float = 0.0
    max_pe_fy23_price: float = 0.0
    max_pe_fy24_price: float = 0.0

    # MINIMUM scenario
    min_ev_ebitda_ltm_price: float = 0.0
    min_ev_ebitda_fy23_price: float = 0.0
    min_ev_ebitda_fy24_price: float = 0.0
    min_pe_ltm_price: float = 0.0
    min_pe_fy23_price: float = 0.0
    min_pe_fy24_price: float = 0.0

    # Football field chart data (rows 87-93 in Excel)
    chart_data: List[Dict] = field(default_factory=list)

    # Counts and metadata
    peer_count_total: int = 0
    peer_count_after_filtering: int = 0
    analysis_date: str = ""
    currency: str = "GBP"
    primary_multiple: str = "ev_ebitda"
    excluded_peers: List[str] = field(default_factory=list)

    def to_json_schema_format(self) -> Dict:
        """Convert to JSON format matching Excel structure."""
        return {
            "target_metrics": {
                "ebitda_ltm": round(self.target_ebitda_ltm, 1),
                "ebitda_fy2023": round(self.target_ebitda_fy23, 1),
                "ebitda_fy2024": round(self.target_ebitda_fy24, 1),
                "eps_ltm": round(self.target_eps_ltm, 3),
                "eps_fy2023": round(self.target_eps_fy23, 3),
                "eps_fy2024": round(self.target_eps_fy24, 3)
            },
            "peer_multiples": self.peer_multiples,
            "statistics": {
                "ev_ebitda_ltm": self.ev_ebitda_ltm_stats.to_dict() if self.ev_ebitda_ltm_stats else None,
                "ev_ebitda_fy2023": self.ev_ebitda_fy23_stats.to_dict() if self.ev_ebitda_fy23_stats else None,
                "ev_ebitda_fy2024": self.ev_ebitda_fy24_stats.to_dict() if self.ev_ebitda_fy24_stats else None,
                "pe_ltm": self.pe_ltm_stats.to_dict() if self.pe_ltm_stats else None,
                "pe_fy2023": self.pe_fy23_stats.to_dict() if self.pe_fy23_stats else None,
                "pe_fy2024": self.pe_fy24_stats.to_dict() if self.pe_fy24_stats else None
            },
            "implied_share_prices": {
                "average": {
                    "ev_ebitda_ltm": round(self.avg_ev_ebitda_ltm_price, 2),
                    "ev_ebitda_fy2023": round(self.avg_ev_ebitda_fy23_price, 2),
                    "ev_ebitda_fy2024": round(self.avg_ev_ebitda_fy24_price, 2),
                    "pe_ltm": round(self.avg_pe_ltm_price, 2),
                    "pe_fy2023": round(self.avg_pe_fy23_price, 2),
                    "pe_fy2024": round(self.avg_pe_fy24_price, 2)
                },
                "maximum": {
                    "ev_ebitda_ltm": round(self.max_ev_ebitda_ltm_price, 2),
                    "ev_ebitda_fy2023": round(self.max_ev_ebitda_fy23_price, 2),
                    "ev_ebitda_fy2024": round(self.max_ev_ebitda_fy24_price, 2),
                    "pe_ltm": round(self.max_pe_ltm_price, 2),
                    "pe_fy2023": round(self.max_pe_fy23_price, 2),
                    "pe_fy2024": round(self.max_pe_fy24_price, 2)
                },
                "minimum": {
                    "ev_ebitda_ltm": round(self.min_ev_ebitda_ltm_price, 2),
                    "ev_ebitda_fy2023": round(self.min_ev_ebitda_fy23_price, 2),
                    "ev_ebitda_fy2024": round(self.min_ev_ebitda_fy24_price, 2),
                    "pe_ltm": round(self.min_pe_ltm_price, 2),
                    "pe_fy2023": round(self.min_pe_fy23_price, 2),
                    "pe_fy2024": round(self.min_pe_fy24_price, 2)
                }
            },
            "football_field_chart": self.chart_data,
            "peer_count": {
                "total": self.peer_count_total,
                "after_filtering": self.peer_count_after_filtering
            },
            "metadata": {
                "analysis_date": self.analysis_date,
                "currency": self.currency,
                "primary_multiple": self.primary_multiple,
                "excluded_peers": self.excluded_peers
            }
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_json_schema_format(), indent=indent)

    def save_to_file(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.to_json_schema_format(), f, indent=2)


class TradingCompsAnalyzer:
    """Main analyzer class for Trading Comps"""

    def __init__(self, target: TargetCompanyData, peers: List[PeerCompanyData]):
        self.target = target
        self.all_peers = peers
        self.filtered_peers: List[PeerCompanyData] = []
        self.excluded_peers: List[str] = []
        self.exclusion_reasons: Dict[str, str] = {}

    def calculate_peer_multiples(self, peer: PeerCompanyData) -> Dict:
        """
        Calculate all multiples for a single peer.
        Matches Excel columns V-AA for EV/EBITDA and P/E.
        """
        multiples = {
            "ticker": peer.ticker,
            "company_name": peer.company_name,
            "is_primary": peer.is_primary_comparable,

            # EV/EBITDA multiples (Excel columns V, W, X)
            "ev_ebitda_ltm": round(peer.enterprise_value / peer.ebitda_ltm, 2) if peer.ebitda_ltm > 0 else None,
            "ev_ebitda_fy23": round(peer.enterprise_value / peer.ebitda_fy2023, 2) if peer.ebitda_fy2023 > 0 else None,
            "ev_ebitda_fy24": round(peer.enterprise_value / peer.ebitda_fy2024, 2) if peer.ebitda_fy2024 > 0 else None,

            # P/E multiples (Excel columns Y, Z, AA)
            "pe_ltm": round(peer.share_price / peer.eps_ltm, 2) if peer.eps_ltm > 0 else None,
            "pe_fy23": round(peer.share_price / peer.eps_fy2023, 2) if peer.eps_fy2023 > 0 else None,
            "pe_fy24": round(peer.share_price / peer.eps_fy2024, 2) if peer.eps_fy2024 > 0 else None
        }
        return multiples

    def filter_peers_by_iqr(self, multiple_values: List[float], iqr_multiplier: float = 1.5) -> Tuple[List[float], List[int]]:
        """Filter outliers using IQR method"""
        if len(multiple_values) < 4:
            return multiple_values, list(range(len(multiple_values)))

        sorted_values = sorted(multiple_values)
        q1_idx = len(sorted_values) // 4
        q3_idx = 3 * len(sorted_values) // 4

        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr

        filtered_values = []
        kept_indices = []

        for i, val in enumerate(multiple_values):
            if lower_bound <= val <= upper_bound:
                filtered_values.append(val)
                kept_indices.append(i)

        return filtered_values, kept_indices

    def calculate_statistics(self, values: List[float]) -> MultipleStatistics:
        """Calculate comprehensive statistics for a list of values"""
        clean_values = [v for v in values if v is not None and v > 0]

        if len(clean_values) == 0:
            return MultipleStatistics(
                mean=0, median=0, std_dev=0, min=0, max=0, p25=0, p75=0, count=0
            )

        sorted_values = sorted(clean_values)
        n = len(sorted_values)

        mean_val = statistics.mean(clean_values)
        median_val = statistics.median(clean_values)
        std_dev_val = statistics.stdev(clean_values) if n > 1 else 0

        # Percentiles
        p25_idx = n // 4
        p75_idx = (3 * n) // 4

        return MultipleStatistics(
            mean=mean_val,
            median=median_val,
            std_dev=std_dev_val,
            min=min(clean_values),
            max=max(clean_values),
            p25=sorted_values[p25_idx],
            p75=sorted_values[p75_idx],
            count=n
        )

    def calculate_implied_valuation(self, multiple: float, metric_value: float,
                                    metric_type: str) -> ImpliedSharePriceResult:
        """Calculate implied valuation from a multiple"""
        if metric_type in ["ev_ebitda", "ev_sales", "ev_ebit", "ev_fcf"]:
            implied_ev = multiple * metric_value
            implied_equity = implied_ev - self.target.enterprise_value + self.target.market_cap
        else:  # pe, pb, p_fcf
            implied_equity = multiple * metric_value
            implied_ev = implied_equity + self.target.enterprise_value - self.target.market_cap

        implied_share_price = implied_equity / self.target.shares_outstanding
        current_price = self.target.current_stock_price
        upside = (implied_share_price - current_price) / current_price * 100

        return ImpliedSharePriceResult(
            implied_enterprise_value=implied_ev,
            implied_equity_value=implied_equity,
            implied_share_price=implied_share_price,
            current_share_price=current_price,
            upside_downside_pct=upside
        )

    def run_analysis(self, apply_outlier_filtering: bool = True) -> TradingCompsOutputs:
        """Run complete trading comps analysis"""

        # Calculate multiples for all peers
        all_peer_multiples = []
        for peer in self.all_peers:
            multiples = self.calculate_peer_multiples(peer)
            all_peer_multiples.append(multiples)

        self.peer_count_total = len(self.all_peers)

        # Extract multiple values for filtering
        ev_ebitda_values = [m["ev_ebitda_ltm"] for m in all_peer_multiples if m["ev_ebitda_ltm"] is not None]

        # Apply outlier filtering
        if apply_outlier_filtering and len(ev_ebitda_values) >= 4:
            _, kept_indices = self.filter_peers_by_iqr(ev_ebitda_values)

            # Keep peers that pass filtering for EV/EBITDA
            self.filtered_peers = [self.all_peers[i] for i in kept_indices if i < len(self.all_peers)]
            self.excluded_peers = [p.ticker for i, p in enumerate(self.all_peers) if i not in kept_indices]

            for ticker in self.excluded_peers:
                self.exclusion_reasons[ticker] = "Outlier based on IQR filtering"
        else:
            self.filtered_peers = self.all_peers.copy()

        self.peer_count_after_filtering = len(self.filtered_peers)

        # Recalculate multiples for filtered peers
        filtered_peer_multiples = []
        for peer in self.filtered_peers:
            multiples = self.calculate_peer_multiples(peer)
            filtered_peer_multiples.append(multiples)

        # Initialize outputs
        outputs = TradingCompsOutputs()
        outputs.peer_multiples = filtered_peer_multiples
        outputs.peer_count_total = self.peer_count_total
        outputs.peer_count_after_filtering = self.peer_count_after_filtering
        outputs.excluded_peers = self.excluded_peers
        outputs.exclusion_reasons = self.exclusion_reasons
        outputs.outlier_filtering_applied = apply_outlier_filtering

        # Calculate target multiples
        t = self.target
        outputs.ev_ebitda_ltm = t.enterprise_value / t.ebitda_ltm if t.ebitda_ltm > 0 else 0
        outputs.ev_sales_ltm = t.enterprise_value / t.revenue_ltm if t.revenue_ltm > 0 else 0
        outputs.ev_ebit_ltm = t.enterprise_value / t.ebit_ltm if t.ebit_ltm > 0 else 0
        outputs.pe_diluted_ltm = t.market_cap / t.net_income_ltm if t.net_income_ltm > 0 else 0
        outputs.pb_ltm = t.market_cap / t.book_equity if t.book_equity > 0 else 0
        outputs.p_fcf_ltm = t.market_cap / t.free_cash_flow_ltm if t.free_cash_flow_ltm > 0 else 0
        outputs.ev_fcf_ltm = t.enterprise_value / t.free_cash_flow_ltm if t.free_cash_flow_ltm > 0 else 0

        # Calculate peer statistics for each multiple
        ev_ebitda_vals = [m["ev_ebitda_ltm"] for m in filtered_peer_multiples if m["ev_ebitda_ltm"] is not None]
        ev_sales_vals = [m["ev_sales_ltm"] for m in filtered_peer_multiples if m["ev_sales_ltm"] is not None]
        ev_ebit_vals = [m["ev_ebit_ltm"] for m in filtered_peer_multiples if m["ev_ebit_ltm"] is not None]
        pe_vals = [m["pe_diluted_ltm"] for m in filtered_peer_multiples if m["pe_diluted_ltm"] is not None]
        pb_vals = [m["pb_ltm"] for m in filtered_peer_multiples if m["pb_ltm"] is not None]
        p_fcf_vals = [m["p_fcf_ltm"] for m in filtered_peer_multiples if m["p_fcf_ltm"] is not None]
        ev_fcf_vals = [m["ev_fcf_ltm"] for m in filtered_peer_multiples if m["ev_fcf_ltm"] is not None]

        outputs.ev_ebitda_ltm_stats = self.calculate_statistics(ev_ebitda_ltm_vals)
        outputs.ev_ebitda_fy23_stats = self.calculate_statistics(ev_ebitda_fy23_vals)
        outputs.ev_ebitda_fy24_stats = self.calculate_statistics(ev_ebitda_fy24_vals)
        outputs.pe_ltm_stats = self.calculate_statistics(pe_ltm_vals)
        outputs.pe_fy23_stats = self.calculate_statistics(pe_fy23_vals)
        outputs.pe_fy24_stats = self.calculate_statistics(pe_fy24_vals)

        # Calculate implied valuations using median multiples
        if outputs.ev_ebitda_stats and outputs.ev_ebitda_stats.median > 0:
            outputs.implied_by_ev_ebitda = self.calculate_implied_valuation(
                outputs.ev_ebitda_stats.median, t.ebitda_ltm, "ev_ebitda"
            )

        if outputs.ev_sales_stats and outputs.ev_sales_stats.median > 0:
            outputs.implied_by_ev_sales = self.calculate_implied_valuation(
                outputs.ev_sales_stats.median, t.revenue_ltm, "ev_sales"
            )

        if outputs.ev_ebit_stats and outputs.ev_ebit_stats.median > 0:
            outputs.implied_by_ev_ebit = self.calculate_implied_valuation(
                outputs.ev_ebit_stats.median, t.ebit_ltm, "ev_ebit"
            )

        if outputs.pe_stats and outputs.pe_stats.median > 0:
            outputs.implied_by_pe = self.calculate_implied_valuation(
                outputs.pe_stats.median, t.net_income_ltm, "pe"
            )

        if outputs.pb_stats and outputs.pb_stats.median > 0:
            outputs.implied_by_pb = self.calculate_implied_valuation(
                outputs.pb_stats.median, t.book_equity, "pb"
            )

        if outputs.p_fcf_stats and outputs.p_fcf_stats.median > 0:
            outputs.implied_by_p_fcf = self.calculate_implied_valuation(
                outputs.p_fcf_stats.median, t.free_cash_flow_ltm, "p_fcf"
            )

        if outputs.ev_fcf_stats and outputs.ev_fcf_stats.median > 0:
            outputs.implied_by_ev_fcf = self.calculate_implied_valuation(
                outputs.ev_fcf_stats.median, t.free_cash_flow_ltm, "ev_fcf"
            )

        return outputs


def fetch_comps_inputs(ticker: str, peer_tickers: Optional[List[str]] = None) -> Tuple[TargetCompanyData, List[PeerCompanyData]]:
    """
    Fetch target and peer data from yfinance
    Returns target company data and list of peer company data
    """
    import yfinance as yf

    # Fetch target data
    target_yf = yf.Ticker(ticker)
    info = target_yf.info

    # Extract target metrics
    target = TargetCompanyData(
        ticker=ticker,
        company_name=info.get("longName", ticker),
        market_cap=info.get("marketCap", 0),
        enterprise_value=info.get("enterpriseValue", 0),
        revenue_ltm=info.get("totalRevenue", 0) or info.get("revenue", 0),
        ebitda_ltm=info.get("ebitda", 0),
        ebit_ltm=info.get("operatingIncome", 0),
        net_income_ltm=info.get("netIncomeToCommon", 0) or info.get("trailingEps", 0) * info.get("sharesOutstanding", 1),
        free_cash_flow_ltm=info.get("freeCashflow", 0),
        book_equity=info.get("totalStockholderEquity", 0),
        shares_outstanding=info.get("sharesOutstanding", 1),
        current_stock_price=info.get("currentPrice", 0) or info.get("regularMarketPrice", 0),
        currency=info.get("currency", "USD")
    )

    # If no peer tickers provided, use AI to suggest peers
    if peer_tickers is None or len(peer_tickers) == 0:
        print(f"🤖 No peer tickers provided. Using AI to suggest peers for {ticker}...")
        ai_suggestions = suggest_peer_companies(ticker, num_peers=10)
        if ai_suggestions and len(ai_suggestions) > 0:
            peer_tickers = [p["ticker"] for p in ai_suggestions]
            print(f"✅ AI suggested {len(peer_tickers)} peers: {', '.join(peer_tickers)}")
        else:
            print("⚠️ AI peer suggestion failed. Please provide peer tickers manually.")
            return target, []
    # Fetch peer data
    peers = []
    for peer_ticker in peer_tickers:
        try:
            peer_yf = yf.Ticker(peer_ticker)
            peer_info = peer_yf.info

            peer = PeerCompanyData(
                ticker=peer_ticker,
                company_name=peer_info.get("longName", peer_ticker),
                market_cap=peer_info.get("marketCap", 0),
                enterprise_value=peer_info.get("enterpriseValue", 0),
                revenue_ltm=peer_info.get("totalRevenue", 0) or peer_info.get("revenue", 0),
                ebitda_ltm=peer_info.get("ebitda", 0),
                ebit_ltm=peer_info.get("operatingIncome", 0),
                net_income_ltm=peer_info.get("netIncomeToCommon", 0) or peer_info.get("trailingEps", 0) * peer_info.get("sharesOutstanding", 1),
                free_cash_flow_ltm=peer_info.get("freeCashflow", 0),
                book_equity=peer_info.get("totalStockholderEquity", 0),
                shares_outstanding=peer_info.get("sharesOutstanding", 1),
                current_stock_price=peer_info.get("currentPrice", 0) or peer_info.get("regularMarketPrice", 0),
                industry=peer_info.get("industry", ""),
                sector=peer_info.get("sector", ""),
                selection_reason="Industry peer"
            )
            peers.append(peer)
        except Exception as e:
            print(f"Warning: Could not fetch data for {peer_ticker}: {e}")
# ============================================================================
    return target, peers

# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example with manual inputs matching Excel specification
    print("=" * 70)
    print("TRADING COMPS ANALYSIS - Excel-Compatible Implementation")
    print("=" * 70)

    # Target company (from Excel "Trading Comps" sheet rows 58-82)
    target = TargetCompanyData(
        ticker="TEST",
        company_name="Test Company",
        market_cap=3800,  # GBP mm
        enterprise_value=5525,
        ebitda_ltm=1234,  # D60
        ebitda_fy2023=1320,  # F60
        ebitda_fy2024=1360,  # H60
        eps_ltm=0.325,  # E61
        eps_fy2023=0.3575,  # G61
        eps_fy2024=0.3754,  # I61
        net_debt=1725,  # D65
        shares_outstanding=1525,  # D66 (mm)
        current_stock_price=2.49,
        currency="GBP",
        analysis_date="2022-08-31"
    )

    # Primary comparable - TSCO (from Excel "TSCO" sheet)
    tsco = PeerCompanyData(
        ticker="TSCO",
        company_name="Tesco PLC",
        market_cap=18500,
        enterprise_value=26000,
        share_price=2.487,
        shares_outstanding=7746,
        ebitda_ltm=4543,  # G90
        ebitda_fy2023=4435.76,  # H90
        ebitda_fy2024=4596.49,  # I90
        eps_ltm=0.218,  # G95
        eps_fy2023=0.21,  # H95
        eps_fy2024=0.22,  # I95
        is_primary_comparable=True
    )

    # Run analysis
    analyzer = TradingCompsAnalyzer(target, [tsco])
    outputs = analyzer.run_analysis(apply_outlier_filtering=False)

    # Print results
    print(f"\nTarget: {target.ticker} ({target.company_name})")
    print(f"Currency: {target.currency}")
    print(f"Analysis Date: {outputs.analysis_date}")
    print(f"Peer Count: {outputs.peer_count_total}")

    print("\n--- Target Metrics ---")
    print(f"EBITDA LTM: £{target.ebitda_ltm}mm")
    print(f"EBITDA FY23: £{target.ebitda_fy2023}mm")
    print(f"EBITDA FY24: £{target.ebitda_fy2024}mm")
    print(f"EPS LTM: £{target.eps_ltm}")
    print(f"EPS FY23: £{target.eps_fy2023}")
    print(f"EPS FY24: £{target.eps_fy2024}")

    print("\n--- Peer Multiples ---")
    for p in outputs.peer_multiples:
        print(f"\n{p['ticker']} ({p['company_name']}):")
        print(f"  EV/EBITDA: LTM={p['ev_ebitda_ltm']}x, FY23={p['ev_ebitda_fy23']}x, FY24={p['ev_ebitda_fy24']}x")
        print(f"  P/E: LTM={p['pe_ltm']}x, FY23={p['pe_fy23']}x, FY24={p['pe_fy24']}x")

    print("\n--- Statistics (Average / Median / Max / Min) ---")
    if outputs.ev_ebitda_ltm_stats:
        s = outputs.ev_ebitda_ltm_stats
        print(f"EV/EBITDA LTM: {s.average:.2f}x / {s.median:.2f}x / {s.maximum:.2f}x / {s.minimum:.2f}x")
    if outputs.pe_ltm_stats:
        s = outputs.pe_ltm_stats
        print(f"P/E LTM:       {s.average:.2f}x / {s.median:.2f}x / {s.maximum:.2f}x / {s.minimum:.2f}x")

    print("\n--- Implied Share Prices (using Average Multiples) ---")
    print(f"LTM EV/EBITDA: £{outputs.avg_ev_ebitda_ltm_price:.2f} ({(outputs.avg_ev_ebitda_ltm_price/target.current_stock_price-1)*100:+.1f}% vs current)")
    print(f"FY23 EV/EBITDA: £{outputs.avg_ev_ebitda_fy23_price:.2f}")
    print(f"FY24 EV/EBITDA: £{outputs.avg_ev_ebitda_fy24_price:.2f}")
    print(f"LTM P/E: £{outputs.avg_pe_ltm_price:.2f}")

    print("\n--- Football Field Range ---")
    for row in outputs.chart_data:
        print(f"{row['metric']}: £{row['min']:.2f} - £{row['average']:.2f} - £{row['max']:.2f}")

    print("\n--- JSON Output Preview ---")
    print(outputs.to_json(indent=2)[:500] + "...")

    # Save to file
    outputs.save_to_file("trading_comps_output.json")
    print("\n✓ Results saved to trading_comps_output.json")

"""
Comparable Company Analysis (Trading Comps) & Precedent Transaction Model
Complete implementation matching Excel specification with:
- Trading Comps: EV/EBITDA and P/E multiples for LTM, FY2023, FY2024
- Transaction Comps: Precedent M&A deal multiples
- Implied share price calculations using Min/Average/Max multiples
- Football field chart data generation
All figures can be in any currency (USD, GBP, etc.)
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import statistics


# ============================================================================
# DATA CLASSES - TRADING COMPS
# ============================================================================

@dataclass
class TargetCompanyData:
    """
    Input data for the target company being valued.
    Matches Excel "Trading Comps" sheet rows 58-82.
    """
    ticker: str
    company_name: str
    market_cap: float  # Equity value (GBP mm or USD mm)
    enterprise_value: float  # EV (GBP mm or USD mm)

    # Revenue & Profitability metrics (all in same currency units as market cap)
    revenue_ltm: float = 0.0
    ebitda_ltm: float = 0.0
    ebitda_fy2023: float = 0.0  # Next fiscal year estimate
    ebitda_fy2024: float = 0.0  # Year after estimate
    ebit_ltm: float = 0.0
    net_income_ltm: float = 0.0
    free_cash_flow_ltm: float = 0.0
    book_equity: float = 0.0

    # EPS metrics (per share, same currency as stock price)
    eps_ltm: float = 0.0
    eps_fy2023: float = 0.0
    eps_fy2024: float = 0.0

    # Capital structure
    net_debt: float = 0.0
    shares_outstanding: float = 0.0  # In millions
    current_stock_price: float = 0.0  # Per share

    # Metadata
    currency: str = "GBP"
    analysis_date: str = ""


@dataclass
class PeerCompanyData:
    """
    Input data for each peer company.
    Matches Excel "TSCO" sheet structure with LTM and forward estimates.
    """
    ticker: str
    company_name: str

    # Valuation metrics
    market_cap: float = 0.0
    enterprise_value: float = 0.0
    share_price: float = 0.0
    shares_outstanding: float = 0.0

    # Revenue & EBITDA metrics
    revenue_ltm: float = 0.0
    ebitda_ltm: float = 0.0
    ebitda_fy2023: float = 0.0
    ebitda_fy2024: float = 0.0
    ebit_ltm: float = 0.0

    # EPS metrics
    eps_ltm: float = 0.0
    eps_fy2023: float = 0.0
    eps_fy2024: float = 0.0

    # Additional metrics for extended multiples
    net_income_ltm: float = 0.0
    free_cash_flow_ltm: float = 0.0
    book_equity: float = 0.0

    # Optional metadata
    industry: str = ""
    sector: str = ""
    selection_reason: str = "Industry peer"
    is_primary_comparable: bool = False  # Like TSCO in Excel


@dataclass
class PeerMultiples:
    """Calculated multiples for a single peer company."""
    ticker: str
    company_name: str
    is_primary: bool

    # EV/EBITDA multiples
    ev_ebitda_ltm: Optional[float] = None
    ev_ebitda_fy23: Optional[float] = None
    ev_ebitda_fy24: Optional[float] = None

    # P/E multiples
    pe_ltm: Optional[float] = None
    pe_fy23: Optional[float] = None
    pe_fy24: Optional[float] = None

    # Additional multiples (EV/Sales, EV/EBIT, etc.)
    ev_sales_ltm: Optional[float] = None
    ev_ebit_ltm: Optional[float] = None
    pb_ltm: Optional[float] = None
    p_fcf_ltm: Optional[float] = None
    ev_fcf_ltm: Optional[float] = None


@dataclass
class MultipleStatistics:
    """
    Summary statistics for a specific multiple.
    Matches Excel rows 30-33 (Average, Median, Max, Min).
    """
    average: float = 0.0
    median: float = 0.0
    maximum: float = 0.0
    minimum: float = 0.0
    count: int = 0
    std_dev: float = 0.0


@dataclass
class ImpliedSharePriceResult:
    """
    Implied share price from applying a multiple to target metrics.
    Matches Excel rows 64-82 for Average/Max/Min calculations.
    """
    scenario: str = ""  # "Average", "Maximum", "Minimum"
    multiple_type: str = ""  # "ev_ebitda" or "pe"
    period: str = ""  # "LTM", "FY2023", "FY2024"
    multiple_value: float = 0.0
    implied_enterprise_value: float = 0.0
    implied_equity_value: float = 0.0
    implied_share_price: float = 0.0
    current_share_price: float = 0.0
    premium_discount_pct: float = 0.0  # (Implied - Current) / Current


# ============================================================================
# DATA CLASSES - TRANSACTION COMPS
# ============================================================================

@dataclass
class PrecedentTransaction:
    """
    Input data for a precedent M&A transaction.
    Matches Excel "transaction comps" sheet rows 15-24.
    """
    announcement_date: str = ""
    target_name: str = ""
    acquirer_name: str = ""
    transaction_value: float = 0.0  # Enterprise Value of the deal
    target_ebitda_ltm: float = 0.0
    target_ebitda_fy2022: float = 0.0  # Next fiscal year at time of deal
    target_ebitda_fy2023: float = 0.0  # Year after
    status: str = "Completed"
    is_primary: bool = False


@dataclass
class TransactionMultiple:
    """Calculated transaction multiples."""
    announcement_date: str = ""
    target_name: str = ""
    acquirer_name: str = ""
    ev_ebitda_ltm: Optional[float] = None
    ev_ebitda_fy22: Optional[float] = None
    ev_ebitda_fy23: Optional[float] = None
    is_primary: bool = False


@dataclass
class TransactionCompsOutputs:
    """
    Complete Transaction Comps output.
    Matches Excel "transaction comps" sheet.
    """
    transactions: List[Dict] = field(default_factory=list)

    # Statistics by period
    ltm_stats: Optional[MultipleStatistics] = None
    fy2022_stats: Optional[MultipleStatistics] = None
    fy2023_stats: Optional[MultipleStatistics] = None

    # Counts
    transaction_count: int = 0

    # Metadata
    analysis_date: str = ""
    currency: str = "GBP"

    def to_dict(self) -> Dict:
        return {
            "transactions": self.transactions,
            "statistics": {
                "ltm": self.ltm_stats.to_dict() if self.ltm_stats else None,
                "fy2022": self.fy2022_stats.to_dict() if self.fy2022_stats else None,
                "fy2023": self.fy2023_stats.to_dict() if self.fy2023_stats else None
            },
            "transaction_count": self.transaction_count,
            "metadata": {
                "analysis_date": self.analysis_date,
                "currency": self.currency
            }
        }


# ============================================================================
# MAIN OUTPUT CLASS
# ============================================================================

@dataclass
class TradingCompsOutputs:
    """
    Complete Trading Comps output matching Excel specification.
    Includes all multiples, statistics, and implied valuations.
    """

    # Target company multiples (for reference)
    target_ebitda_ltm: float = 0.0
    target_ebitda_fy23: float = 0.0
    target_ebitda_fy24: float = 0.0
    target_eps_ltm: float = 0.0
    target_eps_fy23: float = 0.0
    target_eps_fy24: float = 0.0

    # Peer multiples list
    peer_multiples: List[Dict] = field(default_factory=list)

    # Statistics by multiple type (rows 30-33 in Excel)
    ev_ebitda_ltm_stats: Optional[MultipleStatistics] = None
    ev_ebitda_fy23_stats: Optional[MultipleStatistics] = None
    ev_ebitda_fy24_stats: Optional[MultipleStatistics] = None
    pe_ltm_stats: Optional[MultipleStatistics] = None
    pe_fy23_stats: Optional[MultipleStatistics] = None
    pe_fy24_stats: Optional[MultipleStatistics] = None

    # Implied share prices by scenario (rows 64-82 in Excel)
    # AVERAGE scenario
    avg_ev_ebitda_ltm_price: float = 0.0
    avg_ev_ebitda_fy23_price: float = 0.0
    avg_ev_ebitda_fy24_price: float = 0.0
    avg_pe_ltm_price: float = 0.0
    avg_pe_fy23_price: float = 0.0
    avg_pe_fy24_price: float = 0.0

    # MAXIMUM scenario
    max_ev_ebitda_ltm_price: float = 0.0
    max_ev_ebitda_fy23_price: float = 0.0
    max_ev_ebitda_fy24_price: float = 0.0
    max_pe_ltm_price: float = 0.0
    max_pe_fy23_price: float = 0.0
    max_pe_fy24_price: float = 0.0

    # MINIMUM scenario
    min_ev_ebitda_ltm_price: float = 0.0
    min_ev_ebitda_fy23_price: float = 0.0
    min_ev_ebitda_fy24_price: float = 0.0
    min_pe_ltm_price: float = 0.0
    min_pe_fy23_price: float = 0.0
    min_pe_fy24_price: float = 0.0

    # Football field chart data (rows 87-93 in Excel)
    chart_data: List[Dict] = field(default_factory=list)

    # Counts and metadata
    peer_count_total: int = 0
    peer_count_after_filtering: int = 0
    analysis_date: str = ""
    currency: str = "GBP"
    primary_multiple: str = "ev_ebitda"
    excluded_peers: List[str] = field(default_factory=list)

    def to_json_schema_format(self) -> Dict:
        """Convert to JSON format matching Excel structure."""
        return {
            "target_metrics": {
                "ebitda_ltm": round(self.target_ebitda_ltm, 1),
                "ebitda_fy2023": round(self.target_ebitda_fy23, 1),
                "ebitda_fy2024": round(self.target_ebitda_fy24, 1),
                "eps_ltm": round(self.target_eps_ltm, 3),
                "eps_fy2023": round(self.target_eps_fy23, 3),
                "eps_fy2024": round(self.target_eps_fy24, 3)
            },
            "peer_multiples": self.peer_multiples,
            "statistics": {
                "ev_ebitda_ltm": self.ev_ebitda_ltm_stats.to_dict() if self.ev_ebitda_ltm_stats else None,
                "ev_ebitda_fy2023": self.ev_ebitda_fy23_stats.to_dict() if self.ev_ebitda_fy23_stats else None,
                "ev_ebitda_fy2024": self.ev_ebitda_fy24_stats.to_dict() if self.ev_ebitda_fy24_stats else None,
                "pe_ltm": self.pe_ltm_stats.to_dict() if self.pe_ltm_stats else None,
                "pe_fy2023": self.pe_fy23_stats.to_dict() if self.pe_fy23_stats else None,
                "pe_fy2024": self.pe_fy24_stats.to_dict() if self.pe_fy24_stats else None
            },
            "implied_share_prices": {
                "average": {
                    "ev_ebitda_ltm": round(self.avg_ev_ebitda_ltm_price, 2),
                    "ev_ebitda_fy2023": round(self.avg_ev_ebitda_fy23_price, 2),
                    "ev_ebitda_fy2024": round(self.avg_ev_ebitda_fy24_price, 2),
                    "pe_ltm": round(self.avg_pe_ltm_price, 2),
                    "pe_fy2023": round(self.avg_pe_fy23_price, 2),
                    "pe_fy2024": round(self.avg_pe_fy24_price, 2)
                },
                "maximum": {
                    "ev_ebitda_ltm": round(self.max_ev_ebitda_ltm_price, 2),
                    "ev_ebitda_fy2023": round(self.max_ev_ebitda_fy23_price, 2),
                    "ev_ebitda_fy2024": round(self.max_ev_ebitda_fy24_price, 2),
                    "pe_ltm": round(self.max_pe_ltm_price, 2),
                    "pe_fy2023": round(self.max_pe_fy23_price, 2),
                    "pe_fy2024": round(self.max_pe_fy24_price, 2)
                },
                "minimum": {
                    "ev_ebitda_ltm": round(self.min_ev_ebitda_ltm_price, 2),
                    "ev_ebitda_fy2023": round(self.min_ev_ebitda_fy23_price, 2),
                    "ev_ebitda_fy2024": round(self.min_ev_ebitda_fy24_price, 2),
                    "pe_ltm": round(self.min_pe_ltm_price, 2),
                    "pe_fy2023": round(self.min_pe_fy23_price, 2),
                    "pe_fy2024": round(self.min_pe_fy24_price, 2)
                }
            },
            "football_field_chart": self.chart_data,
            "peer_count": {
                "total": self.peer_count_total,
                "after_filtering": self.peer_count_after_filtering
            },
            "metadata": {
                "analysis_date": self.analysis_date,
                "currency": self.currency,
                "primary_multiple": self.primary_multiple,
                "excluded_peers": self.excluded_peers
            }
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_json_schema_format(), indent=indent)

    def save_to_file(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.to_json_schema_format(), f, indent=2)


class TradingCompsAnalyzer:
    """Main analyzer class for Trading Comps"""

    def __init__(self, target: TargetCompanyData, peers: List[PeerCompanyData]):
        self.target = target
        self.all_peers = peers
        self.filtered_peers: List[PeerCompanyData] = []
        self.excluded_peers: List[str] = []
        self.exclusion_reasons: Dict[str, str] = {}

    def calculate_peer_multiples(self, peer: PeerCompanyData) -> Dict:
        """
        Calculate all multiples for a single peer.
        Matches Excel columns V-AA for EV/EBITDA and P/E.
        """
        multiples = {
            "ticker": peer.ticker,
            "company_name": peer.company_name,
            "is_primary": peer.is_primary_comparable,

            # EV/EBITDA multiples (Excel columns V, W, X)
            "ev_ebitda_ltm": round(peer.enterprise_value / peer.ebitda_ltm, 2) if peer.ebitda_ltm > 0 else None,
            "ev_ebitda_fy23": round(peer.enterprise_value / peer.ebitda_fy2023, 2) if peer.ebitda_fy2023 > 0 else None,
            "ev_ebitda_fy24": round(peer.enterprise_value / peer.ebitda_fy2024, 2) if peer.ebitda_fy2024 > 0 else None,

            # P/E multiples (Excel columns Y, Z, AA)
            "pe_ltm": round(peer.share_price / peer.eps_ltm, 2) if peer.eps_ltm > 0 else None,
            "pe_fy23": round(peer.share_price / peer.eps_fy2023, 2) if peer.eps_fy2023 > 0 else None,
            "pe_fy24": round(peer.share_price / peer.eps_fy2024, 2) if peer.eps_fy2024 > 0 else None
        }
        return multiples

    def filter_peers_by_iqr(self, multiple_values: List[float], iqr_multiplier: float = 1.5) -> Tuple[List[float], List[int]]:
        """Filter outliers using IQR method"""
        if len(multiple_values) < 4:
            return multiple_values, list(range(len(multiple_values)))

        sorted_values = sorted(multiple_values)
        q1_idx = len(sorted_values) // 4
        q3_idx = 3 * len(sorted_values) // 4

        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr

        filtered_values = []
        kept_indices = []

        for i, val in enumerate(multiple_values):
            if lower_bound <= val <= upper_bound:
                filtered_values.append(val)
                kept_indices.append(i)

        return filtered_values, kept_indices

    def calculate_statistics(self, values: List[float]) -> MultipleStatistics:
        """Calculate comprehensive statistics for a list of values"""
        clean_values = [v for v in values if v is not None and v > 0]

        if len(clean_values) == 0:
            return MultipleStatistics(
                average=0, median=0, std_dev=0, minimum=0, maximum=0, count=0
            )

        sorted_values = sorted(clean_values)
        n = len(sorted_values)

        mean_val = statistics.mean(clean_values)
        median_val = statistics.median(clean_values)
        std_dev_val = statistics.stdev(clean_values) if n > 1 else 0

        return MultipleStatistics(
            average=mean_val,
            median=median_val,
            std_dev=std_dev_val,
            minimum=min(clean_values),
            maximum=max(clean_values),
            count=n
        )

    def calculate_implied_valuation(self, multiple: float, metric_value: float,
                                    metric_type: str) -> ImpliedSharePriceResult:
        """Calculate implied valuation from a multiple"""
        if metric_type in ["ev_ebitda", "ev_sales", "ev_ebit", "ev_fcf"]:
            implied_ev = multiple * metric_value
            implied_equity = implied_ev - self.target.enterprise_value + self.target.market_cap
        else:  # pe, pb, p_fcf
            implied_equity = multiple * metric_value
            implied_ev = implied_equity + self.target.enterprise_value - self.target.market_cap

        implied_share_price = implied_equity / self.target.shares_outstanding
        current_price = self.target.current_stock_price
        upside = (implied_share_price - current_price) / current_price * 100

        return ImpliedSharePriceResult(
            implied_enterprise_value=implied_ev,
            implied_equity_value=implied_equity,
            implied_share_price=implied_share_price,
            current_share_price=current_price,
            premium_discount_pct=upside
        )

    def run_analysis(self, apply_outlier_filtering: bool = True) -> TradingCompsOutputs:
        """Run complete trading comps analysis"""

        # Calculate multiples for all peers
        all_peer_multiples = []
        for peer in self.all_peers:
            multiples = self.calculate_peer_multiples(peer)
            all_peer_multiples.append(multiples)

        self.peer_count_total = len(self.all_peers)

        # Extract multiple values for filtering
        ev_ebitda_values = [m["ev_ebitda_ltm"] for m in all_peer_multiples if m["ev_ebitda_ltm"] is not None]

        # Apply outlier filtering
        if apply_outlier_filtering and len(ev_ebitda_values) >= 4:
            _, kept_indices = self.filter_peers_by_iqr(ev_ebitda_values)

            # Keep peers that pass filtering for EV/EBITDA
            self.filtered_peers = [self.all_peers[i] for i in kept_indices if i < len(self.all_peers)]
            self.excluded_peers = [p.ticker for i, p in enumerate(self.all_peers) if i not in kept_indices]

            for ticker in self.excluded_peers:
                self.exclusion_reasons[ticker] = "Outlier based on IQR filtering"
        else:
            self.filtered_peers = self.all_peers.copy()

        self.peer_count_after_filtering = len(self.filtered_peers)

        # Recalculate multiples for filtered peers
        filtered_peer_multiples = []
        for peer in self.filtered_peers:
            multiples = self.calculate_peer_multiples(peer)
            filtered_peer_multiples.append(multiples)

        # Initialize outputs
        outputs = TradingCompsOutputs()
        outputs.peer_multiples = filtered_peer_multiples
        outputs.peer_count_total = self.peer_count_total
        outputs.peer_count_after_filtering = self.peer_count_after_filtering
        outputs.excluded_peers = self.excluded_peers
        outputs.exclusion_reasons = self.exclusion_reasons
        outputs.outlier_filtering_applied = apply_outlier_filtering

        # Calculate target multiples
        t = self.target
        outputs.ev_ebitda_ltm = t.enterprise_value / t.ebitda_ltm if t.ebitda_ltm > 0 else 0
        outputs.ev_sales_ltm = t.enterprise_value / t.revenue_ltm if t.revenue_ltm > 0 else 0
        outputs.ev_ebit_ltm = t.enterprise_value / t.ebit_ltm if t.ebit_ltm > 0 else 0
        outputs.pe_diluted_ltm = t.market_cap / t.net_income_ltm if t.net_income_ltm > 0 else 0
        outputs.pb_ltm = t.market_cap / t.book_equity if t.book_equity > 0 else 0
        outputs.p_fcf_ltm = t.market_cap / t.free_cash_flow_ltm if t.free_cash_flow_ltm > 0 else 0
        outputs.ev_fcf_ltm = t.enterprise_value / t.free_cash_flow_ltm if t.free_cash_flow_ltm > 0 else 0

        # Calculate peer statistics for each multiple
        ev_ebitda_ltm_vals = [m["ev_ebitda_ltm"] for m in filtered_peer_multiples if m["ev_ebitda_ltm"] is not None]
        ev_ebitda_fy23_vals = [m["ev_ebitda_fy23"] for m in filtered_peer_multiples if m["ev_ebitda_fy23"] is not None]
        ev_ebitda_fy24_vals = [m["ev_ebitda_fy24"] for m in filtered_peer_multiples if m["ev_ebitda_fy24"] is not None]
        pe_ltm_vals = [m["pe_ltm"] for m in filtered_peer_multiples if m["pe_ltm"] is not None]
        pe_fy23_vals = [m["pe_fy23"] for m in filtered_peer_multiples if m["pe_fy23"] is not None]
        pe_fy24_vals = [m["pe_fy24"] for m in filtered_peer_multiples if m["pe_fy24"] is not None]

        outputs.ev_ebitda_ltm_stats = self.calculate_statistics(ev_ebitda_ltm_vals)
        outputs.ev_ebitda_fy23_stats = self.calculate_statistics(ev_ebitda_fy23_vals)
        outputs.ev_ebitda_fy24_stats = self.calculate_statistics(ev_ebitda_fy24_vals)
        outputs.pe_ltm_stats = self.calculate_statistics(pe_ltm_vals)
        outputs.pe_fy23_stats = self.calculate_statistics(pe_fy23_vals)
        outputs.pe_fy24_stats = self.calculate_statistics(pe_fy24_vals)

        # Calculate implied valuations using AVERAGE, MAX, MIN multiples (matching Excel rows 64-82)
        # Per Excel spec: Implied EV = Multiple × Target EBITDA, then Equity = EV - Net Debt, Price = Equity / Shares
        
        # Helper function to calculate implied share price from multiple
        def calc_implied_price(multiple, ebitda, period_name):
            implied_ev = multiple * ebitda
            implied_equity = implied_ev - t.net_debt
            implied_price = implied_equity / t.shares_outstanding
            return implied_price
        
        def calc_implied_pe(multiple, eps):
            return multiple * eps
        
        # AVERAGE scenario (Excel rows 64-68)
        if outputs.ev_ebitda_ltm_stats and outputs.ev_ebitda_ltm_stats.average > 0:
            outputs.avg_ev_ebitda_ltm_price = calc_implied_price(outputs.ev_ebitda_ltm_stats.average, t.ebitda_ltm, "LTM")
        if outputs.ev_ebitda_fy23_stats and outputs.ev_ebitda_fy23_stats.average > 0:
            outputs.avg_ev_ebitda_fy23_price = calc_implied_price(outputs.ev_ebitda_fy23_stats.average, t.ebitda_fy2023, "FY23")
        if outputs.ev_ebitda_fy24_stats and outputs.ev_ebitda_fy24_stats.average > 0:
            outputs.avg_ev_ebitda_fy24_price = calc_implied_price(outputs.ev_ebitda_fy24_stats.average, t.ebitda_fy2024, "FY24")
        
        if outputs.pe_ltm_stats and outputs.pe_ltm_stats.average > 0:
            outputs.avg_pe_ltm_price = calc_implied_pe(outputs.pe_ltm_stats.average, t.eps_ltm)
        if outputs.pe_fy23_stats and outputs.pe_fy23_stats.average > 0:
            outputs.avg_pe_fy23_price = calc_implied_pe(outputs.pe_fy23_stats.average, t.eps_fy2023)
        if outputs.pe_fy24_stats and outputs.pe_fy24_stats.average > 0:
            outputs.avg_pe_fy24_price = calc_implied_pe(outputs.pe_fy24_stats.average, t.eps_fy2024)
        
        # MAXIMUM scenario (Excel rows 71-75)
        if outputs.ev_ebitda_ltm_stats and outputs.ev_ebitda_ltm_stats.maximum > 0:
            outputs.max_ev_ebitda_ltm_price = calc_implied_price(outputs.ev_ebitda_ltm_stats.maximum, t.ebitda_ltm, "LTM")
        if outputs.ev_ebitda_fy23_stats and outputs.ev_ebitda_fy23_stats.maximum > 0:
            outputs.max_ev_ebitda_fy23_price = calc_implied_price(outputs.ev_ebitda_fy23_stats.maximum, t.ebitda_fy2023, "FY23")
        if outputs.ev_ebitda_fy24_stats and outputs.ev_ebitda_fy24_stats.maximum > 0:
            outputs.max_ev_ebitda_fy24_price = calc_implied_price(outputs.ev_ebitda_fy24_stats.maximum, t.ebitda_fy2024, "FY24")
        
        if outputs.pe_ltm_stats and outputs.pe_ltm_stats.maximum > 0:
            outputs.max_pe_ltm_price = calc_implied_pe(outputs.pe_ltm_stats.maximum, t.eps_ltm)
        if outputs.pe_fy23_stats and outputs.pe_fy23_stats.maximum > 0:
            outputs.max_pe_fy23_price = calc_implied_pe(outputs.pe_fy23_stats.maximum, t.eps_fy2023)
        if outputs.pe_fy24_stats and outputs.pe_fy24_stats.maximum > 0:
            outputs.max_pe_fy24_price = calc_implied_pe(outputs.pe_fy24_stats.maximum, t.eps_fy2024)
        
        # MINIMUM scenario (Excel rows 78-82)
        if outputs.ev_ebitda_ltm_stats and outputs.ev_ebitda_ltm_stats.minimum > 0:
            outputs.min_ev_ebitda_ltm_price = calc_implied_price(outputs.ev_ebitda_ltm_stats.minimum, t.ebitda_ltm, "LTM")
        if outputs.ev_ebitda_fy23_stats and outputs.ev_ebitda_fy23_stats.minimum > 0:
            outputs.min_ev_ebitda_fy23_price = calc_implied_price(outputs.ev_ebitda_fy23_stats.minimum, t.ebitda_fy2023, "FY23")
        if outputs.ev_ebitda_fy24_stats and outputs.ev_ebitda_fy24_stats.minimum > 0:
            outputs.min_ev_ebitda_fy24_price = calc_implied_price(outputs.ev_ebitda_fy24_stats.minimum, t.ebitda_fy2024, "FY24")
        
        if outputs.pe_ltm_stats and outputs.pe_ltm_stats.minimum > 0:
            outputs.min_pe_ltm_price = calc_implied_pe(outputs.pe_ltm_stats.minimum, t.eps_ltm)
        if outputs.pe_fy23_stats and outputs.pe_fy23_stats.minimum > 0:
            outputs.min_pe_fy23_price = calc_implied_pe(outputs.pe_fy23_stats.minimum, t.eps_fy2023)
        if outputs.pe_fy24_stats and outputs.pe_fy24_stats.minimum > 0:
            outputs.min_pe_fy24_price = calc_implied_pe(outputs.pe_fy24_stats.minimum, t.eps_fy2024)
        
        # Build football field chart data (Excel rows 87-93)
        outputs.chart_data = [
            {
                "metric": "LTM EV/EBITDA",
                "min": outputs.min_ev_ebitda_ltm_price,
                "max": outputs.max_ev_ebitda_ltm_price,
                "average": outputs.avg_ev_ebitda_ltm_price
            },
            {
                "metric": "FY2023 EV/EBITDA",
                "min": outputs.min_ev_ebitda_fy23_price,
                "max": outputs.max_ev_ebitda_fy23_price,
                "average": outputs.avg_ev_ebitda_fy23_price
            },
            {
                "metric": "FY2024 EV/EBITDA",
                "min": outputs.min_ev_ebitda_fy24_price,
                "max": outputs.max_ev_ebitda_fy24_price,
                "average": outputs.avg_ev_ebitda_fy24_price
            },
            {
                "metric": "LTM P/E",
                "min": outputs.min_pe_ltm_price,
                "max": outputs.max_pe_ltm_price,
                "average": outputs.avg_pe_ltm_price
            },
            {
                "metric": "FY2023 P/E",
                "min": outputs.min_pe_fy23_price,
                "max": outputs.max_pe_fy23_price,
                "average": outputs.avg_pe_fy23_price
            },
            {
                "metric": "FY2024 P/E",
                "min": outputs.min_pe_fy24_price,
                "max": outputs.max_pe_fy24_price,
                "average": outputs.avg_pe_fy24_price
            }
        ]
        
        # Also store implied valuation objects for backward compatibility
        if outputs.ev_ebitda_ltm_stats and outputs.ev_ebitda_ltm_stats.median > 0:
            outputs.implied_by_ev_ebitda = self.calculate_implied_valuation(
                outputs.ev_ebitda_ltm_stats.median, t.ebitda_ltm, "ev_ebitda"
            )

        if outputs.pe_ltm_stats and outputs.pe_ltm_stats.median > 0:
            outputs.implied_by_pe = self.calculate_implied_valuation(
                outputs.pe_ltm_stats.median, t.eps_ltm if t.eps_ltm > 0 else t.net_income_ltm / t.shares_outstanding, "pe"
            )

        return outputs


def fetch_comps_inputs(ticker: str, peer_tickers: Optional[List[str]] = None) -> Tuple[TargetCompanyData, List[PeerCompanyData]]:
    """
    Fetch target and peer data from yfinance
    Returns target company data and list of peer company data
    """
    import yfinance as yf

    # Fetch target data
    target_yf = yf.Ticker(ticker)
    info = target_yf.info

    # Extract target metrics
    target = TargetCompanyData(
        ticker=ticker,
        company_name=info.get("longName", ticker),
        market_cap=info.get("marketCap", 0),
        enterprise_value=info.get("enterpriseValue", 0),
        revenue_ltm=info.get("totalRevenue", 0) or info.get("revenue", 0),
        ebitda_ltm=info.get("ebitda", 0),
        ebit_ltm=info.get("operatingIncome", 0),
        net_income_ltm=info.get("netIncomeToCommon", 0) or info.get("trailingEps", 0) * info.get("sharesOutstanding", 1),
        free_cash_flow_ltm=info.get("freeCashflow", 0),
        book_equity=info.get("totalStockholderEquity", 0),
        shares_outstanding=info.get("sharesOutstanding", 1),
        current_stock_price=info.get("currentPrice", 0) or info.get("regularMarketPrice", 0),
        currency=info.get("currency", "USD")
    )

    # Fetch peer data
    peers = []
    for peer_ticker in peer_tickers:
        try:
            peer_yf = yf.Ticker(peer_ticker)
            peer_info = peer_yf.info

            peer = PeerCompanyData(
                ticker=peer_ticker,
                company_name=peer_info.get("longName", peer_ticker),
                market_cap=peer_info.get("marketCap", 0),
                enterprise_value=peer_info.get("enterpriseValue", 0),
                revenue_ltm=peer_info.get("totalRevenue", 0) or peer_info.get("revenue", 0),
                ebitda_ltm=peer_info.get("ebitda", 0),
                ebit_ltm=peer_info.get("operatingIncome", 0),
                net_income_ltm=peer_info.get("netIncomeToCommon", 0) or peer_info.get("trailingEps", 0) * peer_info.get("sharesOutstanding", 1),
                free_cash_flow_ltm=peer_info.get("freeCashflow", 0),
                book_equity=peer_info.get("totalStockholderEquity", 0),
                shares_outstanding=peer_info.get("sharesOutstanding", 1),
                current_stock_price=peer_info.get("currentPrice", 0) or peer_info.get("regularMarketPrice", 0),
                industry=peer_info.get("industry", ""),
                sector=peer_info.get("sector", ""),
                selection_reason="Industry peer"
            )
            peers.append(peer)
        except Exception as e:
            print(f"Warning: Could not fetch data for {peer_ticker}: {e}")
# ============================================================================
    return target, peers

# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example with manual inputs matching Excel specification
    print("=" * 70)
    print("TRADING COMPS ANALYSIS - Excel-Compatible Implementation")
    print("=" * 70)

    # Target company (from Excel "Trading Comps" sheet rows 58-82)
    target = TargetCompanyData(
        ticker="TEST",
        company_name="Test Company",
        market_cap=3800,  # GBP mm
        enterprise_value=5525,
        ebitda_ltm=1234,  # D60
        ebitda_fy2023=1320,  # F60
        ebitda_fy2024=1360,  # H60
        eps_ltm=0.325,  # E61
        eps_fy2023=0.3575,  # G61
        eps_fy2024=0.3754,  # I61
        net_debt=1725,  # D65
        shares_outstanding=1525,  # D66 (mm)
        current_stock_price=2.49,
        currency="GBP",
        analysis_date="2022-08-31"
    )

    # Primary comparable - TSCO (from Excel "TSCO" sheet)
    tsco = PeerCompanyData(
        ticker="TSCO",
        company_name="Tesco PLC",
        market_cap=18500,
        enterprise_value=26000,
        share_price=2.487,
        shares_outstanding=7746,
        ebitda_ltm=4543,  # G90
        ebitda_fy2023=4435.76,  # H90
        ebitda_fy2024=4596.49,  # I90
        eps_ltm=0.218,  # G95
        eps_fy2023=0.21,  # H95
        eps_fy2024=0.22,  # I95
        is_primary_comparable=True
    )

    # Run analysis
    analyzer = TradingCompsAnalyzer(target, [tsco])
    outputs = analyzer.run_analysis(apply_outlier_filtering=False)

    # Print results
    print(f"\nTarget: {target.ticker} ({target.company_name})")
    print(f"Currency: {target.currency}")
    print(f"Analysis Date: {outputs.analysis_date}")
    print(f"Peer Count: {outputs.peer_count_total}")

    print("\n--- Target Metrics ---")
    print(f"EBITDA LTM: £{target.ebitda_ltm}mm")
    print(f"EBITDA FY23: £{target.ebitda_fy2023}mm")
    print(f"EBITDA FY24: £{target.ebitda_fy2024}mm")
    print(f"EPS LTM: £{target.eps_ltm}")
    print(f"EPS FY23: £{target.eps_fy2023}")
    print(f"EPS FY24: £{target.eps_fy2024}")

    print("\n--- Peer Multiples ---")
    for p in outputs.peer_multiples:
        print(f"\n{p['ticker']} ({p['company_name']}):")
        print(f"  EV/EBITDA: LTM={p['ev_ebitda_ltm']}x, FY23={p['ev_ebitda_fy23']}x, FY24={p['ev_ebitda_fy24']}x")
        print(f"  P/E: LTM={p['pe_ltm']}x, FY23={p['pe_fy23']}x, FY24={p['pe_fy24']}x")

    print("\n--- Statistics (Average / Median / Max / Min) ---")
    if outputs.ev_ebitda_ltm_stats:
        s = outputs.ev_ebitda_ltm_stats
        print(f"EV/EBITDA LTM: {s.average:.2f}x / {s.median:.2f}x / {s.maximum:.2f}x / {s.minimum:.2f}x")
    if outputs.pe_ltm_stats:
        s = outputs.pe_ltm_stats
        print(f"P/E LTM:       {s.average:.2f}x / {s.median:.2f}x / {s.maximum:.2f}x / {s.minimum:.2f}x")

    print("\n--- Implied Share Prices (using Average Multiples) ---")
    print(f"LTM EV/EBITDA: £{outputs.avg_ev_ebitda_ltm_price:.2f} ({(outputs.avg_ev_ebitda_ltm_price/target.current_stock_price-1)*100:+.1f}% vs current)")
    print(f"FY23 EV/EBITDA: £{outputs.avg_ev_ebitda_fy23_price:.2f}")
    print(f"FY24 EV/EBITDA: £{outputs.avg_ev_ebitda_fy24_price:.2f}")
    print(f"LTM P/E: £{outputs.avg_pe_ltm_price:.2f}")

    print("\n--- Football Field Range ---")
    for row in outputs.chart_data:
        print(f"{row['metric']}: £{row['min']:.2f} - £{row['average']:.2f} - £{row['max']:.2f}")

    print("\n--- JSON Output Preview ---")
    print(outputs.to_json(indent=2)[:500] + "...")

    # Save to file
    outputs.save_to_file("trading_comps_output.json")
    print("\n✓ Results saved to trading_comps_output.json")