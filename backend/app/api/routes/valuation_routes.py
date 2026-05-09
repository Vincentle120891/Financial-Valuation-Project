"""
Valuation Routes - Refactored to use SessionService and International Services

Handles valuation workflow steps 4-10 using advanced service processors.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
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
    ValuateResponse
)
from app.services.international.step5_assumptions_processor import Step5AssumptionsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.step7_historical_data_processor import Step7HistoricalDataProcessor
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor
from app.services.international.yfinance_service import YFinanceService

logger = get_logger(__name__)

router = APIRouter(tags=["Valuation"])

# Initialize processors
step5_processor = Step5AssumptionsProcessor()
step6_processor = Step6DataReviewProcessor()
step7_processor = Step7HistoricalDataProcessor()
step8_processor = Step8ManualOverridesProcessor()
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


@router.post("/step-4-select-models", response_model=ModelSelectResponse)
async def select_models(request: ModelSelectRequest):
    """
    Step 4: User selects valuation model.
    Uses SessionService for session management.
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update session with selected model
        session_service.update_session_data(request.session_id, "selected_model", request.model.upper())
        session_service.update_session_data(request.session_id, "status", "ready_for_data_fetch")

        return ModelSelectResponse(
            message="Model selected",
            next_step="fetch_data",
            selected_model=request.model.upper()
        )
    except Exception as e:
        logger.error(f"Model selection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-5-prepare-inputs", response_model=PrepareInputsResponse)
