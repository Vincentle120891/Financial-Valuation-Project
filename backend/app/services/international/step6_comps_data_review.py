"""Step 6: Comps Data Review Layer - Pure Data Aggregation for Trading Comps Method

This is a dedicated processor for Trading Comps valuation method only.
It eliminates conditional branching by focusing exclusively on Comps-specific data requirements.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
import pandas as pd

from .yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


class DataStatus(str, Enum):
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DataField(BaseModel):
    field_name: str
    display_name: Optional[str] = None
    value: Optional[Any] = None
    unit: str = ""
    status: DataStatus
    source: Optional[str] = None
    formula: Optional[str] = None
    is_critical: bool = False
    allow_override: bool = False


class HistoricalFinancialsDisplay(BaseModel):
    years: List[int] = []
    data_fields: List[DataField] = []


class MarketDataDisplay(BaseModel):
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    enterprise_value: Optional[DataField] = None
    data_fields: List[DataField] = []


class PeerCompany(BaseModel):
    ticker: str
    name: Optional[str] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    ev_ebitda: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_revenue: Optional[float] = None
    pb_ratio: Optional[float] = None


class PeerComparablesDisplay(BaseModel):
    companies: List[PeerCompany] = []
    median_ev_ebitda: Optional[float] = None
    median_pe: Optional[float] = None
    median_ev_revenue: Optional[float] = None
    median_pb: Optional[float] = None
    data_fields: List[DataField] = []


class CalculatedMetricsDisplay(BaseModel):
    data_fields: List[DataField] = []


class MissingDataSummary(BaseModel):
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    total_missing: int = 0


class CompsDataReviewResponse(BaseModel):
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "COMPS"
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    peer_comparables: Optional[PeerComparablesDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    data_complete: bool = False
    message: str = ""


class CompsStep6Processor:
    def __init__(self):
        self.yfinance_service = YFinanceService()

    async def process_comps_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> CompsDataReviewResponse:
        if historical_data is None or market_data is None or retrieved_assumptions is None:
            logger.info(f"Fetching data for Comps analysis of {ticker}")
            all_data = self.yfinance_service.fetch_all_data(ticker, market)
            historical_data = historical_data or {'financials': None, 'balance_sheet': None, 'cashflow': None}
            market_data = market_data or all_data.get('key_stats', {})
            retrieved_assumptions = retrieved_assumptions or {}

        user_overrides = user_overrides or {}
        historical_display = self._process_comps_historical(historical_data, user_overrides)
        market_display = self._process_comps_market_data(market_data, user_overrides)
        peer_display = self._process_comps_peer_comparables(retrieved_assumptions, user_overrides)
        calculated_display = self._calculate_comps_intermediate_metrics(historical_display, market_display, peer_display)
        
        all_displays = [historical_display, market_display]
        missing_summary = self._aggregate_missing_data(all_displays)
        ready = len(missing_summary.critical_missing) == 0

        return CompsDataReviewResponse(
            session_id=f"step6_comps_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="COMPS",
            historical_financials=historical_display,
            market_data=market_display,
            peer_comparables=peer_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            data_complete=ready,
            message="Comps data aggregated successfully." if ready else "Missing critical Comps data."
        )

    def _process_comps_historical(self, historical_data: Dict, user_overrides: Dict) -> HistoricalFinancialsDisplay:
        data_fields = []
        comps_fields = [("revenue", "Total Revenue", True), ("ebitda", "EBITDA", True), ("net_income", "Net Income", True)]
        for field_name, display_name, is_critical in comps_fields:
            data_fields.append(DataField(field_name=field_name, display_name=display_name, value=None, unit="USD", status=DataStatus.MISSING, is_critical=is_critical, allow_override=True))
        return HistoricalFinancialsDisplay(years=[], data_fields=data_fields)

    def _process_comps_market_data(self, market_data: Dict, user_overrides: Dict) -> MarketDataDisplay:
        data_fields = []
        return MarketDataDisplay(data_fields=data_fields)

    def _process_comps_peer_comparables(self, retrieved_assumptions: Dict, user_overrides: Dict) -> PeerComparablesDisplay:
        peers = retrieved_assumptions.get('peers', [])
        companies = [PeerCompany(ticker=p) for p in peers]
        return PeerComparablesDisplay(companies=companies)

    def _calculate_comps_intermediate_metrics(self, historical_display, market_display, peer_display) -> CalculatedMetricsDisplay:
        return CalculatedMetricsDisplay(data_fields=[])

    def _aggregate_missing_data(self, displays: List) -> MissingDataSummary:
        return MissingDataSummary(critical_missing=[], optional_missing=[], total_missing=0)


comps_step6_processor = CompsStep6Processor()
