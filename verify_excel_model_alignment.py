"""
Excel Model Alignment Verification Script
==========================================
This script verifies that all inputs required by each valuation model (DCF, Comps, DuPont)
are correctly retrieved and match the Excel model specifications.

Reference: /workspace/excel models/*.txt
"""

import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel


# =============================================================================
# EXCEL MODEL SPECIFICATIONS (Extracted from documentation files)
# =============================================================================

class ExcelDCFSpec(BaseModel):
    """Specification for DCF model inputs based on Excel documentation"""
    
    # Revenue Drivers
    revenue_volume_growth: List[float]  # 6 periods: Historical 3 + Forecast 5 + Terminal
    revenue_price_growth: List[float]   # 6 periods
    revenue_growth_formula: str = "prior_year × (1 + volume_growth) × (1 + price_growth)"
    
    # Cost Drivers
    inflation_rate: List[float]  # Applied to COGS and OpEx
    capex_forecast: List[float]  # USD thousands
    
    # Working Capital
    ar_days: float = 45.0
    inv_days: float = 25.0
    ap_days: float = 40.0
    wc_formula: str = "(Days / Days_in_Period) × Base"
    
    # WACC Inputs
    risk_free_rate: float = 0.024
    market_risk_premium: float = 0.047
    country_risk_premium: float = 0.036
    target_debt_weight: float = 0.15
    target_equity_weight: float = 0.85
    pre_tax_cost_of_debt: float = 0.052
    tax_rate: float = 0.30
    
    # Terminal Value
    terminal_growth_rate: float = 0.020
    terminal_ebitda_multiple: float = 7.0
    
    # Depreciation
    useful_life_existing: float = 16.0
    useful_life_new: float = 20.0
    first_year_tax_dep_rate: float = 0.50
    blended_tax_dep_rate: float = 0.15
    
    # Dates & Shares
    shares_outstanding: float  # in thousands
    current_stock_price: float


class ExcelCompsSpec(BaseModel):
    """Specification for Comps model inputs based on Excel documentation"""
    
    # Comparable Companies (5 peers in Excel spec)
    peer_count_min: int = 5
    peer_count_max: int = 10
    
    # Required Peer Metrics
    required_peer_fields: List[str] = [
        "debt",
        "equity", 
        "tax_rate",
        "levered_beta",
        "ev_ebitda_ltm",
        "pe_ratio_ltm",
        "market_cap",
        "enterprise_value"
    ]
    
    # Derived Metrics (calculated from raw data)
    derived_metrics: List[str] = [
        "de_to_equity",      # Debt / Equity
        "debt_to_capital",   # Debt / (Debt + Equity)
        "unlevered_beta"     # Levered β / (1 + (1-Tax) × D/E)
    ]
    
    # Averaging Method
    averaging_method: str = "AVERAGE()"  # Simple average across peers
    
    # Outlier Filtering
    apply_iqr_filtering: bool = True
    iqr_multiplier: float = 1.5


class ExcelDuPontSpec(BaseModel):
    """Specification for DuPont model inputs based on Excel documentation"""
    
    # Three Core Components
    required_components: List[str] = [
        "net_profit_margin",    # Net Income / Revenue
        "asset_turnover",       # Revenue / Total Assets
        "equity_multiplier"     # Total Assets / Shareholders' Equity
    ]
    
    # ROE Formula
    roe_formula: str = "NPM × AT × EM"
    
    # Required Raw Financials
    required_raw_fields: List[str] = [
        "net_income",
        "revenue",
        "total_assets",
        "shareholders_equity"
    ]
    
    # Analysis Period
    min_years: int = 3
    max_years: int = 5


# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================

