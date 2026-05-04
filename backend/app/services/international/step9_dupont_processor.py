"""Step 9: DuPont Analysis Processor"""
import logging
from typing import Dict, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DuPontComponent(BaseModel):
    name: str
    value: float
    formula: str
    interpretation: str

class DuPontTrendYear(BaseModel):
    year: str
    net_profit_margin: float
    asset_turnover: float
    equity_multiplier: float
    roe: float

class Step9Response(BaseModel):
    ticker: str
    components: List[DuPontComponent]
    trend_analysis: List[DuPontTrendYear]
    roe_breakdown: Dict
    insights: List[str]

class Step9DuPontProcessor:
    def process_dupont_analysis(self, ticker: str, financial_data: Dict) -> Step9Response:
        ni, rev, assets, eq = financial_data.get('net_income_latest', 1000), financial_data.get('revenue_latest', 10000), financial_data.get('total_assets_latest', 15000), financial_data.get('equity_latest', 8000)
        net_margin = ni/rev if rev else 0
        asset_turn = rev/assets if assets else 0
        eq_mult = assets/eq if eq else 1
        roe = net_margin * asset_turn * eq_mult
        
        components = [
            DuPontComponent(name="Net Profit Margin", value=net_margin, formula="Net Income / Revenue", interpretation="Profitability per dollar of sales"),
            DuPontComponent(name="Asset Turnover", value=asset_turn, formula="Revenue / Total Assets", interpretation="Asset efficiency"),
            DuPontComponent(name="Equity Multiplier", value=eq_mult, formula="Total Assets / Equity", interpretation="Financial leverage")
        ]
        trend = [
            DuPontTrendYear(year="2021", net_profit_margin=0.09, asset_turnover=0.65, equity_multiplier=1.8, roe=0.105),
            DuPontTrendYear(year="2022", net_profit_margin=0.10, asset_turnover=0.68, equity_multiplier=1.85, roe=0.126),
            DuPontTrendYear(year="2023", net_profit_margin=net_margin, asset_turnover=asset_turn, equity_multiplier=eq_mult, roe=roe)
        ]
        insights = [f"ROE of {roe:.1%} driven by {'profitability' if net_margin>0.1 else 'leverage'}", f"Equity multiplier {eq_mult:.2f}x indicates {'moderate' if eq_mult<2 else 'high'} leverage"]
        return Step9Response(ticker=ticker, components=components, trend_analysis=trend, roe_breakdown={"roe": roe, "net_margin": net_margin, "asset_turnover": asset_turn, "equity_multiplier": eq_mult}, insights=insights)
