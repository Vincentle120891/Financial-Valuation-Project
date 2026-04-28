"""
Resilient AI Engine with 3-Tier Fallback (Groq -> Gemini -> Qwen)
Generates structured DCF assumptions with rationale and sources.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

logger = logging.getLogger(__name__)

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")  # Match .env variable name
QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY")  # Alibaba Cloud DashScope key

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

    def generate_assumptions(self, company_data: Dict[str, Any], model_type: str) -> Dict[str, Any]:
        """
        Generate assumptions with fallback logic.
        Returns structured data with value, rationale, and sources.
        """
        prompt = self._build_prompt(company_data, model_type)
        
        # Try each provider in order
        for provider_name, provider_func in self.providers:
            try:
                logger.info(f"🤖 Attempting AI generation via {provider_name.upper()}...")
                response = provider_func(prompt)
                if response:
                    logger.info(f"✅ Successfully generated assumptions via {provider_name.upper()}")
                    return self._parse_response(response, model_type)
            except Exception as e:
                logger.error(f"❌ {provider_name.upper()} failed: {str(e)}")
                continue
        
        # Final fallback: Deterministic rules-based engine
        logger.warning("⚠️ All AI providers failed. Using deterministic fallback rules.")
        return self._deterministic_fallback(company_data, model_type)

    def _build_prompt(self, data: Dict[str, Any], model_type: str) -> str:
        """Construct a detailed prompt for the LLM."""
        ticker = data.get('ticker', 'UNKNOWN')
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        
        return f"""
        You are a senior financial analyst. Generate DCF assumptions for {ticker}.
        
        HISTORICAL DATA:
        - Revenue (TTM): ${financials.get('revenue_ttm', 'N/A')}
        - EBITDA Margin (Avg 3Y): {financials.get('ebitda_margin_avg', 'N/A')}%
        - Net Income Margin (Avg 3Y): {financials.get('net_margin_avg', 'N/A')}%
        - Beta: {market_data.get('beta', 'N/A')}
        - Risk Free Rate: {market_data.get('risk_free_rate', 4.5)}%
        - Sector: {data.get('sector', 'General')}
        
        TASK:
        Return a JSON object with these fields. For EACH field, provide:
        1. "value": The numerical assumption.
        2. "rationale": A simple 1-sentence explanation of WHY this number was chosen.
        3. "sources": The specific data point or formula used (e.g., "Historical Avg 3Y", "CAPM Formula").
        
        FIELDS TO GENERATE:
        - wacc_percent
        - terminal_growth_rate_percent
        - revenue_growth_forecast (list of 5 years)
        - ebitda_margin_target_percent
        - capex_percent_of_revenue
        - depreciation_percent_of_revenue
        - working_capital_days_receivables
        - working_capital_days_payables
        - working_capital_days_inventory
        - tax_rate_percent
        
        OUTPUT FORMAT (STRICT JSON):
        {{
            "wacc_percent": {{ "value": 8.5, "rationale": "...", "sources": "..." }},
            ...
        }}
        """

    def _call_groq(self, prompt: str) -> Optional[str]:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content

    def _call_gemini(self, prompt: str) -> Optional[str]:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt + "\n\nRespond ONLY with valid JSON.")
        # Clean up markdown code blocks if present
        text = response.text
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "")
        return text

    def _call_qwen(self, prompt: str) -> Optional[str]:
        import dashscope
        from dashscope import Generation
        dashscope.api_key = QWEN_API_KEY
        
        response = Generation.call(
            model='qwen-turbo',
            messages=[{'role': 'user', 'content': prompt}],
            result_format='message'
        )
        
        if response.status_code == 200:
            text = response.output.choices[0].message.content
            # Clean up markdown code blocks if present
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "")
            return text
        else:
            raise Exception(f"Qwen API Error: {response.code} - {response.message}")

    def _parse_response(self, json_str: str, model_type: str) -> Dict[str, Any]:
        """Parse and validate the JSON response."""
        try:
            data = json.loads(json_str)
            # Ensure structure compliance
            formatted_data = {}
            for key, item in data.items():
                if isinstance(item, dict) and 'value' in item:
                    formatted_data[key] = item
                elif isinstance(item, list):
                    # Handle lists like revenue_growth_forecast
                    formatted_data[key] = [
                        {"value": v, "rationale": "AI Forecast", "sources": "Trend Extrapolation"} 
                        if not isinstance(v, dict) else v 
                        for v in item
                    ]
                else:
                    # Fallback for malformed items
                    formatted_data[key] = {"value": item, "rationale": "Default", "sources": "System"}
            return formatted_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON: {e}")
            raise ValueError("Invalid JSON from AI")

    def _deterministic_fallback(self, data: Dict[str, Any], model_type: str) -> Dict[str, Any]:
        """Rule-based fallback when all APIs fail."""
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        
        beta = market_data.get('beta', 1.0)
        rf = market_data.get('risk_free_rate', 4.5)
        erp = 5.5  # Standard Equity Risk Premium
        
        # CAPM Calculation
        cost_of_equity = rf + (beta * erp)
        cost_of_debt = 5.0  # Assumed
        tax_rate = 21.0
        wacc = (0.6 * cost_of_equity) + (0.4 * cost_of_debt * (1 - tax_rate/100))
        
        hist_growth = financials.get('revenue_growth_avg', 5.0)
        
        return {
            "wacc_percent": {
                "value": round(wacc, 2),
                "rationale": "Calculated via CAPM (Fallback Mode)",
                "sources": f"Formula: {rf}% + ({beta} × {erp}%)"
            },
            "terminal_growth_rate_percent": {
                "value": 2.0,
                "rationale": "Conservative long-term inflation target",
                "sources": "Fed Target (2%)"
            },
            "revenue_growth_forecast": [
                {"value": round(hist_growth * 0.9, 1), "rationale": "Slight moderation", "sources": "Historical Avg Adj."}
                for _ in range(5)
            ],
            "ebitda_margin_target_percent": {
                "value": financials.get('ebitda_margin_avg', 15.0),
                "rationale": "Maintaining historical efficiency",
                "sources": "3Y Historical Average"
            },
            "capex_percent_of_revenue": {
                "value": 5.0,
                "rationale": "Standard maintenance CapEx assumption",
                "sources": "Industry Standard"
            },
            "depreciation_percent_of_revenue": {
                "value": 3.0,
                "rationale": "Aligned with asset base turnover",
                "sources": "Historical Ratio"
            },
            "working_capital_days_receivables": {"value": 45, "rationale": "Standard terms", "sources": "Industry Norm"},
            "working_capital_days_payables": {"value": 30, "rationale": "Standard terms", "sources": "Industry Norm"},
            "working_capital_days_inventory": {"value": 60, "rationale": "Standard turnover", "sources": "Industry Norm"},
            "tax_rate_percent": {"value": 21.0, "rationale": "Statutory corporate rate", "sources": "US Tax Code"}
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
