#!/usr/bin/env python3
"""
DCF Calculation Engine - Python Version
Migrated from Node.js dcf-engine.js
"""


def round_to(num, decimals=2):
    """Round to specified decimal places"""
    factor = 10 ** decimals
    return round(num * factor) / factor


def calculate_median(arr):
    """Calculate median of array"""
    if not arr:
        return 0
    sorted_arr = sorted(arr)
    mid = len(sorted_arr) // 2
    if len(sorted_arr) % 2 != 0:
        return sorted_arr[mid]
    return (sorted_arr[mid - 1] + sorted_arr[mid]) / 2


def calculate_percentile(arr, p):
    """Calculate percentile"""
    if not arr:
        return 0
    sorted_arr = sorted(arr)
    idx = max(0, int(p * len(sorted_arr)) - 1)
    return sorted_arr[idx]


def calculate_revenue_schedule(base_revenue, growth_rates):
    """Module 1: Revenue Schedule Calculator"""
    revenue = [base_revenue]
    validation_flags = {'all_positive': True}
    
    for i in range(len(growth_rates)):
        prev_revenue = revenue[-1]
        new_revenue = prev_revenue * (1 + growth_rates[i])
        
        if new_revenue <= 0:
            validation_flags['all_positive'] = False
            print(f"[WARNING] Negative revenue detected in year {i + 1}")
        
        revenue.append(new_revenue)
    
    return {'revenue': revenue, 'validation_flags': validation_flags}


def calculate_cogs_schedule(base_cogs, inflation_rates):
    """Module 2: COGS Schedule Calculator"""
    cogs = [base_cogs]
    
    for i in range(len(inflation_rates)):
        prev_cogs = cogs[-1]
        new_cogs = prev_cogs * (1 + inflation_rates[i])
        cogs.append(new_cogs)
    
    return cogs


def calculate_gross_profit(revenue, cogs):
    """Module 3: Gross Profit Calculator"""
    gross_profit = []
    gross_margin = []
    
    for i in range(len(revenue)):
        gp = revenue[i] - cogs[i]
        gross_profit.append(gp)
        gross_margin.append(gp / revenue[i] if revenue[i] > 0 else 0)
    
    return {'gross_profit': gross_profit, 'gross_margin': gross_margin}


def calculate_opex_schedule(base_sga, base_other, opex_growth_rates):
    """Module 4: OpEx Schedule Calculator"""
    sga = [base_sga]
    other = [base_other]
    
    for i in range(len(opex_growth_rates)):
        sga.append(sga[-1] * (1 + opex_growth_rates[i]))
        other.append(other[-1] * (1 + opex_growth_rates[i]))
    
    return {'sga': sga, 'other': other}


def calculate_ebitda(gross_profit, sga, other):
    """Module 5: EBITDA Calculator"""
    ebitda = []
    ebitda_margin = []
    
    # Note: gross_profit includes historical year, so we need matching revenue
    # For simplicity, assume revenue is passed or calculated elsewhere
    for i in range(len(gross_profit)):
        e = gross_profit[i] - sga[i] - other[i]
        ebitda.append(e)
    
    return {'ebitda': ebitda, 'ebitda_margin': ebitda_margin}


def calculate_depreciation_schedule(base_existing_ppe, useful_life_existing, capex_forecast, useful_life_new):
    """Module 6: Depreciation Schedule Calculator"""
    existing_depr = []
    new_assets_depr = []
    total_depreciation = []
    
    # Existing assets depreciation (straight-line)
    annual_depr_existing = base_existing_ppe / useful_life_existing
    
    # New assets depreciation - build array of new assets by year
    num_years = len(capex_forecast) + 2  # historical + forecast years + terminal
    new_assets = [0] * num_years
    for i, capex in enumerate(capex_forecast):
        if i + 1 < num_years:
            new_assets[i + 1] = capex
    
    for year in range(num_years):
        # Existing asset depreciation
        existing_depr.append(annual_depr_existing)
        
        # New assets depreciation (simplified - spread over useful life)
        new_depr = 0
        for j in range(min(year, useful_life_new)):
            asset_year = year - j
            if asset_year < len(new_assets) and asset_year >= 0:
                new_depr += new_assets[asset_year] / useful_life_new
        new_assets_depr.append(new_depr)
        
        total_depreciation.append(existing_depr[-1] + new_assets_depr[-1])
    
    # Terminal CapEx (maintenance capex = depreciation in terminal year)
    terminal_capex = total_depreciation[-1]
    
    return {
        'existing_depr': existing_depr,
        'new_assets_depr': new_assets_depr,
        'total_depreciation': total_depreciation,
        'terminal_capex': terminal_capex
    }


