"""
Vietnamese Step 4: Forecast Drivers Processor

Handles forecast driver inputs for Vietnamese companies across all 3 valuation models:
- DCF: Revenue growth, margins, capex, working capital assumptions
- DuPont: ROE decomposition ratios and trend analysis
- Trading Comps: Peer selection and valuation multiples

Vietnam-specific features:
- VND currency formatting
- TT99 compliance for financial metrics
- Vietnamese market growth expectations
- HOSE/HNX/UPCOM peer filtering
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)


class vn_ValuationModel(str, Enum):
    """Type of valuation model for Vietnamese market"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class vn_ForecastDriver(BaseModel):
    """Vietnamese forecast driver with VND context"""
    metric: str
    historical_avg: Optional[float] = None
    suggested_value: float
    min_reasonable: float
    max_reasonable: float
    rationale: str
    formula: str
    confidence: float
    status: str = "SUGGESTED"
    currency: str = "VND"
    tt99_compliant: bool = True


class vn_CompsInputs(BaseModel):
    """Inputs specific to Vietnamese Comps analysis"""
    peer_tickers: List[str] = []
    valuation_multiples: List[str] = ["P/E", "EV/EBITDA", "P/B", "P/S", "PEG"]
    apply_outlier_filter: bool = True
    exchange_filter: List[str] = ["HOSE", "HNX", "UPCOM"]
    liquidity_filter_days: int = 60  # 60-day average volume for VN market
    sector_match_required: bool = True


class vn_DuPontInputs(BaseModel):
    """Inputs specific to Vietnamese DuPont analysis"""
    years_to_analyze: int = 3
    include_trend_analysis: bool = True
    custom_ratios: Optional[Dict[str, float]] = None
    tt99_adjustments: bool = True  # Apply TT99 accounting adjustments
    peer_comparison_enabled: bool = True


class vn_Step4Response(BaseModel):
    """Vietnamese Step 4 response model"""
    ticker: str
    market_code: str  # VN, HA, VC
    valuation_model: vn_ValuationModel
    forecast_drivers: Optional[List[vn_ForecastDriver]] = None
    revenue_growth_forecast: Optional[List[Dict]] = None
    margin_assumptions: Optional[Dict] = None
    comps_inputs: Optional[vn_CompsInputs] = None
    dupont_inputs: Optional[vn_DuPontInputs] = None
    warnings: List[str] = []
    data_quality_score: float = 0.0
    model_specific_notes: str = ""
    currency: str = "VND"
    currency_symbol: str = "₫"


