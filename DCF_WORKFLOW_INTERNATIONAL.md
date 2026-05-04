# DCF Model (International Market) - Complete Function Call Workflow

This document traces the exact function calls through files for the **DCF Model** in the **International Market**, from API endpoint to final valuation output.

---

## 📍 Starting Point: API Endpoint

### File: `/workspace/backend/app/api/routes/valuation_routes.py`

**Endpoint:** `POST /step-10-valuate`  
**Line:** 1118-1152

```python
@router.post("/step-10-valuate", response_model=ValuationResultResponse)
async def run_valuation(request: CalculationRequest):
    # Line 1129: Import session store
    from app.main import get_session_store
    
    # Line 1133-1134: Get session data
    sessions = get_session_store()
    session = get_session(request.session_id, sessions)
    
    # Line 1136-1140: Validate confirmed assumptions
    if not session['confirmed_assumptions']:
        raise ValidationException(...)
    
    # Line 1142: CALL → run_valuation_engine(session)
    results = run_valuation_engine(session)
    
    # Line 1143-1144: Update session
    session['valuation_result'] = results
    session['status'] = "completed"
    
    # Line 1148-1152: Return response
    return ValuationResultResponse(
        status="completed",
        result=results,
        inputs_used=session['confirmed_assumptions']
    )
```

---

## 🔧 Step 1: Valuation Engine Dispatcher

### File: `/workspace/backend/app/api/routes/valuation_routes.py`

**Function:** `run_valuation_engine(session_data: Dict)`  
**Line:** 279-441

```python
def run_valuation_engine(session_data: Dict) -> Dict:
    # Line 289: Import DCF components
    from app.engines.dcf_engine import DCFEngine, DCFInputs, ScenarioDrivers, fetch_dcf_inputs
    
    # Line 291-297: Extract session data
    model = session_data.get('selected_model', 'DCF')
    market = session_data.get('market', 'international')
    assumptions = session_data['confirmed_assumptions']
    financial_data = session_data['financial_data']
    financials = financial_data['financials']
    profile = financial_data['profile']
    ticker = session_data.get('ticker', 'UNKNOWN')
    
    # Line 303: Check if DCF model selected
    if selected_model == 'dcf':
        # Line 305-309: CALL → fetch_dcf_inputs(ticker_symbol, peer_tickers)
        company_info, comparables = fetch_dcf_inputs(ticker_symbol, peer_tickers_from_input)
        
        # Line 311-321: Extract historical data and build inputs
        revenue_history = list(financials.get('revenue', {}).values())
        # ... (extract EBITDA, net income, shares, debt, cash, etc.)
        
        # Line 353-375: Build ScenarioDrivers from assumptions
        base_drivers = ScenarioDrivers(
            volume_growth=base_volume_growth,
            price_growth=base_price_growth,
            inflation_rate=inflation_rates,
            capex=capex_array,
            ar_days=ar_days_array,
            inv_days=inv_days_array,
            ap_days=ap_days_array,
            terminal_ebitda_multiple=terminal_multiple,
            terminal_growth_rate=terminal_growth
        )
        
        # Line 377-404: Build DCFInputs
        dcf_inputs = DCFInputs(
            valuation_date=date.today().isoformat(),
            currency=profile.get('currency', 'USD'),
            historical_fy_minus_1=hist_fy_minus_1,
            historical_fy_minus_2=hist_fy_minus_2,
            historical_fy_minus_3=hist_fy_minus_3,
            net_debt=net_debt,
            ppe_net=ppe_net,
            tax_basis_ppe=ppe_net * 0.8,
            tax_losses_nol=0,
            shares_outstanding=shares_outstanding,
            current_stock_price=current_price,
            projected_interest_expense=net_debt * 0.05,
            useful_life_existing=assumptions.get('useful_life_existing', 10.0),
            useful_life_new=assumptions.get('useful_life_new', 10.0),
            forecast_drivers={
                "base_case": base_drivers,
                "best_case": base_drivers,
                "worst_case": base_drivers
            },
            wacc=wacc,
            risk_free_rate=assumptions.get('risk_free_rate', 0.045),
            equity_risk_premium=assumptions.get('equity_risk_premium', 0.055),
            beta=assumptions.get('beta', 1.0),
            cost_of_debt=assumptions.get('cost_of_debt', 0.05),
            tax_rate_statutory=assumptions.get('tax_rate', 0.21),
            tax_loss_utilization_limit_pct=assumptions.get('tax_loss_utilization_limit_pct', 0.80)
        )
        
        # Line 406: INSTANTIATE → DCFEngine(dcf_inputs)
        engine = DCFEngine(dcf_inputs)
        
        # Line 407: CALL → engine._calculate_dcf_perpetuity(base_drivers)
        pv_discrete, pv_terminal_perp, ev_perpetuity = engine._calculate_dcf_perpetuity(base_drivers)
        
        # Line 408: CALL → engine._calculate_dcf_exit_multiple(base_drivers)
        pv_terminal_mult, ev_multiple = engine._calculate_dcf_exit_multiple(base_drivers)
        
        # Line 410-415: Calculate equity values and share prices
        equity_value_perp = ev_perpetuity - net_debt
        equity_value_mult = ev_multiple - net_debt
        share_price_perp = equity_value_perp / shares_outstanding
        share_price_mult = equity_value_mult / shares_outstanding
        upside_perp = (share_price_perp - current_price) / current_price * 100
        upside_mult = (share_price_mult - current_price) / current_price * 100
        
        # Line 419-433: Return DCF results
        return {
            "model": "DCF",
            "main_outputs": {
                "enterprise_value_perpetuity": round(ev_perpetuity, 2),
                "enterprise_value_multiple": round(ev_multiple, 2),
                "equity_value_perpetuity": round(equity_value_perp, 2),
                "equity_value_multiple": round(equity_value_mult, 2),
                "equity_value_per_share_perpetuity": round(share_price_perp, 2),
                "equity_value_per_share_multiple": round(share_price_mult, 2),
                "current_stock_price": current_price,
                "upside_downside_perpetuity_pct": round(upside_perp, 2),
                "upside_downside_multiple_pct": round(upside_mult, 2)
            },
            "message": "DCF calculated successfully"
        }
```

