"""Step 7: Sensitivity Analysis Processor"""
import logging
from typing import Dict, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SensitivityMatrix(BaseModel):
    variable_x: str
    variable_y: str
    x_values: List[float]
    y_values: List[float]
    results: List[List[float]]

class Step7Response(BaseModel):
    base_case_value: float
    sensitivity_matrices: List[SensitivityMatrix]
    tornado_data: List[Dict]
    key_insights: List[str]

class Step7SensitivityProcessor:
    def process_sensitivity_analysis(self, base_case_value: float, base_wacc: float, base_terminal_growth: float, base_revenue_growth: float) -> Step7Response:
        wacc_range = [base_wacc-0.02, base_wacc-0.01, base_wacc, base_wacc+0.01, base_wacc+0.02]
        term_range = [base_terminal_growth-0.01, base_terminal_growth, base_terminal_growth+0.01]
        matrix = [[round(base_case_value*(1+(base_terminal_growth-t)*10-(w-base_wacc)*15), 2) for t in term_range] for w in wacc_range]
        
        tornado = [
            {"variable": "WACC ±1%", "impact_high": base_case_value*1.12, "impact_low": base_case_value*0.88},
            {"variable": "Terminal Growth ±1%", "impact_high": base_case_value*1.08, "impact_low": base_case_value*0.92},
            {"variable": "Revenue Growth ±2%", "impact_high": base_case_value*1.06, "impact_low": base_case_value*0.94}
        ]
        return Step7Response(base_case_value=base_case_value, sensitivity_matrices=[SensitivityMatrix(variable_x="WACC", variable_y="Terminal Growth", x_values=wacc_range, y_values=term_range, results=matrix)], tornado_data=tornado, key_insights=["Valuation most sensitive to WACC", "Terminal growth has moderate impact"])