def calculate_ebit(ebitda, depreciation):
    """Module 7: EBIT Calculator"""
    ebit = []
    for i in range(len(ebitda)):
        ebit.append(ebitda[i] - depreciation[i])
    return ebit


def calculate_tax_schedule_unlevered(ebit, depreciation, tax_depr, base_nol, tax_rate, nol_limit=0.8):
    """Module 8: Tax Schedule (Unlevered)"""
    current_tax = []
    deferred_tax = []
    total_tax = []
    nol_remaining = [base_nol]
    
    for i in range(len(ebit)):
        taxable_income = ebit[i] - tax_depr[i]
        
        # NOL utilization
        nol_used = min(max(0, taxable_income) * nol_limit, nol_remaining[-1])
        taxable_after_nol = max(0, taxable_income - nol_used)
        
        tax = taxable_after_nol * tax_rate
        current_tax.append(tax)
        
        # Deferred tax (simplified)
        deferred = (depreciation[i] - tax_depr[i]) * tax_rate if i > 0 else 0
        deferred_tax.append(deferred)
        
        total_tax.append(tax + deferred)
        nol_remaining.append(max(0, nol_remaining[-1] - nol_used))
    
    return {
        'current_tax_unlevered': current_tax,
        'deferred_tax': deferred_tax,
        'total_tax': total_tax,
        'nol_remaining': nol_remaining[1:]
    }


def calculate_working_capital_schedule(revenue, cogs, ar_days, inv_days, ap_days, days_in_period=365):
    """Module 9: Working Capital Schedule"""
    ar = []
    inventory = []
    ap = []
    nwc = []
    change_nwc = []
    
    for i in range(len(revenue)):
        # Accounts Receivable
        ar_val = (revenue[i] / days_in_period) * ar_days
        ar.append(ar_val)
        
        # Inventory
        inv_val = (cogs[i] / days_in_period) * inv_days
        inventory.append(inv_val)
        
        # Accounts Payable
        ap_val = (cogs[i] / days_in_period) * ap_days
        ap.append(ap_val)
        
        # Net Working Capital
        nwc_val = ar_val + inv_val - ap_val
        nwc.append(nwc_val)
        
        # Change in NWC
        if i == 0:
            change_nwc.append(0)
        else:
            change_nwc.append(nwc_val - nwc[i - 1])
    
    return {
        'ar': ar,
        'inventory': inventory,
        'ap': ap,
        'nwc': nwc,
        'change_nwc': change_nwc
    }


def calculate_ufcf(ebitda, tax_unlevered, capex_forecast, change_nwc, terminal_capex=None):
    """Module 10: Unlevered Free Cash Flow Calculator"""
    ufcf = []
    
    for i in range(len(ebitda) - 1):  # Exclude terminal from main calculation
        # Operating cash flow
        ocf = ebitda[i + 1] - tax_unlevered[i + 1]
        
        # CapEx (use forecast for years 1-5)
        capex = capex_forecast[i] if i < len(capex_forecast) else 0
        
        # Change in working capital
        nwc_change = change_nwc[i + 1] if i + 1 < len(change_nwc) else 0
        
        # UFCF
        free_cash_flow = ocf - capex - nwc_change
        ufcf.append(free_cash_flow)
    
    # Terminal year UFCF
    if terminal_capex:
        terminal_ocf = ebitda[-1] - tax_unlevered[-1]
        terminal_fcf = terminal_ocf - terminal_capex
        ufcf.append(terminal_fcf)
    
    return ufcf


