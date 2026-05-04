"""
Vietnamese Input Manager Service Layer

This module provides the service layer for Vietnamese stock valuation workflows.
It enforces strict separation from international workflows by:

1. Using VND currency throughout (no USD conversions)
2. Using Vietnam-specific data sources (vndirect, cafef, VNStockDatabase)
3. Applying Vietnam-specific parameters (risk-free rates, tax rates, market premiums)
4. Validating HOSE/HNX/UPCOM ticker formats exclusively

NO CROSS-CONTAMINATION:
- Does NOT import yfinance or international services
- Does NOT use international risk-free rates or market premiums
- Does NOT accept non-Vietnamese tickers
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import date

from app.models.vietnamese_inputs import (
    VietnameseDCFRequest,
    VietnameseCompsSelectionRequest,
    VietnameseCompsValuationRequest,
    VietnameseDuPontRequest,
    VNDuPontComponents,
    VNPeerMultiple,
    VNFinancialData,
    VNExchange,
    VNSector
)
from app.services.vietnam.vn_stock_database import get_vn_stock_database, VNStockDatabase
from app.services.vietnam.vnd_financial_parser import parse_vn_financials_from_dict

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Vietnam-Specific Constants
# ──────────────────────────────────────────────────────────────────────────────

VIETNAM_CORPORATE_TAX_RATE = 0.20  # 20% standard corporate tax rate
VIETNAM_RISK_FREE_RATE_DEFAULT = 0.068  # ~6.8% (10-year government bond)
VIETNAM_MARKET_RISK_PREMIUM_DEFAULT = 0.075  # ~7.5% Vietnam ERP
VIETNAM_INFLATION_TARGET = 0.04  # 4% State Bank of Vietnam target

# Exchange rates (VND per USD, for reference only - calculations stay in VND)
USD_VND_RATE = 24500  # Approximate rate


class VietnameseInputManager:
    """
    Service layer for Vietnamese stock valuation inputs.
    
    This class handles:
    1. Building DCF requests from Vietnamese financial data
    2. Building Comps requests with peer filtering from VNINDEX/VN30
    3. Building DuPont requests from TT99 financial statements
    4. IQR outlier filtering for Vietnamese peer multiples
    
    All operations use VND currency and Vietnam-specific parameters.
    """
    
    def __init__(self):
        """Initialize with Vietnamese stock database."""
        self.vn_db: VNStockDatabase = get_vn_stock_database()
    
    # ──────────────────────────────────────────────────────────────────────────
    # DCF Input Building
    # ──────────────────────────────────────────────────────────────────────────
    
    def build_vn_dcf_request(
        self,
        ticker: str,
        company_name: str,
        exchange: str,
        sector: str,
        current_price_vnd: float,
        shares_outstanding: float,
        financial_data: Optional[Dict[str, Any]] = None,
        risk_free_rate_vn: Optional[float] = None,
        market_risk_premium_vn: Optional[float] = None,
        beta: Optional[float] = None,
        terminal_growth_rate: Optional[float] = None,
        forecast_years: int = 5,
        wacc_override: Optional[float] = None
    ) -> VietnameseDCFRequest:
        """
        Build a Vietnamese DCF request from raw data.
        
        Uses Vietnam-specific risk-free rates and market premiums.
        Validates ticker format against HOSE/HNX/UPCOM standards.
        
        Args:
            ticker: Vietnamese ticker symbol
            company_name: Company name
            exchange: Stock exchange (HOSE, HNX, UPCOM)
            sector: Industry sector
            current_price_vnd: Current stock price in VND
            shares_outstanding: Number of outstanding shares
            financial_data: Optional dict with financial metrics
            risk_free_rate_vn: Override default VN risk-free rate
            market_risk_premium_vn: Override default VN market risk premium
            beta: Stock beta (default: 1.0)
            terminal_growth_rate: Terminal growth rate
            forecast_years: Forecast horizon
            wacc_override: Optional custom WACC
            
        Returns:
            VietnameseDCFRequest object ready for DCF engine
            
        Raises:
            ValueError: If ticker is invalid or not Vietnamese
        """
        # Map string exchange to enum
        try:
            vn_exchange = VNExchange[exchange.upper()]
        except KeyError:
            raise ValueError(f"Invalid Vietnamese exchange: {exchange}. Must be HOSE, HNX, or UPCOM")
        
        # Map string sector to enum
        try:
            vn_sector = VNSector[sector.replace(' ', '_').upper()]
        except KeyError:
            vn_sector = VNSector.OTHER
        
        return VietnameseDCFRequest(
            ticker=ticker,
            company_name=company_name,
            exchange=vn_exchange,
            sector=vn_sector,
            current_price_vnd=current_price_vnd,
            shares_outstanding=shares_outstanding,
            risk_free_rate_vn=risk_free_rate_vn or VIETNAM_RISK_FREE_RATE_DEFAULT,
            market_risk_premium_vn=market_risk_premium_vn or VIETNAM_MARKET_RISK_PREMIUM_DEFAULT,
            beta=beta or 1.0,
            terminal_growth_rate=terminal_growth_rate or 0.03,
            forecast_years=forecast_years,
            wacc_override=wacc_override,
            corporate_tax_rate=VIETNAM_CORPORATE_TAX_RATE
        )
    
    def build_vn_dcf_from_financials(
        self,
        ticker: str,
        financials: VNFinancialData,
        beta: Optional[float] = None,
        wacc_override: Optional[float] = None
    ) -> VietnameseDCFRequest:
        """
        Build Vietnamese DCF request from parsed financial data.
        
        Extracts necessary information from VNFinancialData object.
        
        Args:
            ticker: Vietnamese ticker
            financials: Parsed Vietnamese financial data
            beta: Optional beta override
            wacc_override: Optional WACC override
            
        Returns:
            VietnameseDCFRequest
        """
        # Get stock info from database if available
        stock_info = self.vn_db.get_stock(ticker)
        
        company_name = stock_info.company_name_en if stock_info else f"{ticker} Joint Stock Company"
        exchange = stock_info.exchange.value if stock_info and stock_info.exchange else "HOSE"
        sector = stock_info.sector.value if stock_info and stock_info.sector else "OTHER"
        
        return self.build_vn_dcf_request(
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            sector=sector,
            current_price_vnd=financials.current_price_vnd or 0,
            shares_outstanding=financials.shares_outstanding or 0,
            financial_data=financials.model_dump(),
            beta=beta,
            wacc_override=wacc_override
        )
    
    # ──────────────────────────────────────────────────────────────────────────
    # Comps Input Building
    # ──────────────────────────────────────────────────────────────────────────
    
    def build_vn_comps_selection_request(
        self,
        target_ticker: str,
        peer_list: Optional[List[str]] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        min_market_cap_vnd: Optional[float] = None,
        max_peers: int = 10,
        include_vn30_only: bool = False
    ) -> VietnameseCompsSelectionRequest:
        """
        Build Vietnamese comps selection criteria.
        
        Handles peer selection from VNINDEX, VN30, or local sector indices.
        
        Args:
            target_ticker: Target company ticker
            peer_list: Optional explicit peer list
            sector: Sector filter
            industry: Sub-industry filter
            min_market_cap_vnd: Minimum market cap in billion VND
            max_peers: Maximum peers to include
            include_vn30_only: Filter to VN30 constituents only
            
        Returns:
            VietnameseCompsSelectionRequest
        """
        vn_sector = None
        if sector:
            try:
                vn_sector = VNSector[sector.replace(' ', '_').upper()]
            except KeyError:
                vn_sector = VNSector.OTHER
        
        return VietnameseCompsSelectionRequest(
            target_ticker=target_ticker,
            peer_list=peer_list,
            sector=vn_sector,
            industry=industry,
            min_market_cap_vnd=min_market_cap_vnd,
            max_peers=max_peers,
            include_vn30_only=include_vn30_only
        )
    
    def build_vn_comps_valuation_request(
        self,
        target_ticker: str,
        target_company_name: str,
        sector: str,
        target_revenue_vnd: float,
        target_ebitda_vnd: float,
        target_net_income_vnd: float,
        target_eps_vnd: float,
        target_book_value_vnd: float,
        peer_multiples: List[Dict[str, Any]],
        apply_outlier_filtering: bool = True,
        iqr_multiplier: float = 1.5,
        outlier_metric: str = "ev_ebitda_ltm"
    ) -> VietnameseCompsValuationRequest:
        """
        Build Vietnamese comps valuation request.
        
        Validates peer data and applies IQR outlier filtering if enabled.
        
        Args:
            target_ticker: Target ticker
            target_company_name: Target company name
            sector: Sector classification
            target_revenue_vnd: Target revenue (billion VND)
            target_ebitda_vnd: Target EBITDA (billion VND)
            target_net_income_vnd: Target net income (billion VND)
            target_eps_vnd: Target EPS (VND)
            target_book_value_vnd: Target book value (billion VND)
            peer_multiples: List of peer multiple dicts
            apply_outlier_filtering: Enable IQR filtering
            iqr_multiplier: IQR multiplier for outliers
            outlier_metric: Metric for outlier detection
            
        Returns:
            VietnameseCompsValuationRequest with filtered peers
        """
        # Map sector
        try:
            vn_sector = VNSector[sector.replace(' ', '_').upper()]
        except KeyError:
            vn_sector = VNSector.OTHER
        
        # Convert peer dicts to VNPeerMultiple objects
        validated_peers: List[VNPeerMultiple] = []
        for peer_dict in peer_multiples:
            try:
                peer = VNPeerMultiple(**peer_dict)
                validated_peers.append(peer)
            except Exception as e:
                logger.warning(f"Skipping invalid peer data: {e}")
                continue
        
        if len(validated_peers) < 3:
            raise ValueError(
                f"Need at least 3 valid peers, got {len(validated_peers)}. "
                "Vietnamese comps analysis requires minimum 3 comparable companies."
            )
        
        # Apply outlier filtering if enabled
        if apply_outlier_filtering and len(validated_peers) >= 5:
            validated_peers = self._apply_iqr_outlier_filtering(
                peers=validated_peers,
                metric=outlier_metric,
                iqr_multiplier=iqr_multiplier
            )
        
        if len(validated_peers) < 3:
            logger.warning(
                f"After outlier filtering, only {len(validated_peers)} peers remain. "
                "Proceeding with reduced peer set."
            )
        
        return VietnameseCompsValuationRequest(
            target_ticker=target_ticker,
            target_company_name=target_company_name,
            sector=vn_sector,
            target_revenue_vnd=target_revenue_vnd,
            target_ebitda_vnd=target_ebitda_vnd,
            target_net_income_vnd=target_net_income_vnd,
            target_eps_vnd=target_eps_vnd,
            target_book_value_vnd=target_book_value_vnd,
            peer_multiples=validated_peers,
            apply_outlier_filtering=apply_outlier_filtering,
            iqr_multiplier=iqr_multiplier,
            outlier_metric=outlier_metric
        )
    
    def _apply_iqr_outlier_filtering(
        self,
        peers: List[VNPeerMultiple],
        metric: str = "ev_ebitda_ltm",
        iqr_multiplier: float = 1.5
    ) -> List[VNPeerMultiple]:
        """
        Apply IQR-based outlier filtering to peer multiples.
        
        Filters out peers whose multiples fall outside Q1 - 1.5*IQR to Q3 + 1.5*IQR.
        
        Args:
            peers: List of peer multiples
            metric: Metric to filter on (e.g., 'ev_ebitda_ltm', 'pe_ltm')
            iqr_multiplier: IQR multiplier (default 1.5)
            
        Returns:
            Filtered list of peers without outliers
        """
        if len(peers) < 5:
            return peers  # Not enough data for meaningful IQR calculation
        
        # Extract metric values
        values = []
        for peer in peers:
            value = getattr(peer, metric, None)
            if value is not None and value > 0:
                values.append((peer, value))
        
        if len(values) < 5:
            return peers
        
        # Sort by value
        values.sort(key=lambda x: x[1])
        sorted_values = [v[1] for v in values]
        
        # Calculate quartiles
        n = len(sorted_values)
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        # Calculate bounds
        lower_bound = q1 - (iqr_multiplier * iqr)
        upper_bound = q3 + (iqr_multiplier * iqr)
        
        # Filter peers
        filtered_peers = [
            peer for peer, value in values
            if lower_bound <= value <= upper_bound
        ]
        
        logger.info(
            f"IQR filtering on {metric}: Removed {len(peers) - len(filtered_peers)} outliers "
            f"(bounds: {lower_bound:.2f} - {upper_bound:.2f})"
        )
        
        return filtered_peers
    
    # ──────────────────────────────────────────────────────────────────────────
    # DuPont Input Building
    # ──────────────────────────────────────────────────────────────────────────
    
    def build_vn_dupont_request(
        self,
        ticker: str,
        company_name: str,
        exchange: str,
        years: List[int],
        financial_data_by_year: Optional[Dict[int, Dict[str, Any]]] = None,
        custom_ratios: Optional[Dict[int, Dict[str, float]]] = None
    ) -> VietnameseDuPontRequest:
        """
        Build Vietnamese DuPont analysis request.
        
        Parses TT99 financial statement data to calculate DuPont components.
        
        Args:
            ticker: Vietnamese ticker
            company_name: Company name
            exchange: Stock exchange
            years: List of fiscal years
            financial_data_by_year: Dict of year -> financial data
            custom_ratios: Optional pre-calculated ratios
            
        Returns:
            VietnameseDuPontRequest
        """
        # Map exchange
        try:
            vn_exchange = VNExchange[exchange.upper()]
        except KeyError:
            vn_exchange = VNExchange.HOSE
        
        # Parse custom ratios if provided
        parsed_ratios: Optional[Dict[int, VNDuPontComponents]] = None
        if custom_ratios:
            parsed_ratios = {}
            for year, ratio_dict in custom_ratios.items():
                try:
                    components = VNDuPontComponents(**ratio_dict)
                    parsed_ratios[int(year)] = components
                except Exception as e:
                    logger.warning(f"Invalid ratio data for year {year}: {e}")
        
        # Auto-calculate ratios from financial data if custom_ratios not provided
        if not parsed_ratios and financial_data_by_year:
            parsed_ratios = self._calculate_dupont_from_financials(financial_data_by_year)
        
        return VietnameseDuPontRequest(
            ticker=ticker,
            company_name=company_name,
            exchange=vn_exchange,
            years=years,
            custom_ratios=parsed_ratios
        )
    
    def _calculate_dupont_from_financials(
        self,
        financial_data_by_year: Dict[int, Dict[str, Any]]
    ) -> Dict[int, VNDuPontComponents]:
        """
        Calculate DuPont components from raw financial data.
        
        DuPont Formula: ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
        
        Args:
            financial_data_by_year: Dict of year -> financial metrics
            
        Returns:
            Dict of year -> VNDuPontComponents
        """
        results = {}
        
        for year, data in financial_data_by_year.items():
            try:
                # Extract required fields
                net_income = data.get('net_income')
                revenue = data.get('revenue')
                total_assets = data.get('total_assets')
                shareholders_equity = data.get('shareholders_equity')
                
                if all(v is not None and v > 0 for v in [revenue, total_assets, shareholders_equity]):
                    # Calculate components
                    net_profit_margin = net_income / revenue if revenue > 0 else 0
                    asset_turnover = revenue / total_assets if total_assets > 0 else 0
                    equity_multiplier = total_assets / shareholders_equity if shareholders_equity > 0 else 1
                    
                    # Create components object
                    components = VNDuPontComponents(
                        net_profit_margin=net_profit_margin,
                        asset_turnover=asset_turnover,
                        equity_multiplier=equity_multiplier,
                        net_income_vnd=net_income,
                        revenue_vnd=revenue,
                        total_assets_vnd=total_assets,
                        shareholders_equity_vnd=shareholders_equity
                    )
                    
                    results[year] = components
                    logger.debug(f"Calculated DuPont for {year}: ROE={components.roe:.2%}")
                    
            except Exception as e:
                logger.warning(f"Failed to calculate DuPont for year {year}: {e}")
                continue
        
        return results
    
    # ──────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_vn_peer_candidates(
        self,
        target_ticker: str,
        sector: Optional[VNSector] = None,
        min_market_cap_vnd: Optional[float] = None,
        vn30_only: bool = False
    ) -> List[VNStockDatabase]:
        """
        Get list of potential Vietnamese peer companies.
        
        Filters from VNINDEX, VN30, or sector indices.
        
        Args:
            target_ticker: Target company (excluded from results)
            sector: Sector filter
            min_market_cap_vnd: Minimum market cap
            vn30_only: Only return VN30 constituents
            
        Returns:
            List of potential peer stocks
        """
        # Get all stocks from database
        all_stocks = self.vn_db.get_all_stocks()
        
        # Filter candidates
        candidates = []
        for stock in all_stocks:
            # Skip target
            if stock.ticker == target_ticker:
                continue
            
            # VN30 filter
            if vn30_only and not stock.is_vn30:
                continue
            
            # Sector filter
            if sector and stock.sector != sector:
                continue
            
            # Market cap filter (if applicable)
            # Note: Would need market cap data from stock object
            
            candidates.append(stock)
        
        return candidates[:20]  # Limit to top 20 candidates


# Singleton instance
_vn_input_manager: Optional[VietnameseInputManager] = None


def get_vietnamese_input_manager() -> VietnameseInputManager:
    """Get or create VietnameseInputManager singleton."""
    global _vn_input_manager
    if _vn_input_manager is None:
        _vn_input_manager = VietnameseInputManager()
    return _vn_input_manager
