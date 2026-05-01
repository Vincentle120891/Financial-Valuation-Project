"""
AI Engine with Strategy Pattern for No-Hallucination Logic
Implements strict separation between AI-generated inputs and calculated/fetched data.

Strategy Pattern:
- PromptStrategy Interface: Defines standard contract for building prompts
- DCFStrategy: Generates 4 forward-looking inputs (ERP, CRP, Terminal Growth, Terminal Multiple)
- VietnamDCFStrategy: Specialized for Vietnam (higher CRP logic, VND context, emerging market risks)
- DuPontStrategy: Returns NULL (all inputs calculated from financials)
- CompsStrategy: Returns NULL (all inputs fetched/calculated from peer data)
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Protocol
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

logger = logging.getLogger(__name__)

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY")


# === Strategy Pattern Interface ===
class PromptStrategy(Protocol):
    """Interface for prompt generation strategies."""
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """Build the prompt for the LLM."""
        ...
    
    def get_ai_inputs(self) -> Dict[str, Any]:
        """Return the AI-generated inputs structure. Returns NULL for strategies that don't use AI."""
        ...


# === Concrete Strategies ===

class DuPontStrategy:
    """
    DuPont Analysis Strategy - NO AI INPUTS
    All metrics are calculated from historical financial statements:
    - Net Profit Margin (from income statement)
    - Asset Turnover (from balance sheet and income statement)
    - Equity Multiplier (from balance sheet)
    """
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """No prompt needed - AI is bypassed for DuPont."""
        return ""
    
    def get_ai_inputs(self) -> Dict[str, Any]:
        """Return NULL - no AI assumptions for DuPont."""
        return None


class CompsStrategy:
    """
    Comparable Company Analysis Strategy - NO AI INPUTS
    All valuation multiples are CALCULATED from peer company data:
    - EV/EBITDA, P/E, EV/Revenue, P/B (all fetched from yfinance)
    """
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """No prompt needed - AI is bypassed for Comps."""
        return ""
    
    def get_ai_inputs(self) -> Dict[str, Any]:
        """Return NULL - no AI assumptions for Comps."""
        return None


class DCFStrategy:
    """
    DCF Strategy - AI generates ONLY 4 forward-looking inputs:
    1. Equity Risk Premium (ERP)
    2. Country Risk Premium (CRP)
    3. Terminal Growth Rate
    4. Terminal EBITDA Multiple
    
    AI is EXPLICITLY FORBIDDEN from guessing:
    - Beta, Risk-Free Rate, Cost of Debt, WACC (calculated from data)
    - Historical Margins, Working Capital Days, Capex % (from financials)
    """
    
    def __init__(self, country: str = "US"):
        self.country = country
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """Build DCF prompt restricted to 4 macro/forward inputs."""
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        sector = data.get('sector', 'General')
        industry = data.get('industry', 'General')
        country = data.get('country', self.country)
        
        # Extract key metrics for context
        revenue_growth = financials.get('revenue_growth_avg', 'N/A')
        ebitda_margin = financials.get('ebitda_margin_avg', 'N/A')
        net_margin = financials.get('net_margin_avg', 'N/A')
        beta = market_data.get('beta', 'N/A')
        risk_free_rate = market_data.get('risk_free_rate', 4.5)
        debt_to_equity = financials.get('debt_to_equity', 'N/A')
        
        return f"""SYSTEM:
You are a financial analyst assistant. You output ONLY raw JSON. No markdown. No explanation outside the JSON. No preamble. No trailing text. If you cannot comply, return {{"error": "<reason>"}}.

USER:
Generate the 4 forward-looking DCF assumptions that cannot be sourced from financial APIs for {company_name} ({ticker}).

## Context
- Sector: {sector}
- Industry: {industry}
- Country: {country}
- Beta: {beta}
- Risk-Free Rate: {risk_free_rate}%
- Avg 3Y Revenue Growth: {revenue_growth}%
- Avg 3Y EBITDA Margin: {ebitda_margin}%
- Avg 3Y Net Margin: {net_margin}%
- Debt-to-Equity: {debt_to_equity}

## Do NOT return
Risk-free rate, beta, cost of debt, WACC, revenue growth forecasts, margins, working capital days, capex %. These are already sourced from API data.

## Return exactly this JSON structure
{{
  "equity_risk_premium": <number>,
  "country_risk_premium": <number>,
  "terminal_growth_rate": <number>,
  "terminal_ebitda_multiple": <number>,
  "rationale": "<one paragraph explaining all 4 choices>"
}}

## Reference ranges
- ERP: 4.5–6.5% developed markets; higher for volatility or uncertainty
- CRP: 0–0.5% (US/UK/DE/JP); 1–5%+ emerging markets; assess {country} for political/currency risk
- Terminal growth: ≤ long-term GDP growth (2–3% developed); must be < WACC
- Terminal EBITDA multiple by sector: Tech 10–15x | Consumer Staples 10–14x | Healthcare 10–14x | Industrials 8–12x | Energy 6–10x | Financials: N/A (use P/B)

Now return the JSON for {ticker}:
""".strip()
    
    def get_ai_inputs(self) -> Dict[str, Any]:
        """Return structure for 4 AI inputs."""
        return {
            "equity_risk_premium": None,
            "country_risk_premium": None,
            "terminal_growth_rate": None,
            "terminal_ebitda_multiple": None,
            "rationale": None
        }


