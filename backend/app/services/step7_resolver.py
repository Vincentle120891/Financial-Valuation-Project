"""
Step 7 Enhanced Resolver Service
Handles missing data retrieval with dynamic prompts and intelligent routing.
"""
import logging
from typing import List, Dict, Any, Optional

from app.core.metric_registry import METRIC_REGISTRY
# Lazy imports for optional dependencies
# from langchain_core.prompts import ChatPromptTemplate
# from app.services.llm_service import LLMService
# from app.services.pdf_extractor import PDFExtractor
# from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)

class Step7Resolver:
    def __init__(self):
        # Lazy initialization - will be imported when needed
        self._llm_service = None
        self._pdf_extractor = None
        self._web_search = None

    @property
    def llm_service(self):
        if self._llm_service is None:
            try:
                from app.services.llm_service import LLMService
                self._llm_service = LLMService()
            except ImportError:
                logger.warning("LLMService not available")
        return self._llm_service

    @property
    def pdf_extractor(self):
        if self._pdf_extractor is None:
            try:
                from app.services.pdf_extractor import PDFExtractor
                self._pdf_extractor = PDFExtractor()
            except ImportError:
                logger.warning("PDFExtractor not available")
        return self._pdf_extractor

    @property
    def web_search(self):
        if self._web_search is None:
            try:
                from app.services.web_search import WebSearchService
                self._web_search = WebSearchService()
            except ImportError:
                logger.warning("WebSearchService not available")
        return self._web_search

    async def resolve_missing_data(
        self,
        session_id: str,
        missing_metrics: List[str],
        company_ticker: str,
        method: str,
        source_type: str = "auto", # auto, pdf, web_search, ai_estimate
        pdf_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Intelligent router for missing data resolution.
        """
        results = {
            "resolved": [],
            "failed": [],
            "source_used": {},
            "logs": []
        }

        for metric_id in missing_metrics:
            metric_def = METRIC_REGISTRY.get_metric(metric_id, method)
            if not metric_def:
                results["failed"].append({"metric": metric_id, "reason": "Unknown metric"})
                continue

            try:
                resolved_value = None
                source = ""
                confidence = 0.0

                # 1. PDF Extraction (if provided or previously uploaded)
                if source_type in ["pdf", "auto"] and pdf_content:
                    resolved_value, confidence = await self._extract_from_pdf(
                        pdf_content, metric_def, company_ticker
                    )
                    if resolved_value is not None:
                        source = "pdf_upload"

                # 2. AI Web Search (if PDF failed or source is web_search)
                if resolved_value is None and source_type in ["web_search", "auto"]:
                    resolved_value, confidence = await self._search_web(
                        metric_def, company_ticker
                    )
                    if resolved_value is not None:
                        source = "ai_web_search"

                # 3. AI Estimation/Interpolation (Last resort)
                if resolved_value is None:
                    resolved_value, confidence = await self._estimate_with_ai(
                        metric_def, company_ticker, method
                    )
                    source = "ai_estimation"

                if resolved_value is not None:
                    results["resolved"].append({
                        "metric_id": metric_id,
                        "value": resolved_value,
                        "source": source,
                        "confidence": confidence,
                        "unit": metric_def.unit
                    })
                    results["source_used"][metric_id] = source
                    results["logs"].append(f"Resolved {metric_id} via {source} (conf: {confidence})")
                else:
                    results["failed"].append({
                        "metric": metric_id,
                        "reason": "All sources exhausted"
                    })

            except Exception as e:
                logger.error(f"Error resolving {metric_id}: {str(e)}")
                results["failed"].append({"metric": metric_id, "reason": str(e)})

        return results

    async def _extract_from_pdf(self, content: str, metric_def: Any, ticker: str) -> tuple:
        """Extract specific metric from PDF content using dynamic prompt."""
        prompt = f"""
        Extract the value for '{metric_def.description}' ({metric_id}) for {ticker}.
        Look for historical values in the text.
        Return ONLY the numeric value and the year.
        Format: {{ "value": number, "year": int, "confidence": float }}

        Context Keywords: {', '.join(metric_def.keywords)}
        """
        # Implementation calls LLM with PDF context
        # Mock response for structure
        return None, 0.0

    async def _search_web(self, metric_def: Any, ticker: str) -> tuple:
        """Search web for specific missing metric."""
        query = f"{ticker} {metric_def.description} historical value {metric_def.unit}"
        # Uses Tavily/SerpApi via WebSearchService
        # Parses results for numbers
        return None, 0.0

    async def _estimate_with_ai(self, metric_def: Any, ticker: str, method: str) -> tuple:
        """Estimate missing value based on industry averages or trends."""
        prompt = f"""
        The value for '{metric_def.description}' for {ticker} is missing.
        Based on general knowledge of the {method} valuation method and typical values for this sector,
        estimate a reasonable historical value.
        Explain the reasoning briefly.
        """
        # Calls LLM for estimation
        return None, 0.0

    def generate_dynamic_prompt(self, metric_def: Any, context: Dict) -> str:
        """Generates a specific prompt for the missing metric."""
        return f"""
        Task: Find historical data for {metric_def.name}.
        Target Company: {context.get('ticker')}
        Required Unit: {metric_def.unit}
        Valid Range: {metric_def.validation_rules.get('min', 'N/A')} to {metric_def.validation_rules.get('max', 'N/A')}
        Keywords to look for: {', '.join(metric_def.keywords)}

        Please search financial reports or news for this specific figure.
        """