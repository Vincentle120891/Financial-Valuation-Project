--- backend/comps_engine.py (原始)
"""
Trading Comps Analysis Module
Complete implementation with peer selection, multiple calculations, and implied valuations
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
import statistics


@dataclass
class TargetCompanyData:
    """Input data for the target company being valued"""
    ticker: str
    company_name: str
    market_cap: float
    enterprise_value: float
    revenue_ltm: float
    ebitda_ltm: float
    ebit_ltm: float
    net_income_ltm: float
    free_cash_flow_ltm: float
    book_equity: float
    shares_outstanding: float
    current_stock_price: float
    currency: str = "USD"


@dataclass
class PeerCompanyData:
    """Input data for each peer company"""
    ticker: str
    company_name: str
    market_cap: float
    enterprise_value: float
    revenue_ltm: float
    ebitda_ltm: float
    ebit_ltm: float
    net_income_ltm: float
    free_cash_flow_ltm: float
    book_equity: float
    shares_outstanding: float
    current_stock_price: float
    industry: str = ""
    sector: str = ""
    selection_reason: str = ""  # Why this peer was selected
    similarity_score: float = 1.0  # 0-1 score for AI-based matching


@dataclass
class PeerMultipleStats:
    """Statistics for a specific multiple across peers"""
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p25: float
    p75: float
    count: int

    def to_dict(self) -> Dict:
        return {
            "mean": round(self.mean, 3),
            "median": round(self.median, 3),
            "std_dev": round(self.std_dev, 3),
            "min": round(self.min, 3),
            "max": round(self.max, 3),
            "p25": round(self.p25, 3),
            "p75": round(self.p75, 3),
            "count": self.count
        }


@dataclass
class ImpliedValuation:
    """Implied valuation from a specific multiple"""
    implied_enterprise_value: float
    implied_equity_value: float
    implied_share_price: float
    current_share_price: float
    upside_downside_pct: float

    def to_dict(self) -> Dict:
        return {
            "implied_enterprise_value": round(self.implied_enterprise_value, 0),
            "implied_equity_value": round(self.implied_equity_value, 0),
            "implied_share_price": round(self.implied_share_price, 2),
            "current_share_price": round(self.current_share_price, 2),
            "upside_downside_pct": round(self.upside_downside_pct, 1)
        }


@dataclass
class TradingCompsOutputs:
    """Complete Trading Comps output matching the JSON schema"""

    # Target company multiples
    ev_ebitda_ltm: float = 0.0
    ev_sales_ltm: float = 0.0
    ev_ebit_ltm: float = 0.0
    pe_diluted_ltm: float = 0.0
    pb_ltm: float = 0.0
    p_fcf_ltm: float = 0.0
    ev_fcf_ltm: float = 0.0

    # Peer multiples (list of dicts)
    peer_multiples: List[Dict] = field(default_factory=list)

    # Statistics by multiple type
    ev_ebitda_stats: Optional[PeerMultipleStats] = None
    ev_sales_stats: Optional[PeerMultipleStats] = None
    ev_ebit_stats: Optional[PeerMultipleStats] = None
    pe_stats: Optional[PeerMultipleStats] = None
    pb_stats: Optional[PeerMultipleStats] = None
    p_fcf_stats: Optional[PeerMultipleStats] = None
    ev_fcf_stats: Optional[PeerMultipleStats] = None

    # Implied valuations by multiple type
    implied_by_ev_ebitda: Optional[ImpliedValuation] = None
    implied_by_ev_sales: Optional[ImpliedValuation] = None
    implied_by_ev_ebit: Optional[ImpliedValuation] = None
    implied_by_pe: Optional[ImpliedValuation] = None
    implied_by_pb: Optional[ImpliedValuation] = None
    implied_by_p_fcf: Optional[ImpliedValuation] = None
    implied_by_ev_fcf: Optional[ImpliedValuation] = None

    # Counts
    peer_count_total: int = 0
    peer_count_after_filtering: int = 0

    # Metadata
    analysis_date: str = ""
    currency: str = "USD"
    primary_multiple: str = "ev_ebitda_ltm"
    outlier_filtering_applied: bool = True
    filtering_method: str = "IQR"  # Interquartile range
    excluded_peers: List[str] = field(default_factory=list)
    exclusion_reasons: Dict[str, str] = field(default_factory=dict)

    def to_json_schema_format(self) -> Dict:
        """Convert to exact JSON schema format"""

        # Build target multiples
        target_multiples = {
            "ev_ebitda_ltm": round(self.ev_ebitda_ltm, 2),
            "ev_sales_ltm": round(self.ev_sales_ltm, 2),
            "ev_ebit_ltm": round(self.ev_ebit_ltm, 2),
            "pe_diluted_ltm": round(self.pe_diluted_ltm, 2),
            "pb_ltm": round(self.pb_ltm, 2),
            "p_fcf_ltm": round(self.p_fcf_ltm, 2),
            "ev_fcf_ltm": round(self.ev_fcf_ltm, 2)
        }

        # Build peer statistics
        peer_statistics = {}
        if self.ev_ebitda_stats:
            peer_statistics["ev_ebitda_ltm"] = self.ev_ebitda_stats.to_dict()
        if self.ev_sales_stats:
            peer_statistics["ev_sales_ltm"] = self.ev_sales_stats.to_dict()
        if self.ev_ebit_stats:
            peer_statistics["ev_ebit_ltm"] = self.ev_ebit_stats.to_dict()
        if self.pe_stats:
            peer_statistics["pe_diluted_ltm"] = self.pe_stats.to_dict()
        if self.pb_stats:
            peer_statistics["pb_ltm"] = self.pb_stats.to_dict()
        if self.p_fcf_stats:
            peer_statistics["p_fcf_ltm"] = self.p_fcf_stats.to_dict()
        if self.ev_fcf_stats:
            peer_statistics["ev_fcf_ltm"] = self.ev_fcf_stats.to_dict()

        # Build implied valuations
        implied_valuations = {}
        if self.implied_by_ev_ebitda:
            implied_valuations["by_ev_ebitda_median"] = self.implied_by_ev_ebitda.to_dict()
        if self.implied_by_ev_sales:
            implied_valuations["by_ev_sales_median"] = self.implied_by_ev_sales.to_dict()
        if self.implied_by_ev_ebit:
            implied_valuations["by_ev_ebit_median"] = self.implied_by_ev_ebit.to_dict()
        if self.implied_by_pe:
            implied_valuations["by_pe_median"] = self.implied_by_pe.to_dict()
        if self.implied_by_pb:
            implied_valuations["by_pb_median"] = self.implied_by_pb.to_dict()
        if self.implied_by_p_fcf:
            implied_valuations["by_p_fcf_median"] = self.implied_by_p_fcf.to_dict()
        if self.implied_by_ev_fcf:
            implied_valuations["by_ev_fcf_median"] = self.implied_by_ev_fcf.to_dict()

        # Build metadata
        metadata = {
            "analysis_date": self.analysis_date or datetime.now().strftime("%Y-%m-%d"),
            "currency": self.currency,
            "primary_multiple": self.primary_multiple,
            "outlier_filtering_applied": self.outlier_filtering_applied
        }

        return {
            "target_multiples": target_multiples,
            "peer_multiples": self.peer_multiples,
            "peer_statistics": peer_statistics,
            "implied_valuations": implied_valuations,
            "peer_count": self.peer_count_total,
            "peer_count_after_filtering": self.peer_count_after_filtering,
            "metadata": metadata
        }

    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string"""
        return json.dumps(self.to_json_schema_format(), indent=indent)

    def save_to_file(self, filename: str):
        """Save to JSON file"""
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
        """Calculate all multiples for a single peer"""
        multiples = {
            "ticker": peer.ticker,
            "company_name": peer.company_name,
            "market_cap": round(peer.market_cap, 0),
            "ev_ebitda_ltm": round(peer.enterprise_value / peer.ebitda_ltm, 2) if peer.ebitda_ltm > 0 else None,
            "ev_sales_ltm": round(peer.enterprise_value / peer.revenue_ltm, 2) if peer.revenue_ltm > 0 else None,
            "ev_ebit_ltm": round(peer.enterprise_value / peer.ebit_ltm, 2) if peer.ebit_ltm > 0 else None,
            "pe_diluted_ltm": round(peer.market_cap / peer.net_income_ltm, 2) if peer.net_income_ltm > 0 else None,
            "pb_ltm": round(peer.market_cap / peer.book_equity, 2) if peer.book_equity > 0 else None,
            "p_fcf_ltm": round(peer.market_cap / peer.free_cash_flow_ltm, 2) if peer.free_cash_flow_ltm > 0 else None,
            "ev_fcf_ltm": round(peer.enterprise_value / peer.free_cash_flow_ltm, 2) if peer.free_cash_flow_ltm > 0 else None
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

    def calculate_statistics(self, values: List[float]) -> PeerMultipleStats:
        """Calculate comprehensive statistics for a list of values"""
        clean_values = [v for v in values if v is not None and v > 0]

        if len(clean_values) == 0:
            return PeerMultipleStats(
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

        return PeerMultipleStats(
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
                                    metric_type: str) -> ImpliedValuation:
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

        return ImpliedValuation(
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

        outputs.ev_ebitda_stats = self.calculate_statistics(ev_ebitda_vals)
        outputs.ev_sales_stats = self.calculate_statistics(ev_sales_vals)
        outputs.ev_ebit_stats = self.calculate_statistics(ev_ebit_vals)
        outputs.pe_stats = self.calculate_statistics(pe_vals)
        outputs.pb_stats = self.calculate_statistics(pb_vals)
        outputs.p_fcf_stats = self.calculate_statistics(p_fcf_vals)
        outputs.ev_fcf_stats = self.calculate_statistics(ev_fcf_vals)

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


def fetch_comps_inputs(ticker: str, peer_tickers: List[str]) -> Tuple[TargetCompanyData, List[PeerCompanyData]]:
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

    return target, peers


# Example usage
if __name__ == "__main__":
    # Example with mock data
    target = TargetCompanyData(
        ticker="AAPL",
        company_name="Apple Inc.",
        market_cap=2800000000000,
        enterprise_value=2850000000000,
        revenue_ltm=383000000000,
        ebitda_ltm=125000000000,
        ebit_ltm=114000000000,
        net_income_ltm=97000000000,
        free_cash_flow_ltm=99000000000,
        book_equity=62000000000,
        shares_outstanding=15500000000,
        current_stock_price=180.50
    )

    peers = [
        PeerCompanyData(ticker="MSFT", company_name="Microsoft", market_cap=2700000000000,
                       enterprise_value=2680000000000, revenue_ltm=211000000000,
                       ebitda_ltm=95000000000, ebit_ltm=88000000000,
                       net_income_ltm=72000000000, free_cash_flow_ltm=65000000000,
                       book_equity=206000000000, shares_outstanding=7430000000,
                       current_stock_price=363.50),
        PeerCompanyData(ticker="GOOGL", company_name="Alphabet", market_cap=1700000000000,
                       enterprise_value=1650000000000, revenue_ltm=307000000000,
                       ebitda_ltm=98000000000, ebit_ltm=84000000000,
                       net_income_ltm=73000000000, free_cash_flow_ltm=69000000000,
                       book_equity=283000000000, shares_outstanding=12800000000,
                       current_stock_price=132.80),
        PeerCompanyData(ticker="AMZN", company_name="Amazon", market_cap=1500000000000,
                       enterprise_value=1550000000000, revenue_ltm=574000000000,
                       ebitda_ltm=71000000000, ebit_ltm=36000000000,
                       net_income_ltm=30000000000, free_cash_flow_ltm=35000000000,
                       book_equity=201000000000, shares_outstanding=10300000000,
                       current_stock_price=145.60),
        PeerCompanyData(ticker="META", company_name="Meta Platforms", market_cap=900000000000,
                       enterprise_value=850000000000, revenue_ltm=134000000000,
                       ebitda_ltm=55000000000, ebit_ltm=46000000000,
                       net_income_ltm=39000000000, free_cash_flow_ltm=43000000000,
                       book_equity=188000000000, shares_outstanding=2550000000,
                       current_stock_price=353.20),
        PeerCompanyData(ticker="NVDA", company_name="NVIDIA", market_cap=1100000000000,
                       enterprise_value=1080000000000, revenue_ltm=60000000000,
                       ebitda_ltm=33000000000, ebit_ltm=32000000000,
                       net_income_ltm=29000000000, free_cash_flow_ltm=28000000000,
                       book_equity=42000000000, shares_outstanding=2470000000,
                       current_stock_price=445.30),
        PeerCompanyData(ticker="TSLA", company_name="Tesla", market_cap=800000000000,
                       enterprise_value=790000000000, revenue_ltm=96000000000,
                       ebitda_ltm=19000000000, ebit_ltm=11000000000,
                       net_income_ltm=15000000000, free_cash_flow_ltm=10000000000,
                       book_equity=62000000000, shares_outstanding=3170000000,
                       current_stock_price=252.40)
    ]

    # Run analysis
    analyzer = TradingCompsAnalyzer(target, peers)
    outputs = analyzer.run_analysis(apply_outlier_filtering=True)

    # Print results
    print("=" * 60)
    print("TRADING COMPS ANALYSIS")
    print("=" * 60)
    print(f"\nTarget: {target.ticker} ({target.company_name})")
    print(f"Peer Count: {outputs.peer_count_total} total, {outputs.peer_count_after_filtering} after filtering")
    if outputs.excluded_peers:
        print(f"Excluded Peers: {', '.join(outputs.excluded_peers)}")

    print("\n--- Target Multiples ---")
    print(f"EV/EBITDA: {outputs.ev_ebitda_ltm:.2f}x")
    print(f"EV/Sales: {outputs.ev_sales_ltm:.2f}x")
    print(f"P/E: {outputs.pe_diluted_ltm:.2f}x")
    print(f"P/B: {outputs.pb_ltm:.2f}x")

    print("\n--- Peer Statistics (Median) ---")
    if outputs.ev_ebitda_stats:
        print(f"EV/EBITDA: {outputs.ev_ebitda_stats.median:.2f}x (Mean: {outputs.ev_ebitda_stats.mean:.2f}x)")
    if outputs.pe_stats:
        print(f"P/E: {outputs.pe_stats.median:.2f}x (Mean: {outputs.pe_stats.mean:.2f}x)")

    print("\n--- Implied Valuations (using Median Multiples) ---")
    if outputs.implied_by_ev_ebitda:
        print(f"By EV/EBITDA: ${outputs.implied_by_ev_ebitda.implied_share_price:.2f} ({outputs.implied_by_ev_ebitda.upside_downside_pct:+.1f}%)")
    if outputs.implied_by_pe:
        print(f"By P/E: ${outputs.implied_by_pe.implied_share_price:.2f} ({outputs.implied_by_pe.upside_downside_pct:+.1f}%)")

    print("\n--- JSON Output ---")
    print(outputs.to_json(indent=2))

    # Save to file
    outputs.save_to_file("trading_comps_output.json")
    print("\n✓ Results saved to trading_comps_output.json")

+++ backend/comps_engine.py (修改后)
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


def fetch_comps_inputs(ticker: str, peer_tickers: List[str]) -> Tuple[TargetCompanyData, List[PeerCompanyData]]:
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