---

## 📊 Step 2: Fetch DCF Inputs (Market Data)

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Function:** `fetch_dcf_inputs(ticker: str, peer_tickers: Optional[List[str]] = None)`  
**Line:** 1444-1511

```python
def fetch_dcf_inputs(ticker: str, peer_tickers: Optional[List[str]] = None):
    # Line 1455: IMPORT → yfinance
    import yfinance as yf
    
    # Line 1458-1466: Fetch target company info via yfinance
    target = yf.Ticker(ticker)
    info = target.info
    company_name = info.get("longName", ticker)
    industry = info.get("industry", "General")
    sector = info.get("sector", "General")
    market_cap = info.get("marketCap", 0)
    enterprise_value = info.get("enterpriseValue", 0)
    beta = info.get("beta", 1.0)
    
    # Line 1472-1480: If no peers provided, use AI engine
    if peer_tickers is None or len(peer_tickers) == 0:
        # CALL → suggest_peer_companies(ticker, num_peers=10)
        ai_suggestions = suggest_peer_companies(ticker, num_peers=10)
        if ai_suggestions:
            peer_tickers = [p["ticker"] for p in ai_suggestions]
    
    # Line 1483-1506: Fetch peer data and build ComparableCompany objects
    comparables = []
    for peer_ticker in peer_tickers:
        peer_yf = yf.Ticker(peer_ticker)
        peer_info = peer_yf.info
        
        debt = peer_info.get("totalDebt", 0)
        equity = peer_info.get("marketCap", 0)
        tax_rate = peer_info.get("taxRate", 0.21)
        levered_beta = peer_info.get("beta", 1.0)
        
        # Create ComparableCompany object
        comp = ComparableCompany(
            name=peer_info.get("longName", peer_ticker),
            debt=debt,
            equity=equity,
            tax_rate=tax_rate,
            levered_beta=levered_beta
        )
        comparables.append(comp)
    
    # Line 1511: Return target info and comparables
    return info, comparables
```

