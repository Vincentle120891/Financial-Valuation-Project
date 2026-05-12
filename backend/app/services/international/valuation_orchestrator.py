"""
Valuation Orchestrator Service - Parallel Multi-Method Execution

This service provides concurrent execution of multiple valuation methods.
It accepts a list of methods and executes them in parallel using asyncio.gather,
then aggregates results into a unified response.

SUPPORTS:
- 3 Valuation Methods: DCF, DuPont, COMPS
- 2 Market Versions: International, Vietnam
- True parallel processing with asyncio.gather
- Unified response containing all method results
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.session_service import session_service
from app.services.international.step5_required_inputs_processor import Step5RequiredInputsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.step7_historical_data_processor import Step7HistoricalDataProcessor
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor

logger = logging.getLogger(__name__)


class MethodExecutionResult:
    """Result of executing a single valuation method."""
    
    def __init__(
        self,
        method: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.method = method.upper()
        self.status = status  # 'success', 'error', 'skipped'
        self.data = data or {}
        self.result = result or {}
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "status": self.status,
            "data": self.data,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp
        }


class ValuationOrchestrator:
    """
    Orchestrates parallel execution of multiple valuation methods.
    
    USAGE:
    ```python
    orchestrator = ValuationOrchestrator()
    results = await orchestrator.execute_multi_method_valuation(
        session_id="xxx",
        methods=["dcf", "dupont", "comps"],
        market="international"
    )
    ```
    """
    
    def __init__(self):
        # Initialize processors (shared across all methods)
        self.step5_processor = Step5RequiredInputsProcessor()
        self.step6_processor = Step6DataReviewProcessor()
        self.step7_processor = Step7HistoricalDataProcessor()
        self.step8_processor = Step8ManualOverridesProcessor()
        self.step10_processor = Step10ValuationProcessor()
    
    async def execute_multi_method_valuation(
        self,
        session_id: str,
        methods: List[str],
        market: str = "international",
        start_step: int = 4
    ) -> Dict[str, Any]:
        """
        Execute multiple valuation methods in parallel.
        
        Args:
            session_id: Session identifier
            methods: List of methods to execute ['dcf', 'dupont', 'comps']
            market: Market version ('international' or 'vietnam')
            start_step: Starting step (4=model selection, 5=prepare inputs, etc.)
            
        Returns:
            Unified response with results from all methods
        """
        logger.info(f"Starting multi-method valuation: methods={methods}, market={market}")
        
        # Normalize methods
        normalized_methods = [m.lower() for m in methods]
        
        # Validate session exists
        session = session_service.get_session_data(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found",
                "results": []
            }
        
        # Create tasks for each method
        tasks = []
        for method in normalized_methods:
            task = self._execute_single_method(
                session_id=session_id,
                method=method,
                market=market,
                start_step=start_step
            )
            tasks.append(task)
        
        # Execute all methods concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Multi-method execution failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "results": []
            }
        
        # Process results
        method_results = []
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results):
            method = normalized_methods[i]
            
            if isinstance(result, Exception):
                logger.error(f"Method {method} failed with exception: {result}")
                method_results.append(MethodExecutionResult(
                    method=method,
                    status="error",
                    error=str(result)
                ).to_dict())
                error_count += 1
            elif isinstance(result, MethodExecutionResult):
                if result.status == "success":
                    success_count += 1
                else:
                    error_count += 1
                method_results.append(result.to_dict())
            else:
                method_results.append(result)
        
        # Generate unified summary
        summary = self._generate_unified_summary(method_results, session)
        
        return {
            "status": "partial_success" if error_count > 0 and success_count > 0 else ("success" if success_count > 0 else "error"),
            "market": market,
            "methods_requested": normalized_methods,
            "methods_completed": [r["method"] for r in method_results if r["status"] == "success"],
            "methods_failed": [r["method"] for r in method_results if r["status"] == "error"],
            "summary": summary,
            "results": method_results,
            "execution_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_single_method(
        self,
        session_id: str,
        method: str,
        market: str,
        start_step: int
    ) -> MethodExecutionResult:
        """
        Execute a single valuation method through all steps.
        
        This runs the complete workflow for one method:
        - Step 4: Select model
        - Step 5: Prepare inputs
        - Step 6: Fetch API data
        - Step 7: Retrieve historical data
        - Step 8: Generate AI assumptions (optional, can be manual)
        - Step 9: Confirm assumptions (uses defaults if not confirmed)
        - Step 10: Run valuation
        
        Args:
            session_id: Session identifier
            method: Single method ('dcf', 'dupont', 'comps')
            market: Market version
            start_step: Starting step number
            
        Returns:
            MethodExecutionResult with status and data
        """
        method_upper = method.upper()
        logger.info(f"Executing method {method_upper} for {market}")
        
        try:
            # Step 4: Select model
            session_service.update_valuation_status(
                session_id, market=market, method=method, status="selected"
            )
            session_service.update_session_data(
                session_id, "selected_model", method_upper,
                market=market, method=method
            )
            
            # Step 5: Prepare inputs
            ticker = session_service.get_session_value(session_id, "ticker", "UNKNOWN")
            peer_tickers = session_service.get_session_value(session_id, "peer_tickers", [])
            
            step5_result = self.step5_processor.process_data_retrieval_inputs(
                ticker=ticker,
                valuation_model=method_upper,
                peer_tickers=peer_tickers
            )
            
            # Step 6: Fetch API data
            retrieved_assumptions = session_service.get_session_value(
                session_id, "retrieved_assumptions", {}
            )
            
            step6_result = await self.step6_processor.process_data_review(
                ticker=ticker,
                market=market,
                valuation_model=method_upper,
                retrieved_assumptions=retrieved_assumptions
            )
            
            # Store step 6 data
            step6_dict = step6_result.model_dump(mode='json') if hasattr(step6_result, 'model_dump') else step6_result
            session_service.update_session_data(
                session_id, "financial_data", step6_dict,
                market=market, method=method
            )
            session_service.update_session_step(session_id, step_number=6, market=market, method=method)
            
            # Step 7: Retrieve historical data
            step7_result = await self.step7_processor.retrieve_historical_data(
                ticker=ticker,
                company_name=session_service.get_session_value(session_id, "company_name", ticker),
                valuation_model=method_upper,
                market=market,
                step6_financial_data=step6_dict
            )
            
            # Store step 7 data
            session_service.update_session_data(
                session_id, "historical_data_gaps_filled", step7_result,
                market=market, method=method
            )
            session_service.update_session_step(session_id, step_number=7, market=market, method=method)
            
            # Step 8 & 9: Generate and confirm assumptions
            # For automated flow, we generate default assumptions
            step8_result = await self.step8_processor.generate_all_assumptions(
                session_id=session_id,
                ticker=ticker,
                valuation_model=method_upper,
                market=market
            )
            
            # Store AI suggestions
            session_service.update_session_data(
                session_id, "ai_suggestions", step8_result,
                market=market, method=method
            )
            session_service.update_session_step(session_id, step_number=8, market=market, method=method)
            
            # Auto-confirm assumptions (use AI suggestions as confirmed)
            if hasattr(step8_result, 'assumptions'):
                confirmed = step8_result.assumptions
            elif isinstance(step8_result, dict) and 'assumptions' in step8_result:
                confirmed = step8_result['assumptions']
            else:
                confirmed = step8_result
            
            session_service.update_session_data(
                session_id, "confirmed_assumptions", confirmed,
                market=market, method=method
            )
            session_service.update_session_step(session_id, step_number=9, market=market, method=method)
            
            # Step 10: Run valuation
            valuation_result = await self.step10_processor.run_valuation(
                ticker=ticker,
                model=method_upper,
                assumptions=confirmed
            )
            
            # Store valuation results (async-safe for parallel execution)
            await session_service.save_valuation_results(
                session_id=session_id,
                market=market,
                method=method,
                results=valuation_result
            )
            session_service.update_valuation_status(
                session_id, market=market, method=method, status="completed"
            )
            
            logger.info(f"Method {method_upper} completed successfully")
            
            return MethodExecutionResult(
                method=method,
                status="success",
                data={
                    "step5": step5_result.message if hasattr(step5_result, 'message') else "Inputs prepared",
                    "step6": "Data fetched",
                    "step7": f"{step7_result.total_gaps_filled}/{step7_result.total_gaps_found} gaps filled" if hasattr(step7_result, 'total_gaps_filled') else "Historical data retrieved",
                    "step8": "Assumptions generated",
                },
                result=valuation_result if hasattr(valuation_result, 'model_dump') else valuation_result
            )
            
        except Exception as e:
            logger.error(f"Method {method_upper} failed: {e}", exc_info=True)
            session_service.update_valuation_status(
                session_id, market=market, method=method, status="error"
            )
            
            return MethodExecutionResult(
                method=method,
                status="error",
                error=str(e)
            )
    
    def _generate_unified_summary(
        self,
        method_results: List[Dict[str, Any]],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a unified summary across all methods.
        
        Aggregates key metrics from all completed methods for easy comparison.
        """
        summary = {
            "ticker": session.get("ticker", "UNKNOWN"),
            "market": session.get("market", "international"),
            "methods_executed": len([r for r in method_results if r.get("status") == "success"]),
            "valuation_comparison": {},
            "recommendations": {}
        }
        
        # Extract key values from each method
        for result in method_results:
            if result.get("status") != "success":
                continue
            
            method = result.get("method", "UNKNOWN").upper()
            result_data = result.get("result", {})
            
            # Extract fair value from different result structures
            fair_value = None
            if isinstance(result_data, dict):
                # Try different possible paths
                if "valuation_result" in result_data:
                    fair_value = result_data["valuation_result"].get("fair_value_per_share")
                elif "fair_value_per_share" in result_data:
                    fair_value = result_data.get("fair_value_per_share")
                elif "blended_value" in result_data:
                    fair_value = result_data.get("blended_value")
                elif "value" in result_data:
                    fair_value = result_data.get("value")
            
            if fair_value is not None:
                summary["valuation_comparison"][method] = {
                    "fair_value": fair_value,
                    "full_result": result_data
                }
        
        # Generate cross-method insights
        if len(summary["valuation_comparison"]) >= 2:
            values = [v["fair_value"] for v in summary["valuation_comparison"].values() if v.get("fair_value")]
            if values:
                summary["cross_method_analysis"] = {
                    "min_value": min(values),
                    "max_value": max(values),
                    "avg_value": sum(values) / len(values),
                    "spread": max(values) - min(values),
                    "spread_pct": ((max(values) - min(values)) / min(values) * 100) if min(values) > 0 else 0
                }
        
        return summary
    
    async def run_step_for_multiple_methods(
        self,
        session_id: str,
        step_number: int,
        methods: List[str],
        market: str = "international",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run a specific step for multiple methods in parallel.
        
        Useful for incremental execution where user wants to proceed step-by-step
        but for all selected methods simultaneously.
        
        Args:
            session_id: Session identifier
            step_number: Step to execute (4-10)
            methods: List of methods
            market: Market version
            **kwargs: Additional step-specific parameters
            
        Returns:
            Results from all methods
        """
        logger.info(f"Running step {step_number} for methods: {methods}")
        
        normalized_methods = [m.lower() for m in methods]
        
        # Create tasks for each method
        tasks = []
        for method in normalized_methods:
            task = self._run_single_step(
                session_id=session_id,
                step_number=step_number,
                method=method,
                market=market,
                **kwargs
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        aggregated = {
            "step": step_number,
            "market": market,
            "methods": normalized_methods,
            "results": {}
        }
        
        for i, result in enumerate(results):
            method = normalized_methods[i]
            if isinstance(result, Exception):
                aggregated["results"][method] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                aggregated["results"][method] = result
        
        return aggregated
    
    async def _run_single_step(
        self,
        session_id: str,
        step_number: int,
        method: str,
        market: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a single step for one method."""
        method_upper = method.upper()
        
        try:
            if step_number == 4:
                # Model selection
                session_service.update_valuation_status(
                    session_id, market=market, method=method, status="selected"
                )
                return {"status": "success", "message": f"{method_upper} model selected"}
            
            elif step_number == 5:
                # Prepare inputs
                ticker = session_service.get_session_value(session_id, "ticker", "UNKNOWN")
                result = self.step5_processor.process_data_retrieval_inputs(
                    ticker=ticker,
                    valuation_model=method_upper,
                    peer_tickers=kwargs.get('peer_tickers', [])
                )
                return {"status": "success", "inputs": result}
            
            elif step_number == 6:
                # Fetch data
                ticker = session_service.get_session_value(session_id, "ticker", "UNKNOWN")
                retrieved_assumptions = session_service.get_session_value(
                    session_id, "retrieved_assumptions", {}
                )
                result = await self.step6_processor.process_data_review(
                    ticker=ticker,
                    market=market,
                    valuation_model=method_upper,
                    retrieved_assumptions=retrieved_assumptions
                )
                result_dict = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result
                session_service.update_session_data(
                    session_id, "financial_data", result_dict,
                    market=market, method=method
                )
                return {"status": "success", "data": result_dict}
            
            elif step_number == 7:
                # Historical data
                ticker = session_service.get_session_value(session_id, "ticker", "UNKNOWN")
                financial_data = session_service.get_session_value(
                    session_id, "financial_data", {},
                    market=market, method=method
                )
                result = await self.step7_processor.retrieve_historical_data(
                    ticker=ticker,
                    company_name=session_service.get_session_value(session_id, "company_name", ticker),
                    valuation_model=method_upper,
                    market=market,
                    step6_financial_data=financial_data
                )
                session_service.update_session_data(
                    session_id, "historical_data_gaps_filled", result,
                    market=market, method=method
                )
                return {"status": "success", "historical_data": result}
            
            elif step_number == 8:
                # Generate assumptions
                ticker = session_service.get_session_value(session_id, "ticker", "UNKNOWN")
                result = await self.step8_processor.generate_all_assumptions(
                    session_id=session_id,
                    ticker=ticker,
                    valuation_model=method_upper,
                    market=market
                )
                session_service.update_session_data(
                    session_id, "ai_suggestions", result,
                    market=market, method=method
                )
                return {"status": "success", "assumptions": result}
            
            elif step_number == 9:
                # Confirm assumptions (auto-confirm for now)
                ai_suggestions = session_service.get_session_value(
                    session_id, "ai_suggestions", {},
                    market=market, method=method
                )
                session_service.update_session_data(
                    session_id, "confirmed_assumptions", ai_suggestions,
                    market=market, method=method
                )
                return {"status": "success", "confirmed": ai_suggestions}
            
            elif step_number == 10:
                # Run valuation
                ticker = session_service.get_session_value(session_id, "ticker", "UNKNOWN")
                confirmed = session_service.get_session_value(
                    session_id, "confirmed_assumptions", {},
                    market=market, method=method
                )
                result = await self.step10_processor.run_valuation(
                    ticker=ticker,
                    model=method_upper,
                    assumptions=confirmed
                )
                await session_service.save_valuation_results(
                    session_id=session_id,
                    market=market,
                    method=method,
                    results=result
                )
                return {"status": "success", "valuation": result}
            
            else:
                return {"status": "error", "error": f"Unknown step number: {step_number}"}
                
        except Exception as e:
            logger.error(f"Step {step_number} for {method_upper} failed: {e}")
            return {"status": "error", "error": str(e)}


# Singleton instance
orchestrator = ValuationOrchestrator()
