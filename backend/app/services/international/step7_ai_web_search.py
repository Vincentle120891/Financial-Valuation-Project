"""
AI Web Search Service for Step 7 Historical Data Retrieval
Uses Groq, Gemini, and Qwen via AIFallbackEngine to search and extract financial data.
"""
import json
import re
from typing import Dict, Any, Optional, List
from app.services.international.ai_engine import AIFallbackEngine
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class AIWebSearchExtractor:
    """
    Extracts historical financial data using AI web search capabilities.
    Supports Groq, Gemini, and Qwen providers with automatic fallback.
    """

    def __init__(self):
        self.ai_engine = AIFallbackEngine()

    def _build_search_prompt(self, ticker: str, company_name: str, market: str, metrics: List[str]) -> str:
        """Build a structured prompt for AI web search."""
        metric_list = ", ".join(metrics)
        return f"""
You are a financial data analyst. Search the internet for the latest historical financial data for {company_name} ({ticker}), listed in the {market} market.

Extract the following metrics for the last 5 available fiscal years:
{metric_list}

Return the data strictly in this JSON format:
{{
    "company_name": "{company_name}",
    "ticker": "{ticker}",
    "currency": "USD or local currency",
    "fiscal_years": [
        {{
            "year": 2023,
            "revenue": 1000000,
            "net_income": 500000,
            ...
        }},
        ...
    ],
    "source_urls": ["url1", "url2"],
    "confidence_score": 0.95,
    "notes": "Any relevant notes about data quality or accounting standards"
}}

If exact values are not found, provide estimates based on reliable sources (Yahoo Finance, Bloomberg, Reuters, Official IR sites) and mark confidence appropriately.
Do not invent numbers. If data is missing for a specific year, omit that year or use null.
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
        context_data: Optional[Dict] = None
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
        # Define key metrics to extract based on valuation needs
        metrics = [
            "Revenue",
            "Net Income",
            "EBITDA",
            "Operating Cash Flow",
            "Capital Expenditures (CapEx)",
            "Total Assets",
            "Total Equity",
            "Working Capital",
            "Free Cash Flow"
        ]

        try:
            logger.info(f"Starting AI web search for {ticker} ({market}) using Groq/Gemini/Qwen")

            # Step 1: Search and Extract
            search_prompt = self._build_search_prompt(ticker, company_name, market, metrics)

            # Use the existing fallback engine which tries Groq -> Gemini -> Qwen
            extraction_result = await self.ai_engine.generate_analysis(
                prompt=search_prompt,
                model_preference=None  # Let the engine decide based on availability
            )

            if not extraction_result or "error" in extraction_result:
                return {
                    "success": False,
                    "error": "Failed to extract data from AI providers",
                    "details": extraction_result.get("error", "Unknown error"),
                    "provider_used": None
                }

            # Step 2: Clean and Validate JSON
            # The AI might return markdown or extra text, so we clean it
            cleaned_json_str = self._extract_json_from_response(extraction_result.get("analysis", ""))

            if not cleaned_json_str:
                # Try validation prompt if direct extraction failed
                validation_prompt = self._build_validation_prompt(ticker, extraction_result.get("analysis", ""))
                validation_result = await self.ai_engine.generate_analysis(prompt=validation_prompt)
                cleaned_json_str = self._extract_json_from_response(validation_result.get("analysis", ""))

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

            # Step 3: Format for Frontend
            formatted_data = self._format_for_frontend(extracted_data, ticker, context_data)

            return {
                "success": True,
                "data": formatted_data["time_series"],
                "metadata": {
                    "extraction_method": "AI Web Search",
                    "provider_used": extraction_result.get("metadata", {}).get("provider"),
                    "confidence_score": extracted_data.get("confidence_score", 0.8),
                    "sources": extracted_data.get("source_urls", []),
                    "notes": extracted_data.get("notes", ""),
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
        """Format extracted data for frontend consumption and session storage."""
        from datetime import datetime

        time_series = {}
        fiscal_years = data.get("fiscal_years", [])

        for year_data in fiscal_years:
            year = year_data.get("year")
            if not year:
                continue

            date_key = f"{year}-12-31" # Simplified assumption for fiscal year end

            time_series[date_key] = {
                "Revenue": year_data.get("revenue"),
                "Net Income": year_data.get("net_income"),
                "EBITDA": year_data.get("ebitda"),
                "Operating Cash Flow": year_data.get("operating_cash_flow"),
                "CapEx": year_data.get("capital_expenditures") or year_data.get("capex"),
                "Total Assets": year_data.get("total_assets"),
                "Total Equity": year_data.get("total_equity"),
                "Working Capital": year_data.get("working_capital"),
                "Free Cash Flow": year_data.get("free_cash_flow")
            }

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

    # Extract key metric series
    revenue_series = get_series("Revenue")
    net_income_series = get_series("Net Income")
    ebitda_series = get_series("EBITDA")

    # Calculate margins per year then average
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

    # Determine trend direction
    def get_trend(series: List[float]) -> str:
        if not series:
            return "flat"
        if series[0] > series[-1]:
            return "up"
        elif series[0] < series[-1]:
            return "down"
        return "flat"

    analysis = {
        "period": f"{sorted_dates[-1]} to {sorted_dates[0]}",
        "years_analyzed": years_count,
        "growth_rates": {
            "revenue_cagr": calc_cagr(revenue_series),
            "net_income_cagr": calc_cagr(net_income_series),
            "ebitda_cagr": calc_cagr(ebitda_series)
        },
        "averages": {
            "revenue_avg": calc_stats(revenue_series)["average"],
            "net_income_avg": calc_stats(net_income_series)["average"],
            "ebitda_avg": calc_stats(ebitda_series)["average"],
            "net_margin_avg": sum(net_margins)/len(net_margins) if net_margins else None,
            "ebitda_margin_avg": sum(ebitda_margins)/len(ebitda_margins) if ebitda_margins else None
        },
        "volatility": {
            "revenue_volatility": calc_stats(revenue_series)["volatility"],
            "net_income_volatility": calc_stats(net_income_series)["volatility"],
            "ebitda_volatility": calc_stats(ebitda_series)["volatility"]
        },
        "trend_direction": {
            "revenue": get_trend(revenue_series),
            "net_income": get_trend(net_income_series),
            "ebitda": get_trend(ebitda_series)
        }
    }

    return analysis