--- backend/app/services/international/step10_comps_report.py (原始)


+++ backend/app/services/international/step10_comps_report.py (修改后)
"""Step 10: Comps Report Generator

Generates comprehensive Comparable Companies analysis reports including:
- Peer Group Multiples Table (P/E, EV/EBITDA, P/B, P/S)
- Outlier Analysis & Exclusion logic
- Implied Valuation Range (Low/Median/High)
- Premium/Discount Analysis vs. Peers
- Final Relative Valuation Conclusion
"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


class CompsPeerMultiple(BaseModel):
    """Individual peer company multiples."""
    company_name: str
    ticker: str
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    market_cap: float
    is_outlier: bool = False
    outlier_reason: Optional[str] = None


class CompsMultiplesSummary(BaseModel):
    """Summary statistics for peer multiples."""
    metric_name: str
    mean: float
    median: float
    min: float
    max: float
    std_dev: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr: Optional[float] = None
    num_peers: int
    num_outliers_excluded: int


class CompsImpliedValuation(BaseModel):
    """Implied valuation from comparable companies."""
    method: str  # e.g., "Median P/E", "Mean EV/EBITDA"
    multiple_used: float
    target_metric: float
    implied_value: float
    implied_value_per_share: float


class CompsValuationRange(BaseModel):
    """Valuation range from comps analysis."""
    low_value: float
    low_multiple: float
    median_value: float
    median_multiple: float
    high_value: float
    high_multiple: float
    current_price: float
    upside_to_median: float


class CompsRecommendation(BaseModel):
    """Investment recommendation based on Comps analysis."""
    rating: str  # OVERVALUED, FAIRLY VALUED, UNDERVALUED
    target_price_range_low: float
    target_price_range_high: float
    preferred_multiple: str
    rationale: str
    confidence_level: str


class CompsReportResponse(BaseModel):
    """Complete Comps valuation report response."""
    ticker: str
    company_name: str
    valuation_date: str
    peer_group: List[CompsPeerMultiple]
    multiples_summary: Dict[str, CompsMultiplesSummary]
    implied_valuations: List[CompsImpliedValuation]
    valuation_range: CompsValuationRange
    recommendation: CompsRecommendation
    key_insights: List[str]
    report_url: Optional[str] = None


class CompsStep10Processor:
    """
    Step 10: Comps Report Generator

    Generates comprehensive Comparable Companies analysis reports by:
    1. Collecting and validating peer company multiples
    2. Applying outlier detection and exclusion (IQR method)
    3. Calculating implied valuations from multiple methods
    4. Generating valuation ranges (low/median/high)
    5. Creating investment recommendations with rationale
    """

    def generate_comps_report(
        self,
        ticker: str,
        comps_inputs: Dict,
        company_name: Optional[str] = None
    ) -> CompsReportResponse:
        """
        Generate comprehensive Comps valuation report.

        Args:
            ticker: Stock ticker symbol
            comps_inputs: Dictionary containing Comps parameters
            company_name: Optional company name for the report

        Returns:
            CompsReportResponse with complete Comps analysis report
        """
        logger.info(f"Generating Comps report for {ticker}")

        # Extract data from inputs
        peer_data = comps_inputs.get('peer_companies', [])
        target_metrics = comps_inputs.get('target_metrics', {})
        current_price = comps_inputs.get('current_price', 100.0)
        shares_outstanding = comps_inputs.get('shares_outstanding', 1000)

        # Process peer group and detect outliers
        peer_group = self._process_peer_group(peer_data)

        # Calculate multiples summary statistics
        multiples_summary = self._calculate_multiples_summary(peer_group)

        # Calculate implied valuations
        implied_valuations = self._calculate_implied_valuations(
            multiples_summary, target_metrics, shares_outstanding
        )

        # Generate valuation range
        valuation_range = self._generate_valuation_range(
            implied_valuations, current_price, shares_outstanding
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(valuation_range, multiples_summary)

        # Generate key insights
        insights = self._generate_key_insights(peer_group, multiples_summary, valuation_range)

        return CompsReportResponse(
            ticker=ticker,
            company_name=company_name or ticker,
            valuation_date=datetime.now().strftime("%Y-%m-%d"),
            peer_group=peer_group,
            multiples_summary=multiples_summary,
            implied_valuations=implied_valuations,
            valuation_range=valuation_range,
            recommendation=recommendation,
            key_insights=insights
        )

    def _process_peer_group(self, peer_data: List[Dict]) -> List[CompsPeerMultiple]:
        """Process peer company data and detect outliers."""
        if not peer_data:
            # Return empty list if no peer data
            return []

        peer_multiples = []

        # First pass: collect all multiples for outlier detection
        pe_ratios = [p.get('pe_ratio') for p in peer_data if p.get('pe_ratio') is not None]
        ev_ebitdas = [p.get('ev_ebitda') for p in peer_data if p.get('ev_ebitda') is not None]
        pb_ratios = [p.get('pb_ratio') for p in peer_data if p.get('pb_ratio') is not None]
        ps_ratios = [p.get('ps_ratio') for p in peer_data if p.get('ps_ratio') is not None]

        # Calculate IQR thresholds for each multiple
        pe_thresholds = self._calculate_iqr_thresholds(pe_ratios)
        ev_ebitda_thresholds = self._calculate_iqr_thresholds(ev_ebitdas)
        pb_thresholds = self._calculate_iqr_thresholds(pb_ratios)
        ps_thresholds = self._calculate_iqr_thresholds(ps_ratios)

        # Second pass: create peer objects with outlier flags
        for peer in peer_data:
            is_outlier = False
            outlier_reasons = []

            pe = peer.get('pe_ratio')
            if pe and pe_thresholds:
                if pe < pe_thresholds['lower'] or pe > pe_thresholds['upper']:
                    is_outlier = True
                    outlier_reasons.append(f"P/E {pe:.2f} outside IQR range")

            ev_ebitda = peer.get('ev_ebitda')
            if ev_ebitda and ev_ebitda_thresholds:
                if ev_ebitda < ev_ebitda_thresholds['lower'] or ev_ebitda > ev_ebitda_thresholds['upper']:
                    is_outlier = True
                    outlier_reasons.append(f"EV/EBITDA {ev_ebitda:.2f} outside IQR range")

            pb = peer.get('pb_ratio')
            if pb and pb_thresholds:
                if pb < pb_thresholds['lower'] or pb > pb_thresholds['upper']:
                    is_outlier = True
                    outlier_reasons.append(f"P/B {pb:.2f} outside IQR range")

            ps = peer.get('ps_ratio')
            if ps and ps_thresholds:
                if ps < ps_thresholds['lower'] or ps > ps_thresholds['upper']:
                    is_outlier = True
                    outlier_reasons.append(f"P/S {ps:.2f} outside IQR range")

            peer_multiples.append(CompsPeerMultiple(
                company_name=peer.get('company_name', 'Unknown'),
                ticker=peer.get('ticker', 'N/A'),
                pe_ratio=pe,
                ev_ebitda=ev_ebitda,
                pb_ratio=pb,
                ps_ratio=ps,
                market_cap=peer.get('market_cap', 0.0),
                is_outlier=is_outlier,
                outlier_reason="; ".join(outlier_reasons) if outlier_reasons else None
            ))

        return peer_multiples

    def _calculate_iqr_thresholds(self, values: List[float]) -> Optional[Dict]:
        """Calculate IQR-based outlier thresholds."""
        if not values or len(values) < 4:
            return None

        sorted_values = sorted(values)
        n = len(sorted_values)

        q1_idx = n // 4
        q3_idx = (3 * n) // 4

        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1

        return {
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'lower': q1 - 1.5 * iqr,
            'upper': q3 + 1.5 * iqr
        }

    def _calculate_multiples_summary(
        self,
        peer_group: List[CompsPeerMultiple]
    ) -> Dict[str, CompsMultiplesSummary]:
        """Calculate summary statistics for each multiple type."""
        summary = {}

        # Filter out outliers for calculation
        non_outlier_peers = [p for p in peer_group if not p.is_outlier]

        # P/E Ratio summary
        pe_values = [p.pe_ratio for p in non_outlier_peers if p.pe_ratio is not None]
        summary['pe_ratio'] = self._calculate_single_multiple_summary(
            pe_values, 'P/E Ratio', len(peer_group) - len(non_outlier_peers)
        )

        # EV/EBITDA summary
        ev_ebitda_values = [p.ev_ebitda for p in non_outlier_peers if p.ev_ebitda is not None]
        summary['ev_ebitda'] = self._calculate_single_multiple_summary(
            ev_ebitda_values, 'EV/EBITDA', len(peer_group) - len(non_outlier_peers)
        )

        # P/B Ratio summary
        pb_values = [p.pb_ratio for p in non_outlier_peers if p.pb_ratio is not None]
        summary['pb_ratio'] = self._calculate_single_multiple_summary(
            pb_values, 'P/B Ratio', len(peer_group) - len(non_outlier_peers)
        )

        # P/S Ratio summary
        ps_values = [p.ps_ratio for p in non_outlier_peers if p.ps_ratio is not None]
        summary['ps_ratio'] = self._calculate_single_multiple_summary(
            ps_values, 'P/S Ratio', len(peer_group) - len(non_outlier_peers)
        )

        return summary

    def _calculate_single_multiple_summary(
        self,
        values: List[float],
        metric_name: str,
        num_outliers: int
    ) -> CompsMultiplesSummary:
        """Calculate summary statistics for a single multiple type."""
        if not values:
            return CompsMultiplesSummary(
                metric_name=metric_name,
                mean=0.0,
                median=0.0,
                min=0.0,
                max=0.0,
                num_peers=0,
                num_outliers_excluded=num_outliers
            )

        sorted_values = sorted(values)
        n = len(values)

        mean_val = sum(values) / n
        median_val = statistics.median(values)
        min_val = min(values)
        max_val = max(values)

        # Calculate quartiles and IQR
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_values[q1_idx] if n >= 4 else min_val
        q3 = sorted_values[q3_idx] if n >= 4 else max_val
        iqr = q3 - q1

        std_dev = statistics.stdev(values) if n > 1 else 0.0

        return CompsMultiplesSummary(
            metric_name=metric_name,
            mean=mean_val,
            median=median_val,
            min=min_val,
            max=max_val,
            std_dev=std_dev,
            q1=q1,
            q3=q3,
            iqr=iqr,
            num_peers=n,
            num_outliers_excluded=num_outliers
        )

    def _calculate_implied_valuations(
        self,
        multiples_summary: Dict[str, CompsMultiplesSummary],
        target_metrics: Dict,
        shares_outstanding: float
    ) -> List[CompsImpliedValuation]:
        """Calculate implied valuations using different multiples."""
        implied_vals = []

        # P/E based valuation
        if 'pe_ratio' in multiples_summary and 'net_income' in target_metrics:
            pe_median = multiples_summary['pe_ratio'].median
            net_income = target_metrics['net_income']
            implied_equity_value = pe_median * net_income
            implied_per_share = implied_equity_value / shares_outstanding if shares_outstanding > 0 else 0
            implied_vals.append(CompsImpliedValuation(
                method="Median P/E",
                multiple_used=pe_median,
                target_metric=net_income,
                implied_value=implied_equity_value,
                implied_value_per_share=implied_per_share
            ))

        # EV/EBITDA based valuation
        if 'ev_ebitda' in multiples_summary and 'ebitda' in target_metrics:
            ev_ebitda_median = multiples_summary['ev_ebitda'].median
            ebitda = target_metrics['ebitda']
            implied_ev = ev_ebitda_median * ebitda
            # Convert to equity value (simplified: assume net debt is known)
            net_debt = target_metrics.get('net_debt', 0)
            implied_equity_value = implied_ev - net_debt
            implied_per_share = implied_equity_value / shares_outstanding if shares_outstanding > 0 else 0
            implied_vals.append(CompsImpliedValuation(
                method="Median EV/EBITDA",
                multiple_used=ev_ebitda_median,
                target_metric=ebitda,
                implied_value=implied_equity_value,
                implied_value_per_share=implied_per_share
            ))

        # P/B based valuation
        if 'pb_ratio' in multiples_summary and 'book_value' in target_metrics:
            pb_median = multiples_summary['pb_ratio'].median
            book_value = target_metrics['book_value']
            implied_equity_value = pb_median * book_value
            implied_per_share = implied_equity_value / shares_outstanding if shares_outstanding > 0 else 0
            implied_vals.append(CompsImpliedValuation(
                method="Median P/B",
                multiple_used=pb_median,
                target_metric=book_value,
                implied_value=implied_equity_value,
                implied_value_per_share=implied_per_share
            ))

        # P/S based valuation
        if 'ps_ratio' in multiples_summary and 'revenue' in target_metrics:
            ps_median = multiples_summary['ps_ratio'].median
            revenue = target_metrics['revenue']
            implied_equity_value = ps_median * revenue
            implied_per_share = implied_equity_value / shares_outstanding if shares_outstanding > 0 else 0
            implied_vals.append(CompsImpliedValuation(
                method="Median P/S",
                multiple_used=ps_median,
                target_metric=revenue,
                implied_value=implied_equity_value,
                implied_value_per_share=implied_per_share
            ))

        return implied_vals

    def _generate_valuation_range(
        self,
        implied_valuations: List[CompsImpliedValuation],
        current_price: float,
        shares_outstanding: float
    ) -> CompsValuationRange:
        """Generate valuation range from implied valuations."""
        if not implied_valuations:
            # Fallback to current price
            return CompsValuationRange(
                low_value=current_price * 0.8,
                low_multiple=0.0,
                median_value=current_price,
                median_multiple=0.0,
                high_value=current_price * 1.2,
                high_multiple=0.0,
                current_price=current_price,
                upside_to_median=0.0
            )

        # Collect all implied per-share values
        implied_values = [iv.implied_value_per_share for iv in implied_valuations if iv.implied_value_per_share > 0]

        if not implied_values:
            return CompsValuationRange(
                low_value=current_price * 0.8,
                low_multiple=0.0,
                median_value=current_price,
                median_multiple=0.0,
                high_value=current_price * 1.2,
                high_multiple=0.0,
                current_price=current_price,
                upside_to_median=0.0
            )

        sorted_values = sorted(implied_values)
        n = len(sorted_values)

        low_value = sorted_values[0]
        median_value = statistics.median(sorted_values)
        high_value = sorted_values[-1]

        # Find corresponding multiples
        low_iv = next((iv for iv in implied_valuations if iv.implied_value_per_share == low_value), None)
        median_iv = next((iv for iv in implied_valuations if iv.implied_value_per_share == median_value), None)
        high_iv = next((iv for iv in implied_valuations if iv.implied_value_per_share == high_value), None)

        upside = (median_value - current_price) / current_price if current_price > 0 else 0

        return CompsValuationRange(
            low_value=low_value,
            low_multiple=low_iv.multiple_used if low_iv else 0.0,
            median_value=median_value,
            median_multiple=median_iv.multiple_used if median_iv else 0.0,
            high_value=high_value,
            high_multiple=high_iv.multiple_used if high_iv else 0.0,
            current_price=current_price,
            upside_to_median=upside
        )

    def _generate_recommendation(
        self,
        valuation_range: CompsValuationRange,
        multiples_summary: Dict[str, CompsMultiplesSummary]
    ) -> CompsRecommendation:
        """Generate investment recommendation based on Comps analysis."""
        upside = valuation_range.upside_to_median

        if upside > 0.20:
            rating = "UNDERVALUED"
            rationale = f"Trading at significant discount to peer median. {upside:.1%} upside potential."
            confidence = "High"
        elif upside > 0.10:
            rating = "UNDERVALUED"
            rationale = f"Trading at discount to peers. {upside:.1%} upside potential."
            confidence = "Medium"
        elif upside > -0.10:
            rating = "FAIRLY VALUED"
            rationale = "Trading in line with peer group multiples."
            confidence = "Medium"
        elif upside > -0.20:
            rating = "OVERVALUED"
            rationale = f"Trading at premium to peers. {abs(upside):.1%} downside risk."
            confidence = "Medium"
        else:
            rating = "OVERVALUED"
            rationale = f"Trading at significant premium to peers. {abs(upside):.1%} downside risk."
            confidence = "High"

        # Determine preferred multiple based on data quality
        preferred_multiple = "Median P/E"
        if 'pe_ratio' in multiples_summary and multiples_summary['pe_ratio'].num_peers >= 5:
            preferred_multiple = "Median P/E"
        elif 'ev_ebitda' in multiples_summary and multiples_summary['ev_ebitda'].num_peers >= 5:
            preferred_multiple = "Median EV/EBITDA"
        elif 'pb_ratio' in multiples_summary:
            preferred_multiple = "Median P/B"
        else:
            preferred_multiple = "Median P/S"

        return CompsRecommendation(
            rating=rating,
            target_price_range_low=valuation_range.low_value,
            target_price_range_high=valuation_range.high_value,
            preferred_multiple=preferred_multiple,
            rationale=rationale,
            confidence_level=confidence
        )

    def _generate_key_insights(
        self,
        peer_group: List[CompsPeerMultiple],
        multiples_summary: Dict[str, CompsMultiplesSummary],
        valuation_range: CompsValuationRange
    ) -> List[str]:
        """Generate key insights from Comps analysis."""
        insights = []

        # Peer group size insight
        num_peers = len(peer_group)
        num_outliers = sum(1 for p in peer_group if p.is_outlier)
        insights.append(f"Peer group consists of {num_peers} companies ({num_outliers} excluded as outliers).")

        # Multiple dispersion insight
        if 'pe_ratio' in multiples_summary and multiples_summary['pe_ratio'].num_peers > 0:
            pe_summary = multiples_summary['pe_ratio']
            if pe_summary.std_dev and pe_summary.median > 0:
                cv = pe_summary.std_dev / pe_summary.median  # Coefficient of variation
                if cv > 0.5:
                    insights.append("High dispersion in P/E multiples suggests diverse peer group.")
                else:
                    insights.append("Tight clustering of P/E multiples indicates consistent peer group.")

        # Valuation insight
        if valuation_range.upside_to_median > 0.15:
            insights.append(f"Stock appears undervalued with {valuation_range.upside_to_median:.1%} upside to median.")
        elif valuation_range.upside_to_median < -0.15:
            insights.append(f"Stock appears overvalued with {abs(valuation_range.upside_to_median):.1%} premium to median.")
        else:
            insights.append("Stock valuation is in line with peer group median.")

        # Range insight
        range_spread = (valuation_range.high_value - valuation_range.low_value) / valuation_range.median_value
        if range_spread > 0.5:
            insights.append("Wide valuation range suggests uncertainty in comparable selection.")
        else:
            insights.append("Narrow valuation range provides confident valuation conclusion.")

        return insights