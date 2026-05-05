"""Step 8: Manual Overrides Layer - Final Input Consolidator"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class OverrideStatus(str, Enum):
    """Status of manual override"""
    ACCEPTED_AI = "ACCEPTED_AI"  # User accepted AI suggestion
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"  # User manually changed value
    DEFAULT = "DEFAULT"  # Using default/calculated value

class FinalInput(BaseModel):
    """A finalized input value after manual override review"""
    metric: str
    final_value: float
    original_value: Optional[float] = None
    ai_suggested_value: Optional[float] = None
    status: OverrideStatus
    user_override_reason: Optional[str] = None
    is_valid: bool = True
    validation_message: Optional[str] = None

class FinalInputsResponse(BaseModel):
    """
    Step 8 Response: Final consolidated inputs ready for calculation.
    Contains the definitive dataset (Historical + Finalized Assumptions).
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    final_inputs: List[FinalInput]
    historical_data_summary: Dict[str, Any] = {}
    all_validations_passed: bool = True
    validation_errors: List[str] = []
    ready_for_calculation: bool = False
    message: str = ""


class Step8ManualOverridesProcessor:
    """
    Step 8: Manual Refinement Layer (Final Input Consolidator)
    
    - Accepts AI suggestions from Step 7
    - Allows user to manually override any value
    - Validates final inputs
    - Locks them in for calculation
    
    Output: FinalInputsResponse with definitive dataset ready for Step 9
    """
    
    # Validation rules per model
    DCF_VALIDATION_RULES = {
        "WACC": {"min": 0.05, "max": 0.25, "warning_min": 0.08, "warning_max": 0.15},
        "Terminal Growth Rate": {"min": -0.02, "max": 0.08, "warning_min": 0.01, "warning_max": 0.04},
        "Revenue Growth Rate": {"min": -0.20, "max": 0.50, "warning_min": 0.0, "warning_max": 0.30},
        "EBITDA Margin": {"min": 0.05, "max": 0.60, "warning_min": 0.10, "warning_max": 0.40},
        "Tax Rate": {"min": 0.10, "max": 0.40, "warning_min": 0.15, "warning_max": 0.35}
    }
    
    DUPONT_VALIDATION_RULES = {
        "Target Net Profit Margin": {"min": -0.50, "max": 0.60, "warning_min": 0.05, "warning_max": 0.40},
        "Target Asset Turnover": {"min": 0.1, "max": 5.0, "warning_min": 0.5, "warning_max": 2.0},
        "Target Equity Multiplier": {"min": 1.0, "max": 10.0, "warning_min": 1.5, "warning_max": 4.0},
        "Target ROE": {"min": -0.50, "max": 0.60, "warning_min": 0.05, "warning_max": 0.35}
    }
    
    COMPS_VALIDATION_RULES = {
        "P/E Multiple": {"min": 0.5, "max": 100, "warning_min": 5, "warning_max": 50},
        "EV/EBITDA Multiple": {"min": 1, "max": 50, "warning_min": 3, "warning_max": 25},
        "P/B Multiple": {"min": 0.1, "max": 20, "warning_min": 0.5, "warning_max": 10},
        "P/S Multiple": {"min": 0.1, "max": 50, "warning_min": 0.5, "warning_max": 20},
        "Outlier Filter Threshold": {"min": 1.0, "max": 4.0, "warning_min": 1.5, "warning_max": 3.0}
    }
    
    def __init__(self):
        pass
    
    async def process_manual_overrides(
        self,
        ticker: str,
        valuation_model: str,
        step6_data: Dict[str, Any],
        step7_suggestions: Dict[str, Any],
        user_overrides: Optional[Dict[str, float]] = None,
        override_reasons: Optional[Dict[str, str]] = None
    ) -> FinalInputsResponse:
        """
        Process manual overrides and create final inputs.
        
        Args:
            ticker: Stock ticker symbol
            valuation_model: DCF, DUPONT, or COMPS
            step6_data: Aggregated data from Step 6
            step7_suggestions: AI suggestions from Step 7
            user_overrides: Dictionary of metric -> user-provided value
            override_reasons: Dictionary of metric -> reason for override
        
        Returns:
            FinalInputsResponse with validated, locked-in inputs
        """
        user_overrides = user_overrides or {}
        override_reasons = override_reasons or {}
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return await self._process_dcf_overrides(
                ticker, step6_data, step7_suggestions, user_overrides, override_reasons
            )
        elif model_enum == ValuationModel.DUPONT:
            return await self._process_dupont_overrides(
                ticker, step6_data, step7_suggestions, user_overrides, override_reasons
            )
        elif model_enum == ValuationModel.COMPS:
            return await self._process_comps_overrides(
                ticker, step6_data, step7_suggestions, user_overrides, override_reasons
            )
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    async def _process_dcf_overrides(
        self,
        ticker: str,
        step6_data: Dict,
        step7_suggestions: Dict,
        user_overrides: Dict,
        override_reasons: Dict
    ) -> FinalInputsResponse:
        """Process manual overrides for DCF model"""
        final_inputs = []
        validation_errors = []
        
        # Get AI suggestions
        suggestions_map = {}
        if step7_suggestions and 'suggestions' in step7_suggestions:
            for sugg in step7_suggestions['suggestions']:
                suggestions_map[sugg['metric']] = sugg
        
        # Process each DCF assumption
        dcf_metrics = ["WACC", "Terminal Growth Rate", "Revenue Growth Rate", "EBITDA Margin", "Tax Rate"]
        
        for metric in dcf_metrics:
            ai_suggestion = suggestions_map.get(metric)
            ai_value = ai_suggestion['suggested_value'] if ai_suggestion else None
            
            # Determine final value
            if metric in user_overrides:
                final_value = user_overrides[metric]
                status = OverrideStatus.MANUAL_OVERRIDE
                reason = override_reasons.get(metric, "User manual adjustment")
            elif ai_value is not None:
                final_value = ai_value
                status = OverrideStatus.ACCEPTED_AI
                reason = None
            else:
                # Use default
                final_value = self._get_dcf_default(metric)
                status = OverrideStatus.DEFAULT
                reason = None
            
            # Validate
            is_valid, validation_msg = self._validate_dcf_input(metric, final_value)
            if not is_valid:
                validation_errors.append(f"{metric}: {validation_msg}")
            
            final_inputs.append(FinalInput(
                metric=metric,
                final_value=final_value,
                original_value=ai_value,
                ai_suggested_value=ai_value,
                status=status,
                user_override_reason=reason,
                is_valid=is_valid,
                validation_message=validation_msg
            ))
        
        all_valid = len(validation_errors) == 0
        
        return FinalInputsResponse(
            session_id=f"step8_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            final_inputs=final_inputs,
            historical_data_summary=self._summarize_historical_data(step6_data),
            all_validations_passed=all_valid,
            validation_errors=validation_errors,
            ready_for_calculation=all_valid,
            message="All inputs validated and locked. Ready for final calculation in Step 9." if all_valid else f"Validation errors found: {', '.join(validation_errors)}"
        )
    
    async def _process_dupont_overrides(
        self,
        ticker: str,
        step6_data: Dict,
        step7_suggestions: Dict,
        user_overrides: Dict,
        override_reasons: Dict
    ) -> FinalInputsResponse:
        """Process manual overrides for DuPont model"""
        final_inputs = []
        validation_errors = []
        
        # Get AI suggestions
        suggestions_map = {}
        if step7_suggestions and 'suggestions' in step7_suggestions:
            for sugg in step7_suggestions['suggestions']:
                suggestions_map[sugg['metric']] = sugg
        
        # Process each DuPont assumption
        dupont_metrics = ["Target Net Profit Margin", "Target Asset Turnover", "Target Equity Multiplier", "Target ROE"]
        
        for metric in dupont_metrics:
            ai_suggestion = suggestions_map.get(metric)
            ai_value = ai_suggestion['suggested_value'] if ai_suggestion else None
            
            # Determine final value
            if metric in user_overrides:
                final_value = user_overrides[metric]
                status = OverrideStatus.MANUAL_OVERRIDE
                reason = override_reasons.get(metric, "User manual adjustment")
            elif ai_value is not None:
                final_value = ai_value
                status = OverrideStatus.ACCEPTED_AI
                reason = None
            else:
                final_value = self._get_dupont_default(metric)
                status = OverrideStatus.DEFAULT
                reason = None
            
            # Validate
            is_valid, validation_msg = self._validate_dupont_input(metric, final_value)
            if not is_valid:
                validation_errors.append(f"{metric}: {validation_msg}")
            
            final_inputs.append(FinalInput(
                metric=metric,
                final_value=final_value,
                original_value=ai_value,
                ai_suggested_value=ai_value,
                status=status,
                user_override_reason=reason,
                is_valid=is_valid,
                validation_message=validation_msg
            ))
        
        all_valid = len(validation_errors) == 0
        
        return FinalInputsResponse(
            session_id=f"step8_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            final_inputs=final_inputs,
            historical_data_summary=self._summarize_historical_data(step6_data),
            all_validations_passed=all_valid,
            validation_errors=validation_errors,
            ready_for_calculation=all_valid,
            message="All inputs validated and locked. Ready for final calculation in Step 9." if all_valid else f"Validation errors found: {', '.join(validation_errors)}"
        )
    
    async def _process_comps_overrides(
        self,
        ticker: str,
        step6_data: Dict,
        step7_suggestions: Dict,
        user_overrides: Dict,
        override_reasons: Dict
    ) -> FinalInputsResponse:
        """Process manual overrides for Comps model"""
        final_inputs = []
        validation_errors = []
        
        # Get AI suggestions
        suggestions_map = {}
        if step7_suggestions and 'suggestions' in step7_suggestions:
            for sugg in step7_suggestions['suggestions']:
                suggestions_map[sugg['metric']] = sugg
        
        # Process each Comps assumption
        comps_metrics = ["P/E Multiple", "EV/EBITDA Multiple", "P/B Multiple", "P/S Multiple", "Outlier Filter Threshold"]
        
        for metric in comps_metrics:
            ai_suggestion = suggestions_map.get(metric)
            ai_value = ai_suggestion['suggested_value'] if ai_suggestion else None
            
            # Determine final value
            if metric in user_overrides:
                final_value = user_overrides[metric]
                status = OverrideStatus.MANUAL_OVERRIDE
                reason = override_reasons.get(metric, "User manual adjustment")
            elif ai_value is not None:
                final_value = ai_value
                status = OverrideStatus.ACCEPTED_AI
                reason = None
            else:
                final_value = self._get_comps_default(metric)
                status = OverrideStatus.DEFAULT
                reason = None
            
            # Validate
            is_valid, validation_msg = self._validate_comps_input(metric, final_value)
            if not is_valid:
                validation_errors.append(f"{metric}: {validation_msg}")
            
            final_inputs.append(FinalInput(
                metric=metric,
                final_value=final_value,
                original_value=ai_value,
                ai_suggested_value=ai_value,
                status=status,
                user_override_reason=reason,
                is_valid=is_valid,
                validation_message=validation_msg
            ))
        
        all_valid = len(validation_errors) == 0
        
        return FinalInputsResponse(
            session_id=f"step8_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            final_inputs=final_inputs,
            historical_data_summary=self._summarize_historical_data(step6_data),
            all_validations_passed=all_valid,
            validation_errors=validation_errors,
            ready_for_calculation=all_valid,
            message="All inputs validated and locked. Ready for final calculation in Step 9." if all_valid else f"Validation errors found: {', '.join(validation_errors)}"
        )
    
    # === Helper Methods ===
    
    def _get_dcf_default(self, metric: str) -> float:
        """Get default value for DCF metric"""
        defaults = {
            "WACC": 0.10,
            "Terminal Growth Rate": 0.025,
            "Revenue Growth Rate": 0.05,
            "EBITDA Margin": 0.15,
            "Tax Rate": 0.21
        }
        return defaults.get(metric, 0.0)
    
    def _get_dupont_default(self, metric: str) -> float:
        """Get default value for DuPont metric"""
        defaults = {
            "Target Net Profit Margin": 0.10,
            "Target Asset Turnover": 1.2,
            "Target Equity Multiplier": 2.0,
            "Target ROE": 0.24
        }
        return defaults.get(metric, 0.0)
    
    def _get_comps_default(self, metric: str) -> float:
        """Get default value for Comps metric"""
        defaults = {
            "P/E Multiple": 15.0,
            "EV/EBITDA Multiple": 10.0,
            "P/B Multiple": 2.0,
            "P/S Multiple": 2.5,
            "Outlier Filter Threshold": 2.0
        }
        return defaults.get(metric, 0.0)
    
    def _validate_dcf_input(self, metric: str, value: float) -> tuple[bool, str]:
        """Validate DCF input against rules"""
        if metric not in self.DCF_VALIDATION_RULES:
            return True, "Valid"
        
        rules = self.DCF_VALIDATION_RULES[metric]
        if rules["min"] <= value <= rules["max"]:
            if value < rules["warning_min"] or value > rules["warning_max"]:
                return True, f"Valid but outside typical range [{rules['warning_min']} - {rules['warning_max']}]"
            return True, "Valid"
        else:
            return False, f"Outside valid range [{rules['min']} - {rules['max']}]"
    
    def _validate_dupont_input(self, metric: str, value: float) -> tuple[bool, str]:
        """Validate DuPont input against rules"""
        if metric not in self.DUPONT_VALIDATION_RULES:
            return True, "Valid"
        
        rules = self.DUPONT_VALIDATION_RULES[metric]
        if rules["min"] <= value <= rules["max"]:
            if value < rules["warning_min"] or value > rules["warning_max"]:
                return True, f"Valid but outside typical range"
            return True, "Valid"
        else:
            return False, f"Outside valid range [{rules['min']} - {rules['max']}]"
    
    def _validate_comps_input(self, metric: str, value: float) -> tuple[bool, str]:
        """Validate Comps input against rules"""
        if metric not in self.COMPS_VALIDATION_RULES:
            return True, "Valid"
        
        rules = self.COMPS_VALIDATION_RULES[metric]
        if rules["min"] <= value <= rules["max"]:
            if value < rules["warning_min"] or value > rules["warning_max"]:
                return True, f"Valid but outside typical range"
            return True, "Valid"
        else:
            return False, f"Outside valid range [{rules['min']} - {rules['max']}]"
    
    def _summarize_historical_data(self, step6_data: Dict) -> Dict[str, Any]:
        """Create summary of historical data from Step 6"""
        summary = {}
        
        if 'historical_financials' in step6_data:
            hist = step6_data['historical_financials']
            if hasattr(hist, 'years'):
                summary['years_available'] = hist.years
            if hasattr(hist, 'data_fields'):
                summary['fields_count'] = len(hist.data_fields)
        
        return summary
