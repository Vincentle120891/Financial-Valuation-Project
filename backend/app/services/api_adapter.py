"""
API Adapter Layer
Handles fetching, mapping, normalizing, and validating data from external providers.
Separates mapping logic from fetching logic using the Metric Registry.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from app.core.metric_registry import (
    METRIC_REGISTRY, 
    get_metric_definition, 
    get_source_key,
    get_required_metrics_for_method,
    get_calculated_metrics,
    DataType,
    MetricCategory
)

logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    """Raised when data fails validation checks."""
    pass

class APIAdapter:
    """
    Unified adapter for fetching and processing financial data from multiple providers.
    """
    
    def __init__(self, provider: str = "yfinance"):
        """
        Initialize adapter with a specific provider.
        :param provider: 'yfinance', 'alpha_vantage', 'financial_modeling_prep'
        """
        self.provider = provider
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the API client based on provider."""
        # Placeholder for actual client initialization
        # In real implementation:
        # if self.provider == "yfinance": return yfinance
        # if self.provider == "alpha_vantage": return AlphaVantageClient()
        return None
    
    def fetch_raw_data(self, ticker: str, metrics: List[str]) -> Dict[str, Any]:
        """
        Fetch raw data for specific metrics from the provider.
        Returns raw API response without mapping.
        """
        logger.info(f"Fetching raw data for {ticker} from {self.provider}")
        
        if self.provider == "yfinance":
            return self._fetch_yfinance_raw(ticker, metrics)
        elif self.provider == "alpha_vantage":
            return self._fetch_alpha_vantage_raw(ticker, metrics)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _fetch_yfinance_raw(self, ticker: str, metrics: List[str]) -> Dict[str, Any]:
        """Fetch raw data from yfinance."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            
            # Fetch financials
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet
            cashflow = stock.cashflow
            
            # Fetch info
            info = stock.info
            
            # Fetch history
            history = stock.history(period="5y")
            
            return {
                "income_statement": income_stmt.to_dict() if income_stmt is not None else {},
                "balance_sheet": balance_sheet.to_dict() if balance_sheet is not None else {},
                "cash_flow": cashflow.to_dict() if cashflow is not None else {},
                "info": info,
                "history": history.to_dict() if history is not None else {}
            }
        except Exception as e:
            logger.error(f"Error fetching yfinance data for {ticker}: {e}")
            return {}
    
    def _fetch_alpha_vantage_raw(self, ticker: str, metrics: List[str]) -> Dict[str, Any]:
        """Fetch raw data from Alpha Vantage."""
        # Implementation placeholder
        return {}
    
    def map_and_normalize(self, raw_data: Dict[str, Any], ticker: str) -> Dict[str, Any]:
        """
        Map raw API data to internal metric IDs and normalize values.
        Returns structured data with validation status.
        """
        mapped_data = {}
        missing_metrics = []
        calculated_metrics = []
        
        for metric_id, definition in METRIC_REGISTRY.items():
            source_key = get_source_key(metric_id, self.provider)
            
            if not source_key:
                # Check if can be calculated
                if "calculation_formula" in definition:
                    calculated_metrics.append(metric_id)
                    continue
                else:
                    missing_metrics.append(metric_id)
                    continue
            
            # Extract value from raw data
            value = self._extract_value(raw_data, source_key)
            
            if value is None:
                missing_metrics.append(metric_id)
                continue
            
            # Normalize value
            try:
                normalized_value = self._normalize_value(value, definition)
                
                # Validate
                is_valid, error_msg = self._validate_value(normalized_value, definition)
                
                if is_valid:
                    mapped_data[metric_id] = {
                        "value": normalized_value,
                        "source": self.provider,
                        "source_key": source_key,
                        "status": "FETCHED",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    logger.warning(f"Validation failed for {metric_id}: {error_msg}")
                    mapped_data[metric_id] = {
                        "value": None,
                        "source": self.provider,
                        "source_key": source_key,
                        "status": "INVALID",
                        "error": error_msg,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    missing_metrics.append(metric_id)
                    
            except Exception as e:
                logger.error(f"Error processing {metric_id}: {e}")
                mapped_data[metric_id] = {
                    "value": None,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                missing_metrics.append(metric_id)
        
        return {
            "ticker": ticker,
            "data": mapped_data,
            "missing": missing_metrics,
            "calculated": calculated_metrics,
            "provider": self.provider
        }
    
    def _extract_value(self, raw_data: Dict[str, Any], source_key: str) -> Optional[Any]:
        """Extract specific value from raw API response."""
        # Search through different sections of raw data
        sections = ["info", "income_statement", "balance_sheet", "cash_flow"]
        
        for section in sections:
            if section in raw_data:
                section_data = raw_data[section]
                if isinstance(section_data, dict):
                    # Handle time-series data (get most recent)
                    if source_key in section_data:
                        value = section_data[source_key]
                        if isinstance(value, dict):
                            # Get first value (most recent for yfinance)
                            return list(value.values())[0] if value else None
                        return value
        
        return None
    
    def _normalize_value(self, value: Any, definition: Dict[str, Any]) -> Any:
        """Normalize value based on definition rules."""
        if value is None:
            return None
        
        metric_type = definition.get("type", DataType.FLOAT)
        normalization = definition.get("normalization")
        
        # Convert to appropriate type
        try:
            if metric_type in [DataType.FLOAT, DataType.PERCENTAGE]:
                normalized = float(value)
            elif metric_type == DataType.INTEGER:
                normalized = int(float(value))
            else:
                normalized = value
        except (ValueError, TypeError):
            return None
        
        # Apply specific normalization rules
        if normalization == "absolute_value":
            normalized = abs(normalized)
        
        # Convert percentage if needed (some APIs return 0-100, we want 0-1)
        if metric_type == DataType.PERCENTAGE and normalized > 1.0:
            normalized = normalized / 100.0
        
        return normalized
    
    def _validate_value(self, value: Any, definition: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate value against definition rules."""
        if value is None:
            return False, "Value is None"
        
        validation_rules = definition.get("validation", {})
        
        if "min_value" in validation_rules and validation_rules["min_value"] is not None:
            if value < validation_rules["min_value"]:
                return False, f"Value {value} below minimum {validation_rules['min_value']}"
        
        if "max_value" in validation_rules and validation_rules["max_value"] is not None:
            if value > validation_rules["max_value"]:
                return False, f"Value {value} above maximum {validation_rules['max_value']}"
        
        return True, None
    
    def calculate_derived_metrics(self, fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate metrics that have formulas based on fetched data.
        """
        calculated_results = {}
        data_values = {k: v["value"] for k, v in fetched_data.get("data", {}).items() if v.get("value") is not None}
        
        for metric_id in get_calculated_metrics():
            if metric_id in data_values:
                continue  # Already fetched
            
            definition = get_metric_definition(metric_id)
            if not definition or "calculation_formula" not in definition:
                continue
            
            formula = definition["calculation_formula"]
            try:
                # Simple formula evaluation (in production, use safer eval or parser)
                # Replace metric names with values
                safe_formula = formula
                for dep_metric in METRIC_REGISTRY.keys():
                    if dep_metric in safe_formula and dep_metric in data_values:
                        safe_formula = safe_formula.replace(dep_metric, str(data_values[dep_metric]))
                
                calculated_value = eval(safe_formula)
                
                # Validate
                is_valid, error_msg = self._validate_value(calculated_value, definition)
                
                if is_valid:
                    calculated_results[metric_id] = {
                        "value": calculated_value,
                        "source": "CALCULATED",
                        "formula": formula,
                        "status": "CALCULATED",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    logger.warning(f"Calculated value validation failed for {metric_id}: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Error calculating {metric_id}: {e}")
        
        return calculated_results
    
    def process_ticker(self, ticker: str, required_metrics: List[str]) -> Dict[str, Any]:
        """
        Full pipeline: fetch -> map -> normalize -> validate -> calculate
        Returns complete processed data for a ticker.
        """
        # Fetch raw
        raw_data = self.fetch_raw_data(ticker, required_metrics)
        
        if not raw_data:
            return {
                "ticker": ticker,
                "success": False,
                "error": "Failed to fetch raw data",
                "data": {},
                "missing": required_metrics,
                "calculated": []
            }
        
        # Map and normalize
        mapped_result = self.map_and_normalize(raw_data, ticker)
        
        # Calculate derived metrics
        calculated = self.calculate_derived_metrics(mapped_result)
        
        # Merge calculated into data
        mapped_result["data"].update(calculated)
        mapped_result["calculated"] = list(calculated.keys())
        
        # Update missing list (remove those that were calculated)
        mapped_result["missing"] = [
            m for m in mapped_result["missing"] 
            if m not in calculated
        ]
        
        mapped_result["success"] = len(mapped_result["missing"]) == 0
        mapped_result["completeness"] = len(mapped_result["data"]) / len(required_metrics) if required_metrics else 0
        
        return mapped_result


def process_multiple_tickers(tickers: List[str], method: str) -> Dict[str, Any]:
    """
    Process multiple tickers (company + peers) for a specific valuation method.
    Returns aggregated data with peer averages.
    """
    required_metrics = get_required_metrics_for_method(method)
    adapter = APIAdapter(provider="yfinance")
    
    results = {}
    all_data = {}
    
    for ticker in tickers:
        result = adapter.process_ticker(ticker, required_metrics)
        results[ticker] = result
        if result["success"] or result.get("completeness", 0) > 0.5:
            all_data[ticker] = result["data"]
    
    # Calculate peer averages
    peer_averages = {}
    if len(all_data) > 1:
        for metric_id in required_metrics:
            values = []
            for ticker_data in all_data.values():
                if metric_id in ticker_data and ticker_data[metric_id].get("value") is not None:
                    values.append(ticker_data[metric_id]["value"])
            
            if values:
                avg_value = sum(values) / len(values)
                peer_averages[metric_id] = {
                    "value": avg_value,
                    "source": "PEER_AVERAGE",
                    "sample_size": len(values),
                    "status": "CALCULATED",
                    "timestamp": datetime.utcnow().isoformat()
                }
    
    return {
        "individual_results": results,
        "peer_averages": peer_averages,
        "method": method,
        "required_metrics_count": len(required_metrics),
        "processed_tickers_count": len(tickers)
    }
