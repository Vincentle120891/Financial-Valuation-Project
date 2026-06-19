"""
Vietnamese DCF Schedule Builder — Building Block Schedules for Step 9
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _get_latest(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    val = data.get(key, default)
    if isinstance(val, dict):
        return float(val.get('latest', val.get('value', default)))
    if isinstance(val, list) and len(val) > 0:
        return float(val[-1]) if val[-1] is not None else default
    return float(val) if val is not None else default


def build_vn_schedules(
    confirmed_params: Dict[str, Any],
    historical_financials: Dict[str, Any],
    market_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build all Vietnamese DCF building block schedules for Step 9."""
    mc = market_context or {}
    h = historical_financials

    n = int(confirmed_params.get('forecast_years', 5))
    tax = float(confirmed_params.get('tax_rate', 0.20))
    capex_pct = float(confirmed_params.get('capex_as_percent_revenue',
                       confirmed_params.get('capex_percent_revenue', 0.05)))
    ar_d = float(confirmed_params.get('receivables_days',
                     confirmed_params.get('ar_days', 45)))
    inv_d = float(confirmed_params.get('inventory_days',
                      confirmed_params.get('inv_days', 30)))
    ap_d = float(confirmed_params.get('payables_days',
                     confirmed_params.get('ap_days', 40)))
    ul_new = float(confirmed_params.get('useful_life_new', 20))
    ul_old = float(confirmed_params.get('useful_life_existing', 16))
    cr = float(confirmed_params.get('cash_interest_rate', 0.01))
    ltr = float(confirmed_params.get('lt_debt_interest_rate', 0.06))
    rr = float(confirmed_params.get('revolving_credit_rate',
                 confirmed_params.get('revolving_interest_rate', 0.05)))
    payout = float(confirmed_params.get('dividend_payout_ratio',
                      confirmed_params.get('payout_ratio', 0.30)))

    rg = []
    for i in range(1, n + 1):
        g = confirmed_params.get(f'revenue_growth_year_{i}',
                confirmed_params.get(f'revenue_growth_{i}', 0.08))
        rg.append(float(g) if g is not None else 0.08)

    hr = _get_latest(h, 'revenue', 0)
    hc = _get_latest(h, 'cogs', 0)
    hs = _get_latest(h, 'selling_general_administrative',
         _get_latest(h, 'sg_and_a', 0))

    cash_o = float(confirmed_params.get('cash_opening',
                       _get_latest(h, 'cash_and_equivalents', 0)))
    ltd_o = float(confirmed_params.get('long_term_debt_opening',
                     _get_latest(h, 'long_term_debt', 0)))
    eq_o = float(confirmed_params.get('common_equity_opening',
                    _get_latest(h, 'shareholders_equity', 0)))
    re_o = float(confirmed_params.get('retained_earnings_opening',
                     _get_latest(h, 'retained_earnings', 0)))
    ppe_o = float(confirmed_params.get('ppe_gross_opening',
                     _get_latest(h, 'ppe_gross', 0)))

    years = [f"FY{i+1}" for i in range(n)]

    # Revenue
    revs = []; cur = hr
    for g in rg:
        cur = cur * (1 + g); revs.append(round(cur, 2))

    # COGS
    cr_r = hc / hr if hr else 0.65
    cogs = [round(r * cr_r, 2) for r in revs]

    # GP, SGA, EBITDA
    gp = [round(r - c, 2) for r, c in zip(revs, cogs)]
    sr = hs / hr if hr else 0.15
    sga = [round(r * sr, 2) for r in revs]
    ebitdas = [round(g - s, 2) for g, s in zip(gp, sga)]

    # Depreciation
    depr = _build_depr(n, revs, capex_pct, ul_old, ul_new, ppe_o, years)

    # EBIT, Interest, EBT
    ebits = [round(e - d, 2) for e, d in zip(ebitdas, depr['total_depreciation'])]
    lt_int = ltd_o * ltr
    interest = [round(lt_int, 2)] * n
    ebts = [round(e - i, 2) for e, i in zip(ebits, interest)]

    # Working Capital
    wc = _build_wc(n, revs, cogs, ar_d, inv_d, ap_d,
                   _get_latest(h, 'accounts_receivable', 0),
                   _get_latest(h, 'inventory', 0),
                   _get_latest(h, 'accounts_payable', 0), years)

    # CapEx
    capex = [round(r * capex_pct, 2) for r in revs]

    # Tax
    t_lev = _build_tax_lev(n, ebts, depr['total_depreciation'],
                           depr['tax_depreciation'], tax, years)
    t_unlev = _build_tax_unlev(n, ebits, depr['total_depreciation'],
                               depr['tax_depreciation'], tax, years)

    # Net Income
    ni = [round(e - t, 2) for e, t in zip(ebts, t_lev['total_tax'])]

    # Equity
    eq = _build_equity(n, ni, payout, eq_o, re_o, years)
    divs = eq['dividends']

    # CFS
    cfs = _build_cfs(n, ni, t_lev['deferred_tax'], depr['total_depreciation'],
                     wc, capex, divs, cash_o, years)

    # Debt
    dp1 = _build_dp1(n, cfs, cash_o, cr, ltd_o, ltr, years)
    dp2 = _build_dp2(n, cfs, dp1, eq, rr, years)

    cfs['revolving_credit'] = dp2['revolving_credit']
    cfs['change_in_lt_debt'] = [0.0] * n
    cfs['change_in_common_equity'] = [0.0] * n
    cfs['interest_expense'] = dp2['net_interest']

    # Balance Sheet
    bs = _build_bs(n, cfs, wc, depr, eq, dp1, ltd_o, eq_o, re_o, ppe_o, years)

    # WACC
    rf = float(confirmed_params.get('risk_free_rate',
                 mc.get('risk_free_rate', 0.068)))
    beta = float(confirmed_params.get('beta', 1.0))
    mrp = float(confirmed_params.get('market_risk_premium',
                 mc.get('market_risk_premium', 0.075)))
    crp = float(confirmed_params.get('country_risk_premium',
                 mc.get('country_risk_premium', 0.035)))
    cod = float(confirmed_params.get('cost_of_debt', ltr))
    de = float(confirmed_params.get('debt_to_equity', 0.5))

    ke = rf + beta * (mrp + crp)
    we = 1 / (1 + de) if de >= 0 else 1.0
    wd = de / (1 + de) if de >= 0 else 0.0
    wacc = we * ke + wd * cod * (1 - tax)
    wacc = max(wacc, rf); wacc = min(wacc, 0.30)

    wc_calc = {
        'risk_free_rate': rf, 'beta': beta, 'market_risk_premium': mrp,
        'country_risk_premium': crp, 'cost_of_equity': round(ke, 6),
        'cost_of_debt': cod, 'tax_rate': tax, 'debt_to_equity': de,
        'equity_weight': round(we, 4), 'debt_weight': round(wd, 4),
        'wacc': round(wacc, 6),
    }

    is_sched = {
        'years': years, 'revenue': revs, 'cogs': cogs, 'cost_of_revenue': cogs,
        'gross_profit': gp, 'selling_general_administrative': sga,
        'sg_and_a': sga, 'other_operating_expenses': [0.0] * n,
        'ebitda': ebitdas,
        'depreciation_amortization': depr['total_depreciation'],
        'depreciation': depr['total_depreciation'],
        'ebit': ebits, 'interest_expense': interest, 'ebt': ebts,
        'current_tax': t_lev['current_tax'],
        'deferred_tax': t_lev['deferred_tax'],
        'total_tax': t_lev['total_tax'], 'net_income': ni,
    }

    return {
        'supporting_schedules': {
            'income_statement': is_sched,
            'working_capital': wc,
            'depreciation': depr,
            'tax_levered': t_lev,
            'tax_unlevered': t_unlev,
            'wacc_calculation': wc_calc,
        },
        'cash_flow_statement': cfs,
        'balance_sheet': bs,
        'wacc': wacc,
        'wacc_calculation': wc_calc,
        'terminal_growth_rate': float(confirmed_params.get('terminal_growth_rate', 0.03)),
        'forecast_years': n,
        'validation_flags': {},
        'warnings': [],
    }


