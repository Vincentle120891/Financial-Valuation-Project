"""
Valuation Routes - Refactored to use SessionService and International Services

Handles valuation workflow steps 4-10 using advanced service processors.
Routes are thin - only receiving requests, validating inputs, and delegating to service files.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel, Field
from app.core.logging_config import get_logger
from app.core.session_service import session_service
from app.api.schemas import (
    UnifiedStep4Request,
    UnifiedStep4Response,
    UnifiedStep5Request,
    UnifiedStep5Response,
    UnifiedStep6Request,
    UnifiedStep6Response,
    UnifiedStep7Request,
    UnifiedStep7Response,
    UnifiedStep8InitializeRequest,
    UnifiedStep8GenerateAISuggestionRequest,
    UnifiedStep8ApplyOverrideRequest,
    UnifiedStep8Response,
    UnifiedStep9Request,
    UnifiedStep9Response,
    UnifiedStep10Request,
    UnifiedStep10Response,
    PeerCompany,
    AssumptionCategory,
    DataField,
    DataStatus,
    MissingDataSummary,
    MarketType,
    ValuationMethod,
    AssumptionCategoryType,
    AssumptionCategoryResponse,
    AISuggestionCategoryResponse,
    UnifiedStep10Response as MultiMethodValuateResponse,
    UnifiedStep10Request as MultiMethodValuateRequest,
)

from app.utils.api_key_resolver import check_api_keys_status, get_api_key

# Import Step 4 method-specific discovery services
from app.services.international.step4_dcf_discovery import process as dcf_discover_peers
from app.services.international.step4_dupont_discovery import process as dupont_discover_peers
from app.services.international.step4_comps_discovery import process as comps_discover_peers
from app.services.international.step8_manual_overrides import FullAssumptionsResponse
from app.services.international.step5_required_inputs_processor import Step5RequiredInputsProcessor
from app.services.international.step3_selected_models_processor import Step3SelectedModelsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.step6_unified_transformer import Step6UnifiedTransformer
from app.services.international.step7_historical_data_processor import Step7HistoricalDataProcessor
from app.services.international.step7_unified_transformer import Step7UnifiedTransformer
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step9_confirmation_processor import Step9ConfirmationProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor
from app.services.international.yfinance_service import YFinanceService
from app.services.international.valuation_orchestrator import orchestrator
from app.services.international.institutional_peer_discovery import InstitutionalPeerDiscoveryService, PeerDiscoveryRequest
from app.services.international.step4_peer_management_service import Step4PeerManagementService
from app.services.international.step7_data_enrichment_service import Step7DataEnrichmentService
from app.services.international.sec_edgar_service import get_sec_edgar_service
from app.services.api_adapter import APIAdapter, process_multiple_tickers
from app.middleware.validation_middleware import create_validation_middleware
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter(tags=["Valuation"])

# Initialize processors and services
step3_processor = Step3SelectedModelsProcessor(market="international")
step4_service = Step4PeerManagementService()
step5_processor = Step5RequiredInputsProcessor()
step6_processor = Step6DataReviewProcessor()
step7_processor = Step7HistoricalDataProcessor()
step7_enrichment_service = Step7DataEnrichmentService()
step8_processor = Step8ManualOverridesProcessor()
step9_processor = Step9ConfirmationProcessor()
step10_processor = Step10ValuationProcessor()
yfinance_service = YFinanceService()
peer_discovery_service = InstitutionalPeerDiscoveryService()


class SavePeersRequest(BaseModel):
    """Request to save selected peers to session"""
    session_id: str
    peers: List[Dict[str, Any]]


class SavePeersResponse(BaseModel):
    """Response after saving peers"""
    status: str
    message: str
    peers_saved: int
    peer_data: Optional[Dict[str, Any]] = None


@router.post("/step-4-save-peers", response_model=SavePeersResponse)
async def save_peers(request: SavePeersRequest):
    """
    Step 4: Save selected peer companies to session.
    Delegates to Step4PeerManagementService for all business logic.
    """
    try:
        # Delegate to service layer
        result = step4_service.save_peers_and_fetch_data(
            session_id=request.session_id,
            peers=request.peers
        )

        return SavePeersResponse(
            status=result["status"],
            message=result["message"],
            peers_saved=result["peers_saved"],
            peer_data=result.get("peer_data")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save peers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STEP 4: PEER DISCOVERY
# =============================================================================


@router.post("/step-4-discover-peers", response_model=UnifiedStep4Response)
async def discover_peers_endpoint(request: UnifiedStep4Request, req: Request):
    """
    Step 4: Discover peer companies automatically.
    Routes to method-specific discovery service based on valuation method.

    - DCF: Discovers peers based on sector/industry/market cap
    - DuPont: Returns empty/minimal peers (optional for this method)
    - Comps: Enforces strict sector/industry peer discovery (mandatory)
    """
    try:
        # Validate session exists
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get method from request (already validated by Pydantic)
        valuation_method = request.method.value

        # Route to appropriate discovery service based on method
        # All discovery functions are now async, so we need to await them
        if valuation_method == "dcf":
            discovery_result = await dcf_discover_peers(
                session_id=request.session_id,
                ticker=session.get("ticker", ""),
                market=request.market.value,
                max_peers=request.max_peers or 10,
                request=req
            )
        elif valuation_method == "dupont":
            discovery_result = await dupont_discover_peers(
                session_id=request.session_id,
                ticker=session.get("ticker", ""),
                market=request.market.value,
                max_peers=request.max_peers or 10,
                request=req
            )
        elif valuation_method == "comps":
            discovery_result = await comps_discover_peers(
                session_id=request.session_id,
                ticker=session.get("ticker", ""),
                market=request.market.value,
                max_peers=request.max_peers or 10,
                request=req
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid valuation method: {valuation_method}. Must be 'dcf', 'dupont', or 'comps'"
            )

        # Return unified response with peer discovery results
        return UnifiedStep4Response(
            status="success",
            session_id=request.session_id,
            method=valuation_method,
            market=request.market.value,
            target_company=session.get("ticker", ""),
            suggested_peers=[PeerCompany(**peer) for peer in discovery_result.get("suggested_peers", [])],
            selected_peers=[],
            message=discovery_result.get("message", "Peer discovery completed")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Peer discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-3-select-models", response_model=UnifiedStep4Response)
async def select_models(request: UnifiedStep4Request):
    """
    Step 3: Select valuation model (DCF, DuPont, or Trading Comps).
    Delegates to Step3SelectedModelsProcessor for model validation.
    Uses SessionService for session management with unified schema support.

    MATRIX WORKFLOW:
    - Stores model selection in valuations[market][method] track
    - Supports both suggested peers (auto-discovered via PeerDiscoveryService) and custom peers
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

        # Determine peers to use (custom or suggested/discovered)
        # NOTE: Peers are OPTIONAL in Step 3 - they will be discovered in Step 4
        selected_peers = []
        if request.custom_peers:
            selected_peers = request.custom_peers
        elif request.suggested_peers:
            selected_peers = request.suggested_peers
        # else: No peers provided yet - this is OK for Step 3, peers will be discovered in Step 4

        # Delegate to Step3SelectedModelsProcessor for model validation
        model_result = step3_processor.process_model_selection([method])

        if not model_result['is_valid']:
            raise HTTPException(status_code=400, detail=f"Invalid model selected: {model_result['invalid_models']}")

        # Save peer tickers to session (may be empty if peers not yet discovered)
        if selected_peers:
            session_service.update_session_data(request.session_id, "peer_tickers", selected_peers)

        # Build peer company objects with available data (only if peers were provided)
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

        # Store detailed peer info for Step 6 retrieval (only if peers exist)
        if peer_companies:
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
            suggested_peers=[PeerCompany(**p) for p in peer_companies] if peer_companies else [],
            selected_peers=selected_peers,
            message=f"Selected {method} valuation model. Proceed to Step 4 to discover peers." if not selected_peers else f"Selected {method} valuation model with {len(selected_peers)} peer companies"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model selection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-5-prepare-assumptions", response_model=UnifiedStep5Response)
