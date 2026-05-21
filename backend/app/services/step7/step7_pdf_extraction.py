../
"""
Step 7 AI Service - PDF/Filing Text Extraction
Extracts specific financial metrics from document text using AI with fallback chain.
"""

import logging
from typing import Optional, Dict, Any
from app.services.international.ai_engine import AIFallbackEngine

logger = logging.getLogger(__name__)


async def extract_financial_metric_from_text(
    text: str,
    metric: str,
    fiscal_year: int,
    company_name: str,
    ai_engine: Optional[AIFallbackEngine] = None
) -> Dict[str, Any]:
    """
    Extract a specific financial metric from PDF/filing text.
    
    Args:
        text: Raw text extracted from PDF/filing
        metric: Metric name (e.g., "Revenue", "EBITDA", "CapEx")
        fiscal_year: Target fiscal year
        company_name: Company name for context
        ai_engine: Optional AIFallbackEngine instance
    
    Returns:
        Dict with keys: success, value, confidence, excerpt, notes, provider
    """
    engine = ai_engine or AIFallbackEngine()
    
    prompt = f"""You are a financial data extraction specialist. Extract the {metric} for fiscal year {fiscal_year} from the following text for {company_name}.

CRITICAL RULES:
1. Only extract values explicitly labeled as fiscal year {fiscal_year} or FY{fiscal_year} or year ending in {fiscal_year}
2. Do NOT estimate, interpolate, or use values from other years
3. Handle units carefully: convert 'millions', 'billions', 'thousands' to actual numbers
4. Distinguish between similar metrics (e.g., Operating Income vs EBITDA)
5. Watch for negative values (losses) and preserve the sign
6. If the exact metric is not found, return null - do not hallucinate

TEXT TO ANALYZE:
{text[:8000]}  # Truncate to avoid token limits

Return ONLY a JSON object with this structure:
{{
    "value": <number or null>,
    "confidence": <0.0 to 1.0>,
    "excerpt": "<exact quote from text showing the value>",
    "notes": "<any warnings about data quality, unit conversions, or ambiguities>"
}}

If you cannot find the metric with high confidence, set value to null and explain in notes."""

    logger.info(f"📄 Extracting {metric} for {fiscal_year} from text ({len(text)} chars)")
    
    result = await engine.execute_with_fallback(
        prompt=prompt,
        task_name=f"extract_{metric}_{fiscal_year}",
        provider_order=["groq", "gemini", "qwen"]
    )
    
    if not result["success"]:
        logger.error(f"❌ Failed to extract {metric} for {fiscal_year}: {result.get('error', 'Unknown error')}")
        return {
            "success": False,
            "value": None,
            "confidence": 0.0,
            "excerpt": "",
            "notes": f"AI extraction failed: {result.get('error', 'All providers failed')}",
            "provider": None
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
        
        extracted_value = parsed.get("value")
        confidence = float(parsed.get("confidence", 0.5))
        excerpt = str(parsed.get("excerpt", ""))
        notes = str(parsed.get("notes", ""))
        
        # Validate value is numeric if present
        if extracted_value is not None:
            try:
                extracted_value = float(extracted_value)
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Extracted value for {metric} is not numeric: {extracted_value}")
                extracted_value = None
                confidence = 0.0
        
        success = extracted_value is not None and confidence > 0.3
        
        logger.info(
            f"{'✅' if success else '⚠️'} Extracted {metric}={extracted_value} "
            f"(confidence: {confidence}, provider: {result['metadata']['provider']})"
        )
        
        return {
            "success": success,
            "value": extracted_value,
            "confidence": confidence,
            "excerpt": excerpt,
            "notes": notes,
            "provider": result["metadata"]["provider"]
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON response for {metric}: {e}")
        return {
            "success": False,
            "value": None,
            "confidence": 0.0,
            "excerpt": "",
            "notes": f"JSON parsing failed: {str(e)}",
            "provider": result["metadata"]["provider"]
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error extracting {metric}: {e}")
        return {
            "success": False,
            "value": None,
            "confidence": 0.0,
            "excerpt": "",
            "notes": f"Unexpected error: {str(e)}",
            "provider": result["metadata"]["provider"]
        }