---

## 🤖 Optional: AI Peer Suggestion (if no peers provided)

### File: `/workspace/backend/app/engines/ai_engine.py`

**Function:** `suggest_peer_companies(ticker, num_peers=10)`  
*(Called from `dcf_engine.py` line 1474)*

```python
def suggest_peer_companies(target_ticker: str, num_peers: int = 10):
    """
    Uses AI (Groq API) to suggest peer companies based on:
    - Industry classification
    - Sector
    - Market cap
    - Geographic region
    - Business description similarity
    """
    # Implementation uses LLM to analyze company profiles
    # Returns list of {"ticker": str, "name": str, "rationale": str}
```

---

## ⚙️ Step 3: DCF Engine Initialization

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Class:** `DCFEngine`  
**Line:** 359+

```python
class DCFEngine:
    def __init__(self, inputs: DCFInputs):
        self.inputs = inputs
        self.validation_flags = {}
```

---

## 💰 Step 4: WACC Calculation

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine.calculate_wacc()`  
**Line:** 369-404  
*(Called from `calculate()` method at line 980)*

```python
def calculate_wacc(self) -> Tuple[float, float, float, float]:
    # Line 374-379: If no comparables, use default WACC
    if not self.inputs.comparable_companies:
        after_tax_cost_of_debt = self.inputs.pre_tax_cost_of_debt * (1 - self.inputs.statutory_tax_rate)
        wacc = (self.inputs.target_debt_weight * after_tax_cost_of_debt + 
               self.inputs.target_equity_weight * 0.10)
        return wacc, 1.0, 1.0, 0.10
    
    # Line 382-386: Calculate average unlevered beta and tax rate
    unlevered_betas = [comp.unlevered_beta for comp in self.inputs.comparable_companies]
    tax_rates = [comp.tax_rate for comp in self.inputs.comparable_companies]
    avg_unlevered_beta = sum(unlevered_betas) / len(unlevered_betas)
    avg_tax_rate = sum(tax_rates) / len(tax_rates)
    
    # Line 389-390: Re-lever beta using target capital structure
    target_d_e = self.inputs.target_debt_weight / self.inputs.target_equity_weight
    levered_beta = avg_unlevered_beta * (1 + (1 - avg_tax_rate) * target_d_e)
    
    # Line 393-395: Calculate Cost of Equity (CAPM formula)
    cost_of_equity = (self.inputs.risk_free_rate + 
                     self.inputs.market_risk_premium * levered_beta +
                     self.inputs.country_risk_premium)
    
    # Line 398: After-tax cost of debt
    after_tax_cost_of_debt = self.inputs.pre_tax_cost_of_debt * (1 - self.inputs.statutory_tax_rate)
    
    # Line 401-402: Calculate WACC
    wacc = (self.inputs.target_debt_weight * after_tax_cost_of_debt +
           self.inputs.target_equity_weight * cost_of_equity)
    
    # Line 404: Return tuple
    return wacc, avg_unlevered_beta, levered_beta, cost_of_equity
```

**ComparableCompany Property (Line 92-94):**
```python
@property
def unlevered_beta(self) -> float:
    """Hamada formula: βu = βl / (1 + (1-t) * D/E)"""
    return self.levered_beta / (1 + (1 - self.tax_rate) * self.d_e_ratio)
```

---

## 📈 Step 5: Revenue Schedule Building

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._build_revenue_schedule(drivers)`  
**Line:** 406-422  
*(Called from `calculate()` at line 992)*

