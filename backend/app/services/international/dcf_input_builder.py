"""Shared DCF Input Builder — used by both Step 9 and Step 10.

Extracts DCF-specific inputs from confirmed assumptions and builds DCFInputs
dataclass with proper ScenarioDrivers. Single source of truth for converting
Step 9 confirmed outputs into DCFEngine inputs.

Used by:
  - Step 9: calculate_building_blocks (building block schedules)
  - Step 10: calculate_valuation (UFCF/DCF/valuation)
"""

import logging
from typing import Dict, Any, List

from app.services.international.dcf_engine import (
    DCFInputs,
    ScenarioDrivers,
    create_default_inputs,
)

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────

def msi_to_dict(msi: Any) -> Dict[str, Any]:
    """Convert ModelSpecificInputs (Pydantic model or dict) to a plain dict."""
    if isinstance(msi, dict):
        return msi
    if hasattr(msi, 'model_dump'):
        return msi.model_dump()
    if hasattr(msi, 'dict'):
        return msi.dict()
    return {}


def extract_numeric(data: Dict, key: str, default: float) -> float:
    """Extract a numeric value from raw confirmed_assumptions.
    Handles both raw values and {value, source} wrapper dicts.
    """
    val = data.get(key)
    if val is None:
        return default
    if isinstance(val, dict):
        val = val.get('value', default)
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def normalize_pct(val: float, field_name: str) -> float:
    """Normalize percentage values to decimal (0-1) format.

    Handles:
    - Already decimal (0.047 → 0.047)
    - Whole-number percentages (4.7 → 0.047)
    - Basis-point-like values (470 → 0.047)
    - Negative values: clamped to 0 with warning (except terminal_growth which can be slightly negative)
    """
    if val is None:
        return val
    pct_fields = {
        'risk_free_rate', 'market_risk_premium', 'country_risk_premium',
        'statutory_tax_rate', 'pre_tax_cost_of_debt', 'terminal_growth',
        'lt_debt_interest_rate', 'cash_interest_rate', 'revolving_credit_rate',
        'first_year_acctg_dep_rate', 'first_year_tax_dep_rate', 'blended_tax_dep_rate',
    }
    if field_name in pct_fields:
        # Clamp negative values to 0 (financial rates should be ≥ 0, except terminal_growth)
        if val < 0:
            if field_name == 'terminal_growth':
                # Terminal growth can be slightly negative but not below -10%
                return max(val, -0.10)
            logger.warning(f"normalize_pct: {field_name}={val} is negative; clamping to 0")
            return 0.0
        if val > 1.0 and val <= 100.0:
            return val / 100.0
        if val > 100.0:
            return val / 10000.0
    return val


# ─── Input Extraction ─────────────────────────────────────────────────────

def extract_dcf_inputs(assumptions: Dict[str, Any]) -> Dict[str, Any]:
    """Extract DCF-specific inputs from Step 9 confirmed outputs."""
    msi = msi_to_dict(assumptions.get('model_specific_inputs', {}))
    historical = assumptions.get('historical_financials_summary', {})
    market_ctx = assumptions.get('market_context', {})

    dcf_inputs = {'scenario': assumptions.get('scenario', 'base_case')}

    # WACC components
    dcf_inputs['risk_free_rate'] = normalize_pct(
        msi.get('risk_free_rate') or market_ctx.get('risk_free_rate', 0.04), 'risk_free_rate')
    dcf_inputs['market_risk_premium'] = normalize_pct(
        msi.get('market_risk_premium') or market_ctx.get('market_risk_premium', 0.06), 'market_risk_premium')
    dcf_inputs['country_risk_premium'] = normalize_pct(
        market_ctx.get('country_risk_premium', 0.0), 'country_risk_premium')
    dcf_inputs['statutory_tax_rate'] = normalize_pct(
        msi.get('tax_rate') or market_ctx.get('corporate_tax_rate', 0.21), 'statutory_tax_rate')
    dcf_inputs['beta'] = msi.get('beta', 1.0)

    d_e = msi.get('debt_to_equity', 0.5)
    dcf_inputs['target_debt_weight'] = d_e / (1 + d_e) if d_e else 0.15
    dcf_inputs['target_equity_weight'] = 1.0 - dcf_inputs['target_debt_weight']
    dcf_inputs['pre_tax_cost_of_debt'] = normalize_pct(msi.get('cost_of_debt', 0.05), 'pre_tax_cost_of_debt')
    dcf_inputs['terminal_growth'] = normalize_pct(msi.get('terminal_growth_rate', 0.025), 'terminal_growth')

    # Revenue drivers
    revenue_projections = msi.get('revenue_projections', [])
    dcf_inputs['revenue_growth'] = revenue_projections[0].get('growth_rate', 0.05) if revenue_projections else 0.05

    # Operating margins
    operating_margin_projections = msi.get('operating_margin_projections', [])
    dcf_inputs['ebitda_margin'] = operating_margin_projections[0].get('margin', 0.20) if operating_margin_projections else 0.20

    # Working capital & capex
    dcf_inputs['capex_percent_revenue'] = msi.get('capex_percent_revenue', 0.05)
    dcf_inputs['nwc_percent_revenue'] = msi.get('nwc_percent_revenue', 0.10)

    # Market data
    dcf_inputs['current_price'] = msi.get('current_price')
    dcf_inputs['shares_outstanding'] = msi.get('shares_outstanding')
    dcf_inputs['net_debt'] = msi.get('net_debt')

    # Historical data
    dcf_inputs['latest_revenue'] = historical.get('latest_revenue', 0)
    dcf_inputs['latest_ebitda'] = historical.get('latest_ebitda', 0)
    dcf_inputs['latest_operating_cash_flow'] = historical.get('latest_operating_cash_flow', 0)
    dcf_inputs['latest_capex'] = historical.get('latest_capex', 0)

    # Full multi-year historical arrays
    for field in ['revenue', 'cogs', 'operating_expenses', 'selling_general_administrative',
                  'research_development', 'depreciation_amortization', 'interest_expense',
                  'ebitda', 'operating_income', 'net_income',
                  'accounts_receivable', 'inventory', 'accounts_payable',
                  'total_assets', 'shareholders_equity', 'retained_earnings',
                  'ppe_gross', 'net_ppe', 'accumulated_depreciation',
                  'long_term_debt', 'total_debt', 'cash_and_equivalents',
                  'shares_outstanding', 'capital_expenditure', 'operating_cash_flow',
                  'dividends_paid', 'debt_repayments', 'debt_issuance', 'share_buybacks',
                  # Additional fields for building block output
                  'interest_income', 'other_income_expense', 'tax_paid', 'interest_paid',
                  # Institution-grade balance sheet items
                  'non_current_marketable_securities', 'other_current_liabilities',
                  'deferred_tax_liabilities',
                  # New granularity balance sheet items (Steps 5-6-7 additions)
                  'current_accrued_expenses', 'current_deferred_liabilities',
                  'trade_and_other_payables_non_current', 'other_non_current_liabilities',
                  'other_short_term_investments', 'other_current_assets',
                  'other_non_current_assets', 'common_stock', 'other_equity_adjustments',
                  'total_liabilities']:
        dcf_inputs[f'historical_{field}'] = historical.get(field, [])

    # Also map cash_and_equivalents to historical_cash for backward compatibility
    dcf_inputs['historical_cash'] = historical.get('cash_and_equivalents',
                                    historical.get('cash', []))

    # Map interest_expense to historical_interest_expense for DCFInputs
    if historical.get('interest_expense'):
        dcf_inputs['historical_interest_expense'] = historical.get('interest_expense', [])

    # Market data from historical
    dcf_inputs['current_price'] = msi.get('current_price') or historical.get('current_price', 0)
    shares = msi.get('shares_outstanding') or historical.get('shares_outstanding', [0])
    dcf_inputs['shares_outstanding'] = shares[-1] if isinstance(shares, list) and shares else shares
    dcf_inputs['net_debt'] = msi.get('net_debt')
    dcf_inputs['market_cap'] = historical.get('market_cap', 0)
    dcf_inputs['beta'] = msi.get('beta', 1.0) or historical.get('beta', 1.0)
    dcf_inputs['wacc'] = msi.get('wacc')
    # Pre-computed WACC from frontend — pass through for Step 10 to use directly
    if msi.get('wacc') is not None:
        try:
            wacc_val = float(msi['wacc'])
            if 0.01 <= wacc_val <= 0.30:
                dcf_inputs['precomputed_wacc'] = wacc_val
        except (TypeError, ValueError):
            pass

    # Pass through raw data for ScenarioDrivers construction
    dcf_inputs['raw_confirmed_assumptions'] = assumptions.get('raw_confirmed_assumptions', {})
    dcf_inputs['historical_financials_summary'] = historical

    return dcf_inputs


