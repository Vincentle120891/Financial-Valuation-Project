"""Shared models for Step 6 Data Review across all valuation methods

This module contains Pydantic models and enums used by all Step 6 processors:
- DCFStep6Processor
- DuPontStep6Processor  
- CompsStep6Processor

Using a shared models module ensures consistency across all valuation methods
and avoids code duplication.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class DataStatus(str, Enum):
    """Status of data field"""
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DataField(BaseModel):
    """A single data field with status tracking"""
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
    """Historical financial data display"""
    years: List[int] = []
    data_fields: List[DataField] = []


class ForecastDriversDisplay(BaseModel):
    """Forecast drivers display"""
    data_fields: List[DataField] = []


class MarketDataDisplay(BaseModel):
    """Market data display"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    beta: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash: Optional[DataField] = None
    currency: Optional[DataField] = None
    data_fields: List[DataField] = []


class PeerCompany(BaseModel):
    """Individual peer company data"""
    ticker: str
    name: Optional[str] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    ev_ebitda: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_revenue: Optional[float] = None
    pb_ratio: Optional[float] = None
    beta: Optional[float] = None
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    tax_rate: Optional[float] = None
    cost_of_debt: Optional[float] = None


class PeerComparablesDisplay(BaseModel):
    """Peer comparables display with individual companies and medians"""
    companies: List[PeerCompany] = []
    median_ev_ebitda: Optional[float] = None
    median_pe: Optional[float] = None
    median_ev_revenue: Optional[float] = None
    median_pb: Optional[float] = None
    data_fields: List[DataField] = []  # Keep for backward compatibility


class CalculatedMetricsDisplay(BaseModel):
    """Calculated metrics from retrieved data (NOT final valuations)"""
    data_fields: List[DataField] = []


class MissingDataSummary(BaseModel):
    """Summary of missing data"""
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    total_missing: int = 0


class Step6DataReviewResponse(BaseModel):
    """
    Step 6 Response: Shows all retrieved inputs, missing inputs,
    and calculated intermediate metrics. NO FINAL VALUATIONS.
    
    This is the unified response format used by all valuation methods.
    Each method will populate only the relevant fields.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    forecast_drivers: Optional[ForecastDriversDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    peer_comparables: Optional[PeerComparablesDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    data_complete: bool = False
    message: str = ""