async def prepare_inputs(request: PrepareInputsRequest):
    """
    Step 5: Prepare required inputs for selected model.
    Uses SessionService for session management and Step5AssumptionsProcessor for international markets.
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        model = session_service.get_session_value(request.session_id, "selected_model", "DCF")
        ticker = session.get("ticker")
        peer_tickers = session.get("peer_tickers", [])

        # Use Step5AssumptionsProcessor to get required inputs from international service
        result = step5_processor.process_data_retrieval_inputs(
            ticker=ticker or "UNKNOWN",
            valuation_model=model,
            peer_tickers=peer_tickers
        )

        # Convert retrieval groups to InputRequirement format for frontend
        required_inputs = []
        for group_name, fields in result.retrieval_groups.items():
            for field in fields:
                required_inputs.append({
                    "category": group_name,
                    "name": field.field_name,
                    "requiresInput": field.is_required,
                    "description": field.description,
                    "unit": None
                })

        session_service.update_session_data(request.session_id, "status", "ready_to_fetch")

        return PrepareInputsResponse(
            status="ready_to_fetch",
            required_inputs=required_inputs,
            message=result.message
        )
    except Exception as e:
        logger.error(f"Prepare inputs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-6-fetch-api-data", response_model=FetchDataResponse)
async def fetch_api_data(request: FetchDataRequest):
    """
    Step 6: Fetch financial data from APIs and calculate metrics.
    Uses SessionService for session management and Step6DataReviewProcessor for comprehensive data review.
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        market = session.get("market")
        model = session_service.get_session_value(request.session_id, "selected_model", "DCF")

        # Retrieve peer data and other assumptions from session (saved in Step 3)
        retrieved_assumptions = session_service.get_session_value(request.session_id, "retrieved_assumptions", {})

        # Use Step6DataReviewProcessor for comprehensive data fetching and calculation
        result = await step6_processor.process_data_review(
            ticker=ticker,
            market=market,
            valuation_model=model,
            retrieved_assumptions=retrieved_assumptions
        )

        # Store results in session using SessionService (with JSON serialization)
        result_dict = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result
        session_service.update_session_data(request.session_id, "financial_data", result_dict)
        session_service.update_session_data(request.session_id, "status", "data_ready")

        return FetchDataResponse(
            status="data_ready",
            data=result_dict,
            message="Financial data retrieved successfully from APIs."
        )
    except Exception as e:
        logger.error(f"Fetch API data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-7-retrieve-historical-data", response_model=GenerateAIResponse)
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
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        financial_data = session_service.get_session_value(request.session_id, "financial_data")
        model = session_service.get_session_value(request.session_id, "selected_model", "DCF")
        market = session_service.get_session_value(request.session_id, "market", "US")

        if not financial_data:
            raise HTTPException(status_code=400, detail="No financial data available")

        # Use Step7HistoricalDataProcessor for AI-powered historical data extraction
        result = await step7_processor.retrieve_historical_data(
            ticker=ticker,
            company_name=session.get("company_name", ticker),
            valuation_model=model,
            market=market,
            step6_financial_data=financial_data
        )

        # Store historical data in session using SessionService
        session_service.update_session_data(request.session_id, "historical_data_gaps_filled", result)
        session_service.update_session_data(request.session_id, "status", "historical_data_ready")

        # Convert HistoricalDataRetrievalResponse to dict for GenerateAIResponse
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        elif hasattr(result, 'dict'):
            result_dict = result.dict()
        else:
            result_dict = dict(result) if isinstance(result, dict) else str(result)

        # Add metadata about fallback usage
        metadata = {"model_version": "v2.0"}
        if result.total_gaps_filled > 0 and result.total_gaps_found > 0:
            # Check if any gaps were filled using deterministic fallback
            has_fallback = any(
                gap.get('data_source') == 'Deterministic_Fallback_Calculation'
                for gap in result_dict.get('historical_gaps_filled', [])
            )
            if has_fallback:
                metadata["used_fallback"] = True
                metadata["fallback_reason"] = "AI extraction unavailable, using deterministic calculations"

        logger.info(f"Step 7 complete: {result.total_gaps_filled}/{result.total_gaps_found} gaps filled, completeness: {result.data_completeness_score:.1%}")

        return GenerateAIResponse(
            status="historical_data_ready",
            suggestions=result_dict,
            message=f"Historical data retrieval complete. {result.total_gaps_filled} gaps filled with {result.data_completeness_score:.1%} completeness.",
            _metadata=metadata
        )
    except Exception as e:
        logger.error(f"Step 7 historical data retrieval error: {e}")
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
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        valuation_model = session_service.get_session_value(request.session_id, "selected_model", "DCF")
        step6_data = session_service.get_session_value(request.session_id, "financial_data", {})
        step7_data = session_service.get_session_value(request.session_id, "historical_data_gaps_filled", {})

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Use Step8ManualOverridesProcessor to generate AI suggestions for the category
        result = await step8_processor.generate_ai_suggestions_for_category(
            ticker=ticker,
            valuation_model=valuation_model,
            category=request.category,
            step6_data=step6_data,
            step7_data=step7_data if step7_data else None
        )

        # Store AI suggestions in session for this category
        current_suggestions = session_service.get_session_value(request.session_id, "ai_suggestions", {})
        current_suggestions[request.category] = result.model_dump() if hasattr(result, 'model_dump') else result
        session_service.update_session_data(request.session_id, "ai_suggestions", current_suggestions)

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
    Step 9: User confirms or overrides assumptions.
    Uses SessionService for session management and Step8ManualOverridesProcessor for assumption management.
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ai_suggestions = session_service.get_session_value(request.session_id, "ai_suggestions", {})

        # Use Step8ManualOverridesProcessor to handle confirmations
        result = await step8_processor.initialize_assumptions(
            session_id=request.session_id,
            ai_suggestions=ai_suggestions,
            user_overrides=request.confirmed_values
        )

        # Store confirmed assumptions using SessionService
        session_service.update_session_data(request.session_id, "confirmed_assumptions", result)
        session_service.update_session_data(request.session_id, "status", "assumptions_confirmed")

        return ConfirmAssumptionsResponse(
            status="assumptions_confirmed",
            message="Assumptions confirmed successfully"
        )
    except Exception as e:
        logger.error(f"Confirm assumptions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-10-valuate", response_model=ValuateResponse)
async def valuate(request: ValuateRequest):
    """
    Step 10: Run valuation engine.
    Uses SessionService for session management and Step10ValuationProcessor for comprehensive multi-model valuation.
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        model = session_service.get_session_value(request.session_id, "selected_model", "DCF")
        confirmed_assumptions = session_service.get_session_value(request.session_id, "confirmed_assumptions")

        if not confirmed_assumptions:
            raise HTTPException(status_code=400, detail="No confirmed assumptions available")

        # Use Step10ValuationProcessor for comprehensive valuation
        result = await step10_processor.run_valuation(
            ticker=ticker,
            model=model,
            assumptions=confirmed_assumptions
        )

        # Store valuation result using SessionService
        session_service.update_session_data(request.session_id, "valuation_result", result)
        session_service.update_session_data(request.session_id, "status", "valuation_complete")

        return ValuateResponse(
            status="success",
            valuation_results=[result],
            message="Valuation completed successfully"
        )
    except Exception as e:
        logger.error(f"Valuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))