```python
def _build_revenue_schedule(self, drivers: ScenarioDrivers) -> List[float]:
    """
    Build revenue forecast using separate volume and price growth.
    Formula: Revenue[t] = Revenue[t-1] × (1 + Volume Growth[t]) × (1 + Price Growth[t])
    """
    # Line 412: Start with last historical year
    revenue = [self.inputs.historical_revenue[-1]]
    
    # Line 414-419: Forecast 6 periods (FY1-FY5 + Terminal)
    for i in range(6):
        vol_growth = drivers.volume_growth[i]
        price_growth = drivers.price_growth[i]
        new_revenue = revenue[-1] * (1 + vol_growth) * (1 + price_growth)
        revenue.append(new_revenue)
    
    # Line 422: Remove base year
    return revenue[1:]
```

---

## 🏭 Step 6: COGS Schedule Building

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._build_cogs_schedule(drivers)`  
**Line:** 424-436  
*(Called from `calculate()` at line 995)*

```python
def _build_cogs_schedule(self, drivers: ScenarioDrivers) -> List[float]:
    """
    Build COGS forecast using inflation rate.
    Formula: COGS[t] = COGS[t-1] × (1 + Inflation[t])
    """
    cogs = [self.inputs.historical_cogs[-1]]
    
    for i in range(6):
        inflation = drivers.inflation_rate[i]
        new_cogs = cogs[-1] * (1 + inflation)
        cogs.append(new_cogs)
    
    return cogs[1:]
```

---

## 🏢 Step 7: OpEx Schedule Building

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._build_opex_schedule(drivers, base_value)`  
**Line:** 438-447  
*(Called from `calculate()` at lines 1001-1002)*

```python
def _build_opex_schedule(self, drivers: ScenarioDrivers, base_value: float) -> List[float]:
    """Build OpEx (SG&A or Other) using inflation rate."""
    opex = [base_value]
    
    for i in range(6):
        inflation = drivers.inflation_rate[i]
        new_opex = opex[-1] * (1 + inflation)
        opex.append(new_opex)
    
    return opex[1:]
```

---

## 📉 Step 8: Depreciation Schedule Building

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._build_depreciation_schedule(drivers)`  
**Line:** 449-580  
*(Called from `calculate()` at line 1008)*

**Key Components:**
- Existing asset depreciation (straight-line)
- New asset depreciation (half-year convention)
- Tax depreciation (declining balance)
- PPE gross book roll-forward
- Tax basis roll-forward

```python
def _build_depreciation_schedule(self, drivers: ScenarioDrivers) -> DepreciationSchedule:
    # Initialize arrays for 6 periods
    periods = ["FY1", "FY2", "FY3", "FY4", "FY5", "Terminal"]
    
    # Existing asset depreciation calculation
    opening_ppe = self.inputs.ppe_gross_book
    useful_life_existing = self.inputs.useful_life_existing
    annual_existing_dep = opening_ppe / useful_life_existing
    
    # Loop through periods calculating:
    # - CapEx from drivers
    # - Existing asset depreciation
    # - New asset depreciation from cohorts
    # - Total depreciation (book and tax)
    # - Gross PPE roll-forward
    # - Tax basis roll-forward
    
    return DepreciationSchedule(
        years=periods,
        capex=capex_arr,
        existing_asset_depreciation=existing_dep,
        new_asset_depreciation=new_asset_dep,
        total_depreciation=total_dep,
        gross_ppe_ending=gross_ppe,
        tax_basis_ending=tax_dep,
        tax_depreciation=tax_depreciation
    )
```

---

## 💼 Step 9: Working Capital Schedule Building

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._build_working_capital_schedule(drivers, revenue, cogs)`  
**Line:** 582-680  
*(Called from `calculate()` at line 1022)*

**Key Metrics Calculated:**
- Accounts Receivable (AR Days)
- Inventory (Inventory Days)
- Accounts Payable (AP Days)
- Net Working Capital
- Change in NWC

```python
def _build_working_capital_schedule(self, drivers, revenue, cogs):
    # Calculate AR, Inventory, AP from days ratios
    # Calculate Net Working Capital = AR + Inventory - AP
    # Calculate Change in NWC (cash outflow if positive)
    
    return WorkingCapitalSchedule(...)
```

---