# ─── DCFInputs Builder ────────────────────────────────────────────────────

def build_dcf_inputs(data: Dict) -> DCFInputs:
    """Convert dictionary to DCFInputs dataclass with proper ScenarioDrivers."""
    inputs = create_default_inputs()

    def _last_4(arr):
        """Get last 4 values from array (for 4-year historical)."""
        if not arr or not isinstance(arr, list):
            return []
        return arr[-4:] if len(arr) >= 4 else arr

    def _first_nonzero(arr):
        if not arr or not isinstance(arr, list):
            return 0
        for v in arr:
            if v and v != 0:
                return v
        return 0

    # Market data
    if data.get('shares_outstanding'):
        val = data['shares_outstanding']
        inputs.shares_outstanding = val[-1] if isinstance(val, list) and val else val
    if data.get('current_price'):
        inputs.current_stock_price = data['current_price']
    if data.get('net_debt'):
        inputs.net_debt_opening = data['net_debt']
    elif data.get('historical_total_debt') and data.get('historical_cash'):
        inputs.net_debt_opening = _first_nonzero(data['historical_total_debt']) - _first_nonzero(data['historical_cash'])

    # Historical financials (4 years)
    if data.get('historical_revenue'):
        inputs.historical_revenue = _last_4(data['historical_revenue'])
    elif data.get('latest_revenue'):
        r = data['latest_revenue']
        inputs.historical_revenue = [r * 0.88, r * 0.90, r * 0.92, r * 0.96, r]

    if data.get('historical_cogs'):
        inputs.historical_cogs = _last_4(data['historical_cogs'])

    if data.get('historical_sga'):
        inputs.historical_sga = _last_4(data['historical_sga'])
    elif data.get('historical_operating_expenses') and data.get('historical_depreciation'):
        t5 = _last_4(data['historical_operating_expenses'])
        d5 = _last_4(data['historical_depreciation'])
        inputs.historical_sga = [(t - d) * 0.75 if t and d else 0 for t, d in zip(t5, d5)]

    if data.get('historical_operating_expenses') and data.get('historical_sga'):
        t5 = _last_4(data['historical_operating_expenses'])
        s5 = _last_4(data['historical_sga'])
        # yfinance's OperatingExpense = R&D + SG&A + OtherOperatingExpenses
        # (D&A is NOT in OperatingExpense — it's embedded inside COGS and SG&A)
        # Other OpEx = OperatingExpense - SG&A - R&D
        if data.get('historical_research_development'):
            rd5 = _last_4(data['historical_research_development'])
            while len(rd5) < len(t5): rd5.append(rd5[-1] if rd5 else 0)
            while len(s5) < len(t5): s5.append(s5[-1] if s5 else 0)
            inputs.historical_other_opex = [
                max(t - s - r, 0) if t and s and r else 0
                for t, s, r in zip(t5, s5, rd5)
            ]
        else:
            # R&D not separately available — residual includes R&D
            inputs.historical_other_opex = [max(t - s, 0) if t and s else 0 for t, s in zip(t5, s5)]

    if data.get('historical_depreciation'):
        inputs.historical_depreciation = _last_4(data['historical_depreciation'])
    if data.get('historical_interest'):
        inputs.historical_interest = _last_4(data['historical_interest'])
    if data.get('historical_capex'):
        inputs.historical_capex = _last_4(data['historical_capex'])
    elif data.get('latest_capex'):
        c = data['latest_capex']
        inputs.historical_capex = [c * 0.92, c * 0.94, c * 0.95, c * 0.98, c]

    # Historical balance sheet
    for field, attr in [('historical_ar', 'historical_ar'), ('historical_inventory', 'historical_inventory'),
                        ('historical_ap', 'historical_ap')]:
        if data.get(field):
            val = data[field]
            setattr(inputs, attr, val[-1] if isinstance(val, list) and val else val)

    # Opening balances
    if data.get('historical_ppe_gross'):
        val = data['historical_ppe_gross']
        inputs.ppe_gross_book = val[-1] if isinstance(val, list) and val else val
    elif data.get('historical_net_ppe') and data.get('historical_accumulated_depreciation'):
        inputs.ppe_gross_book = _first_nonzero(data['historical_net_ppe']) + _first_nonzero(data['historical_accumulated_depreciation'])

    if data.get('historical_net_ppe'):
        val = data['historical_net_ppe']
        inputs.tax_basis_ppe = val[-1] if isinstance(val, list) and val else val
    if data.get('historical_cash'):
        val = data['historical_cash']
        inputs.cash_opening = val[-1] if isinstance(val, list) and val else val
    if data.get('historical_long_term_debt'):
        val = data['historical_long_term_debt']
        inputs.long_term_debt_opening = val[-1] if isinstance(val, list) and val else val
    if data.get('historical_shareholders_equity'):
        val = data['historical_shareholders_equity']
        inputs.common_equity_opening = val[-1] if isinstance(val, list) and val else val
    if data.get('historical_retained_earnings'):
        val = data['historical_retained_earnings']
        inputs.retained_earnings_opening = val[-1] if isinstance(val, list) and val else val
    
    # Accumulated depreciation from historical balance sheet
    # yfinance stores this as negative; store as-is for engine to handle
    if data.get('historical_accumulated_depreciation'):
        val = data['historical_accumulated_depreciation']
        inputs.opening_accumulated_depreciation = val[-1] if isinstance(val, list) and val else val

    # ── Institution-grade balance sheet items ──
    # Non-Current Marketable Securities (long-term bond portfolio)
    if data.get('historical_non_current_marketable_securities'):
        inputs.historical_non_current_marketable_securities = _last_4(data['historical_non_current_marketable_securities'])
    
    # Other Current Liabilities (Accrued Expenses + Deferred Revenue)
    if data.get('historical_other_current_liabilities'):
        inputs.historical_other_current_liabilities = _last_4(data['historical_other_current_liabilities'])
    
    # Deferred Tax Liabilities (net DTA/DTL position)
    if data.get('historical_deferred_tax_liabilities'):
        inputs.historical_deferred_tax_liabilities = _last_4(data['historical_deferred_tax_liabilities'])
    
    # Historical Interest Expense (MUST be populated for all periods)
    if data.get('historical_interest_expense'):
        inputs.historical_interest_expense = _last_4(data['historical_interest_expense'])

    # Tax Loss Carryforwards
    if data.get('historical_tax_loss_carryforward'):
        val = data['historical_tax_loss_carryforward']
        inputs.tax_losses_nol = _first_nonzero(val) if isinstance(val, list) else val
    elif data.get('tax_loss_carryforward'):
        inputs.tax_losses_nol = data['tax_loss_carryforward']

    # Financing items
    if data.get('dividend_payout_ratio') is not None:
        inputs.projected_dividends = data['dividend_payout_ratio']
    elif data.get('historical_dividends_paid'):
        val = data['historical_dividends_paid']
        latest = val[-1] if isinstance(val, list) and val else val
        if latest:
            # Validate: dividends should be reasonable relative to net income
            # If dividends > 150% of latest net income, likely a data mapping error
            latest_ni = 0
            if data.get('historical_net_income'):
                ni_arr = data['historical_net_income']
                latest_ni = ni_arr[-1] if isinstance(ni_arr, list) and ni_arr else ni_arr
            if latest_ni and abs(latest) > abs(latest_ni) * 1.5:
                # Dividend value looks corrupted (likely total equity) — use payout ratio fallback
                logger.warning(
                    f"Dividend value {latest} exceeds 150% of net income {latest_ni}. "
                    f"Using 25% payout ratio as fallback."
                )
                inputs.projected_dividends = 0.25  # Store as payout ratio
            else:
                inputs.projected_dividends = abs(latest)

    if data.get('change_in_lt_debt') is not None:
        raw = data['change_in_lt_debt']
        inputs.change_in_lt_debt = _last_4(raw) if isinstance(raw, list) else [raw]
    elif data.get('historical_long_term_debt') and len(data.get('historical_long_term_debt', [])) >= 2:
        ltd = data['historical_long_term_debt']
        inputs.change_in_lt_debt = [ltd[i] - ltd[i-1] for i in range(1, len(ltd))]

    if data.get('change_in_common_equity') is not None:
        raw = data['change_in_common_equity']
        inputs.change_in_common_equity = _last_4(raw) if isinstance(raw, list) else [raw]
    elif data.get('historical_share_buybacks'):
        # Derive equity changes from share buybacks (buybacks reduce equity = negative)
        buybacks = _last_4(data['historical_share_buybacks']) if isinstance(data['historical_share_buybacks'], list) else [data['historical_share_buybacks']]
        equity_changes = [-abs(b) for b in buybacks]
        while len(equity_changes) < 6:
            equity_changes.append(equity_changes[-1] if equity_changes else 0)
        inputs.change_in_common_equity = equity_changes[:6]
    elif data.get('historical_shareholders_equity') and len(data.get('historical_shareholders_equity', [])) >= 2:
        eq = data['historical_shareholders_equity']
        inputs.change_in_common_equity = [eq[i] - eq[i-1] for i in range(1, len(eq))]

    if data.get('historical_revolver'):
        inputs.revolving_credit_line = _last_4(data['historical_revolver'])
    elif data.get('historical_current_debt'):
        inputs.revolving_credit_line = _last_4(data['historical_current_debt'])

    # ── Pass through additional historical fields for building block output ──
    HISTORICAL_FIELD_MAP = {
        'historical_interest_income': 'historical_interest_income',
        'historical_research_development': 'historical_research_development',
        'historical_other_income_expense': 'historical_other_income_expense',
        'historical_tax_paid': 'historical_tax_paid',
        'historical_interest_paid': 'historical_interest_paid',
        'historical_share_buybacks': 'historical_share_buybacks',
        'historical_dividends_paid': 'historical_dividends_paid',
        'historical_debt_issuance': 'historical_debt_issuance',
        'historical_debt_repayments': 'historical_debt_repayments',
        # Multi-year balance sheet arrays
        'historical_cash': 'historical_cash',
        'historical_cash_and_equivalents': 'historical_cash',
        'historical_long_term_debt': 'historical_long_term_debt',
        'historical_total_debt': 'historical_total_debt',
        'historical_total_equity': 'historical_total_equity',
        'historical_common_equity': 'historical_common_equity',
        'historical_retained_earnings': 'historical_retained_earnings',
        # WC schedule lists (list versions for schedule builders)
        'historical_accounts_receivable': 'historical_ar_list',
        'historical_inventory': 'historical_inventory_list',
        'historical_accounts_payable': 'historical_ap_list',
        # New granularity balance sheet items (Steps 5-6-7 additions)
        'historical_current_accrued_expenses': 'historical_current_accrued_expenses',
        'historical_current_deferred_liabilities': 'historical_current_deferred_liabilities',
        'historical_trade_and_other_payables_non_current': 'historical_trade_and_other_payables_non_current',
        'historical_other_non_current_liabilities': 'historical_other_non_current_liabilities',
        'historical_other_short_term_investments': 'historical_other_short_term_investments',
        'historical_other_current_assets': 'historical_other_current_assets',
        'historical_other_non_current_assets': 'historical_other_non_current_assets',
        'historical_common_stock': 'historical_common_stock',
        'historical_other_equity_adjustments': 'historical_other_equity_adjustments',
    }

    for src_key, attr_name in HISTORICAL_FIELD_MAP.items():
        if data.get(src_key) is not None:
            val = data[src_key]
            setattr(inputs, attr_name, _last_4(val) if isinstance(val, list) else [val])

    # WACC inputs
    for field, attr in [('risk_free_rate', 'risk_free_rate'), ('market_risk_premium', 'market_risk_premium'),
                        ('country_risk_premium', 'country_risk_premium'), ('statutory_tax_rate', 'statutory_tax_rate'),
                        ('pre_tax_cost_of_debt', 'pre_tax_cost_of_debt')]:
        if data.get(field) is not None:
            setattr(inputs, attr, data[field])

    # Pre-computed WACC from frontend (passed through extract_dcf_inputs)
    if data.get('precomputed_wacc') is not None:
        inputs.precomputed_wacc = data['precomputed_wacc']

    if data.get('target_debt_weight') is not None:
        inputs.target_debt_weight = data['target_debt_weight']
        inputs.target_equity_weight = 1 - data['target_debt_weight']

    # DCF Model Parameters
    for field in ['useful_life_existing', 'useful_life_new', 'first_year_tax_dep_rate',
                  'blended_tax_dep_rate', 'first_year_acctg_dep_rate']:
        if data.get(field) is not None:
            setattr(inputs, field, data[field])

    # Build ScenarioDrivers from raw confirmed_assumptions
    raw_confirmed = data.get('raw_confirmed_assumptions', {})
    historical = data.get('historical_financials_summary', {})
    terminal_growth = data.get('terminal_growth', 0.02)

    if raw_confirmed:
        inputs.forecast_drivers = _build_scenario_drivers_from_raw(
            raw_confirmed, historical, terminal_growth)
    else:
        if terminal_growth is not None and 'base_case' in inputs.forecast_drivers:
            inputs.forecast_drivers['base_case'].terminal_growth_rate = terminal_growth

    return inputs