class VietnamDCFStrategy:
    """
    Vietnam DCF Strategy - AI generates 4 inputs with Emerging Market constraints:
    1. Equity Risk Premium (ERP): 6.0% - 8.0% (higher than developed markets)
    2. Country Risk Premium (CRP): 2.0% - 5.0% (Vietnam-specific emerging market risk)
    3. Terminal Growth Rate: 4.0% - 6.0% (aligned with Vietnam's GDP growth)
    4. Terminal EBITDA Multiple: 8x - 12x (generally lower than developed markets)
    
    Includes Vietnam-specific context: FOL, VND currency, VNINDEX volatility, liquidity discounts.
    """
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """Build Vietnam-specific DCF prompt with emerging market constraints."""
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        financials = data.get('financials', {})
        sector = data.get('sector', 'General')
        industry = data.get('industry', 'General')
        
        revenue_growth = financials.get('revenue_growth_avg', 'N/A')
        ebitda_margin = financials.get('ebitda_margin_avg', 'N/A')
        
        return f"""
# ROLE
You are a senior financial analyst specializing in Vietnamese market valuations.

# TASK
Generate ONLY the 4 forward-looking assumptions for Vietnamese market company {company_name} ({ticker}).

# CRITICAL: AI-ONLY INPUTS (with Vietnam-specific constraints)
1. **Equity Risk Premium (ERP)**: 6.0% - 8.0% (Vietnam emerging market premium)
2. **Country Risk Premium (CRP)**: 2.0% - 5.0% (Vietnam-specific political/economic/currency risk)
3. **Terminal Growth Rate**: 4.0% - 6.0% (aligned with Vietnam's long-term GDP growth ~5-6%)
4. **Terminal EBITDA Multiple**: 8x - 12x (Vietnamese market conditions, liquidity discount)

# DO NOT PROVIDE
- Risk-Free Rate (use Vietnamese government bond rate, typically 3-4%)
- Beta (calculated from VNINDEX historical prices)
- Cost of Debt (calculated from interest expense / debt)
- WACC (calculated from CAPM with Vietnam adjustments)
- Margins, Growth Rates, Working Capital Days (all calculated from financials)

# COMPANY CONTEXT
## Historical Performance
- Revenue Growth (Avg 3Y): {revenue_growth}%
- EBITDA Margin (Avg 3Y): {ebitda_margin}%

## Market Data
- Sector: {sector}
- Industry: {industry}
- Country: Vietnam
- Currency: VND

# VIETNAM-SPECIFIC GUIDELINES

## 1. Equity Risk Premium (ERP)
- Range: 6.0% - 8.0% (higher than developed markets due to emerging market risk)
- Consider VNINDEX volatility (historically 25-35% annualized)
- Factor in foreign ownership limits (FOL) impact on liquidity

## 2. Country Risk Premium (CRP)
- Range: 2.0% - 5.0%
- Consider: Political stability, currency risk (VND/USD), economic development stage
- Vietnam specific: Strong GDP growth but emerging market institutional risks

## 3. Terminal Growth Rate
- Range: 4.0% - 6.0%
- Aligned with Vietnam's long-term GDP growth potential (~5-6%)
- Must be less than WACC (otherwise terminal value is infinite)
- Consider company's position in high-growth emerging market

## 4. Terminal EBITDA Multiple
- Range: 8x - 12x (generally lower than developed markets)
- Apply liquidity discount for Vietnamese market (smaller investor base)
- Consider sector peer multiples on HOSE/HNX exchanges

# OUTPUT REQUIREMENTS
Return ONLY valid JSON:
{{
    "equity_risk_premium": <number>,
    "country_risk_premium": <number>,
    "terminal_growth_rate": <number>,
    "terminal_ebitda_multiple": <number>,
    "rationale": "<string explaining all 4 choices with Vietnam context>"
}}

# EXAMPLE RESPONSE
{{
    "equity_risk_premium": 7.0,
    "country_risk_premium": 3.0,
    "terminal_growth_rate": 5.0,
    "terminal_ebitda_multiple": 9.5,
    "rationale": "ERP of 7.0% reflects Vietnam's emerging market status with VNINDEX volatility. CRP of 3.0% accounts for Vietnam-specific political and currency risks. Terminal growth of 5.0% aligns with Vietnam's strong GDP growth trajectory. Terminal EBITDA multiple of 9.5x reflects Vietnamese market liquidity discount and sector peer averages on HOSE."
}}

Now generate the JSON response for {ticker}:
""".strip()
    
    def get_ai_inputs(self) -> Dict[str, Any]:
        """Return structure for 4 AI inputs with Vietnam context."""
        return {
            "equity_risk_premium": None,
            "country_risk_premium": None,
            "terminal_growth_rate": None,
            "terminal_ebitda_multiple": None,
            "rationale": None
        }


