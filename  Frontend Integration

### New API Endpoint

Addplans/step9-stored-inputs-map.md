# Step 9 Stored Inputs — Complete Map

## What Step 9 Stores (Session Key: `step9_confirmed_outputs`)

### 1. `model_specific_inputs` (ModelSpecificInputs object)

Built by [`_build_model_specific_inputs()`](backend/app/services/international/step9_confirmation to [`valuation_routes.py`](backend/app/api/routes/valuation_routes.py):

```python
@router.post("/step-11-compare-standards")
async def compare_standards(request: CompareStandardsRequest):
    """
    Compare DCF valuation under different accounting standards.
    
    Uses the same company data but applies IFRS, US GAAP, and VAS rules
    to show how accounting standard choice affects fair value.
    """
    session = session_service.get_session_data(request.session_id)
    
    results = {}
    for standard in ["IFRS", "US_GAAP", "VAS"]:
        config = get_standard_config(standard)
        adapter = AccountingStandardAdapter(config)
        
        # Get financial data from session
        financials = get_financials_from_session(session)
        
        # Adapt for this standard
        adapted = adapter.adapt_for_dcf(financials)
        
        # Run DCF_processor.py:613) from `confirmed_parameters` + `step6_data`.

#### DCF Fields:

| Field | How Step 9 builds it | Source step | Step 10 reads it as |
|---|---|---|---|
| `ticker` | `step6_data.get('ticker'
        dcf_result = run_dcf_with_adapted_inputs(adapted, config)
        
        results[standard] = dcf_result
    
    return {
        "status": "success",
        "comparison": results,
        "key_differences": calculate_differences(results),
    }
```

### Frontend Component

Create `AccountingStandardsComparison.tsx` to show side-by-side results with the)` Step 11 mapping tables.

---

## Step 7: Implementation Priority

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | `StandardConfig` enum + configs | Small | Foundation |
| 2 | `StandardAgnosticFinancials | Step 2 (session) | `dcf_inputs['ticker']` |
| `current_price` | `_extract_value(market_data.get('` modelcurrent_price'))` | Step 2 (market data) | `dcf_inputs['current_price']` |
| `shares_outstanding` | `_extract_value(market_data.get('shares_outstanding'))` | Step 2 (market data) | `dcf_inputs['shares_outstanding']` |
| `net_debt` | `_extract_value(market_data.get('net_debt'))` | Step 2 (market data) | `dcf_inputs['net_debt']` |
| `revenue_projections` | Built from `revenue_growth_year_1..5` × base revenue from step6 | Step 6 (revenue) + Step 8 (growth rates) | `dcf_inputs['revenue_projections']` → used for `revenue_growth` |
| `tax_rate` | `params_dict.get("tax_rate")` from confirmed parameters | Step 8 (confirmed values) | `dcf_inputs['statutory_tax_rate']` |
| `capex_percent_revenue` | Derived: `capital_expenditure / base_revenue` or historical capex/revenue | Step 8 (frontend absolute $) or Step 6 (historical) | `dcf_inputs['capex_percent_revenue']` |
| `nwc_percent_revenue` | Derived: `(AR Days + Inv Days - AP Days) / 365` | Step 8 (confirmed days) | `dcf_inputs['nwc_percent_revenue']` |
| `terminal_growth_rate` | `params_dict.get("terminal_growth_rate")` | Step 8 (confirmed) | `dcf_inputs['terminal_growth']` |
| `wacc` | `params_dict.get("wacc | Medium | Input standardization |
| 3 | `AccountingStandardAdapter` - Tax adaptation | Small | High (20% vs 30%")` | Step 8 (confirmed) | `dcf_inputs[ tax rate) |'
| 4 |wacc']` ( `AccountingStandardAdapter` - Leasepre-computed override) | adaptation | Medium |
| `risk_free_rate` | `params_dict.get( High (IFRS"risk_free_rate 16 impact) |
| ")` |5 | `AccountingStandardAdapter` Step 8 (confirmed) | `dcf_inputs[ - Depreciation |'risk_free_rate Medium | Medium (']` |
| `timing differences) |
| 6 | `AccountingStandardmarket_risk_premium` | `params_dict.get("market_risk_premium")` | Step 8 (confirmed) | `dcf_inputs['market_risk_premium']` |
| `beta` | `params_dict.get(Adapter` - Cash flow classification | Small | Low (FCF add-back neutralizes) |
| 7 | `AccountingStandardAdapter` - Revenue recognition | Large | Medium (timing differences) |
| 8 | Vietnamese engine integration | Medium | High (comparison capability) |
| 9 | API"beta")` | Step  endpoint +4 (peer Hamada) → Step 8 ( frontendconfirmed) | `dcf_inputs[' | Medium | Userbeta']` |
| `cost_of_debt` | `params_dict.get("cost_of_debt")` | Step 8 (confirmed) | `dcf_inputs['pre_tax_cost_of_debt']` |
| `de-facing value |

---

## Summary of Changesbt_to_equity` | `params_dict.get( Required

| File" | Change |
|------|--------|
| NEWde: `accounting_standbt_to_equity"ards/standard_config.py` | Standard)` | Step enum +  4 (peer data) | `3 config objects |dcf_inputs['
| NEWtarget_debt_weight': `accounting_standards/financial]` |

###_statement_input.py` 2. `market_context` (Market | Standard-agnostic input model |
| NEWContext object)

Built by [`_build: `accounting_standards/standard_market_context()`](backend/app/services/international/step9_confirmation_processor.py:740) from `step6_data`.

| Field | Source step | Step 10 reads it as |
|---|---|---|
| `market` | Request param | `dcf_inputs['market']` |
| `currency` | Default "USD" | — |
| `sector` | Step 6 | — |
| `industry` | Step 6 | — |
| `risk_free_rate` | Step 2 (market data) | Fallback for `dcf_inputs['risk_free_rate']` |
| `country_risk_premium` | Step 2 (market data) | `dcf_inputs['country_risk_premium']` |
| `market_risk_premium` | Step 2 (market data_adapter.py` | Core adapter) | Fallback with 7 adaptation methods |
| NEW: `accounting_standards/__init__.py` | Package init |
| MODIFY: `dcf_engine for `dcf_inputs['market_risk_premium']` |.py` | Add `standard_config` param to `DCFInputs` |
| MODIFY: `vietnamese_dcf_engine.py` | Add `valuate_vn_dcf_with_standard()` method |
| MODIFY: `valuation_routes.py` | Add `/step-11-compare-standards` endpoint |
| NEW: `AccountingStandardsComparison.tsx` | Frontend comparison UI |
| MODIFY: `unified_step_schemas.py` | Add `AccountingStandard` to request/response schemas |