# ─── ScenarioDrivers Builder ──────────────────────────────────────────────

def _build_scenario_drivers_from_raw(
    raw_confirmed: Dict[str, Any],
    historical: Dict[str, Any],
    default_terminal_growth: float = 0.02,
    default_terminal_multiple: float = 7.0,
) -> Dict[str, ScenarioDrivers]:
    """Build ScenarioDrivers for all 3 scenarios from raw confirmed_assumptions."""
    drivers = {}
    latest_revenue = historical.get('latest_revenue', 0) or 0

    for scenario_name in ['best_case', 'base_case', 'worst_case']:
        prefix = f"forecast_{scenario_name}_"

        # Revenue Growth
        rev_growth = []
        for yr in range(5):
            key = f"{prefix}revenue_growth_{yr}"
            val = extract_numeric(raw_confirmed, key, None)
            if val is None:
                key = f"{prefix}sales_volume_growth_{yr}"
                val = extract_numeric(raw_confirmed, key, 0.05)
            rev_growth.append(val)
        rev_growth.append(rev_growth[-1] if rev_growth else 0.02)

        # COGS Growth Rate (with fallback to inflation_rate for backward compatibility)
        cogs_growth = []
        for yr in range(5):
            val = extract_numeric(raw_confirmed, f"{prefix}cogs_growth_rate_{yr}", None)
            if val is None:
                val = extract_numeric(raw_confirmed, f"{prefix}inflation_rate_{yr}", 0.03)
            cogs_growth.append(val)
        cogs_growth.append(cogs_growth[-1] if cogs_growth else 0.03)

        # OpEx Growth Rate (with fallback to inflation_rate for backward compatibility)
        opex_growth = []
        for yr in range(5):
            val = extract_numeric(raw_confirmed, f"{prefix}opex_growth_rate_{yr}", None)
            if val is None:
                val = extract_numeric(raw_confirmed, f"{prefix}inflation_rate_{yr}", 0.03)
            opex_growth.append(val)
        opex_growth.append(opex_growth[-1] if opex_growth else 0.03)

        # Inflation Rate (for backward compatibility)
        inflation = []
        for yr in range(5):
            inflation.append(extract_numeric(raw_confirmed, f"{prefix}inflation_rate_{yr}", 0.03))
        inflation.append(inflation[-1] if inflation else 0.03)

        # CapEx
        capex = []
        for yr in range(5):
            raw_val = extract_numeric(raw_confirmed, f"{prefix}capital_expenditure_{yr}", None)
            if raw_val is not None and raw_val > 1:
                capex.append(raw_val)
            else:
                pct = raw_val if raw_val is not None else 0.05
                projected_rev = latest_revenue
                for j in range(yr + 1):
                    g = rev_growth[min(j, len(rev_growth) - 1)]
                    projected_rev *= (1 + g)
                capex.append(projected_rev * pct)
        capex.append(capex[-1] if capex else latest_revenue * 0.05)

        # Working Capital Days
        ar_days = [extract_numeric(raw_confirmed, f"{prefix}receivables_days_{yr}", 45.0) for yr in range(5)]
        inv_days = [extract_numeric(raw_confirmed, f"{prefix}inventory_days_{yr}", 25.0) for yr in range(5)]
        ap_days = [extract_numeric(raw_confirmed, f"{prefix}payables_days_{yr}", 40.0) for yr in range(5)]

        # Terminal Values
        tg = extract_numeric(raw_confirmed, 'dcf_terminal_growth_rate', default_terminal_growth)
        tebitda_m = extract_numeric(raw_confirmed, 'dcf_terminal_ebitda_multiple', default_terminal_multiple)

        drivers[scenario_name] = ScenarioDrivers(
            combined_revenue_growth=rev_growth,
            capex=capex,
            cogs_growth_rate=cogs_growth,
            opex_growth=opex_growth,
            inflation_rate=inflation,
            ar_days=ar_days,
            inv_days=inv_days,
            ap_days=ap_days,
            terminal_growth_rate=tg,
            terminal_ebitda_multiple=tebitda_m,
        )

    return drivers