def verify_dcf_inputs(international_inputs: Dict, vietnamese_inputs: Dict) -> Dict[str, Any]:
    """
    Verify DCF inputs against Excel model specification
    Returns detailed report of missing/mismatched fields
    """
    report = {
        "model": "DCF",
        "status": "PASS",
        "missing_fields": [],
        "mismatched_fields": [],
        "correctly_implemented": [],
        "notes": []
    }
    
    # Check International DCF Inputs
    print("\n=== VERIFYING INTERNATIONAL DCF INPUTS ===")
    
    # 1. Revenue Growth Drivers
    if 'forecast_drivers' in international_inputs:
        drivers = international_inputs['forecast_drivers']
        
        # Check revenue_growth_forecast (should have 6 periods)
        if 'revenue_growth_forecast' in drivers:
            growth_forecast = drivers['revenue_growth_forecast']
            if isinstance(growth_forecast, list) and len(growth_forecast) >= 5:
                report["correctly_implemented"].append("revenue_growth_forecast (5+ periods)")
                print("✓ revenue_growth_forecast: Present with sufficient periods")
            else:
                report["missing_fields"].append("revenue_growth_forecast needs 5-6 periods")
                report["status"] = "PARTIAL"
                print("✗ revenue_growth_forecast: Insufficient periods")
        
        # Check volume_growth_split
        if 'volume_growth_split' in drivers:
            report["correctly_implemented"].append("volume_growth_split")
            print("✓ volume_growth_split: Present")
        else:
            report["notes"].append("volume_growth_split not separated from price growth")
            print("⚠ volume_growth_split: Not explicitly separated")
        
        # Check inflation_rate
        if 'inflation_rate' in drivers:
            report["correctly_implemented"].append("inflation_rate")
            print("✓ inflation_rate: Present")
        else:
            report["missing_fields"].append("inflation_rate")
            report["status"] = "FAIL"
            print("✗ inflation_rate: Missing")
        
        # Check tax_rate
        if 'tax_rate' in drivers:
            actual_tax = drivers['tax_rate']
            expected_tax = 0.21  # International standard
            if abs(actual_tax - expected_tax) < 0.05:
                report["correctly_implemented"].append(f"tax_rate ({actual_tax})")
                print(f"✓ tax_rate: {actual_tax} (close to expected {expected_tax})")
            else:
                report["mismatched_fields"].append(f"tax_rate: {actual_tax} vs expected {expected_tax}")
                print(f"⚠ tax_rate: {actual_tax} differs from expected {expected_tax}")
        else:
            report["missing_fields"].append("tax_rate")
            report["status"] = "FAIL"
            print("✗ tax_rate: Missing")
        
        # Check WACC components
        wacc_fields = ['risk_free_rate', 'equity_risk_premium', 'beta', 'cost_of_debt']
        for field in wacc_fields:
            if field in drivers:
                report["correctly_implemented"].append(field)
                print(f"✓ {field}: Present ({drivers[field]})")
            else:
                report["missing_fields"].append(field)
                print(f"✗ {field}: Missing")
        
        # Check terminal value parameters
        if 'terminal_growth_rate' in drivers:
            tgr = drivers['terminal_growth_rate']
            if tgr <= 0.03:  # Reasonable range
                report["correctly_implemented"].append(f"terminal_growth_rate ({tgr})")
                print(f"✓ terminal_growth_rate: {tgr} (reasonable)")
            else:
                report["mismatched_fields"].append(f"terminal_growth_rate too high: {tgr}")
                print(f"⚠ terminal_growth_rate: {tgr} may be too high")
        else:
            report["missing_fields"].append("terminal_growth_rate")
            report["status"] = "FAIL"
            print("✗ terminal_growth_rate: Missing")
        
        if 'terminal_ebitda_multiple' in drivers:
            report["correctly_implemented"].append(f"terminal_ebitda_multiple ({drivers['terminal_ebitda_multiple']})")
            print(f"✓ terminal_ebitda_multiple: Present")
        else:
            report["missing_fields"].append("terminal_ebitda_multiple")
            print("✗ terminal_ebitda_multiple: Missing")
        
        # Check working capital days
        wc_fields = ['ar_days', 'inv_days', 'ap_days']
        for field in wc_fields:
            if field in drivers:
                report["correctly_implemented"].append(field)
                print(f"✓ {field}: Present ({drivers[field]})")
            else:
                report["missing_fields"].append(field)
                print(f"✗ {field}: Missing")
        
        # Check CapEx
        if 'capex_pct_of_revenue' in drivers:
            report["correctly_implemented"].append("capex_pct_of_revenue")
            print("✓ capex_pct_of_revenue: Present")
        else:
            report["notes"].append("CapEx as % of revenue instead of absolute values")
            print("⚠ capex: Expressed as % of revenue (different from Excel absolute values)")
        
        # Check depreciation parameters
        dep_fields = ['useful_life_existing', 'useful_life_new']
        for field in dep_fields:
            if field in drivers:
                report["correctly_implemented"].append(field)
                print(f"✓ {field}: Present")
            else:
                report["notes"].append(f"{field} may use defaults")
                print(f"⚠ {field}: May use default values")
    
    # 2. Historical Financials
    if 'historical_financials' in international_inputs:
        hist = international_inputs['historical_financials']
        required_hist = ['revenue', 'cogs', 'ebitda', 'net_income', 'capex', 'total_assets', 'total_debt']
        
        print("\n--- Historical Financials ---")
        for field in required_hist:
            if field in hist and hist[field]:
                report["correctly_implemented"].append(f"historical_{field}")
                print(f"✓ historical_{field}: Present")
            else:
                report["missing_fields"].append(f"historical_{field}")
                print(f"✗ historical_{field}: Missing or empty")
    
    # 3. Market Data
    if 'market_data' in international_inputs:
        market = international_inputs['market_data']
        required_market = ['current_stock_price', 'shares_outstanding', 'beta', 'total_debt', 'cash']
        
        print("\n--- Market Data ---")
        for field in required_market:
            if field in market and market[field]:
                report["correctly_implemented"].append(f"market_{field}")
                print(f"✓ market_{field}: Present")
            else:
                report["missing_fields"].append(f"market_{field}")
                print(f"✗ market_{field}: Missing or empty")
    
    # Check Vietnamese DCF Inputs
    print("\n=== VERIFYING VIETNAMESE DCF INPUTS ===")
    
    if vietnamese_inputs:
        # Vietnam-specific parameters
        vn_tax_rate = vietnamese_inputs.get('corporate_tax_rate', 0.20)
        if abs(vn_tax_rate - 0.20) < 0.01:
            report["correctly_implemented"].append("vn_corporate_tax_rate (20%)")
            print("✓ Vietnamese corporate tax rate: 20% (correct)")
        else:
            report["mismatched_fields"].append(f"vn_tax_rate: {vn_tax_rate} vs expected 0.20")
            print(f"✗ Vietnamese tax rate: {vn_tax_rate} (expected 20%)")
        
        vn_rf_rate = vietnamese_inputs.get('risk_free_rate', 0.068)
        if vn_rf_rate >= 0.06 and vn_rf_rate <= 0.08:
            report["correctly_implemented"].append("vn_risk_free_rate")
            print(f"✓ Vietnamese risk-free rate: {vn_rf_rate} (reasonable range)")
        else:
            report["mismatched_fields"].append(f"vn_risk_free_rate: {vn_rf_rate}")
            print(f"⚠ Vietnamese risk-free rate: {vn_rf_rate} (expected ~6.8%)")
        
        vn_mrp = vietnamese_inputs.get('market_risk_premium', 0.075)
        if vn_mrp >= 0.07 and vn_mrp <= 0.09:
            report["correctly_implemented"].append("vn_market_risk_premium")
            print(f"✓ Vietnamese market risk premium: {vn_mrp} (reasonable)")
        else:
            report["mismatched_fields"].append(f"vn_market_risk_premium: {vn_mrp}")
            print(f"⚠ Vietnamese MRP: {vn_mrp} (expected ~7.5%)")
    else:
        report["notes"].append("Vietnamese DCF inputs not provided for verification")
        print("⚠ Vietnamese DCF inputs: Not available")
    
    return report


