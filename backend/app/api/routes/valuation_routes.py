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
    UnifiedStep4SavePeersRequest,
    UnifiedStep4SavePeersResponse,
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
    SensitivityAnalysis,
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
from app.services.international.step8_unified_transformer import Step8UnifiedTransformer
from app.services.international.step9_confirmation_processor import Step9ConfirmationProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor
from app.services.international.step10_dcf_processor import Step10DCFProcessor
from app.services.vietnamese.vn_step3_model_selection_processor import vn_Step3ModelSelectionProcessor
from app.services.vietnamese.vn_step4_peer_discovery_service import vn_Step4PeerDiscoveryService
from app.services.vietnamese.vn_step9_confirmation_processor import vn_Step9ConfirmationProcessor
from app.services.vietnamese.vn_step10_valuation_processor import vn_Step10ValuationProcessor
from app.services.international.yfinance_service import YFinanceService
from app.services.international.institutional_peer_discovery import InstitutionalPeerDiscoveryService, PeerDiscoveryRequest
from app.services.international.step4_peer_management_service import Step4PeerManagementService
from app.services.international.step7_data_enrichment_service import Step7DataEnrichmentService
from app.services.international.sec_edgar_service import get_sec_edgar_service
from app.services.international.step7_financial_statements_merger import FinancialStatementsMerger
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter(tags=["Valuation"])


def _flatten_ai_suggestions(ai_suggestions: dict) -> dict:
    """
    Flatten AI suggestions from Step 8 session format to flat param dict.
    
    Step 8 stores: { "REVENUE_DRIVERS": { assumptions: [{ metric, ai_suggestion: {suggested_value} }] } }
    Step 9 expects: { "revenue_growth_year_1": 0.05, ... }
    """
    METRIC_TO_FIELD = {
        "Revenue Growth": "volume_growth",
        "Inflation Rate": "inflation_rate",
        "COGS % of Revenue": "cogs_percent",
        "SG&A % of Revenue": "sgna_percent",
        "Effective Tax Rate": "tax_rate",
        "Accounts Receivable Days": "receivables_days",
        "Inventory Days": "inventory_days",
        "Accounts Payable Days": "payables_days",
        "Risk-Free Rate": "risk_free_rate",
        "Market Risk Premium": "market_risk_premium",
        "Country Risk Premium": "country_risk_premium",
        "Pre-Tax Cost of Debt": "cost_of_debt",
        "Target Debt-to-Equity": "de_equity_ratio",
        "Terminal Growth Rate": "terminal_growth_rate",
        "Terminal EBITDA Multiple": "terminal_ebitda_multiple",
        "Target Net Profit Margin": "net_profit_margin",
        "Target Asset Turnover": "asset_turnover",
        "Target Equity Multiplier": "equity_multiplier",
        "P/E Multiple": "pe_multiple",
        "EV/EBITDA Multiple": "ev_ebitda_multiple",
        "P/B Multiple": "pb_multiple",
        "P/S Multiple": "ps_multiple",
    }
    flat = {}
    for _category_name, category_data in ai_suggestions.items():
        if isinstance(category_data, dict):
            for assumption in category_data.get("assumptions", []):
                metric = assumption.get("metric", "")
                ai_sugg = assumption.get("ai_suggestion")
                if ai_sugg and metric in METRIC_TO_FIELD:
                    flat[METRIC_TO_FIELD[metric]] = ai_sugg.get("suggested_value")
    return flat

# Initialize processors and services
step3_processor = Step3SelectedModelsProcessor(market="international")
step4_service = Step4PeerManagementService()
step5_processor = Step5RequiredInputsProcessor()
step6_processor = Step6DataReviewProcessor()
step7_processor = Step7HistoricalDataProcessor()
step7_enrichment_service = Step7DataEnrichmentService()
step8_processor = Step8ManualOverridesProcessor()
step9_processor = Step9ConfirmationProcessor()
vn_step3_model_processor = vn_Step3ModelSelectionProcessor()
vn_step4_peer_service = vn_Step4PeerDiscoveryService()
vn_step9_processor = vn_Step9ConfirmationProcessor()


def _extract_peer_medians(step6_data: Dict[str, Any]) -> Dict[str, float]:
    """Extract peer median values from Step 6 calculated_metrics.
    
    Returns a dict like {"ev_ebitda": 10.5, "pe": 15.0, "pb": 2.5, "ps": 3.0}
    for passing to Step 8 processor (Issue #9: eliminate step6_data dependency).
    """
    peer_medians = {}
    if not step6_data:
        return peer_medians
    
    calc_metrics = step6_data.get('calculated_metrics', {})
    if not isinstance(calc_metrics, dict):
        return peer_medians
    
    # Flat dict lookup
    for key in ('peer_median_ev_ebitda', 'peer_median_pe', 'peer_median_pb', 'peer_median_ps'):
        val = calc_metrics.get(key)
        if val is not None:
            # Map to short key for Step 8
            short_key = key.replace('peer_median_', '')
            try:
                peer_medians[short_key] = float(val)
            except (ValueError, TypeError):
                pass
    
    # DataFields list lookup (fallback)
    if not peer_medians:
        data_fields = calc_metrics.get('data_fields', [])
        if isinstance(data_fields, list):
            mapping = {
                'peer_median_ev_ebitda': 'ev_ebitda',
                'peer_median_pe': 'pe',
                'peer_median_pb': 'pb',
                'peer_median_ps': 'ps',
            }
            for field in data_fields:
                if isinstance(field, dict):
                    field_name = field.get('field_name', '')
                    if field_name in mapping:
                        val = field.get('value')
                        if val is not None:
                            try:
                                peer_medians[mapping[field_name]] = float(val)
                            except (ValueError, TypeError):
                                pass
    
    return peer_medians
step10_processor = Step10ValuationProcessor()
dcf_proc = Step10DCFProcessor()
vn_step10_processor = vn_Step10ValuationProcessor()
yfinance_service = YFinanceService()
peer_discovery_service = InstitutionalPeerDiscoveryService()


