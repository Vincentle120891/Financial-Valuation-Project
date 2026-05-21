"""
Validation Middleware for DCF Model Data Pipeline
Checks data types, ranges, completeness, and consistency before saving to session.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from app.core.metric_registry import (
    METRIC_REGISTRY,
    get_metric_definition,
    get_required_metrics_for_method,
    DataType,
    MetricCategory
)

logger = logging.getLogger(__name__)

class ValidationMiddleware:
    """
    Middleware layer for validating financial data before persistence.
    Ensures data integrity across all workflow steps.
    """
    
    def __init__(self, method: str):
        """
        Initialize middleware for a specific valuation method.
        :param method: 'DCF', 'DuPont', or 'COMPS'
        """
        self.method = method
        self.required_metrics = get_required_metrics_for_method(method)
    
    def validate_complete_dataset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a complete dataset before saving.
        Returns validation report with status and errors.
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": self.method,
            "status": "VALID",
            "completeness_score": 0.0,
            "validation_errors": [],
            "warnings": [],
            "missing_required": [],
            "invalid_fields": [],
            "data_quality_issues": []
        }
        
        # Check completeness
        provided_metrics = set(data.get("data", {}).keys())
        required_set = set(self.required_metrics)
        missing_required = required_set - provided_metrics
        
        if missing_required:
            report["missing_required"] = list(missing_required)
            report["validation_errors"].append(
                f"Missing {len(missing_required)} required metrics for {self.method} method"
            )
            report["status"] = "INCOMPLETE"
        
        # Calculate completeness score
        if self.required_metrics:
            report["completeness_score"] = len(provided_metrics & required_set) / len(required_set)
        
        # Validate each field
        for metric_id, metric_data in data.get("data", {}).items():
            field_report = self.validate_single_field(metric_id, metric_data)
            
            if not field_report["is_valid"]:
                report["invalid_fields"].append({
                    "metric": metric_id,
                    "errors": field_report["errors"]
                })
                report["validation_errors"].extend(field_report["errors"])
                report["status"] = "INVALID" if metric_id in required_set else "PARTIAL"
            
            if field_report["warnings"]:
                report["warnings"].extend([
                    {"metric": metric_id, "warning": w} 
                    for w in field_report["warnings"]
                ])
            
            if field_report["quality_issues"]:
                report["data_quality_issues"].extend([
                    {"metric": metric_id, "issue": q} 
                    for q in field_report["quality_issues"]
                ])
        
        # Check for outliers across peers if peer data exists
        if "peer_data" in data:
            outlier_report = self.detect_outliers(data["data"], data["peer_data"])
            report["data_quality_issues"].extend(outlier_report)
        
        return report
    
    def validate_single_field(self, metric_id: str, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single metric field.
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "quality_issues": []
        }
        
        # Get definition
        definition = get_metric_definition(metric_id)
        if not definition:
            result["errors"].append(f"Unknown metric ID: {metric_id}")
            result["is_valid"] = False
            return result
        
        # Check if value exists
        value = metric_data.get("value")
        if value is None:
            status = metric_data.get("status", "UNKNOWN")
            if status not in ["MISSING", "CALCULATED", "FETCHED"]:
                result["errors"].append(f"Value is None and status is {status}")
                result["is_valid"] = False
            return result
        
        # Type validation
        expected_type = definition.get("type", DataType.FLOAT)
        type_error = self._validate_type(value, expected_type)
        if type_error:
            result["errors"].append(type_error)
            result["is_valid"] = False
        
        # Range validation
        range_error = self._validate_range(value, definition)
        if range_error:
            result["errors"].append(range_error)
            result["is_valid"] = False
        
        # Warning checks
        if expected_type == DataType.PERCENTAGE:
            if abs(value) > 0.5:  # > 50%
                result["warnings"].append(f"Unusually high percentage: {value*100:.1f}%")
        
        if expected_type == DataType.FLOAT and value != 0:
            # Check for extreme values
            if abs(value) > 1e9:
                result["warnings"].append(f"Extremely large value: {value}")
        
        # Quality checks
        if metric_data.get("source") == "AI_SUGGESTION":
            result["quality_issues"].append("Value generated by AI - requires user confirmation")
        elif metric_data.get("source") == "PDF_EXTRACTION":
            result["quality_issues"].append("Value extracted from PDF - may have OCR errors")
        
        return result
    
    def _validate_type(self, value: Any, expected_type: DataType) -> Optional[str]:
        """Validate value type."""
        try:
            if expected_type in [DataType.FLOAT, DataType.PERCENTAGE]:
                float(value)
            elif expected_type == DataType.INTEGER:
                int(value)
            elif expected_type == DataType.STRING:
                str(value)
            return None
        except (ValueError, TypeError):
            return f"Type mismatch: expected {expected_type.value}, got {type(value).__name__}"
    
    def _validate_range(self, value: Any, definition: Dict[str, Any]) -> Optional[str]:
        """Validate value range."""
        validation_rules = definition.get("validation", {})
        
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return "Cannot validate range for non-numeric value"
        
        if "min_value" in validation_rules and validation_rules["min_value"] is not None:
            if numeric_value < validation_rules["min_value"]:
                return f"Value {numeric_value} below minimum {validation_rules['min_value']}"
        
        if "max_value" in validation_rules and validation_rules["max_value"] is not None:
            if numeric_value > validation_rules["max_value"]:
                return f"Value {numeric_value} above maximum {validation_rules['max_value']}"
        
        return None
    
    def detect_outliers(self, company_data: Dict[str, Any], peer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect statistical outliers by comparing company metrics to peer averages.
        """
        outliers = []
        
        for metric_id, company_metric in company_data.items():
            if metric_id not in peer_data:
                continue
            
            company_value = company_metric.get("value")
            if company_value is None:
                continue
            
            peer_values = []
            for peer_ticker, peer_metrics in peer_data.items():
                if metric_id in peer_metrics:
                    peer_value = peer_metrics[metric_id].get("value")
                    if peer_value is not None:
                        peer_values.append(peer_value)
            
            if len(peer_values) < 3:
                continue  # Not enough peers for statistical analysis
            
            # Calculate z-score
            mean = sum(peer_values) / len(peer_values)
            variance = sum((x - mean) ** 2 for x in peer_values) / len(peer_values)
            std_dev = variance ** 0.5
            
            if std_dev == 0:
                continue
            
            z_score = abs(company_value - mean) / std_dev
            
            if z_score > 2.5:  # More than 2.5 standard deviations
                outliers.append({
                    "metric": metric_id,
                    "company_value": company_value,
                    "peer_average": mean,
                    "z_score": z_score,
                    "issue": f"Statistical outlier (z-score: {z_score:.2f})"
                })
        
        return outliers
    
    def validate_step_transition(self, current_step: int, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate data completeness before allowing transition to next step.
        Returns (can_proceed, error_messages)
        """
        errors = []
        
        # Step-specific requirements
        if current_step == 6:  # Before moving to Step 7 (Historical Extraction)
            # Must have identified all missing fields
            if "missing_inputs" not in data or not isinstance(data["missing_inputs"], list):
                errors.append("Missing inputs not properly identified")
        
        elif current_step == 7:  # Before moving to Step 8 (Forecast)
            # All historical data must be present
            historical_metrics = [
                mid for mid, defn in METRIC_REGISTRY.items()
                if defn.get("category") in [MetricCategory.INCOME_STATEMENT, 
                                           MetricCategory.BALANCE_SHEET,
                                           MetricCategory.CASH_FLOW]
            ]
            
            missing_historical = []
            for metric_id in historical_metrics:
                if metric_id not in data.get("data", {}):
                    missing_historical.append(metric_id)
            
            if missing_historical:
                errors.append(f"Still missing {len(missing_historical)} historical data points")
        
        elif current_step == 8:  # Before moving to Step 9 (Confirm)
            # All forecast inputs must be present
            forecast_metrics = [
                mid for mid, defn in METRIC_REGISTRY.items()
                if defn.get("category") == MetricCategory.FORECAST
            ]
            
            missing_forecast = []
            for metric_id in forecast_metrics:
                if metric_id not in data.get("data", {}) or \
                   data["data"][metric_id].get("value") is None:
                    missing_forecast.append(metric_id)
            
            if missing_forecast:
                errors.append(f"Missing {len(missing_forecast)} forecast assumptions")
        
        elif current_step == 9:  # Before moving to Step 10 (Valuation)
            # Final validation - all required metrics must be present and valid
            report = self.validate_complete_dataset(data)
            if report["status"] != "VALID":
                errors.extend(report["validation_errors"])
        
        can_proceed = len(errors) == 0
        return can_proceed, errors


def create_validation_middleware(method: str) -> ValidationMiddleware:
    """Factory function to create middleware for a specific method."""
    return ValidationMiddleware(method)