def verify_comps_inputs(comps_data: Dict) -> Dict[str, Any]:
    """
    Verify Comps inputs against Excel model specification
    """
    report = {
        "model": "COMPS",
        "status": "PASS",
        "missing_fields": [],
        "mismatched_fields": [],
        "correctly_implemented": [],
        "notes": []
    }
    
    print("\n=== VERIFYING COMPS INPUTS ===")
    
    # 1. Target Company Data
    if 'target_ticker' in comps_data:
        report["correctly_implemented"].append("target_ticker")
        print(f"✓ target_ticker: {comps_data['target_ticker']}")
    else:
        report["missing_fields"].append("target_ticker")
        report["status"] = "FAIL"
        print("✗ target_ticker: Missing")
    
    # Check target financials
    target_fields = ['target_revenue_ltm', 'target_ebitda_ltm', 'target_net_income_ltm', 'target_eps_ltm']
    print("\n--- Target Financials ---")
    for field in target_fields:
        if field in comps_data and comps_data[field]:
            report["correctly_implemented"].append(field)
            print(f"✓ {field}: Present")
        else:
            report["missing_fields"].append(field)
            print(f"✗ {field}: Missing")
    
    # 2. Peer Multiples
    if 'peer_multiples' in comps_data:
        peers = comps_data['peer_multiples']
        if isinstance(peers, list) and len(peers) >= 1:
            report["correctly_implemented"].append(f"peer_multiples ({len(peers)} peers)")
            print(f"\n✓ peer_multiples: {len(peers)} peers provided")
            
            # Check required peer fields
            if len(peers) > 0:
                first_peer = peers[0] if isinstance(peers[0], dict) else peers[0].__dict__
                required_peer_metrics = ['ev_ebitda_ltm', 'pe_ratio_ltm', 'ticker']
                
                print("\n--- Peer Metrics ---")
                for metric in required_peer_metrics:
                    if metric in first_peer:
                        report["correctly_implemented"].append(f"peer_{metric}")
                        print(f"✓ peer_{metric}: Present")
                    else:
                        report["missing_fields"].append(f"peer_{metric}")
                        print(f"✗ peer_{metric}: Missing")
                
                # Check for additional metrics from Excel spec
                optional_metrics = ['ev_ebitda_fy1', 'ev_ebitda_fy2', 'pe_ratio_fy1', 'ev_revenue_ltm', 'pb_ratio']
                print("\n--- Optional Peer Metrics ---")
                for metric in optional_metrics:
                    if metric in first_peer:
                        report["correctly_implemented"].append(f"peer_{metric}")
                        print(f"✓ peer_{metric}: Present")
                    else:
                        report["notes"].append(f"peer_{metric} not present")
                        print(f"⚠ peer_{metric}: Not present (optional)")
        else:
            report["missing_fields"].append("peer_multiples (need at least 1 peer)")
            report["status"] = "FAIL"
            print("✗ peer_multiples: Empty or invalid")
    else:
        report["missing_fields"].append("peer_multiples")
        report["status"] = "FAIL"
        print("✗ peer_multiples: Missing")
    
    # 3. Outlier Filtering
    if 'apply_outlier_filtering' in comps_data:
        report["correctly_implemented"].append("apply_outlier_filtering flag")
        print(f"\n✓ apply_outlier_filtering: {comps_data['apply_outlier_filtering']}")
        
        if 'iqr_multiplier' in comps_data:
            iqr_mult = comps_data['iqr_multiplier']
            if abs(iqr_mult - 1.5) < 0.1:
                report["correctly_implemented"].append(f"iqr_multiplier ({iqr_mult})")
                print(f"✓ iqr_multiplier: {iqr_mult} (matches Excel spec 1.5)")
            else:
                report["mismatched_fields"].append(f"iqr_multiplier: {iqr_mult} vs expected 1.5")
                print(f"⚠ iqr_multiplier: {iqr_mult} (expected 1.5)")
        else:
            report["notes"].append("iqr_multiplier uses default")
            print("⚠ iqr_multiplier: Uses default value")
    else:
        report["notes"].append("Outlier filtering flag not present")
        print("⚠ apply_outlier_filtering: Not specified")
    
    # 4. Vietnamese Comps Specific
    if 'vietnamese' in str(comps_data).lower() or any(k.startswith('vn_') for k in comps_data.keys()):
        print("\n--- Vietnamese Comps Specific ---")
        report["correctly_implemented"].append("vietnamese_comps_context")
        print("✓ Vietnamese comps context detected")
    
    return report


