"""
Step 8 Unified Schema Transformer - International Market

This module transforms International market Step 8 outputs from method-specific
schemas to the unified schema format (UnifiedStep8Response).

Transformation Strategy:
- DCF: Map DCFAssumptionsResponse → UnifiedStep8Response
- DuPont: Map DuPontAssumptionsResponse → UnifiedStep8Response  
- Comps: Map CompsAssumptionsResponse → UnifiedStep8Response

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

from app.services.international.step8_dcf_assumptions import (
    DCFAssumptionsResponse,
    AssumptionCategory as DCFAssumptionCategory,
    OverrideStatus as DCFOverrideStatus,
    AssumptionInput as DCFAssumptionInput,
    HistoricalTrendline as DCFHistoricalTrendline,
    HistoricalTrendPoint as DCFHistoricalTrendPoint,
    AISuggestion as DCFAISuggestion,
)

from app.services.international.step8_dupont_assumptions import (
    DuPontAssumptionsResponse,
    AssumptionCategory as DuPontAssumptionCategory,
    OverrideStatus as DuPontOverrideStatus,
    AssumptionInput as DuPontAssumptionInput,
    HistoricalTrendline as DuPontHistoricalTrendline,
    HistoricalTrendPoint as DuPontHistoricalTrendPoint,
    AISuggestion as DuPontAISuggestion,
)

from app.services.international.step8_comps_assumptions import (
    CompsAssumptionsResponse,
    AssumptionCategory as CompsAssumptionCategory,
    OverrideStatus as CompsOverrideStatus,
    AssumptionInput as CompsAssumptionInput,
    HistoricalTrendline as CompsHistoricalTrendline,
    HistoricalTrendPoint as CompsHistoricalTrendPoint,
    AISuggestion as CompsAISuggestion,
)

logger = logging.getLogger(__name__)


class Step8UnifiedTransformer:
    """
    Transforms International Step 8 method-specific responses to unified schema.
    
    This is a pure transformation layer - no business logic modification.
    All calculations and data values are preserved exactly as-is.
    """
    
    # Mapping from legacy DCF categories to unified categories
    DCF_CATEGORY_MAPPING = {
        DCFAssumptionCategory.REVENUE_DRIVERS: AssumptionCategoryType.REVENUE_DRIVERS,
        DCFAssumptionCategory.COST_MARGINS: AssumptionCategoryType.COST_MARGINS,
        DCFAssumptionCategory.WORKING_CAPITAL: AssumptionCategoryType.WORKING_CAPITAL,
        DCFAssumptionCategory.WACC_COMPONENTS: AssumptionCategoryType.WACC_COMPONENTS,
        DCFAssumptionCategory.TERMINAL_VALUE: AssumptionCategoryType.TERMINAL_VALUE,
    }
    
    # Mapping from legacy DuPont categories to unified categories
    DUPONT_CATEGORY_MAPPING = {
        DuPontAssumptionCategory.DUPONT_TARGETS: AssumptionCategoryType.DUPONT_TARGETS,
    }
    
    # Mapping from legacy Comps categories to unified categories
    COMPS_CATEGORY_MAPPING = {
        CompsAssumptionCategory.COMPS_MULTIPLES: AssumptionCategoryType.COMPS_MULTIPLES,
    }
    
    @staticmethod
    def transform_legacy_override_status_to_unified(legacy_status: Any) -> UnifiedOverrideStatus:
        """Convert legacy OverrideStatus enum to unified OverrideStatus enum"""
        if isinstance(legacy_status, DCFOverrideStatus):
            mapping = {
                DCFOverrideStatus.ACCEPTED_AI: UnifiedOverrideStatus.ACCEPTED_AI,
                DCFOverrideStatus.MANUAL_OVERRIDE: UnifiedOverrideStatus.MANUAL_OVERRIDE,
                DCFOverrideStatus.DEFAULT: UnifiedOverrideStatus.DEFAULT,
            }
            return mapping.get(legacy_status, UnifiedOverrideStatus.DEFAULT)
        elif isinstance(legacy_status, DuPontOverrideStatus):
            mapping = {
                DuPontOverrideStatus.ACCEPTED_AI: UnifiedOverrideStatus.ACCEPTED_AI,
                DuPontOverrideStatus.MANUAL_OVERRIDE: UnifiedOverrideStatus.MANUAL_OVERRIDE,
                DuPontOverrideStatus.DEFAULT: UnifiedOverrideStatus.DEFAULT,
            }
            return mapping.get(legacy_status, UnifiedOverrideStatus.DEFAULT)
        elif isinstance(legacy_status, CompsOverrideStatus):
            mapping = {
                CompsOverrideStatus.ACCEPTED_AI: UnifiedOverrideStatus.ACCEPTED_AI,
                CompsOverrideStatus.MANUAL_OVERRIDE: UnifiedOverrideStatus.MANUAL_OVERRIDE,
                CompsOverrideStatus.DEFAULT: UnifiedOverrideStatus.DEFAULT,
            }
            return mapping.get(legacy_status, UnifiedOverrideStatus.DEFAULT)
        else:
            # Handle string values
            status_str = str(legacy_status).upper()
            if status_str == "ACCEPTED_AI":
                return UnifiedOverrideStatus.ACCEPTED_AI
            elif status_str == "MANUAL_OVERRIDE":
                return UnifiedOverrideStatus.MANUAL_OVERRIDE
            else:
                return UnifiedOverrideStatus.DEFAULT
    
    @staticmethod
    def transform_legacy_historical_trend_point(legacy_point: Any) -> UnifiedHistoricalTrendPoint:
        """Convert legacy HistoricalTrendPoint to unified format"""
        if legacy_point is None:
            return UnifiedHistoricalTrendPoint(year=0, value=0.0)
        
        return UnifiedHistoricalTrendPoint(
            year=int(legacy_point.year),
            value=float(legacy_point.value),
            label=getattr(legacy_point, 'label', '')
        )
    
    @staticmethod
    def transform_legacy_historical_trendline(legacy_trendline: Any) -> Optional[UnifiedHistoricalTrendline]:
        """Convert legacy HistoricalTrendline to unified format"""
        if not legacy_trendline:
            return None
        
        trend_points = []
        if hasattr(legacy_trendline, 'trend_points') and legacy_trendline.trend_points:
            for point in legacy_trendline.trend_points:
                trend_points.append(Step8UnifiedTransformer.transform_legacy_historical_trend_point(point))
        
        return UnifiedHistoricalTrendline(
            metric=str(getattr(legacy_trendline, 'metric', '')),
            trend_points=trend_points,
            average=float(getattr(legacy_trendline, 'average', 0.0)),
            cagr=float(getattr(legacy_trendline, 'cagr', 0.0)) if getattr(legacy_trendline, 'cagr', None) is not None else None,
            trend_direction=str(getattr(legacy_trendline, 'trend_direction', 'stable')),
            volatility=str(getattr(legacy_trendline, 'volatility', 'low'))
        )
    
    @staticmethod
    def transform_legacy_ai_suggestion(legacy_suggestion: Any, category_mapping: Dict) -> Optional[UnifiedAISuggestion]:
        """Convert legacy AISuggestion to unified format"""
        if not legacy_suggestion:
            return None
        
        # Map legacy category to unified category
        legacy_category = getattr(legacy_suggestion, 'category', None)
        unified_category = category_mapping.get(legacy_category, AssumptionCategoryType.REVENUE_DRIVERS)
        
        return UnifiedAISuggestion(
            metric=str(getattr(legacy_suggestion, 'metric', '')),
            suggested_value=float(getattr(legacy_suggestion, 'suggested_value', 0.0)),
            reasoning=str(getattr(legacy_suggestion, 'reasoning', '')),
            confidence_level=str(getattr(legacy_suggestion, 'confidence_level', 'medium')),
            min_range=float(getattr(legacy_suggestion, 'min_range', 0.0)),
            max_range=float(getattr(legacy_suggestion, 'max_range', 0.0)),
            category=unified_category
        )
    
    @staticmethod
    def transform_legacy_assumption_input(
        legacy_assumption: Any, 
        category_mapping: Dict
    ) -> UnifiedAssumptionInput:
        """Convert legacy AssumptionInput to unified format"""
        if legacy_assumption is None:
            return UnifiedAssumptionInput(
                metric="",
                category=AssumptionCategoryType.REVENUE_DRIVERS,
                description=""
            )
        
        # Map legacy category to unified category
        legacy_category = getattr(legacy_assumption, 'category', None)
        unified_category = category_mapping.get(legacy_category, AssumptionCategoryType.REVENUE_DRIVERS)
        
        # Transform historical trendline
        historical_trendline = None
        if hasattr(legacy_assumption, 'historical_trendline') and legacy_assumption.historical_trendline:
            historical_trendline = Step8UnifiedTransformer.transform_legacy_historical_trendline(
                legacy_assumption.historical_trendline
            )
        
        # Transform AI suggestion
        ai_suggestion = None
        if hasattr(legacy_assumption, 'ai_suggestion') and legacy_assumption.ai_suggestion:
            ai_suggestion = Step8UnifiedTransformer.transform_legacy_ai_suggestion(
                legacy_assumption.ai_suggestion,
                category_mapping
            )
        
        # Transform override status
        status = UnifiedOverrideStatus.DEFAULT
        if hasattr(legacy_assumption, 'status'):
            status = Step8UnifiedTransformer.transform_legacy_override_status_to_unified(
                legacy_assumption.status
            )
        
        # Transform year_values
        year_values = {}
        if hasattr(legacy_assumption, 'year_values') and legacy_assumption.year_values:
            year_values = {int(k): float(v) for k, v in legacy_assumption.year_values.items()}
        
        return UnifiedAssumptionInput(
            metric=str(getattr(legacy_assumption, 'metric', '')),
            category=unified_category,
            description=str(getattr(legacy_assumption, 'description', '')),
            unit=str(getattr(legacy_assumption, 'unit', '%')),
            historical_trendline=historical_trendline,
            ai_suggestion=ai_suggestion,
            user_value=float(getattr(legacy_assumption, 'user_value', 0.0)) if getattr(legacy_assumption, 'user_value', None) is not None else None,
            final_value=float(getattr(legacy_assumption, 'final_value', 0.0)) if getattr(legacy_assumption, 'final_value', None) is not None else None,
            status=status,
            is_valid=bool(getattr(legacy_assumption, 'is_valid', True)),
            validation_message=getattr(legacy_assumption, 'validation_message', None),
            warning_message=getattr(legacy_assumption, 'warning_message', None),
            is_multi_year=bool(getattr(legacy_assumption, 'is_multi_year', False)),
            year_values=year_values
        )
    
    @staticmethod
    def transform_legacy_category_response(
        legacy_category_response: Any,
        category_mapping: Dict
    ) -> UnifiedAssumptionCategoryResponse:
        """Convert legacy AssumptionCategoryResponse to unified format"""
        if legacy_category_response is None:
            return UnifiedAssumptionCategoryResponse(
                category=AssumptionCategoryType.REVENUE_DRIVERS,
                category_name="",
                assumptions=[]
            )
        
        # Map legacy category to unified category
        legacy_category = getattr(legacy_category_response, 'category', None)
        unified_category = category_mapping.get(legacy_category, AssumptionCategoryType.REVENUE_DRIVERS)
        
        # Transform assumptions list
        assumptions = []
        if hasattr(legacy_category_response, 'assumptions') and legacy_category_response.assumptions:
            for assumption in legacy_category_response.assumptions:
                assumptions.append(Step8UnifiedTransformer.transform_legacy_assumption_input(
                    assumption,
                    category_mapping
                ))
        
        return UnifiedAssumptionCategoryResponse(
            category=unified_category,
            category_name=str(getattr(legacy_category_response, 'category_name', '')),
            assumptions=assumptions,
            ai_generated=bool(getattr(legacy_category_response, 'ai_generated', False)),
            generation_timestamp=getattr(legacy_category_response, 'generation_timestamp', None),
            message=str(getattr(legacy_category_response, 'message', ''))
        )
    
    @classmethod
    def transform_dcf_response(cls, dcf_response: DCFAssumptionsResponse) -> UnifiedStep8Response:
        """
        Transform DCF-specific response to unified schema.
        
        This is the main entry point for DCF transformation.
        """
        logger.info(f"Transforming DCF Step 8 response for {dcf_response.ticker} to unified schema")
        
        # Transform categories
        categories = {}
        for category_key, category_response in dcf_response.categories.items():
            unified_category = cls.transform_legacy_category_response(
                category_response,
                cls.DCF_CATEGORY_MAPPING
            )
            categories[category_key] = unified_category
        
        return UnifiedStep8Response(
            status="success",
            session_id=dcf_response.session_id,
            method="DCF",
            market="international",
            operation_type="initialize",
            ticker=dcf_response.ticker,
            valuation_model="DCF",
            categories=categories,
            targeted_category=None,
            all_categories_complete=dcf_response.all_categories_complete,
            all_validations_passed=dcf_response.all_validations_passed,
            total_validation_errors=dcf_response.total_validation_errors,
            ready_for_calculation=dcf_response.ready_for_calculation,
            sensitivity_preview=dcf_response.sensitivity_preview,
            message=dcf_response.message
        )
    
    @classmethod
    def transform_dupont_response(cls, dupont_response: DuPontAssumptionsResponse) -> UnifiedStep8Response:
        """
        Transform DuPont-specific response to unified schema.
        
        This is the main entry point for DuPont transformation.
        """
        logger.info(f"Transforming DuPont Step 8 response for {dupont_response.ticker} to unified schema")
        
        # Transform categories
        categories = {}
        for category_key, category_response in dupont_response.categories.items():
            unified_category = cls.transform_legacy_category_response(
                category_response,
                cls.DUPONT_CATEGORY_MAPPING
            )
            categories[category_key] = unified_category
        
        return UnifiedStep8Response(
            status="success",
            session_id=dupont_response.session_id,
            method="DUPONT",
            market="international",
            operation_type="initialize",
            ticker=dupont_response.ticker,
            valuation_model="DUPONT",
            categories=categories,
            targeted_category=None,
            all_categories_complete=dupont_response.all_categories_complete,
            all_validations_passed=dupont_response.all_validations_passed,
            total_validation_errors=dupont_response.total_validation_errors,
            ready_for_calculation=dupont_response.ready_for_calculation,
            sensitivity_preview=dupont_response.sensitivity_preview,
            message=dupont_response.message
        )
    
    @classmethod
    def transform_comps_response(cls, comps_response: CompsAssumptionsResponse) -> UnifiedStep8Response:
        """
        Transform Comps-specific response to unified schema.
        
        This is the main entry point for Comps transformation.
        """
        logger.info(f"Transforming Comps Step 8 response for {comps_response.ticker} to unified schema")
        
        # Transform categories
        categories = {}
        for category_key, category_response in comps_response.categories.items():
            unified_category = cls.transform_legacy_category_response(
                category_response,
                cls.COMPS_CATEGORY_MAPPING
            )
            categories[category_key] = unified_category
        
        return UnifiedStep8Response(
            status="success",
            session_id=comps_response.session_id,
            method="COMPS",
            market="international",
            operation_type="initialize",
            ticker=comps_response.ticker,
            valuation_model="COMPS",
            categories=categories,
            targeted_category=None,
            all_categories_complete=comps_response.all_categories_complete,
            all_validations_passed=comps_response.all_validations_passed,
            total_validation_errors=comps_response.total_validation_errors,
            ready_for_calculation=comps_response.ready_for_calculation,
            sensitivity_preview=comps_response.sensitivity_preview,
            message=comps_response.message
        )
    
    @classmethod
    def transform_response(
        cls, 
        response: Any, 
        method: str
    ) -> UnifiedStep8Response:
        """
        Generic transformer that routes to method-specific transformer.
        
        Args:
            response: The method-specific response object
            method: The valuation method (DCF, DUPONT, COMPS)
        
        Returns:
            UnifiedStep8Response
        
        Raises:
            ValueError: If method is not recognized
        """
        method_upper = method.upper()
        
        if method_upper == "DCF":
            if not isinstance(response, DCFAssumptionsResponse):
                raise ValueError(f"Expected DCFAssumptionsResponse for DCF method, got {type(response)}")
            return cls.transform_dcf_response(response)
        
        elif method_upper == "DUPONT":
            if not isinstance(response, DuPontAssumptionsResponse):
                raise ValueError(f"Expected DuPontAssumptionsResponse for DuPont method, got {type(response)}")
            return cls.transform_dupont_response(response)
        
        elif method_upper == "COMPS":
            if not isinstance(response, CompsAssumptionsResponse):
                raise ValueError(f"Expected CompsAssumptionsResponse for Comps method, got {type(response)}")
            return cls.transform_comps_response(response)
        
        else:
            raise ValueError(f"Unknown valuation method: {method}. Must be DCF, DUPONT, or COMPS.")
