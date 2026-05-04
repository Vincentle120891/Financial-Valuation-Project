"""
International Valuation Engines Package

Calculation engines for international markets (IFRS/US GAAP):
- DCF valuation engine with WACC calculation
- Comparable company analysis engine
- DuPont ROE decomposition engine
- AI-powered suggestions and fallbacks
"""

from app.engines.international.dcf_engine import (
    DCFEngine,
    DCFInputs,
    ScenarioDrivers,
    ComparableCompany,
    # Note: calculate_dcf_valuation is a method of DCFEngine class
)

from app.engines.international.comps_engine import (
    TradingCompsAnalyzer,
    TargetCompanyData,
    PeerCompanyData,
    # Note: calculate_comps_valuation is a method of TradingCompsAnalyzer class
)

from app.engines.international.dupont_engine import (
    DuPontAnalyzer,
    DuPontResult,
    # Note: analyze_dupont_roe is a method of DuPontAnalyzer class
)

from app.engines.international.ai_engine import (
    ai_engine,
    AIFallbackEngine,
    suggest_peer_companies,
    # Note: generate_financial_insights is not exported - use ai_engine methods directly
)

__all__ = [
    # DCF Engine
    "DCFEngine",
    "DCFInputs",
    "ScenarioDrivers",
    "ComparableCompany",
    
    # Comps Engine
    "TradingCompsAnalyzer",
    "TargetCompanyData",
    "PeerCompanyData",
    
    # DuPont Engine
    "DuPontAnalyzer",
    "DuPontResult",
    
    # AI Engine
    "ai_engine",
    "AIFallbackEngine",
    "suggest_peer_companies",
]