def _build_wc(n, revs, cogs, ar_d, inv_d, ap_d, h_ar, h_inv, h_ap, years):
    ar_b, inv_b, ap_b, nwc, chg, c_ar, c_inv, c_ap = [], [], [], [], [], [], [], []
    p_ar, p_inv, p_ap = h_ar, h_inv, h_ap
    p_nwc = h_ar + h_inv - h_ap
    for i in range(n):
        ar = (ar_d / 365) * revs[i]
        inv = (inv_d / 365) * abs(cogs[i])
        ap = (ap_d / 365) * abs(cogs[i])
        cn = ar + inv - ap
        ar_b.append(round(ar, 2)); inv_b.append(round(inv, 2))
        ap_b.append(round(ap, 2)); nwc.append(round(cn, 2))
        chg.append(round(cn - p_nwc, 2))
        c_ar.append(round(p_ar - ar, 2)); c_inv.append(round(p_inv - inv, 2))
        c_ap.append(round(ap - p_ap, 2))
        p_ar, p_inv, p_ap, p_nwc = ar, inv, ap, cn
    return {
        'years': years, 'ar_days': [ar_d]*n, 'inventory_days': [inv_d]*n,
        'ap_days': [ap_d]*n, 'accounts_receivable': ar_b,
        'inventories': inv_b, 'accounts_payable': ap_b,
        'net_working_capital': nwc, 'change_in_nwc': chg,
        'cash_from_ar': c_ar, 'cash_from_inventory': c_inv, 'cash_from_ap': c_ap,
    }


