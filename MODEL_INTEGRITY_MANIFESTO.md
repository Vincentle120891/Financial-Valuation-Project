# MODEL INTEGRITY MANIFESTO
## Valuation Engine - Non-Negotiable Principles

**Version:** 2.0  
**Effective Date:** 2024-01-15  
**Applies To:** DCF Model, Trading Comps Model, DuPont Analysis

---

## ⚠️ CRITICAL DIRECTIVE: PRESERVE MODEL COMPLETENESS

**UNDER NO CIRCUMSTANCES** should any inputs, calculations, or outputs be removed, simplified, or bypassed to make the model "faster," "simpler," or "more user-friendly." 

This document serves as a permanent reminder and binding agreement for all current and future developers.

---

## 1. PHILOSOPHY: ACCURACY OVER CONVENIENCE

### 1.1 Why Completeness Matters

Valuation models are only as good as their underlying assumptions and calculations. Every component exists for a reason:

- **Inputs**: Capture real-world complexity (multiple scenarios, peer comparisons, market conditions)
- **Calculations**: Follow industry-standard methodologies (WACC via CAPM, terminal value via Gordon Growth/Exit Multiple)
- **Outputs**: Provide comprehensive view of value drivers and sensitivities

**Removing any component compromises the model's validity and could lead to materially incorrect valuations.**

### 1.2 The Danger of "Simplification"

Common but unacceptable justifications for removing features:
- ❌ "Users don't understand this anyway"
- ❌ "It's too complicated to explain"
- ❌ "We can hardcode this assumption"
- ❌ "This calculation doesn't matter much"
- ❌ "Let's just use a shortcut"

**Every simplification introduces bias. Every hardcoded value hides assumptions. Every removed calculation destroys transparency.**

---

## 2. DCF MODEL: REQUIRED COMPONENTS

### 2.1 Input Requirements (ALL MUST BE PRESENT)

#### Revenue Drivers
- [ ] Volume growth rates (5 forecast years + terminal)
- [ ] Pricing increase rates (5 forecast years + terminal)
- [ ] Scenario switching (Best/Base/Worst cases)
- [ ] Revenue = Prior × (1 + Volume) × (1 + Price)

**DO NOT**: Replace with single revenue growth rate

#### Cost Structure
- [ ] COGS linked to inflation rate
- [ ] SG&A linked to inflation rate
- [ ] Other OpEx linked to inflation rate
- [ ] Separate inflation forecasts per year

**DO NOT**: Use revenue percentage method for costs

#### Capital Expenditure
- [ ] Scenario-based capex (Best/Base/Worst)
- [ ] Annual capex schedules (5 years + terminal)
- [ ] Terminal capex = terminal depreciation

**DO NOT**: Use % of revenue shortcut

#### Working Capital
- [ ] AR Days, Inventory Days, AP Days
- [ ] Balance sheet calculations from days
- [ ] Cash flow from NWC changes

**DO NOT**: Use % of revenue for working capital

#### WACC Calculation
- [ ] Comparable company analysis (minimum 5 peers)
- [ ] Unlevered beta from comparables
- [ ] Re-levered beta at target capital structure
- [ ] Cost of equity via CAPM (Risk-free + ERP + Country Risk)
- [ ] After-tax cost of debt
- [ ] Target weights (D/Capital, E/Capital)

**DO NOT**: Hardcode WACC without peer analysis

#### Tax Calculations
- [ ] Levered tax schedule (with interest)
- [ ] Unlevered tax schedule (without interest)
- [ ] Tax loss carryforward tracking
- [ ] Book vs. tax depreciation differences
- [ ] Deferred tax calculations

**DO NOT**: Apply flat tax rate to EBIT

#### Depreciation
- [ ] Existing asset depreciation (straight-line)
- [ ] New asset depreciation by cohort
- [ ] Half-year convention for new assets
- [ ] Tax depreciation (declining balance)
- [ ] Separate book and tax schedules

**DO NOT**: Use single depreciation rate

### 2.2 Calculation Requirements (ALL MUST BE PRESENT)