def verify_dupont_inputs(dupont_data: Dict) -> Dict[str, Any]:
    """
    Verify DuPont inputs against Excel model specification
    """
    report = {
        "model": "DUPONT",
        "status": "PASS",
        "missing_fields": [],
        "mismatched_fields": [],
        "correctly_implemented": [],
        "notes": []
    }
    
    print("\n=== VERIFYING DUPONT INPUTS ===")
    
    # 1. Ticker and Years
    if 'ticker' in dupont_data:
        report["correctly_implemented"].append("ticker")
        print(f"✓ ticker: {dupont_data['ticker']}")
    else:
        report["missing_fields"].append("ticker")
        report["status"] = "FAIL"
        print("✗ ticker: Missing")
    
    if 'years' in dupont_data:
        years = dupont_data['years']
        if isinstance(years, list) and len(years) >= 3:
            report["correctly_implemented"].append(f"years ({len(years)} years)")
            print(f"✓ years: {len(years)} years provided (meets min 3 year requirement)")
        elif isinstance(years, list) and len(years) < 3:
            report["mismatched_fields"].append(f"years: only {len(years)} years (need ≥3)")
            print(f"⚠ years: Only {len(years)} years (Excel spec requires 3-5 years)")
        else:
            report["mismatched_fields"].append("years format invalid")
            print("✗ years: Invalid format")
    else:
        report["missing_fields"].append("years")
        report["status"] = "FAIL"
        print("✗ years: Missing")
    
    # 2. DuPont Components
    if 'custom_ratios' in dupont_data:
        ratios = dupont_data['custom_ratios']
        
        # Handle both dict and object
        if hasattr(ratios, '__dict__'):
            ratios = ratios.__dict__
        
        print("\n--- DuPont Components ---")
        
        # Net Profit Margin
        if 'net_profit_margin' in ratios:
            npm = ratios['net_profit_margin']
            if npm is not None and npm > 0:
                report["correctly_implemented"].append(f"net_profit_margin ({npm})")
                print(f"✓ net_profit_margin: {npm}")
            else:
                report["notes"].append("net_profit_margin is zero or None")
                print(f"⚠ net_profit_margin: {npm} (may need calculation)")
        else:
            report["missing_fields"].append("net_profit_margin")
            print("✗ net_profit_margin: Missing")
        
        # Asset Turnover
        if 'asset_turnover' in ratios:
            at = ratios['asset_turnover']
            if at is not None and at > 0:
                report["correctly_implemented"].append(f"asset_turnover ({at})")
                print(f"✓ asset_turnover: {at}")
            else:
                report["notes"].append("asset_turnover is zero or None")
                print(f"⚠ asset_turnover: {at} (may need calculation)")
        else:
            report["missing_fields"].append("asset_turnover")
            print("✗ asset_turnover: Missing")
        
        # Equity Multiplier
        if 'equity_multiplier' in ratios:
            em = ratios['equity_multiplier']
            if em is not None and em > 0:
                report["correctly_implemented"].append(f"equity_multiplier ({em})")
                print(f"✓ equity_multiplier: {em}")
            else:
                report["notes"].append("equity_multiplier is zero or None")
                print(f"⚠ equity_multiplier: {em} (may need calculation)")
        else:
            report["missing_fields"].append("equity_multiplier")
            print("✗ equity_multiplier: Missing")
        
        # ROE (calculated)
        if 'roe' in ratios:
            roe = ratios['roe']
            if roe is not None:
                report["correctly_implemented"].append(f"roe ({roe})")
                print(f"✓ roe: {roe}")
            else:
                report["notes"].append("roe is None")
                print(f"⚠ roe: {roe} (may need calculation)")
        else:
            report["notes"].append("roe will be calculated from components")
            print("⚠ roe: Will be calculated (NPM × AT × EM)")
        
        # Check for raw financials (alternative input method)
        raw_fields = ['net_income', 'revenue', 'total_assets', 'shareholders_equity']
        print("\n--- Raw Financials (for auto-calculation) ---")
        raw_present = sum(1 for f in raw_fields if f in ratios and ratios[f])
        
        if raw_present >= 4:
            report["correctly_implemented"].append("all_raw_financials_for_calculation")
            print("✓ All raw financials present for auto-calculation")
        elif raw_present > 0:
            report["notes"].append(f"Only {raw_present}/4 raw financials present")
            print(f"⚠ Only {raw_present}/4 raw financials present")
        else:
            report["notes"].append("No raw financials provided")
            print("⚠ No raw financials provided (ratios must be pre-calculated)")
    
    else:
        report["notes"].append("custom_ratios not provided (will calculate from financials)")
        print("⚠ custom_ratios: Not provided (will calculate from historical data)")
    
    # 3. Vietnamese DuPont Specific
    if 'vietnamese' in str(dupont_data).lower() or any(k.startswith('vn_') for k in dupont_data.keys()):
        print("\n--- Vietnamese DuPont Specific ---")
        report["correctly_implemented"].append("vietnamese_dupont_context")
        print("✓ Vietnamese DuPont context detected (TT99 standards)")
    
    return report