# === Strategy Factory ===

def get_strategy(model_type: str, market: str = "US") -> PromptStrategy:
    """
    Factory function to select the appropriate strategy based on model type and market.
    
    Dynamic Routing Logic:
    - DuPont → DuPontStrategy (NULL AI inputs)
    - Comps → CompsStrategy (NULL AI inputs)
    - DCF + Vietnam → VietnamDCFStrategy (4 inputs with EM constraints)
    - DCF + US/International → DCFStrategy (4 inputs standard)
    """
    if model_type == "DuPont":
        return DuPontStrategy()
    elif model_type == "Comps":
        return CompsStrategy()
    elif model_type == "Vietnamese" or (model_type == "DCF" and market == "Vietnam"):
        return VietnamDCFStrategy()
    else:
        # Default to standard DCF for US/International
        return DCFStrategy(country=market)


class AIFallbackEngine:
    def __init__(self):
        self.providers = []
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers based on API keys."""
        if GROQ_API_KEY:
            self.providers.append(("groq", self._call_groq))
        if GEMINI_API_KEY:
            self.providers.append(("gemini", self._call_gemini))
        if QWEN_API_KEY:
            self.providers.append(("qwen", self._call_qwen))
        
        if not self.providers:
            logger.warning("⚠️ NO AI PROVIDERS CONFIGURED. Falling back to deterministic defaults.")
    
    def get_provider_status(self) -> Dict[str, str]:
        """Get status of each provider (available, missing_key, etc.)"""
        status = {}
        if GROQ_API_KEY:
            status["groq"] = "configured"
        else:
            status["groq"] = "missing_key"
        if GEMINI_API_KEY:
            status["gemini"] = "configured"
        else:
            status["gemini"] = "missing_key"
        if QWEN_API_KEY:
            status["qwen"] = "configured"
        else:
            status["qwen"] = "missing_key"
        return status

    def generate_assumptions(self, company_data: Dict[str, Any], model_type: str, market: str = "US") -> Dict[str, Any]:
        """
        Generate assumptions with strategy pattern and fallback logic.
        Returns structured data with value, rationale, and sources.
        
        Strategy Pattern Implementation:
        - DuPont/Comps: Returns NULL immediately (no AI call made)
        - DCF/Vietnam: Uses VietnamDCFStrategy (EM constraints)
        - DCF/US/International: Uses DCFStrategy (standard)
        
        Provider Priority Order (for DCF strategies):
        1. Groq (Primary) - Fastest, most reliable for financial analysis
        2. Gemini (Secondary) - Latest gemini-2.0-flash-lite model
        3. Qwen (Tertiary) - Alibaba Cloud backup
        
        No-Hallucination Guarantee:
        - If model is DuPont or Comps, AI is completely bypassed
        - If model is DCF, AI is restricted to only 4 macro/forward inputs
        """
        # Select strategy based on model type and market
        strategy = get_strategy(model_type, market)
        
        # Check if strategy returns NULL (DuPont or Comps)
        if isinstance(strategy, (DuPontStrategy, CompsStrategy)):
            logger.info(f"ℹ️ {model_type} model: AI bypassed. All inputs calculated/fetched from data.")
            return {
                "ai_assumptions": None,
                "_ai_status": {
                    "success": True,
                    "provider_used": None,
                    "strategy": model_type,
                    "message": f"No AI assumptions required for {model_type} model. All inputs are calculated from financial data."
                }
            }
        
        # For DCF strategies, build prompt using strategy
        prompt = strategy.build_prompt(company_data)
        last_error = None
        provider_errors = {}
        
        logger.info(f"🚀 Starting AI assumption generation with {strategy.__class__.__name__}...")
        logger.info(f"📊 Provider priority order: {[name for name, _ in self.providers]}")
        
        # Try each provider in order
        for provider_name, provider_func in self.providers:
            try:
                logger.info(f"🤖 Attempting AI generation via {provider_name.upper()}...")
                logger.info(f"⏳ Waiting for {provider_name.upper()} response (timeout: 50s)...")
                
                response = provider_func(prompt)
                
                if response:
                    logger.info(f"✅ Successfully generated assumptions via {provider_name.upper()}")
                    return {
                        **self._parse_response(response, model_type),
                        "_ai_status": {
                            "success": True,
                            "provider_used": provider_name,
                            "strategy": strategy.__class__.__name__,
                            "errors": provider_errors
                        }
                    }
                else:
                    logger.warning(f"⚠️ {provider_name.upper()} returned empty response")
                    provider_errors[provider_name] = "Empty response"
                    
            except Exception as e:
                error_msg = f"{provider_name.upper()}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                provider_errors[provider_name] = str(e)
                last_error = error_msg
                logger.info(f"🔄 Falling back to next provider...")
                continue
        
        # Final fallback: Deterministic rules-based engine
        logger.warning("⚠️ All AI providers exhausted, using deterministic fallback...")
        fallback_result = self._deterministic_fallback(company_data, model_type)
        
        # Add detailed error information
        fallback_result["_ai_status"] = {
            "success": False,
            "provider_used": None,
            "strategy": strategy.__class__.__name__,
            "errors": provider_errors,
            "fallback_reason": last_error or "No AI providers configured"
        }
        
        if last_error:
            logger.warning(f"⚠️ All AI providers failed ({last_error}). Using deterministic fallback rules.")
        else:
            logger.warning("⚠️ All AI providers failed. Using deterministic fallback rules.")
            
        return fallback_result
    
    def _build_dcf_prompt(self, data: Dict[str, Any]) -> str:
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        sector = data.get('sector', 'General')
        industry = data.get('industry', 'General')
        country = data.get('country', 'US')
        
        # Extract key metrics for context
        revenue_growth = financials.get('revenue_growth_avg', 'N/A')
        ebitda_margin = financials.get('ebitda_margin_avg', 'N/A')
        net_margin = financials.get('net_margin_avg', 'N/A')
        beta = market_data.get('beta', 'N/A')
        risk_free_rate = market_data.get('risk_free_rate', 4.5)
        debt_to_equity = financials.get('debt_to_equity', 'N/A')
        
        return f"""