def _build_depr(n, revs, capex_pct, ul_old, ul_new, ppe_open, years):
    capex_list = [round(r * capex_pct, 2) for r in revs]
    existing_dep = []
    new_dep_cohorts = []
    total_dep = []
    gross_ppe = []
    tax_dep = []
    tax_basis = []
    ppe_end = ppe_open
    tb = ppe_open
    cohorts = []
    for i in range(n):
        # Existing assets depreciation
        if ul_old > 0:
            ed = ppe_open / ul_old if i < ul_old else 0
        else:
            ed = 0
        # New asset cohort
        cx = capex_list[i]
        cohorts.append(cx / ul_new if ul_new > 0 else 0)
        nd = sum(
            cohorts[j] * (0.5 if j == i else 1.0)
            for j in range(len(cohorts))
        ) if cohorts else 0
        td = round(ed + nd, 2)
        existing_dep.append(round(ed, 2))
        new_dep_cohorts.append(round(nd, 2))
        total_dep.append(td)
        ppe_end = ppe_end + cx - ed
        gross_ppe.append(round(ppe_end, 2))
        # Tax depreciation (declining balance 15%)
        t_dep = (tb + cx * 0.5) * 0.15
        tax_dep.append(round(t_dep, 2))
        tb = tb + cx - t_dep
        tax_basis.append(round(tb, 2))
    # Terminal capex = terminal depreciation
    term_capex = total_dep[-1] if total_dep else 0
    capex_list.append(round(term_capex, 2))
    return {
        'years': years, 'capital_expenditure': capex_list,
        'existing_depreciation': existing_dep,
        'new_asset_depreciation': new_dep_cohorts,
        'total_depreciation': total_dep,
        'gross_ppe_ending': gross_ppe,
        'tax_depreciation': tax_dep, 'tax_basis_ending': tax_basis,
    }


def _build_tax_lev(n, ebts, acctg_dep, tax_dep, tax_rate, years):
    ct, dt, tt = [], [], []
    for i in range(n):
        adj = ebts[i] + (acctg_dep[i] if i < len(acctg_dep) else 0) - (tax_dep[i] if i < len(tax_dep) else 0)
        total = max(adj * tax_rate, 0)
        current = max(adj, 0) * tax_rate
        deferred = total - current
        ct.append(round(current, 2))
        dt.append(round(deferred, 2))
        tt.append(round(total, 2))
    return {'years': years, 'current_tax': ct, 'deferred_tax': dt, 'total_tax': tt}


def _build_tax_unlev(n, ebits, acctg_dep, tax_dep, tax_rate, years):
    ct, dt, tt = [], [], []
    for i in range(n):
        adj = ebits[i] + (acctg_dep[i] if i < len(acctg_dep) else 0) - (tax_dep[i] if i < len(tax_dep) else 0)
        total = max(adj * tax_rate, 0)
        current = max(adj, 0) * tax_rate
        deferred = total - current
        ct.append(round(current, 2))
        dt.append(round(deferred, 2))
        tt.append(round(total, 2))
    return {'years': years, 'current_tax': ct, 'deferred_tax': dt, 'total_tax': tt}


def _build_equity(n, ni, payout, eq_o, re_o, years):
    ce, re_arr, divs = [], [], []
    p_ce, p_re = eq_o, re_o
    for i in range(n):
        d = -ni[i] * payout if ni[i] > 0 else 0
        divs.append(round(d, 2))
        ce_val = p_ce
        re_val = p_re + ni[i] + d
        ce.append(round(ce_val, 2))
        re_arr.append(round(re_val, 2))
        p_ce, p_re = ce_val, re_val
    return {'years': years, 'common_equity': ce, 'retained_earnings': re_arr,
            'dividends': divs, 'net_income': ni}