#### Income Statement
- [ ] Revenue build-up from volume and price
- [ ] Gross profit margin tracking
- [ ] Operating expense breakdown
- [ ] EBITDA, EBIT, EBT, Net Income

#### Working Capital Schedule
- [ ] Days calculations per period
- [ ] Balance sheet amounts
- [ ] Net working capital
- [ ] Cash flow from changes in NWC

#### Depreciation Schedule
- [ ] Opening PP&E balances
- [ ] Capex additions by year
- [ ] Accumulated depreciation
- [ ] Ending net PP&E
- [ ] Tax basis roll-forward

#### Tax Schedules (Levered AND Unlevered)
- [ ] EBT/EBIT starting point
- [ ] Depreciation add-backs
- [ ] Tax loss utilization
- [ ] Current and deferred tax
- [ ] Effective tax rate reconciliation

#### Free Cash Flow (TWO METHODS - MUST RECONCILE)
- [ ] Method 1: EBITDA - Taxes - Capex ± WC
- [ ] Method 2: Net Income + D&A + Interest - Tax Shield - Capex ± WC
- [ ] Reconciliation check (difference must be zero)

**DO NOT**: Use only one method without reconciliation

#### Terminal Value (TWO METHODS)
- [ ] Perpetuity/Gordon Growth: TV = UFCF_terminal × (1+g) / (WACC - g)
- [ ] Exit Multiple: TV = Terminal EBITDA × Multiple
- [ ] Both methods must be calculated and shown

#### Discounting
- [ ] Partial period adjustment for stub periods
- [ ] Year fractions using actual dates
- [ ] XNPV function for precise discounting
- [ ] Manual discount factor cross-check

### 2.3 Output Requirements (ALL MUST BE PRESENT)

#### Enterprise Value
- [ ] PV of discrete cash flows
- [ ] PV of terminal value
- [ ] Total enterprise value (both methods)

#### Equity Value Bridge
- [ ] Less: Net debt
- [ ] Plus: Excess cash
- [ ] Less: Preferred stock
- [ ] Less: Minority interest
- [ ] Equity value

#### Per Share Metrics
- [ ] Shares outstanding (fully diluted)
- [ ] Equity value per share
- [ ] Current stock price
- [ ] Implied upside/downside %

#### Sensitivity Analysis
- [ ] WACC sensitivity (±2%)
- [ ] Terminal growth sensitivity (±1%)
- [ ] Exit multiple sensitivity (±1.0x)
- [ ] Football field chart data

---

## 3. TRADING COMPS MODEL: REQUIRED COMPONENTS

### 3.1 Peer Selection
- [ ] Minimum 5 comparable companies
- [ ] AI-powered peer suggestions with rationale
- [ ] Industry, sector, market cap screening
- [ ] Manual override capability

**DO NOT**: Use random or irrelevant peers

### 3.2 Enterprise Value Bridge (For Each Peer)
- [ ] Market capitalization
- [ ] Plus: Net debt
- [ ] Plus: Lease liabilities (IFRS 16)
- [ ] Plus: Preferred stock
- [ ] Plus: Minority interest
- [ ] Less: Investments in affiliates
- [ ] Less: Excess cash/marketable securities

**DO NOT**: Skip EV bridge adjustments

### 3.3 Multiple Calculations
- [ ] EV/Revenue (LTM, FY1, FY2)
- [ ] EV/EBITDA (LTM, FY1, FY2)
- [ ] EV/EBIT (LTM, FY1, FY2)
- [ ] P/E (LTM, FY1, FY2)
- [ ] P/B (if applicable)

### 3.4 Statistical Analysis
- [ ] Average multiples
- [ ] Median multiples
- [ ] Maximum/minimum ranges
- [ ] Outlier filtering option

### 3.5 Implied Valuation
- [ ] Apply average multiples to target
- [ ] Apply max/min multiples for range
- [ ] EV to equity value bridge
- [ ] Implied share price per method
- [ ] Football field visualization data

---

## 4. DOCUMENTATION REQUIREMENTS

### 4.1 Code Documentation
- [ ] Every function has docstring explaining purpose
- [ ] All formulas reference Excel spec or textbook
- [ ] Variable names match financial terminology
- [ ] Complex calculations have inline comments