# ─── Frontend → Backend DCFInputs Mapper ────────────────────────────────────

# Mapping: frontend camelCase key → backend DCFInputs field (snake_case)
_FRONTEND_TO_BACKEND_MAP = {
    # WACC components
    'riskFreeRate': 'risk_free_rate',
    'equityRiskPremium': 'market_risk_premium',
    'costOfDebt': 'pre_tax_cost_of_debt',
    'debtToEquity': '_debt_to_equity',  # special: derive target_debt_weight

    # Market data
    'currentPrice': 'current_stock_price',
    'sharesOutstanding': 'shares_outstanding',
    'netDebt': 'net_debt_opening',

    # Historical arrays
    'historicalRevenue': 'historical_revenue',
    'historicalCogs': 'historical_cogs',
    'historicalSga': 'historical_sga',
    'historicalOtherOpex': 'historical_other_opex',
    'historicalResearchDevelopment': 'historical_research_development',
    'historicalDepreciation': 'historical_depreciation',
    'historicalInterestExpense': 'historical_interest',
    'historicalCapex': 'historical_capex',
    'historicalAr': 'historical_ar',
    'historicalInventory': 'historical_inventory',
    'historicalAp': 'historical_ap',
    'historicalPpe': 'ppe_gross_book',      # last value = opening balance
    'historicalTaxBasis': 'tax_basis_ppe',
    'historicalTaxLosses': 'tax_losses_nol',
    'historicalAccumulatedDepreciation': 'historical_accumulated_depreciation',
    'historicalPpeNet': 'historical_ppe_net',
    'historicalCash': 'cash_opening',        # last value = opening balance
    'historicalTotalDebt': 'long_term_debt_opening',
    'historicalTotalEquity': 'historical_total_equity',  # kept for reference, not used for opening balance
    'historicalCommonEquity': 'common_equity_opening',   # correct: Common Equity = Total Equity - RE
    'historicalRetainedEarnings': 'retained_earnings_opening',
    'historicalDividendsPaid': '_dividends_paid',  # special: derive projected_dividends
    'historicalShareBuybacks': 'historical_share_buybacks',  # used to derive change_in_common_equity
    'historicalCurrentDebt': 'historical_current_debt',

    # Historical reference fields (multi-year arrays for schedule builders)
    'historicalInterestIncome': 'historical_interest_income',
    'historicalOtherIncomeExpense': 'historical_other_income_expense',
    'historicalTaxPaid': 'historical_tax_paid',
    'historicalInterestPaid': 'historical_interest_paid',
    'historicalDebtIssuance': 'historical_debt_issuance',
    'historicalDebtRepayments': 'historical_debt_repayments',

    # DCF model params
    'usefulLifeExisting': 'useful_life_existing',
    'usefulLifeNew': 'useful_life_new',
    'firstYearDepreciationRate': 'first_year_acctg_dep_rate',  # Frontend's "First Year Acctg Dep Rate"
    'firstYearTaxDepRate': 'first_year_tax_dep_rate',
    'blendedTaxDepRate': 'blended_tax_dep_rate',
    'firstYearAcctgDepRate': 'first_year_acctg_dep_rate',

    # Financing
    'changeInLtDebt': 'change_in_lt_debt',
    'changeInCommonEquity': 'change_in_common_equity',
    'dividendPayoutRatio': '_dividend_ratio',  # special: derive projected_dividends
    'revolvingCreditLine': 'revolving_credit_line',

    # Interest rate schedule inputs
    'ltDebtInterestRate': 'lt_debt_interest_rate',
    'cashInterestRate': 'cash_interest_rate',
    'revolvingCreditRate': 'revolving_credit_rate',
    'opexGrowthRate': 'opex_growth_rate',

    # DCF model parameters (hidden fields exposed in Step 9)
    'ppeGrossBook': 'ppe_gross_book',
    'taxBasisPpe': 'tax_basis_ppe',
    'taxLossesNol': 'tax_losses_nol',
    'taxLossUtilizationLimit': 'tax_loss_utilization_limit',
}


