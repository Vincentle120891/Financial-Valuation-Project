"""Step 5: Assumptions Review Processor - Model-Specific Validation"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

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

class CompsAssumptions(BaseModel):
    """Assumptions specific to Comps analysis"""
    selected_peers: List[str] = []
    valuation_multiples: List[str] = ["P/E", "EV/EBITDA", "P/B", "P/S"]
    apply_outlier_filter: bool = True
    weighting_method: str = "median"  # median, mean, or harmonic_mean

class DuPontAssumptions(BaseModel):
    """Assumptions specific to DuPont analysis"""
    years_to_analyze: int = 3
    include_benchmark_comparison: bool = True
    sector_average_roe: Optional[float] = None

class Step5Response(BaseModel):
    valuation_model: ValuationModel
    validated_assumptions: Optional[List[AssumptionValidation]] = None
    scenarios: Optional[List[ScenarioModel]] = None
    comps_assumptions: Optional[CompsAssumptions] = None
    dupont_assumptions: Optional[DuPontAssumptions] = None
    warnings: List[str] = []
    ready_for_valuation: bool = False
    model_specific_notes: str = ""

class Step5AssumptionsProcessor:
    DCF_VALIDATION_RULES = {
        "revenue_growth": {"min": -0.20, "max": 0.50, "warning_min": 0.0, "warning_max": 0.30},
        "wacc": {"min": 0.05, "max": 0.25, "warning_min": 0.08, "warning_max": 0.15},
        "terminal_growth": {"min": -0.02, "max": 0.08, "warning_min": 0.01, "warning_max": 0.04},
        "ebitda_margin": {"min": 0.05, "max": 0.60, "warning_min": 0.10, "warning_max": 0.40},
        "tax_rate": {"min": 0.10, "max": 0.40, "warning_min": 0.15, "warning_max": 0.35}
    }
    
    COMPS_VALIDATION_RULES = {
        "pe_ratio": {"min": 0.5, "max": 100, "warning_min": 5, "warning_max": 50},
        "ev_ebitda": {"min": 1, "max": 50, "warning_min": 3, "warning_max": 25},
        "pb_ratio": {"min": 0.1, "max": 20, "warning_min": 0.5, "warning_max": 10}
    }
    
    DUPONT_VALIDATION_RULES = {
        "net_margin": {"min": -0.50, "max": 0.60, "warning_min": 0.05, "warning_max": 0.40},
        "asset_turnover": {"min": 0.1, "max": 5.0, "warning_min": 0.5, "warning_max": 2.0},
        "equity_multiplier": {"min": 1.0, "max": 10.0, "warning_min": 1.5, "warning_max": 4.0}
    }
    
    def process_assumptions_review(
        self, 
        assumptions: Dict[str, float], 
        valuation_model: str = "DCF",
        market: str = "international"
    ) -> Step5Response:
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return self._process_dcf_assumptions(assumptions, market)
        elif model_enum == ValuationModel.COMPS:
            return self._process_comps_assumptions(assumptions)
        elif model_enum == ValuationModel.DUPONT:
            return self._process_dupont_assumptions(assumptions)
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    def _process_dcf_assumptions(self, assumptions: Dict[str, float], market: str) -> Step5Response:
        """Validate DCF-specific assumptions"""
        validated, warnings, all_valid = [], [], True
        
        for metric, value in assumptions.items():
            if metric in self.DCF_VALIDATION_RULES:
                rules = self.DCF_VALIDATION_RULES[metric]
                is_valid = rules["min"] <= value <= rules["max"]
                if not is_valid:
                    all_valid = False
                    warnings.append(f"{metric} ({value:.2%}) outside valid range [{rules['min']:.2%} - {rules['max']:.2%}]")
                
                validated.append(AssumptionValidation(
                    metric=metric,
                    value=value,
                    is_valid=is_valid,
                    validation_message="Valid" if is_valid else "Invalid",
                    recommended_range={"min": rules["warning_min"], "max": rules["warning_max"]}
                ))
        
        base_wacc = assumptions.get("wacc", 0.10)
        base_growth = assumptions.get("terminal_growth", 0.025)
        
        scenarios = [
            ScenarioModel(scenario_name="Bull Case", assumptions={"wacc": base_wacc-0.015, "terminal_growth": base_growth+0.01}, description="Optimistic scenario with lower discount rate and higher terminal growth"),
            ScenarioModel(scenario_name="Base Case", assumptions=assumptions, description="Most likely scenario based on current assumptions"),
            ScenarioModel(scenario_name="Bear Case", assumptions={"wacc": base_wacc+0.02, "terminal_growth": base_growth-0.01}, description="Conservative scenario with higher discount rate and lower terminal growth")
        ]
        
        return Step5Response(
            valuation_model=ValuationModel.DCF,
            validated_assumptions=validated,
            scenarios=scenarios,
            warnings=warnings,
            ready_for_valuation=all_valid,
            model_specific_notes="DCF assumptions validated. Ready to calculate intrinsic value."
        )
    
    def _process_comps_assumptions(self, assumptions: Dict[str, float]) -> Step5Response:
        """Validate Comps-specific assumptions"""
        validated, warnings, all_valid = [], [], True
        
        selected_peers = assumptions.get("peer_tickers", [])
        if len(selected_peers) < 3:
            warnings.append(f"Only {len(selected_peers)} peers selected. Minimum 3 recommended for reliable comparison.")
            all_valid = False
        
        for metric, value in assumptions.items():
            if metric in self.COMPS_VALIDATION_RULES:
                rules = self.COMPS_VALIDATION_RULES[metric]
                is_valid = rules["min"] <= value <= rules["max"]
                if not is_valid:
                    all_valid = False
                    warnings.append(f"{metric} ({value:.2f}) outside valid range")
                
                validated.append(AssumptionValidation(
                    metric=metric,
                    value=value,
                    is_valid=is_valid,
                    validation_message="Valid" if is_valid else "Invalid",
                    recommended_range={"min": rules["warning_min"], "max": rules["warning_max"]}
                ))
        
        comps_assumptions = CompsAssumptions(
            selected_peers=selected_peers,
            valuation_multiples=assumptions.get("valuation_multiples", ["P/E", "EV/EBITDA", "P/B", "P/S"]),
            apply_outlier_filter=assumptions.get("apply_outlier_filter", True),
            weighting_method=assumptions.get("weighting_method", "median")
        )
        
        return Step5Response(
            valuation_model=ValuationModel.COMPS,
            comps_assumptions=comps_assumptions,
            validated_assumptions=validated if validated else None,
            warnings=warnings,
            ready_for_valuation=all_valid and len(selected_peers) >= 3,
            model_specific_notes="Comps analysis ready. Ensure peer group is truly comparable."
        )
    
    def _process_dupont_assumptions(self, assumptions: Dict[str, float]) -> Step5Response:
        """Validate DuPont-specific assumptions"""
        validated, warnings, all_valid = [], [], True
        
        for metric, value in assumptions.items():
            if metric in self.DUPONT_VALIDATION_RULES:
                rules = self.DUPONT_VALIDATION_RULES[metric]
                is_valid = rules["min"] <= value <= rules["max"]
                if not is_valid:
                    all_valid = False
                    warnings.append(f"{metric} ({value:.2f}) outside valid range")
                
                validated.append(AssumptionValidation(
                    metric=metric,
                    value=value,
                    is_valid=is_valid,
                    validation_message="Valid" if is_valid else "Invalid",
                    recommended_range={"min": rules["warning_min"], "max": rules["warning_max"]}
                ))
        
        dupont_assumptions = DuPontAssumptions(
            years_to_analyze=assumptions.get("years_to_analyze", 3),
            include_benchmark_comparison=assumptions.get("include_benchmark_comparison", True),
            sector_average_roe=assumptions.get("sector_average_roe")
        )
        
        return Step5Response(
            valuation_model=ValuationModel.DUPONT,
            dupont_assumptions=dupont_assumptions,
            validated_assumptions=validated if validated else None,
            warnings=warnings,
            ready_for_valuation=all_valid,
            model_specific_notes="DuPont analysis will decompose ROE into operational efficiency, asset use efficiency, and financial leverage."
        )