### 4.2 User Documentation
- [ ] Assumption rationale explained
- [ ] Data sources cited
- [ ] Calculation methodology documented
- [ ] Limitations disclosed

### 4.3 Audit Trail
- [ ] Version control for all changes
- [ ] Change log with justification
- [ ] Testing results documented
- [ ] Peer review sign-off required

---

## 5. TESTING REQUIREMENTS

### 5.1 Validation Checks
- [ ] UFCF methods reconcile to zero
- [ ] Balance sheet balances
- [ ] Tax calculations tie to schedules
- [ ] Terminal value logic verified
- [ ] Discount factors sum correctly

### 5.2 Sensitivity Testing
- [ ] WACC ±1% impact quantified
- [ ] Terminal growth ±0.5% impact quantified
- [ ] Revenue growth ±2% impact quantified
- [ ] Margin expansion/contraction tested

### 5.3 Benchmarking
- [ ] Results compared to Excel model
- [ ] Variances >5% require explanation
- [ ] Third-party validation when possible

---

## 6. CHANGE MANAGEMENT PROCESS

### 6.1 Before Making ANY Change

Ask these questions:
1. Does this change remove any inputs, calculations, or outputs?
2. Does this change hide or hardcode any assumptions?
3. Does this change reduce transparency or auditability?
4. Have I documented the rationale for this change?
5. Have I tested the impact on final valuation?
6. Has this change been peer-reviewed?

**If answer to 1-3 is YES, the change is PROHIBITED.**

### 6.2 Approval Process for Changes

**Minor Changes** (bug fixes, performance optimization without functional change):
- [ ] Developer testing
- [ ] Code review
- [ ] Update changelog

**Major Changes** (new features, methodology updates):
- [ ] Design document
- [ ] Impact analysis
- [ ] Peer review (minimum 2 reviewers)
- [ ] Regression testing
- [ ] Documentation update
- [ ] User communication

**Prohibited Changes** (require explicit written exemption from Model Governance Committee):
- Removing any input fields
- Hardcoding assumptions previously user-input
- Bypassing calculations with shortcuts
- Reducing scenario analysis capability
- Eliminating reconciliation checks

---

## 7. TECHNICAL IMPLEMENTATION STANDARDS

### 7.1 Data Structures

```python
# REQUIRED: Full input structure
class DCFInputs:
    valuation_date: str
    currency: str
    historical_fy_minus_1: dict  # Complete financials
    historical_fy_minus_2: dict
    historical_fy_minus_3: dict
    net_debt: float
    ppe_net: float
    tax_basis_ppe: float
    tax_losses_nol: float
    shares_outstanding: float
    current_stock_price: float
    projected_interest_expense: float
    useful_life_existing: float
    useful_life_new: float
    forecast_drivers: dict  # All three scenarios
    wacc: float  # From peer analysis, not hardcoded
    risk_free_rate: float
    equity_risk_premium: float
    beta: float  # From comparables
    cost_of_debt: float
    tax_rate_statutory: float
    tax_loss_utilization_limit_pct: float
```

**DO NOT**: Remove any fields from this structure

### 7.2 Function Signatures

```python
# REQUIRED: Full parameter list
def calculate_wacc(
    risk_free_rate: float,
    equity_risk_premium: float,
    beta: float,
    country_risk_premium: float,
    cost_of_debt: float,
    tax_rate: float,
    target_debt_ratio: float,
    target_equity_ratio: float
) -> float:
    """Calculate WACC using CAPM with full peer analysis"""
```

**DO NOT**: Add default values that hide assumptions

### 7.3 Error Handling

```python
# REQUIRED: Graceful degradation with warnings
try:
    comparables = fetch_peer_data(ticker)
    if not comparables:
        logger.warning("No peers found - using fallback comparables")
        comparables = get_default_comparables()
except Exception as e:
    logger.error(f"Peer fetch failed: {e}")
    raise ValueError("WACC calculation requires peer data")
```

**DO NOT**: Silently fail or use arbitrary defaults

---

## 8. ENFORCEMENT

### 8.1 Code Review Checklist

