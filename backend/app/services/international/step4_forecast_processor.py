"""Step 4: Forecast Drivers Processor - Model Selection Point"""
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

class CompsInputs(BaseModel):
    """Inputs specific to Comps analysis"""
    peer_tickers: List[str] = []
    valuation_multiples: List[str] = ["P/E", "EV/EBITDA", "P/B", "P/S"]
    apply_outlier_filter: bool = True

class DuPontInputs(BaseModel):
    """Inputs specific to DuPont analysis"""
    years_to_analyze: int = 3
    include_trend_analysis: bool = True
    custom_ratios: Optional[Dict[str, float]] = None

class Step4Response(BaseModel):
    ticker: str
    valuation_model: ValuationModel
    forecast_drivers: Optional[List[ForecastDriver]] = None
    revenue_growth_forecast: Optional[List[Dict]] = None
    margin_assumptions: Optional[Dict] = None
    comps_inputs: Optional[CompsInputs] = None
    dupont_inputs: Optional[DuPontInputs] = None
    warnings: List[str] = []
    data_quality_score: float = 0.0
    model_specific_notes: str = ""

class Step4ForecastProcessor:
    def process_forecast_drivers(
        self, 
        ticker: str, 
        historical_data: Dict, 
        valuation_model: str = "DCF",
        market: str = "international",
        peer_tickers: Optional[List[str]] = None
    ) -> Step4Response:
        logger.info(f"Processing forecast drivers for {ticker} using {valuation_model} model")
        
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return self._process_dcf_inputs(ticker, historical_data, market)
        elif model_enum == ValuationModel.COMPS:
            return self._process_comps_inputs(ticker, historical_data, peer_tickers)
        elif model_enum == ValuationModel.DUPONT:
            return self._process_dupont_inputs(ticker, historical_data)
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    def _process_dcf_inputs(self, ticker: str, historical_data: Dict, market: str) -> Step4Response:
        """Process inputs for DCF model"""
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
        
        return Step4Response(
            ticker=ticker,
            valuation_model=ValuationModel.DCF,
            forecast_drivers=drivers,
            revenue_growth_forecast=rev_forecast,
            margin_assumptions={"ebitda_margin": hist_margin, "tax_rate": tax_rate},
            data_quality_score=75.0,
            model_specific_notes="DCF model requires cash flow projections, WACC, and terminal value assumptions"
        )
    
    def _process_comps_inputs(self, ticker: str, historical_data: Dict, peer_tickers: Optional[List[str]] = None) -> Step4Response:
        """Process inputs for Comps model"""
        if peer_tickers is None:
            peer_tickers = []
            warnings = ["No peer tickers provided. Please select comparable companies."]
            data_quality = 50.0
        else:
            warnings = []
            data_quality = 80.0
        
        comps_inputs = CompsInputs(
            peer_tickers=peer_tickers,
            valuation_multiples=["P/E", "EV/EBITDA", "P/B", "P/S"],
            apply_outlier_filter=True
        )
        
        return Step4Response(
            ticker=ticker,
            valuation_model=ValuationModel.COMPS,
            comps_inputs=comps_inputs,
            warnings=warnings,
            data_quality_score=data_quality,
            model_specific_notes="Comps model compares valuation multiples against peer companies"
        )
    
    def _process_dupont_inputs(self, ticker: str, historical_data: Dict) -> Step4Response:
        """Process inputs for DuPont model"""
        dupont_inputs = DuPontInputs(
            years_to_analyze=3,
            include_trend_analysis=True,
            custom_ratios=None
        )
        
        has_income_statement = 'net_income' in historical_data or 'latest_net_income' in historical_data
        has_balance_sheet = 'total_assets' in historical_data or 'shareholders_equity' in historical_data
        
        warnings = []
        data_quality = 85.0
        
        if not has_income_statement:
            warnings.append("Income statement data missing for DuPont analysis")
            data_quality -= 20.0
        if not has_balance_sheet:
            warnings.append("Balance sheet data missing for DuPont analysis")
            data_quality -= 20.0
        
        return Step4Response(
            ticker=ticker,
            valuation_model=ValuationModel.DUPONT,
            dupont_inputs=dupont_inputs,
            warnings=warnings,
            data_quality_score=max(data_quality, 0.0),
            model_specific_notes="DuPont model decomposes ROE into Net Margin, Asset Turnover, and Equity Multiplier"
        )
