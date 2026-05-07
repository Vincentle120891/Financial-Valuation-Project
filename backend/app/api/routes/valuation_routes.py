"""
Valuation Routes - Refactored to use SessionService and International Services

Handles valuation workflow steps 4-10 using advanced service processors.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    ConfirmAssumptionsRequest,
    ConfirmAssumptionsResponse,
    ValuateRequest,
    ValuateResponse
)
from app.services.international.step5_assumptions_processor import Step5AssumptionsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.step7_ai_suggestions import Step7AISuggestionsProcessor
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor

logger = get_logger(__name__)

router = APIRouter(tags=["Valuation"])

# Initialize processors
step5_processor = Step5AssumptionsProcessor()
step6_processor = Step6DataReviewProcessor()
step7_processor = Step7AISuggestionsProcessor()
step8_processor = Step8ManualOverridesProcessor()
step10_processor = Step10ValuationProcessor()


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
        
        # Use Step6DataReviewProcessor for comprehensive data fetching and calculation
        result = await step6_processor.process_data_review(
            ticker=ticker,
            market=market,
            valuation_model=model
        )
        
        # Store results in session using SessionService
        session_service.update_session_data(request.session_id, "financial_data", result.model_dump() if hasattr(result, 'model_dump') else result)
        session_service.update_session_data(request.session_id, "status", "data_ready")
        
        return FetchDataResponse(
            status="data_ready",
            data=result.model_dump() if hasattr(result, 'model_dump') else result,
            message="Financial data retrieved successfully from APIs."
        )
    except Exception as e:
        logger.error(f"Fetch API data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-7-generate-ai-assumptions", response_model=GenerateAIResponse)
async def generate_ai_assumptions(request: GenerateAIRequest):
    """
    Step 7: Generate AI-powered assumptions.
    Uses SessionService for session management and Step7DerivedDataProcessor for advanced derived calculations.
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        ticker = session.get("ticker")
        financial_data = session_service.get_session_value(request.session_id, "financial_data")
        model = session_service.get_session_value(request.session_id, "selected_model", "DCF")
        
        if not financial_data:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        # Use Step7AISuggestionsProcessor for AI-driven analysis
        result = await step7_processor.generate_ai_suggestions(
            ticker=ticker,
            company_name=session.get("company_name", ticker),
            valuation_model=model,
            market=session.get("market", "US"),
            financial_data=financial_data
        )
        
        # Store AI suggestions in session using SessionService
        session_service.update_session_data(request.session_id, "ai_suggestions", result)
        session_service.update_session_data(request.session_id, "status", "ai_ready")
        
        # Convert AISuggestionResponse to dict for GenerateAIResponse
        suggestions_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        
        return GenerateAIResponse(
            status="ai_ready",
            suggestions=suggestions_dict,
            message="AI analysis complete. Please review assumptions.",
            _metadata={"model_version": "v2.0"}
        )
    except Exception as e:
        logger.error(f"Generate AI assumptions error: {e}")
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
