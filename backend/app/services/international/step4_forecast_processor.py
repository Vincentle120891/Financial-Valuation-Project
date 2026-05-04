"""Step 4: Forecast Drivers Processor"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ForecastDriver(BaseModel):
    metric: str
    historical_avg: Optional[float] = None
    suggested_value: float
    min_reasonable: float
    max_reasonable: float
    rationale: str
    formula: str
    confidence: float
    status: str = "SUGGESTED"

class Step4Response(BaseModel):
    ticker: str
    forecast_drivers: List[ForecastDriver]
    revenue_growth_forecast: List[Dict]
    margin_assumptions: Dict
    warnings: List[str] = []
    data_quality_score: float = 0.0

class Step4ForecastProcessor:
    def process_forecast_drivers(self, ticker: str, historical_data: Dict, market: str = "international") -> Step4Response:
        logger.info(f"Processing forecast drivers for {ticker}")
        hist_growth = historical_data.get('revenue_cagr_3y', 0.05)
        suggested_growth = max(0.02, min(hist_growth * 0.9, 0.25))
        hist_margin = historical_data.get('avg_ebitda_margin', 0.15)
        tax_rate = 0.21 if market == "international" else 0.20
        
        drivers = [
            ForecastDriver(metric="revenue_growth", historical_avg=hist_growth, suggested_value=suggested_growth, min_reasonable=0.0, max_reasonable=0.30, rationale=f"Based on 3Y CAGR", formula="CAGR × 0.9", confidence=0.75),
            ForecastDriver(metric="ebitda_margin", historical_avg=hist_margin, suggested_value=hist_margin, min_reasonable=0.05, max_reasonable=0.40, rationale="Stable margins", formula="Historical avg", confidence=0.70),
            ForecastDriver(metric="tax_rate", historical_avg=tax_rate, suggested_value=tax_rate, min_reasonable=0.15, max_reasonable=0.35, rationale="Statutory rate", formula="Corporate tax", confidence=0.95)
        ]
        
        current_rev = historical_data.get('latest_revenue', 1000)
        rev_forecast = [{"year": y, "revenue": current_rev * ((1 + suggested_growth) ** y), "growth_rate": suggested_growth} for y in range(1, 6)]
        
        return Step4Response(ticker=ticker, forecast_drivers=drivers, revenue_growth_forecast=rev_forecast, margin_assumptions={"ebitda_margin": hist_margin, "tax_rate": tax_rate}, data_quality_score=75.0)