def calculate_dcf_perpetuity(ufcf, wacc, terminal_growth_rate, partial_period_adj=None):
    """Module 11: DCF Valuation (Perpetuity Growth Method)"""
    if partial_period_adj is None:
        partial_period_adj = [0.75, 1.0, 1.0, 1.0, 1.0, 1.0]
    
    # Discount discrete period FCFs
    pv_discrete = 0
    for i in range(len(ufcf) - 1):  # Exclude terminal
        adj = partial_period_adj[i] if i < len(partial_period_adj) else 1.0
        pv_discrete += ufcf[i] / ((1 + wacc) ** (i + adj))
    
    # Terminal value (Gordon Growth Model)
    terminal_fcf = ufcf[-1]
    terminal_value = terminal_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
    
    # Discount terminal value
    n = len(ufcf) - 1
    adj_terminal = partial_period_adj[-1] if len(partial_period_adj) > n else 1.0
    pv_terminal = terminal_value / ((1 + wacc) ** (n + adj_terminal))
    
    enterprise_value = pv_discrete + pv_terminal
    
    return {
        'pv_discrete': pv_discrete,
        'pv_terminal': pv_terminal,
        'enterprise_value': enterprise_value
    }


def calculate_dcf_multiple(ufcf, ebitda_terminal, terminal_multiple, wacc, partial_period_adj=None):
    """Module 12: DCF Valuation (Exit Multiple Method)"""
    if partial_period_adj is None:
        partial_period_adj = [0.75, 1.0, 1.0, 1.0, 1.0, 1.0]
    
    # Discount discrete period FCFs
    pv_discrete = 0
    for i in range(len(ufcf) - 1):
        adj = partial_period_adj[i] if i < len(partial_period_adj) else 1.0
        pv_discrete += ufcf[i] / ((1 + wacc) ** (i + adj))
    
    # Terminal value (Exit Multiple)
    terminal_value = ebitda_terminal * terminal_multiple
    
    # Discount terminal value
    n = len(ufcf) - 1
    adj_terminal = partial_period_adj[-1] if len(partial_period_adj) > n else 1.0
    pv_terminal = terminal_value / ((1 + wacc) ** (n + adj_terminal))
    
    enterprise_value = pv_discrete + pv_terminal
    
    return {
        'pv_discrete': pv_discrete,
        'pv_terminal': pv_terminal,
        'enterprise_value': enterprise_value
    }


def calculate_equity_value(ev_perpetuity, ev_multiple, net_debt, shares_outstanding, current_stock_price=None):
    """Module 13: Equity Value Calculator"""
    equity_value_perpetuity = ev_perpetuity - net_debt
    equity_value_multiple = ev_multiple - net_debt
    
    equity_per_share_perpetuity = equity_value_perpetuity / shares_outstanding if shares_outstanding > 0 else 0
    equity_per_share_multiple = equity_value_multiple / shares_outstanding if shares_outstanding > 0 else 0
    
    upside_perpetuity = (equity_per_share_perpetuity - current_stock_price) / current_stock_price if current_stock_price and current_stock_price > 0 else 0
    upside_multiple = (equity_per_share_multiple - current_stock_price) / current_stock_price if current_stock_price and current_stock_price > 0 else 0
    
    return {
        'equity_value_perpetuity': equity_value_perpetuity,
        'equity_value_multiple': equity_value_multiple,
        'equity_per_share_perpetuity': equity_per_share_perpetuity,
        'equity_per_share_multiple': equity_per_share_multiple,
        'upside_perpetuity': upside_perpetuity,
        'upside_multiple': upside_multiple
    }


