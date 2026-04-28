"""
Custom Exceptions for Valuation Engine

Provides structured exception handling with error codes and details.
"""

from typing import Optional, Dict, Any


class ValuationException(Exception):
    """Base exception for all valuation-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "VALUATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }


class ConfigurationException(ValuationException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details
        )


class DataFetchException(ValuationException):
    """Raised when data fetching from external sources fails."""
    
    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if source:
            details["source"] = source
        super().__init__(
            message=message,
            error_code="DATA_FETCH_ERROR",
            details=details
        )


class CalculationException(ValuationException):
    """Raised when valuation calculation fails."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if model:
            details["model"] = model
        super().__init__(
            message=message,
            error_code="CALCULATION_ERROR",
            details=details
        )


class AIEngineException(ValuationException):
    """Raised when AI engine fails to generate assumptions."""
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        fallback_used: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if provider:
            details["provider"] = provider
        details["fallback_used"] = fallback_used
        super().__init__(
            message=message,
            error_code="AI_ENGINE_ERROR",
            details=details
        )


class SessionNotFoundException(ValuationException):
    """Raised when a session is not found."""
    
    def __init__(self, session_id: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["session_id"] = session_id
        super().__init__(
            message=f"Session not found: {session_id}",
            error_code="SESSION_NOT_FOUND",
            details=details
        )


class ValidationException(ValuationException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )
