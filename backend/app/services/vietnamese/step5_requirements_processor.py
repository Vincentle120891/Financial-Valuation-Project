"""
Vietnamese Step 5: Requirements & Parameters Processor

Handles collection of valuation requirements and parameters for Vietnamese companies.
This step gathers all necessary inputs before data fetching, including:
- Forecast periods and growth assumptions
- Risk-free rates (Vietnamese government bonds)
- Market risk premiums (Vietnam-specific)
- Country risk premiums
- Tax rates (Vietnamese corporate tax)
- Currency settings (VND)
- Model-specific parameters

Maintains full Model Integrity by capturing every parameter explicitly.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import logging
from datetime import date

logger = logging.getLogger(__name__)


class VNRequirementsInput(BaseModel):
    """Input for Vietnamese requirements collection step."""
    session_id: str = Field(..., description="Session identifier")
    
    # DCF-specific parameters
    dcf_forecast_years: int = Field(
        default=5, 
        ge=3, le=10,
        description="Number of years for DCF forecast period"
    )
    dcf_terminal_growth_rate: float = Field(
        default=0.03, 
        ge=0.0, le=0.08,
        description="Terminal growth rate for DCF (typically close to GDP growth)"
    )
    dcf_risk_free_rate: float = Field(
        default=0.068, 
        ge=0.0, le=0.20,
        description="Risk-free rate (Vietnamese 10Y government bond yield)"
    )
    dcf_market_risk_premium: float = Field(
        default=0.075, 
        ge=0.0, le=0.15,
        description="Market risk premium for Vietnam"
    )
    dcf_country_risk_premium: float = Field(
        default=0.035, 
        ge=0.0, le=0.10,
        description="Country risk premium for Vietnam"
    )
    dcf_tax_rate: float = Field(
        default=0.20, 
        ge=0.0, le=0.50,
        description="Corporate tax rate in Vietnam (standard 20%)"
    )
    dcf_beta: Optional[float] = Field(
        default=None,
        ge=-2.0, le=3.0,
        description="Company beta (vs VNINDEX). If not provided, will be calculated later"
    )
    
    # DuPont-specific parameters
    dupont_peer_count: int = Field(
        default=5,
        ge=3, le=10,
        description="Number of peers for DuPont comparison"
    )
    dupont_industry_focus: Optional[str] = Field(
        default=None,
        description="Industry focus for DuPont analysis (e.g., 'Banking', 'Manufacturing')"
    )
    
    # Comps-specific parameters
    comps_peer_count: int = Field(
        default=5,
        ge=3, le=10,
        description="Number of comparable companies"
    )
    comps_multiples: List[str] = Field(
        default=["P/E", "P/B", "EV/EBITDA", "P/S"],
        description="Valuation multiples to use"
    )
    comps_liquidity_filter_days: int = Field(
        default=60,
        ge=30, le=252,
        description="Days for average volume liquidity filter (Vietnamese market)"
    )
    
    # General parameters
    currency: str = Field(
        default="VND",
        description="Currency for valuation (always VND for Vietnamese market)"
    )
    fiscal_year_end: str = Field(
        default="12-31",
        pattern=r"^\d{2}-\d{2}$",
        description="Fiscal year end date (MM-DD format)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "dcf_forecast_years": 5,
                "dcf_terminal_growth_rate": 0.03,
                "dcf_risk_free_rate": 0.068,
                "dcf_market_risk_premium": 0.075,
                "dcf_country_risk_premium": 0.035,
                "dcf_tax_rate": 0.20,
                "dupont_peer_count": 5,
                "comps_peer_count": 5,
                "comps_multiples": ["P/E", "P/B", "EV/EBITDA", "P/S"],
                "currency": "VND",
                "fiscal_year_end": "12-31"
            }
        }
    
    @validator('comps_multiples')
    def validate_multiples(cls, v):
        """Validate that only supported multiples are used."""
        allowed_multiples = {"P/E", "P/B", "EV/EBITDA", "P/S", "PEG", "P/FCF", "EV/Sales"}
        invalid = [m for m in v if m not in allowed_multiples]
        if invalid:
            raise ValueError(f"Unsupported multiples: {invalid}. Allowed: {allowed_multiples}")
        return v


class VNRequirementsOutput(BaseModel):
    """Output from Vietnamese requirements collection step."""
    session_id: str = Field(..., description="Session identifier")
    
    # Consolidated parameters by model
    dcf_parameters: Dict[str, Any] = Field(
        ..., 
        description="DCF-specific parameters with Vietnam adjustments"
    )
    dupont_parameters: Dict[str, Any] = Field(
        ..., 
        description="DuPont-specific parameters"
    )
    comps_parameters: Dict[str, Any] = Field(
        ..., 
        description="Comps-specific parameters"
    )
    
    # Validation results
    parameter_validation: Dict[str, bool] = Field(
        ..., 
        description="Validation status for each parameter group"
    )
    
    # Vietnam-specific context
    market_context: Dict[str, Any] = Field(
        ..., 
        description="Vietnamese market context and benchmarks"
    )
    
    # Tracking
    input_sources: Dict[str, str] = Field(
        ..., 
        description="Source tracking for all requirement inputs"
    )
    next_step: int = Field(..., description="Next step number (6)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "dcf_parameters": {
                    "forecast_years": 5,
                    "terminal_growth_rate": 0.03,
                    "risk_free_rate": 0.068,
                    "market_risk_premium": 0.075,
                    "country_risk_premium": 0.035,
                    "tax_rate": 0.20,
                    "wacc_components_included": True
                },
                "dupont_parameters": {
                    "peer_count": 5,
                    "metrics": ["roe", "profit_margin", "asset_turnover", "equity_multiplier"]
                },
                "comps_parameters": {
                    "peer_count": 5,
                    "multiples": ["P/E", "P/B", "EV/EBITDA", "P/S"],
                    "liquidity_filter_days": 60
                },
                "parameter_validation": {
                    "dcf": True,
                    "dupont": True,
                    "comps": True
                },
                "market_context": {
                    "market": "vietnamese",
                    "currency": "VND",
                    "currency_symbol": "₫",
                    "risk_free_rate_source": "Vietnamese 10Y Government Bond",
                    "gdp_growth_estimate": 0.055,
                    "inflation_rate": 0.04
                },
                "input_sources": {
                    "dcf_forecast_years": "manual",
                    "dcf_terminal_growth_rate": "manual",
                    "dcf_risk_free_rate": "manual",
                    "dcf_market_risk_premium": "manual",
                    "dcf_country_risk_premium": "manual",
                    "dcf_tax_rate": "manual"
                },
                "next_step": 6
            }
        }


class VNStep5RequirementsProcessor:
    """
    Processor for Vietnamese Step 5: Requirements & Parameters
    
    Collects and validates all valuation parameters specific to Vietnamese market,
    ensuring complete transparency and adherence to Model Integrity principles.
    """
    
    # Vietnamese market benchmarks (as of latest available data)
    VN_MARKET_BENCHMARKS = {
        "risk_free_rate": {
            "value": 0.068,  # 6.8% - Vietnamese 10Y government bond
            "source": "State Bank of Vietnam / Bloomberg",
            "last_updated": "2024"
        },
        "market_risk_premium": {
            "value": 0.075,  # 7.5% - Emerging market premium for Vietnam
            "source": "Damodaran / Local research",
            "note": "Higher than developed markets due to emerging market status"
        },
        "country_risk_premium": {
            "value": 0.035,  # 3.5% - Additional country risk for Vietnam
            "source": "Country risk rating agencies",
            "note": "Reflects political, economic, and currency risks"
        },
        "corporate_tax_rate": {
            "value": 0.20,  # 20% standard rate
            "source": "Vietnamese Tax Law",
            "note": "Standard rate; some sectors may have incentives"
        },
        "gdp_growth_estimate": {
            "value": 0.055,  # 5.5% projected GDP growth
            "source": "World Bank / IMF / Vietnamese government",
            "note": "Used as reference for terminal growth rate"
        },
        "inflation_rate": {
            "value": 0.04,  # 4% target inflation
            "source": "State Bank of Vietnam",
            "note": "Central bank inflation target"
        }
    }
    
    # Default multiples for Vietnamese market
    DEFAULT_COMPS_MULTIPLES = ["P/E", "P/B", "EV/EBITDA", "P/S"]
    
    # Supported multiples
    SUPPORTED_MULTIPLES = {"P/E", "P/B", "EV/EBITDA", "P/S", "PEG", "P/FCF", "EV/Sales"}
    
    def __init__(self, session_service=None):
        """Initialize with session service dependency."""
        self.session_service = session_service
        logger.info("VNStep5RequirementsProcessor initialized for Vietnamese market")
    
    async def process(self, input_data: VNRequirementsInput) -> VNRequirementsOutput:
        """
        Process Vietnamese valuation requirements.
        
        Args:
            input_data: Requirements input with all parameters
            
        Returns:
            Output with validated parameters and Vietnam market context
            
        Raises:
            ValueError: If parameters fail validation
        """
        logger.info(f"Processing Vietnamese requirements for session {input_data.session_id}")
        
        # Build model-specific parameter dictionaries
        dcf_params = self._build_dcf_parameters(input_data)
        dupont_params = self._build_dupont_parameters(input_data)
        comps_params = self._build_comps_parameters(input_data)
        
        # Validate all parameters
        validation_results = self._validate_parameters(
            dcf_params, dupont_params, comps_params
        )
        
        # Check for any validation failures
        if not all(validation_results.values()):
            failed = [k for k, v in validation_results.items() if not v]
            raise ValueError(f"Parameter validation failed for: {failed}")
        
        # Build Vietnam market context
        market_context = self._build_market_context(input_data)
        
        # Track input sources (all manual for this step)
        input_sources = self._track_input_sources(input_data)
        
        # Update session state if session service available
        if self.session_service:
            await self._update_session_state(
                input_data.session_id,
                dcf_params,
                dupont_params,
                comps_params,
                market_context,
                input_sources
            )
        
        return VNRequirementsOutput(
            session_id=input_data.session_id,
            dcf_parameters=dcf_params,
            dupont_parameters=dupont_params,
            comps_parameters=comps_params,
            parameter_validation=validation_results,
            market_context=market_context,
            input_sources=input_sources,
            next_step=6
        )
    
    def _build_dcf_parameters(self, input_data: VNRequirementsInput) -> Dict[str, Any]:
        """Build DCF-specific parameters dictionary."""
        return {
            "forecast_years": input_data.dcf_forecast_years,
            "terminal_growth_rate": input_data.dcf_terminal_growth_rate,
            "risk_free_rate": input_data.dcf_risk_free_rate,
            "market_risk_premium": input_data.dcf_market_risk_premium,
            "country_risk_premium": input_data.dcf_country_risk_premium,
            "tax_rate": input_data.dcf_tax_rate,
            "beta": input_data.dcf_beta,  # May be None, calculated later
            "wacc_components_included": True,
            "currency": input_data.currency,
            "currency_symbol": "₫",
            "fiscal_year_end": input_data.fiscal_year_end,
            
            # Derived values (for display/transparency)
            "equity_risk_premium": input_data.dcf_market_risk_premium + input_data.dcf_country_risk_premium,
            "reference_gdp_growth": self.VN_MARKET_BENCHMARKS["gdp_growth_estimate"]["value"],
            "reference_inflation": self.VN_MARKET_BENCHMARKS["inflation_rate"]["value"]
        }
    
    def _build_dupont_parameters(self, input_data: VNRequirementsInput) -> Dict[str, Any]:
        """Build DuPont-specific parameters dictionary."""
        return {
            "peer_count": input_data.dupont_peer_count,
            "industry_focus": input_data.dupont_industry_focus,
            "metrics": ["roe", "profit_margin", "asset_turnover", "equity_multiplier"],
            "currency": input_data.currency,
            "currency_symbol": "₫",
            "fiscal_year_end": input_data.fiscal_year_end,
            "market": "vietnamese"
        }
    
    def _build_comps_parameters(self, input_data: VNRequirementsInput) -> Dict[str, Any]:
        """Build Comps-specific parameters dictionary."""
        return {
            "peer_count": input_data.comps_peer_count,
            "multiples": input_data.comps_multiples,
            "liquidity_filter_days": input_data.comps_liquidity_filter_days,
            "currency": input_data.currency,
            "currency_symbol": "₫",
            "fiscal_year_end": input_data.fiscal_year_end,
            "market": "vietnamese",
            "exchange_filters": ["HOSE", "HNX", "UPCOM"]
        }
    
    def _validate_parameters(
        self,
        dcf_params: Dict[str, Any],
        dupont_params: Dict[str, Any],
        comps_params: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Validate all parameter groups.
        
        Returns:
            Dictionary with validation status for each parameter group
        """
        validation = {}
        
        # Validate DCF parameters
        try:
            # Terminal growth should not exceed GDP growth significantly
            gdp_growth = self.VN_MARKET_BENCHMARKS["gdp_growth_estimate"]["value"]
            if dcf_params["terminal_growth_rate"] > gdp_growth + 0.02:
                logger.warning(
                    f"Terminal growth rate {dcf_params['terminal_growth_rate']} "
                    f"exceeds Vietnam GDP growth {gdp_growth} by more than 2%"
                )
            
            # Risk-free rate should be reasonable
            if dcf_params["risk_free_rate"] < 0.01 or dcf_params["risk_free_rate"] > 0.20:
                raise ValueError("Risk-free rate out of reasonable range for Vietnam")
            
            validation["dcf"] = True
        except Exception as e:
            logger.error(f"DCF parameter validation failed: {e}")
            validation["dcf"] = False
        
        # Validate DuPont parameters
        try:
            if dupont_params["peer_count"] < 3:
                raise ValueError("DuPont requires at least 3 peers for meaningful comparison")
            validation["dupont"] = True
        except Exception as e:
            logger.error(f"DuPont parameter validation failed: {e}")
            validation["dupont"] = False
        
        # Validate Comps parameters
        try:
            if comps_params["peer_count"] < 3:
                raise ValueError("Comps requires at least 3 peers for meaningful comparison")
            
            if not comps_params["multiples"]:
                raise ValueError("At least one valuation multiple must be selected")
            
            validation["comps"] = True
        except Exception as e:
            logger.error(f"Comps parameter validation failed: {e}")
            validation["comps"] = False
        
        return validation
    
    def _build_market_context(self, input_data: VNRequirementsInput) -> Dict[str, Any]:
        """Build Vietnamese market context information."""
        return {
            "market": "vietnamese",
            "currency": input_data.currency,
            "currency_symbol": "₫",
            "risk_free_rate_source": self.VN_MARKET_BENCHMARKS["risk_free_rate"]["source"],
            "risk_free_rate_note": self.VN_MARKET_BENCHMARKS["risk_free_rate"]["note"],
            "market_premium_source": self.VN_MARKET_BENCHMARKS["market_risk_premium"]["source"],
            "market_premium_note": self.VN_MARKET_BENCHMARKS["market_risk_premium"]["note"],
            "country_risk_premium_note": self.VN_MARKET_BENCHMARKS["country_risk_premium"]["note"],
            "tax_rate_source": self.VN_MARKET_BENCHMARKS["corporate_tax_rate"]["source"],
            "gdp_growth_estimate": self.VN_MARKET_BENCHMARKS["gdp_growth_estimate"]["value"],
            "gdp_growth_source": self.VN_MARKET_BENCHMARKS["gdp_growth_estimate"]["source"],
            "inflation_rate": self.VN_MARKET_BENCHMARKS["inflation_rate"]["value"],
            "inflation_source": self.VN_MARKET_BENCHMARKS["inflation_rate"]["source"],
            "exchanges": ["HOSE", "HNX", "UPCOM"],
            "benchmark_index": "VNINDEX",
            "trading_currency": "VND",
            "fiscal_year_convention": "Calendar year (Jan-Dec)",
            "reporting_standards": "Vietnamese Accounting Standards (VAS) / IFRS convergence"
        }
    
    def _track_input_sources(self, input_data: VNRequirementsInput) -> Dict[str, str]:
        """Track source of all input parameters (all manual for this step)."""
        sources = {}
        
        # DCF parameters
        sources["dcf_forecast_years"] = "manual"
        sources["dcf_terminal_growth_rate"] = "manual"
        sources["dcf_risk_free_rate"] = "manual"
        sources["dcf_market_risk_premium"] = "manual"
        sources["dcf_country_risk_premium"] = "manual"
        sources["dcf_tax_rate"] = "manual"
        if input_data.dcf_beta is not None:
            sources["dcf_beta"] = "manual"
        
        # DuPont parameters
        sources["dupont_peer_count"] = "manual"
        if input_data.dupont_industry_focus:
            sources["dupont_industry_focus"] = "manual"
        
        # Comps parameters
        sources["comps_peer_count"] = "manual"
        sources["comps_multiples"] = "manual"
        sources["comps_liquidity_filter_days"] = "manual"
        
        # General parameters
        sources["currency"] = "manual"
        sources["fiscal_year_end"] = "manual"
        
        return sources
    
    async def _update_session_state(
        self,
        session_id: str,
        dcf_params: Dict[str, Any],
        dupont_params: Dict[str, Any],
        comps_params: Dict[str, Any],
        market_context: Dict[str, Any],
        sources: Dict[str, str]
    ) -> None:
        """Update session state with requirements data."""
        try:
            await self.session_service.update_session(session_id, {
                "dcf_parameters": dcf_params,
                "dupont_parameters": dupont_params,
                "comps_parameters": comps_params,
                "market_context": market_context,
                "current_step": 5,
                "step_5_completed": True
            })
            
            await self.session_service.add_input_sources(session_id, sources)
            
            logger.info(f"Updated session {session_id} with Vietnamese requirements")
        except Exception as e:
            logger.error(f"Failed to update session state for requirements: {e}")
    
    def get_market_benchmarks(self) -> Dict[str, Any]:
        """Get current Vietnamese market benchmarks."""
        return self.VN_MARKET_BENCHMARKS.copy()
    
    def get_supported_multiples(self) -> set:
        """Get set of supported valuation multiples."""
        return self.SUPPORTED_MULTIPLES.copy()