def run_complete_dcf(inputs):
    """Main DCF calculation function"""
    # Support both flat structure and nested structure
    hist = inputs.get('historical_financials', {}).get('fy_minus_1', inputs)
    scenario_name = inputs.get('scenario', 'base_case')
    drivers = inputs.get('forecast_drivers', {}).get(scenario_name, inputs)
    
    # Extract inputs with defaults
    base_revenue = inputs.get('base_revenue', hist.get('revenue', 100000))
    base_cogs = inputs.get('base_cogs', hist.get('cogs', 60000))
    base_sga = inputs.get('base_sga', hist.get('sga', 20000))
    base_other = inputs.get('base_other', hist.get('other_opex', 5000))
    base_existing_ppe = inputs.get('base_existing_ppe', hist.get('ppe', hist.get('total_assets', 50000)))
    base_nol = inputs.get('base_nol', hist.get('nol_remaining', 0))
    base_net_debt = inputs.get('base_net_debt', hist.get('net_debt', 0))
    base_current_stock_price = inputs.get('base_current_stock_price', hist.get('current_stock_price', 100))
    base_shares_outstanding = inputs.get('base_shares_outstanding', hist.get('shares_outstanding', 1000))
    
    # Forecast drivers (6 values: 5 years + terminal)
    revenue_growth_rates = inputs.get('revenue_growth_rates', drivers.get('sales_volume_growth', drivers.get('revenue_growth', [0.05] * 6)))
    inflation_rates = inputs.get('inflation_rates', drivers.get('inflation_rate', [0.02] * 6))
    opex_growth_rates = inputs.get('opex_growth_rates', drivers.get('opex_growth', drivers.get('inflation_rate', [0.02] * 6)))
    capital_expenditures = inputs.get('capital_expenditures', drivers.get('capital_expenditure', drivers.get('capex', [5000] * 5)))
    ar_days = inputs.get('ar_days', drivers.get('ar_days', 45))
    inv_days = inputs.get('inv_days', drivers.get('inv_days', drivers.get('inventory_days', 30)))
    ap_days = inputs.get('ap_days', drivers.get('ap_days', 60))
    
    # Assumptions
    useful_life_existing = inputs.get('useful_life_existing', 10)
    useful_life_new = inputs.get('useful_life_new', 5)
    tax_rate = inputs.get('tax_rate', hist.get('tax_rate', 0.21))
    nol_limit = inputs.get('nol_utilization_limit', drivers.get('tax_loss_utilization_limit_pct', 0.80))
    wacc = inputs.get('wacc', 0.097)
    terminal_growth_rate = inputs.get('terminal_growth_rate', 0.02)
    terminal_multiple = inputs.get('terminal_multiple', inputs.get('terminal_ebitda_multiple', 7.0))
    partial_period_adj = inputs.get('partial_period_adjustment', [0.75, 1.0, 1.0, 1.0, 1.0, 1.0])
    days_in_period = inputs.get('days_in_period', 365)
    
    # Ensure arrays have correct length
    if len(revenue_growth_rates) != 6:
        revenue_growth_rates = revenue_growth_rates[:6] if len(revenue_growth_rates) > 6 else revenue_growth_rates + [0.02] * (6 - len(revenue_growth_rates))
    
    # Handle CapEx array
    if len(capital_expenditures) < 5:
        capital_expenditures = capital_expenditures + [5000] * (5 - len(capital_expenditures))
    capex_forecast = capital_expenditures[:5]
    capex_terminal = capital_expenditures[5] if len(capital_expenditures) > 5 else None
    
    # Execute calculation modules
    revenue_schedule = calculate_revenue_schedule(base_revenue, revenue_growth_rates)
    cogs_schedule = calculate_cogs_schedule(base_cogs, inflation_rates)
    gross_profit = calculate_gross_profit(revenue_schedule['revenue'], cogs_schedule)
    opex_schedule = calculate_opex_schedule(base_sga, base_other, opex_growth_rates)
    ebitda_result = calculate_ebitda(gross_profit['gross_profit'], opex_schedule['sga'], opex_schedule['other'])
    depreciation = calculate_depreciation_schedule(base_existing_ppe, useful_life_existing, capex_forecast, useful_life_new)
    ebit = calculate_ebit(ebitda_result['ebitda'], depreciation['total_depreciation'])
    
    # Assume fixed interest expense (simplified model)
    interest_expense = [0] * 6
    ebt = [e - interest_expense[0] for e in ebit]
    
    # Tax schedules
    tax_unlevered = calculate_tax_schedule_unlevered(
        ebit, depreciation['total_depreciation'], depreciation['total_depreciation'],
        base_nol, tax_rate, nol_limit
    )
    
    # Working capital
    working_capital = calculate_working_capital_schedule(
        revenue_schedule['revenue'], cogs_schedule, ar_days, inv_days, ap_days, days_in_period
    )
    
    # UFCF
    ufcf = calculate_ufcf(
        ebitda_result['ebitda'], tax_unlevered['current_tax_unlevered'],
        capex_forecast, working_capital['change_nwc'],
        capex_terminal or depreciation['terminal_capex']
    )
    
    # DCF Valuation
    dcf_perpetuity = calculate_dcf_perpetuity(ufcf, wacc, terminal_growth_rate, partial_period_adj)
    dcf_multiple = calculate_dcf_multiple(ufcf, ebitda_result['ebitda'][5], terminal_multiple, wacc, partial_period_adj)
    
    # Equity Value
    equity_value = calculate_equity_value(
        dcf_perpetuity['enterprise_value'],
        dcf_multiple['enterprise_value'],
        base_net_debt,
        base_shares_outstanding,
        base_current_stock_price
    )
    
    # Build output structure
    output = {
        'success': True,
        'main_outputs': {
            'enterprise_value_perpetuity': round_to(dcf_perpetuity['enterprise_value'], 0),
            'enterprise_value_multiple': round_to(dcf_multiple['enterprise_value'], 0),
            'equity_value_perpetuity': round_to(equity_value['equity_value_perpetuity'], 0),
            'equity_value_multiple': round_to(equity_value['equity_value_multiple'], 0),
            'equity_value_per_share_perpetuity': round_to(equity_value['equity_per_share_perpetuity'], 2),
            'equity_value_per_share_multiple': round_to(equity_value['equity_per_share_multiple'], 2),
            'current_stock_price': base_current_stock_price,
            'upside_downside_perpetuity_pct': round_to(equity_value['upside_perpetuity'] * 100, 1),
            'upside_downside_multiple_pct': round_to(equity_value['upside_multiple'] * 100, 1)
        },
        'supporting_schedules': {
            'revenue_forecast': [round_to(r, 2) for r in revenue_schedule['revenue']],
            'ebitda_forecast': [round_to(e, 2) for e in ebitda_result['ebitda']],
            'ufcf_forecast': [round_to(u, 2) for u in ufcf],
            'discounting_details': {
                'pv_discrete_perpetuity': round_to(dcf_perpetuity['pv_discrete'], 2),
                'pv_terminal_perpetuity': round_to(dcf_perpetuity['pv_terminal'], 2),
                'enterprise_value_perpetuity': round_to(dcf_perpetuity['enterprise_value'], 2),
                'pv_discrete_multiple': round_to(dcf_multiple['pv_discrete'], 2),
                'pv_terminal_multiple': round_to(dcf_multiple['pv_terminal'], 2),
                'enterprise_value_multiple': round_to(dcf_multiple['enterprise_value'], 2)
            }
        },
        'metadata': {
            'scenario_used': scenario_name,
            'wacc': wacc,
            'terminal_growth_rate': terminal_growth_rate,
            'terminal_multiple': terminal_multiple
        }
    }
    
    return output


