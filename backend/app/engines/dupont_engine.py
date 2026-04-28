#!/usr/bin/env python3
"""
DuPont Analysis Model - Full Implementation
Matches: MID RETAILER FINANCIAL ANALYSIS specification
NO HARDCODED FALLBACKS - Uses API -> AI -> Manual flow only
"""

import pandas as pd
import logging
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DuPontResult:
    """Standardized DuPont Analysis Result."""
    net_profit_margin: float = 0.0
    asset_turnover: float = 0.0
    equity_multiplier: float = 0.0
    roe: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)
    ai_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    status: str = "success"
    message: str = ""
    detailed_results: Optional[Dict] = None

class DuPontAnalyzer:
    """
    DuPont Analysis Engine.
    Flow: Fetch Data (API/AI) -> Calculate Ratios -> Return Result.
    NO silent fallbacks to hardcoded data.
    """
    
    REQUIRED_FIELDS = [
        "net_income",
        "revenue",
        "total_assets",
        "shareholders_equity"
    ]

    def __init__(self, api_key: str, model: str = "groq-llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.data: Dict = {}
        self.results: Dict = {}
        self.ai_service = None  # Lazy init to avoid circular imports
        
    def _get_ai_service(self):
        """Lazy initialization of AI service to avoid circular imports."""
        if self.ai_service is None:
            from .ai_service import AIService
            self.ai_service = AIService(api_key=self.api_key, model=self.model)
        return self.ai_service

    async def fetch_data(self, ticker: str, verbose: bool = False) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Fetch required financial data.
        Priority: Real API (yfinance) -> AI Estimation -> Mark as Missing.
        NO hardcoded defaults.
        """
        suggestions = []
        metrics = {
            "ticker": ticker.upper() if ticker else None,
            "net_income": None,
            "revenue": None,
            "total_assets": None,
            "shareholders_equity": None,
        }
        
        # Attempt real data fetch first via yfinance
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            fs = stock.financials
            bs = stock.balance_sheet
            
            if not fs.empty and not bs.empty:
                latest_col = fs.columns[0]
                bs_latest_col = bs.columns[0]
                
                # Extract available data
                if "Total Revenue" in fs.index:
                    metrics["revenue"] = float(fs.loc["Total Revenue", latest_col])
                if "Net Income" in fs.index:
                    metrics["net_income"] = float(fs.loc["Net Income", latest_col])
                if "Total Assets" in bs.index:
                    metrics["total_assets"] = float(bs.loc["Total Assets", bs_latest_col])
                if "Total Stockholders Equity" in bs.index:
                    metrics["shareholders_equity"] = float(bs.loc["Total Stockholders Equity", bs_latest_col])
                
                # If we got all data, return early
                if all([metrics[f] for f in self.REQUIRED_FIELDS]):
                    metrics["source"] = "yfinance_api"
                    return metrics, []
        except Exception as e:
            logger.warning(f"yfinance fetch failed for {ticker}: {e}")
        
        # Identify missing fields
        missing = [f for f in self.REQUIRED_FIELDS if metrics.get(f) is None]
        
        if not missing:
            metrics["source"] = "yfinance_api"
            return metrics, []

        # Construct AI Prompt for missing data
        prompt = (
            f"Provide estimated financial values for {ticker} for the most recent fiscal year.\n"
            f"Missing fields: {', '.join(missing)}\n"
            f"Return ONLY a JSON object with keys: {', '.join(missing)} and numeric values.\n"
            f"If exact numbers are unknown, provide reasonable estimates based on industry averages for {ticker}."
        )

        ai_service = self._get_ai_service()
        ai_response = await ai_service.generate_json(prompt, system_prompt="You are a financial data assistant.")
        
        if ai_response and isinstance(ai_response, dict):
            for fld in missing:
                if fld in ai_response:
                    val = ai_response[fld]
                    if isinstance(val, (int, float)):
                        metrics[fld] = val
                        suggestions.append({
                            "field": fld,
                            "value": val,
                            "source": "AI_Estimation",
                            "explanation": f"Value estimated by AI based on industry data for {ticker}."
                        })
                    else:
                        suggestions.append({
                            "field": fld,
                            "value": None,
                            "source": "AI_Failed",
                            "explanation": f"AI could not provide a numeric value for {fld}."
                        })
                else:
                    suggestions.append({
                        "field": fld,
                        "value": None,
                        "source": "AI_Missing",
                        "explanation": f"AI did not return a value for {fld}."
                    })
        
        # Final check for any remaining missing fields
        final_missing = [f for f in self.REQUIRED_FIELDS if metrics.get(f) is None]
        for f in final_missing:
             suggestions.append({
                "field": f,
                "value": None,
                "source": "Manual_Required",
                "explanation": f"Data unavailable via API or AI. Manual input required for {f}."
            })

        metrics["source"] = "hybrid" if any(s["source"] == "AI_Estimation" for s in suggestions) else "incomplete"
        return metrics, suggestions

    async def analyze(self, ticker: str, custom_inputs: Optional[Dict[str, float]] = None) -> DuPontResult:
        """
        Main entry point. Fetches data, applies custom overrides, calculates ratios.
        NO hardcoded fallbacks.
        """
        # 1. Fetch Data
        metrics, suggestions = await self.fetch_data(ticker)
        
        if not metrics:
            return DuPontResult(
                status="error",
                message="Failed to initialize metrics structure.",
                ai_suggestions=suggestions
            )

        # 2. Apply Custom Overrides (Manual Inputs)
        if custom_inputs:
            for key, value in custom_inputs.items():
                if key in metrics and value is not None:
                    metrics[key] = value
                    # Update suggestion to reflect manual override
                    suggestions = [s for s in suggestions if s.get('field') != key]
                    suggestions.append({
                        "field": key,
                        "value": value,
                        "source": "Manual_Override",
                        "explanation": "User provided manual input."
                    })

        # 3. Validate Critical Data
        missing_final = [f for f in self.REQUIRED_FIELDS if metrics.get(f) is None]
        if missing_final:
            return DuPontResult(
                status="incomplete",
                message=f"Cannot calculate DuPont analysis. Missing critical data: {', '.join(missing_final)}",
                missing_fields=missing_final,
                ai_suggestions=suggestions
            )

        # 4. Calculate Ratios
        try:
            net_income = float(metrics["net_income"])
            revenue = float(metrics["revenue"])
            total_assets = float(metrics["total_assets"])
            equity = float(metrics["shareholders_equity"])

            if revenue == 0 or total_assets == 0 or equity == 0:
                 return DuPontResult(
                    status="error",
                    message="Division by zero error in ratio calculation. Check inputs.",
                    ai_suggestions=suggestions
                )

            net_profit_margin = net_income / revenue
            asset_turnover = revenue / total_assets
            equity_multiplier = total_assets / equity
            roe = net_profit_margin * asset_turnover * equity_multiplier

            return DuPontResult(
                net_profit_margin=net_profit_margin,
                asset_turnover=asset_turnover,
                equity_multiplier=equity_multiplier,
                roe=roe,
                components={
                    "net_profit_margin": net_profit_margin,
                    "asset_turnover": asset_turnover,
                    "equity_multiplier": equity_multiplier
                },
                ai_suggestions=suggestions,
                status="success",
                message="DuPont analysis completed successfully.",
                detailed_results=metrics
            )

        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return DuPontResult(
                status="error",
                message=f"Calculation error: {str(e)}",
                ai_suggestions=suggestions
            )

    # Legacy methods removed - use async analyze() instead
    def load_default_data(self) -> bool:
        """DEPRECATED: No longer loads hardcoded data. Raises exception if called."""
        raise NotImplementedError(
            "load_default_data() is deprecated. Use async analyze() method instead. "
            "No hardcoded fallbacks are allowed per system requirements."
        )
        
    def calculate_ratios(self):
        """DEPRECATED: Use async analyze() method instead."""
        raise NotImplementedError(
            "calculate_ratios() is deprecated. Use async analyze() method instead."
        )
        
    def print_report(self):
        """DEPRECATED: Use async analyze() method and handle DuPontResult instead."""
        raise NotImplementedError(
            "print_report() is deprecated. Use async analyze() method and handle DuPontResult instead."
        )