# ROLE
You are a senior financial analyst at a top investment bank, specializing in Discounted Cash Flow (DCF) valuation.

# TASK
Generate ONLY the 4 forward-looking assumptions that CANNOT be fetched from financial APIs for {company_name} ({ticker}).

# CRITICAL: AI-ONLY INPUTS
You must provide ONLY these 4 inputs. All other DCF inputs are already calculated from API data:
1. **Equity Risk Premium (ERP)**: Market risk premium over risk-free rate
2. **Country Risk Premium (CRP)**: Additional premium for {country} (0% for US/stable markets)
3. **Terminal Growth Rate**: Perpetual growth rate for terminal value (should not exceed long-term GDP growth)
4. **Terminal EBITDA Multiple**: Exit multiple at end of forecast period

# DO NOT PROVIDE
- Risk-Free Rate (already provided: {risk_free_rate}%)
- Beta (already calculated: {beta})
- Cost of Debt (calculated from interest expense / debt)
- WACC (calculated from CAPM formula)
- Revenue Growth Forecasts (from user scenario drivers or historical averages)
- Margins (calculated from financials)
- Working Capital Days (calculated from balance sheet)
- Capex % (from historical cash flow)

# COMPANY CONTEXT
## Historical Performance
- Revenue Growth (Avg 3Y): {revenue_growth}%
- EBITDA Margin (Avg 3Y): {ebitda_margin}%
- Net Margin (Avg 3Y): {net_margin}%
- Debt-to-Equity: {debt_to_equity}

## Market Data
- Beta: {beta}
- Risk-Free Rate: {risk_free_rate}%
- Sector: {sector}
- Industry: {industry}
- Country: {country}

# OUTPUT REQUIREMENTS
Return ONLY valid JSON with exactly these 4 keys plus rationale:
{{
    "equity_risk_premium": <number>,
    "country_risk_premium": <number>,
    "terminal_growth_rate": <number>,
    "terminal_ebitda_multiple": <number>,
    "rationale": "<string explaining all 4 choices>"
}}

# GUIDELINES FOR EACH INPUT

## 1. Equity Risk Premium (ERP)
- Typical range: 4.5% - 6.5% for developed markets
- Use higher end for volatile markets or uncertain economic conditions
- Consider current market volatility and economic outlook

## 2. Country Risk Premium (CRP)
- US, UK, Germany, Japan: 0% - 0.5%
- Emerging markets: 1% - 5%+ depending on risk
- For {country}: assess political stability, currency risk, economic development

## 3. Terminal Growth Rate
- Should not exceed long-term GDP growth (typically 2% - 3% for developed markets)
- Must be less than WACC (otherwise terminal value is infinite)
- Consider company's mature growth prospects and industry lifecycle

## 4. Terminal EBITDA Multiple
- Based on industry peers and company's competitive position
- Typical ranges by sector:
  - Technology: 10x - 15x
  - Consumer Staples: 10x - 14x
  - Healthcare: 10x - 14x
  - Industrials: 8x - 12x
  - Energy: 6x - 10x
  - Financials: Not typically used (use P/B instead)
- Consider company's growth profile vs peers (higher growth = higher multiple)

# EXAMPLE RESPONSE
{{
    "equity_risk_premium": 5.5,
    "country_risk_premium": 0.0,
    "terminal_growth_rate": 2.0,
    "terminal_ebitda_multiple": 10.5,
    "rationale": "ERP of 5.5% reflects current market conditions with moderate volatility. CRP of 0% as company operates primarily in US stable market. Terminal growth of 2.0% aligns with long-term Fed inflation target and GDP growth expectations. Terminal EBITDA multiple of 10.5x is based on sector peer average, adjusted for company's mature market position and stable cash flows."
}}

