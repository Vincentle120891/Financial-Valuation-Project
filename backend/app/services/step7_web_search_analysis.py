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

Extract the following metrics for the last 4 available fiscal years (most recent first):
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
        ... (up to 4 years)
    ],
    "source_urls": ["url1", "url2", ...],
    "confidence_score": <0.0 to 1.0>,
    "notes": "<data quality notes, source discrepancies, accounting standards>"
}}

If exact values are not found for a specific year, omit that year or use null values.
Prioritize the most recent 4 fiscal years."""

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
    Deterministic Python validation — no AI call needed.
    
    Args:
        raw_data: Raw extracted data dict
        ticker: Stock ticker
        ai_engine: Optional AIFallbackEngine instance (unused, kept for API compat)
    
    Returns:
        Cleaned and validated data dict
    """
    import re
    
    logger.info(f"🧹 Validating and cleaning financial data for {ticker} (deterministic)")
    
    validation_notes = []
    cleaned = dict(raw_data)  # shallow copy
    
    # 1. Clean fiscal_years
    fiscal_years = cleaned.get("fiscal_years", [])
    if not isinstance(fiscal_years, list):
        validation_notes.append("fiscal_years was not a list, coerced to empty list")
        fiscal_years = []
    
    # Fields that should NOT be coerced to numeric
    NON_NUMERIC_FIELDS = {"year", "period", "date", "fiscal_year", "quarter", "currency", "unit", "source", "notes"}
    
    cleaned_years = []
    for year_data in fiscal_years:
        if not isinstance(year_data, dict):
            continue
        
        entry = {}
        for key, value in year_data.items():
            if key.lower() in NON_NUMERIC_FIELDS:
                # Keep as-is (string metadata)
                entry[key] = value
                continue
            if key == "year":
                # Ensure year is integer
                try:
                    entry["year"] = int(float(str(value).strip()))
                except (ValueError, TypeError):
                    validation_notes.append(f"Invalid year value: {value}, skipped entry")
                    entry = None
                    break
            elif value is None:
                entry[key] = None
            else:
                # Coerce numeric values: strip strings, handle "N/A", etc.
                str_val = str(value).strip()
                # Remove common non-numeric prefixes/suffixes
                str_val = re.sub(r'[,$%\s]', '', str_val)
                str_val = str_val.replace('−', '-').replace('–', '-')  # unicode minus
                
                if str_val in ('', 'N/A', 'n/a', 'NA', '-', '--', 'null', 'None'):
                    entry[key] = None
                else:
                    try:
                        entry[key] = float(str_val)
                    except (ValueError, TypeError):
                        validation_notes.append(f"Invalid numeric value for {key} in {year_data.get('year')}: {value}")
                        entry[key] = None
        
        if entry is not None:
            cleaned_years.append(entry)
    
    # 2. Sort fiscal years descending (most recent first)
    cleaned_years.sort(key=lambda y: y.get("year", 0), reverse=True)
    
    # 3. Basic sanity checks
    for yd in cleaned_years:
        year = yd.get("year")
        revenue = yd.get("revenue")
        if revenue is not None and revenue < 0:
            validation_notes.append(f"Negative revenue in {year}: {revenue}")
        net_income = yd.get("net_income")
        if net_income is not None and revenue is not None and revenue > 0:
            margin = net_income / revenue
            if abs(margin) > 2.0:
                validation_notes.append(f"Unusual net margin in {year}: {margin:.1%}")
    
    cleaned["fiscal_years"] = cleaned_years
    
    # 4. Ensure source_urls is a list
    if not isinstance(cleaned.get("source_urls"), list):
        cleaned["source_urls"] = []
    
    # 5. Ensure confidence_score is a float
    try:
        cleaned["confidence_score"] = float(cleaned.get("confidence_score", 0.7))
    except (ValueError, TypeError):
        cleaned["confidence_score"] = 0.7
    
    # 6. Merge validation notes
    if validation_notes:
        existing = cleaned.get("notes", "")
        cleaned["notes"] = f"{existing}\nValidation: {'; '.join(validation_notes)}".strip()
        logger.warning(f"⚠️ Validation issues for {ticker}: {'; '.join(validation_notes)}")
    
    logger.info(f"✅ Validated and cleaned {len(cleaned_years)} fiscal years for {ticker}")
    return cleaned
