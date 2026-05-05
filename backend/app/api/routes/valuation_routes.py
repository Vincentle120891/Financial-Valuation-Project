"""
Valuation Routes - Refactored to use International Services

Handles valuation workflow steps 4-10 using advanced service processors.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.logging_config import get_logger
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
from app.services.international.step6_data_review_processor import Step6DataReviewProcessor
from app.services.international.step7_derived_data_processor import Step7DerivedDataProcessor
from app.services.international.step8_manual_overrides_processor import Step8ManualOverridesProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor

logger = get_logger(__name__)

router = APIRouter(tags=["Valuation"])

# Initialize processors
step6_processor = Step6DataReviewProcessor()
step7_processor = Step7DerivedDataProcessor()
step8_processor = Step8ManualOverridesProcessor()
step10_processor = Step10ValuationProcessor()


@router.post("/step-4-select-models", response_model=ModelSelectResponse)
async def select_models(request: ModelSelectRequest):
    """
    Step 4: User selects valuation model.
    """
    try:
        from app.main import get_session_store
        sessions = get_session_store()
        
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sessions[request.session_id]["selected_model"] = request.model.upper()
        sessions[request.session_id]["status"] = "ready_for_data_fetch"
        
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
    """
    try:
        from app.main import get_session_store
        sessions = get_session_store()
        
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[request.session_id]
        model = session.get("selected_model", "DCF")
        
        # Define required inputs based on model
        required_inputs = [
            {"field": "revenue", "type": "historical", "required": True},
            {"field": "net_income", "type": "historical", "required": True},
            {"field": "total_assets", "type": "historical", "required": True},
            {"field": "total_equity", "type": "historical", "required": True},
            {"field": "operating_income", "type": "historical", "required": True},
            {"field": "ebitda", "type": "historical", "required": True},
            {"field": "free_cash_flow", "type": "historical", "required": False},
            {"field": "revenue_growth_rate", "type": "forecast", "required": True},
            {"field": "operating_margin", "type": "forecast", "required": True},
            {"field": "tax_rate", "type": "forecast", "required": True},
            {"field": "wacc", "type": "discount_rate", "required": True},
            {"field": "terminal_growth_rate", "type": "terminal_value", "required": True},
        ]
        
        session["status"] = "ready_to_fetch"
        
        return PrepareInputsResponse(
            status="ready_to_fetch",
            required_inputs=required_inputs,
            message=f"Found {len(required_inputs)} required inputs for your selected model"
        )
    except Exception as e:
        logger.error(f"Prepare inputs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-6-fetch-api-data", response_model=FetchDataResponse)
async def fetch_api_data(request: FetchDataRequest):
    """
    Step 6: Fetch financial data from APIs and calculate metrics.
    Uses Step6DataReviewProcessor for comprehensive data review.
    """
    try:
        from app.main import get_session_store
        sessions = get_session_store()
        
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[request.session_id]
        ticker = session.get("ticker")
        market = session.get("market")
        model = session.get("selected_model", "DCF")
        
        # Use Step6DataReviewProcessor for comprehensive data fetching and calculation
        result = await step6_processor.process_data_review(
            ticker=ticker,
            model=model,
            market=market
        )
        
        # Store results in session
        session["financial_data"] = result
        session["status"] = "data_ready"
        
        return FetchDataResponse(
            status="data_ready",
            data=result,
            message="Financial data retrieved successfully from APIs."
        )
    except Exception as e:
        logger.error(f"Fetch API data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-7-generate-ai-assumptions", response_model=GenerateAIResponse)
async def generate_ai_assumptions(request: GenerateAIRequest):
    """
    Step 7: Generate AI-powered assumptions.
    Uses Step7DerivedDataProcessor for advanced derived calculations.
    """
    try:
        from app.main import get_session_store
        sessions = get_session_store()
        
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[request.session_id]
        ticker = session.get("ticker")
        financial_data = session.get("financial_data")
        
        if not financial_data:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        # Use Step7DerivedDataProcessor for AI-driven analysis
        result = await step7_processor.calculate_derived_data(
            ticker=ticker,
            historical_data=financial_data.get("historical_financials", []),
            peers_data=financial_data.get("peers_data", [])
        )
        
        # Store AI suggestions in session
        session["ai_suggestions"] = result
        session["status"] = "ai_ready"
        
        return GenerateAIResponse(
            status="ai_ready",
            suggestions=result,
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
    Uses Step8ManualOverridesProcessor for assumption management.
    """
    try:
        from app.main import get_session_store
        sessions = get_session_store()
        
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[request.session_id]
        
        # Use Step8ManualOverridesProcessor to handle confirmations
        result = await step8_processor.initialize_assumptions(
            session_id=request.session_id,
            ai_suggestions=session.get("ai_suggestions", {}),
            user_overrides=request.confirmed_values
        )
        
        # Store confirmed assumptions
        session["confirmed_assumptions"] = result
        session["status"] = "assumptions_confirmed"
        
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
    Uses Step10ValuationProcessor for comprehensive multi-model valuation.
    """
    try:
        from app.main import get_session_store
        sessions = get_session_store()
        
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[request.session_id]
        ticker = session.get("ticker")
        model = session.get("selected_model", "DCF")
        confirmed_assumptions = session.get("confirmed_assumptions")
        
        if not confirmed_assumptions:
            raise HTTPException(status_code=400, detail="No confirmed assumptions available")
        
        # Use Step10ValuationProcessor for comprehensive valuation
        result = await step10_processor.run_valuation(
            ticker=ticker,
            model=model,
            assumptions=confirmed_assumptions
        )
        
        # Store valuation result
        session["valuation_result"] = result
        session["status"] = "valuation_complete"
        
        return ValuateResponse(
            status="success",
            valuation_results=[result],
            message="Valuation completed successfully"
        )
    except Exception as e:
        logger.error(f"Valuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