class vn_Step4ForecastProcessor:
    """
    Processor for Vietnamese Step 4: Forecast Drivers

    Handles model-specific forecast inputs for Vietnamese companies,
    ensuring TT99 compliance and VND currency formatting.

    Responsibilities:
    - Process DCF forecast drivers (revenue growth, margins, capex)
    - Configure DuPont analysis parameters
    - Set up Comps peer selection criteria
    - Apply Vietnam-specific adjustments and defaults
    - Validate data quality per TT99 standards
    """

    # Vietnam-specific default assumptions
    DEFAULT_REVENUE_GROWTH_VN = 0.10  # 10% average for Vietnamese market
    DEFAULT_EBITDA_MARGIN_VN = 0.15  # 15% typical EBITDA margin
    DEFAULT_TAX_RATE_VN = 0.20  # 20% corporate tax rate in Vietnam
    DEFAULT_CAPEX_RATIO_VN = 0.05  # 5% of revenue for capex
    DEFAULT_WC_RATIO_VN = 0.10  # 10% of revenue for working capital

    def process_forecast_drivers(
        self,
        ticker: str,
        historical_data: Dict,
        valuation_model: str = "DCF",
        market_code: str = "VN",
        peer_tickers: Optional[List[str]] = None
    ) -> vn_Step4Response:
        """
        Process forecast drivers for Vietnamese company.

        Args:
            ticker: Vietnamese ticker symbol
            historical_data: Historical financial metrics
            valuation_model: Model type (DCF, DUPONT, or COMPS)
            market_code: Vietnamese market code (VN, HA, VC)
            peer_tickers: Optional list of peer tickers for Comps

        Returns:
            vn_Step4Response with model-specific inputs

        Raises:
            ValueError: If unknown valuation model provided
        """
        logger.info(f"Processing Vietnamese forecast drivers for {ticker} using {valuation_model} model")

        try:
            model_enum = vn_ValuationModel(valuation_model.upper())
        except ValueError:
            raise ValueError(f"Unknown valuation model: {valuation_model}. Valid options: DCF, DUPONT, COMPS")

        if model_enum == vn_ValuationModel.DCF:
            return self._process_vn_dcf_inputs(ticker, historical_data, market_code)
        elif model_enum == vn_ValuationModel.COMPS:
            return self._process_vn_comps_inputs(ticker, historical_data, peer_tickers, market_code)
        elif model_enum == vn_ValuationModel.DUPONT:
            return self._process_vn_dupont_inputs(ticker, historical_data, market_code)
        else:
            raise ValueError(f"Unsupported valuation model: {valuation_model}")

    def _process_vn_dcf_inputs(
        self,
        ticker: str,
        historical_data: Dict,
        market_code: str = "VN"
    ) -> vn_Step4Response:
        """
        Process DCF inputs for Vietnamese company.

        Args:
            ticker: Vietnamese ticker
            historical_data: Historical financial data
            market_code: Market code

        Returns:
            vn_Step4Response with DCF forecast drivers
        """
        # Extract historical metrics with Vietnam context
        hist_growth = historical_data.get('revenue_cagr_3y', self.DEFAULT_REVENUE_GROWTH_VN)
        hist_margin = historical_data.get('avg_ebitda_margin', self.DEFAULT_EBITDA_MARGIN_VN)
        latest_revenue = historical_data.get('latest_revenue', 1000000000000)  # 1 trillion VND default

        # Calculate suggested values with Vietnam market adjustments
        # Vietnamese companies typically have higher growth but lower margins than developed markets
        suggested_growth = max(0.05, min(hist_growth * 0.85, 0.25))  # Conservative adjustment
        suggested_margin = max(0.10, min(hist_margin, 0.30))

        # Build forecast drivers with TT99 compliance
        drivers = [
            vn_ForecastDriver(
                metric="revenue_growth",
                historical_avg=hist_growth,
                suggested_value=suggested_growth,
                min_reasonable=0.0,
                max_reasonable=0.35,  # Higher max for emerging market
                rationale=f"Dựa trên CAGR 3 năm ({hist_growth:.1%}), điều chỉnh cho thị trường Việt Nam",
                formula="CAGR × 0.85 (điều chỉnh giảm)",
                confidence=0.70,  # Lower confidence for emerging market
                tt99_compliant=True
            ),
            vn_ForecastDriver(
                metric="ebitda_margin",
                historical_avg=hist_margin,
                suggested_value=suggested_margin,
                min_reasonable=0.05,
                max_reasonable=0.40,
                rationale="Biên lợi nhuận ổn định theo chuẩn TT99",
                formula="Bình quân lịch sử",
                confidence=0.75,
                tt99_compliant=True
            ),
            vn_ForecastDriver(
                metric="tax_rate",
                historical_avg=self.DEFAULT_TAX_RATE_VN,
                suggested_value=self.DEFAULT_TAX_RATE_VN,
                min_reasonable=0.15,
                max_reasonable=0.25,
                rationale="Thuế suất thuế TNDN 20% theo Luật Thuế Việt Nam",
                formula="Corporate tax rate Vietnam",
                confidence=0.95,
                tt99_compliant=True
            ),
            vn_ForecastDriver(
                metric="capex_to_revenue",
                historical_avg=self.DEFAULT_CAPEX_RATIO_VN,
                suggested_value=self.DEFAULT_CAPEX_RATIO_VN,
                min_reasonable=0.02,
                max_reasonable=0.15,
                rationale="Chi phí vốn điển hình cho công ty Việt Nam",
                formula="CAPEX / Revenue",
                confidence=0.65,
                tt99_compliant=True
            ),
            vn_ForecastDriver(
                metric="working_capital_to_revenue",
                historical_avg=self.DEFAULT_WC_RATIO_VN,
                suggested_value=self.DEFAULT_WC_RATIO_VN,
                min_reasonable=0.05,
                max_reasonable=0.20,
                rationale="Vốn lưu động điển hình",
                formula="Working Capital / Revenue",
                confidence=0.65,
                tt99_compliant=True
            )
        ]

        # Build revenue forecast (5 years in VND)
        revenue_forecast = []
        current_rev = latest_revenue
        for year in range(1, 6):
            projected_rev = current_rev * ((1 + suggested_growth) ** year)
            revenue_forecast.append({
                "year": year,
                "revenue": projected_rev,
                "revenue_vnd_billions": projected_rev / 1e9,  # Convert to billions for readability
                "growth_rate": suggested_growth,
                "currency": "VND"
            })

        # Margin assumptions
        margin_assumptions = {
            "ebitda_margin": suggested_margin,
            "tax_rate": self.DEFAULT_TAX_RATE_VN,
            "capex_ratio": self.DEFAULT_CAPEX_RATIO_VN,
            "working_capital_ratio": self.DEFAULT_WC_RATIO_VN,
            "currency": "VND"
        }

        # Calculate data quality score
        data_quality = self._calculate_dcf_data_quality(historical_data)

        return vn_Step4Response(
            ticker=ticker.upper(),
            market_code=market_code,
            valuation_model=vn_ValuationModel.DCF,
            forecast_drivers=drivers,
            revenue_growth_forecast=revenue_forecast,
            margin_assumptions=margin_assumptions,
            warnings=self._get_dcf_warnings(historical_data),
            data_quality_score=data_quality,
            model_specific_notes="Mô hình DCF yêu cầu dự báo dòng tiền, WACC, và giá trị terminal. Tuân thủ chuẩn TT99.",
            currency="VND",
            currency_symbol="₫"
        )

    def _process_vn_comps_inputs(
        self,
        ticker: str,
        historical_data: Dict,
        peer_tickers: Optional[List[str]] = None,
        market_code: str = "VN"
    ) -> vn_Step4Response:
        """
        Process Comps inputs for Vietnamese company.

        Args:
            ticker: Vietnamese ticker
            historical_data: Historical data
            peer_tickers: List of peer tickers
            market_code: Market code

        Returns:
            vn_Step4Response with Comps configuration
        """
        warnings = []
        data_quality = 85.0

        # Validate peer tickers
        if peer_tickers is None or len(peer_tickers) == 0:
            peer_tickers = []
            warnings.append("Chưa chọn công ty so sánh. Vui lòng chọn các công ty cùng ngành.")
            data_quality = 50.0
        elif len(peer_tickers) < 3:
            warnings.append(f"Chỉ có {len(peer_tickers)} công ty so sánh. Khuyến nghị tối thiểu 3 công ty.")
            data_quality = 65.0

        # Vietnam-specific Comps inputs
        vn_comps_inputs = vn_CompsInputs(
            peer_tickers=peer_tickers,
            valuation_multiples=["P/E", "EV/EBITDA", "P/B", "P/S", "PEG"],
            apply_outlier_filter=True,
            exchange_filter=["HOSE", "HNX", "UPCOM"],
            liquidity_filter_days=60,  # 60-day average volume
            sector_match_required=True
        )

        return vn_Step4Response(
            ticker=ticker.upper(),
            market_code=market_code,
            valuation_model=vn_ValuationModel.COMPS,
            comps_inputs=vn_comps_inputs,
            warnings=warnings,
            data_quality_score=data_quality,
            model_specific_notes="Mô hình Comps so sánh bội số định giá với các công ty cùng ngành trên HOSE/HNX/UPCOM.",
            currency="VND",
            currency_symbol="₫"
        )

    def _process_vn_dupont_inputs(
        self,
        ticker: str,
        historical_data: Dict,
        market_code: str = "VN"
    ) -> vn_Step4Response:
        """
        Process DuPont inputs for Vietnamese company.

        Args:
            ticker: Vietnamese ticker
            historical_data: Historical data
            market_code: Market code

        Returns:
            vn_Step4Response with DuPont configuration
        """
        warnings = []
        data_quality = 85.0

        # Check for required financial statements per TT99
        has_income_statement = any(key in historical_data for key in ['net_income', 'latest_net_income', 'revenue'])
        has_balance_sheet = any(key in historical_data for key in ['total_assets', 'shareholders_equity', 'equity'])

        if not has_income_statement:
            warnings.append("Thiếu dữ liệu báo cáo kết quả kinh doanh cho phân tích DuPont")
            data_quality -= 20.0
        if not has_balance_sheet:
            warnings.append("Thiếu dữ liệu bảng cân đối kế toán cho phân tích DuPont")
            data_quality -= 20.0

        # Vietnam-specific DuPont inputs
        vn_dupont_inputs = vn_DuPontInputs(
            years_to_analyze=3,
            include_trend_analysis=True,
            custom_ratios=None,
            tt99_adjustments=True,  # Apply TT99 adjustments
            peer_comparison_enabled=True
        )

        return vn_Step4Response(
            ticker=ticker.upper(),
            market_code=market_code,
            valuation_model=vn_ValuationModel.DUPONT,
            dupont_inputs=vn_dupont_inputs,
            warnings=warnings,
            data_quality_score=max(data_quality, 0.0),
            model_specific_notes="Mô hình DuPont phân tích ROE thành: Biên lợi nhuận ròng × Vòng quay tài sản × Đòn bẩy tài chính. Tuân thủ TT99.",
            currency="VND",
            currency_symbol="₫"
        )

    def _calculate_dcf_data_quality(self, historical_data: Dict) -> float:
        """
        Calculate data quality score for DCF inputs.

        Args:
            historical_data: Historical financial metrics

        Returns:
            Data quality score (0-100)
        """
        score = 100.0

        # Check for key metrics
        required_metrics = ['revenue_cagr_3y', 'avg_ebitda_margin', 'latest_revenue']
        for metric in required_metrics:
            if metric not in historical_data or historical_data[metric] is None:
                score -= 15.0

        # Bonus for additional metrics
        bonus_metrics = ['avg_net_margin', 'avg_roe', 'debt_to_equity_avg']
        for metric in bonus_metrics:
            if metric in historical_data and historical_data[metric] is not None:
                score += 5.0

        return max(min(score, 100.0), 0.0)

    def _get_dcf_warnings(self, historical_data: Dict) -> List[str]:
        """
        Generate warnings for DCF inputs.

        Args:
            historical_data: Historical financial metrics

        Returns:
            List of warning messages
        """
        warnings = []

        if 'revenue_cagr_3y' not in historical_data or historical_data.get('revenue_cagr_3y') is None:
            warnings.append("Thiếu dữ liệu tăng trưởng doanh thu 3 năm. Sử dụng mức trung bình thị trường.")

        if 'avg_ebitda_margin' not in historical_data or historical_data.get('avg_ebitda_margin') is None:
            warnings.append("Thiếu dữ liệu biên lợi nhuận EBITDA. Sử dụng ước tính ngành.")

        if historical_data.get('years_of_data', 0) < 3:
            warnings.append(f"Chỉ có {historical_data.get('years_of_data', 0)} năm dữ liệu. Khuyến nghị tối thiểu 3 năm để dự báo đáng tin cậy.")

        return warnings

    def get_default_assumptions(self, valuation_model: str) -> Dict:
        """
        Get default assumptions for a valuation model.

        Args:
            valuation_model: Model type (DCF, DUPONT, COMPS)

        Returns:
            Dictionary of default assumptions
        """
        if valuation_model.upper() == "DCF":
            return {
                "revenue_growth": self.DEFAULT_REVENUE_GROWTH_VN,
                "ebitda_margin": self.DEFAULT_EBITDA_MARGIN_VN,
                "tax_rate": self.DEFAULT_TAX_RATE_VN,
                "capex_ratio": self.DEFAULT_CAPEX_RATIO_VN,
                "working_capital_ratio": self.DEFAULT_WC_RATIO_VN,
                "currency": "VND"
            }
        elif valuation_model.upper() == "DUPONT":
            return {
                "years_to_analyze": 3,
                "tt99_adjustments": True,
                "peer_comparison_enabled": True
            }
        elif valuation_model.upper() == "COMPS":
            return {
                "peer_count_min": 3,
                "peer_count_recommended": 5,
                "multiples": ["P/E", "EV/EBITDA", "P/B", "P/S", "PEG"],
                "liquidity_filter_days": 60,
                "exchange_filter": ["HOSE", "HNX", "UPCOM"]
            }
        else:
            return {}