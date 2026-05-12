"""
Valuation Routes - Refactored to use SessionService and International Services

Handles valuation workflow steps 4-10 using advanced service processors.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from typing import List, Dict, Any
from app.core.logging_config import get_logger
from app.core.session_service import session_service
from app.api.schemas import (
    ModelSelectRequest,
    ModelSelectResponse,
    PrepareInputsRequest,
    PrepareInputsResponse,
    FetchDataRequest,
    FetchDataResponse,
    GenerateAIRequest,
    GenerateAIResponse,
    GenerateAISuggestionRequest,
    AISuggestionCategoryResponse,
    ConfirmAssumptionsRequest,
    ConfirmAssumptionsResponse,
    ValuateRequest,
    ValuateResponse,
    MultiMethodValuateRequest,
    MultiMethodValuateResponse
)
from app.api.schemas.unified_step_schemas import (
    UnifiedStep4Request,
    UnifiedStep4Response,
    UnifiedStep5Request,
    UnifiedStep5Response,
    UnifiedStep6Response,
    UnifiedStep7Response,
    PeerCompany,
    AssumptionCategory,
    DataField,
    DataStatus,
    MissingDataSummary,
    MarketType,
    ValuationMethod
)
from app.services.international.step8_manual_overrides import FullAssumptionsResponse
from app.services.international.step5_assumptions_processor import Step5AssumptionsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.step6_unified_transformer import Step6UnifiedTransformer
from app.services.international.step7_historical_data_processor import Step7HistoricalDataProcessor
from app.services.international.step7_unified_transformer import Step7UnifiedTransformer
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step9_confirmation_processor import Step9ConfirmationProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor
from app.services.international.yfinance_service import YFinanceService
from app.services.international.valuation_orchestrator import orchestrator
from app.services.pdf_extraction_service import VietnamesePDFExtractor
from app.services.international.step7_ai_web_search import AIWebSearchExtractor, calculate_historical_trends
from app.api.schemas.unified_step_schemas import UnifiedStep6Response, UnifiedStep7Response

logger = get_logger(__name__)

router = APIRouter(tags=["Valuation"])

# Initialize processors
step5_processor = Step5AssumptionsProcessor()
step6_processor = Step6DataReviewProcessor()
step7_processor = Step7HistoricalDataProcessor()
step8_processor = Step8ManualOverridesProcessor()
step9_processor = Step9ConfirmationProcessor()
step10_processor = Step10ValuationProcessor()
yfinance_service = YFinanceService()


class SavePeersRequest(BaseModel):
    """Request to save selected peers to session"""
    session_id: str
    peers: List[Dict[str, Any]]


class SavePeersResponse(BaseModel):
    """Response after saving peers"""
    status: str
    message: str
    peers_saved: int


@router.post("/step-3-save-peers", response_model=SavePeersResponse)
async def save_peers(request: SavePeersRequest):
    """
    Step 3: Save selected peer companies to session.
    Stores peer tickers and triggers automatic peer data fetching from yfinance/AlphaVantage.
    """
    try:
        # Validate session exists
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Extract peer tickers from the peer objects
        peer_tickers = [peer.get('symbol') or peer.get('ticker') for peer in request.peers]
        peer_tickers = [t for t in peer_tickers if t]  # Filter out None values

        if not peer_tickers:
            raise HTTPException(status_code=400, detail="No valid peer tickers provided")

        # Save peer tickers to session
        session_service.update_session_data(request.session_id, "peer_tickers", peer_tickers)
        session_service.update_session_data(request.session_id, "selected_peers", request.peers)

        # Automatically fetch peer market data from yfinance
        logger.info(f"Fetching market data for {len(peer_tickers)} peers: {peer_tickers}")
        peer_data = {}
        for ticker in peer_tickers:
            try:
                # Fetch key stats for each peer (includes 5 WACC metrics + costOfDebt)
                peer_stats = yfinance_service.fetch_key_stats(ticker)

                # Store in format expected by step6: peer_{TICKER}_info
                # The 5 key WACC inputs per peer: Beta, Market Cap, Cost of Debt, Tax Rate, Risk-free Rate (global)
                peer_info = {
                    'marketCap': peer_stats.get('marketCap'),
                    'beta': peer_stats.get('beta'),
                    'totalDebt': peer_stats.get('totalDebt'),
                    'cash': peer_stats.get('cash'),
                    'effectiveTaxRate': peer_stats.get('effectiveTaxRate'),
                    'costOfDebt': peer_stats.get('costOfDebt'),  # NEW: Pre-tax cost of debt
                }
                peer_data[f"peer_{ticker}_info"] = peer_info
                logger.info(f"Fetched data for peer {ticker}: marketCap={peer_info['marketCap']}, beta={peer_info['beta']}, costOfDebt={peer_info['costOfDebt']}")
            except Exception as peer_err:
                logger.warning(f"Failed to fetch data for peer {ticker}: {peer_err}")
                peer_data[f"peer_{ticker}_info"] = {
                    'marketCap': None,
                    'beta': None,
                    'totalDebt': None,
                    'cash': None,
                    'effectiveTaxRate': None,
                    'costOfDebt': None,
                    'error': str(peer_err)
                }

        # Also store list of peers for easy access
        peer_data['peers'] = peer_tickers

        # Save all peer data to session
        session_service.update_session_data(request.session_id, "retrieved_assumptions", peer_data)

        return SavePeersResponse(
            status="success",
            message=f"Saved {len(peer_tickers)} peers and fetched market data",
            peers_saved=len(peer_tickers)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save peers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-4-select-peers", response_model=UnifiedStep4Response)
async def select_peers(request: UnifiedStep4Request):
    """
    Step 4: Select peer companies for comparable analysis.
    Uses SessionService for session management with unified schema support.

    MATRIX WORKFLOW:
    - Stores peer selection in valuations[market][method] track
    - Supports both suggested peers (auto-discovered) and custom peers
    - Each model's peer selection is stored independently

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session fallback
    - Each method operates independently with its own peer track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Use market/method from request ONLY (no fallback to session)
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()
        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

        ticker = session.get("ticker")
        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker selected in session")

        # Determine peers to use (custom or suggested)
        selected_peers = []
        if request.custom_peers:
            selected_peers = request.custom_peers
        elif request.suggested_peers:
            selected_peers = request.suggested_peers
        else:
            raise HTTPException(status_code=400, detail="Either custom_peers or suggested_peers must be provided")

        # Save peer tickers to session
        session_service.update_session_data(request.session_id, "peer_tickers", selected_peers)
        
        # Build peer company objects with available data
        peer_companies = []
        for peer_ticker in selected_peers:
            peer_info = {
                "ticker": peer_ticker,
                "company_name": peer_ticker,  # Will be enriched later
                "sector": session.get("sector", "Unknown"),
                "industry": session.get("industry", "Unknown"),
                "market_cap": None,
                "selected": True
            }
            peer_companies.append(peer_info)

        # Store detailed peer info for Step 6 retrieval
        session_service.update_session_data(request.session_id, "selected_peers", peer_companies)

        session_service.update_session_step(
            request.session_id,
            step_number=4,
            market=market,
            method=method.lower()
        )

        return UnifiedStep4Response(
            status="success",
            session_id=request.session_id,
            method=method,
            market=market,
            target_company=ticker,
            suggested_peers=[PeerCompany(**p) for p in peer_companies],
            selected_peers=selected_peers,
            message=f"Selected {len(selected_peers)} peer companies for {method} valuation"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Peer selection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-5-prepare-assumptions", response_model=UnifiedStep5Response)
async def prepare_assumptions(request: UnifiedStep5Request):
    """
    Step 5: Prepare assumptions for selected valuation model.
    Uses SessionService for session management and Step5AssumptionsProcessor.

    MATRIX WORKFLOW:
    - Retrieves model/method from request (REQUIRED - no fallback to session)
    - Prepares assumptions specific to the valuation track
    - Supports AI generation of initial assumptions

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own assumption track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Use market/method from request ONLY (no fallback to session)
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()
        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

        ticker = session.get("ticker")
        peer_tickers = session.get("peer_tickers", [])

        # Use Step5AssumptionsProcessor to get required inputs
        result = step5_processor.process_data_retrieval_inputs(
            ticker=ticker or "UNKNOWN",
            valuation_model=method,
            peer_tickers=peer_tickers
        )

        # Convert to unified AssumptionCategory format
        categories = []
        total_fields = 0
        missing_fields = []
        
        for group_name, fields in result.retrieval_groups.items():
            assumptions_dict = {}
            requires_input = False
            
            for field in fields:
                total_fields += 1
                assumptions_dict[field.field_name] = DataField(
                    value=None,
                    status=DataStatus.MISSING,
                    source=None,
                    description=field.description,
                    is_missing=True,
                    can_override=True
                )
                if field.is_required:
                    requires_input = True
                    missing_fields.append(f"{group_name}.{field.field_name}")
            
            categories.append(AssumptionCategory(
                category_name=group_name,
                assumptions=assumptions_dict,
                requires_user_input=requires_input,
                ai_generated=False
            ))

        # Build missing data summary
        missing_summary = MissingDataSummary(
            total_fields=total_fields,
            retrieved_count=0,
            calculated_count=0,
            estimated_count=0,
            missing_count=len(missing_fields),
            manual_override_count=0,
            completion_percentage=0.0,
            critical_missing=missing_fields[:10],  # Top 10 critical
            optional_missing=[],
            valuation_ready=False,
            data_quality_score=0.0,
            warnings=["No data retrieved yet. Proceed to Step 6 to fetch data."],
            recommendations=["Click 'Fetch Data' in Step 6 to retrieve required inputs"]
        )

        session_service.update_session_step(
            request.session_id,
            step_number=5,
            market=market,
            method=method.lower()
        )

        return UnifiedStep5Response(
            status="prepared",
            session_id=request.session_id,
            method=method,
            market=market,
            categories=categories,
            missing_data_summary=missing_summary,
            ai_provider=None,
            message=result.message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prepare assumptions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-6-fetch-api-data", response_model=UnifiedStep6Response)
async def fetch_api_data(request: FetchDataRequest):
    """
    Step 6: Fetch financial data from APIs and calculate metrics.
    Uses SessionService for session management and Step6DataReviewProcessor for comprehensive data review.

    PHASE 1.2 UNIFIED SCHEMA IMPLEMENTATION:
    - Returns UnifiedStep6Response instead of legacy FetchDataResponse
    - Transforms method-specific outputs (DCF/DuPont/Comps) to unified schema
    - Preserves ALL original calculations and data values
    - Only changes the wrapping structure to match unified contract

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Stores financial data in the specific valuation track
    - Each model's data is stored independently

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own data track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        # Use market from request ONLY (no fallback to session)
        market = request.market.lower() if request.market else "international"

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.upper()

        # Retrieve peer data and other assumptions from session (saved in Step 3)
        retrieved_assumptions = session_service.get_session_value(
            request.session_id,
            "retrieved_assumptions",
            {}
        )

        # GAP 1 FIX: Get session cache for "Fetch Once, Use Many" - pass entire session as cache
        session_cache = session_service.get_session_data(request.session_id)

        # Use Step6DataReviewProcessor for comprehensive data fetching and calculation
        legacy_result = await step6_processor.process_data_review(
            ticker=ticker,
            market=market,
            valuation_model=method,
            retrieved_assumptions=retrieved_assumptions,
            session_cache=session_cache  # PASS session cache to enable caching
        )

        # PHASE 1.2: Transform legacy response to unified schema
        unified_response = Step6UnifiedTransformer.transform_any_response(
            response=legacy_result,
            valuation_model=method
        )

        # Store results in session using SessionService (with JSON serialization)
        # Store in the specific valuation track
        result_dict = unified_response.model_dump(mode='json') if hasattr(unified_response, 'model_dump') else unified_response
        session_service.update_session_data(
            request.session_id,
            "financial_data",
            result_dict,
            market=market,
            method=method.lower()
        )

        session_service.update_session_step(
            request.session_id,
            step_number=6,
            market=market,
            method=method.lower()
        )

        return unified_response

    except Exception as e:
        logger.error(f"Fetch API data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-7-retrieve-historical-data", response_model=UnifiedStep7Response)
async def retrieve_historical_data(request: GenerateAIRequest):
    """
    Step 7: Retrieve Historical Data Using AI Extraction

    Uses AI to extract historical financial data that cannot be retrieved via standard APIs
    (yfinance/AlphaVantage). This is strictly for HISTORICAL data retrieval - NO forward-looking
    assumptions are generated here.

    Purpose:
    - Fill gaps in historical financial statements when APIs don't have complete data
    - Extract historical metrics from PDF reports, filings, or other sources using AI
    - Provide complete historical dataset for Step 8 assumption generation

    AI Usage: ZERO AI involvement in generating forward-looking inputs.
    AI is ONLY used as a data extraction tool for historical information.

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Stores historical data in the specific valuation track
    - Each model's historical data is stored independently

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own data track

    UNIFIED SCHEMA OUTPUT:
    - Returns UnifiedStep7Response with standardized ProcessedHistoricalPeriod structures
    - Includes trend analysis (CAGR, average growth rates)
    - Provides MissingDataSummary for data quality tracking
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        # Use market/method from request ONLY (no fallback)
        market = request.market.lower() if request.market else "international"

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.upper()

        # Get financial data from the specific valuation track
        financial_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            market=market,
            method=method.lower()
        )

        # Fallback to shared context if not found in track
        if not financial_data:
            financial_data = session_service.get_session_value(request.session_id, "financial_data")

        if not financial_data:
            raise HTTPException(status_code=400, detail="No financial data available")

        # Use Step7HistoricalDataProcessor for AI-powered historical data extraction
        legacy_result = await step7_processor.retrieve_historical_data(
            ticker=ticker,
            company_name=session.get("company_name", ticker),
            valuation_model=method,
            market=market,
            step6_financial_data=financial_data
        )

        # Transform to unified schema using Step7UnifiedTransformer
        unified_result = Step7UnifiedTransformer.transform_any_response(legacy_result, method)

        # Store historical data in session using SessionService - in the specific valuation track
        session_service.update_session_data(
            request.session_id,
            "historical_data_gaps_filled",
            unified_result,  # Store unified format
            market=market,
            method=method.lower()
        )

        session_service.update_session_step(
            request.session_id,
            step_number=7,
            market=market,
            method=method.lower()
        )

        logger.info(f"Step 7 complete: {unified_result.missing_data_summary.retrieved_count}/{unified_result.missing_data_summary.total_fields} gaps filled, completeness: {unified_result.missing_data_summary.completion_percentage:.1%}")

        return unified_result

    except Exception as e:
        logger.error(f"Step 7 historical data retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-7-upload-pdf")
async def upload_pdf_for_step7(
    session_id: str,
    method: str,
    market: str = "international",
    file: UploadFile = File(..., description="PDF financial report to extract data from")
):
    """
    Step 7: Upload PDF Financial Report for AI Extraction

    Allows users to upload PDF annual reports, financial statements, or filings
    for AI-powered historical data extraction. This fills gaps where API data
    from Step 6 is incomplete or missing.

    Supported documents:
    - Annual Reports (10-K, Annual Reports)
    - Financial Statements (10-Q, Quarterly Reports)
    - Prospectuses
    - Vietnamese annual reports (Báo cáo thường niên)

    Workflow:
    1. User uploads PDF in Step 7 frontend
    2. Backend extracts financial data using VietnamesePDFExtractor
    3. Extracted data is merged with Step 6 API data
    4. Updated historical data is stored in session for Step 8

    Args:
        session_id: Session identifier
        method: Valuation method (DCF, DUPONT, COMPS)
        market: Market type (international, vietnamese)
        file: PDF file upload

    Returns:
        Extraction results with extracted metrics and confidence scores
    """
    try:
        # Validate session
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Read and save file temporarily
        import tempfile
        import os

        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Extract data from PDF
            extractor = VietnamesePDFExtractor(extraction_method="auto")
            result = extractor.extract_from_file(tmp_path)

            # Convert to dict
            extracted_data = extractor.to_dict(result)

            # Get existing Step 6 data
            method_lower = method.lower()
            market_lower = market.lower()

            step6_data = session_service.get_session_value(
                session_id,
                "financial_data",
                market=market_lower,
                method=method_lower
            )

            if not step6_data:
                step6_data = session_service.get_session_value(session_id, "financial_data")

            # Merge extracted data with Step 6 data
            # Priority: PDF extraction > API data
            merged_historical = {}

            # Map extracted fields to Step 6 format
            if result.revenue:
                merged_historical['revenue'] = result.revenue
            if result.net_income:
                merged_historical['net_income'] = result.net_income
            if result.ebitda:
                merged_historical['ebitda'] = result.ebitda
            if result.total_assets:
                merged_historical['total_assets'] = result.total_assets
            if result.total_equity:
                merged_historical['total_equity'] = result.total_equity
            if result.operating_cash_flow:
                merged_historical['operating_cash_flow'] = result.operating_cash_flow
            if result.capex:
                merged_historical['capex'] = result.capex

            # Store extracted data in session
            extraction_metadata = {
                'source': f'PDF_{file.filename}',
                'fiscal_year': result.fiscal_year,
                'company_name': result.company_name,
                'extraction_method': result.extraction_method,
                'confidence_score': result.confidence_score,
                'upload_timestamp': datetime.now().isoformat(),
                'extracted_metrics': list(merged_historical.keys())
            }

            session_service.update_session_data(
                session_id,
                "pdf_extraction_results",
                {
                    **extracted_data,
                    'metadata': extraction_metadata
                },
                market=market_lower,
                method=method_lower
            )

            # Update historical data with extracted values
            if step6_data and 'historical_financials' in step6_data:
                # Merge into existing structure
                for key, value in merged_historical.items():
                    step6_data['historical_financials'][key] = value

            # Calculate historical trends and averages
            trend_analysis = calculate_historical_trends(step6_data.get('historical_financials', {}) if step6_data else merged_historical)

            session_service.update_session_data(
                session_id,
                "financial_data",
                step6_data,
                market=market_lower,
                method=method_lower
            )

            # Store trend analysis for Step 8
            session_service.update_session_data(
                session_id,
                "historical_trend_analysis",
                trend_analysis,
                market=market_lower,
                method=method_lower
            )

            logger.info(
                f"Successfully extracted {len(merged_historical)} metrics from {file.filename} "
                f"for {session.get('ticker', 'UNKNOWN')} ({method})"
            )

            return {
                "success": True,
                "message": f"Extracted {len(merged_historical)} financial metrics from PDF",
                "fiscal_year": result.fiscal_year,
                "company_name": result.company_name,
                "extraction_method": result.extraction_method,
                "confidence_score": result.confidence_score,
                "extracted_metrics": merged_historical,
                "trend_analysis": trend_analysis,
                "notes": result.notes
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload and extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/step-7-ai-web-search")
async def ai_web_search_for_step7(
    session_id: str,
    ticker: str,
    company_name: str,
    method: str,
    market: str = "international"
):
    """
    Step 7: AI Web Search for Historical Data

    Uses Groq, Gemini, and Qwen AI providers to search the internet and extract
    historical financial data. This is an alternative to PDF upload when users
    don't have access to official financial reports.

    Workflow:
    1. User clicks "Search with AI" in Step 7 frontend
    2. Backend uses AIFallbackEngine to query AI providers (Groq → Gemini → Qwen)
    3. AI searches web for financial data from reliable sources
    4. Extracted data is validated, formatted, and merged with Step 6 data
    5. Results stored in session for Step 8

    Args:
        session_id: Session identifier
        ticker: Stock ticker symbol (e.g., AAPL, VNM)
        company_name: Full company name
        method: Valuation method (DCF, DUPONT, COMPS)
        market: Market type (international, vietnamese)

    Returns:
        Extraction results with time series data, metadata, and source URLs
    """
    try:
        # Validate session
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get existing Step 6 data for merging
        method_lower = method.lower()
        market_lower = market.lower()

        step6_data = session_service.get_session_value(
            session_id,
            "financial_data",
            market=market_lower,
            method=method_lower
        )

        if not step6_data:
            step6_data = session_service.get_session_value(session_id, "financial_data")

        # Initialize AI Web Search Extractor
        extractor = AIWebSearchExtractor()

        # Perform AI web search and extraction
        result = await extractor.extract_data(
            ticker=ticker,
            company_name=company_name,
            market=market,
            context_data=step6_data
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "AI web search failed")
            )

        # Store results in session
        extraction_metadata = {
            'source': 'AI Web Search',
            'provider_used': result['metadata']['provider_used'],
            'confidence_score': result['metadata']['confidence_score'],
            'sources': result['metadata'].get('sources', []),
            'notes': result['metadata'].get('notes', ''),
            'search_timestamp': datetime.now().isoformat(),
            'extracted_metrics': list(result['data'].keys()) if result['data'] else []
        }

        session_service.update_session_data(
            session_id,
            "ai_web_search_results",
            {
                'time_series': result['data'],
                'metadata': extraction_metadata
            },
            market=market_lower,
            method=method_lower
        )

        # Update historical data with AI-extracted values
        if step6_data:
            if 'historical_financials' not in step6_data:
                step6_data['historical_financials'] = {}

            # Merge AI data into existing structure
            for date_key, metrics in result['data'].items():
                if date_key not in step6_data['historical_financials']:
                    step6_data['historical_financials'][date_key] = metrics
                else:
                    # Fill gaps in existing data with AI data
                    for metric, value in metrics.items():
                        if step6_data['historical_financials'][date_key].get(metric) is None and value is not None:
                            step6_data['historical_financials'][date_key][metric] = value

        # Calculate historical trends and averages
        trend_analysis = calculate_historical_trends(step6_data.get('historical_financials', {}) if step6_data else result['data'])

        session_service.update_session_data(
            session_id,
            "financial_data",
            step6_data,
            market=market_lower,
            method=method_lower
        )

        # Store trend analysis for Step 8
        session_service.update_session_data(
            session_id,
            "historical_trend_analysis",
            trend_analysis,
            market=market_lower,
            method=method_lower
        )

        logger.info(
            f"Successfully extracted data via AI web search for {ticker} ({company_name}) "
            f"using {result['metadata']['provider_used']}"
        )

        return {
            "success": True,
            "message": f"Successfully extracted data using {result['metadata']['provider_used']}",
            "provider_used": result['metadata']['provider_used'],
            "confidence_score": result['metadata']['confidence_score'],
            "sources": result['metadata'].get('sources', []),
            "time_series": result['data'],
            "trend_analysis": trend_analysis,
            "notes": result['metadata'].get('notes', '')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI web search error for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI web search failed: {str(e)}")


@router.post("/step-8-initialize", response_model=FullAssumptionsResponse)
async def initialize_step8_assumptions(request: GenerateAISuggestionRequest):
    """
    Step 8: Initialize assumptions with historical trendlines from Step 6.

    This endpoint loads historical data and prepares the assumption categories
    with trendlines. No AI suggestions are generated yet - user must click
    buttons to generate them per category.

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Initializes assumptions for the specific valuation track

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own data track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        # Use market/method from request ONLY (no fallback)
        market = request.market.lower() if hasattr(request, 'market') and request.market else "international"

        # Validate method is provided
        if not hasattr(request, 'method') or not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.upper()

        # Get data from the specific valuation track
        step6_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            {},
            market=market,
            method=method.lower()
        )
        step7_data = session_service.get_session_value(
            request.session_id,
            "historical_data_gaps_filled",
            {},
            market=market,
            method=method.lower()
        )

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Use Step8ManualOverridesProcessor to initialize assumptions with historical trendlines
        result = await step8_processor.initialize_assumptions(
            ticker=ticker,
            valuation_model=method,
            step6_data=step6_data,
            step7_data=step7_data if step7_data else None
        )

        # Store initial assumptions in the specific valuation track
        session_service.update_session_data(
            request.session_id,
            "step8_assumptions",
            result.model_dump() if hasattr(result, 'model_dump') else result.dict(),
            market=market,
            method=method.lower()
        )

        return result
    except Exception as e:
        logger.error(f"Step 8 initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-8-generate-ai-suggestion", response_model=AISuggestionCategoryResponse)
