"""
Step 3: Vietnamese Historical Financial Data Processor
Handles Vietnamese historical financials retrieval, TT99 compliance, and gap filling.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.services.vietnamese.vietnamese_ticker_service import VietnameseTickerService
from app.services.vietnamese.vn_stock_database import VNStockDatabase

logger = logging.getLogger(__name__)


class VNHistoricalYearData(BaseModel):
    """Vietnamese financial data for a single year."""
    year: str
    revenue: Optional[float] = None
    cogs: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    shareholders_equity: Optional[float] = None
    free_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    depreciation: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    status: str = "RETRIEVED"
    source: str = "vietnamese_data"  # VNDirect, CafeF, VNStockDatabase, Manual
    currency: str = "VND"


class VNCalculatedMetrics(BaseModel):
    """Calculated Vietnamese historical metrics."""
    revenue_cagr_3y: Optional[float] = None
    revenue_cagr_5y: Optional[float] = None
    avg_ebitda_margin: Optional[float] = None
    avg_net_margin: Optional[float] = None
    avg_roe: Optional[float] = None
    avg_roa: Optional[float] = None
    debt_to_equity_avg: Optional[float] = None
    asset_turnover_avg: Optional[float] = None


class VNStep3Response(BaseModel):
    """Vietnamese Step 3 response model."""
    ticker: str
    market_code: str
    historical_data: List[VNHistoricalYearData]
    calculated_metrics: VNCalculatedMetrics
    missing_years: List[str] = []
    missing_fields: Dict[str, List[str]] = {}
    warnings: List[str] = []
    data_quality_score: float = 0.0
    tt99_compliance: Optional[Dict] = None


class VNStep3HistoricalProcessor:
    """
    Processor for Vietnamese Step 3: Historical Financial Data.
    
    Responsibilities:
    - Fetch Vietnamese historical financials (3-5 years) per TT99 standards
    - Handle VND currency and local accounting standards
    - Fill missing years with estimates
    - Calculate growth rates and margins
    - Flag data gaps and TT99 compliance issues
    """
    
    MIN_YEARS_REQUIRED = 3
    IDEAL_YEARS = 5
    
    def __init__(
        self, 
        vn_ticker_service: Optional[VietnameseTickerService] = None,
        vn_stock_db: Optional[VNStockDatabase] = None
    ):
        self.vn_ticker_service = vn_ticker_service or VietnameseTickerService()
        self.vn_stock_db = vn_stock_db or VNStockDatabase()
    
    async def validate_ticker(
        self,
        ticker: str,
        market: str = "vietnamese"
    ) -> tuple[bool, str]:
        """
        Validate that a Vietnamese ticker has sufficient historical data.
        
        Args:
            ticker: Vietnamese ticker symbol
            market: Market type
            
        Returns:
            Tuple of (is_valid, message)
        """
        logger.info(f"Validating Vietnamese ticker '{ticker}' for historical data")
        
        try:
            # Process historical data
            response = self.process_historical_data(ticker, market)
            
            if response.data_quality_score >= 0.6:
                return True, f"Ticker {ticker} has sufficient historical data (score: {response.data_quality_score:.2f})"
            elif len(response.historical_data) >= self.MIN_YEARS_REQUIRED:
                return True, f"Ticker {ticker} has minimum required years but some data gaps"
            else:
                return False, f"Insufficient historical data for {ticker}. Need at least {self.MIN_YEARS_REQUIRED} years."
                
        except Exception as e:
            logger.error(f"Validation error for {ticker}: {str(e)}")
            return False, f"Validation failed: {str(e)}"
    
    def process_historical_data(
        self,
        ticker: str,
        market: str = "vietnamese"
    ) -> VNStep3Response:
        """
        Process Vietnamese historical financial data for a ticker.
        
        Args:
            ticker: Vietnamese ticker symbol
            market: Market type
            
        Returns:
            VNStep3Response with historical data and metrics
        """
        logger.info(f"Processing Vietnamese historical data for ticker='{ticker}'")
        
        # Determine market code
        market_code = "VN"
        if ".HA" in ticker.upper():
            market_code = "HA"
            ticker_clean = ticker.replace(".HA", "").upper()
        elif ".VC" in ticker.upper():
            market_code = "VC"
            ticker_clean = ticker.replace(".VC", "").upper()
        elif ".VN" in ticker.upper():
            ticker_clean = ticker.replace(".VN", "").upper()
        else:
            ticker_clean = ticker.upper()
        
        # Fetch comprehensive Vietnamese data
        ticker_data = self.vn_ticker_service.fetch_vietnamese_data_enhanced(
            ticker_clean, 
            market_code,
            include_peers=False,
            include_index_data=False
        )
        
        if not ticker_data.get('success'):
            return VNStep3Response(
                ticker=ticker_clean,
                market_code=market_code,
                historical_data=[],
                calculated_metrics=VNCalculatedMetrics(),
                missing_years=[f"All years for {ticker}"],
                warnings=[f"Could not fetch any data for {ticker}"],
                data_quality_score=0.0
            )
        
        # Build historical year data
        historical_data_points: List[VNHistoricalYearData] = []
        missing_years: List[str] = []
        missing_fields: Dict[str, List[str]] = {}
        warnings: List[str] = []
        
        # Extract financials
        financials = ticker_data.get('financials', {})
        years_available = []
        
        if financials is not None:
            # Get available years from financial statements
            if hasattr(financials, 'columns'):
                years_available = list(financials.columns)
            elif isinstance(financials, dict):
                years_available = list(financials.keys())
            
            # Process each year
            for year in years_available[-5:]:  # Last 5 years
                try:
                    year_data = self._extract_year_data(financials, year, ticker_data)
                    historical_data_points.append(year_data)
                    
                    # Track missing fields
                    for field in ['revenue', 'ebitda', 'net_income', 'total_assets', 'shareholders_equity']:
                        if getattr(year_data, field) is None:
                            if field not in missing_fields:
                                missing_fields[field] = []
                            missing_fields[field].append(str(year))
                    
                except Exception as e:
                    logger.warning(f"Error extracting data for year {year}: {e}")
                    missing_years.append(str(year))
                    warnings.append(f"Could not extract data for year {year}")
        
        # If no data from API, try VNStockDatabase
        if not historical_data_points:
            logger.info(f"Trying VNStockDatabase for {ticker_clean}")
            db_data = self.vn_stock_db.get_financial_statements(ticker_clean)
            if db_data:
                historical_data_points = self._convert_db_to_historical_data(db_data)
        
        # Calculate metrics
        calculated_metrics = self._calculate_vn_metrics(historical_data_points)
        
        # Check TT99 compliance
        tt99_compliance = self._check_tt99_compliance(historical_data_points)
        
        # Calculate data quality score
        total_possible = len(historical_data_points) * 11  # 11 key fields per year
        actual_filled = sum(
            sum(1 for field in ['revenue', 'cogs', 'gross_profit', 'ebitda', 'ebit', 
                               'net_income', 'total_assets', 'total_debt', 'shareholders_equity',
                               'free_cash_flow', 'capex'] 
                if getattr(year, field) is not None)
            for year in historical_data_points
        )
        data_quality_score = (actual_filled / total_possible * 100) if total_possible > 0 else 0
        
        # Add warnings for data quality
        if data_quality_score < 70:
            warnings.append(f"Low data quality score ({data_quality_score:.1f}%). Consider manual entry.")
        
        if len(historical_data_points) < self.MIN_YEARS_REQUIRED:
            warnings.append(f"Only {len(historical_data_points)} years available. Minimum {self.MIN_YEARS_REQUIRED} recommended.")
        
        return VNStep3Response(
            ticker=ticker_clean,
            market_code=market_code,
            historical_data=historical_data_points,
            calculated_metrics=calculated_metrics,
            missing_years=missing_years,
            missing_fields=missing_fields,
            warnings=warnings,
            data_quality_score=data_quality_score,
            tt99_compliance=tt99_compliance
        )
    
    def _extract_year_data(self, financials, year, ticker_data: Dict) -> VNHistoricalYearData:
        """Extract data for a specific year from financials."""
        # Extract based on data structure
        if hasattr(financials, 'loc'):
            # DataFrame format
            row = financials.loc[:, year] if year in financials.columns else {}
        elif isinstance(financials, dict):
            row = financials.get(year, {})
        else:
            row = {}
        
        # Map Vietnamese accounting terms to standard fields
        revenue = self._get_value(row, ['Revenue', 'Net Revenue', 'Doanh thu thuần'])
        cogs = self._get_value(row, ['Cost of Goods Sold', 'COGS', 'Giá vốn hàng bán'])
        gross_profit = self._get_value(row, ['Gross Profit', 'Lợi nhuận gộp'])
        ebitda = self._get_value(row, ['EBITDA', 'EBITDA Adjusted'])
        ebit = self._get_value(row, ['Operating Income', 'EBIT', 'Lợi nhuận thuần từ HĐKD'])
        net_income = self._get_value(row, ['Net Income', 'Profit After Tax', 'Lợi nhuận sau thuế'])
        total_assets = self._get_value(row, ['Total Assets', 'Tổng tài sản'])
        total_debt = self._get_value(row, ['Total Debt', 'Nợ vay'])
        shareholders_equity = self._get_value(row, ["Shareholders' Equity", 'Vốn chủ sở hữu'])
        capex = self._get_value(row, ['Capital Expenditure', 'CAPEX', 'Mua sắm TSCĐ'])
        depreciation = self._get_value(row, ['Depreciation', 'Khấu hao'])
        
        # Calculate FCF if possible
        operating_cash_flow = self._get_value(row, ['Operating Cash Flow', 'Lưu chuyển tiền từ HĐKD'])
        free_cash_flow = None
        if operating_cash_flow and capex:
            free_cash_flow = operating_cash_flow - abs(capex)
        
        return VNHistoricalYearData(
            year=str(year),
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            ebitda=ebitda,
            ebit=ebit,
            net_income=net_income,
            total_assets=total_assets,
            total_debt=total_debt,
            shareholders_equity=shareholders_equity,
            free_cash_flow=free_cash_flow,
            capex=capex,
            depreciation=depreciation,
            operating_cash_flow=operating_cash_flow,
            status="RETRIEVED" if revenue else "PARTIAL",
            source="vietnamese_data",
            currency="VND"
        )
    
    def _get_value(self, row, field_names: List[str]) -> Optional[float]:
        """Get value from row trying multiple field names."""
        for field in field_names:
            if hasattr(row, 'get'):
                val = row.get(field)
            else:
                val = getattr(row, field, None)
            
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return None
    
    def _calculate_vn_metrics(self, historical_data: List[VNHistoricalYearData]) -> VNCalculatedMetrics:
        """Calculate Vietnamese historical metrics."""
        if len(historical_data) < 2:
            return VNCalculatedMetrics()
        
        # Sort by year
        sorted_data = sorted(historical_data, key=lambda x: x.year)
        
        # Revenue CAGR calculations
        revenue_cagr_3y = None
        revenue_cagr_5y = None
        
        revenues = [d.revenue for d in sorted_data if d.revenue]
        if len(revenues) >= 3:
            n = min(3, len(revenues))
            revenue_cagr_3y = ((revenues[-1] / revenues[-n]) ** (1/(n-1))) - 1
        
        if len(revenues) >= 5:
            revenue_cagr_5y = ((revenues[-1] / revenues[-5]) ** (1/4)) - 1
        
        # Average margins
        ebitda_margins = [d.ebitda/d.revenue for d in sorted_data if d.ebitda and d.revenue and d.revenue > 0]
        avg_ebitda_margin = sum(ebitda_margins)/len(ebitda_margins) if ebitda_margins else None
        
        net_margins = [d.net_income/d.revenue for d in sorted_data if d.net_income and d.revenue and d.revenue > 0]
        avg_net_margin = sum(net_margins)/len(net_margins) if net_margins else None
        
        # Average ROE and ROA
        roes = [d.net_income/d.shareholders_equity for d in sorted_data if d.net_income and d.shareholders_equity and d.shareholders_equity > 0]
        avg_roe = sum(roes)/len(roes) if roes else None
        
        roas = [d.net_income/d.total_assets for d in sorted_data if d.net_income and d.total_assets and d.total_assets > 0]
        avg_roa = sum(roas)/len(roas) if roas else None
        
        # Average D/E
        de_ratios = [d.total_debt/d.shareholders_equity for d in sorted_data if d.total_debt and d.shareholders_equity and d.shareholders_equity > 0]
        debt_to_equity_avg = sum(de_ratios)/len(de_ratios) if de_ratios else None
        
        # Asset turnover
        asset_turnovers = [d.revenue/d.total_assets for d in sorted_data if d.revenue and d.total_assets and d.total_assets > 0]
        asset_turnover_avg = sum(asset_turnovers)/len(asset_turnovers) if asset_turnovers else None
        
        return VNCalculatedMetrics(
            revenue_cagr_3y=revenue_cagr_3y * 100 if revenue_cagr_3y else None,
            revenue_cagr_5y=revenue_cagr_5y * 100 if revenue_cagr_5y else None,
            avg_ebitda_margin=avg_ebitda_margin * 100 if avg_ebitda_margin else None,
            avg_net_margin=avg_net_margin * 100 if avg_net_margin else None,
            avg_roe=avg_roe * 100 if avg_roe else None,
            avg_roa=avg_roa * 100 if avg_roa else None,
            debt_to_equity_avg=debt_to_equity_avg,
            asset_turnover_avg=asset_turnover_avg
        )
    
    def _check_tt99_compliance(self, historical_data: List[VNHistoricalYearData]) -> Dict:
        """Check TT99 (Vietnamese accounting standards) compliance."""
        if not historical_data:
            return {'compliant': False, 'issues': ['No data available']}
        
        issues = []
        
        # Check for required TT99 fields
        required_fields = ['revenue', 'net_income', 'total_assets', 'shareholders_equity']
        for year_data in historical_data:
            for field in required_fields:
                if getattr(year_data, field) is None:
                    issues.append(f"Missing {field} for year {year_data.year}")
        
        # Check currency consistency
        if any(d.currency != 'VND' for d in historical_data):
            issues.append("Inconsistent currency - should be VND")
        
        return {
            'compliant': len(issues) == 0,
            'issues': issues,
            'years_covered': len(historical_data),
            'standard': 'TT99 (Vietnamese Accounting Standards)'
        }
    
    def _convert_db_to_historical_data(self, db_data: Dict) -> List[VNHistoricalYearData]:
        """Convert VNStockDatabase format to historical data points."""
        historical_data = []
        
        for year, data in db_data.items():
            historical_data.append(VNHistoricalYearData(
                year=str(year),
                revenue=data.get('revenue'),
                cogs=data.get('cogs'),
                gross_profit=data.get('gross_profit'),
                ebitda=data.get('ebitda'),
                ebit=data.get('ebit'),
                net_income=data.get('net_income'),
                total_assets=data.get('total_assets'),
                total_debt=data.get('total_debt'),
                shareholders_equity=data.get('equity'),
                free_cash_flow=data.get('fcf'),
                capex=data.get('capex'),
                depreciation=data.get('depreciation'),
                status="RETRIEVED_FROM_DB",
                source="VNStockDatabase",
                currency="VND"
            ))
        
        return sorted(historical_data, key=lambda x: x.year)