async def prepare_assumptions(request: UnifiedStep5Request):
    """
    Step 5: Show required inputs for selected valuation model.
    Uses SessionService for session management and Step5RequiredInputsProcessor.

    MATRIX WORKFLOW:
    - Retrieves model/method from request (REQUIRED - no fallback to session)
    - Shows required inputs specific to the valuation track
    - No AI generation, no calculations - just listing requirements

    METHOD-AGNOSTIC DESIGN:
    - Method MUST be provided in request.method - no session.selected_model fallback
    - Each method operates independently with its own input requirements
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

        # Use Step5RequiredInputsProcessor to get required inputs
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
async def fetch_api_data(request: UnifiedStep6Request):
    """
    Step 6: Fetch financial data from APIs and calculate metrics.
    Uses SessionService for session management, APIAdapter for data fetching,
    and ValidationMiddleware for data quality checks.

    ENHANCED WITH NEW ARCHITECTURE:
    - APIAdapter: Handles fetching, mapping, normalizing, and validating data
    - MetricRegistry: Centralized field mappings and validation rules
    - ValidationMiddleware: Pre-save validation with outlier detection

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Stores financial data in the specific valuation track
    - Each model's data is stored independently
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        peer_tickers = session.get("peer_tickers", [])
        # Use market from request ONLY (no fallback to session)
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

        # Create validation middleware for this method
        validator = create_validation_middleware(method)

        # Use new APIAdapter for robust data fetching and processing
        all_tickers = [ticker] + peer_tickers if peer_tickers else [ticker]

        logger.info(f"Processing {len(all_tickers)} tickers using APIAdapter")

        # Process all tickers through the adapter pipeline
        adapter_result = process_multiple_tickers(all_tickers, method)

        # Extract company data and peer data
        company_data = adapter_result["individual_results"].get(ticker, {})
        peer_averages = adapter_result.get("peer_averages", {})
        individual_results = adapter_result["individual_results"]

        # Validate the fetched data before saving
        validation_report = validator.validate_complete_dataset({
            "data": company_data.get("data", {}),
            "peer_data": {k: v.get("data", {}) for k, v in individual_results.items() if k != ticker}
        })

        logger.info(f"Validation report for {ticker}: {validation_report['status']}, completeness: {validation_report['completeness_score']:.2f}")

        # Build structured data with status tracking
        structured_data = {}
        missing_inputs = []

        for metric_id, metric_info in company_data.get("data", {}).items():
            structured_data[metric_id] = metric_info

        for metric_id in company_data.get("missing", []):
            missing_inputs.append({
                "metric_id": metric_id,
                "company": ticker,
                "required_for_method": method
            })

        # Add peer averages
        for metric_id, avg_info in peer_averages.items():
            if metric_id not in structured_data:
                structured_data[metric_id] = avg_info

        # CALL THE ACTUAL STEP 6 PROCESSOR instead of creating a fake object
        # The processor will wrap the adapter results in proper DataField objects
        logger.info(f"Calling Step6DataReviewProcessor for {ticker} ({method})")
        
        legacy_result = await step6_processor.process_data_review(
            ticker=ticker,
            market=market,
            historical_data={'data': company_data.get("data", {}), 'periods': []},
            market_data=company_data.get("data", {}),
            forecast_data={},
            retrieved_assumptions={'peer_data': individual_results, 'peer_averages': peer_averages},
            user_overrides={},
            valuation_model=method,
            session_cache={
                'session_id': request.session_id,
                'international_market_data': {
                    'timestamp': datetime.now(),
                    'historical_data': {'data': company_data.get("data", {}), 'periods': []},
                    'market_data': company_data.get("data", {}),
                    'forecast_data': {},
                    'retrieved_assumptions': {'peer_data': individual_results, 'peer_averages': peer_averages}
                }
            }
        )

        unified_response = Step6UnifiedTransformer.transform_any_response(
            response=legacy_result,
            valuation_model=method
        )

        # Store results in session using SessionService
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
async def retrieve_historical_data(request: UnifiedStep7Request):
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
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

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
    2. Backend extracts financial data using Step7DataEnrichmentService
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
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Read file content
        content = await file.read()

        # Delegate to service layer
        result = step7_enrichment_service.extract_from_pdf(
            session_id=session_id,
            file_content=content,
            filename=file.filename,
            method=method,
            market=market
        )

        return result

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
        # Delegate to service layer
        result = await step7_enrichment_service.extract_from_web_search(
            session_id=session_id,
            ticker=ticker,
            company_name=company_name,
            method=method,
            market=market
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI web search error for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI web search failed: {str(e)}")


@router.post("/step-7-fetch-sec-edgar")
async def fetch_sec_edgar_for_step7(
    session_id: str,
    ticker: str,
    company_name: str,
    email: str,
    method: str,
    market: str = "international"
):
    """
    Step 7: Fetch SEC EDGAR Filings for Historical Data

    Fetches 10-K and 10-Q filings directly from SEC EDGAR database.
    Requires email address for rate limit compliance (SEC requirement).

    Workflow:
    1. User clicks "Fetch SEC Filings" in Step 7 frontend (US companies only)
    2. Backend queries SEC EDGAR API to get recent 10-K/10-Q filings
    3. Filing metadata is extracted and stored in session
    4. Optionally, AI can be used to extract data from filing content
    5. Results merged with Step 6 data for Step 8

    Args:
        session_id: Session identifier
        ticker: Stock ticker symbol (e.g., AAPL, MSFT) - US companies only
        company_name: Full company name for User-Agent header
        email: Contact email for SEC rate limit compliance
        method: Valuation method (DCF, DUPONT, COMPS)
        market: Market type (international, vietnamese)

    Returns:
        SEC filing metadata including accession numbers, filing dates, and document URLs
    """
    try:
        # Get SEC EDGAR service
        sec_service = get_sec_edgar_service()
        
        # Search for company filings
        result = await sec_service.search_company_filings(
            ticker=ticker.upper(),
            email=email,
            company_name=company_name or ticker,
            limit=10
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", f"No SEC filings found for {ticker}")
            )
        
        # Store SEC filings data in session for potential AI extraction
        session_data = session_service.get_session_data(session_id)
        if session_data:
            session_data["sec_edgar_filings"] = result
            session_service.save_session(session_id, session_data)
        
        # Log successful fetch
        logger.info(
            f"Successfully fetched {result['filings_count']} SEC filings for {ticker}",
            extra={
                "session_id": session_id,
                "cik": result.get("cik"),
                "filings_count": result["filings_count"]
            }
        )
        
        return {
            "success": True,
            "message": f"Found {result['filings_count']} SEC filings for {ticker}",
            "filings": result["filings"],
            "filings_count": result["filings_count"],
            "cik": result.get("cik"),
            "company_name": result.get("company_name"),
            "source": "SEC EDGAR"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SEC EDGAR fetch error for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SEC EDGAR fetch failed: {str(e)}")


@router.post("/step-8-initialize", response_model=UnifiedStep8Response)
async def initialize_step8_assumptions(request: UnifiedStep8InitializeRequest):
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
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # Validate method is provided
        if not hasattr(request, 'method') or not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

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
async def generate_ai_suggestion(request: UnifiedStep8GenerateAISuggestionRequest):
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
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # Validate method is provided
        if not hasattr(request, 'method') or not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

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


@router.post("/step-9-confirm-assumptions", response_model=UnifiedStep9Response)
async def confirm_assumptions(request: UnifiedStep9Request):
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
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

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

        return UnifiedStep9Response(
            status="assumptions_confirmed",
            session_id=request.session_id,
            method=method,
            market=market,
            all_categories_confirmed=True,
            confirmed_assumptions=step9_output.confirmed_inputs if hasattr(step9_output, 'confirmed_inputs') else {},
            ready_for_valuation=step9_output.ready_for_valuation,
            validation_errors=step9_output.errors if hasattr(step9_output, 'errors') else [],
            message=f"Assumptions confirmed successfully. {len(step9_output.warnings)} warnings." if step9_output.warnings else "Assumptions confirmed successfully."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step 9 confirmation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-10-valuate", response_model=UnifiedStep10Response)
async def valuate(request: UnifiedStep10Request):
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
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # Validate method is provided
        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

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

        return UnifiedStep10Response(
            status="success",
            session_id=request.session_id,
            method=method,
            market=market,
            ticker=ticker,
            company_name=session.get("company_name", ticker),
            valuation_summary=result.valuation_summary if hasattr(result, 'valuation_summary') else {},
            detailed_outputs=result.detailed_outputs if hasattr(result, 'detailed_outputs') else result.dict() if hasattr(result, 'dict') else {},
            sensitivity_analysis=result.sensitivity_analysis if hasattr(result, 'sensitivity_analysis') else None,
            scenario_analysis=result.scenario_analysis if hasattr(result, 'scenario_analysis') else None,
            confidence_level=result.confidence_level if hasattr(result, 'confidence_level') else "medium",
            key_assumptions_summary=result.key_assumptions_summary if hasattr(result, 'key_assumptions_summary') else {},
            warnings=result.warnings if hasattr(result, 'warnings') else [],
            calculation_timestamp=datetime.now(),
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


# ============================================================================
# API KEY MANAGEMENT ENDPOINTS (Step 6)
# ============================================================================

class SaveApiKeysRequest(BaseModel):
    """Request to save API keys to session
    
    Uses standardized service names matching api_key_resolver.py config.
    Frontend should send keys using these exact field names.
    """
    session_id: str
    fmp: Optional[str] = Field(None, description="Financial Modeling Prep API key")
    alpha_vantage: Optional[str] = Field(None, description="Alpha Vantage API key")
    fred: Optional[str] = Field(None, description="FRED API key")
    sec_edgar: Optional[str] = Field(None, description="SEC EDGAR email/identifier")
    openrouter: Optional[str] = Field(None, description="OpenRouter AI API key")
    groq: Optional[str] = Field(None, description="Groq AI API key")
    gemini: Optional[str] = Field(None, description="Google Gemini API key")
    qwen: Optional[str] = Field(None, description="Qwen/DashScope AI API key")


class SaveApiKeysResponse(BaseModel):
    """Response after saving API keys"""
    status: str
    message: str
    keys_configured: Dict[str, bool]


@router.post("/save-api-keys", response_model=SaveApiKeysResponse)
async def save_api_keys(request: SaveApiKeysRequest):
    """
    Step 6: Save API keys to session for AI tools.
    
    Stores API keys securely in the session for use in Step 7+ AI operations.
    Keys are encrypted and stored per-session.
    
    Required Keys:
    - openrouter: Primary AI provider for Step 7-8
    - alpha_vantage: Financial data API (optional if using yfinance)
    - groq, gemini, qwen: Alternative AI providers
    - fmp, fred, sec_edgar: Financial data APIs
    
    Args:
        request: SaveApiKeysRequest with session_id and API keys
        
    Returns:
        SaveApiKeysResponse with status and configured keys
    """
    try:
        # Validate session exists
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Build keys dictionary from request using standardized service names
        api_keys = {}
        if request.fmp:
            api_keys["fmp"] = request.fmp
        if request.alpha_vantage:
            api_keys["alpha_vantage"] = request.alpha_vantage
        if request.fred:
            api_keys["fred"] = request.fred
        if request.sec_edgar:
            api_keys["sec_edgar"] = request.sec_edgar
        if request.openrouter:
            api_keys["openrouter"] = request.openrouter
        if request.groq:
            api_keys["groq"] = request.groq
        if request.gemini:
            api_keys["gemini"] = request.gemini
        if request.qwen:
            api_keys["qwen"] = request.qwen
        
        # Store keys in session under dedicated 'api_keys' section
        session_service.update_session_data(
            request.session_id,
            "api_keys",
            api_keys
        )
        
        # Return status of all keys using standardized service names
        keys_configured = {
            "fmp": request.fmp is not None,
            "alpha_vantage": request.alpha_vantage is not None,
            "fred": request.fred is not None,
            "sec_edgar": request.sec_edgar is not None,
            "openrouter": request.openrouter is not None,
            "groq": request.groq is not None,
            "gemini": request.gemini is not None,
            "qwen": request.qwen is not None,
        }
        
        return SaveApiKeysResponse(
            status="success",
            message=f"Saved {len(api_keys)} API key(s) to session",
            keys_configured=keys_configured
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save API keys error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-api-keys")
async def check_api_keys(request: Request, session_id: str):
    """
    Step 6: Check which API keys are configured for a session.
    
    Returns the status of all API keys stored in the session.
    Used by frontend to show configuration status and enable/disable buttons.
    
    Uses centralized API key resolver with fallback chain:
    1. Request headers (highest priority)
    2. Session storage
    3. Environment variables
    
    Args:
        request: FastAPI request object (for header extraction)
        session_id: Session identifier
        
    Returns:
        Dictionary with key status (true/false for each provider)
    """
    try:
        # Validate session exists
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Use centralized API key resolver with fallback chain
        keys_status = check_api_keys_status(request=request, session_id=session_id)
        
        # Add overall status - openrouter is required for AI features
        keys_status["all_required_configured"] = keys_status.get("openrouter", False)
        # Count only boolean values (service statuses), not metadata fields
        keys_status["total_configured"] = sum(
            1 for k, v in keys_status.items() 
            if isinstance(v, bool) and k not in ["all_required_configured", "total_configured"]
        )
        
        return keys_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check API keys error: {e}")
        raise HTTPException(status_code=500, detail=str(e))