async def generate_ai_suggestion(request: GenerateAISuggestionRequest):
    """
    Step 8: Generate AI suggestions for a specific assumption category.

    This endpoint is called when the user clicks an "AI Suggest" button for a specific category.
    It generates AI-powered suggestions based on historical trends and market data.

    Categories:
    - DCF: REVENUE_DRIVERS, COST_MARGINS, WORKING_CAPITAL, WACC_COMPONENTS, TERMINAL_VALUE
    - DuPont: DUPONT_TARGETS
    - Comps: COMPS_MULTIPLES

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Generates AI suggestions for the specific valuation track

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own data track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        # Use market/method from request ONLY (no fallback)
        market = request.market.lower() if hasattr(request, 'market') and request.market else "international"

        # Validate method is provided
        if not hasattr(request, 'method') or not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.upper()

        # Get data from the specific valuation track
        step6_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            {},
            market=market,
            method=method.lower()
        )
        step7_data = session_service.get_session_value(
            request.session_id,
            "historical_data_gaps_filled",
            {},
            market=market,
            method=method.lower()
        )

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Use Step8ManualOverridesProcessor to generate AI suggestions for the category
        result = await step8_processor.generate_ai_suggestions_for_category(
            ticker=ticker,
            valuation_model=method,
            category=request.category,
            step6_data=step6_data,
            step7_data=step7_data if step7_data else None
        )

        # Store AI suggestions in the specific valuation track
        current_suggestions = session_service.get_session_value(
            request.session_id,
            "ai_suggestions",
            {},
            market=market,
            method=method.lower()
        )
        current_suggestions[request.category] = result.model_dump() if hasattr(result, 'model_dump') else result
        session_service.update_session_data(
            request.session_id,
            "ai_suggestions",
            current_suggestions,
            market=market,
            method=method.lower()
        )

        # Convert result to dict for response
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict() if hasattr(result, 'dict') else dict(result)

        return AISuggestionCategoryResponse(
            status="success",
            category=result_dict.get('category', request.category),
            category_name=result_dict.get('category_name', request.category),
            assumptions=result_dict.get('assumptions', []),
            ai_generated=True,
            message=result_dict.get('message', 'AI suggestions generated successfully')
        )
    except Exception as e:
        logger.error(f"Generate AI suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-9-confirm-assumptions", response_model=ConfirmAssumptionsResponse)
async def confirm_assumptions(request: ConfirmAssumptionsRequest):
    """
    Step 9: Confirmation Processing - Consolidates Steps 6-8 inputs for Step 10.
    
    Uses Step9ConfirmationProcessor to:
    1. Receive all inputs from Step 6 (historical financials), Step 7 (gap-filled data), 
       and Step 8 (manual overrides + AI suggestions)
    2. Process and validate all confirmed parameters
    3. Build model-specific inputs exclusively for Step 10
    4. Store output that Step 10 will use (Step 10 cannot access earlier steps directly)

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Confirms assumptions for the specific valuation track
    - Ensures Step 8 manual overrides are included in final inputs

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own data track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        # Use market/method from request ONLY (no fallback)
        market = request.market.lower() if request.market else "international"

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.upper()

        # Get data from the specific valuation track
        # Step 6: Aggregated historical financials and market data
        step6_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            {},
            market=market,
            method=method.lower()
        )
        # Step 7: Gap-filled historical data
        step7_data = session_service.get_session_value(
            request.session_id,
            "historical_data_gaps_filled",
            {},
            market=market,
            method=method.lower()
        )
        # Step 8: Final inputs including manual overrides and AI suggestions
        step8_final_inputs = session_service.get_session_value(
            request.session_id,
            "confirmed_assumptions",
            {},
            market=market,
            method=method.lower()
        )

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        if not step8_final_inputs:
            raise HTTPException(
                status_code=400, 
                detail="No Step 8 confirmed assumptions found. Please complete Step 8 first."
            )

        # Use Step9ConfirmationProcessor to consolidate all inputs
        step9_output = await step9_processor.process_confirmation(
            session_id=request.session_id,
            ticker=ticker,
            valuation_model=method,
            step6_data=step6_data,
            step7_data=step7_data if step7_data else None,
            step8_final_inputs=step8_final_inputs,
            market=market
        )

        # Validate Step 9 output
        if not step9_output.ready_for_valuation:
            error_msg = f"Step 9 validation failed: {', '.join(step9_output.errors)}"
            raise HTTPException(status_code=400, detail=error_msg)

        # Store Step 9 output in session - this is what Step 10 will use
        session_service.update_session_data(
            request.session_id,
            "step9_confirmed_outputs",
            step9_output.model_dump() if hasattr(step9_output, 'model_dump') else step9_output.dict(),
            market=market,
            method=method.lower()
        )

        session_service.update_session_step(
            request.session_id,
            step_number=9,
            market=market,
            method=method.lower()
        )

        # Log confirmation summary
        logger.info(
            f"Step 9 confirmation completed for {ticker} ({method}): "
            f"{step9_output.total_parameters_confirmed} parameters confirmed, "
            f"{step9_output.parameters_manually_overridden} manually overridden, "
            f"ready for Step 10: {step9_output.ready_for_valuation}"
        )

        return ConfirmAssumptionsResponse(
            status="assumptions_confirmed",
            message=f"Assumptions confirmed successfully. {len(step9_output.warnings)} warnings." if step9_output.warnings else "Assumptions confirmed successfully."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step 9 confirmation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-10-valuate", response_model=ValuateResponse)
async def valuate(request: ValuateRequest):
    """
    Step 10: Final Valuation - Uses ONLY Step 9 outputs.
    
    CRITICAL WORKFLOW CONSTRAINT:
    - Step 10 CANNOT access Step 6, 7, or 8 data directly
    - Step 10 receives inputs EXCLUSIVELY from Step 9 confirmed outputs
    - This ensures strict workflow order and proper confirmation/override processing
    
    Uses SessionService for session management and Step10ValuationProcessor for comprehensive multi-model valuation.

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Runs valuation for the specific track
    - Stores results in the specific valuation track
    - Does NOT overwrite other models' results

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own data track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        # Use market/method from request ONLY (no fallback)
        market = request.market.lower() if request.market else "international"

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.upper()

        # CRITICAL: Get Step 9 confirmed outputs (Step 10 can ONLY use this)
        # Step 10 cannot access step6_data, step7_data, or step8_final_inputs directly
        step9_confirmed_outputs = session_service.get_session_value(
            request.session_id,
            "step9_confirmed_outputs",
            None,
            market=market,
            method=method.lower()
        )

        if not step9_confirmed_outputs:
            raise HTTPException(
                status_code=400, 
                detail="No Step 9 confirmed outputs available. Please complete Step 9 confirmation first."
            )

        # Extract model-specific inputs from Step 9 output
        # This is the ONLY data source Step 10 can use
        model_specific_inputs = step9_confirmed_outputs.get('model_specific_inputs', {})
        historical_summary = step9_confirmed_outputs.get('historical_financials_summary', {})
        market_context = step9_confirmed_outputs.get('market_context', {})
        
        # Build consolidated assumptions dict for Step 10 processor
        # Combining Step 9 outputs into format expected by Step 10 engines
        confirmed_assumptions = {
            'model_specific_inputs': model_specific_inputs,
            'historical_financials_summary': historical_summary,
            'market_context': market_context,
            'confirmed_parameters': step9_confirmed_outputs.get('confirmed_parameters', []),
            'validation_status': step9_confirmed_outputs.get('validation_status', 'passed'),
            'warnings': step9_confirmed_outputs.get('warnings', [])
        }

        # Use Step10ValuationProcessor for comprehensive valuation
        # Pass only Step 9 derived data - no direct access to earlier steps
        result = await step10_processor.run_valuation(
            ticker=ticker,
            model=method,
            assumptions=confirmed_assumptions
        )

        # Store valuation result in the specific valuation track (async-safe)
        await session_service.save_valuation_results(
            session_id=request.session_id,
            market=market,
            method=method.lower(),
            results=result
        )

        logger.info(
            f"Step 10 valuation completed for {ticker} ({method}): "
            f"Used Step 9 outputs only, validation status: {step9_confirmed_outputs.get('validation_status')}"
        )

        return ValuateResponse(
            status="success",
            valuation_results=[result],
            message=f"Valuation completed successfully for {method} ({market}) using Step 9 confirmed inputs"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step 10 valuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-10-valuate-multi", response_model=MultiMethodValuateResponse)
async def valuate_multi_method(request: MultiMethodValuateRequest):
    """
    Step 10 (Multi-Method): Run valuation for multiple methods simultaneously.

    This endpoint uses the ValuationOrchestrator to execute DCF, DuPont, and/or COMPS
    valuations in parallel using asyncio.gather, then returns a unified response.

    SUPPORTS:
    - Multiple methods: ["dcf", "dupont", "comps"]
    - Both markets: "international" or "vietnam"
    - Parallel execution with comprehensive error handling
    - Unified response with cross-method comparison

    USAGE EXAMPLE:
    ```json
    {
        "session_id": "xxx",
        "methods": ["dcf", "dupont", "comps"],
        "market": "international"
    }
    ```
    """
    try:
        # Validate session exists
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Validate at least one method provided
        if not request.methods or len(request.methods) == 0:
            raise HTTPException(status_code=400, detail="At least one valuation method must be specified")

        # Normalize market
        market = request.market.lower() if request.market else "international"
        if market not in ["international", "vietnam"]:
            raise HTTPException(status_code=400, detail="Market must be 'international' or 'vietnam'")

        # Use orchestrator to run all methods in parallel
        logger.info(f"Starting multi-method valuation: methods={request.methods}, market={market}")

        result = await orchestrator.execute_multi_method_valuation(
            session_id=request.session_id,
            methods=request.methods,
            market=market,
            start_step=4  # Start from model selection
        )

        # Check for errors
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Multi-method valuation failed"))

        return MultiMethodValuateResponse(
            status=result.get("status", "success"),
            market=result.get("market", market),
            methods_requested=result.get("methods_requested", []),
            methods_completed=result.get("methods_completed", []),
            methods_failed=result.get("methods_failed", []),
            summary=result.get("summary", {}),
            results=result.get("results", []),
            message=f"Multi-method valuation completed: {len(result.get('methods_completed', []))}/{len(request.methods)} methods successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-method valuation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))