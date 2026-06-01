"""
API Adapter Layer
Handles fetching, mapping, normalizing, and validating data from external providers.
Separates mapping logic from fetching logic using the Metric Registry.
Integrates Audit Logging and Data Versioning for full traceability.
"""
import logging
import re
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
from app.services.audit_logger import get_audit_logger, TransformationType
from app.services.data_versioning import get_versioning_service

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
            return self._fetch_yfinance_raw(ticker)
        elif self.provider == "alpha_vantage":
            return self._fetch_alpha_vantage_raw(ticker)
        elif self.provider == "fmp":
            return self._fetch_fmp_raw(ticker)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _fetch_yfinance_raw(self, ticker: str) -> Dict[str, Any]:
        """Fetch raw data from yfinance."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)

            # Fetch financials using get_* methods for yfinance v1.3.0+ compatibility
            # These return CamelCase without spaces (e.g., TotalRevenue)
            income_stmt = stock.get_income_stmt()
            balance_sheet = stock.get_balance_sheet()
            cashflow = stock.get_cash_flow()

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

    def _fetch_alpha_vantage_raw(self, ticker: str) -> Dict[str, Any]:
        """Fetch raw data from Alpha Vantage via AlphaVantageService."""
        try:
            from app.services.international.alphavantage_service import AlphaVantageService
            
            av_service = AlphaVantageService()
            if not av_service.api_key:
                logger.warning("AlphaVantage API key not configured, skipping fetch")
                return {}
            
            av_data = av_service.fetch_all_data(ticker, market="international")
            return av_data if av_data else {}
        except Exception as e:
            logger.error(f"Error fetching AlphaVantage data for {ticker}: {e}")
            return {}

    def _fetch_fmp_raw(self, ticker: str) -> Dict[str, Any]:
        """Fetch raw data from Financial Modeling Prep (FMP)."""
        try:
            import os
            import requests
            
            api_key = os.getenv('FMP_API_KEY')
            if not api_key:
                logger.warning("FMP_API_KEY not configured, skipping fetch")
                return {}
            
            base_url = "https://financialmodelingprep.com/api/v3"
            
            # Fetch income statement
            income_resp = requests.get(
                f"{base_url}/income-statement/{ticker}?apikey={api_key}&limit=5",
                timeout=30
            )
            income_stmt = income_resp.json() if income_resp.status_code == 200 else []
            
            # Fetch balance sheet
            balance_resp = requests.get(
                f"{base_url}/balance-sheet-statement/{ticker}?apikey={api_key}&limit=5",
                timeout=30
            )
            balance_sheet = balance_resp.json() if balance_resp.status_code == 200 else []
            
            # Fetch cash flow
            cashflow_resp = requests.get(
                f"{base_url}/cash-flow-statement/{ticker}?apikey={api_key}&limit=5",
                timeout=30
            )
            cashflow = cashflow_resp.json() if cashflow_resp.status_code == 200 else []
            
            # Fetch company profile
            profile_resp = requests.get(
                f"{base_url}/profile/{ticker}?apikey={api_key}",
                timeout=30
            )
            profile = profile_resp.json()[0] if profile_resp.status_code == 200 and profile_resp.json() else {}
            
            # Fetch key metrics
            metrics_resp = requests.get(
                f"{base_url}/key-metrics-ttm/{ticker}?apikey={api_key}",
                timeout=30
            )
            key_metrics = metrics_resp.json()[0] if metrics_resp.status_code == 200 and metrics_resp.json() else {}
            
            return {
                "income_statement": {"columns": [list(d.keys()) for d in income_stmt], "data": income_stmt} if income_stmt else {},
                "balance_sheet": {"columns": [list(d.keys()) for d in balance_sheet], "data": balance_sheet} if balance_sheet else {},
                "cash_flow": {"columns": [list(d.keys()) for d in cashflow], "data": cashflow} if cashflow else {},
                "info": {**profile, **key_metrics},
                "history": {}  # FMP historical data requires separate endpoint
            }
        except Exception as e:
            logger.error(f"Error fetching FMP data for {ticker}: {e}")
            return {}

    def map_and_normalize(self, raw_data: Dict[str, Any], ticker: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Map raw API data to internal metric IDs and normalize values.
        Returns structured data with validation status.
        Integrates audit logging and versioning if session_id provided.
        """
        mapped_data = {}
        missing_metrics = []
        calculated_metrics = []

        # Initialize audit logger and versioning if session provided
        audit_logger = get_audit_logger(session_id) if session_id else None
        versioning = get_versioning_service(session_id) if session_id else None

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

            if value is not None:
                # Log fetch event
                if audit_logger:
                    audit_logger.log_fetch(metric_id, value, self.provider)

                # Create version entry
                if versioning:
                    versioning.create_version(
                        metric_id=metric_id,
                        value=value,
                        source=self.provider,
                        changed_by="system",
                        metadata={"raw_key": source_key}
                    )

                # Normalize value (unit conversion, decimal adjustment)
                normalized = self._normalize_value(value, definition)

                # Log mapping event
                if audit_logger:
                    audit_logger.log_map(metric_id, source_key, normalized)

                mapped_data[metric_id] = {
                    "value": normalized,
                    "unit": definition.get("unit", "unknown"),
                    "source": self.provider,
                    "status": "fetched",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                if "calculation_formula" in definition:
                    calculated_metrics.append(metric_id)
                else:
                    missing_metrics.append(metric_id)

        return {
            "data": mapped_data,
            "missing": missing_metrics,
            "calculated": calculated_metrics,
            "ticker": ticker,
            "provider": self.provider,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_data": raw_data  # Include raw data for DataFrame construction
        }

    def _extract_value(self, raw_data: Dict[str, Any], source_key: str) -> Optional[Any]:
        """
        Extract specific value from raw API response.
        Intelligently sorts period keys to ensure the absolute latest date is grabbed,
        defensively unwraps dictionary-wrapped primitives, and performs normalized/fuzzy
        matching to resolve vendor-specific naming mismatches (e.g., yfinance vs standard registry).
        """
        if not source_key:
            return None

        # Helper function to normalize strings for robust comparison
        def normalize(s: str) -> str:
            if not s:
                return ""
            # Remove text inside parentheses (e.g., "(COGS)", "(CapEx)")
            s = re.sub(r'\(.*?\)', '', s)
            # Remove symbols like /, &, _, - and spaces, convert to lowercase
            return "".join(c for c in s.lower() if c.isalnum())

        # Direct lookups/synonyms map for yfinance specific variations
        yfinance_synonyms = {
            normalize("Cost of Revenue (COGS)"): ["costofrevenue", "costofgoods_sold"],
            normalize("Operating Expenses"): ["operatingexpense", "operatingexpenses"],
            normalize("EBIT / Operating Income"): ["ebit", "operatingincome"],
            normalize("Pre-Tax Income"): ["pretaxincome", "incomebeforetax"],
            normalize("Depreciation & Amortization"): ["depreciationandamortization", "depreciation&amortization"],
            normalize("Capital Expenditures (CapEx)"): ["capitalexpenditure", "capex"],
            normalize("Cash & Equivalents"): ["cashandcashequivalents", "cashcashequivalents"],
            normalize("Total Debt"): ["totaldebt", "longtermdebt", "currentdebt"],
            normalize("Tax Provision"): ["taxprovision", "incomeincome_tax_expense"]
        }

        target_normalized = normalize(source_key)
        allowed_matches = [target_normalized] + yfinance_synonyms.get(target_normalized, [])

        sections = ["info", "income_statement", "balance_sheet", "cash_flow"]

        for section in sections:
            if section in raw_data:
                section_data = raw_data[section]

                # Handle info section (flat dict)
                if section == "info" and isinstance(section_data, dict):
                    matched_key = None
                    for k in section_data.keys():
                        if normalize(k) in allowed_matches or k == source_key:
                            matched_key = k
                            break
                    
                    if matched_key:
                        value = section_data[matched_key]
                        if isinstance(value, dict):
                            return value.get("raw", value.get("value", value))
                        return value

                # Handle financial statements (dict with timestamps/dates as keys)
                elif isinstance(section_data, dict) and section_data:
                    try:
                        sorted_keys = sorted(list(section_data.keys()), reverse=True)
                        
                        # Prioritize "TTM" if present
                        most_recent_key = sorted_keys[0]
                        for key in sorted_keys:
                            if str(key).upper() == "TTM":
                                most_recent_key = key
                                break
                                
                        period_data = section_data[most_recent_key]
                        
                        if isinstance(period_data, dict):
                            # Search through keys with normalized fallback matching
                            matched_key = None
                            for k in period_data.keys():
                                if normalize(k) in allowed_matches or k == source_key:
                                    matched_key = k
                                    break
                            
                            if matched_key:
                                value = period_data[matched_key]
                                if isinstance(value, dict):
                                    return value.get("raw", value.get("value", value))
                                return value
                                
                    except Exception as e:
                        logger.error(f"[APIAdapter] Error parsing sorted periods in section {section}: {e}")
                        continue

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
        Only calculates if all required dependencies are available.
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
                # Replace metric names with values - sort by length descending to avoid partial replacements
                safe_formula = formula
                sorted_metrics = sorted(METRIC_REGISTRY.keys(), key=len, reverse=True)

                missing_deps = []
                for dep_metric in sorted_metrics:
                    if dep_metric in safe_formula:
                        if dep_metric in data_values:
                            # Use word boundary replacement to avoid partial matches
                            pattern = r'\b' + re.escape(dep_metric) + r'\b'
                            safe_formula = re.sub(pattern, str(data_values[dep_metric]), safe_formula)
                        else:
                            missing_deps.append(dep_metric)

                # Skip calculation if any dependencies are missing
                if missing_deps:
                    logger.debug(f"Skipping calculation of {metric_id}: missing dependencies {missing_deps}")
                    continue

                # Verify no variable names remain in formula (should be all numbers now)
                remaining_vars = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', safe_formula)
                if remaining_vars:
                    logger.warning(f"Cannot calculate {metric_id}: unresolved variables {remaining_vars} in formula '{formula}'")
                    continue

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