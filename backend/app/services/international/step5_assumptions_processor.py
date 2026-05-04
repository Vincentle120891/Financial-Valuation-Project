"""Step 5: Assumptions Review Processor"""
import logging
from typing import Dict, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AssumptionValidation(BaseModel):
    metric: str
    value: float
    is_valid: bool
    validation_message: str
    recommended_range: Dict[str, float]

class ScenarioModel(BaseModel):
    scenario_name: str
    assumptions: Dict[str, float]
    description: str

class Step5Response(BaseModel):
    validated_assumptions: List[AssumptionValidation]
    scenarios: List[ScenarioModel]
    warnings: List[str] = []
    ready_for_valuation: bool = False

class Step5AssumptionsProcessor:
    VALIDATION_RULES = {
        "revenue_growth": {"min": -0.20, "max": 0.50, "warning_min": 0.0, "warning_max": 0.30},
        "wacc": {"min": 0.05, "max": 0.25, "warning_min": 0.08, "warning_max": 0.15},
        "terminal_growth": {"min": -0.02, "max": 0.08, "warning_min": 0.01, "warning_max": 0.04}
    }
    
    def process_assumptions_review(self, assumptions: Dict[str, float], market: str = "international") -> Step5Response:
        validated, warnings, all_valid = [], [], True
        for metric, value in assumptions.items():
            if metric in self.VALIDATION_RULES:
                rules = self.VALIDATION_RULES[metric]
                is_valid = rules["min"] <= value <= rules["max"]
                if not is_valid: all_valid = False; warnings.append(f"{metric} outside valid range")
                validated.append(AssumptionValidation(metric=metric, value=value, is_valid=is_valid, validation_message="Valid" if is_valid else "Invalid", recommended_range={"min": rules["warning_min"], "max": rules["warning_max"]}))
        
        base_wacc, base_growth = assumptions.get("wacc", 0.10), assumptions.get("terminal_growth", 0.025)
        scenarios = [
            ScenarioModel(scenario_name="Bull Case", assumptions={"wacc": base_wacc-0.015, "terminal_growth": base_growth+0.01}, description="Optimistic"),
            ScenarioModel(scenario_name="Base Case", assumptions=assumptions, description="Most likely"),
            ScenarioModel(scenario_name="Bear Case", assumptions={"wacc": base_wacc+0.02, "terminal_growth": base_growth-0.01}, description="Conservative")
        ]
        return Step5Response(validated_assumptions=validated, scenarios=scenarios, warnings=warnings, ready_for_valuation=all_valid)
