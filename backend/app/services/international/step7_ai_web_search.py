"""
AI Web Search Service for Step 7 Historical Data Retrieval
Uses Groq, Gemini, and Qwen via AIFallbackEngine to search and extract financial data.
"""
import json
import re
from typing import Dict, Any, Optional, List
from app.services.international.ai_engine import AIFallbackEngine
from app.core.logging_config import get_logger
from app.services.step7_web_search_analysis import analyze_web_search_results, validate_and_clean_financial_data

logger = get_logger(__name__)

class AIWebSearchExtractor:
    """
    Extracts historical financial data using AI web search capabilities.
    Supports Groq, Gemini, and Qwen providers with automatic fallback.
    """

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.ai_engine = AIFallbackEngine(api_keys=api_keys)

    def _build_search_prompt(self, ticker: str, company_name: str, market: str, metrics: List[str], context_data: Optional[Dict] = None) -> str:
        """Build a structured prompt for AI web search — only asks for missing metrics.
        
        Uses actual fiscal year periods from Step 6 data to ensure the AI returns
        data for the correct periods (not generic calendar years).
        """
        metric_list = ", ".join(metrics)
        # Build dynamic JSON example with only the requested metrics
        example_fields = ",\n            ".join([f'"{m.lower().replace(" ", "_").replace("(", "").replace(")", "")}": 0' for m in metrics])
        
        # Extract actual fiscal year periods from Step 6 context data
        periods_info = ""
        example_periods = ""
        if context_data:
            periods = []
            
            # PRIMARY: periods_covered is at the TOP level of UnifiedStep6Response
            top_level_periods = context_data.get("periods_covered", [])
            if isinstance(top_level_periods, list):
                periods = [p for p in top_level_periods if p and not str(p).startswith("Period_")]
            
            # FALLBACK: Check calculated_metrics for periods_covered (some data shapes nest it)
            if not periods:
                calc_metrics = context_data.get("calculated_metrics", {})
                if isinstance(calc_metrics, dict):
                    cm_periods = calc_metrics.get("periods_covered", [])
                    if isinstance(cm_periods, list):
                        periods = [p for p in cm_periods if p and not str(p).startswith("Period_")]
            
            # FALLBACK 2: Scan historical_financials field values for period keys
            if not periods:
                historical = context_data.get("historical_financials", {})
                if isinstance(historical, dict):
                    for key, field in historical.items():
                        if key in ('data_fields', 'periods_covered'):
                            continue
                        if isinstance(field, dict) and isinstance(field.get("value"), list):
                            for pv in field["value"]:
                                if isinstance(pv, dict) and pv.get("period"):
                                    period_val = pv["period"]
                                    # Skip placeholder Period_X entries
                                    if not str(period_val).startswith("Period_") and period_val not in periods:
                                        periods.append(period_val)
                            if periods:
                                break
            
            if periods:
                # Sort periods descending (most recent first), take last 4
                periods_sorted = sorted([p for p in periods if p], reverse=True)[:4]
                periods_str = ", ".join([f'"{p}"' for p in periods_sorted])
                periods_info = f"\n\nCRITICAL: This company uses NON-Calendar fiscal years. You MUST use EXACTLY these fiscal year end dates: [{periods_str}]"
                periods_info += "\nDo NOT use calendar year dates (e.g., 2023-12-31). Use the fiscal year end dates listed above."
                periods_info += "\nThe 'year' field in your JSON should use the period string (e.g., '2025-05-31'), not just the year number."
                
                # Build example periods for the JSON
                example_periods_list = []
                for p in periods_sorted[:2]:
                    example_periods_list.append(f'{{"period": "{p}", {example_fields.replace("{", "").replace("}", "")}}}')
                example_periods = ",\n            ".join(example_periods_list)
        
        if not example_periods:
            example_periods = f'{{"year": 2023, {example_fields}}}'
        
        return f"""
You are a senior financial analyst providing historical financial data for {company_name} ({ticker}), listed on the {market} market.

Provide the following metrics for {company_name} ({ticker}):
{metric_list}
{periods_info}

IMPORTANT: Only return data for the metrics listed above. Do NOT include other financial metrics.

Rules:
- Use your training knowledge of {company_name}'s actual financial statements (10-K, 20-F filings)
- Provide actual numeric values — only use null if you genuinely have no knowledge of a specific metric for a specific year
- Use the EXACT fiscal year end dates specified above, NOT calendar year dates

Return the data strictly in this JSON format:
{{
    "company_name": "{company_name}",
    "ticker": "{ticker}",
    "currency": "USD or local currency",
    "fiscal_years": [
        {example_periods},
        ...
    ],
    "source_urls": [],
    "confidence_score": 0.85,
    "notes": "Notes about data quality, confidence level, and any caveats"
}}
"""

    def _build_validation_prompt(self, ticker: str, raw_data: str) -> str:
        """Build a prompt to validate and clean the extracted JSON."""
        return f"""
Validate and clean the following financial data extracted for {ticker}.
Ensure all numeric values are numbers (not strings), years are integers, and the structure is valid JSON.
Remove any markdown formatting (```json ... ```).
If there are obvious errors (e.g., negative revenue for a healthy company), flag them in 'notes'.

Raw Data:
{raw_data}

Return ONLY the cleaned JSON object.
"""

    async def extract_data(
        self,
        ticker: str,
        company_name: str,
        market: str,
        context_data: Optional[Dict] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform AI web search and extract historical financial data.

        Args:
            ticker: Stock ticker symbol
            company_name: Full company name
            market: 'International' or 'Vietnam'
            context_data: Optional existing data from Step 6 to guide extraction

        Returns:
            Dictionary containing extracted data, metadata, and status
        """
        # IMPORTANT: Check custom_prompt FIRST — user may want AI for fields not in the default list
        if custom_prompt and custom_prompt.strip():
            search_prompt = custom_prompt.strip()
            logger.info(f"Using custom prompt for {ticker}: {search_prompt[:100]}...")
        else:
            # Detect missing metrics from Step 6 data using the missing_data_summary
            # Step 6 provides critical_missing and optional_missing lists — use them directly
            missing_metrics = []
            if context_data:
                # PRIMARY: Use missing_data_summary from Step 6 (most reliable)
                missing_summary = context_data.get("missing_data_summary", {})
                if not missing_summary:
                    # Try nested in calculated_metrics
                    calc_metrics = context_data.get("calculated_metrics", {})
                    if isinstance(calc_metrics, dict):
                        missing_summary = calc_metrics.get("missing_data_summary", {})
                
                critical = missing_summary.get("critical_missing", [])
                optional = missing_summary.get("optional_missing", [])
                missing_metrics = critical + optional
                
                # FALLBACK: If no summary, scan historical_financials for MISSING status
                if not missing_metrics:
                    historical = context_data.get("historical_financials", {})
                    
                    def _is_missing(field):
                        if isinstance(field, dict):
                            return field.get('status') == 'MISSING' or field.get('is_missing') is True or field.get('value') is None
                        return field is None
                    
                    for key, field in historical.items():
                        if key in ('data_fields', 'periods_covered'):
                            continue
                        if isinstance(field, dict) and _is_missing(field):
                            display_name = key.replace('_', ' ').title()
                            if display_name not in missing_metrics:
                                missing_metrics.append(display_name)
                        elif field is None:
                            display_name = key.replace('_', ' ').title()
                            if display_name not in missing_metrics:
                                missing_metrics.append(display_name)
                    
                    # Also scan market_data and forecast_drivers
                    for section_key in ['market_data', 'forecast_drivers']:
                        section = context_data.get(section_key, {})
                        if isinstance(section, dict):
                            for key, field in section.items():
                                if key in ('data_fields', 'periods_covered'):
                                    continue
                                if (isinstance(field, dict) and _is_missing(field)) or field is None:
                                    display_name = key.replace('_', ' ').title()
                                    if display_name not in missing_metrics:
                                        missing_metrics.append(display_name)
            else:
                logger.info(f"No context data for {ticker} — cannot determine missing metrics")
                return {
                    "success": True,
                    "time_series": {},
                    "metadata": {
                        "provider": "none",
                        "message": "No context data available to determine missing metrics"
                    }
                }

            # If no metrics are missing, skip AI extraction
            if not missing_metrics:
                logger.info(f"No missing metrics for {ticker} — all data available from Step 6")
                return {
                    "success": True,
                    "time_series": {},
                    "metadata": {
                        "provider": "none",
                        "message": "All data already available from Step 6 API retrieval"
                    }
                }

            logger.info(f"AI extraction needed for {len(missing_metrics)} missing metrics: {missing_metrics}")
            search_prompt = self._build_search_prompt(ticker, company_name, market, missing_metrics, context_data)

        try:
            logger.info(f"Starting AI web search for {ticker} ({market}) using OpenRouter")

            # Use the existing fallback engine which tries Groq -> Gemini -> Qwen
            extraction_result = self.ai_engine.generate_analysis(
                prompt=search_prompt,
                model_preference=None  # Let the engine decide based on availability
            )

            if not extraction_result or "error" in extraction_result or not extraction_result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to extract data from AI providers",
                    "details": extraction_result.get("metadata", {}).get("errors", {}) if extraction_result else "No response",
                    "provider_used": None
                }

            # Step 2: Clean and Validate JSON
            # The AI might return markdown or extra text, so we clean it
            analysis_text = extraction_result.get("analysis") or ""
            cleaned_json_str = self._extract_json_from_response(analysis_text)

            if not cleaned_json_str:
                # Try to re-extract JSON from the raw response (no AI call needed)
                raw_text = extraction_result.get("analysis", "")
                cleaned_json_str = self._extract_json_from_response(raw_text)

            if not cleaned_json_str:
                return {
                    "success": False,
                    "error": "AI response could not be parsed as valid JSON",
                    "raw_response": extraction_result.get("analysis", "")[:500],
                    "provider_used": extraction_result.get("metadata", {}).get("provider")
                }

            # Parse the JSON
            try:
                extracted_data = json.loads(cleaned_json_str)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON format: {str(e)}",
                    "raw_response": cleaned_json_str[:500]
                }

            # Step 3: Validate and clean using the existing ai_engine (with api_keys)
            validated_data = await validate_and_clean_financial_data(
                raw_data=extracted_data,
                ticker=ticker,
                ai_engine=self.ai_engine
            )

            # Step 4: Format for Frontend
            formatted_data = self._format_for_frontend(validated_data, ticker, context_data)

            return {
                "success": True,
                "data": formatted_data["time_series"],
                "metadata": {
                    "extraction_method": "AI Web Search",
                    "provider_used": extraction_result.get("metadata", {}).get("provider"),
                    "confidence_score": validated_data.get("confidence_score", 0.8),
                    "sources": validated_data.get("source_urls", []),
                    "notes": validated_data.get("notes", ""),
                    "timestamp": formatted_data["timestamp"]
                },
                "message": f"Successfully extracted data using {extraction_result.get('metadata', {}).get('provider', 'AI')}"
            }

        except Exception as e:
            logger.error(f"Error in AI web search for {ticker}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "An unexpected error occurred during AI extraction"
            }

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extract JSON block from AI response string."""
        if not response:
            return None

        # Try to find JSON between ```json and ```
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try to find JSON between ``` and ```
        json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            content = json_match.group(1)
            # Check if it looks like JSON
            if content.strip().startswith('{'):
                return content

        # Try to find the first { and last }
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            return response[start:end+1]

        return None

    def _format_for_frontend(self, data: Dict, ticker: str, context_data: Optional[Dict]) -> Dict:
        """Format extracted data for frontend consumption and session storage.
        
        Dynamically includes ALL fields from the AI response, not just the 9 standard ones.
        This ensures additional missing fields (Cash & Equivalents, Accumulated Depreciation,
        PP&E Gross, R&D, Dividends Paid, Debt, etc.) are preserved.
        """
        from datetime import datetime

        # Mapping from snake_case AI response keys to human-readable display names
        FIELD_NAME_MAP = {
            "revenue": "Revenue",
            "net_income": "Net Income",
            "ebitda": "EBITDA",
            "operating_cash_flow": "Operating Cash Flow",
            "capital_expenditures": "CapEx",
            "capex": "CapEx",
            "total_assets": "Total Assets",
            "total_equity": "Total Equity",
            "shareholders_equity": "Total Equity",
            "working_capital": "Working Capital",
            "free_cash_flow": "Free Cash Flow",
            "cash_and_equivalents": "Cash & Equivalents",
            "cash_and_cash_equivalents": "Cash & Cash Equivalents",
            "accumulated_depreciation": "Accumulated Depreciation",
            "ppe_gross": "PP&E (Gross)",
            "net_debt_opening": "Net Debt",
            "research_and_development": "R&D",
            "other_income_expense": "Other Income/Expense",
            "interest_paid": "Interest Paid (Cash)",
            "income_tax_paid": "Income Tax Paid (Cash)",
            "dividends_paid": "Dividends Paid",
            "long_term_debt": "Long-Term Debt",
            "current_debt": "Current Debt",
            "interest_income": "Interest Income",
            "depreciation": "Depreciation",
            "interest_expense": "Interest Expense",
            "tax_provision": "Tax Provision",
        }

        time_series = {}
        fiscal_years = data.get("fiscal_years", [])

        for year_data in fiscal_years:
            # Support both old format {"year": 2023} and new format {"period": "2025-05-31"}
            period = year_data.get("period")
            year = year_data.get("year")
            if not period and not year:
                continue

            # Use period string if available (e.g., "2025-05-31"), otherwise construct from year
            if period:
                date_key = str(period)
            elif isinstance(year, (int, float)):
                date_key = f"{int(year)}-12-31"  # Legacy fallback for calendar year companies
            else:
                date_key = str(year)

            # Build metrics dict from ALL fields in the AI response (skip metadata fields)
            skip_keys = {"year", "period", "company_name", "ticker", "currency", "source_urls", "confidence_score", "notes"}
            metrics = {}
            for key, value in year_data.items():
                if key in skip_keys:
                    continue
                display_name = FIELD_NAME_MAP.get(key, key.replace('_', ' ').title())
                # Only include non-null values
                if value is not None:
                    try:
                        metrics[display_name] = float(value)
                    except (ValueError, TypeError):
                        pass  # Skip non-numeric values

            time_series[date_key] = metrics

        # Merge with context data if available (Step 6 data)
        if context_data:
            for date_key, metrics in context_data.get("historical_data", {}).items():
                if date_key not in time_series:
                    time_series[date_key] = metrics
                else:
                    # Fill gaps in AI data with Step 6 data
                    for metric, value in metrics.items():
                        if time_series[date_key].get(metric) is None and value is not None:
                            time_series[date_key][metric] = value

        return {
            "ticker": ticker,
            "time_series": time_series,
            "currency": data.get("currency", "USD"),
            "timestamp": datetime.now().isoformat()
        }

def calculate_historical_trends(historical_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates CAGR, Averages, and Volatility from historical data.
    Input: {"2023-12-31": {"Revenue": 100, ...}, "2022-12-31": {...}}
    Output: Analysis object with trends and averages for Step 8.
    """
    from datetime import datetime

    if not historical_data:
        return {}

    # Sort by date descending (newest first)
    sorted_dates = sorted(historical_data.keys(), reverse=True)
    if len(sorted_dates) < 2:
        return {"note": "Insufficient data for trend analysis (need >= 2 years)"}

    years_count = len(sorted_dates)

    # Helper to extract series (handles both capitalized and lowercase keys)
    def get_series(key: str) -> List[float]:
        values = []
        for date in sorted_dates:
            d = historical_data[date]
            # Try both capitalizations
            val = d.get(key) or d.get(key.lower())
            if val is not None and isinstance(val, (int, float)):
                values.append(val)
        return values

    # Helper to calculate CAGR
    def calc_cagr(values: List[float]) -> Optional[float]:
        if len(values) < 2:
            return None
        start_val = values[-1]  # Oldest
        end_val = values[0]     # Newest
        if start_val <= 0 or end_val <= 0:
            return None
        n = len(values) - 1
        return ((end_val / start_val) ** (1/n)) - 1

    # Helper to calculate Average and Volatility (Coefficient of Variation)
    def calc_stats(values: List[float]) -> Dict[str, Optional[float]]:
        if not values:
            return {"average": None, "volatility": None}
        avg = sum(values) / len(values)
        if len(values) < 2:
            return {"average": avg, "volatility": None}
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        # Coefficient of variation as volatility metric
        volatility = (std_dev / abs(avg)) if avg != 0 else 0
        return {"average": avg, "volatility": volatility}

    # Determine trend direction
    def get_trend(series: List[float]) -> str:
        if not series:
            return "flat"
        if series[0] > series[-1]:
            return "up"
        elif series[0] < series[-1]:
            return "down"
        return "flat"

    # Dynamically calculate trends for ALL available metrics
    # Collect all metric names across all years
    all_metric_names = set()
    for date in sorted_dates:
        all_metric_names.update(historical_data[date].keys())

    # Calculate CAGR, average, volatility, and trend for every numeric metric
    growth_rates = {}
    averages = {}
    volatility = {}
    trend_direction = {}

    for metric_name in sorted(all_metric_names):
        series = get_series(metric_name)
        if len(series) >= 2:
            growth_rates[f"{metric_name}_cagr"] = calc_cagr(series)
            stats = calc_stats(series)
            averages[f"{metric_name}_avg"] = stats["average"]
            volatility[f"{metric_name}_volatility"] = stats["volatility"]
            trend_direction[metric_name.lower().replace(" ", "_")] = get_trend(series)
        elif len(series) == 1:
            # Single value — no CAGR possible, but record average
            averages[f"{metric_name}_avg"] = series[0]

    # Calculate margins per year (if Revenue is available)
    net_margins = []
    ebitda_margins = []
    for date in sorted_dates:
        d = historical_data[date]
        rev = d.get("Revenue") or d.get("revenue")
        ni = d.get("Net Income") or d.get("net_income")
        ebit = d.get("EBITDA") or d.get("ebitda")
        if rev and rev > 0:
            if ni is not None:
                net_margins.append(ni / rev)
            if ebit is not None:
                ebitda_margins.append(ebit / rev)

    if net_margins:
        averages["net_margin_avg"] = sum(net_margins) / len(net_margins)
    if ebitda_margins:
        averages["ebitda_margin_avg"] = sum(ebitda_margins) / len(ebitda_margins)

    analysis = {
        "period": f"{sorted_dates[-1]} to {sorted_dates[0]}",
        "years_analyzed": years_count,
        "growth_rates": growth_rates,
        "averages": averages,
        "volatility": volatility,
        "trend_direction": trend_direction
    }

    return analysis