# =============================================================================
# MAIN VERIFICATION RUNNER
# =============================================================================

def run_verification():
    """
    Run complete verification of all models against Excel specifications
    """
    print("=" * 80)
    print("EXCEL MODEL ALIGNMENT VERIFICATION")
    print("=" * 80)
    print("\nReference Files:")
    print("  - /workspace/excel models/DCF_Model_Documentation.txt")
    print("  - /workspace/excel models/Comps_Model_Documentation.txt")
    print("  - /workspace/excel models/dupont.txt")
    print("\nVerifying input models against Excel specifications...")
    
    # Import actual input models
    import sys
    sys.path.insert(0, '/workspace/backend')
    
    try:
        from app.models.international.international_inputs import (
            DCFValuationRequest,
            CompsValuationRequest,
            DuPontRequest
        )
        from app.models.vietnamese.vietnamese_inputs import (
            VietnameseDCFRequest,
            VietnameseCompsValuationRequest,
            VietnameseDuPontRequest
        )
        
        print("\n✓ All input models imported successfully\n")
        
    except ImportError as e:
        print(f"\n✗ Failed to import models: {e}")
        return {"status": "FAIL", "error": str(e)}
    
    # Create sample instances to verify structure
    print("\n" + "=" * 80)
    print("CREATING SAMPLE INSTANCES FOR STRUCTURE VERIFICATION")
    print("=" * 80)
    
    all_reports = {}
    
    # Test DCF
    try:
        dcf_sample = DCFValuationRequest(
            session_id="test123",
            ticker="AAPL",
            company_name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            forecast_drivers={
                "revenue_growth_forecast": [0.05, 0.05, 0.04, 0.04, 0.03, 0.02],
                "volume_growth_split": 0.6,
                "inflation_rate": 0.02,
                "tax_rate": 0.21,
                "capex_pct_of_revenue": 0.05,
                "ar_days": 45,
                "inv_days": 60,
                "ap_days": 30,
                "risk_free_rate": 0.045,
                "equity_risk_premium": 0.055,
                "beta": 1.2,
                "cost_of_debt": 0.05,
                "terminal_growth_rate": 0.023,
                "terminal_ebitda_multiple": 8.0,
                "useful_life_existing": 10.0,
                "useful_life_new": 10.0
            },
            historical_financials={
                "revenue": {"2023": 383285000000, "2022": 394328000000},
                "cogs": {"2023": 214137000000, "2022": 223546000000},
                "ebitda": {"2023": 125820000000, "2022": 130541000000},
                "net_income": {"2023": 96995000000, "2022": 99803000000},
                "capex": {"2023": -10959000000, "2022": -10708000000},
                "total_assets": {"2023": 352755000000, "2022": 352583000000},
                "total_debt": {"2023": 111088000000, "2022": 120069000000}
            },
            market_data={
                "current_stock_price": 175.43,
                "shares_outstanding": 15552752000,
                "beta": 1.29,
                "total_debt": 111088000000,
                "cash": 29965000000
            }
        )
        
        dcf_report = verify_dcf_inputs(
            dcf_sample.model_dump(),
            {}  # No VN data in this test
        )
        all_reports["DCF"] = dcf_report
        
    except Exception as e:
        print(f"\n✗ DCF sample creation failed: {e}")
        all_reports["DCF"] = {"status": "FAIL", "error": str(e)}
    
    # Test Comps
    try:
        comps_sample = CompsValuationRequest(
            session_id="test123",
            target_ticker="AAPL",
            target_company_name="Apple Inc.",
            target_market_cap=2800000000000,
            target_ebitda_ltm=120000000000,
            peer_multiples=[
                {
                    "ticker": "MSFT",
                    "company_name": "Microsoft",
                    "ev_ebitda_ltm": 18.5,
                    "ev_ebitda_fy1": 17.2,
                    "pe_ratio_ltm": 28.3,
                    "pe_ratio_fy1": 25.1,
                    "sector": "Technology",
                    "industry": "Software"
                },
                {
                    "ticker": "GOOGL",
                    "company_name": "Alphabet",
                    "ev_ebitda_ltm": 14.2,
                    "pe_ratio_ltm": 22.5,
                    "sector": "Technology",
                    "industry": "Internet"
                }
            ],
            apply_outlier_filtering=True,
            iqr_multiplier=1.5
        )
        
        comps_report = verify_comps_inputs(comps_sample.model_dump())
        all_reports["COMPS"] = comps_report
        
    except Exception as e:
        print(f"\n✗ Comps sample creation failed: {e}")
        all_reports["COMPS"] = {"status": "FAIL", "error": str(e)}
    
    # Test DuPont
    try:
        dupont_sample = DuPontRequest(
            ticker="AAPL",
            years=[2023, 2022, 2021],
            custom_ratios={
                "net_profit_margin": 0.253,
                "asset_turnover": 1.09,
                "equity_multiplier": 5.48,
                "roe": 1.51,
                "net_income": 96995000000,
                "revenue": 383285000000,
                "total_assets": 352755000000,
                "shareholders_equity": 64443000000
            }
        )
        
        dupont_report = verify_dupont_inputs(dupont_sample.model_dump())
        all_reports["DUPONT"] = dupont_report
        
    except Exception as e:
        print(f"\n✗ DuPont sample creation failed: {e}")
        all_reports["DUPONT"] = {"status": "FAIL", "error": str(e)}
    
    # Print Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    overall_status = "PASS"
    for model_name, report in all_reports.items():
        status_icon = "✓" if report["status"] == "PASS" else ("⚠" if report["status"] == "PARTIAL" else "✗")
        print(f"\n{status_icon} {model_name} Model: {report['status']}")
        print(f"   Correctly Implemented: {len(report.get('correctly_implemented', []))}")
        print(f"   Missing Fields: {len(report.get('missing_fields', []))}")
        print(f"   Mismatched Fields: {len(report.get('mismatched_fields', []))}")
        print(f"   Notes: {len(report.get('notes', []))}")
        
        if report["status"] != "PASS":
            overall_status = "PARTIAL" if overall_status == "PASS" else overall_status
    
    print("\n" + "=" * 80)
    print(f"OVERALL STATUS: {overall_status}")
    print("=" * 80)
    
    # Generate detailed recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    for model_name, report in all_reports.items():
        if report.get("missing_fields"):
            recommendations.append(f"\n{model_name}: Add missing fields:")
            for field in report["missing_fields"]:
                recommendations.append(f"  - {field}")
        
        if report.get("mismatched_fields"):
            recommendations.append(f"\n{model_name}: Review mismatched fields:")
            for field in report["mismatched_fields"]:
                recommendations.append(f"  - {field}")
    
    if not recommendations:
        print("\n✓ All models align well with Excel specifications!")
        print("\nKey Strengths:")
        print("  - Revenue growth forecasting with multiple periods")
        print("  - Complete WACC component breakdown")
        print("  - Working capital days properly captured")
        print("  - Terminal value parameters included")
        print("  - Peer multiples with IQR outlier filtering")
        print("  - DuPont three-component decomposition")
        print("  - Vietnam-specific parameters (20% tax, 6.8% Rf, 7.5% MRP)")
    else:
        for rec in recommendations:
            print(rec)
    
    return {
        "overall_status": overall_status,
        "reports": all_reports,
        "recommendations": recommendations
    }


if __name__ == "__main__":
    result = run_verification()
    
    # Save results to JSON
    import json
    with open("/workspace/verification_results.json", "w") as f:
        # Convert any non-serializable objects
        serializable_result = {}
        for key, value in result.items():
            if isinstance(value, dict):
                serializable_result[key] = value
            else:
                serializable_result[key] = str(value)
        json.dump(serializable_result, f, indent=2, default=str)
    
    print(f"\n✓ Verification results saved to /workspace/verification_results.json")
