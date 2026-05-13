"""
Step 7 AI Service - Web Search Analysis
Analyzes web search results to extract historical financial data.
"""

import logging
from typing import Optional, Dict, Any, List
from app.services.international.ai_engine import AIFallbackEngine

logger = logging.getLogger(__name__)


async def analyze_web_search_results(
    search_query: str,
    search_results: List[Dict[str, Any]],
    company_name: str,
    ticker: str,
    market: str,
    ai_engine: Optional[AIFallbackEngine] = None
) -> Dict[str, Any]:
    """
    Analyze web search results to extract historical financial data.
    
    Args:
        search_query: Original search query
        search_results: List of search result dicts with url, title, snippet
        company_name: Company name
        ticker: Stock ticker
        market: Market name (e.g., "US", "International")
        ai_engine: Optional AIFallbackEngine instance
    
    Returns:
        Dict with keys: success, analysis, extracted_data, source_urls, confidence, notes
    """
    engine = ai_engine or AIFallbackEngine()
    
    # Format search results for the prompt
    formatted_results = "\n\n".join([
        f"Result {i+1}:\nTitle: {r.get('title', 'N/A')}\nURL: {r.get('url', 'N/A')}\nSnippet: {r.get('snippet', 'N/A')}"
        for i, r in enumerate(search_results[:10])  # Limit to top 10 results
    ])
    
    prompt = f"""You are a financial data analyst. Analyze these web search results to extract historical financial data for {company_name} ({ticker}), listed in the {market} market.

SEARCH RESULTS:
{formatted_results}

Extract the following metrics for the last 5 available fiscal years (most recent first):
- Revenue
- Net Income
- EBITDA
- Operating Cash Flow
- Capital Expenditures (CapEx)
- Total Assets
- Total Equity
- Working Capital
- Free Cash Flow (if available)

CRITICAL RULES:
1. Only use data from reliable sources (Yahoo Finance, Bloomberg, Reuters, Official IR sites, SEC filings)
2. Do NOT invent numbers - if data is missing, use null
3. Note the currency (USD or local currency)
4. Flag any inconsistencies between different sources
5. Provide confidence scores based on source reliability and data consistency

Return ONLY a JSON object with this structure:
{{
    "company_name": "{company_name}",
    "ticker": "{ticker}",
    "currency": "USD or detected currency",
    "fiscal_years": [
        {{
            "year": 2023,
            "revenue": <number or null>,
            "net_income": <number or null>,
            "ebitda": <number or null>,
            "operating_cash_flow": <number or null>,
            "capex": <number or null>,
            "total_assets": <number or null>,
            "total_equity": <number or null>,
            "working_capital": <number or null>,
            "free_cash_flow": <number or null>
        }},
        ... (up to 5 years)
    ],
    "source_urls": ["url1", "url2", ...],
    "confidence_score": <0.0 to 1.0>,
    "notes": "<data quality notes, source discrepancies, accounting standards>"
}}

If exact values are not found for a specific year, omit that year or use null values.
Prioritize the most recent 5 fiscal years."""

    logger.info(f"🔍 Analyzing web search results for {ticker} ({len(search_results)} results)")
    
    result = await engine.execute_with_fallback(
        prompt=prompt,
        task_name=f"web_search_analysis_{ticker}",
        provider_order=["groq", "gemini", "qwen"]
    )
    
    if not result["success"]:
        logger.error(f"❌ Failed to analyze web search for {ticker}: {result.get('error', 'Unknown error')}")
        return {
            "success": False,
            "analysis": None,
            "extracted_data": None,
            "source_urls": [],
            "confidence": 0.0,
            "notes": f"AI analysis failed: {result.get('error', 'All providers failed')}"
        }
    
    # Parse the response
    try:
        import json
        # Remove markdown code blocks if present
        response_text = result["response"].strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text.strip("`")
        
        parsed = json.loads(response_text)
        
        # Validate structure
        fiscal_years = parsed.get("fiscal_years", [])
        if not isinstance(fiscal_years, list) or len(fiscal_years) == 0:
            logger.warning(f"⚠️ No fiscal years extracted for {ticker}")
            fiscal_years = []
        
        # Ensure all numeric values are actually numbers
        for year_data in fiscal_years:
            for key, value in year_data.items():
                if key != "year" and value is not None:
                    try:
                        year_data[key] = float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ Invalid numeric value for {key} in {year_data.get('year')}: {value}")
                        year_data[key] = None
        
        confidence = float(parsed.get("confidence_score", 0.5))
        source_urls = parsed.get("source_urls", [])
        notes = str(parsed.get("notes", ""))
        
        # Determine success based on whether we got any data
        success = len(fiscal_years) > 0 and confidence > 0.3
        
        logger.info(
            f"{'✅' if success else '⚠️'} Analyzed {len(fiscal_years)} fiscal years for {ticker} "
            f"(confidence: {confidence}, provider: {result['metadata']['provider']})"
        )
        
        return {
            "success": success,
            "analysis": result["response"],
            "extracted_data": {
                "company_name": parsed.get("company_name", company_name),
                "ticker": parsed.get("ticker", ticker),
                "currency": parsed.get("currency", "USD"),
                "fiscal_years": fiscal_years
            },
            "source_urls": source_urls if isinstance(source_urls, list) else [],
            "confidence": confidence,
            "notes": notes,
            "provider": result["metadata"]["provider"]
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON from web search analysis: {e}")
        return {
            "success": False,
            "analysis": result["response"],
            "extracted_data": None,
            "source_urls": [],
            "confidence": 0.0,
            "notes": f"JSON parsing failed: {str(e)}",
            "provider": result["metadata"]["provider"]
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error in web search analysis: {e}")
        return {
            "success": False,
            "analysis": result["response"] if result else None,
            "extracted_data": None,
            "source_urls": [],
            "confidence": 0.0,
            "notes": f"Unexpected error: {str(e)}",
            "provider": result["metadata"]["provider"] if result else None
        }


async def validate_and_clean_financial_data(
    raw_data: Dict[str, Any],
    ticker: str,
    ai_engine: Optional[AIFallbackEngine] = None
) -> Dict[str, Any]:
    """
    Validate and clean financial data extracted from web search.
    
    Args:
        raw_data: Raw extracted data dict
        ticker: Stock ticker
        ai_engine: Optional AIFallbackEngine instance
    
    Returns:
        Cleaned and validated data dict
    """
    engine = ai_engine or AIFallbackEngine()
    
    import json
    raw_json = json.dumps(raw_data, indent=2)
    
    prompt = f"""Validate and clean the following financial data extracted for {ticker}.

RAW DATA:
{raw_json}

TASKS:
1. Ensure all numeric values are numbers (not strings)
2. Ensure years are integers
3. Remove any markdown formatting
4. Flag obvious errors (e.g., negative revenue for a healthy company, unrealistic growth rates)
5. Ensure consistent currency across all years
6. Sort fiscal years in descending order (most recent first)

Return ONLY the cleaned JSON object with the same structure as the input.
If you find errors, add them to a new 'validation_notes' field."""

    logger.info(f"🧹 Validating and cleaning financial data for {ticker}")
    
    result = await engine.execute_with_fallback(
        prompt=prompt,
        task_name=f"validate_data_{ticker}",
        provider_order=["groq", "gemini", "qwen"]
    )
    
    if not result["success"]:
        logger.warning(f"⚠️ Validation failed for {ticker}, returning raw data")
        return {
            **raw_data,
            "validation_notes": f"Validation failed: {result.get('error', 'Unknown error')}"
        }
    
    try:
        # Remove markdown code blocks if present
        response_text = result["response"].strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text.strip("`")
        
        cleaned_data = json.loads(response_text)
        
        # Merge validation notes
        validation_notes = cleaned_data.pop("validation_notes", "")
        if validation_notes:
            existing_notes = raw_data.get("notes", "")
            cleaned_data["notes"] = f"{existing_notes}\nValidation: {validation_notes}".strip()
        
        logger.info(f"✅ Successfully validated and cleaned data for {ticker}")
        return cleaned_data
        
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON parsing failed during validation, returning raw data: {e}")
        return {
            **raw_data,
            "validation_notes": f"JSON parsing failed: {str(e)}"
        }
    except Exception as e:
        logger.warning(f"⚠️ Unexpected error during validation, returning raw data: {e}")
        return {
            **raw_data,
            "validation_notes": f"Validation error: {str(e)}"
        }
