"""
Audit Logging Service
Tracks all data transformations, sources, and changes for compliance and debugging.
"""
import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class TransformationType(Enum):
    FETCH = "fetch"
    MAP = "map"
    NORMALIZE = "normalize"
    CALCULATE = "calculate"
    VALIDATE = "validate"
    RESOLVE = "resolve"
    MODIFY = "modify" # User manual modification
    AI_SUGGEST = "ai_suggest"

class AuditLogger:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logs: List[Dict[str, Any]] = []

    def log_transformation(
        self,
        metric_id: str,
        transformation_type: TransformationType,
        old_value: Optional[Any],
        new_value: Any,
        source: str,
        metadata: Optional[Dict] = None
    ):
        """Records a single data transformation event."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "metric_id": metric_id,
            "type": transformation_type.value,
            "old_value": old_value,
            "new_value": new_value,
            "source": source,
            "metadata": metadata or {}
        }
        self.logs.append(entry)
        logger.info(f"AUDIT: {entry}")

    def log_fetch(self, metric_id: str, raw_value: Any, api_source: str):
        self.log_transformation(
            metric_id, TransformationType.FETCH, None, raw_value, api_source
        )

    def log_map(self, metric_id: str, raw_key: str, mapped_value: Any):
        self.log_transformation(
            metric_id, TransformationType.MAP, raw_key, mapped_value, "schema_mapper"
        )

    def log_calculation(self, metric_id: str, formula: str, result: Any, inputs: List[str]):
        self.log_transformation(
            metric_id, TransformationType.CALCULATE, None, result, "calc_engine",
            {"formula": formula, "inputs": inputs}
        )

    def log_validation(self, metric_id: str, passed: bool, errors: List[str]):
        self.log_transformation(
            metric_id, TransformationType.VALIDATE, None, passed, "validator",
            {"errors": errors}
        )

    def log_resolution(self, metric_id: str, method: str, value: Any, confidence: float):
        self.log_transformation(
            metric_id, TransformationType.RESOLVE, None, value, method,
            {"confidence": confidence}
        )

    def log_user_modification(self, metric_id: str, old_val: Any, new_val: Any):
        self.log_transformation(
            metric_id, TransformationType.MODIFY, old_val, new_val, "user_input"
        )

    def log_ai_suggestion(self, metric_id: str, suggestion: Any, explanation: str):
        self.log_transformation(
            metric_id, TransformationType.AI_SUGGEST, None, suggestion, "llm_engine",
            {"explanation": explanation}
        )

    def get_audit_trail(self) -> List[Dict]:
        return self.logs

    def save_to_session(self, db_session):
        """Persist audit logs to database associated with session."""
        # Implementation depends on DB ORM
        pass

# Global registry of active loggers per session
_active_loggers: Dict[str, AuditLogger] = {}

def get_audit_logger(session_id: str) -> AuditLogger:
    if session_id not in _active_loggers:
        _active_loggers[session_id] = AuditLogger(session_id)
    return _active_loggers[session_id]