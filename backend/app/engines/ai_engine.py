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

    def generate_assumptions(self, company_data: Dict[str, Any], model_type: str) -> Dict[str, Any]:
        """
        Generate assumptions with fallback logic.
        Returns structured data with value, rationale, and sources.
        Includes detailed error tracking for each provider attempt.
        
        Provider Priority Order:
        1. Groq (Primary) - Fastest, most reliable for financial analysis
        2. Gemini (Secondary) - Latest gemini-2.0-flash-lite model
        3. Qwen (Tertiary) - Alibaba Cloud backup
        
        Detailed logging shows waiting time and response status for each provider.
        """
        prompt = self._build_prompt(company_data, model_type)
        last_error = None
        provider_errors = {}  # Track errors from each provider
        
        logger.info("🚀 Starting AI assumption generation...")
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
            "errors": provider_errors,
            "fallback_reason": last_error or "No AI providers configured"
        }
        
        if last_error:
            logger.warning(f"⚠️ All AI providers failed ({last_error}). Using deterministic fallback rules.")
        else:
            logger.warning("⚠️ All AI providers failed. Using deterministic fallback rules.")
            
        return fallback_result

    def _build_prompt(self, data: Dict[str, Any], model_type: str) -> str:
        """
        Construct a detailed, well-structured prompt for the LLM.
        Enhanced with clear instructions, context, and output format requirements.
        
        NOTE: AI ONLY generates 4 inputs that cannot be fetched from APIs:
        1. Equity Risk Premium
        2. Country Risk Premium  
        3. Terminal Growth Rate
        4. Terminal EBITDA Multiple
        
        All other inputs (Risk-Free Rate, Beta, Cost of Debt, WACC, Forecast Drivers)
        are calculated from API data or user-provided scenario drivers.
        """
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
        """Parse and validate the JSON response.
        
        Expected format from AI:
        {
            "equity_risk_premium": <number>,
            "country_risk_premium": <number>,
            "terminal_growth_rate": <number>,
            "terminal_ebitda_multiple": <number>,
            "rationale": "<string>"
        }
        
        Returns formatted data with value/rationale/sources structure for each field.
        """
        try:
            data = json.loads(json_str)
            
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
            
            # Parse the 4 AI-only inputs
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
        
        Returns ONLY the 4 AI-only inputs with sensible defaults:
        1. Equity Risk Premium
        2. Country Risk Premium
        3. Terminal Growth Rate
        4. Terminal EBITDA Multiple
        
        All other inputs are calculated from API data, not generated here.
        """
        financials = data.get('financials', {})
        market_data = data.get('market_data', {})
        country = data.get('country', 'US')
        
        # Standard defaults for the 4 AI-only inputs
        erp = 5.5  # Standard Equity Risk Premium for developed markets
        tgr = 2.0  # Conservative terminal growth (aligned with inflation target)
        tem = 10.0  # Neutral EBITDA multiple
        
        # Adjust CRP based on country (simplified logic)
        emerging_markets = ['BR', 'IN', 'CN', 'RU', 'ZA', 'MX', 'ID', 'TR', 'AR']
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