def run_dcf_with_scenarios(inputs):
    """Run DCF with multiple scenarios"""
    results = {}
    
    scenarios = ['base_case', 'best_case', 'worst_case']
    
    for scenario in scenarios:
        scenario_inputs = inputs.copy()
        scenario_inputs['scenario'] = scenario
        
        # Apply scenario-specific adjustments
        if scenario == 'best_case':
            base_growth = inputs.get('revenue_growth_rates', [0.05] * 6)
            scenario_inputs['revenue_growth_rates'] = [g * 1.2 for g in base_growth]
        elif scenario == 'worst_case':
            base_growth = inputs.get('revenue_growth_rates', [0.05] * 6)
            scenario_inputs['revenue_growth_rates'] = [g * 0.8 for g in base_growth]
        
        try:
            results[scenario] = run_complete_dcf(scenario_inputs)
        except Exception as e:
            results[scenario] = {'success': False, 'error': str(e)}
    
    return results


# Main entry point for testing
if __name__ == "__main__":
    import json
    
    # Test inputs
    test_inputs = {
        'base_revenue': 100000,
        'base_cogs': 60000,
        'base_sga': 20000,
        'base_other': 5000,
        'base_existing_ppe': 50000,
        'base_net_debt': 10000,
        'base_shares_outstanding': 1000,
        'base_current_stock_price': 150,
        'revenue_growth_rates': [0.05, 0.05, 0.05, 0.04, 0.03, 0.02],
        'capital_expenditures': [5000, 5000, 5000, 5000, 5000],
        'wacc': 0.10,
        'terminal_growth_rate': 0.02,
        'terminal_multiple': 8.0,
        'tax_rate': 0.21
    }
    
    result = run_complete_dcf(test_inputs)
    print(json.dumps(result, indent=2))