def _build_cfs(n, ni, def_tax, dep, wc, capex, divs, cash_o, years):
    cfo = [round(ni[i] + def_tax[i] + dep[i] + wc['cash_from_ar'][i] + wc['cash_from_inventory'][i] + wc['cash_from_ap'][i], 2) for i in range(n)]
    cfi = [round(-capex[i], 2) for i in range(n)]
    cff = [round(divs[i], 2) for i in range(n)]
    bc, inc, ec = [], [], []
    p = cash_o
    for i in range(n):
        bc.append(round(p, 2))
        ch = cfo[i] + cfi[i] + cff[i]
        inc.append(round(ch, 2))
        e = p + ch
        ec.append(round(e, 2))
        p = e
    return {
        'years': years, 'net_income': ni, 'deferred_taxes': def_tax,
        'depreciation': dep, 'cash_from_ar': wc['cash_from_ar'],
        'cash_from_inventory': wc['cash_from_inventory'],
        'cash_from_ap': wc['cash_from_ap'], 'subtotal_cfo': cfo,
        'capital_expenditure': cfi, 'subtotal_cfi': cfi,
        'dividends': cff, 'subtotal_cff': cff,
        'beginning_cash': bc, 'increase_decrease': inc, 'ending_cash': ec,
    }


def _build_dp1(n, cfs, cash_o, cr, ltd_o, ltr, years):
    cb, cc, ce = [], [], []
    ltb, lti = [], []
    p = cash_o
    for i in range(n):
        cb.append(round(p, 2))
        ch = cfs['increase_decrease'][i] if i < len(cfs['increase_decrease']) else 0
        e = p + ch
        ce.append(round(e, 2))
        cc.append(round(ch, 2))
        ltb.append(round(ltd_o, 2))
        lti.append(round(ltd_o * ltr, 2))
        p = e
    return {'years': years, 'cash_beginning': cb, 'cash_change': cc,
            'cash_ending': ce, 'lt_debt_ending': ltb, 'lt_interest': lti}


def _build_dp2(n, cfs, dp1, eq, rr, years):
    rev_c = []
    ni = cfs['net_income']
    for i in range(n):
        avail = dp1['cash_ending'][i] + (cfs['subtotal_cfo'][i] if i < len(cfs['subtotal_cfo']) else 0)
        rev_c.append(round(-min(avail, 0), 2) if avail < 0 else 0)
    ri = [round(max(rev_c[i], 0) * rr, 2) for i in range(n)]
    net_int = [round(dp1['lt_interest'][i] + ri[i] - (dp1['cash_ending'][i] * 0.01 if i < len(dp1['cash_ending']) else 0), 2) for i in range(n)]
    return {'years': years, 'revolving_credit': rev_c, 'revolving_interest': ri,
            'net_interest': net_int}


def _build_bs(n, cfs, wc, depr, eq, dp1, ltd_o, eq_o, re_o, ppe_o, years):
    cash = cfs['ending_cash']
    ar = wc['accounts_receivable']
    inv = wc['inventories']
    ap = wc['accounts_payable']
    ppe = depr['gross_ppe_ending']
    ltd = dp1['lt_debt_ending']
    ce = eq['common_equity']
    re_a = eq['retained_earnings']
    tca = [round(cash[i] + ar[i] + inv[i], 2) for i in range(n)]
    ta = [round(tca[i] + ppe[i], 2) for i in range(n)]
    tcl = [round(ap[i], 2) for i in range(n)]
    tl = [round(tcl[i] + ltd[i], 2) for i in range(n)]
    tse = [round(ce[i] + re_a[i], 2) for i in range(n)]
    tle = [round(tl[i] + tse[i], 2) for i in range(n)]
    check = [round(ta[i] - tle[i], 2) for i in range(n)]
    return {
        'years': years, 'cash': cash, 'accounts_receivable': ar,
        'inventories': inv, 'total_current_assets': tca,
        'ppe_gross': ppe, 'total_assets': ta,
        'accounts_payable': ap, 'revolving_credit': dp1.get('cash_ending', [0]*n),
        'total_current_liabilities': tcl, 'long_term_debt': ltd,
        'total_liabilities': tl, 'common_equity': ce,
        'retained_earnings': re_a, 'shareholders_equity': tse,
        'total_liabilities_equity': tle, 'balance_check': check,
    }