async def _enrich_peers_for_wacc(peer_companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich peer companies with real financial data for WACC calculation.
    
    The Step 4 peer_companies only have ticker/company_name/sector/industry.
    This function fetches beta, total_debt, market_cap, tax_rate from yfinance
    so that _build_peer_wacc_data can calculate D/E ratios and Hamada betas.
    
    Runs concurrently for all peers to minimize latency.
    """
    import asyncio
    
    async def _fetch_peer_financials(peer: Dict[str, Any]) -> Dict[str, Any]:
        ticker = peer.get("ticker", "")
        if not ticker:
            return peer
        try:
            # Run yfinance in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, yfinance_service.get_ticker_info, ticker)
            if info:
                # Map yfinance fields to peer_wacc_data format
                market_cap = info.get("marketCap") or 0
                total_debt = info.get("totalDebt") or 0
                beta = info.get("beta") or 1.0
                tax_rate = info.get("effectiveTaxRate") or 0.21
                country = info.get("country", "")
                
                # Detect currency mismatch: yfinance returns totalDebt in local currency
                # but marketCap is always in USD. Use country (not currency) to detect.
                if market_cap > 0 and total_debt > 0:
                    raw_d_e = total_debt / market_cap
                    if raw_d_e > 5:
                        logger.warning(f"Peer {ticker}: D/E={raw_d_e:.1f} seems high (country={country}). "
                                      f"Market cap=${market_cap/1e9:.1f}B, total debt={total_debt/1e9:.1f}B")
                        # yfinance returns debt in local currency for non-US companies
                        # Approximate exchange rates for common currencies
                        EXCHANGE_RATES = {"Japan": 150, "Eurozone": 1.1, "Taiwan": 32, "South Korea": 1350, "UK": 0.79}
                        for key, rate in EXCHANGE_RATES.items():
                            if key.lower() in country.lower():
                                total_debt = total_debt / rate
                                logger.info(f"  → Converted {country} debt to USD: ${total_debt/1e9:.1f}B (÷{rate})")
                                break
                        else:
                            # No exchange rate found — use D/E clamp as fallback
                            logger.warning(f"  → No exchange rate for {country}, using D/E clamp")
                
                peer["market_cap"] = market_cap
                peer["equity"] = market_cap  # Equity ≈ Market Cap for WACC
                peer["total_debt"] = total_debt
                peer["debt"] = total_debt
                peer["beta"] = beta
                peer["tax_rate"] = tax_rate
                peer["company_name"] = info.get("longName") or info.get("shortName") or ticker
        except Exception as e:
            logger.warning(f"Failed to enrich peer {ticker} for WACC: {e}")
        return peer
    
    # Fetch all peers concurrently
    tasks = [_fetch_peer_financials(peer) for peer in peer_companies]
    enriched = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    result = []
    for item in enriched:
        if isinstance(item, dict):
            result.append(item)
    return result


@router.post("/step-4-save-peers", response_model=UnifiedStep4SavePeersResponse)
async def save_peers(request: UnifiedStep4SavePeersRequest):
    """
    Step 4: Save selected peer companies to session.
    Delegates to Step4PeerManagementService for all business logic.
    Uses unified PeerCompany schema for strict validation.
    """
    try:
        # Convert PeerCompany objects to dicts for the service layer
        peer_dicts = [peer.model_dump() for peer in request.peers]

        # Delegate to service layer
        result = step4_service.save_peers_and_fetch_data(
            session_id=request.session_id,
            peers=peer_dicts
        )

        # Store full peer company data in session for Step 8 WACC pre-population
        peer_list = result.get("peer_list", [])
        if peer_list:
            session_service.update_session_data(
                request.session_id, "peer_companies",
                peer_list
            )

        return UnifiedStep4SavePeersResponse(
            status=result["status"],
            message=result["message"],
            peers_saved=result["peers_saved"],
            peer_list=result.get("peer_list")
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

        # Get method and market from request
        valuation_method = request.method.value.lower()
        market_val = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        # ── Market-aware routing: delegate to VN or INT processor ──────────
        if market_val == "vietnam":
            discovery_result = vn_step4_peer_service.discover_peers(
                session_id=request.session_id,
                ticker=session.get("ticker", ""),
                method=valuation_method,
                max_peers=request.max_peers or 10,
                market=market_val,
            )
        else:
            # Route to appropriate INT discovery service based on method
            if valuation_method == "dcf":
                discovery_result = await dcf_discover_peers(
                    session_id=request.session_id,
                    ticker=session.get("ticker", ""),
                    market=request.market.value,
                    max_peers=request.max_peers or 10,
                    request=req,
                )
            elif valuation_method == "dupont":
                discovery_result = await dupont_discover_peers(
                    session_id=request.session_id,
                    ticker=session.get("ticker", ""),
                    market=request.market.value,
                    max_peers=request.max_peers or 10,
                    request=req,
                )
            elif valuation_method == "comps":
                discovery_result = await comps_discover_peers(
                    session_id=request.session_id,
                    ticker=session.get("ticker", ""),
                    market=request.market.value,
                    max_peers=request.max_peers or 10,
                    request=req,
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid valuation method: {valuation_method}. Must be 'dcf', 'dupont', or 'comps'",
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

        # ── Market-aware routing: delegate to VN or INT processor ──────────
        if market == "vietnam":
            model_result = vn_step3_model_processor.process_model_selection([method])
        else:
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
        # SessionService stores peer data in session["data"]["peer_tickers"]
        # (because "peer_tickers" is not in shared_keys list)
        peer_tickers = session.get("data", {}).get("peer_tickers", [])
        if not peer_tickers:
            peer_tickers = session.get("peer_tickers", [])
        if not peer_tickers:
            # Check selected_peers in data dict
            selected_peers = session.get("data", {}).get("selected_peers", [])
            if selected_peers:
                peer_tickers = [p.get('symbol', p.get('ticker', '')) if isinstance(p, dict) else str(p) for p in selected_peers]
        logger.info(f"Step 5: Found {len(peer_tickers)} peer tickers: {peer_tickers}")

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

    ARCHITECTURE (Option C - Processor-Owned Fetch):
    Route passes None for data parameters. Each processor (DCF, DuPont, Comps)
    has its own complete fetch logic via APIAdapter that runs when data is None.
    This avoids data format mismatches between route-level and processor-level fetching.

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Stores financial data in the specific valuation track
    - Each model's data is stored independently
    """
    try:
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        if not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

        logger.info(f"Step 6: Delegating data fetch to {method} processor for {ticker}")

        # Pass session data as session_cache so processors can access peer_tickers and other session state
        # This enables "Fetch Once, Use Many" pattern - processors check cache before fetching
        legacy_result = await step6_processor.process_data_review(
            ticker=ticker,
            market=market,
            historical_data=None,
            market_data=None,
            forecast_data={},
            retrieved_assumptions=None,
            user_overrides={},
            valuation_model=method,
            session_cache=session  # Pass session data so processors can access peer_tickers
        )

        unified_response = Step6UnifiedTransformer.transform_any_response(
            response=legacy_result,
            valuation_model=method
        )

        # Store results in session
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
    request: Request,
    session_id: str,
    ticker: str,
    company_name: str,
    method: str,
    market: str = "international",
    custom_prompt: str = None
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
        # Get API keys from request headers (injected by APIKeyMiddleware)
        api_keys = getattr(request.state, 'api_keys', {})
        
        result = await step7_enrichment_service.extract_from_web_search(
            session_id=session_id,
            ticker=ticker,
            company_name=company_name,
            method=method,
            market=market,
            api_keys=api_keys,
            custom_prompt=custom_prompt
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI web search error for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI web search failed: {str(e)}")


class SecEdgarFetchRequest(BaseModel):
    """Request body for SEC EDGAR filing fetch"""
    session_id: str
    ticker: str
    company_name: str = ""
    email: str = ""
    method: str = "DCF"
    market: str = "international"


@router.post("/step-7-fetch-sec-edgar")
async def fetch_sec_edgar_for_step7(request: SecEdgarFetchRequest):
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
        
        # 1. Fetch filing metadata (10-K, 10-Q listings) — scan 100 recent forms
        filings_result = await sec_service.search_company_filings(
            ticker=request.ticker.upper(),
            email=request.email,
            company_name=request.company_name or request.ticker,
            limit=100
        )
        
        # 2. Fetch actual financial data via XBRL (PP&E Gross, Accumulated Depreciation)
        xbrl_result = await sec_service.fetch_company_facts_xbrl(
            ticker=request.ticker.upper(),
            email=request.email,
            company_name=request.company_name or request.ticker
        )
        
        # Build combined result
        combined_result = {
            "success": filings_result.get("success", False),
            "filings": filings_result.get("filings", []),
            "filings_count": filings_result.get("filings_count", 0),
            "cik": filings_result.get("cik"),
            "company_name": filings_result.get("company_name"),
            "source": "SEC EDGAR"
        }
        
        # Add XBRL financial data if available
        if xbrl_result.get("success"):
            # Store ALL XBRL data (including nested income_statement/balance_sheet/cash_flow sections
            # and flat backward-compatible keys like interest_expense, pretax_income, interest_paid)
            combined_result["xbrl_data"] = {k: v for k, v in xbrl_result.items() if k != "success"}
            # Count years from whichever field has data
            ppe_years = len(xbrl_result.get("ppe_gross", {}))
            accum_years = len(xbrl_result.get("accumulated_depreciation", {}))
            assets_years = len(xbrl_result.get("total_assets", {}))
            tax_years = len(xbrl_result.get("tax_loss_carryforward", {}))
            deferred_years = len(xbrl_result.get("deferred_tax_assets", {}))
            interest_years = len(xbrl_result.get("interest_expense", {}))
            pretax_years = len(xbrl_result.get("pretax_income", {}))
            combined_result["xbrl_data_years"] = max(ppe_years, accum_years, assets_years, tax_years, deferred_years, interest_years, pretax_years)
            combined_result["xbrl_fields_extracted"] = xbrl_result.get("total_fields_extracted", 0)
            combined_result["message"] = (
                f"Found {combined_result['filings_count']} SEC filings and extracted "
                f"{combined_result['xbrl_data_years']} years of XBRL data "
                f"(PP&E, Accum Depr, Total Assets, Tax NOL, Deferred Tax, Interest Expense, Pretax Income)"
            )
        else:
            combined_result["xbrl_data"] = None
            combined_result["xbrl_data_years"] = 0
            combined_result["message"] = (
                f"Found {combined_result['filings_count']} SEC filings. "
                f"XBRL extraction: {xbrl_result.get('error', 'unavailable')}"
            )
        
        # Validate: At least filing metadata or XBRL data must be present
        has_filings = combined_result["filings_count"] > 0
        has_xbrl = combined_result.get("xbrl_data") is not None
        
        if not has_filings and not has_xbrl:
            raise HTTPException(
                status_code=404,
                detail=f"No SEC filings or XBRL data found for {request.ticker}. "
                       f"SEC EDGAR only covers US publicly traded companies."
            )
        
        # Store in session for FinancialStatementsMerger integration
        session_service.update_session_data(
            request.session_id,
            "sec_edgar_results",
            combined_result,
            market=request.market,
            method=request.method.lower()
        )
        
        # Log successful fetch
        logger.info(
            f"SEC EDGAR: {combined_result['filings_count']} filings, "
            f"XBRL: {combined_result['xbrl_data_years']} years for {request.ticker}",
            extra={
                "session_id": request.session_id,
                "cik": combined_result.get("cik"),
                "filings_count": combined_result["filings_count"],
                "xbrl_years": combined_result["xbrl_data_years"]
            }
        )
        
        return combined_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SEC EDGAR fetch error for {request.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SEC EDGAR fetch failed: {str(e)}")


# =============================================================================
# COMPLETE FINANCIAL STATEMENTS ENDPOINT
# =============================================================================

financial_statements_merger = FinancialStatementsMerger()


@router.get("/complete-financial-statements")
async def get_complete_financial_statements(
    session_id: str,
    market: str = "international",
    method: str = "dcf"
):
    """
    Get complete merged financial statements (Income Statement, Balance Sheet, Cash Flow).
    
    Returns the merged Step 6 + Step 7 data organized by financial statement type.
    Created during Step 8 initialization, stored in session for user access.
    """
    try:
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Try to get already-merged data from session
        complete_statements = session_service.get_session_value(
            session_id,
            "complete_financial_statements",
            None,
            market=market,
            method=method.lower()
        )
        
        if complete_statements:
            return {"status": "success", "data": complete_statements}
        
        # If not yet merged, run the merger on-demand
        step6_data = session_service.get_session_value(
            session_id, "financial_data", {}, market=market, method=method.lower()
        )
        step7_data = session_service.get_session_value(
            session_id, "historical_data_gaps_filled", {}, market=market, method=method.lower()
        )
        ai_web_data = session_service.get_session_value(
            session_id, "ai_web_search_results", {}, market=market, method=method.lower()
        )
        pdf_data = session_service.get_session_value(
            session_id, "pdf_extraction_results", {}, market=market, method=method.lower()
        )
        sec_edgar_data = session_service.get_session_value(
            session_id, "sec_edgar_results", {}, market=market, method=method.lower()
        )
        
        # Convert Pydantic models to dicts for the merger
        def to_dict(obj):
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, 'model_dump'):
                return obj.model_dump(mode='json')
            if hasattr(obj, 'dict'):
                return obj.dict()
            return obj
        
        result = financial_statements_merger.merge(
            step6_data=to_dict(step6_data),
            step7_data=to_dict(step7_data),
            ai_web_search_data=to_dict(ai_web_data),
            pdf_extraction_data=to_dict(pdf_data),
            sec_edgar_data=to_dict(sec_edgar_data),
        )
        result["market"] = market
        result["method"] = method
        
        # Store for future access
        session_service.update_session_data(
            session_id, "complete_financial_statements", result,
            market=market, method=method.lower()
        )
        
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Get complete financial statements error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STEP 8: INITIALIZE ASSUMPTIONS (with merger)
# =============================================================================

@router.post("/step-8-initialize", response_model=UnifiedStep8Response)
async def initialize_step8_assumptions(request: UnifiedStep8InitializeRequest):
    """
    Step 8: Initialize assumptions with historical trendlines.

    1. MERGES Step 6 + Step 7 into complete_financial_statements
    2. Stores merged data in session (user-accessible)
    3. Builds assumption categories with trendlines from merged data

    MATRIX WORKFLOW:
    - Uses market/method from request parameters (REQUIRED - no fallback)
    - Initializes assumptions for the specific valuation track
    """
    try:
        # Get session data using SessionService
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()

        if not hasattr(request, 'method') or not request.method:
            raise HTTPException(status_code=400, detail="Method parameter is required")

        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

        # Get data from the specific valuation track
        step6_data = session_service.get_session_value(
            request.session_id, "financial_data", {}, market=market, method=method.lower()
        )
        step7_data = session_service.get_session_value(
            request.session_id, "historical_data_gaps_filled", {}, market=market, method=method.lower()
        )
        ai_web_data = session_service.get_session_value(
            request.session_id, "ai_web_search_results", {}, market=market, method=method.lower()
        )
        pdf_data = session_service.get_session_value(
            request.session_id, "pdf_extraction_results", {}, market=market, method=method.lower()
        )
        sec_edgar_data = session_service.get_session_value(
            request.session_id, "sec_edgar_results", {}, market=market, method=method.lower()
        )

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # 1. MERGE Step 6 + Step 7 into complete financial statements
        # Convert Pydantic models to dicts for the merger
        def _to_dict(obj):
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, 'model_dump'):
                return obj.model_dump(mode='json')
            if hasattr(obj, 'dict'):
                return obj.dict()
            return obj
        
        complete_statements = financial_statements_merger.merge(
            step6_data=_to_dict(step6_data),
            step7_data=_to_dict(step7_data),
            ai_web_search_data=_to_dict(ai_web_data),
            pdf_extraction_data=_to_dict(pdf_data),
            sec_edgar_data=_to_dict(sec_edgar_data),
        )
        complete_statements["market"] = market
        complete_statements["method"] = method
        
        # 2. Store merged data in session (user-accessible via GET endpoint)
        session_service.update_session_data(
            request.session_id, "complete_financial_statements", complete_statements,
            market=market, method=method.lower()
        )

        # 3. Extract peer medians from step6 calculated_metrics (Issue #9)
        peer_medians = _extract_peer_medians(step6_data)

        # 4. Read Step 2 market data for WACC pre-population
        risk_metrics = session_service.get_session_value(
            request.session_id, "risk_metrics", {}, market=market
        )

        # 5. Read Step 4 peer companies and enrich with real financial data for WACC
        peer_companies = session_service.get_session_value(
            request.session_id, "peer_companies", [], market=market
        )
        # Fallback: also check "selected_peers" (stored by Step 3)
        if not peer_companies:
            peer_companies = session_service.get_session_value(
                request.session_id, "selected_peers", [], market=market
            )
        if peer_companies:
            peer_companies = await _enrich_peers_for_wacc(peer_companies)

        # 6. Use Step8ManualOverridesProcessor with merged data
        result = await step8_processor.initialize_assumptions(
            ticker=ticker,
            valuation_model=method,
            complete_statements=complete_statements,
            peer_medians=peer_medians,
            market_data=risk_metrics,
            peer_companies=peer_companies
        )

        # Store initial assumptions in the specific valuation track
        session_service.update_session_data(
            request.session_id, "step8_assumptions",
            result.model_dump() if hasattr(result, 'model_dump') else result.dict(),
            market=market, method=method.lower()
        )

        # Debug: Log WACC values in the response
        for cat_key, cat_resp in result.categories.items():
            for a in cat_resp.assumptions:
                if a.metric in ("WACC", "Beta", "Risk-Free Rate", "Market Risk Premium"):
                    logger.info(f"Step8 response: {a.metric} = final_value={a.final_value}, user_value={a.user_value}")

        # Transform to UnifiedStep8Response (Issue #1 fix)
        unified = Step8UnifiedTransformer.transform_response(result, method)
        result_dict = unified.model_dump()
        result_dict["complete_financial_statements"] = complete_statements
        
        # Include peer WACC data for frontend peer table display
        if peer_companies:
            peer_wacc_data = step8_processor._build_peer_wacc_data(peer_companies)
            result_dict["peer_wacc_data"] = peer_wacc_data

        return result_dict
    except Exception as e:
        logger.error(f"Step 8 initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-8-generate-ai-suggestion")
async def generate_ai_suggestion(request: UnifiedStep8GenerateAISuggestionRequest, raw_request: Request):
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
        
        # Get complete_statements from session (merged during step-8-initialize)
        complete_statements = session_service.get_session_value(
            request.session_id,
            "complete_financial_statements",
            {},
            market=market,
            method=method.lower()
        )

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Extract peer medians from step6 calculated_metrics (Issue #9)
        peer_medians = _extract_peer_medians(step6_data)
        
        # Use Step8ManualOverridesProcessor with merged data (complete_statements only)
        # Pass request-level API keys so the AI engine uses frontend-provided keys
        request_api_keys = getattr(raw_request.state, 'api_keys', {})
        result = await step8_processor.generate_ai_suggestions_for_category(
            ticker=ticker,
            valuation_model=method,
            category=request.category,
            complete_statements=complete_statements,
            peer_medians=peer_medians,
            api_keys=request_api_keys if request_api_keys else None
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

        # Transform assumptions array to flat suggestion dict (Issue #2 fix)
        METRIC_TO_FIELD = {
            "Revenue Growth": "volume_growth",
            "Revenue Volume Growth": "volume_growth",
            "Revenue Price Increase": "price_increase",
            "COGS % of Revenue": "cogs_percent",
            "OpEx Growth": "opex_growth",
            "SG&A % of Revenue": "sgna_percent",
            "Capital Expenditure": "capital_expenditure",
            "Effective Tax Rate": "tax_rate",
            "Accounts Receivable Days": "receivables_days",
            "Inventory Days": "inventory_days",
            "Accounts Payable Days": "payables_days",
            "Risk-Free Rate": "risk_free_rate",
            "Market Risk Premium": "market_risk_premium",
            "Country Risk Premium": "country_risk_premium",
            "Pre-Tax Cost of Debt": "cost_of_debt",
            "Target Debt-to-Equity": "de_equity_ratio",
            "Terminal Growth Rate": "terminal_growth_rate",
            "Terminal EBITDA Multiple": "terminal_ebitda_multiple",
            "Target Net Profit Margin": "net_profit_margin",
            "Target Asset Turnover": "asset_turnover",
            "Target Equity Multiplier": "equity_multiplier",
            "P/E Multiple": "pe_multiple",
            "EV/EBITDA Multiple": "ev_ebitda_multiple",
            "P/B Multiple": "pb_multiple",
            "P/S Multiple": "ps_multiple",
        }

        suggestion = {}
        ai_details = {}  # Rich details per field (reasoning, confidence)
        for assumption in result_dict.get("assumptions", []):
            metric = assumption.get("metric", "")
            ai_suggestion = assumption.get("ai_suggestion")
            if ai_suggestion and metric in METRIC_TO_FIELD:
                field_key = METRIC_TO_FIELD[metric]
                suggestion[field_key] = ai_suggestion.get("suggested_value")
                ai_details[field_key] = {
                    "value": ai_suggestion.get("suggested_value"),
                    "reasoning": ai_suggestion.get("reasoning", ""),
                    "confidence": ai_suggestion.get("confidence_level", "medium"),
                }

        return {
            "status": "success",
            "category": result_dict.get("category", request.category),
            "category_name": result_dict.get("category_name", request.category),
            "suggestion": suggestion,
            "ai_details": ai_details,
            "ai_generated": True,
            "message": result_dict.get("message", "AI suggestions generated")
        }
    except Exception as e:
        logger.error(f"Generate AI suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GenerateScenariosRequest(BaseModel):
    """Request body for scenario generation"""
    session_id: str
    method: str = "DCF"
    market: str = "international"
    base_case: Dict[str, Any] = Field(default_factory=dict, description="Base case values for each metric")


@router.post("/step-8-generate-scenarios")
async def generate_scenarios(request: GenerateScenariosRequest):
    """
    Step 8: Generate Best/Worst scenarios from Base Case using historical volatility.
    
    Uses historical trendline std_dev to create optimistic (Best) and pessimistic (Worst)
    scenarios around the user's confirmed Base Case values.
    """
    try:
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        ticker = session.get("ticker")
        market = request.market.lower()
        method = request.method.upper()
        
        # Get complete_statements from session
        complete_statements = session_service.get_session_value(
            request.session_id, "complete_financial_statements", {},
            market=market, method=method.lower()
        )
        
        if not complete_statements:
            raise HTTPException(status_code=400, detail="No complete financial statements found. Run step-8-initialize first.")
        
        result = await step8_processor.generate_scenarios(
            ticker=ticker,
            valuation_model=method,
            base_case=request.base_case,
            complete_statements=complete_statements
        )
        
        return {
            "status": "success",
            "best_case": result["best_case"],
            "worst_case": result["worst_case"],
            "volatility": result["volatility"],
            "message": "Scenarios generated from historical volatility"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate scenarios error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-8-save-overrides")
async def save_overrides(request: Request):
    """
    Step 8: Save confirmed assumptions/overrides to session.
    Called by auto-save on every edit in ForecastDriversStep.
    Persists user edits so they survive page refresh and are available to Step 9.
    """
    try:
        body = await request.json()
        session_id = body.get("session_id")
        market = body.get("market", "international")
        method = body.get("method", "dcf")
        confirmed_values = body.get("confirmed_assumptions", {})

        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Merge with existing confirmed_assumptions (upsert per key)
        existing = session_service.get_session_value(
            session_id, "confirmed_assumptions", {}, market=market, method=method.lower()
        )
        existing.update(confirmed_values)

        session_service.update_session_data(
            session_id, "confirmed_assumptions", existing, market=market, method=method.lower()
        )

        return {"status": "saved", "keys": len(existing)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save overrides error: {e}")
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
        # Step 6: Aggregated historical financials and market data (still needed for market_data, peer data)
        step6_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            {},
            market=market,
            method=method.lower()
        )
        # Step 8: Merged complete financial statements (Step 6 + Step 7 merged in step-8-initialize)
        # Step 9 should use this merged data instead of raw Step 6/7
        complete_statements = session_service.get_session_value(
            request.session_id,
            "complete_financial_statements",
            {},
            market=market,
            method=method.lower()
        )
        # Step 7: Gap-filled historical data (fallback if complete_statements not yet merged)
        step7_data = session_service.get_session_value(
            request.session_id,
            "historical_data_gaps_filled",
            {},
            market=market,
            method=method.lower()
        )
        # Step 8: Read from confirmed_assumptions (auto-save) + step8_assumptions + ai_suggestions
        # Issue #1 fix: confirmed_assumptions is now written by /step-8-save-overrides endpoint
        saved_confirmed = session_service.get_session_value(
            request.session_id,
            "confirmed_assumptions",
            {},
            market=market,
            method=method.lower()
        )
        step8_assumptions = session_service.get_session_value(
            request.session_id,
            "step8_assumptions",
            {},
            market=market,
            method=method.lower()
        )
        step8_ai_suggestions = session_service.get_session_value(
            request.session_id,
            "ai_suggestions",
            {},
            market=market,
            method=method.lower()
        )

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        if not saved_confirmed and not step8_assumptions and not request.confirmed_assumptions and not request.confirmed_values:
            raise HTTPException(
                status_code=400,
                detail="No Step 8 assumptions found. Please complete Step 8 first."
            )

        # Build step8_final_inputs for the processor (Issue #3 + #6 fix:
        # Transform frontend confirmedValues format to flat dict expected by Step 9)
        # Priority: request body > saved session > step8_assumptions
        frontend_confirmed = request.confirmed_assumptions or request.confirmed_values or saved_confirmed or {}

        # Percentage normalization: ensure decimal (0-1) format for rate fields
        def _normalize_pct(val, field_name):
            """Normalize percentage values to decimal (0-1) format.
            Some upstream data stores percentages as whole numbers (e.g., 4.56 for 4.56%)
            instead of decimals (0.0456)."""
            if not isinstance(val, (int, float)):
                return val
            # Fields that must be in decimal (0-1) range
            pct_fields = {
                'risk_free_rate', 'market_risk_premium', 'country_risk_premium',
                'cost_of_debt', 'tax_rate', 'wacc',
                'terminal_growth_rate',
            }
            if field_name in pct_fields:
                if val > 1.0 and val <= 100.0:
                    return val / 100.0
                if val > 100.0:
                    return val / 10000.0  # Handle basis-point-like values
            return val

        # Transform frontend format: { "forecast_base_case_sales_volume_growth_0": {value, source}, "dcf_wacc": {value, source} }
        # to flat dict: { "revenue_growth_year_1": 0.05, "wacc": 0.08 }
        transformed_confirmed = {}
        transformed_overrides = {}
        for key, val in frontend_confirmed.items():
            # Extract the actual value from {value, source} wrapper
            if isinstance(val, dict) and 'value' in val:
                actual_value = val['value']
                source = val.get('source', 'manual')
            else:
                actual_value = val
                source = 'manual'

            # Transform forecast_* keys to Step 9 parameter names
            if key.startswith('forecast_'):
                # Format: forecast_{scenario}_{field}_{yearIndex}
                # e.g. forecast_base_case_revenue_growth_0
                # We need to extract scenario, field, and year_idx
                # Strategy: find the last part (year_idx), then split the rest
                without_prefix = key[len('forecast_'):]  # e.g. "base_case_revenue_growth_0"
                last_underscore = without_prefix.rfind('_')
                if last_underscore > 0:
                    year_part = without_prefix[last_underscore+1:]
                    rest = without_prefix[:last_underscore]  # e.g. "base_case_revenue_growth"
                    
                    # The scenario is the first word after forecast_
                    # The field is everything after scenario, before year_idx
                    # Try to find scenario by checking known scenarios
                    known_scenarios = ['best_case', 'base_case', 'worst_case']
                    field = rest
                    scenario = 'base_case'  # default
                    for s in known_scenarios:
                        if rest.startswith(s + '_'):
                            scenario = s
                            field = rest[len(s)+1:]  # Remove "scenario_"
                            break
                    
                    try:
                        year_idx = int(year_part)
                    except ValueError:
                        continue
                    
                    # Map to Step 9 parameter names
                    param_map = {
                        'revenue_growth': 'revenue_growth_year',
                        'sales_volume_growth': 'revenue_growth_year',
                        'inflation_rate': 'revenue_price_growth_year',
                        'opex_growth': 'opex_growth_year',
                        'receivables_days': 'receivables_days',
                        'inventory_days': 'inventory_days',
                        'payables_days': 'payables_days',
                        'tax_rate': 'tax_rate',
                        # capital_expenditure is an ABSOLUTE $ value, not a % of revenue
                        # Store as-is; step 9 will derive capex_percent_revenue from it + revenue
                        'capital_expenditure': 'capital_expenditure',
                    }
                    if field in param_map:
                        if 'year' in param_map[field]:
                            param_name = f"{param_map[field]}_{year_idx + 1}"
                        else:
                            param_name = param_map[field]
                        transformed_confirmed[param_name] = actual_value
                        if source == 'manual':
                            transformed_overrides[param_name] = actual_value
            elif key.startswith('dcf_'):
                dcf_field = key.replace('dcf_', '')
                # Map frontend DCF field names to Step 9 parameter names
                dcf_param_map = {
                    'risk_free_rate': 'risk_free_rate',
                    'equity_risk_premium': 'market_risk_premium',
                    'beta': 'beta',
                    'cost_of_debt': 'cost_of_debt',
                    'wacc': 'wacc',
                    'terminal_growth_rate': 'terminal_growth_rate',
                    'terminal_ebitda_multiple': 'terminal_ebitda_multiple',
                    'useful_life_existing': 'useful_life_existing',
                }
                if dcf_field in dcf_param_map:
                    param_name = dcf_param_map[dcf_field]
                    transformed_confirmed[param_name] = _normalize_pct(actual_value, param_name)
                    if source == 'manual':
                        transformed_overrides[param_name] = _normalize_pct(actual_value, param_name)
            else:
                # Pass through any other keys directly
                transformed_confirmed[key] = actual_value
                if source == 'manual':
                    transformed_overrides[key] = actual_value

        # Build step8_final_inputs dict expected by Step9ConfirmationProcessor
        step8_final_inputs = {
            'confirmed_values': transformed_confirmed,
            'manual_overrides': transformed_overrides,
            'ai_suggestions': _flatten_ai_suggestions(step8_ai_suggestions),
        }

        # Also store the raw (unwrapped) frontend keys so Step 10 can build ScenarioDrivers
        # Step 10 reads keys like "forecast_base_case_revenue_growth_0", "dcf_wacc", etc.
        raw_frontend_confirmed = {}
        for key, val in frontend_confirmed.items():
            if isinstance(val, dict) and 'value' in val:
                raw_frontend_confirmed[key] = val['value']
            else:
                raw_frontend_confirmed[key] = val
        step8_final_inputs['raw_frontend_confirmed'] = raw_frontend_confirmed

        # ── Market-aware routing: delegate to VN or INT processor ──────────
        if market == "vietnam":
            step9_output = await vn_step9_processor.process_confirmation(
                session_id=request.session_id,
                ticker=ticker,
                valuation_model=method,
                step6_data=step6_data,
                step7_data=step7_data if step7_data else None,
                step8_final_inputs=step8_final_inputs,
                market=market,
                complete_statements=complete_statements if complete_statements else None,
            )
        else:
            # Use Step9ConfirmationProcessor to consolidate all inputs
            # Pass complete_statements (merged Step 6+7) as the primary historical data source
            # Also pass raw step6_data for market_data and peer data
            step9_output = await step9_processor.process_confirmation(
                session_id=request.session_id,
                ticker=ticker,
                valuation_model=method,
                step6_data=step6_data,
                step7_data=step7_data if step7_data else None,
                step8_final_inputs=step8_final_inputs,
                market=market,
                complete_statements=complete_statements if complete_statements else None,
            )

        # Validate Step 9 output
        if not step9_output.ready_for_valuation:
            error_msg = f"Step 9 validation failed: {', '.join(step9_output.errors)}"
            raise HTTPException(status_code=400, detail=error_msg)

        # Store Step 9 output in session - this is what Step 10 will use
        step9_output_dict = step9_output.model_dump() if hasattr(step9_output, 'model_dump') else step9_output.dict()
        # Include raw (unwrapped) frontend keys so Step 10 can build ScenarioDrivers
        # Step 10 reads keys like "forecast_base_case_revenue_growth_0", "dcf_wacc", etc.
        step9_output_dict['raw_confirmed_assumptions'] = step8_final_inputs.get('raw_frontend_confirmed', {})
        
        # Store the full DCF engine output for Step 10 reuse (avoids double calculation)
        # Step 10 reads this to extract UFCF/DCF/valuation schedules
        if step9_output.dcf_engine_output:
            step9_output_dict['dcf_engine_output'] = step9_output.dcf_engine_output
        
        session_service.update_session_data(
            request.session_id,
            "step9_confirmed_outputs",
            step9_output_dict,
            market=market,
            method=method.lower(),
        )

        session_service.update_session_step(
            request.session_id,
            step_number=9,
            market=market,
            method=method.lower(),
        )

        # Log confirmation summary
        logger.info(
            f"Step 9 confirmation completed for {ticker} ({method}, {market}): "
            f"{step9_output.total_parameters_confirmed} parameters confirmed, "
            f"{step9_output.parameters_manually_overridden} manually overridden, "
            f"ready for Step 10: {step9_output.ready_for_valuation}"
            f"{' with building block schedules' if step9_output.calculated_schedules else ''}"
        )

        return UnifiedStep9Response(
            status="assumptions_confirmed",
            session_id=request.session_id,
            method=method,
            market=market,
            all_categories_confirmed=True,
            confirmed_assumptions=step9_output.model_specific_inputs.model_dump() if hasattr(step9_output.model_specific_inputs, 'model_dump') else (step9_output.model_specific_inputs if isinstance(step9_output.model_specific_inputs, dict) else {}),
            ready_for_valuation=step9_output.ready_for_valuation,
            validation_errors=step9_output.errors if hasattr(step9_output, 'errors') else [],
            message=f"Assumptions confirmed successfully. {len(step9_output.warnings)} warnings." if step9_output.warnings else "Assumptions confirmed successfully.",
            calculated_schedules=step9_output.calculated_schedules,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Step 9 confirmation error: {type(e).__name__}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


class CalculateBuildingBlocksRequest(BaseModel):
    """Request to recalculate DCF building block schedules."""
    session_id: str
    method: ValuationMethod = Field(default=ValuationMethod.DCF)
    market: MarketType = Field(default=MarketType.INTERNATIONAL)
    scenario: str = Field(default="base_case")
    assumption_overrides: Optional[Dict[str, Any]] = None


@router.post("/step-9-calculate-building-blocks")
async def calculate_building_blocks_endpoint(request: CalculateBuildingBlocksRequest):
    """
    Calculate DCF building block schedules from current session data + overrides.

    ALWAYS works — no dependency on step9_confirmed_outputs.
    Reads Steps 6/7/8 session data, applies any assumption_overrides from the
    frontend's current field values, runs DCF Engine building blocks, and returns
    per-schedule success/error status.

    Called by the "🧮 Calculate" button on Step 9. The user can click this
    repeatedly after editing any field to preview projected schedules.

    Does NOT run UFCF/DCF/valuation — those are deferred to Step 10.
    """
    try:
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        market = request.market.value if isinstance(request.market, MarketType) else request.market.lower()
        method = request.method.value if isinstance(request.method, ValuationMethod) else request.method.upper()

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # ── Build DCF inputs from frontend data ONLY ────────────────────────
        # The frontend has ALL data mapped from Steps 6/7/8 into its form
        # fields. assumption_overrides contains the frontend's full DCFInputs
        # state — no session reads needed.
        frontend_inputs = request.assumption_overrides or {}

        # ── Vietnamese market: use VN schedule builder ─────────────────────
        if market == "vietnam":
            from app.services.vietnamese.vn_schedule_builder import build_vn_schedules

            # Get historical financials from session (needed for schedule builder)
            historical_financials = {}
            complete_stmts = session_service.get_session_value(
                request.session_id, "complete_statements", {},
                market=market, method=method.lower(),
            )
            if complete_stmts:
                historical_financials = complete_stmts.get("historical_financials", {})
            if not historical_financials:
                step6_data = session_service.get_session_value(
                    request.session_id, "step6_data", {},
                    market=market, method=method.lower(),
                )
                historical_financials = step6_data.get("historical_financials", {}) if step6_data else {}

            # Merge session step8 data with frontend overrides
            step8_session = session_service.get_session_value(
                request.session_id, "step8_assumptions", {},
                market=market, method=method.lower(),
            )
            confirmed_params = {}
            if step8_session:
                # Extract confirmed values from session
                for cat in (step8_session.get("revenue_drivers", {}) or {}).get("assumptions", []):
                    if cat.get("final_value") is not None:
                        confirmed_params[cat["metric"]] = cat["final_value"]
                for cat in (step8_session.get("cost_margins", {}) or {}).get("assumptions", []):
                    if cat.get("final_value") is not None:
                        confirmed_params[cat["metric"]] = cat["final_value"]
                for cat in (step8_session.get("working_capital", {}) or {}).get("assumptions", []):
                    if cat.get("final_value") is not None:
                        confirmed_params[cat["metric"]] = cat["final_value"]
                for cat in (step8_session.get("wacc_components", {}) or {}).get("assumptions", []):
                    if cat.get("final_value") is not None:
                        confirmed_params[cat["metric"]] = cat["final_value"]
                for cat in (step8_session.get("terminal_value", {}) or {}).get("assumptions", []):
                    if cat.get("final_value") is not None:
                        confirmed_params[cat["metric"]] = cat["final_value"]

            # Frontend overrides take priority
            for key, val in frontend_inputs.items():
                if val is not None:
                    confirmed_params[key] = val['value'] if isinstance(val, dict) and 'value' in val else val

            # Get market context from session
            market_context = session_service.get_session_value(
                request.session_id, "market_context", {},
                market=market, method=method.lower(),
            ) or {}

            building_blocks_dict = build_vn_schedules(
                confirmed_params=confirmed_params,
                historical_financials=historical_financials,
                market_context=market_context,
            )
            # VN builder returns a plain dict (no .wacc attribute), use dict keys
            building_blocks_wacc = building_blocks_dict.get('wacc', 0)
            building_blocks_vflags = building_blocks_dict.get('validation_flags', {})
            building_blocks_warnings = building_blocks_dict.get('warnings', [])
        else:
            # ── International market: use INT DCFEngine ─────────────────────
            from app.services.international.dcf_input_builder import build_dcf_inputs_from_frontend
            from app.services.international.dcf_engine import DCFEngine

            dcf_inputs = build_dcf_inputs_from_frontend(frontend_inputs)

            engine = DCFEngine(dcf_inputs)
            building_blocks = engine.calculate_building_blocks(request.scenario)
            building_blocks_dict = building_blocks.to_dict()
            building_blocks_wacc = building_blocks.wacc
            building_blocks_vflags = building_blocks.validation_flags
            building_blocks_warnings = building_blocks.warnings

        # ── Build per-schedule status ───────────────────────────────────────
        schedules = building_blocks_dict.get('supporting_schedules', {})
        schedule_status = {}
        for schedule_name, schedule_data in schedules.items():
            if schedule_data and isinstance(schedule_data, dict):
                # Check if the schedule has actual data (not all zeros/empty)
                has_data = any(
                    v for v in schedule_data.values()
                    if isinstance(v, list) and any(x != 0 for x in v)
                ) or any(
                    v for k, v in schedule_data.items()
                    if k != 'years' and isinstance(v, (int, float)) and v != 0
                )
                schedule_status[schedule_name] = "success" if has_data else "empty"
            else:
                schedule_status[schedule_name] = "error"

        # Check CFS and BS separately (top-level keys)
        cfs = building_blocks_dict.get('cash_flow_statement', {})
        bs = building_blocks_dict.get('balance_sheet', {})
        schedule_status['cash_flow_statement'] = "success" if cfs and any(
            isinstance(v, list) and any(x != 0 for x in v)
            for v in cfs.values()
        ) else "empty"
        schedule_status['balance_sheet'] = "success" if bs and any(
            isinstance(v, list) and any(x != 0 for x in v)
            for v in bs.values()
        ) else "empty"

        all_schedules_ok = all(v == "success" for v in schedule_status.values())

        # Store building blocks in session for Step 10 reuse
        session_service.update_session_data(
            request.session_id,
            "dcf_building_blocks",
            building_blocks_dict,
            market=market,
            method=method.lower(),
        )

        logger.info(
            f"Building blocks calculated for {ticker} ({method}, {market}): "
            f"WACC={building_blocks_wacc:.4f}, all_ok={all_schedules_ok}"
        )

        return {
            "status": "success",
            "session_id": request.session_id,
            "method": method,
            "market": market,
            "calculated_schedules": schedules,
            "cash_flow_statement": cfs,
            "balance_sheet": bs,
            "wacc_calculation": building_blocks_dict.get('wacc_calculation', {}),
            # Full-period schedules (historical + forecast) — top-level in to_dict()
            "interest_schedule": building_blocks_dict.get('interest_schedule', {}),
            "historical_references": building_blocks_dict.get('historical_references', {}),
            "full_working_capital": building_blocks_dict.get('full_working_capital', {}),
            # Debt & Equity schedules — top-level in to_dict()
            "debt_schedule_part1": building_blocks_dict.get('debt_schedule_part1', {}),
            "debt_schedule_part2": building_blocks_dict.get('debt_schedule_part2', {}),
            "equity_schedule": building_blocks_dict.get('equity_schedule', {}),
            # Period labels and metadata
            "metadata": building_blocks_dict.get('metadata', {}),
            "schedule_status": schedule_status,
            "all_schedules_ok": all_schedules_ok,
            "validation_flags": building_blocks_vflags,
            "warnings": building_blocks_warnings,
            "stored_in_session": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Building blocks calculation error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

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
        scenario = request.scenario if hasattr(request, 'scenario') else 'base_case'
        
        # Read raw confirmed_assumptions from session (contains ALL scenario forecast drivers)
        # Frontend saves keys like: forecast_best_case_sales_volume_growth_0, forecast_base_case_*, etc.
        raw_confirmed = session_service.get_session_value(
            request.session_id,
            "confirmed_assumptions",
            {},
            market=market,
            method=method.lower()
        )
        
        # Check if Step 9 stored a pre-computed DCF engine output (avoids double calculation)
        stored_dcf_output = step9_confirmed_outputs.get('dcf_engine_output')
        
        confirmed_assumptions = {
            'model_specific_inputs': model_specific_inputs,
            'historical_financials_summary': historical_summary,
            'market_context': market_context,
            'confirmed_parameters': step9_confirmed_outputs.get('confirmed_parameters', []),
            'validation_status': step9_confirmed_outputs.get('validation_status', 'passed'),
            'warnings': step9_confirmed_outputs.get('warnings', []),
            'scenario': scenario,
            'raw_confirmed_assumptions': raw_confirmed,
        }

        # ── Check for stored building blocks (new Phase 1 split path) ─────
        stored_building_blocks = session_service.get_session_value(
            request.session_id,
            "dcf_building_blocks",
            None,
            market=market,
            method=method.lower()
        )

        # ── Market-aware routing: delegate to VN or INT processor ──────────
        if market == "vietnam":
            result = await vn_step10_processor.run_valuation(
                ticker=ticker,
                model=method,
                assumptions=confirmed_assumptions,
            )
        elif method.upper() == 'DCF':
            if not stored_building_blocks:
                raise HTTPException(
                    status_code=400,
                    detail="No DCF building blocks found. Please complete Step 9 (Calculate Building Blocks) first."
                )
            # Use pre-computed building blocks from Step 9
            from app.services.international.dcf_input_builder import extract_dcf_inputs
            dcf_inputs_dict = extract_dcf_inputs(confirmed_assumptions)
            result = await dcf_proc.run_valuation_with_building_blocks(
                ticker=ticker,
                building_blocks=stored_building_blocks,
                dcf_inputs_dict=dcf_inputs_dict,
                scenario=scenario,
            )
        else:
            # DuPont and COMPS — route through Step10ValuationProcessor
            result = await step10_processor.run_valuation(
                ticker=ticker,
                model=method,
                assumptions=confirmed_assumptions,
            )

        # result is a dict with keys: valuation_summary, detailed_outputs,
        # sensitivity_analysis, scenario_analysis, confidence_level,
        # key_assumptions_summary, warnings

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

        # Safely extract fields from result dict
        valuation_summary = result.get('valuation_summary', {}) if isinstance(result, dict) else {}
        detailed_outputs = result.get('detailed_outputs', {}) if isinstance(result, dict) else {}
        sensitivity = result.get('sensitivity_analysis') if isinstance(result, dict) else None
        scenario = result.get('scenario_analysis') if isinstance(result, dict) else None
        confidence = result.get('confidence_level', 'medium') if isinstance(result, dict) else 'medium'
        key_assumptions = result.get('key_assumptions_summary', {}) if isinstance(result, dict) else {}
        warnings_list = result.get('warnings', []) if isinstance(result, dict) else []

        # Extract calculated_schedules from detailed_outputs (DCFEngine.to_dict() output)
        # Step 10 shows UFCF / DCF / Valuation schedules (Outputs sheet equivalent)
        # Building block schedules (IS, BS, CFS, WC, Dep, etc.) are in Step 9.
        calc_schedules = None
        if isinstance(detailed_outputs, dict) and method.upper() == 'DCF':
            # Start with building block schedules from Step 9 (stored in session)
            bb_schedules = {}
            if stored_building_blocks and isinstance(stored_building_blocks, dict):
                bb_schedules = stored_building_blocks.get('supporting_schedules', {})
            
            calc_schedules = {
                # ── Building block schedules (from Step 9) ──
                'supporting_schedules': bb_schedules,
                'cash_flow_statement': stored_building_blocks.get('cash_flow_statement', {}) if stored_building_blocks else {},
                'balance_sheet': stored_building_blocks.get('balance_sheet', {}) if stored_building_blocks else {},
                'income_statement': bb_schedules.get('income_statement', {}),
                'working_capital': bb_schedules.get('working_capital', {}),
                'depreciation_schedule': bb_schedules.get('depreciation_schedule', {}),
                'tax_levered': bb_schedules.get('tax_levered', {}),
                'debt_schedule_part1': stored_building_blocks.get('debt_schedule_part1', {}) if stored_building_blocks else {},
                'debt_schedule_part2': stored_building_blocks.get('debt_schedule_part2', {}) if stored_building_blocks else {},
                'equity_schedule': stored_building_blocks.get('equity_schedule', {}) if stored_building_blocks else {},
                # ── Valuation-specific schedules (from Step 10) ──
                'ufcf': detailed_outputs.get('supporting_schedules', {}).get('ufcf', {}),
                'ufcf_3_methods': detailed_outputs.get('ufcf_3_methods'),
                'intrinsic_extracts': detailed_outputs.get('intrinsic_extracts'),
                'dcf_details': detailed_outputs.get('dcf_details'),
                'npv_xnpv': detailed_outputs.get('npv_xnpv'),
                'sensitivity_perpetuity': detailed_outputs.get('sensitivity_perpetuity'),
                'sensitivity_multiple': detailed_outputs.get('sensitivity_multiple'),
                'main_outputs': detailed_outputs.get('main_outputs'),
                'wacc_calculation': detailed_outputs.get('wacc_calculation'),
            }

        # Parse sensitivity_analysis if it's a dict (not a Pydantic model)
        parsed_sensitivity = None
        if sensitivity and isinstance(sensitivity, dict):
            try:
                parsed_sensitivity = SensitivityAnalysis(**sensitivity)
            except Exception:
                parsed_sensitivity = None

        return UnifiedStep10Response(
            status="success",
            session_id=request.session_id,
            method=method,
            market=market,
            ticker=ticker,
            company_name=session.get("company_name", ticker),
            valuation_summary=valuation_summary,
            detailed_outputs=detailed_outputs,
            calculated_schedules=calc_schedules,
            sensitivity_analysis=parsed_sensitivity,
            scenario_analysis=scenario,
            confidence_level=confidence,
            key_assumptions_summary=key_assumptions,
            warnings=warnings_list,
            calculation_timestamp=datetime.now(),
            message=f"Valuation completed successfully for {method} ({market}) using Step 9 confirmed inputs"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step 10 valuation error: {e}")
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