Now generate the JSON response for {ticker}:
""".strip()

    def _build_dupont_prompt(self, data: Dict[str, Any]) -> str:
        """
        DuPont Analysis requires NO AI-generated inputs.
        All metrics are calculated from historical financial statements.
        
        This prompt informs the AI that no action is needed for DuPont.
        """
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        
        return f"""
# ROLE
You are a senior financial analyst specializing in DuPont analysis.

# TASK
NO AI INPUTS REQUIRED for DuPont Analysis.

DuPont analysis is a PURELY HISTORICAL calculation that decomposes ROE into:
1. Net Profit Margin (from income statement)
2. Asset Turnover (from balance sheet and income statement)
3. Equity Multiplier (from balance sheet)

All required inputs are fetched from yfinance API:
- Revenue, Net Income → Margins
- Total Assets, Total Equity → Leverage ratios
- Working Capital components (AR, Inventory, AP) → Efficiency ratios

# COMPANY CONTEXT
- Ticker: {ticker}
- Name: {company_name}

# OUTPUT
Return an empty JSON object as no AI assumptions are needed:
{{}}

Do NOT generate any forward-looking assumptions. All DuPont metrics will be calculated from historical API data.
""".strip()

    def _build_comps_prompt(self, data: Dict[str, Any]) -> str:
        """
        Comps Analysis requires NO AI-generated valuation inputs.
        All multiples are calculated from peer company financial data.
        
        NOTE: Peer suggestion is handled separately by suggest_peer_companies().
        This prompt confirms no additional AI inputs are needed.
        """
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        sector = data.get('sector', 'General')
        industry = data.get('industry', 'General')
        
        return f"""
# ROLE
You are a senior equity research analyst specializing in comparable company analysis.

# TASK
NO AI INPUTS REQUIRED for Comparable Company Analysis.

All valuation multiples are CALCULATED from peer company data:
- EV/EBITDA = Enterprise Value / EBITDA (fetched from yfinance)
- P/E = Price per Share / EPS (fetched from yfinance)
- EV/Revenue = Enterprise Value / Revenue (fetched from yfinance)
- P/B = Market Cap / Book Value (fetched from yfinance)

Peer companies are suggested via separate function (suggest_peer_companies).

# COMPANY CONTEXT
- Ticker: {ticker}
- Name: {company_name}
- Sector: {sector}
- Industry: {industry}

# OUTPUT
Return an empty JSON object as no AI assumptions are needed:
{{}}

Do NOT generate any multiples or forward-looking assumptions. All Comps metrics will be calculated from peer API data.
""".strip()

    def _build_vietnamese_prompt(self, data: Dict[str, Any]) -> str:
        """
        Vietnamese Model may require market-specific assumptions.
        For now, similar to DCF but with Vietnam-specific context.
        """
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        country = data.get('country', 'Vietnam')
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        
        revenue_growth = financials.get('revenue_growth_avg', 'N/A')
        ebitda_margin = financials.get('ebitda_margin_avg', 'N/A')
        
        return f"""
# ROLE
You are a senior financial analyst specializing in Vietnamese market valuations.

# TASK
Generate ONLY the 4 forward-looking assumptions for Vietnamese market company {company_name} ({ticker}).

