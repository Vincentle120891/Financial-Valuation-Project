"""
Vietnamese Comparable Company Analysis (Trading Comps) Engine
Complete implementation matching international comps_engine.py structure,
adapted for Vietnamese market conditions.

Features:
- EV/EBITDA and P/E multiples for LTM
- Implied share price calculations using Min/Average/Max/Median multiples
- IQR outlier filtering for peer multiples
- VND currency handling throughout
- Vietnam-specific peer selection from VNINDEX/VN30
- TT99/VAS accounting standards compliance

All figures in VND billions unless stated otherwise.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import statistics
import math


# ============================================================================
# DATA CLASSES - VIETNAMESE TRADING COMPS
# ============================================================================

@dataclass
class VNTargetCompanyData:
    """
    Input data for the Vietnamese target company being valued.
    Adapted from international TargetCompanyData for VND market.
    
    Attributes:
        ticker: Vietnamese ticker (e.g., VNM, VCB, HPG)
        company_name: Full company name
        market_cap_vnd: Equity value (tỷ VND)
        enterprise_value_vnd: EV (tỷ VND)
        
        # EBITDA metrics (tỷ VND)
        ebitda_ltm_vnd: LTM EBITDA
        ebitda_fy2023_vnd: Next fiscal year estimate
        ebitda_fy2024_vnd: Year after estimate
        
        # EPS metrics (VND per share)
        eps_ltm_vnd: LTM EPS
        eps_fy2023_vnd: Forward EPS estimate FY2023
        eps_fy2024_vnd: Forward EPS estimate FY2024
        
        # Capital structure
        net_debt_vnd: Net debt (tỷ VND)
        shares_outstanding: In millions
        share_price_vnd: Per share (VND)
        
        # Vietnam-specific
        exchange: HOSE, HNX, or UPCOM
        sector: Sector classification
        fol_remaining: Foreign Ownership Limit remaining (%)
        state_ownership_percent: State ownership (%)
    """
    ticker: str
    company_name: str
    market_cap_vnd: float = 0.0  # Tỷ VND
    enterprise_value_vnd: float = 0.0  # Tỷ VND

    # EBITDA metrics (tỷ VND)
    ebitda_ltm_vnd: float = 0.0
    ebitda_fy2023_vnd: Optional[float] = None
    ebitda_fy2024_vnd: Optional[float] = None

    # EPS metrics (VND per share)
    eps_ltm_vnd: float = 0.0
    eps_fy2023_vnd: Optional[float] = None
    eps_fy2024_vnd: Optional[float] = None

    # Capital structure
    net_debt_vnd: float = 0.0
    shares_outstanding: float = 0.0  # In millions
    share_price_vnd: float = 0.0  # Per share (VND)

    # Vietnam-specific
    exchange: str = "HOSE"
    sector: str = ""
    fol_remaining: float = 49.0  # Default 49% FOL
    state_ownership_percent: float = 0.0

    # Metadata
    analysis_date: str = ""


@dataclass
class VNPeerCompanyData:
    """
    Input data for each Vietnamese peer company.
    Adapted from international PeerCompanyData for VND market.
    
    Attributes:
        ticker: Vietnamese ticker
        company_name: Full company name
        
        # Valuation metrics
        market_cap_vnd: Market cap (tỷ VND)
        enterprise_value_vnd: EV (tỷ VND)
        share_price_vnd: Share price (VND)
        shares_outstanding: Shares outstanding (millions)
        
        # EBITDA metrics (tỷ VND)
        ebitda_ltm_vnd: LTM EBITDA
        ebitda_fy2023_vnd: Forward EBITDA FY2023
        ebitda_fy2024_vnd: Forward EBITDA FY2024
        
        # EPS metrics (VND per share)
        eps_ltm_vnd: LTM EPS
        eps_fy2023_vnd: Forward EPS FY2023
        eps_fy2024_vnd: Forward EPS FY2024
        
        # Financials for additional multiples
        revenue_ltm_vnd: LTM Revenue (tỷ VND)
        net_income_ltm_vnd: LTM Net Income (tỷ VND)
        book_value_vnd: Book Value of Equity (tỷ VND)
        
        # Optional metadata
        industry: str = ""
        sector: str = ""
        exchange: str = "HOSE"
        selection_reason: str = "Industry peer"
        is_primary_comparable: bool = False
        vn30_constituent: bool = False  # Whether peer is in VN30 index
    """
    ticker: str
    company_name: str

    # Valuation metrics
    market_cap_vnd: float
    enterprise_value_vnd: float
    share_price_vnd: float
    shares_outstanding: float

    # EBITDA metrics
    ebitda_ltm_vnd: float = 0.0
    ebitda_fy2023_vnd: Optional[float] = None
    ebitda_fy2024_vnd: Optional[float] = None

    # EPS metrics
    eps_ltm_vnd: float = 0.0
    eps_fy2023_vnd: Optional[float] = None
    eps_fy2024_vnd: Optional[float] = None

    # Financials for additional multiples
    revenue_ltm_vnd: float = 0.0
    net_income_ltm_vnd: float = 0.0
    book_value_vnd: float = 0.0

    # Optional metadata
    industry: str = ""
    sector: str = ""
    exchange: str = "HOSE"
    selection_reason: str = "Industry peer"
    is_primary_comparable: bool = False
    vn30_constituent: bool = False


@dataclass
class VNPeerMultiples:
    """Calculated multiples for a single Vietnamese peer company."""
    ticker: str
    company_name: str
    is_primary: bool
    vn30_constituent: bool = False

    # EV/EBITDA multiples
    ev_ebitda_ltm: Optional[float] = None
    ev_ebitda_fy23: Optional[float] = None
    ev_ebitda_fy24: Optional[float] = None

    # P/E multiples
    pe_ltm: Optional[float] = None
    pe_fy23: Optional[float] = None
    pe_fy24: Optional[float] = None

    # Additional multiples common in Vietnam
    ev_revenue_ltm: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None


@dataclass
class VNMultipleStatistics:
    """Statistical summary of peer multiples."""
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p25: float  # 25th percentile
    p75: float  # 75th percentile
    count: int
    
    # Vietnam-specific: include whether outliers were excluded
    outliers_excluded: int = 0


@dataclass
class VNImpliedSharePriceResult:
    """Implied valuation result from comps analysis."""
    implied_enterprise_value_vnd: float  # Tỷ VND
    implied_equity_value_vnd: float  # Tỷ VND
    implied_share_price_vnd: float  # VND per share
    current_share_price_vnd: float  # VND per share
    upside_downside_pct: float
    
    # Multiple used for calculation
    multiple_type: str
    multiple_value: float
    metric_used: str
    
    # Vietnam-specific
    valuation_range: str = ""  # "Conservative", "Base", "Optimistic"


@dataclass
class VNTradingCompsOutputs:
    """
    Complete output structure for Vietnamese Trading Comps analysis.
    Matches international TradingCompsOutputs structure.
    """
    # Target company info
    target_ticker: str
    target_company_name: str
    exchange: str
    sector: str
    currency: str = "VND"
    
    # Peer analysis
    num_peers_initial: int
    num_peers_filtered: int
    excluded_peers: List[str] = field(default_factory=list)
    exclusion_reasons: Dict[str, str] = field(default_factory=dict)
    
    # Peer multiples (detailed)
    peer_multiples: List[Dict] = field(default_factory=list)
    
    # Multiple statistics
    ev_ebitda_stats: Optional[VNMultipleStatistics] = None
    pe_stats: Optional[VNMultipleStatistics] = None
    ev_revenue_stats: Optional[VNMultipleStatistics] = None
    pb_stats: Optional[VNMultipleStatistics] = None
    
    # Implied valuations
    implied_valuations: List[VNImpliedSharePriceResult] = field(default_factory=list)
    
    # Summary valuation range
    valuation_summary: Dict[str, float] = field(default_factory=dict)
    
    # Vietnam-specific metrics
    peer_vn30_count: int = 0
    avg_fol_remaining: float = 0.0
    state_ownership_avg: float = 0.0
    
    # Validation
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "target": {
                "ticker": self.target_ticker,
                "company_name": self.target_company_name,
                "exchange": self.exchange,
                "sector": self.sector,
                "currency": self.currency
            },
            "peer_analysis": {
                "num_peers_initial": self.num_peers_initial,
                "num_peers_filtered": self.num_peers_filtered,
                "excluded_peers": self.excluded_peers,
                "exclusion_reasons": self.exclusion_reasons,
                "vn30_constituents": self.peer_vn30_count,
                "avg_fol_remaining": round(self.avg_fol_remaining, 2),
                "state_ownership_avg": round(self.state_ownership_avg, 2)
            },
            "multiple_statistics": {
                "ev_ebitda": {
                    "mean": round(self.ev_ebitda_stats.mean, 2) if self.ev_ebitda_stats else None,
                    "median": round(self.ev_ebitda_stats.median, 2) if self.ev_ebitda_stats else None,
                    "min": round(self.ev_ebitda_stats.min, 2) if self.ev_ebitda_stats else None,
                    "max": round(self.ev_ebitda_stats.max, 2) if self.ev_ebitda_stats else None,
                    "std_dev": round(self.ev_ebitda_stats.std_dev, 2) if self.ev_ebitda_stats else None,
                    "count": self.ev_ebitda_stats.count if self.ev_ebitda_stats else 0,
                    "outliers_excluded": self.ev_ebitda_stats.outliers_excluded if self.ev_ebitda_stats else 0
                } if self.ev_ebitda_stats else None,
                "pe_ratio": {
                    "mean": round(self.pe_stats.mean, 2) if self.pe_stats else None,
                    "median": round(self.pe_stats.median, 2) if self.pe_stats else None,
                    "min": round(self.pe_stats.min, 2) if self.pe_stats else None,
                    "max": round(self.pe_stats.max, 2) if self.pe_stats else None,
                    "std_dev": round(self.pe_stats.std_dev, 2) if self.pe_stats else None,
                    "count": self.pe_stats.count if self.pe_stats else 0,
                    "outliers_excluded": self.pe_stats.outliers_excluded if self.pe_stats else 0
                } if self.pe_stats else None,
                "ev_revenue": {
                    "mean": round(self.ev_revenue_stats.mean, 2) if self.ev_revenue_stats else None,
                    "median": round(self.ev_revenue_stats.median, 2) if self.ev_revenue_stats else None,
                    "min": round(self.ev_revenue_stats.min, 2) if self.ev_revenue_stats else None,
                    "max": round(self.ev_revenue_stats.max, 2) if self.ev_revenue_stats else None,
                    "count": self.ev_revenue_stats.count if self.ev_revenue_stats else 0
                } if self.ev_revenue_stats else None,
                "pb_ratio": {
                    "mean": round(self.pb_stats.mean, 2) if self.pb_stats else None,
                    "median": round(self.pb_stats.median, 2) if self.pb_stats else None,
                    "min": round(self.pb_stats.min, 2) if self.pb_stats else None,
                    "max": round(self.pb_stats.max, 2) if self.pb_stats else None,
                    "count": self.pb_stats.count if self.pb_stats else 0
                } if self.pb_stats else None
            },
            "implied_valuations": [
                {
                    "multiple_type": v.multiple_type,
                    "multiple_value": round(v.multiple_value, 2),
                    "metric_used": v.metric_used,
                    "implied_ev_vnd": round(v.implied_enterprise_value_vnd, 2),
                    "implied_equity_vnd": round(v.implied_equity_value_vnd, 2),
                    "implied_share_price_vnd": round(v.implied_share_price_vnd, 2),
                    "current_price_vnd": round(v.current_share_price_vnd, 2),
                    "upside_downside_pct": round(v.upside_downside_pct, 2),
                    "valuation_range": v.valuation_range
                }
                for v in self.implied_valuations
            ],
            "valuation_summary": self.valuation_summary,
            "validation_errors": self.validation_errors,
            "warnings": self.warnings
        }


# ============================================================================
# VIETNAMESE TRADING COMPS ANALYZER
# ============================================================================

class VNTradingCompsAnalyzer:
    """
    Vietnamese Trading Comps Analyzer implementing comparable company analysis.
    
    Follows the same methodology as international TradingCompsAnalyzer but
    adapted for Vietnamese market conditions:
    - VND currency throughout
    - TT99/VAS accounting standards
    - VN30/VNINDEX peer selection
    - FOL and state ownership tracking
    - Emerging market liquidity considerations
    
    Usage:
        analyzer = VNTradingCompsAnalyzer(target, peers)
        results = analyzer.run_analysis(apply_outlier_filtering=True)
    """
    
    # Vietnam-specific constants
    VIETNAM_FOL_DEFAULT_MAX = 0.49  # 49% default FOL
    VIETNAM_VN30_CONSTITUENTS_LIMIT = 30  # VN30 index has 30 stocks
    MIN_PEERS_REQUIRED = 3  # Minimum peers for meaningful analysis
    MIN_PEERS_FOR_OUTLIER_FILTERING = 5  # Need 5+ peers for IQR filtering
    
    def __init__(self, target: VNTargetCompanyData, peers: List[VNPeerCompanyData]):
        """
        Initialize the Vietnamese comps analyzer.
        
        Args:
            target: Target company data
            peers: List of peer company data
        """
        self.target = target
        self.all_peers = peers
        self.filtered_peers: List[VNPeerCompanyData] = []
        self.excluded_peers: List[str] = []
        self.exclusion_reasons: Dict[str, str] = {}
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []
    
    def calculate_peer_multiples(self, peer: VNPeerCompanyData) -> VNPeerMultiples:
        """
        Calculate all multiples for a single Vietnamese peer.
        Matches international structure with VND adaptations.
        
        Args:
            peer: Peer company data
            
        Returns:
            VNPeerMultiples with calculated ratios
        """
        # EV/EBITDA multiples
        ev_ebitda_ltm = None
        ev_ebitda_fy23 = None
        ev_ebitda_fy24 = None
        
        if peer.ebitda_ltm_vnd > 0:
            ev_ebitda_ltm = round(peer.enterprise_value_vnd / peer.ebitda_ltm_vnd, 2)
        if peer.ebitda_fy2023_vnd and peer.ebitda_fy2023_vnd > 0:
            ev_ebitda_fy23 = round(peer.enterprise_value_vnd / peer.ebitda_fy2023_vnd, 2)
        if peer.ebitda_fy2024_vnd and peer.ebitda_fy2024_vnd > 0:
            ev_ebitda_fy24 = round(peer.enterprise_value_vnd / peer.ebitda_fy2024_vnd, 2)
        
        # P/E multiples
        pe_ltm = None
        pe_fy23 = None
        pe_fy24 = None
        
        if peer.eps_ltm_vnd > 0:
            pe_ltm = round(peer.share_price_vnd / peer.eps_ltm_vnd, 2)
        if peer.eps_fy2023_vnd and peer.eps_fy2023_vnd > 0:
            pe_fy23 = round(peer.share_price_vnd / peer.eps_fy2023_vnd, 2)
        if peer.eps_fy2024_vnd and peer.eps_fy2024_vnd > 0:
            pe_fy24 = round(peer.share_price_vnd / peer.eps_fy2024_vnd, 2)
        
        # EV/Revenue multiple
        ev_revenue_ltm = None
        if peer.revenue_ltm_vnd > 0:
            ev_revenue_ltm = round(peer.enterprise_value_vnd / peer.revenue_ltm_vnd, 2)
        
        # P/B ratio
        pb_ratio = None
        if peer.book_value_vnd > 0:
            pb_ratio = round(peer.market_cap_vnd / peer.book_value_vnd, 2)
        
        return VNPeerMultiples(
            ticker=peer.ticker,
            company_name=peer.company_name,
            is_primary=peer.is_primary_comparable,
            vn30_constituent=peer.vn30_constituent,
            ev_ebitda_ltm=ev_ebitda_ltm,
            ev_ebitda_fy23=ev_ebitda_fy23,
            ev_ebitda_fy24=ev_ebitda_fy24,
            pe_ltm=pe_ltm,
            pe_fy23=pe_fy23,
            pe_fy24=pe_fy24,
            ev_revenue_ltm=ev_revenue_ltm,
            pb_ratio=pb_ratio,
            dividend_yield=None  # Can be added if available
        )
    
    def filter_peers_by_iqr(
        self, 
        multiple_values: List[float], 
        peer_indices: List[int],
        iqr_multiplier: float = 1.5
    ) -> Tuple[List[float], List[int], int]:
        """
        Filter outliers using IQR (Interquartile Range) method.
        
        Vietnam market adaptation:
        - Emerging markets have higher volatility, so use conservative IQR multiplier
        - Minimum 5 peers required for meaningful outlier detection
        
        Args:
            multiple_values: List of multiple values
            peer_indices: Corresponding peer indices
            iqr_multiplier: IQR multiplier (default 1.5, standard)
            
        Returns:
            Tuple of (filtered_values, kept_indices, num_outliers)
        """
        if len(multiple_values) < self.MIN_PEERS_FOR_OUTLIER_FILTERING:
            # Not enough peers for outlier filtering
            return multiple_values, peer_indices, 0
        
        sorted_values = sorted(multiple_values)
        n = len(sorted_values)
        
        # Calculate quartiles
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        # Calculate bounds
        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr
        
        # Filter values
        filtered_values = []
        kept_indices = []
        outliers_count = 0
        
        for i, val in enumerate(multiple_values):
            if lower_bound <= val <= upper_bound:
                filtered_values.append(val)
                kept_indices.append(peer_indices[i])
            else:
                outliers_count += 1
        
        return filtered_values, kept_indices, outliers_count
    
    def calculate_statistics(self, values: List[Optional[float]]) -> VNMultipleStatistics:
        """
        Calculate comprehensive statistics for a list of multiple values.
        
        Args:
            values: List of multiple values (may contain None)
            
        Returns:
            VNMultipleStatistics with all statistical measures
        """
        # Clean values: remove None and non-positive
        clean_values = [v for v in values if v is not None and v > 0]
        
        if len(clean_values) == 0:
            return VNMultipleStatistics(
                mean=0, median=0, std_dev=0, min=0, max=0, 
                p25=0, p75=0, count=0, outliers_excluded=0
            )
        
        sorted_values = sorted(clean_values)
        n = len(sorted_values)
        
        # Basic statistics
        mean_val = statistics.mean(clean_values)
        median_val = statistics.median(clean_values)
        std_dev_val = statistics.stdev(clean_values) if n > 1 else 0
        
        # Percentiles
        p25_idx = n // 4
        p75_idx = (3 * n) // 4
        
        return VNMultipleStatistics(
            mean=mean_val,
            median=median_val,
            std_dev=std_dev_val,
            min=min(clean_values),
            max=max(clean_values),
            p25=sorted_values[p25_idx],
            p75=sorted_values[p75_idx],
            count=n,
            outliers_excluded=0  # Will be updated during filtering
        )
    
    def calculate_implied_valuation(
        self, 
        multiple: float, 
        metric_value: float,
        metric_type: str
    ) -> VNImpliedSharePriceResult:
        """
        Calculate implied valuation from a multiple.
        
        Args:
            multiple: Trading multiple (e.g., EV/EBITDA, P/E)
            metric_value: Metric value (e.g., EBITDA, Net Income)
            metric_type: Type of multiple ("ev_ebitda", "pe", etc.)
            
        Returns:
            VNImpliedSharePriceResult with valuation details
        """
        # Determine valuation range label
        if multiple <= 0.8:
            valuation_range = "Conservative"
        elif multiple >= 1.2:
            valuation_range = "Optimistic"
        else:
            valuation_range = "Base"
        
        # Calculate implied values based on multiple type
        if metric_type in ["ev_ebitda", "ev_sales", "ev_ebit", "ev_fcf"]:
            # Enterprise value multiple
            implied_ev_vnd = multiple * metric_value
            # Convert EV to Equity Value: Equity = EV - Net Debt
            implied_equity_vnd = implied_ev_vnd - self.target.net_debt_vnd
        else:  # pe, pb, p_fcf
            # Equity value multiple
            implied_equity_vnd = multiple * metric_value
            # Convert Equity to EV: EV = Equity + Net Debt
            implied_ev_vnd = implied_equity_vnd + self.target.net_debt_vnd
        
        # Calculate implied share price
        if self.target.shares_outstanding > 0:
            implied_share_price_vnd = implied_equity_vnd / self.target.shares_outstanding
        else:
            implied_share_price_vnd = 0
        
        current_price = self.target.share_price_vnd
        
        # Calculate upside/downside
        if current_price > 0:
            upside_downside_pct = (implied_share_price_vnd - current_price) / current_price * 100
        else:
            upside_downside_pct = 0
        
        return VNImpliedSharePriceResult(
            implied_enterprise_value_vnd=implied_ev_vnd,
            implied_equity_value_vnd=implied_equity_vnd,
            implied_share_price_vnd=implied_share_price_vnd,
            current_share_price_vnd=current_price,
            upside_downside_pct=upside_downside_pct,
            multiple_type=metric_type,
            multiple_value=multiple,
            metric_used=metric_type.split('_')[1] if '_' in metric_type else metric_type,
            valuation_range=valuation_range
        )
    
    def run_analysis(
        self, 
        apply_outlier_filtering: bool = True,
        iqr_multiplier: float = 1.5,
        outlier_metric: str = "ev_ebitda_ltm"
    ) -> VNTradingCompsOutputs:
        """
        Run complete Vietnamese trading comps analysis.
        
        Args:
            apply_outlier_filtering: Enable IQR outlier removal
            iqr_multiplier: IQR multiplier for outlier detection
            outlier_metric: Primary metric for outlier filtering
            
        Returns:
            VNTradingCompsOutputs with complete analysis results
        """
        # Validate minimum peers
        if len(self.all_peers) < self.MIN_PEERS_REQUIRED:
            self.validation_errors.append(
                f"Need at least {self.MIN_PEERS_REQUIRED} peers for comps analysis, "
                f"got {len(self.all_peers)}"
            )
        
        # Calculate multiples for all peers
        all_peer_multiples = []
        ev_ebitda_ltm_values = []
        pe_ltm_values = []
        ev_revenue_ltm_values = []
        pb_ratio_values = []
        
        peer_indices = list(range(len(self.all_peers)))
        
        for idx, peer in enumerate(self.all_peers):
            multiples = self.calculate_peer_multiples(peer)
            all_peer_multiples.append(multiples)
            
            # Collect values for statistical analysis
            if multiples.ev_ebitda_ltm:
                ev_ebitda_ltm_values.append(multiples.ev_ebitda_ltm)
            if multiples.pe_ltm:
                pe_ltm_values.append(multiples.pe_ltm)
            if multiples.ev_revenue_ltm:
                ev_revenue_ltm_values.append(multiples.ev_revenue_ltm)
            if multiples.pb_ratio:
                pb_ratio_values.append(multiples.pb_ratio)
        
        # Apply outlier filtering if enabled
        filtered_indices = set(peer_indices)
        total_outliers_excluded = 0
        
        if apply_outlier_filtering and len(self.all_peers) >= self.MIN_PEERS_FOR_OUTLIER_FILTERING:
            # Filter by primary outlier metric
            if outlier_metric == "ev_ebitda_ltm" and len(ev_ebitda_ltm_values) >= self.MIN_PEERS_FOR_OUTLIER_FILTERING:
                # Map values back to peer indices
                ev_peers_with_values = [
                    (i, v) for i, m in enumerate(all_peer_multiples) 
                    if m.ev_ebitda_ltm for v in [m.ev_ebitda_ltm]
                ]
                if len(ev_peers_with_values) >= self.MIN_PEERS_FOR_OUTLIER_FILTERING:
                    values = [v for _, v in ev_peers_with_values]
                    indices = [i for i, _ in ev_peers_with_values]
                    
                    _, kept_indices, outliers_count = self.filter_peers_by_iqr(
                        values, indices, iqr_multiplier
                    )
                    
                    # Update filtered indices
                    kept_original_indices = [peer_indices[i] for i in kept_indices]
                    filtered_indices = set(kept_original_indices)
                    total_outliers_excluded = outliers_count
                    
                    # Record excluded peers
                    excluded_indices = set(indices) - set(kept_indices)
                    for excl_idx in excluded_indices:
                        orig_idx = peer_indices[excl_idx]
                        self.excluded_peers.append(self.all_peers[orig_idx].ticker)
                        self.exclusion_reasons[self.all_peers[orig_idx].ticker] = \
                            f"Outlier in {outlier_metric}"
        
        # Filter peers based on outlier analysis
        self.filtered_peers = [
            peer for i, peer in enumerate(self.all_peers) 
            if i in filtered_indices
        ]
        
        # Recalculate statistics with filtered peers
        filtered_peer_multiples = [
            m for i, m in enumerate(all_peer_multiples)
            if i in filtered_indices
        ]
        
        # Extract filtered values
        filtered_ev_ebitda = [m.ev_ebitda_ltm for m in filtered_peer_multiples if m.ev_ebitda_ltm]
        filtered_pe = [m.pe_ltm for m in filtered_peer_multiples if m.pe_ltm]
        filtered_ev_revenue = [m.ev_revenue_ltm for m in filtered_peer_multiples if m.ev_revenue_ltm]
        filtered_pb = [m.pb_ratio for m in filtered_peer_multiples if m.pb_ratio]
        
        # Calculate statistics
        ev_ebitda_stats = self.calculate_statistics(filtered_ev_ebitda)
        pe_stats = self.calculate_statistics(filtered_pe)
        ev_revenue_stats = self.calculate_statistics(filtered_ev_revenue)
        pb_stats = self.calculate_statistics(filtered_pb)
        
        # Update outliers excluded count
        if ev_ebitda_stats:
            ev_ebitda_stats.outliers_excluded = total_outliers_excluded
        if pe_stats:
            pe_stats.outliers_excluded = total_outliers_excluded
        
        # Calculate implied valuations using median multiples
        implied_valuations = []
        
        # EV/EBITDA implied valuation
        if ev_ebitda_stats.median > 0 and self.target.ebitda_ltm_vnd > 0:
            implied = self.calculate_implied_valuation(
                ev_ebitda_stats.median,
                self.target.ebitda_ltm_vnd,
                "ev_ebitda"
            )
            implied_valuations.append(implied)
        
        # P/E implied valuation
        if pe_stats.median > 0 and self.target.eps_ltm_vnd > 0:
            # For P/E, metric_value should be EPS * shares to get equity value
            # But we're using the simplified version where we multiply P/E by EPS to get price
            implied_price = pe_stats.median * self.target.eps_ltm_vnd
            implied_equity = implied_price * self.target.shares_outstanding
            implied_ev = implied_equity + self.target.net_debt_vnd
            
            current_price = self.target.share_price_vnd
            upside = (implied_price - current_price) / current_price * 100 if current_price > 0 else 0
            
            valuation_range = "Base"
            if pe_stats.median <= pe_stats.p25 * 1.1:
                valuation_range = "Conservative"
            elif pe_stats.median >= pe_stats.p75 * 0.9:
                valuation_range = "Optimistic"
            
            implied_valuations.append(VNImpliedSharePriceResult(
                implied_enterprise_value_vnd=implied_ev,
                implied_equity_value_vnd=implied_equity,
                implied_share_price_vnd=implied_price,
                current_share_price_vnd=current_price,
                upside_downside_pct=upside,
                multiple_type="pe",
                multiple_value=pe_stats.median,
                metric_used="eps",
                valuation_range=valuation_range
            ))
        
        # Calculate valuation summary
        valuation_summary = {}
        if implied_valuations:
            prices = [v.implied_share_price_vnd for v in implied_valuations]
            valuation_summary = {
                "implied_price_min": round(min(prices), 2),
                "implied_price_median": round(statistics.median(prices), 2),
                "implied_price_max": round(max(prices), 2),
                "current_price": round(self.target.share_price_vnd, 2),
                "upside_to_median": round(
                    (statistics.median(prices) - self.target.share_price_vnd) / 
                    self.target.share_price_vnd * 100 if self.target.share_price_vnd > 0 else 0, 
                    2
                )
            }
        
        # Vietnam-specific metrics
        peer_vn30_count = sum(1 for p in self.filtered_peers if p.vn30_constituent)
        avg_fol = statistics.mean([p.fol_remaining for p in self.filtered_peers]) if self.filtered_peers else 0
        
        # Build outputs
        outputs = VNTradingCompsOutputs(
            target_ticker=self.target.ticker,
            target_company_name=self.target.company_name,
            exchange=self.target.exchange,
            sector=self.target.sector,
            currency="VND",
            num_peers_initial=len(self.all_peers),
            num_peers_filtered=len(self.filtered_peers),
            excluded_peers=self.excluded_peers,
            exclusion_reasons=self.exclusion_reasons,
            peer_multiples=[
                {
                    "ticker": m.ticker,
                    "company_name": m.company_name,
                    "is_primary": m.is_primary,
                    "vn30_constituent": m.vn30_constituent,
                    "ev_ebitda_ltm": m.ev_ebitda_ltm,
                    "pe_ltm": m.pe_ltm,
                    "ev_revenue_ltm": m.ev_revenue_ltm,
                    "pb_ratio": m.pb_ratio
                }
                for m in filtered_peer_multiples
            ],
            ev_ebitda_stats=ev_ebitda_stats,
            pe_stats=pe_stats,
            ev_revenue_stats=ev_revenue_stats,
            pb_stats=pb_stats,
            implied_valuations=implied_valuations,
            valuation_summary=valuation_summary,
            peer_vn30_count=peer_vn30_count,
            avg_fol_remaining=avg_fol,
            validation_errors=self.validation_errors,
            warnings=self.warnings
        )
        
        return outputs
    
    def get_football_field_data(self) -> Dict:
        """
        Generate data for football field chart visualization.
        
        Returns:
            Dictionary with valuation ranges for chart rendering
        """
        if not self.filtered_peers:
            return {"ranges": [], "current_price": self.target.share_price_vnd}
        
        ranges = []
        
        # EV/EBITDA range
        if self.ev_ebitda_stats and self.ev_ebitda_stats.count > 0:
            if self.target.ebitda_ltm_vnd > 0:
                low_price = (self.ev_ebitda_stats.p25 * self.target.ebitda_ltm_vnd - 
                           self.target.net_debt_vnd) / self.target.shares_outstanding
                high_price = (self.ev_ebitda_stats.p75 * self.target.ebitda_ltm_vnd - 
                            self.target.net_debt_vnd) / self.target.shares_outstanding
                ranges.append({
                    "method": "EV/EBITDA",
                    "low": round(low_price, 2),
                    "high": round(high_price, 2),
                    "median": round((low_price + high_price) / 2, 2)
                })
        
        # P/E range
        if self.pe_stats and self.pe_stats.count > 0:
            if self.target.eps_ltm_vnd > 0:
                low_price = self.pe_stats.p25 * self.target.eps_ltm_vnd
                high_price = self.pe_stats.p75 * self.target.eps_ltm_vnd
                ranges.append({
                    "method": "P/E",
                    "low": round(low_price, 2),
                    "high": round(high_price, 2),
                    "median": round((low_price + high_price) / 2, 2)
                })
        
        return {
            "ranges": ranges,
            "current_price": round(self.target.share_price_vnd, 2),
            "currency": "VND"
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_vn_target_from_dict(data: Dict) -> VNTargetCompanyData:
    """
    Create VNTargetCompanyData from dictionary.
    
    Args:
        data: Dictionary with target company data
        
    Returns:
        VNTargetCompanyData instance
    """
    return VNTargetCompanyData(
        ticker=data.get("ticker", ""),
        company_name=data.get("company_name", ""),
        market_cap_vnd=data.get("market_cap_vnd", 0),
        enterprise_value_vnd=data.get("enterprise_value_vnd", 0),
        ebitda_ltm_vnd=data.get("ebitda_ltm_vnd", 0),
        ebitda_fy2023_vnd=data.get("ebitda_fy2023_vnd"),
        ebitda_fy2024_vnd=data.get("ebitda_fy2024_vnd"),
        eps_ltm_vnd=data.get("eps_ltm_vnd", 0),
        eps_fy2023_vnd=data.get("eps_fy2023_vnd"),
        eps_fy2024_vnd=data.get("eps_fy2024_vnd"),
        net_debt_vnd=data.get("net_debt_vnd", 0),
        shares_outstanding=data.get("shares_outstanding", 0),
        share_price_vnd=data.get("share_price_vnd", 0),
        exchange=data.get("exchange", "HOSE"),
        sector=data.get("sector", ""),
        fol_remaining=data.get("fol_remaining", 49.0),
        state_ownership_percent=data.get("state_ownership_percent", 0.0)
    )


def create_vn_peer_from_dict(data: Dict) -> VNPeerCompanyData:
    """
    Create VNPeerCompanyData from dictionary.
    
    Args:
        data: Dictionary with peer company data
        
    Returns:
        VNPeerCompanyData instance
    """
    return VNPeerCompanyData(
        ticker=data.get("ticker", ""),
        company_name=data.get("company_name", ""),
        market_cap_vnd=data.get("market_cap_vnd", 0),
        enterprise_value_vnd=data.get("enterprise_value_vnd", 0),
        share_price_vnd=data.get("share_price_vnd", 0),
        shares_outstanding=data.get("shares_outstanding", 0),
        ebitda_ltm_vnd=data.get("ebitda_ltm_vnd", 0),
        ebitda_fy2023_vnd=data.get("ebitda_fy2023_vnd"),
        ebitda_fy2024_vnd=data.get("ebitda_fy2024_vnd"),
        eps_ltm_vnd=data.get("eps_ltm_vnd", 0),
        eps_fy2023_vnd=data.get("eps_fy2023_vnd"),
        eps_fy2024_vnd=data.get("eps_fy2024_vnd"),
        revenue_ltm_vnd=data.get("revenue_ltm_vnd", 0),
        net_income_ltm_vnd=data.get("net_income_ltm_vnd", 0),
        book_value_vnd=data.get("book_value_vnd", 0),
        industry=data.get("industry", ""),
        sector=data.get("sector", ""),
        exchange=data.get("exchange", "HOSE"),
        vn30_constituent=data.get("vn30_constituent", False)
    )


async def run_vietnamese_comps_analysis(
    target_data: Dict,
    peer_data_list: List[Dict],
    apply_outlier_filtering: bool = True,
    iqr_multiplier: float = 1.5
) -> Dict:
    """
    High-level function to run Vietnamese comps analysis.
    
    Args:
        target_data: Target company data as dict
        peer_data_list: List of peer company data dicts
        apply_outlier_filtering: Enable outlier removal
        iqr_multiplier: IQR multiplier for filtering
        
    Returns:
        Dictionary with analysis results
    """
    # Create data objects
    target = create_vn_target_from_dict(target_data)
    peers = [create_vn_peer_from_dict(p) for p in peer_data_list]
    
    # Run analysis
    analyzer = VNTradingCompsAnalyzer(target, peers)
    results = analyzer.run_analysis(
        apply_outlier_filtering=apply_outlier_filtering,
        iqr_multiplier=iqr_multiplier
    )
    
    # Convert to dict
    return results.to_dict()
