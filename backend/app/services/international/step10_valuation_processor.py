"""Step 10: Final Valuation Processor — DuPont and COMPS only.

DCF valuation is handled directly by Step10DCFProcessor.run_valuation_with_building_blocks()
in valuation_routes.py (Phase 1 runs in Step 9, Phase 2 runs in Step 10).

This processor handles:
- Step10DuPontProcessor: DuPont ROE decomposition analysis
- Step10CompsProcessor: Comparable Company analysis
"""
import logging
from typing import Dict, Any
from enum import Enum

from app.services.international.step10_dupont_processor import Step10DuPontProcessor
from app.services.international.step10_comps_processor import Step10CompsProcessor

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Custom exception for data validation errors in valuation calculations."""
    def __init__(self, message: str, missing_fields: list = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(self.message)


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class Step10ValuationProcessor:
    """
    Step 10: Final Valuation Processor — DuPont and COMPS only.

    DCF valuation is handled directly by Step10DCFProcessor.run_valuation_with_building_blocks()
    in valuation_routes.py (no longer routed through this processor).

    This processor handles:
    - DuPont: ROE decomposition analysis
    - COMPS: Comparable company multiples
    """

    def __init__(self):
        self._dupont = Step10DuPontProcessor()
        self._comps = Step10CompsProcessor()

    async def run_valuation(
        self,
        ticker: str,
        model: str,
        assumptions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run valuation for DuPont or COMPS models.

        Args:
            ticker: Stock ticker symbol
            model: Valuation model ('DUPONT', 'COMPS')
            assumptions: Confirmed assumptions from Step 9

        Returns:
            Dictionary with valuation_summary, detailed_outputs, sensitivity_analysis,
            scenario_analysis, confidence_level, key_assumptions_summary, warnings
        """
        model = model.upper()

        if model == 'DUPONT':
            return await self._dupont.run_dupont_valuation(ticker, assumptions)
        elif model == 'COMPS':
            return await self._comps.run_comps_valuation(ticker, assumptions)
        else:
            raise ValueError(f"Unsupported valuation model: {model}. DCF must use run_valuation_with_building_blocks() directly.")