## 🧾 Step 10: Tax Schedule Building (Levered & Unlevered)

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Methods:**
- `DCFEngine._build_tax_schedule_levered()` (Line 682-780)
- `DCFEngine._build_tax_schedule_unlevered()` (Line 782-880)

*(Called from `calculate()` at lines 1025-1026)*

**Key Features:**
- Separate levered (for Net Income) and unlevered (for UFCF) tax calculations
- Tax loss carryforward tracking
- Tax loss utilization limit
- Deferred tax from book vs tax depreciation differences

---

## 💵 Step 11: UFCF Calculation

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._calculate_ufcf(...)`  
**Line:** 882-930  
*(Called from `calculate()` at line 1032)*

```python
def _calculate_ufcf(self, ebitda, tax_unlevered, capex, change_in_nwc, tax_levered, depreciation):
    """
    Calculate Unlevered Free Cash Flow.
    Formula: UFCF = EBITDA - Cash Taxes - CapEx - ΔNWC + Tax Shield
    where Tax Shield = Tax Rate × Interest Expense
    """
    ufcf = []
    tax_shield = [self.inputs.statutory_tax_rate * interest for interest in tax_levered.interest_expense]
    
    for i in range(6):
        cash_flow = (ebitda[i] 
                    - tax_unlevered.total_tax[i] 
                    - capex[i] 
                    - change_in_nwc[i] 
                    + tax_shield[i])
        ufcf.append(cash_flow)
    
    return UFCFSchedule(years=[...], ufcf=ufcf, ...)
```

---

## 📅 Step 12: Partial Period Adjustment

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._calculate_partial_period_factor(...)`  
**Line:** 932-966  
*(Called from `calculate()` at line 1042)*

**Purpose:** Adjust discounting for partial first year based on valuation date vs fiscal year end.

---

