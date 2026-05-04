"""
Vietnamese-Specific Input Models for Valuation Workflows

This module contains strictly typed Pydantic models for Vietnamese stock valuation,
enforcing complete separation from international workflows.

Key Features:
- TT99 accounting standards compliance (Thông Tư 99/2025/TT-BTC)
- HOSE/HNX/UPCOM ticker format validation
- VND currency handling throughout
- Vietnam-specific financial metrics and ratios

Market Isolation:
- Vietnamese tickers CANNOT use international logic or data sources
- Separate validation, service layer, and engine execution
- No cross-contamination with yfinance or international dependencies
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum
import re


class VNExchange(str, Enum):
    """Vietnamese Stock Exchanges"""
    HOSE = "HOSE"  # Ho Chi Minh Stock Exchange
    HNX = "HNX"    # Hanoi Stock Exchange
    UPCOM = "UPCOM"  # Unlisted Public Company Market


class VNSector(str, Enum):
    """Vietnamese Market Sectors"""
    BANKING = "Banking"
    REAL_ESTATE = "Real Estate"
    MANUFACTURING = "Manufacturing"
    CONSUMER_GOODS = "Consumer Goods"
    ENERGY = "Energy"
    MATERIALS = "Materials"
    UTILITIES = "Utilities"
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    TELECOMMUNICATIONS = "Telecommunications"
    OTHER = "Other"


# ──────────────────────────────────────────────────────────────────────────────
# DCF Request Models
# ──────────────────────────────────────────────────────────────────────────────

class VietnameseDCFRequest(BaseModel):
    """
    Vietnamese DCF Valuation Request
    
    Strictly typed input for Vietnamese stock DCF analysis.
    Uses TT99 accounting standards and VND currency throughout.
    
    Attributes:
        ticker: Vietnamese ticker symbol (e.g., VNM, VCB.HN, ABC.UP)
        company_name: Full company name in Vietnamese or English
        exchange: Trading exchange (HOSE, HNX, or UPCOM)
        sector: Industry sector classification
        current_price_vnd: Current stock price in VND
        shares_outstanding: Number of outstanding shares
        risk_free_rate_vn: Vietnam risk-free rate (default: 10-year government bond)
        market_risk_premium_vn: Vietnam equity risk premium
        beta: Stock beta relative to VNINDEX
        terminal_growth_rate: Perpetual growth rate (g)
        forecast_years: Number of years for explicit forecast period
        wacc_override: Optional custom WACC (if provided, overrides calculated WACC)
    """
    
    ticker: str = Field(..., description="Vietnamese ticker symbol")
    company_name: str = Field(..., description="Company name")
    exchange: VNExchange = Field(..., description="Stock exchange")
    sector: VNSector = Field(..., description="Industry sector")
    
    # Market data (VND)
    current_price_vnd: float = Field(..., gt=0, description="Current stock price in VND")
    shares_outstanding: float = Field(..., gt=0, description="Shares outstanding")
    
    # Vietnam-specific parameters
    risk_free_rate_vn: float = Field(
        default=0.068,  # ~6.8% typical 10-year VN government bond
        ge=0.01, le=0.20,
        description="Vietnam risk-free rate"
    )
    market_risk_premium_vn: float = Field(
        default=0.075,  # ~7.5% Vietnam ERP
        ge=0.03, le=0.15,
        description="Vietnam market risk premium"
    )
    beta: float = Field(default=1.0, ge=0, le=3.0, description="Stock beta vs VNINDEX")
    
    # DCF parameters
    terminal_growth_rate: float = Field(
        default=0.03, ge=0, le=0.08,
        description="Terminal growth rate"
    )
    forecast_years: int = Field(default=5, ge=3, le=10, description="Forecast horizon")
    
    # Optional overrides
    wacc_override: Optional[float] = Field(
        None, ge=0, le=0.30,
        description="Custom WACC override"
    )
    corporate_tax_rate: float = Field(
        default=0.20,  # 20% Vietnam corporate tax
        ge=0, le=0.30,
        description="Corporate tax rate"
    )
    
    @field_validator('ticker')
    @classmethod
    def validate_vn_ticker_format(cls, v: str) -> str:
        """
        Validate Vietnamese ticker format.
        
        Accepts formats:
        - Simple: VNM, VCB, HPG
        - With exchange suffix: VNM.HN, ABC.UP
        - With .VN suffix: VNM.VN
        
        Rejects:
        - International tickers: AAPL, MSFT, GOOGL
        - Invalid characters
        """
        v = v.strip().upper()
        
        # Pattern for Vietnamese tickers
        # 1-10 alphanumeric chars, optionally followed by .HN, .UP, or .VN
        vn_pattern = r'^[A-Z0-9]{1,10}(\.(HN|UP|VN))?$'
        
        if not re.match(vn_pattern, v):
            raise ValueError(
                f"Invalid Vietnamese ticker format: {v}. "
                "Expected format: VNM, VCB.HN, ABC.UP, or VNM.VN"
            )
        
        # Block known international tickers
        international_blocklist = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM',
            'V', 'JNJ', 'WMT', 'PG', 'MA', 'UNH', 'HD', 'DIS', 'PYPL'
        ]
        base_ticker = v.split('.')[0]
        if base_ticker in international_blocklist:
            raise ValueError(
                f"Ticker {v} appears to be an international stock. "
                "Vietnamese workflow only accepts HOSE/HNX/UPCOM listed companies."
            )
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "VNM",
                "company_name": "Công ty Cổ phần Sữa Việt Nam",
                "exchange": "HOSE",
                "sector": "Consumer Goods",
                "current_price_vnd": 75000,
                "shares_outstanding": 1000000000,
                "risk_free_rate_vn": 0.068,
                "market_risk_premium_vn": 0.075,
                "beta": 0.85,
                "terminal_growth_rate": 0.03,
                "forecast_years": 5,
                "corporate_tax_rate": 0.20
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Comps Request Models
# ──────────────────────────────────────────────────────────────────────────────

class VNPeerMultiple(BaseModel):
    """
    Vietnamese Peer Company Multiples
    
    Standardized schema for individual Vietnamese peer data.
    All values in VND or VND-based ratios.
    
    Attributes:
        ticker: Peer company ticker
        company_name: Peer company name
        sector: Sector classification
        market_cap_vnd: Market capitalization in billion VND
        ev_vnd: Enterprise value in billion VND
        revenue_ltm_vnd: LTM revenue in billion VND
        ebitda_ltm_vnd: LTM EBITDA in billion VND
        net_income_ltm_vnd: LTM net income in billion VND
        book_value_vnd: Book value of equity in billion VND
        ev_ebitda_ltm: EV/EBITDA LTM multiple
        pe_ltm: P/E LTM multiple
        ev_revenue_ltm: EV/Revenue LTM multiple
        pb_ratio: Price-to-Book ratio
        dividend_yield: Dividend yield (%)
    """
    
    ticker: str = Field(..., description="Peer ticker")
    company_name: str = Field(..., description="Company name")
    sector: VNSector = Field(..., description="Sector")
    
    # Market data (VND billions)
    market_cap_vnd: float = Field(..., gt=0, description="Market cap (tỷ VND)")
    ev_vnd: float = Field(..., gt=0, description="Enterprise value (tỷ VND)")
    
    # Financials (VND billions)
    revenue_ltm_vnd: float = Field(..., gt=0, description="LTM Revenue (tỷ VND)")
    ebitda_ltm_vnd: float = Field(..., gt=0, description="LTM EBITDA (tỷ VND)")
    net_income_ltm_vnd: float = Field(..., description="LTM Net Income (tỷ VND)")
    book_value_vnd: float = Field(..., gt=0, description="Book Value (tỷ VND)")
    
    # Calculated multiples
    ev_ebitda_ltm: float = Field(..., gt=0, description="EV/EBITDA LTM")
    pe_ltm: float = Field(..., description="P/E LTM")
    ev_revenue_ltm: float = Field(..., gt=0, description="EV/Revenue LTM")
    pb_ratio: float = Field(..., gt=0, description="P/B Ratio")
    
    # Additional metrics
    dividend_yield: Optional[float] = Field(None, ge=0, description="Dividend Yield %")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "VCB",
                "company_name": "Ngân hàng TMCP Ngoại thương Việt Nam",
                "sector": "Banking",
                "market_cap_vnd": 350000,
                "ev_vnd": 380000,
                "revenue_ltm_vnd": 95000,
                "ebitda_ltm_vnd": 72000,
                "net_income_ltm_vnd": 45000,
                "book_value_vnd": 280000,
                "ev_ebitda_ltm": 5.28,
                "pe_ltm": 7.78,
                "ev_revenue_ltm": 4.0,
                "pb_ratio": 1.25,
                "dividend_yield": 3.5
            }
        }


class VietnameseCompsSelectionRequest(BaseModel):
    """
    Vietnamese Comps Selection Criteria
    
    Handles peer selection for Vietnamese stocks.
    Filters peers from VNINDEX, VN30, or local sector indices.
    
    Attributes:
        target_ticker: Target company ticker
        peer_list: Optional explicit list of peer tickers
        sector: Sector filter for automatic peer selection
        industry: Sub-industry filter (optional)
        min_market_cap_vnd: Minimum market cap filter (billion VND)
        max_peers: Maximum number of peers to include
        include_vn30_only: If True, only select from VN30 constituents
    """
    
    target_ticker: str = Field(..., description="Target company ticker")
    peer_list: Optional[List[str]] = Field(None, description="Explicit peer tickers")
    sector: Optional[VNSector] = Field(None, description="Sector filter")
    industry: Optional[str] = Field(None, description="Sub-industry filter")
    
    # Filtering parameters
    min_market_cap_vnd: Optional[float] = Field(
        None, gt=0,
        description="Minimum market cap (tỷ VND)"
    )
    max_peers: int = Field(default=10, ge=3, le=20, description="Max peers")
    include_vn30_only: bool = Field(
        default=False,
        description="Only select from VN30 index"
    )
    
    @field_validator('target_ticker')
    @classmethod
    def validate_target_ticker(cls, v: str) -> str:
        """Validate Vietnamese ticker format."""
        v = v.strip().upper()
        vn_pattern = r'^[A-Z0-9]{1,10}(\.(HN|UP|VN))?$'
        if not re.match(vn_pattern, v):
            raise ValueError(f"Invalid Vietnamese ticker: {v}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_ticker": "VNM",
                "sector": "Consumer Goods",
                "industry": "Food & Beverages",
                "min_market_cap_vnd": 10000,
                "max_peers": 8,
                "include_vn30_only": False
            }
        }


class VietnameseCompsValuationRequest(BaseModel):
    """
    Vietnamese Comps Valuation Request
    
    Complete request structure for Vietnamese comparable company analysis.
    Includes target financials, peer multiples, and outlier filtering.
    
    Attributes:
        target_ticker: Target company
        target_financials: Target company financial metrics
        peer_multiples: List of peer company multiples
        apply_outlier_filtering: Enable IQR-based outlier removal
        iqr_multiplier: IQR multiplier for outlier detection (default: 1.5)
        outlier_metric: Metric to use for outlier filtering
    """
    
    target_ticker: str = Field(..., description="Target ticker")
    target_company_name: str = Field(..., description="Target company name")
    sector: VNSector = Field(..., description="Sector")
    
    # Target financials (VND billions)
    target_revenue_vnd: float = Field(..., gt=0, description="Target revenue")
    target_ebitda_vnd: float = Field(..., gt=0, description="Target EBITDA")
    target_net_income_vnd: float = Field(..., description="Target net income")
    target_eps_vnd: float = Field(..., description="Target EPS (VND)")
    target_book_value_vnd: float = Field(..., gt=0, description="Target book value")
    
    # Peer data
    peer_multiples: List[VNPeerMultiple] = Field(
        ..., min_length=3,
        description="List of peer company multiples"
    )
    
    # Outlier filtering
    apply_outlier_filtering: bool = Field(
        default=True,
        description="Apply IQR outlier filtering"
    )
    iqr_multiplier: float = Field(
        default=1.5, ge=0.5, le=3.0,
        description="IQR multiplier for outliers"
    )
    outlier_metric: str = Field(
        default="ev_ebitda_ltm",
        description="Metric for outlier detection"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_ticker": "VNM",
                "target_company_name": "Vinamilk",
                "sector": "Consumer Goods",
                "target_revenue_vnd": 85500,
                "target_ebitda_vnd": 18200,
                "target_net_income_vnd": 12700,
                "target_eps_vnd": 12500,
                "target_book_value_vnd": 32300,
                "peer_multiples": [],  # List of VNPeerMultiple
                "apply_outlier_filtering": True,
                "iqr_multiplier": 1.5,
                "outlier_metric": "ev_ebitda_ltm"
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# DuPont Request Models
# ──────────────────────────────────────────────────────────────────────────────

class VNDuPontComponents(BaseModel):
    """
    Vietnamese DuPont Analysis Components
    
    Strict schema for Net Profit Margin, Asset Turnover, and Equity Multiplier
    breakdowns using TT99 accounting standards.
    
    Attributes:
        net_profit_margin: Net Income / Revenue
        asset_turnover: Revenue / Total Assets
        equity_multiplier: Total Assets / Shareholders' Equity
        roe: Return on Equity (calculated as product of above three)
        
    Optional raw financial fields for validation:
        net_income_vnd: Net income in billion VND
        revenue_vnd: Revenue in billion VND
        total_assets_vnd: Total assets in billion VND
        shareholders_equity_vnd: Shareholders' equity in billion VND
    """
    
    # Core DuPont components
    net_profit_margin: float = Field(..., ge=-1, le=1, description="Net Profit Margin")
    asset_turnover: float = Field(..., ge=0, description="Asset Turnover")
    equity_multiplier: float = Field(..., ge=1, description="Equity Multiplier")
    
    # Calculated ROE
    roe: Optional[float] = Field(None, ge=-1, le=2, description="ROE (calculated)")
    
    # Raw financial data for validation (VND billions)
    net_income_vnd: Optional[float] = Field(None, description="Net Income (tỷ VND)")
    revenue_vnd: Optional[float] = Field(None, gt=0, description="Revenue (tỷ VND)")
    total_assets_vnd: Optional[float] = Field(None, gt=0, description="Total Assets (tỷ VND)")
    shareholders_equity_vnd: Optional[float] = Field(None, gt=0, description="Equity (tỷ VND)")
    
    @field_validator('roe', mode='before')
    @classmethod
    def calculate_roe(cls, v, info):
        """Auto-calculate ROE if not provided."""
        if v is not None:
            return v
        
        data = info.data
        if all(k in data for k in ['net_profit_margin', 'asset_turnover', 'equity_multiplier']):
            return data['net_profit_margin'] * data['asset_turnover'] * data['equity_multiplier']
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "net_profit_margin": 0.1485,
                "asset_turnover": 1.69,
                "equity_multiplier": 1.56,
                "roe": 0.392,
                "net_income_vnd": 12.7,
                "revenue_vnd": 85.5,
                "total_assets_vnd": 50.5,
                "shareholders_equity_vnd": 32.3
            }
        }


class VietnameseDuPontRequest(BaseModel):
    """
    Vietnamese DuPont Analysis Request
    
    Captures ticker, years, and optional custom ratios for Vietnamese companies.
    Uses TT99 financial statement data.
    
    Attributes:
        ticker: Vietnamese ticker symbol
        company_name: Company name
        years: List of fiscal years to analyze
        custom_ratios: Optional pre-calculated DuPont components
        exchange: Stock exchange for reference
    """
    
    ticker: str = Field(..., description="Vietnamese ticker")
    company_name: str = Field(..., description="Company name")
    exchange: VNExchange = Field(..., description="Stock exchange")
    years: List[int] = Field(..., min_length=1, max_length=10, description="Fiscal years")
    
    # Optional custom ratios (if pre-calculated from TT99 statements)
    custom_ratios: Optional[Dict[int, VNDuPontComponents]] = Field(
        None,
        description="Custom DuPont ratios by year"
    )
    
    @field_validator('ticker')
    @classmethod
    def validate_vn_ticker(cls, v: str) -> str:
        """Validate Vietnamese ticker format."""
        v = v.strip().upper()
        vn_pattern = r'^[A-Z0-9]{1,10}(\.(HN|UP|VN))?$'
        if not re.match(vn_pattern, v):
            raise ValueError(f"Invalid Vietnamese ticker: {v}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "VNM",
                "company_name": "Vinamilk",
                "exchange": "HOSE",
                "years": [2021, 2022, 2023],
                "custom_ratios": {
                    "2023": {
                        "net_profit_margin": 0.1485,
                        "asset_turnover": 1.69,
                        "equity_multiplier": 1.56
                    }
                }
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Financial Data Models (TT99 Compliant)
# ──────────────────────────────────────────────────────────────────────────────

class VNFinancialData(BaseModel):
    """
    Vietnamese Financial Data Container
    
    Aggregated financial data extracted from TT99-compliant statements.
    Used as input for building valuation requests.
    
    Attributes:
        ticker: Company ticker
        fiscal_year: Fiscal year
        currency: Always VND
        balance_sheet_items: Key balance sheet items (billion VND)
        income_statement_items: Key income statement items (billion VND)
        cash_flow_items: Key cash flow items (billion VND)
        ratios: Pre-calculated financial ratios
    """
    
    ticker: str = Field(..., description="Ticker")
    fiscal_year: int = Field(..., description="Fiscal year")
    currency: str = Field(default="VND", description="Currency")
    
    # Balance Sheet (tỷ VND)
    cash_and_equivalents: Optional[float] = Field(None, description="Tiền và tương đương tiền")
    total_assets: Optional[float] = Field(None, description="Tổng tài sản")
    total_liabilities: Optional[float] = Field(None, description="Tổng nợ phải trả")
    shareholders_equity: Optional[float] = Field(None, description="Vốn chủ sở hữu")
    
    # Income Statement (tỷ VND)
    revenue: Optional[float] = Field(None, description="Doanh thu thuần")
    gross_profit: Optional[float] = Field(None, description="Lợi nhuận gộp")
    operating_profit: Optional[float] = Field(None, description="Lợi nhuận từ HĐKD")
    net_income: Optional[float] = Field(None, description="Lợi nhuận sau thuế")
    ebitda: Optional[float] = Field(None, description="EBITDA")
    
    # Cash Flow (tỷ VND)
    operating_cash_flow: Optional[float] = Field(None, description="Lưu chuyển tiền từ HĐKD")
    investing_cash_flow: Optional[float] = Field(None, description="Lưu chuyển tiền từ HĐĐT")
    financing_cash_flow: Optional[float] = Field(None, description="Lưu chuyển tiền từ HĐTC")
    capex: Optional[float] = Field(None, description="Chi mua sắm TSCĐ")
    
    # Shares & Price
    shares_outstanding: Optional[float] = Field(None, description="Số cổ phiếu lưu hành")
    current_price_vnd: Optional[float] = Field(None, description="Giá thị trường")
    
    # Pre-calculated ratios
    gross_margin: Optional[float] = Field(None, description="Biên lợi nhuận gộp")
    operating_margin: Optional[float] = Field(None, description="Biên lợi nhuận HĐKD")
    net_margin: Optional[float] = Field(None, description="Biên lợi nhuận ròng")
    roe: Optional[float] = Field(None, description="ROE")
    roa: Optional[float] = Field(None, description="ROA")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "VNM",
                "fiscal_year": 2023,
                "currency": "VND",
                "cash_and_equivalents": 8.5,
                "total_assets": 50.5,
                "total_liabilities": 18.2,
                "shareholders_equity": 32.3,
                "revenue": 85.5,
                "gross_profit": 33.2,
                "operating_profit": 15.8,
                "net_income": 12.7,
                "ebitda": 18.2,
                "shares_outstanding": 1000000000,
                "current_price_vnd": 75000,
                "gross_margin": 0.388,
                "operating_margin": 0.185,
                "net_margin": 0.149,
                "roe": 0.393,
                "roa": 0.251
            }
        }
