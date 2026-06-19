"""Shared utilities for Step 10 valuation processors.

Provides common helper functions used by Step10DCFProcessor,
Step10DuPontProcessor, and Step10CompsProcessor to eliminate
code duplication.
"""
from typing import Any, Dict, List


def msi_to_dict(msi: Any) -> Dict[str, Any]:
    """Convert ModelSpecificInputs (Pydantic model or dict) to a plain dict.

    Handles both raw dicts, Pydantic v2 models (model_dump), and v1 models (dict).
    """
    if isinstance(msi, dict):
        return msi
    if hasattr(msi, 'model_dump'):
        return msi.model_dump()
    if hasattr(msi, 'dict'):
        return msi.dict()
    return {}


def build_fallback_result(ticker: str, model_name: str, warnings: List[str]) -> Dict[str, Any]:
    """Build a standardized fallback result when a valuation engine fails.

    Args:
        ticker: Stock ticker symbol
        model_name: Valuation model name ('DCF', 'DUPONT', 'COMPS')
        warnings: Warning list (will be appended to)

    Returns:
        Standardized fallback result dictionary
    """
    warnings.append(f"{model_name} calculation used fallback method due to engine error")
    return {
        'valuation_summary': {
            'enterprise_value': None, 'equity_value': None,
            'fair_value_per_share': None, 'current_price': None,
            'implied_upside_downside': None,
        },
        'detailed_outputs': {'fallback': True, 'model': model_name},
        'sensitivity_analysis': None, 'scenario_analysis': None,
        'confidence_level': 'low', 'key_assumptions_summary': {},
        'warnings': warnings,
    }