## 🎯 Step 13: Full DCF Calculation (Orchestration)

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine.calculate(scenario="base_case")`  
**Line:** 968-1140

**Complete Execution Flow:**

```python
def calculate(self, scenario: str = "base_case") -> DCFOutput:
    # Line 972-975: Get drivers for scenario
    drivers = self.inputs.forecast_drivers[scenario]
    
    # Line 980: CALL → calculate_wacc()
    wacc, avg_unlev_beta, lev_beta, cost_of_equity = self.calculate_wacc()
    
    # Line 984-989: Validate terminal growth < WACC
    
    # Line 992: CALL → _build_revenue_schedule(drivers)
    revenue = self._build_revenue_schedule(drivers)
    
    # Line 995: CALL → _build_cogs_schedule(drivers)
    cogs = self._build_cogs_schedule(drivers)
    
    # Line 998: Calculate Gross Profit
    gross_profit = [r - c for r, c in zip(revenue, cogs)]
    
    # Line 1001-1002: CALL → _build_opex_schedule() for SG&A and Other OpEx
    sga = self._build_opex_schedule(drivers, self.inputs.historical_sga[-1])
    other_opex = self._build_opex_schedule(drivers, self.inputs.historical_other_opex[-1])
    
    # Line 1005: Calculate EBITDA
    ebitda = [gp - s - o for gp, s, o in zip(gross_profit, sga, other_opex)]
    
    # Line 1008: CALL → _build_depreciation_schedule(drivers)
    depr_schedule = self._build_depreciation_schedule(drivers)
    depreciation = depr_schedule.total_depreciation
    
    # Line 1013: Calculate EBIT
    ebit = [e - d for e, d in zip(ebitda, depreciation)]
    
    # Line 1016: Interest Expense (constant from inputs)
    interest = [self.inputs.projected_interest_expense] * 6
    
    # Line 1019: Calculate EBT
    ebt = [e - i for e, i in zip(ebit, interest)]
    
    # Line 1022: CALL → _build_working_capital_schedule()
    wc_schedule = self._build_working_capital_schedule(drivers, revenue, cogs)
    
    # Line 1025-1026: CALL → _build_tax_schedule_levered() and _build_tax_schedule_unlevered()
    tax_levered = self._build_tax_schedule_levered(...)
    tax_unlevered = self._build_tax_schedule_unlevered(...)
    
    # Line 1029: Calculate Net Income
    net_income = [e - t for e, t in zip(ebt, tax_levered.total_tax)]
    
    # Line 1032: CALL → _calculate_ufcf()
    ufcf_schedule = self._calculate_ufcf(...)
    
    # Line 1042: CALL → _calculate_partial_period_factor()
    partial_factor, yearfractions = self._calculate_partial_period_factor(...)
    
    # Line 1053-1054: Perpetuity Method Terminal Value
    terminal_ufcf = ufcf_schedule.ufcf[-1]
    tv_perpetuity = terminal_ufcf * (1 + drivers.terminal_growth_rate) / (wacc - drivers.terminal_growth_rate)
    
    # Line 1057-1063: CALL → _discount_cash_flows() for Perpetuity Method
    perpetuity_dcf = self._discount_cash_flows(ufcf_schedule.ufcf, tv_perpetuity, wacc, ...)
    
    # Line 1068-1069: Exit Multiple Method Terminal Value
    terminal_ebitda = ebitda[-1]
    tv_multiple = terminal_ebitda * drivers.terminal_ebitda_multiple
    
    # Line 1072-1078: CALL → _discount_cash_flows() for Multiple Method
    multiple_dcf = self._discount_cash_flows(ufcf_schedule.ufcf, tv_multiple, wacc, ...)
    
    # Line 1081-1091: Calculate Enterprise Values, Equity Values, Share Prices
    ev_perpetuity = perpetuity_dcf.enterprise_value
    ev_multiple = multiple_dcf.enterprise_value
    equity_perpetuity = ev_perpetuity - self.inputs.net_debt_opening
    equity_multiple = ev_multiple - self.inputs.net_debt_opening
    eq_per_share_perp = equity_perpetuity / self.inputs.shares_outstanding
    eq_per_share_mult = equity_multiple / self.inputs.shares_outstanding
    premium_perp = (eq_per_share_perp - self.inputs.current_stock_price) / self.inputs.current_stock_price
    premium_mult = (eq_per_share_mult - self.inputs.current_stock_price) / self.inputs.current_stock_price
    
    # Line 1094-1140: Build complete Income Statement and return DCFOutput
    income_stmt = IncomeStatement(...)
    
    return DCFOutput(
        scenario=scenario,
        wacc=wacc,
        # ... all schedules and outputs
    )
```

---

## 🔢 Step 14: Discount Cash Flows

### File: `/workspace/backend/app/engines/dcf_engine.py`

**Method:** `DCFEngine._discount_cash_flows(...)`  
**Line:** 820-860 (approximate)

```python
def _discount_cash_flows(self, ufcf, terminal_value, wacc, yearfractions, partial_factor):
    """
    Discount UFCF and Terminal Value to present value.
    Formula: PV = Σ [UFCF[t] / (1+WACC)^(yearfraction[t])] + TV / (1+WACC)^final_year
    """
    pv_ufcf = []
    cumulative_pv = 0
    
    for i in range(len(ufcf)):
        discount_factor = (1 + wacc) ** (yearfractions[i] * partial_factor if i == 0 else yearfractions[i])
        pv = ufcf[i] / discount_factor
        pv_ufcf.append(pv)
        cumulative_pv += pv
    
    # Discount terminal value
    tv_discount_factor = (1 + wacc) ** yearfractions[-1]
    pv_terminal = terminal_value / tv_discount_factor
    
    enterprise_value = cumulative_pv + pv_terminal
    
    return DCFResult(
        pv_ufcf=pv_ufcf,
        pv_terminal=pv_terminal,
        enterprise_value=enterprise_value
    )