def build_dcf_inputs_from_frontend(frontend_inputs: Dict[str, Any]) -> DCFInputs:
    """
    Convert frontend Step 9 DCFInputs (camelCase) to backend DCFInputs dataclass.

    The frontend has ALL data mapped from Steps 6/7/8 into its form fields.
    This function takes the frontend's inputs directly — no session reads needed.
    """
    inputs = create_default_inputs()

    def _last_4(arr):
        if not arr or not isinstance(arr, list):
            return []
        return arr[-4:] if len(arr) >= 4 else arr

    def _last(arr):
        if not arr or not isinstance(arr, list):
            return 0
        return arr[-1] if arr[-1] != 0 else (arr[0] if arr else 0)

    # ── Direct mappings ──
    direct_fields = [
        'taxRate', 'arDays', 'invDays', 'apDays',
        'wacc', 'beta', 'terminalGrowthRate', 'terminalEbitdaMultiple',
        'cashInterestRate', 'revolvingCreditRate', 'ltDebtInterestRate',
    ]
    # taxRate → statutory_tax_rate
    if frontend_inputs.get('taxRate') is not None:
        inputs.statutory_tax_rate = frontend_inputs['taxRate']

    # ── Pre-computed WACC from frontend ──
    # The frontend auto-calculates WACC from components and displays it.
    # Store it so the backend uses the same value instead of re-calculating.
    if frontend_inputs.get('wacc') is not None:
        wacc_val = frontend_inputs['wacc']
        if isinstance(wacc_val, (int, float)) and 0.01 <= wacc_val <= 0.30:
            inputs.precomputed_wacc = wacc_val
            logger.info(f"Stored frontend WACC: {wacc_val:.4f} ({wacc_val*100:.2f}%)")

    # ── Mapped fields (camelCase → snake_case DCFInputs) ──
    for fe_key, be_key in _FRONTEND_TO_BACKEND_MAP.items():
        if fe_key in frontend_inputs and frontend_inputs[fe_key] is not None:
            val = frontend_inputs[fe_key]

            if be_key == '_debt_to_equity':
                # Derive target_debt_weight from D/E ratio
                de = val if val else 0.5
                inputs.target_debt_weight = de / (1 + de)
                inputs.target_equity_weight = 1 - inputs.target_debt_weight
            elif be_key == '_dividends_paid':
                # Use absolute value of latest dividends paid
                if isinstance(val, list):
                    latest = _last(val)
                    if latest:
                        # Validate: dividends should be reasonable relative to net income
                        latest_ni = 0
                        if frontend_inputs.get('historicalNetIncome'):
                            ni_arr = frontend_inputs['historicalNetIncome']
                            latest_ni = ni_arr[-1] if isinstance(ni_arr, list) and ni_arr else ni_arr
                        if latest_ni and abs(latest) > abs(latest_ni) * 1.5:
                            logger.warning(
                                f"Dividend value {latest} exceeds 150% of net income {latest_ni}. "
                                f"Using 25% payout ratio as fallback."
                            )
                            inputs.projected_dividends = 0.25
                        else:
                            inputs.projected_dividends = abs(latest)
                elif val:
                    inputs.projected_dividends = abs(val)
            elif be_key == '_dividend_ratio':
                # Use payout ratio directly
                inputs.projected_dividends = val
            elif be_key in ('historical_ar', 'historical_inventory', 'historical_ap'):
                # Balance sheet items: use last value as scalar
                setattr(inputs, be_key, _last(val) if isinstance(val, list) else val)
            elif be_key in ('ppe_gross_book', 'tax_basis_ppe', 'cash_opening',
                            'long_term_debt_opening', 'common_equity_opening',
                            'retained_earnings_opening', 'tax_losses_nol'):
                # Opening balances: use last value
                setattr(inputs, be_key, _last(val) if isinstance(val, list) else val)
            elif be_key in ('historical_revenue', 'historical_cogs', 'historical_sga',
                            'historical_other_opex', 'historical_research_development',
                            'historical_depreciation',
                            'historical_interest', 'historical_capex',
                            'historical_share_buybacks',
                            'historical_accumulated_depreciation', 'historical_ppe_net',
                            'historical_interest_income', 'historical_other_income_expense',
                            'historical_tax_paid', 'historical_interest_paid',
                            'historical_debt_issuance', 'historical_debt_repayments',
                            'historical_current_debt'):
                # Multi-year arrays: use last 5
                setattr(inputs, be_key, _last_4(val) if isinstance(val, list) else [val])
            elif be_key in ('change_in_lt_debt', 'change_in_common_equity', 'revolving_credit_line'):
                # Financing arrays — ensure these are period-over-period CHANGES, not absolute balances
                raw_val = _last_4(val) if isinstance(val, list) else [val]
                # Heuristic: if values look like absolute balances (all positive and close to opening balance),
                # convert to deltas. Changes should include negative values (repayments/buybacks).
                opening_map = {
                    'change_in_lt_debt': inputs.long_term_debt_opening,
                    'change_in_common_equity': inputs.common_equity_opening,
                    'revolving_credit_line': 0.0,
                }
                opening = _last(opening_map.get(be_key, 0)) if isinstance(opening_map.get(be_key, 0), list) else opening_map.get(be_key, 0)
                if opening and isinstance(opening, (int, float)) and opening > 0:
                    # Check if values look like absolute balances (all positive, close to opening)
                    avg_val = sum(abs(v) for v in raw_val) / max(len(raw_val), 1)
                    if avg_val > 0 and abs(avg_val - opening) / max(opening, 1) < 0.5:
                        # Values are likely absolute balances — convert to deltas
                        deltas = [raw_val[0] - opening] + [raw_val[i] - raw_val[i-1] for i in range(1, len(raw_val))]
                        raw_val = deltas
                setattr(inputs, be_key, raw_val)
            elif be_key in ('current_stock_price', 'shares_outstanding', 'net_debt_opening',
                            'tax_loss_utilization_limit'):
                setattr(inputs, be_key, val)
            elif be_key in ('risk_free_rate', 'market_risk_premium', 'pre_tax_cost_of_debt',
                            'lt_debt_interest_rate', 'cash_interest_rate', 'revolving_credit_rate'):
                setattr(inputs, be_key, normalize_pct(val, be_key))
            elif be_key in ('useful_life_existing', 'useful_life_new',
                            'first_year_tax_dep_rate', 'blended_tax_dep_rate',
                            'first_year_acctg_dep_rate'):
                setattr(inputs, be_key, val)

    # ── Pass through multi-year historical arrays for schedule builders ──
    # The mapping above sets scalar opening balances (e.g., cash_opening, historical_ar).
    # The schedule builders (interest schedule, WC schedule) also need the FULL multi-year
    # arrays (e.g., historical_cash, historical_ar_list). This block sets those.
    _HISTORICAL_LIST_MAP = {
        # Balance sheet arrays → list fields for WC schedule
        'historicalAr': 'historical_ar_list',
        'historicalInventory': 'historical_inventory_list',
        'historicalAp': 'historical_ap_list',
        # Cash & debt arrays → list fields for interest schedule
        'historicalCash': 'historical_cash',
        'historicalTotalDebt': 'historical_long_term_debt',
        'historicalLongTermDebt': 'historical_long_term_debt',
        'historicalShortTermDebt': 'historical_total_debt',
        'historicalCurrentDebt': 'historical_total_debt',
        'historicalTotalEquity': 'historical_total_equity',
        'historicalCommonEquity': 'historical_common_equity',
        'historicalRetainedEarnings': 'historical_retained_earnings',
        # Dividends (list version for schedule builders, in addition to scalar handling above)
        'historicalDividendsPaid': 'historical_dividends_paid',
        # Balance sheet structural items (for schedule builders)
        'historicalTotalAssets': 'historical_total_assets',
        'historicalTotalLiabilities': 'historical_total_liabilities',
        'historicalCurrentAssets': 'historical_current_assets',
        'historicalCurrentLiabilities': 'historical_current_liabilities',
        'historicalDeferredTax': 'historical_deferred_tax',
        'historicalDeferredTaxLiabilities': 'historical_deferred_tax_liabilities',
        # New granularity balance sheet items (Steps 5-6-7 additions)
        'historicalCurrentAccruedExpenses': 'historical_current_accrued_expenses',
        'historicalCurrentDeferredLiabilities': 'historical_current_deferred_liabilities',
        'historicalTradeAndOtherPayablesNonCurrent': 'historical_trade_and_other_payables_non_current',
        'historicalOtherNonCurrentLiabilities': 'historical_other_non_current_liabilities',
        'historicalOtherShortTermInvestments': 'historical_other_short_term_investments',
        'historicalOtherCurrentAssets': 'historical_other_current_assets',
        'historicalOtherNonCurrentAssets': 'historical_other_non_current_assets',
        'historicalCommonStock': 'historical_common_stock',
        'historicalOtherEquityAdjustments': 'historical_other_equity_adjustments',
    }
    for fe_key, attr_name in _HISTORICAL_LIST_MAP.items():
        if fe_key in frontend_inputs and frontend_inputs[fe_key] is not None:
            val = frontend_inputs[fe_key]
            setattr(inputs, attr_name, _last_4(val) if isinstance(val, list) else [val])

    # ── Recompute other_opex from components ──
    # yfinance's OperatingExpense = R&D + SG&A + OtherOperatingExpenses
    # (D&A is NOT in OperatingExpense — it's embedded inside COGS and SG&A)
    # Other OpEx = OperatingExpense - SG&A - R&D
    hist_opex_total = getattr(inputs, 'historical_operating_expenses', None) or frontend_inputs.get('historicalOperatingExpenses')
    hist_sga = getattr(inputs, 'historical_sga', None) or frontend_inputs.get('historicalSga')
    hist_rd = getattr(inputs, 'historical_research_development', None) or frontend_inputs.get('historicalResearchDevelopment')
    
    if hist_opex_total and isinstance(hist_opex_total, list) and len(hist_opex_total) > 0:
        # We have total operating_expenses — recompute other_opex as the true residual
        t5 = _last_4(hist_opex_total)
        s5 = _last_4(hist_sga) if hist_sga and isinstance(hist_sga, list) else [0.0] * len(t5)
        if hist_rd and isinstance(hist_rd, list):
            rd5 = _last_4(hist_rd)
            # Pad shorter arrays
            while len(rd5) < len(t5): rd5.append(rd5[-1] if rd5 else 0)
            while len(s5) < len(t5): s5.append(s5[-1] if s5 else 0)
            inputs.historical_other_opex = [
                max(t - s - r, 0) if t and s and r else 0
                for t, s, r in zip(t5, s5, rd5)
            ]
        else:
            # No R&D — other_opex = operating_expenses - sga
            while len(s5) < len(t5): s5.append(s5[-1] if s5 else 0)
            inputs.historical_other_opex = [
                max(t - s, 0) if t and s else 0
                for t, s in zip(t5, s5)
            ]
    # If no total opex available, keep other_opex as-is (DO NOT set to R&D — R&D is separate)

    # ── Derive change_in_common_equity from buybacks ──
    # Always prefer buyback data when available — more authoritative than defaults.
    # The frontend always sends changeInCommonEquity (even with defaults like [0,0,0,0,0]),
    # so we override with actual buyback amounts when we have them.
    if hasattr(inputs, 'historical_share_buybacks') and inputs.historical_share_buybacks:
        buybacks = _last_4(inputs.historical_share_buybacks) if isinstance(inputs.historical_share_buybacks, list) else [inputs.historical_share_buybacks]
        if any(b and abs(b) > 0 for b in buybacks):
            equity_changes = [-abs(b) for b in buybacks]
            while len(equity_changes) < 6:
                equity_changes.append(equity_changes[-1] if equity_changes else 0)
            inputs.change_in_common_equity = equity_changes[:6]

    # ── Scalar fields not in the map (direct_fields were declared but not used) ──
    # These values are passed to ScenarioDrivers via raw_confirmed below.
    # No action needed here — they're handled in the forecast_* key generation loop.
    if frontend_inputs.get('wacc') is not None:
        inputs.risk_free_rate = frontend_inputs['wacc']  # WACC is recalculated by engine
    if frontend_inputs.get('beta') is not None:
        pass  # beta is used in WACC calculation by engine
    if frontend_inputs.get('terminalGrowthRate') is not None:
        pass  # terminalGrowthRate goes to ScenarioDrivers only
    if frontend_inputs.get('terminalEbitdaMultiple') is not None:
        pass  # terminalEbitdaMultiple goes to ScenarioDrivers only
    # Interest rates are now mapped via _FRONTEND_TO_BACKEND_MAP above
    # and set via the main mapping loop (be_key in ('lt_debt_interest_rate', etc.))

    # ── Build ScenarioDrivers from frontend's forecast_* keys ──
    # The frontend sends forecast_base_case_revenue_growth_0, etc. via assumption_overrides.
    # We need to pass these through so _build_scenario_drivers_from_raw can use them.
    # Store them in a special key that build_dcf_inputs will pick up.
    raw_confirmed = {}
    for key, val in frontend_inputs.items():
        if isinstance(val, dict) and 'value' in val:
            raw_confirmed[key] = val['value']
        # Pass through forecast_* and dcf_* keys already in the right format

    # Also include the frontend's forecast driver fields as raw keys
    for yr in range(5):
        if 'revenueGrowth' in frontend_inputs and isinstance(frontend_inputs['revenueGrowth'], list):
            raw_confirmed[f'forecast_base_case_revenue_growth_{yr}'] = (
                frontend_inputs['revenueGrowth'][yr] if yr < len(frontend_inputs['revenueGrowth']) else 0.05
            )
        if 'cogsGrowthRate' in frontend_inputs and isinstance(frontend_inputs['cogsGrowthRate'], list):
            raw_confirmed[f'forecast_base_case_cogs_growth_rate_{yr}'] = (
                frontend_inputs['cogsGrowthRate'][yr] if yr < len(frontend_inputs['cogsGrowthRate']) else 0.03
            )
        if 'inflationRate' in frontend_inputs and isinstance(frontend_inputs['inflationRate'], list):
            raw_confirmed[f'forecast_base_case_inflation_rate_{yr}'] = (
                frontend_inputs['inflationRate'][yr] if yr < len(frontend_inputs['inflationRate']) else 0.03
            )
        if 'opexGrowthRate' in frontend_inputs and isinstance(frontend_inputs['opexGrowthRate'], list):
            raw_confirmed[f'forecast_base_case_opex_growth_rate_{yr}'] = (
                frontend_inputs['opexGrowthRate'][yr] if yr < len(frontend_inputs['opexGrowthRate']) else 0.03
            )
        if 'capex' in frontend_inputs and isinstance(frontend_inputs['capex'], list):
            raw_confirmed[f'forecast_base_case_capital_expenditure_{yr}'] = (
                frontend_inputs['capex'][yr] if yr < len(frontend_inputs['capex']) else 0
            )
        if frontend_inputs.get('arDays') is not None:
            raw_confirmed[f'forecast_base_case_receivables_days_{yr}'] = frontend_inputs['arDays']
        if frontend_inputs.get('invDays') is not None:
            raw_confirmed[f'forecast_base_case_inventory_days_{yr}'] = frontend_inputs['invDays']
        if frontend_inputs.get('apDays') is not None:
            raw_confirmed[f'forecast_base_case_payables_days_{yr}'] = frontend_inputs['apDays']

    # Terminal values
    if frontend_inputs.get('terminalGrowthRate') is not None:
        raw_confirmed['dcf_terminal_growth_rate'] = frontend_inputs['terminalGrowthRate']
    if frontend_inputs.get('terminalEbitdaMultiple') is not None:
        raw_confirmed['dcf_terminal_ebitda_multiple'] = frontend_inputs['terminalEbitdaMultiple']

    # Build historical summary for ScenarioDrivers
    historical_summary = {}
    if frontend_inputs.get('historicalRevenue'):
        historical_summary['latest_revenue'] = _last(frontend_inputs['historicalRevenue'])

    terminal_growth = frontend_inputs.get('terminalGrowthRate', 0.02)
    if raw_confirmed:
        inputs.forecast_drivers = _build_scenario_drivers_from_raw(
            raw_confirmed, historical_summary, terminal_growth)

    # ── Override ScenarioDrivers with exact frontend values ──
    # The _build_scenario_drivers_from_raw may modify values via projection/mean-reversion.
    # Ensure the frontend's exact values are used for ALL forecast drivers.
    for scenario_key in inputs.forecast_drivers:
        sd = inputs.forecast_drivers[scenario_key]

        # Working capital days — use exact frontend scalar for all years
        if frontend_inputs.get('arDays') is not None:
            ar_val = frontend_inputs['arDays']
            sd.ar_days = [ar_val] * len(sd.ar_days)
        if frontend_inputs.get('invDays') is not None:
            inv_val = frontend_inputs['invDays']
            sd.inv_days = [inv_val] * len(sd.inv_days)
        if frontend_inputs.get('apDays') is not None:
            ap_val = frontend_inputs['apDays']
            sd.ap_days = [ap_val] * len(sd.ap_days)

        # Growth rate arrays — use exact frontend year-by-year values
        if 'revenueGrowth' in frontend_inputs and isinstance(frontend_inputs['revenueGrowth'], list):
            rg = frontend_inputs['revenueGrowth']
            sd.combined_revenue_growth = rg + [rg[-1]] if len(rg) == 5 else rg
        if 'cogsGrowthRate' in frontend_inputs and isinstance(frontend_inputs['cogsGrowthRate'], list):
            cg = frontend_inputs['cogsGrowthRate']
            sd.cogs_growth_rate = cg + [cg[-1]] if len(cg) == 5 else cg
        if 'opexGrowthRate' in frontend_inputs and isinstance(frontend_inputs['opexGrowthRate'], list):
            og = frontend_inputs['opexGrowthRate']
            sd.opex_growth = og + [og[-1]] if len(og) == 5 else og
        if 'inflationRate' in frontend_inputs and isinstance(frontend_inputs['inflationRate'], list):
            ir = frontend_inputs['inflationRate']
            sd.inflation_rate = ir + [ir[-1]] if len(ir) == 5 else ir

        # Capex array — convert percentages to dollar amounts if needed
        # Frontend may send CapEx as % of revenue (e.g., 0.031 = 3.1%) or as absolute $ values
        if 'capex' in frontend_inputs and isinstance(frontend_inputs['capex'], list):
            cx = frontend_inputs['capex']
            # Get latest revenue for percentage conversion
            latest_rev = 0
            if historical_summary.get('latest_revenue'):
                latest_rev = historical_summary['latest_revenue']
            elif frontend_inputs.get('historicalRevenue'):
                hr = frontend_inputs['historicalRevenue']
                latest_rev = hr[-1] if isinstance(hr, list) and hr else 0
            
            # Convert percentages to dollar amounts if values are small (likely percentages)
            converted_cx = []
            for yr_idx, val in enumerate(cx):
                if val is not None and val > 1:
                    # Already a dollar amount
                    converted_cx.append(val)
                elif val is not None and latest_rev > 0:
                    # Percentage of revenue — project revenue forward to get dollar amount
                    projected_rev = latest_rev
                    for j in range(yr_idx + 1):
                        g = sd.combined_revenue_growth[min(j, len(sd.combined_revenue_growth) - 1)]
                        projected_rev *= (1 + g)
                    converted_cx.append(projected_rev * val)
                else:
                    converted_cx.append(val if val is not None else 0)
            
            sd.capex = converted_cx + [converted_cx[-1]] if len(converted_cx) == 5 else converted_cx

        # Terminal values
        if frontend_inputs.get('terminalGrowthRate') is not None:
            sd.terminal_growth_rate = frontend_inputs['terminalGrowthRate']
        if frontend_inputs.get('terminalEbitdaMultiple') is not None:
            sd.terminal_ebitda_multiple = frontend_inputs['terminalEbitdaMultiple']

    return inputs