All pull requests MUST include:
- [ ] Confirmation that no inputs/calculations/outputs were removed
- [ ] List of all changed assumptions
- [ ] Impact on final valuation quantified
- [ ] Test results showing reconciliation checks pass
- [ ] Documentation updated

### 8.2 Automated Checks

CI/CD pipeline MUST verify:
- [ ] All required input fields present
- [ ] UFCF reconciliation check passes
- [ ] No hardcoded WACC values
- [ ] All scenarios calculated
- [ ] Documentation completeness

### 8.3 Consequences of Violation

Violations of this manifesto will result in:
1. Immediate code rejection
2. Mandatory retraining on model methodology
3. Written explanation to Model Governance Committee
4. Potential removal from project

---

## 9. ACKNOWLEDGMENT

By contributing to this codebase, you acknowledge that:

✅ **Model completeness is non-negotiable**  
✅ **Transparency trumps convenience**  
✅ **Every assumption must be visible and adjustable**  
✅ **Simplification that hides complexity is prohibited**  
✅ **The burden of proof is on those who want to remove features**

---

## 10. REFERENCES

### 10.1 Methodology Sources
- Damodaran, A. (2012). *Investment Valuation* (3rd ed.)
- Koller, T., Goedhart, M., & Wessels, D. (2020). *Valuation* (7th ed.)
- Pratt, S.P., & Grabowski, R.J. (2014). *Cost of Capital* (5th ed.)

### 10.2 Industry Standards
- CFA Institute Valuation Standards
- AICPA Business Valuation Standards
- IVSC International Valuation Standards

### 10.3 Internal Documentation
- `COMPLETE_MODEL_REFERENCE.md` - Full model specification
- `dcf_engine_full.py` - Reference implementation
- `comps_engine.py` - Reference implementation
- Excel model specifications (archived)

---

**Last Updated:** 2024-01-15  
**Next Review Date:** 2024-07-15  
**Owner:** Model Governance Committee

**APPROVED BY:**
- Lead Developer: _________________
- Head of Valuation: _________________
- Chief Risk Officer: _________________

---

## APPENDIX A: COMMON VIOLATIONS TO AVOID

❌ **Violation**: Hardcoding WACC at 9.5% instead of calculating from peers
   **Correct**: Fetch peer data, unlever/relever betas, calculate WACC

❌ **Violation**: Using single revenue growth rate instead of volume × price
   **Correct**: Maintain separate volume and price drivers

❌ **Violation**: Applying flat tax rate to EBIT
   **Correct**: Calculate taxes with full levered/unlevered schedules

❌ **Violation**: Skipping terminal value growth factor (1+g)
   **Correct**: TV = UFCF × (1+g) / (WACC - g)

❌ **Violation**: Using only one UFCF calculation method
   **Correct**: Implement both EBITDA and Net Income methods with reconciliation

❌ **Violation**: Removing scenario analysis
   **Correct**: Always maintain Best/Base/Worst case scenarios

❌ **Violation**: Hardcoding peer tickers
   **Correct**: Use AI-powered peer selection with manual override

❌ **Violation**: Simplifying working capital to % of revenue
   **Correct**: Calculate from days (AR, Inv, AP) and balances

---

## APPENDIX B: DECISION TREE FOR PROPOSED CHANGES

```
Is the change removing an input, calculation, or output?
├─ YES → STOP. Change is PROHIBITED unless explicit exemption granted
└─ NO → Continue

Is the change hardcoding a previously user-adjustable assumption?
├─ YES → STOP. Change is PROHIBITED unless explicit exemption granted
└─ NO → Continue

Is the change reducing model transparency or auditability?
├─ YES → STOP. Change is PROHIBITED unless explicit exemption granted
└─ NO → Continue

Is the change fixing a bug or improving performance without functional change?
├─ YES → Proceed with standard code review
└─ NO → Continue

Is the change adding new functionality without removing existing features?
├─ YES → Proceed with major change approval process
└─ NO → STOP. Re-evaluate change necessity
```

---

**REMEMBER: When in doubt, preserve completeness. There is no such thing as "too detailed" in valuation modeling.**