# CRITICAL: AI-ONLY INPUTS (same as DCF)
1. **Equity Risk Premium (ERP)**: Market risk premium for Vietnamese market
2. **Country Risk Premium (CRP)**: Vietnam-specific risk premium (typically 2-4% for emerging market)
3. **Terminal Growth Rate**: Perpetual growth rate (should not exceed Vietnam's long-term GDP growth ~5-6%)
4. **Terminal EBITDA Multiple**: Exit multiple based on Vietnamese market conditions

# DO NOT PROVIDE
- Risk-Free Rate (use Vietnamese government bond rate)
- Beta (calculated from historical prices)
- Cost of Debt (calculated from interest expense / debt)
- WACC (calculated from CAPM)
- Margins, Growth Rates, Working Capital Days (all calculated from financials)

# COMPANY CONTEXT
## Historical Performance
- Revenue Growth (Avg 3Y): {revenue_growth}%
- EBITDA Margin (Avg 3Y): {ebitda_margin}%

## Market Data
- Sector: {data.get('sector', 'General')}
- Industry: {data.get('industry', 'General')}
- Country: {country}

# VIETNAM-SPECIFIC GUIDELINES
- ERP for Vietnam: Typically 6.0% - 8.0% (higher than developed markets due to emerging market risk)
- CRP for Vietnam: 2.0% - 4.0% (reflecting emerging market political/economic risk)
- Terminal Growth: 4.0% - 6.0% (aligned with Vietnam's higher GDP growth potential)
- Terminal Multiples: Generally lower than developed markets (8x - 12x typical)

# OUTPUT REQUIREMENTS
Return ONLY valid JSON:
{{
    "equity_risk_premium": <number>,
    "country_risk_premium": <number>,
    "terminal_growth_rate": <number>,
    "terminal_ebitda_multiple": <number>,
    "rationale": "<string explaining all 4 choices with Vietnam context>"
}}

# EXAMPLE RESPONSE
{{
    "equity_risk_premium": 7.0,
    "country_risk_premium": 3.0,
    "terminal_growth_rate": 5.0,
    "terminal_ebitda_multiple": 9.5,
    "rationale": "ERP of 7.0% reflects Vietnam's emerging market status with moderate volatility. CRP of 3.0% accounts for Vietnam-specific political and currency risks. Terminal growth of 5.0% aligns with Vietnam's strong GDP growth expectations. Terminal EBITDA multiple of 9.5x reflects Vietnamese market discount vs developed market peers."
}}

Now generate the JSON response for {ticker}:
""".strip()

    def _build_international_prompt(self, data: Dict[str, Any]) -> str:
        """
        International Model requires cross-border adjustments.
        Similar to DCF but with multi-country considerations.
        """
        ticker = data.get('ticker', 'UNKNOWN')
        company_name = data.get('company_name', 'Unknown Company')
        country = data.get('country', 'US')
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        
        revenue_growth = financials.get('revenue_growth_avg', 'N/A')
        ebitda_margin = financials.get('ebitda_margin_avg', 'N/A')
        
        return f"""
# ROLE
You are a senior financial analyst specializing in international/cross-border valuations.

# TASK
Generate ONLY the 4 forward-looking assumptions for international company {company_name} ({ticker}) operating in {country}.

# CRITICAL: AI-ONLY INPUTS (same as DCF, with international context)
1. **Equity Risk Premium (ERP)**: Base market risk premium (adjust for developed vs emerging)
2. **Country Risk Premium (CRP)**: Specific to {country} operations
3. **Terminal Growth Rate**: Perpetual growth rate (consider country's long-term GDP growth)
4. **Terminal EBITDA Multiple**: Exit multiple (adjust for market development level)

# DO NOT PROVIDE
- Risk-Free Rate (use appropriate government bond rate for base currency)
- Beta (calculated from historical prices, may need unlevering/relevering)
- Cost of Debt (calculated from interest expense / debt)
- WACC (calculated from CAPM with country adjustments)
- Margins, Growth Rates, Working Capital Days (all calculated from financials)

# COMPANY CONTEXT
## Historical Performance
- Revenue Growth (Avg 3Y): {revenue_growth}%
- EBITDA Margin (Avg 3Y): {ebitda_margin}%

## Market Data
- Sector: {data.get('sector', 'General')}
- Industry: {data.get('industry', 'General')}
- Country: {country}

# INTERNATIONAL GUIDELINES
- Developed Markets (US, UK, Germany, Japan):
  - ERP: 4.5% - 6.0%
  - CRP: 0% - 0.5%
  - Terminal Growth: 1.5% - 2.5%
  - Multiples: Market-appropriate (Tech 12-15x, Industrials 8-12x, etc.)

- Emerging Markets (China, India, Brazil, etc.):
  - ERP: 6.0% - 8.0%
  - CRP: 1.5% - 5.0%+
  - Terminal Growth: 3.0% - 6.0%
  - Multiples: Typically 20-30% discount to developed markets

# OUTPUT REQUIREMENTS
Return ONLY valid JSON:
{{
    "equity_risk_premium": <number>,
    "country_risk_premium": <number>,
    "terminal_growth_rate": <number>,
    "terminal_ebitda_multiple": <number>,
    "rationale": "<string explaining all 4 choices with international context>"
}}

Now generate the JSON response for {ticker}:
""".strip()

    def _call_groq(self, prompt: str) -> Optional[str]:
        """
        Call Groq API with detailed logging and timeout handling.
        Groq is the PRIMARY provider - fastest and most reliable for financial analysis.
        """
        from groq import Groq
        import time
        
        start_time = time.time()
        logger.info("⏳ Connecting to Groq API (Primary Provider)...")
        
        try:
            client = Groq(api_key=GROQ_API_KEY, timeout=60000)
            logger.info("📡 Sending request to Groq (llama-3.3-70b-versatile)...")
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst specializing in DCF valuation. Always respond with valid JSON only, no markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=50
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Groq response received in {elapsed:.2f}s")
            
            return completion.choices[0].message.content
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Groq failed after {elapsed:.2f}s: {str(e)}")
            raise

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """
        Call Gemini API with latest gemini-2.0-flash-lite model.
        Secondary fallback provider with detailed logging.
        """
        import google.generativeai as genai
        import time
        
        start_time = time.time()
        logger.info("⏳ Connecting to Google Gemini API (Secondary Provider - gemini-2.0-flash-lite)...")
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Use the latest lite version for speed and cost efficiency
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            logger.info("📡 Sending request to Gemini...")
            
            response = model.generate_content(
                prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. Do not include markdown code blocks or any explanatory text outside the JSON.",
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                ),
                request_options={'timeout': 50}
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Gemini response received in {elapsed:.2f}s")
            
            # Clean up markdown code blocks if present
            text = response.text
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "")
            elif text.startswith("```"):
                text = text.replace("```", "")
            
            return text.strip()
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Gemini failed after {elapsed:.2f}s: {str(e)}")
            raise
        genai.configure(api_key=GEMINI_API_KEY)
        # Use available model - gemini-pro or gemini-1.5-pro
        try:
            model = genai.GenerativeModel('gemini-pro')
        except Exception:
            # Fallback to default available model
            model = genai.GenerativeModel()
        response = model.generate_content(prompt + "\n\nRespond ONLY with valid JSON.")
        # Clean up markdown code blocks if present
        text = response.text
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "")
        return text

    def _call_qwen(self, prompt: str) -> Optional[str]:
        """
        Call Qwen API as tertiary fallback with detailed logging.
        """
        import dashscope
        from dashscope import Generation
        import time
        
        start_time = time.time()
        logger.info("⏳ Connecting to Alibaba Qwen API (Tertiary Provider - qwen-turbo)...")
        
        try:
            dashscope.api_key = QWEN_API_KEY
            
            response = Generation.call(
                model='qwen-turbo',
                messages=[
                    {'role': 'system', 'content': 'You are a senior financial analyst. Respond ONLY with valid JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                result_format='message',
                timeout=50
            )
            
            if response.status_code == 200:
                elapsed = time.time() - start_time
                logger.info(f"✅ Qwen response received in {elapsed:.2f}s")
                
                text = response.output.choices[0].message.content
                # Clean up markdown code blocks if present
                if text.startswith("```json"):
                    text = text.replace("```json", "").replace("```", "")
                elif text.startswith("```"):
                    text = text.replace("```", "")
                return text.strip()
            else:
                elapsed = time.time() - start_time
                logger.error(f"❌ Qwen failed after {elapsed:.2f}s: {response.code} - {response.message}")
                raise Exception(f"Qwen API Error: {response.code} - {response.message}")
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Qwen failed after {elapsed:.2f}s: {str(e)}")
            raise

    def _parse_response(self, json_str: str, model_type: str) -> Dict[str, Any]:
        """Parse and validate the JSON response based on model type.
        
        DCF/Vietnamese/International format from AI:
        {
            "equity_risk_premium": <number>,
            "country_risk_premium": <number>,
            "terminal_growth_rate": <number>,
            "terminal_ebitda_multiple": <number>,
            "rationale": "<string>"
        }
        
        DuPont/Comps format from AI:
        {}  (empty - no AI inputs needed)
        
        Returns formatted data with value/rationale/sources structure for each field.
        """
        try:
            data = json.loads(json_str)
            
            # For DuPont and Comps, return empty dict (no AI inputs needed)
            if model_type in ['DuPont', 'Comps']:
                logger.info(f"Model {model_type} requires no AI inputs. Returning empty dict.")
                return {}
            
            # Helper function to wrap values in standard format
            def wrap_value(key, default_value=None):
                if key in data:
                    return {
                        "value": float(data[key]),
                        "rationale": data.get('rationale', 'AI-generated assumption'),
                        "sources": "AI Analysis"
                    }
                elif default_value is not None:
                    return {
                        "value": default_value,
                        "rationale": "Default fallback value",
                        "sources": "System Default"
                    }
                return None
            
            formatted_data = {}
            
            # Parse the 4 AI-only inputs (for DCF, Vietnamese, International models)
            erp = wrap_value('equity_risk_premium', 5.5)
            if erp:
                formatted_data['equity_risk_premium'] = erp
                
            crp = wrap_value('country_risk_premium', 0.0)
            if crp:
                formatted_data['country_risk_premium'] = crp
                
            tgr = wrap_value('terminal_growth_rate', 2.0)
            if tgr:
                formatted_data['terminal_growth_rate'] = tgr
                
            tem = wrap_value('terminal_ebitda_multiple', 10.0)
            if tem:
                formatted_data['terminal_ebitda_multiple'] = tem
            
            # Include rationale at top level if present
            if 'rationale' in data:
                formatted_data['ai_rationale'] = {
                    "value": data['rationale'],
                    "rationale": "Complete AI rationale for all 4 assumptions",
                    "sources": "AI Analysis"
                }
            
            return formatted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON: {e}")
            raise ValueError("Invalid JSON from AI")

    def _deterministic_fallback(self, data: Dict[str, Any], model_type: str) -> Dict[str, Any]:
        """Rule-based fallback when all APIs fail.
        
        Returns ONLY the 4 AI-only inputs for DCF/Vietnamese/International models.
        Returns empty dict for DuPont/Comps (no AI inputs needed).
        
        All other inputs are calculated from API data, not generated here.
        """
        # DuPont and Comps require NO AI inputs
        if model_type in ['DuPont', 'Comps']:
            logger.info(f"Model {model_type} requires no AI inputs. Returning empty fallback.")
            return {}
        
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        country = data.get('country', 'US')
        
        # Standard defaults for the 4 AI-only inputs
        erp = 5.5  # Standard Equity Risk Premium for developed markets
        tgr = 2.0  # Conservative terminal growth (aligned with inflation target)
        tem = 10.0  # Neutral EBITDA multiple
        
        # Adjust CRP based on country (simplified logic)
        emerging_markets = ['BR', 'IN', 'CN', 'RU', 'ZA', 'MX', 'ID', 'TR', 'AR', 'VN']
        crp = 2.0 if any(code in country.upper() for code in emerging_markets) else 0.0
        
        return {
            "equity_risk_premium": {
                "value": erp,
                "rationale": "Standard equity risk premium for developed markets",
                "sources": "Damodaran Data (Fallback)"
            },
            "country_risk_premium": {
                "value": crp,
                "rationale": f"Country risk adjustment for {country} ({'emerging market' if crp > 0 else 'developed market'})",
                "sources": "Country Risk Classification (Fallback)"
            },
            "terminal_growth_rate": {
                "value": tgr,
                "rationale": "Conservative long-term growth aligned with central bank inflation targets",
                "sources": "Fed/ECB Target 2% (Fallback)"
            },
            "terminal_ebitda_multiple": {
                "value": tem,
                "rationale": "Neutral industry average multiple",
                "sources": "Sector Comparables Average (Fallback)"
            },
            "ai_rationale": {
                "value": f"Deterministic fallback: ERP={erp}%, CRP={crp}% for {country}, Terminal Growth={tgr}%, Terminal EBITDA Multiple={tem}x. These are conservative default values used when AI providers are unavailable.",
                "rationale": "Fallback mode - all AI providers exhausted",
                "sources": "System Defaults"
            }
        }

# Singleton instance
ai_engine = AIFallbackEngine()


# ============================================================================
# PEER SUGGESTION ENGINE
# ============================================================================

def suggest_peer_companies(target_ticker: str, num_peers: int = 10) -> List[Dict[str, str]]:
    """
    Use AI to suggest peer companies for comparable analysis.
    Returns a list of dictionaries with ticker, company_name, industry, and selection_reason.
    """
    import yfinance as yf
    
    # First, get basic info about the target company
    try:
        target = yf.Ticker(target_ticker)
        info = target.info
        company_name = info.get("longName", target_ticker)
        industry = info.get("industry", "General")
        sector = info.get("sector", "General")
        description = info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else ""
        country = info.get("country", "")
    except Exception as e:
        logger.warning(f"Could not fetch target company info: {e}")
        company_name = target_ticker
        industry = "General"
        sector = "General"
        description = ""
        country = ""
    
    prompt = f"""
You are a senior equity research analyst specializing in comparable company analysis.

TARGET COMPANY:
- Ticker: {target_ticker}
- Name: {company_name}
- Industry: {industry}
- Sector: {sector}
- Country: {country}
- Business Description: {description}

TASK:
Suggest exactly {num_peers} publicly traded peer companies for comparable valuation analysis.

CRITERIA FOR PEER SELECTION:
1. Direct competitors in the same industry/sector
2. Similar business models and revenue streams
3. Comparable market capitalization (when possible)
4. Geographic overlap (same regions/countries)
5. Publicly traded with available financial data
6. Mix of: direct competitors, regional peers, and global benchmarks

For EACH peer, provide:
- ticker: Stock ticker symbol (include exchange suffix if needed, e.g., "TSCO.L" for London)
- company_name: Full legal name
- industry: Their specific industry
- selection_reason: Detailed explanation (2-3 sentences) of WHY this company is a relevant peer

OUTPUT FORMAT (STRICT JSON ARRAY):
[
  {{
    "ticker": "SBRY.L",
    "company_name": "J Sainsbury plc",
    "industry": "Grocery Retail",
    "selection_reason": "Direct UK supermarket competitor fighting for same customers. Second-largest UK grocery chain with similar format stores, loyalty programs, and banking divisions. Closest rival to Tesco as #1 and #2 UK players."
  }},
  ...
]

Respond ONLY with valid JSON array. No markdown, no explanations outside JSON.
"""
    
    # Try to use AI engine if available
    if ai_engine.providers:
        try:
            for provider_name, provider_func in ai_engine.providers:
                try:
                    response = provider_func(prompt)
                    if response:
                        # Clean up response
                        text = response.strip()
                        if text.startswith("```json"):
                            text = text.replace("```json", "").replace("```", "").strip()
                        elif text.startswith("```"):
                            text = text.replace("```", "").strip()
                        
                        # Parse JSON
                        peers = json.loads(text)
                        if isinstance(peers, list) and len(peers) > 0:
                            logger.info(f"✅ Successfully generated {len(peers)} peer suggestions via {provider_name.upper()}")
                            return peers
                except Exception as e:
                    logger.error(f"Provider {provider_name} failed: {e}")
                    continue
        except Exception as e:
            logger.error(f"AI peer suggestion failed: {e}")
    
    # Fallback: Return empty list with warning
    logger.warning("⚠️ Could not generate AI peer suggestions. Returning empty list.")
    return []