```

---

## 📁 Complete File Call Chain Summary

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. API ROUTE LAYER                                              │
│    File: /backend/app/api/routes/valuation_routes.py            │
│    • POST /step-10-valuate (line 1118)                          │
│      └─→ run_valuation()                                        │
│          └─→ run_valuation_engine() (line 279)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. DATA FETCHING LAYER                                          │
│    File: /backend/app/engines/dcf_engine.py                     │
│    • fetch_dcf_inputs() (line 1444)                             │
│      ├─→ yfinance.Ticker() (line 1459)                          │
│      └─→ suggest_peer_companies() [optional]                    │
│          └─→ /backend/app/engines/ai_engine.py                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ENGINE INITIALIZATION                                        │
│    File: /backend/app/engines/dcf_engine.py                     │
│    • DCFEngine.__init__() (line 359)                            │
│    • DCFInputs dataclass populated                              │
│    • ScenarioDrivers dataclass populated                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. WACC CALCULATION                                             │
│    File: /backend/app/engines/dcf_engine.py                     │
│    • DCFEngine.calculate_wacc() (line 369)                      │
│      ├─→ ComparableCompany.unlevered_beta property (line 92)    │
│      └─→ CAPM formula application                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. FULL DCF CALCULATION ORCHESTRATION                           │
│    File: /backend/app/engines/dcf_engine.py                     │
│    • DCFEngine.calculate() (line 968)                           │
│      ├─→ _build_revenue_schedule() (line 406)                   │
│      ├─→ _build_cogs_schedule() (line 424)                      │
│      ├─→ _build_opex_schedule() (line 438) [×2]                 │
│      ├─→ _build_depreciation_schedule() (line 449)              │
│      ├─→ _build_working_capital_schedule() (line 582)           │
│      ├─→ _build_tax_schedule_levered() (line 682)               │
│      ├─→ _build_tax_schedule_unlevered() (line 782)             │
│      ├─→ _calculate_ufcf() (line 882)                           │
│      ├─→ _calculate_partial_period_factor() (line 932)          │
│      ├─→ _discount_cash_flows() (line ~820) [×2 methods]        │
│      └─→ DCFOutput construction                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. RESULT RETURN                                                │
│    File: /backend/app/api/routes/valuation_routes.py            │
│    • Results formatted and returned to API client               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Supporting Files

| File | Purpose |
|------|---------|
| `/backend/app/engines/dcf_engine.py` | Core DCF calculation engine with all schedules |
| `/backend/app/engines/ai_engine.py` | AI-powered peer company suggestions |
| `/backend/app/api/routes/valuation_routes.py` | API endpoints and session management |
| `/backend/app/api/schemas.py` | Pydantic models for request/response validation |
| `/backend/app/main.py` | Session store management |
| `/backend/app/core/exceptions.py` | Custom exception classes |
| `/backend/app/core/logging_config.py` | Logging configuration |

---

## 📊 Key Data Classes Used

From `/backend/app/engines/dcf_engine.py`:

- `InputWithMetadata` (line 42) - Tracks input source (API/AI/MANUAL)
- `ComparableCompany` (line 75) - Peer company data for WACC
- `ScenarioDrivers` (line 98) - Forecast assumptions per scenario
- `DCFInputs` (line ~200) - All inputs for DCF calculation
- `DepreciationSchedule` - Output from `_build_depreciation_schedule()`
- `WorkingCapitalSchedule` - Output from `_build_working_capital_schedule()`
- `TaxSchedule` - Output from tax schedule builders
- `UFCFSchedule` - Output from `_calculate_ufcf()`
- `DCFOutput` - Final calculation result
- `IncomeStatement` - Complete projected income statement

---

## 🎯 Market-Specific Notes

**International Market:**
- Currency: USD (or local currency from yfinance)
- Risk-free rate: Typically US Treasury yield (~4.5%)
- Equity Risk Premium: ~5.5%
- Country Risk Premium: 0% for developed markets

**Vietnamese Market** (handled separately):
- Currency: VND
- Higher risk-free rate (Vietnam government bonds)
- Additional Country Risk Premium applied
- Specialized engines for Banking, Real Estate, Manufacturing sectors

---

*Document generated from code analysis of backend repository.*
