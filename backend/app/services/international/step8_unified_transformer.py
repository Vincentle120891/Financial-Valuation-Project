"""
Step 8 Unified Schema Transformer - International Market

This module transforms International market Step 8 outputs from method-specific
schemas to the unified schema format (UnifiedStep8Response).

Transformation Strategy:
- All methods (DCF, DuPont, Comps) are now handled by step8_manual_overrides.py
- This transformer maps FullAssumptionsResponse → UnifiedStep8Response

Key Differences:
- Legacy: Method-specific enum types (AssumptionCategory, OverrideStatus)
- Unified: Standardized enum types (AssumptionCategoryType, OverrideStatus)

IMPORTANT: This transformer preserves ALL original data and calculations.
It only changes the wrapping structure to match the unified contract.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.api.schemas.unified_step_schemas import (
    UnifiedStep8Response,
    AssumptionCategoryResponse as UnifiedAssumptionCategoryResponse,
    AssumptionInput as UnifiedAssumptionInput,
    HistoricalTrendline as UnifiedHistoricalTrendline,
    HistoricalTrendPoint as UnifiedHistoricalTrendPoint,
    AISuggestion as UnifiedAISuggestion,
    AssumptionCategoryType,
    OverrideStatus as UnifiedOverrideStatus,
)

from app.services.international.step8_manual_overrides import (
    AssumptionCategory,
    OverrideStatus,
)

logger = logging.getLogger(__name__)


# Category string → unified enum mapping (covers DCF, DuPont, Comps)
CATEGORY_STRING_TO_UNIFIED: Dict[str, AssumptionCategoryType] = {
    "REVENUE_DRIVERS": AssumptionCategoryType.REVENUE_DRIVERS,
    "COST_MARGINS": AssumptionCategoryType.COST_MARGINS,
    "WORKING_CAPITAL": AssumptionCategoryType.WORKING_CAPITAL,
    "WACC_COMPONENTS": AssumptionCategoryType.WACC_COMPONENTS,
    "TERMINAL_VALUE": AssumptionCategoryType.TERMINAL_VALUE,
    "DUPONT_TARGETS": AssumptionCategoryType.DUPONT_TARGETS,
    "COMPS_MULTIPLES": AssumptionCategoryType.COMPS_MULTIPLES,
}


class Step8UnifiedTransformer:
    """
    Transforms International Step 8 method-specific responses to unified schema.

    This is a pure transformation layer - no business logic modification.
    All calculations and data values are preserved exactly as-is.
    """

    @staticmethod
    def transform_override_status_to_unified(status: Any) -> UnifiedOverrideStatus:
        """Convert OverrideStatus enum or string to unified OverrideStatus enum"""
        if isinstance(status, OverrideStatus):
            mapping = {
                OverrideStatus.ACCEPTED_AI: UnifiedOverrideStatus.ACCEPTED_AI,
                OverrideStatus.MANUAL_OVERRIDE: UnifiedOverrideStatus.MANUAL_OVERRIDE,
                OverrideStatus.DEFAULT: UnifiedOverrideStatus.DEFAULT,
            }
            return mapping.get(status, UnifiedOverrideStatus.DEFAULT)
        else:
            # Handle string values
            status_str = str(status).upper()
            if status_str == "ACCEPTED_AI":
                return UnifiedOverrideStatus.ACCEPTED_AI
            elif status_str == "MANUAL_OVERRIDE":
                return UnifiedOverrideStatus.MANUAL_OVERRIDE
            else:
                return UnifiedOverrideStatus.DEFAULT

    @staticmethod
    def transform_historical_trend_point(point: Any) -> UnifiedHistoricalTrendPoint:
        """Convert a HistoricalTrendPoint to unified format"""
        if point is None:
            return UnifiedHistoricalTrendPoint(year=0, value=0.0)

        return UnifiedHistoricalTrendPoint(
            year=int(point.year),
            value=float(point.value),
            label=getattr(point, 'label', '')
        )

    @staticmethod
    def transform_historical_trendline(trendline: Any) -> Optional[UnifiedHistoricalTrendline]:
        """Convert a HistoricalTrendline to unified format"""
        if not trendline:
            return None

        trend_points = []
        if hasattr(trendline, 'trend_points') and trendline.trend_points:
            for point in trendline.trend_points:
                trend_points.append(Step8UnifiedTransformer.transform_historical_trend_point(point))

        def _safe_float(val, default=0.0):
            """Safely convert to float, returning default for None/missing."""
            if val is None:
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        return UnifiedHistoricalTrendline(
            metric=str(getattr(trendline, 'metric', '')),
            trend_points=trend_points,
            average=float(getattr(trendline, 'average', 0.0)),
            cagr=_safe_float(getattr(trendline, 'cagr', None)),
            trend_direction=str(getattr(trendline, 'trend_direction', 'stable')),
            volatility=str(getattr(trendline, 'volatility', 'low')),
            median=_safe_float(getattr(trendline, 'median', None)),
            min_value=_safe_float(getattr(trendline, 'min_value', None)),
            max_value=_safe_float(getattr(trendline, 'max_value', None)),
            standard_deviation=_safe_float(getattr(trendline, 'standard_deviation', None)),
            average_yoy_growth=_safe_float(getattr(trendline, 'average_yoy_growth', None)),
            latest_value=_safe_float(getattr(trendline, 'latest_value', None)),
            oldest_value=_safe_float(getattr(trendline, 'oldest_value', None)),
        )

    @staticmethod
    def transform_ai_suggestion(suggestion: Any, category_mapping: Dict) -> Optional[UnifiedAISuggestion]:
        """Convert an AISuggestion to unified format"""
        if not suggestion:
            return None

        # Map category enum or string to unified category
        legacy_category = getattr(suggestion, 'category', None)
        if isinstance(legacy_category, AssumptionCategory):
            unified_category = category_mapping.get(legacy_category.value, AssumptionCategoryType.REVENUE_DRIVERS)
        else:
            unified_category = category_mapping.get(str(legacy_category), AssumptionCategoryType.REVENUE_DRIVERS)

        return UnifiedAISuggestion(
            metric=str(getattr(suggestion, 'metric', '')),
            suggested_value=float(getattr(suggestion, 'suggested_value', 0.0)),
            reasoning=str(getattr(suggestion, 'reasoning', '')),
            confidence_level=str(getattr(suggestion, 'confidence_level', 'medium')),
            min_range=float(getattr(suggestion, 'min_range', 0.0)),
            max_range=float(getattr(suggestion, 'max_range', 0.0)),
            category=unified_category
        )

    @staticmethod
    def transform_assumption_input(
        assumption: Any,
        category_mapping: Dict
    ) -> UnifiedAssumptionInput:
        """Convert an AssumptionInput to unified format"""
        if assumption is None:
            return UnifiedAssumptionInput(
                metric="",
                category=AssumptionCategoryType.REVENUE_DRIVERS,
                description=""
            )

        # Map category enum or string to unified category
        legacy_category = getattr(assumption, 'category', None)
        if isinstance(legacy_category, AssumptionCategory):
            unified_category = category_mapping.get(legacy_category.value, AssumptionCategoryType.REVENUE_DRIVERS)
        else:
            unified_category = category_mapping.get(str(legacy_category), AssumptionCategoryType.REVENUE_DRIVERS)

        # Transform historical trendline
        historical_trendline = None
        if hasattr(assumption, 'historical_trendline') and assumption.historical_trendline:
            historical_trendline = Step8UnifiedTransformer.transform_historical_trendline(
                assumption.historical_trendline
            )

        # Transform AI suggestion
        ai_suggestion = None
        if hasattr(assumption, 'ai_suggestion') and assumption.ai_suggestion:
            ai_suggestion = Step8UnifiedTransformer.transform_ai_suggestion(
                assumption.ai_suggestion,
                category_mapping
            )

        # Transform override status
        status = UnifiedOverrideStatus.DEFAULT
        if hasattr(assumption, 'status'):
            status = Step8UnifiedTransformer.transform_override_status_to_unified(
                assumption.status
            )

        # Transform year_values
        year_values = {}
        if hasattr(assumption, 'year_values') and assumption.year_values:
            year_values = {int(k): float(v) for k, v in assumption.year_values.items()}

        # Extract data_source (provenance)
        data_source = getattr(assumption, 'data_source', None)

        return UnifiedAssumptionInput(
            metric=str(getattr(assumption, 'metric', '')),
            category=unified_category,
            description=str(getattr(assumption, 'description', '')),
            unit=str(getattr(assumption, 'unit', '%')),
            data_source=data_source,
            historical_trendline=historical_trendline,
            ai_suggestion=ai_suggestion,
            user_value=float(getattr(assumption, 'user_value', 0.0)) if getattr(assumption, 'user_value', None) is not None else None,
            final_value=float(getattr(assumption, 'final_value', 0.0)) if getattr(assumption, 'final_value', None) is not None else None,
            status=status,
            is_valid=bool(getattr(assumption, 'is_valid', True)),
            validation_message=getattr(assumption, 'validation_message', None),
            warning_message=getattr(assumption, 'warning_message', None),
            is_multi_year=bool(getattr(assumption, 'is_multi_year', False)),
            year_values=year_values
        )

    @staticmethod
    def transform_category_response(
        category_response: Any,
        category_mapping: Dict
    ) -> UnifiedAssumptionCategoryResponse:
        """Convert an AssumptionCategoryResponse to unified format"""
        if category_response is None:
            return UnifiedAssumptionCategoryResponse(
                category=AssumptionCategoryType.REVENUE_DRIVERS,
                category_name="",
                assumptions=[]
            )

        # Map category enum or string to unified category
        legacy_category = getattr(category_response, 'category', None)
        if isinstance(legacy_category, AssumptionCategory):
            unified_category = category_mapping.get(legacy_category.value, AssumptionCategoryType.REVENUE_DRIVERS)
        else:
            unified_category = category_mapping.get(str(legacy_category), AssumptionCategoryType.REVENUE_DRIVERS)

        # Transform assumptions list
        assumptions = []
        if hasattr(category_response, 'assumptions') and category_response.assumptions:
            for assumption in category_response.assumptions:
                assumptions.append(Step8UnifiedTransformer.transform_assumption_input(
                    assumption,
                    category_mapping
                ))

        return UnifiedAssumptionCategoryResponse(
            category=unified_category,
            category_name=str(getattr(category_response, 'category_name', '')),
            assumptions=assumptions,
            ai_generated=bool(getattr(category_response, 'ai_generated', False)),
            generation_timestamp=getattr(category_response, 'generation_timestamp', None),
            message=str(getattr(category_response, 'message', ''))
        )

    @classmethod
    def transform_response(
        cls,
        response: Any,
        method: str
    ) -> UnifiedStep8Response:
        """
        Generic transformer that handles any response type from step8_manual_overrides.

        Accepts FullAssumptionsResponse. Uses getattr() for field access so it works
        with any response structure that has the standard fields.

        Args:
            response: The response object (FullAssumptionsResponse)
            method: The valuation method (DCF, DUPONT, COMPS)

        Returns:
            UnifiedStep8Response

        Raises:
            ValueError: If method is not recognized
        """
        method_upper = method.upper()

        # Select category mapping based on method
        # All methods now use the same string-based CATEGORY_STRING_TO_UNIFIED mapping
        category_mapping = CATEGORY_STRING_TO_UNIFIED

        # Transform categories using the shared logic
        categories = {}
        raw_categories = getattr(response, 'categories', {})
        for category_key, category_response in raw_categories.items():
            unified_category = cls.transform_category_response(
                category_response,
                category_mapping
            )
            categories[category_key] = unified_category

        # Extract valuation_model value if it's an enum
        valuation_model = getattr(response, 'valuation_model', method_upper)
        if hasattr(valuation_model, 'value'):
            valuation_model = valuation_model.value

        return UnifiedStep8Response(
            status="success",
            session_id=getattr(response, 'session_id', ''),
            method=method_upper,
            market="international",
            operation_type="initialize",
            ticker=getattr(response, 'ticker', ''),
            valuation_model=str(valuation_model),
            categories=categories,
            targeted_category=None,
            all_categories_complete=getattr(response, 'all_categories_complete', False),
            all_validations_passed=getattr(response, 'all_validations_passed', True),
            total_validation_errors=getattr(response, 'total_validation_errors', []),
            ready_for_calculation=getattr(response, 'ready_for_calculation', False),
            sensitivity_preview=getattr(response, 'sensitivity_preview', None),
            message=getattr(response, 'message', '')
        )
