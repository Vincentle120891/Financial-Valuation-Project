"""
Step 9 & 10 Unified Schema Transformers - Vietnamese Market

This module transforms Vietnamese market Step 9 and Step 10 outputs to
unified schema formats (UnifiedStep9Response and UnifiedStep10Response).

Transformation Strategy:
- Step 9: Map vn_ConfirmationOutput → UnifiedStep9Response
- Step 10: Map vn_ValuationOutput → UnifiedStep10Response
- Preserve ALL original data and calculations (Model Integrity)

IMPORTANT: This transformer preserves ALL original data and calculations.
It only changes the wrapping structure to match the unified contract.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.api.schemas.unified_step_schemas import (
    UnifiedStep9Response,
    UnifiedStep10Response,
    ValuationResultSummary,
    SensitivityAnalysis,
    DataField as UnifiedDataField,
    DataStatus as UnifiedDataStatus,
)

logger = logging.getLogger(__name__)


class VNStep9UnifiedTransformer:
    """
    Transforms Vietnamese Step 9 confirmation outputs to unified schema.

    This is a pure transformation layer - no business logic modification.
    """

    def transform(
        self,
        vn_output: Any,  # vn_ConfirmationOutput
        session_id: str,
        method: str,
        market: str,
        confirmed_assumptions: Dict[str, Any]
    ) -> UnifiedStep9Response:
        """
        Transform Vietnamese Step 9 output to unified schema.

        Args:
            vn_output: Output from vn_Step9ConfirmationProcessor
            session_id: Session identifier
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type ("vietnam")
            confirmed_assumptions: Dictionary of confirmed assumptions

        Returns:
            UnifiedStep9Response conforming to unified schema
        """
        logger.info(f"Transforming Vietnamese Step 9 data for {getattr(vn_output, 'ticker', 'unknown')} ({method})")

        # Extract data from Vietnamese output
        success = getattr(vn_output, 'success', False)
        validation_errors = getattr(vn_output, 'validation_errors', [])
        warnings = getattr(vn_output, 'warnings', [])

        # Build unified response
        response = UnifiedStep9Response(
            status="success" if success else "partial_success",
            session_id=session_id,
            method=method.upper(),
            market=market,
            all_categories_confirmed=success and len(validation_errors) == 0,
            confirmed_assumptions=confirmed_assumptions,
            ready_for_valuation=success and len(validation_errors) == 0,
            validation_errors=validation_errors,
            message=getattr(vn_output, 'message', f"Assumptions confirmed for {method} valuation")
        )

        logger.info(f"Successfully transformed Vietnamese Step 9 data")
        return response


class VNStep10UnifiedTransformer:
    """
    Transforms Vietnamese Step 10 valuation outputs to unified schema.

    This is a pure transformation layer - no business logic modification.
    All valuation results are preserved exactly as-is.
    """

    @staticmethod
    def create_valuation_result_summary(
        vn_output: Any
    ) -> ValuationResultSummary:
        """
        Create unified ValuationResultSummary from Vietnamese output.

        Args:
            vn_output: Vietnamese valuation output

        Returns:
            ValuationResultSummary with DataField wrappers
        """
        summary = ValuationResultSummary()

        # Enterprise Value
        ev = getattr(vn_output, 'enterprise_value', None)
        if ev is not None:
            summary.enterprise_value = UnifiedDataField(
                value=ev,
                status=UnifiedDataStatus.CALCULATED,
                source="valuation_model",
                formula="Sum of discounted FCF + Terminal Value",
                unit="millions_VND",
                currency="VND"
            )

        # Equity Value
        equity_value = getattr(vn_output, 'equity_value', None)
        if equity_value is not None:
            summary.equity_value = UnifiedDataField(
                value=equity_value,
                status=UnifiedDataStatus.CALCULATED,
                source="valuation_model",
                formula="Enterprise Value - Net Debt",
                unit="millions_VND",
                currency="VND"
            )

        # Fair Value Per Share
        fair_value = getattr(vn_output, 'fair_value_per_share', None)
        if fair_value is not None:
            summary.fair_value_per_share = UnifiedDataField(
                value=fair_value,
                status=UnifiedDataStatus.CALCULATED,
                source="valuation_model",
                formula="Equity Value / Shares Outstanding",
                unit="VND/share",
                currency="VND"
            )

        # Current Price
        current_price = getattr(vn_output, 'current_price', None)
        if current_price is not None:
            summary.current_price = UnifiedDataField(
                value=current_price,
                status=UnifiedDataStatus.RETRIEVED,
                source="vietstock",
                unit="VND/share",
                currency="VND"
            )

        # Implied Upside/Downside
        if fair_value and current_price and current_price != 0:
            upside = (fair_value - current_price) / current_price * 100
            summary.implied_upside_downside = UnifiedDataField(
                value=round(upside, 2),
                status=UnifiedDataStatus.CALCULATED,
                source="calculated",
                formula="(Fair Value - Current Price) / Current Price * 100",
                unit="%"
            )

        # Valuation Range (if sensitivity analysis performed)
        range_low = getattr(vn_output, 'valuation_range_low', None)
        range_high = getattr(vn_output, 'valuation_range_high', None)

        if range_low:
            summary.valuation_range_low = UnifiedDataField(
                value=range_low,
                status=UnifiedDataStatus.CALCULATED,
                source="sensitivity_analysis",
                unit="millions_VND",
                currency="VND"
            )

        if range_high:
            summary.valuation_range_high = UnifiedDataField(
                value=range_high,
                status=UnifiedDataStatus.CALCULATED,
                source="sensitivity_analysis",
                unit="millions_VND",
                currency="VND"
            )

        return summary

    @staticmethod
    def create_sensitivity_analysis(
        vn_output: Any
    ) -> Optional[SensitivityAnalysis]:
        """
        Create unified SensitivityAnalysis from Vietnamese output.

        Args:
            vn_output: Vietnamese valuation output with sensitivity data

        Returns:
            SensitivityAnalysis or None if not available
        """
        # Check if sensitivity data exists
        sensitivity_data = getattr(vn_output, 'sensitivity_analysis', None)
        if not sensitivity_data:
            return None

        try:
            # Extract sensitivity matrix data
            variable_1 = sensitivity_data.get('variable_1', 'WACC')
            variable_2 = sensitivity_data.get('variable_2', 'Terminal Growth')
            ranges = sensitivity_data.get('ranges', {})
            results_matrix = sensitivity_data.get('results_matrix', [])

            return SensitivityAnalysis(
                variable_1=variable_1,
                variable_2=variable_2,
                ranges=ranges,
                results_matrix=results_matrix
            )
        except Exception as e:
            logger.warning(f"Failed to parse sensitivity analysis: {e}")
            return None

    @staticmethod
    def determine_confidence_level(
        vn_output: Any,
        data_quality_score: float
    ) -> str:
        """Determine overall confidence level from data quality"""
        if data_quality_score >= 85:
            return "high"
        elif data_quality_score >= 70:
            return "medium"
        return "low"

    def transform(
        self,
        vn_output: Any,  # vn_ValuationOutput
        session_id: str,
        method: str,
        market: str,
        ticker: str,
        company_name: str
    ) -> UnifiedStep10Response:
        """
        Transform Vietnamese Step 10 output to unified schema.

        Args:
            vn_output: Output from vn_Step10ValuationProcessor
            session_id: Session identifier
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type ("vietnam")
            ticker: Company ticker
            company_name: Company name

        Returns:
            UnifiedStep10Response conforming to unified schema
        """
        logger.info(f"Transforming Vietnamese Step 10 valuation for {ticker} ({method})")

        # Create valuation summary
        valuation_summary = self.create_valuation_result_summary(vn_output)

        # Create sensitivity analysis if available
        sensitivity_analysis = self.create_sensitivity_analysis(vn_output)

        # Extract detailed outputs
        detailed_outputs = getattr(vn_output, 'detailed_outputs', {})
        if not detailed_outputs:
            # Build from available attributes
            detailed_outputs = {
                'enterprise_value': getattr(vn_output, 'enterprise_value', None),
                'equity_value': getattr(vn_output, 'equity_value', None),
                'fair_value_per_share': getattr(vn_output, 'fair_value_per_share', None),
                'wacc': getattr(vn_output, 'wacc', None),
                'terminal_value': getattr(vn_output, 'terminal_value', None),
                'pv_fcf': getattr(vn_output, 'present_value_fcf', None),
            }

        # Extract key assumptions summary
        key_assumptions = getattr(vn_output, 'key_assumptions', {})
        if not key_assumptions:
            key_assumptions = {
                'revenue_growth': getattr(vn_output, 'revenue_growth', None),
                'ebitda_margin': getattr(vn_output, 'ebitda_margin', None),
                'wacc': getattr(vn_output, 'wacc', None),
                'terminal_growth': getattr(vn_output, 'terminal_growth', None),
            }

        # Determine confidence level
        data_quality = getattr(vn_output, 'data_quality_score', 75.0)
        confidence_level = self.determine_confidence_level(vn_output, data_quality)

        # Extract warnings
        warnings = getattr(vn_output, 'warnings', [])

        # Extract scenario analysis if available
        scenario_analysis = getattr(vn_output, 'scenario_analysis', None)
        if scenario_analysis:
            # Convert to proper format if needed
            pass

        # Build unified response
        response = UnifiedStep10Response(
            status="success" if getattr(vn_output, 'success', False) else "partial_success",
            session_id=session_id,
            method=method.upper(),
            market=market,
            ticker=ticker,
            company_name=company_name,
            valuation_summary=valuation_summary,
            detailed_outputs=detailed_outputs,
            sensitivity_analysis=sensitivity_analysis,
            scenario_analysis=scenario_analysis,
            confidence_level=confidence_level,
            key_assumptions_summary=key_assumptions,
            warnings=warnings,
            calculation_timestamp=getattr(vn_output, 'calculation_timestamp', datetime.utcnow()),
            message=getattr(vn_output, 'message', f"{method} valuation completed for {company_name}")
        )

        logger.info(f"Successfully transformed Vietnamese Step 10 valuation for {ticker}")
        return response