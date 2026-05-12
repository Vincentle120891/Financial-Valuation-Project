"""
Step 7 Unified Schema Transformer - Vietnamese Market

This module transforms Vietnamese market Step 7 outputs from method-specific
schemas to the unified schema format (UnifiedStep7Response).

Transformation Strategy:
- Map vn_HistoricalDataOutput → UnifiedStep7Response
- Convert normalized time-series dictionaries to DataField wrappers with trend analysis
- Preserve ALL original data and calculations (Model Integrity)

Key Differences:
- Vietnamese Legacy: NormalizedFinancials with {period: value} dictionaries
- Unified: ProcessedHistoricalPeriod list with DataField wrappers and trend analysis

IMPORTANT: This transformer preserves ALL original data and calculations.
It only changes the wrapping structure to match the unified contract.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.api.schemas.unified_step_schemas import (
    UnifiedStep7Response,
    ProcessedHistoricalPeriod,
    DataField as UnifiedDataField,
    DataStatus as UnifiedDataStatus,
    MissingDataSummary as UnifiedMissingDataSummary,
)

from app.services.vietnamese.vn_step7_historical_processor import (
    vn_HistoricalDataOutput,
    NormalizedFinancials,
)

logger = logging.getLogger(__name__)


class VNStep7UnifiedTransformer:
    """
    Transforms Vietnamese Step 7 processor outputs to unified schema.

    This is a pure transformation layer - no business logic modification.
    All calculations and data values are preserved exactly as-is.
    """

    @staticmethod
    def determine_data_status(value: Any, source: str) -> UnifiedDataStatus:
        """Determine data status based on value and source"""
        if value is None:
            return UnifiedDataStatus.MISSING
        if source in ["AI", "ai_extraction", "pdf_extraction"]:
            return UnifiedDataStatus.ESTIMATED
        if source in ["calculated", "derived"]:
            return UnifiedDataStatus.CALCULATED
        return UnifiedDataStatus.RETRIEVED

    @staticmethod
    def calculate_growth_rate(values: Dict[str, float]) -> Optional[float]:
        """Calculate CAGR from a dictionary of period -> value"""
        if not values or len(values) < 2:
            return None

        sorted_periods = sorted(values.keys(), reverse=True)
        if len(sorted_periods) < 2:
            return None

        # Get oldest and newest values
        newest = values.get(sorted_periods[0])
        oldest = values.get(sorted_periods[-1])

        if not newest or not oldest or oldest == 0:
            return None

        years = len(sorted_periods) - 1
        if years <= 0:
            return None

        # Calculate CAGR
        cagr = (newest / oldest) ** (1 / years) - 1
        return round(cagr * 100, 2)  # Return as percentage

    @staticmethod
    def calculate_trend_direction(values: Dict[str, float]) -> str:
        """Determine trend direction from historical values"""
        if not values or len(values) < 2:
            return "stable"

        sorted_periods = sorted(values.keys())
        values_list = [values[p] for p in sorted_periods if values.get(p) is not None]

        if len(values_list) < 2:
            return "stable"

        increases = sum(1 for i in range(1, len(values_list)) if values_list[i] > values_list[i-1])
        decreases = sum(1 for i in range(1, len(values_list)) if values_list[i] < values_list[i-1])

        if increases > decreases * 1.5:
            return "increasing"
        elif decreases > increases * 1.5:
            return "decreasing"
        return "stable"

    @staticmethod
    def calculate_volatility(values: Dict[str, float]) -> str:
        """Determine volatility level from historical values"""
        if not values or len(values) < 2:
            return "low"

        values_list = [v for v in values.values() if v is not None]
        if len(values_list) < 2:
            return "low"

        avg = sum(values_list) / len(values_list)
        if avg == 0:
            return "low"

        variance = sum((v - avg) ** 2 for v in values_list) / len(values_list)
        std_dev = variance ** 0.5
        cv = std_dev / abs(avg)  # Coefficient of variation

        if cv > 0.3:
            return "high"
        elif cv > 0.15:
            return "medium"
        return "low"

    @staticmethod
    def transform_normalized_to_processed_periods(
        normalized: NormalizedFinancials,
        method: str
    ) -> List[ProcessedHistoricalPeriod]:
        """
        Transform NormalizedFinancials to list of ProcessedHistoricalPeriod.

        Args:
            normalized: NormalizedFinancials from Vietnamese Step 7
            method: Valuation method (DCF, DUPONT, COMPS)

        Returns:
            List of ProcessedHistoricalPeriod with DataField wrappers
        """
        processed_periods = []

        # Collect all periods from all fields
        all_periods = set()
        field_names = [
            'revenue', 'cost_of_revenue', 'gross_profit', 'operating_expenses',
            'operating_income', 'net_income', 'total_assets', 'total_equity',
            'operating_cash_flow', 'capital_expenditures'
        ]

        for field_name in field_names:
            field_data = getattr(normalized, field_name, {})
            if isinstance(field_data, dict):
                all_periods.update(field_data.keys())

        # Sort periods chronologically
        sorted_periods = sorted(all_periods)

        for period in sorted_periods:
            year = int(period.split('-')[0]) if '-' in period else int(period)

            # Build data dictionary for this period
            period_data = {}

            for field_name in field_names:
                field_data = getattr(normalized, field_name, {})
                if isinstance(field_data, dict) and period in field_data:
                    value = field_data[period]
                    source = normalized.source_map.get(period, "API")

                    period_data[field_name] = UnifiedDataField(
                        value=value,
                        status=VNStep7UnifiedTransformer.determine_data_status(value, source),
                        source=source,
                        unit="millions_VND",
                        currency="VND",
                        reporting_period=period,
                        last_updated=datetime.now()
                    )

            # Calculate growth rates for this period (vs previous)
            growth_rates = {}
            if sorted_periods.index(period) > 0:
                prev_period = sorted_periods[sorted_periods.index(period) - 1]

                # Revenue growth
                rev_current = normalized.revenue.get(period)
                rev_prev = normalized.revenue.get(prev_period)
                if rev_current and rev_prev and rev_prev != 0:
                    growth_rates['revenue_growth'] = UnifiedDataField(
                        value=round((rev_current - rev_prev) / rev_prev * 100, 2),
                        status=UnifiedDataStatus.CALCULATED,
                        source="calculated",
                        formula="(current_revenue - previous_revenue) / previous_revenue * 100",
                        unit="%",
                        reporting_period=period
                    )

                # Net income growth
                ni_current = normalized.net_income.get(period)
                ni_prev = normalized.net_income.get(prev_period)
                if ni_current and ni_prev and ni_prev != 0:
                    growth_rates['net_income_growth'] = UnifiedDataField(
                        value=round((ni_current - ni_prev) / ni_prev * 100, 2),
                        status=UnifiedDataStatus.CALCULATED,
                        source="calculated",
                        formula="(current_ni - previous_ni) / previous_ni * 100",
                        unit="%",
                        reporting_period=period
                    )

            # Calculate margins for this period
            margins = {}
            revenue = normalized.revenue.get(period)
            if revenue and revenue != 0:
                # Gross margin
                gross_profit = normalized.gross_profit.get(period)
                if gross_profit:
                    margins['gross_margin'] = UnifiedDataField(
                        value=round(gross_profit / revenue * 100, 2),
                        status=UnifiedDataStatus.CALCULATED,
                        source="calculated",
                        formula="gross_profit / revenue * 100",
                        unit="%",
                        reporting_period=period
                    )

                # Operating margin
                operating_income = normalized.operating_income.get(period)
                if operating_income:
                    margins['operating_margin'] = UnifiedDataField(
                        value=round(operating_income / revenue * 100, 2),
                        status=UnifiedDataStatus.CALCULATED,
                        source="calculated",
                        formula="operating_income / revenue * 100",
                        unit="%",
                        reporting_period=period
                    )

                # Net margin
                net_income = normalized.net_income.get(period)
                if net_income:
                    margins['net_margin'] = UnifiedDataField(
                        value=round(net_income / revenue * 100, 2),
                        status=UnifiedDataStatus.CALCULATED,
                        source="calculated",
                        formula="net_income / revenue * 100",
                        unit="%",
                        reporting_period=period
                    )

            processed_period = ProcessedHistoricalPeriod(
                period=period,
                year=year,
                data=period_data,
                growth_rates=growth_rates if growth_rates else None,
                margins=margins if margins else None
            )

            processed_periods.append(processed_period)

        return processed_periods

    @staticmethod
    def create_trend_analysis(normalized: NormalizedFinancials) -> Dict[str, UnifiedDataField]:
        """
        Create trend analysis summary from normalized financials.

        Returns key metrics with their historical trends.
        """
        trend_analysis = {}

        # Revenue trend
        if normalized.revenue:
            revenue_cagr = VNStep7UnifiedTransformer.calculate_growth_rate(normalized.revenue)
            trend_direction = VNStep7UnifiedTransformer.calculate_trend_direction(normalized.revenue)
            volatility = VNStep7UnifiedTransformer.calculate_volatility(normalized.revenue)

            trend_analysis['revenue_trend'] = UnifiedDataField(
                value=revenue_cagr,
                status=UnifiedDataStatus.CALCULATED if revenue_cagr else UnifiedDataStatus.MISSING,
                source="calculated",
                formula="CAGR(revenue)",
                unit="%",
                confidence_score=85.0 if revenue_cagr else 50.0
            )

        # Net income trend
        if normalized.net_income:
            ni_cagr = VNStep7UnifiedTransformer.calculate_growth_rate(normalized.net_income)
            trend_analysis['net_income_trend'] = UnifiedDataField(
                value=ni_cagr,
                status=UnifiedDataStatus.CALCULATED if ni_cagr else UnifiedDataStatus.MISSING,
                source="calculated",
                formula="CAGR(net_income)",
                unit="%"
            )

        # Profitability trends
        if normalized.revenue and normalized.net_income:
            avg_margin = sum(
                normalized.net_income.get(p, 0) / normalized.revenue.get(p, 1)
                for p in normalized.revenue.keys()
                if normalized.revenue.get(p) and normalized.revenue.get(p) != 0
            ) / len([p for p in normalized.revenue.keys() if normalized.revenue.get(p)])

            trend_analysis['avg_net_margin'] = UnifiedDataField(
                value=round(avg_margin * 100, 2),
                status=UnifiedDataStatus.CALCULATED,
                source="calculated",
                formula="AVG(net_income / revenue)",
                unit="%"
            )

        # ROE trend
        if normalized.net_income and normalized.total_equity:
            roe_values = {
                p: normalized.net_income.get(p, 0) / normalized.total_equity.get(p, 1)
                for p in normalized.net_income.keys()
                if normalized.total_equity.get(p) and normalized.total_equity.get(p) != 0
            }

            if roe_values:
                avg_roe = sum(roe_values.values()) / len(roe_values)
                trend_analysis['avg_roe'] = UnifiedDataField(
                    value=round(avg_roe * 100, 2),
                    status=UnifiedDataStatus.CALCULATED,
                    source="calculated",
                    formula="AVG(net_income / equity)",
                    unit="%"
                )

        return trend_analysis

    @staticmethod
    def create_missing_data_summary(
        normalized: NormalizedFinancials,
        missing_critical: List[str],
        data_warnings: List[str],
        completeness_score: float
    ) -> UnifiedMissingDataSummary:
        """Create unified missing data summary from Vietnamese Step 7 output"""
        summary = UnifiedMissingDataSummary(
            total_fields=len([f for f in normalized.model_fields.keys()
                            if f not in ['currency', 'unit_multiplier', 'fiscal_year_end', 'source_map']]),
            retrieved_count=0,
            calculated_count=0,
            estimated_count=0,
            missing_count=len(missing_critical),
            completion_percentage=round(completeness_score * 100, 2),
            critical_missing=missing_critical.copy(),
            optional_missing=[],
            valuation_ready=(completeness_score >= 0.7 and len(missing_critical) == 0),
            data_quality_score=round(completeness_score * 100, 2),
            warnings=data_warnings.copy()
        )

        # Count by source
        for source, count in normalized.source_map.items():
            if source == "API":
                summary.retrieved_count += count
            elif source == "AI":
                summary.estimated_count += count

        # Add recommendations
        if missing_critical:
            summary.recommendations.append(
                f"Critical missing fields detected: {', '.join(missing_critical)}. "
                "Consider AI extraction or manual input."
            )

        if completeness_score < 0.7:
            summary.recommendations.append(
                f"Data completeness is {summary.completion_percentage}%. "
                "Aim for at least 70% before proceeding to valuation."
            )

        return summary

    def transform(
        self,
        vn_output: vn_HistoricalDataOutput,
        session_id: str,
        method: str,
        market: str
    ) -> UnifiedStep7Response:
        """
        Transform Vietnamese Step 7 output to unified schema.

        Args:
            vn_output: Output from vn_Step7HistoricalProcessor
            session_id: Session identifier
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type ("vietnam")

        Returns:
            UnifiedStep7Response conforming to unified schema
        """
        logger.info(f"Transforming Vietnamese Step 7 data for {vn_output.ticker} ({method})")

        # Transform normalized financials to processed periods
        processed_periods = self.transform_normalized_to_processed_periods(
            normalized=vn_output.normalized_financials,
            method=method
        )

        # Create trend analysis
        trend_analysis = self.create_trend_analysis(vn_output.normalized_financials)

        # Create missing data summary
        missing_data_summary = self.create_missing_data_summary(
            normalized=vn_output.normalized_financials,
            missing_critical=vn_output.missing_critical_fields,
            data_warnings=vn_output.data_warnings,
            completeness_score=vn_output.completeness_score
        )

        # Determine adjustments applied (from AI extraction if any)
        adjustments_applied = []
        if vn_output.ai_extraction_results:
            adjustments_applied.append(
                f"AI extraction applied for {len(vn_output.ai_extraction_results.extracted_fields)} fields"
            )

        # Build unified response
        response = UnifiedStep7Response(
            status="success" if vn_output.success else "partial_success",
            session_id=session_id,
            method=method.upper(),
            market=market,
            processed_periods=processed_periods,
            trend_analysis=trend_analysis,
            adjustments_applied=adjustments_applied,
            missing_data_summary=missing_data_summary,
            message=f"Historical data processed for {vn_output.ticker}. "
                   f"Completeness: {vn_output.completeness_score * 100:.1f}%. "
                   f"Periods covered: {len(vn_output.periods_covered)}"
        )

        logger.info(f"Successfully transformed Vietnamese Step 7 data for {vn_output.ticker}")
        return response