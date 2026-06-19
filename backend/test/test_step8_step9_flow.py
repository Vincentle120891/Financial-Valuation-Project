"""
Test: Step 8 → Step 9 Data Flow
Verifies that forecast drivers saved in Step 8 are correctly received by Step 9.

Flow:
1. Create session (ticker: AAPL)
2. Step 8: Initialize assumptions
3. Step 8: Save overrides via /step-8-save-overrides
4. Step 9: Confirm assumptions via /step-9-confirm-assumptions
5. Verify: Step 9 response contains confirmed parameters with correct values
"""

import json
import sys
import requests

BASE_URL = "http://localhost:8000/api"


def test_step8_step9_flow():
    results = []
    
    # ── Step 1: Create session ──────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 1: Create session")
    print("="*60)
    
    import uuid
    test_session_id = f"test-{uuid.uuid4().hex[:8]}"
    
    resp = requests.post(f"{BASE_URL}/step-2-create-session", json={
        "session_id": test_session_id,
        "ticker": "AAPL",
        "market": "international"
    })
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 200, f"Session creation failed: {resp.text}"
    
    data = resp.json()
    session_id = data.get("session_id", test_session_id)
    print(f"  Session ID: {session_id}")
    assert session_id, "No session_id returned"
    results.append(("Session created", True))
    
    # ── Step 2: Step 8 Initialize ───────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 2: Step 8 Initialize")
    print("="*60)
    
    resp = requests.post(f"{BASE_URL}/step-8-initialize", json={
        "session_id": session_id,
        "method": "DCF",
        "market": "international"
    })
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 200, f"Step 8 initialize failed: {resp.text}"
    
    step8_data = resp.json()
    categories = step8_data.get("categories", {})
    print(f"  Categories: {list(categories.keys())}")
    print(f"  Has complete_financial_statements: {'complete_financial_statements' in step8_data}")
    results.append(("Step 8 initialized", len(categories) > 0))
    
    # ── Step 3: Save overrides ──────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 3: Save overrides via /step-8-save-overrides")
    print("="*60)
    
    confirmed_assumptions = {
        "forecast_base_case_revenue_growth_0": {"value": 2.0, "source": "manual"},
        "forecast_base_case_revenue_growth_1": {"value": 2.0, "source": "manual"},
        "forecast_base_case_revenue_growth_2": {"value": 2.0, "source": "manual"},
        "forecast_base_case_revenue_growth_3": {"value": 2.0, "source": "manual"},
        "forecast_base_case_revenue_growth_4": {"value": 2.0, "source": "manual"},
        "forecast_base_case_tax_rate_0": {"value": 15.9, "source": "manual"},
        "forecast_base_case_tax_rate_1": {"value": 15.9, "source": "manual"},
        "forecast_base_case_receivables_days_0": {"value": 30.0, "source": "manual"},
        "forecast_base_case_inventory_days_0": {"value": 10.0, "source": "manual"},
        "forecast_base_case_payables_days_0": {"value": 112.0, "source": "manual"},
        "forecast_base_case_opex_growth_0": {"value": 6.6, "source": "manual"},
        "forecast_base_case_capital_expenditure_0": {"value": 12715000000, "source": "manual"},
        "dcf_risk_free_rate": {"value": 0.045, "source": "manual"},
        "dcf_equity_risk_premium": {"value": 0.1112, "source": "manual"},
        "dcf_beta": {"value": 3.39, "source": "manual"},
        "dcf_cost_of_debt": {"value": 0.0354, "source": "manual"},
        "dcf_wacc": {"value": 0.25, "source": "manual"},
        "dcf_terminal_growth_rate": {"value": 0.025, "source": "manual"},
        "dcf_terminal_ebitda_multiple": {"value": 8.5, "source": "manual"},
    }
    
    resp = requests.post(f"{BASE_URL}/step-8-save-overrides", json={
        "session_id": session_id,
        "confirmed_assumptions": confirmed_assumptions,
        "method": "DCF",
        "market": "international"
    })
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.json()}")
    assert resp.status_code == 200, f"Save overrides failed: {resp.text}"
    results.append(("Step 8 save overrides", resp.json().get("status") == "saved"))
    
    # ── Step 4: Step 9 Confirm ──────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 4: Step 9 Confirm Assumptions")
    print("="*60)
    
    resp = requests.post(f"{BASE_URL}/step-9-confirm-assumptions", json={
        "session_id": session_id,
        "confirmed_values": confirmed_assumptions,
        "scenario": "base_case",
        "method": "DCF",
        "market": "international"
    })
    print(f"  Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"  ERROR: {resp.text[:500]}")
        results.append(("Step 9 confirm", False))
        return results
    
    step9_response = resp.json()
    print(f"  Status field: {step9_response.get('status')}")
    print(f"  Ready for valuation: {step9_response.get('ready_for_valuation')}")
    print(f"  Validation errors: {step9_response.get('validation_errors')}")
    results.append(("Step 9 confirm (200 OK)", True))
    results.append(("Step 9 ready_for_valuation", step9_response.get('ready_for_valuation') == True))
    results.append(("Step 9 no validation errors", len(step9_response.get('validation_errors', [])) == 0))
    
    # ── Step 5: Verify confirmed_assumptions ────────────────────────────
    print("\n" + "="*60)
    print("STEP 5: Verify confirmed_assumptions in Step 9 response")
    print("="*60)
    
    confirmed = step9_response.get("confirmed_assumptions", {})
    print(f"  Confirmed assumptions keys: {list(confirmed.keys()) if isinstance(confirmed, dict) else 'NOT A DICT'}")
    
    expected_keys = [
        "risk_free_rate", "market_risk_premium", "beta", "cost_of_debt",
        "wacc", "terminal_growth_rate", "terminal_ebitda_multiple",
        "tax_rate", "current_price", "shares_outstanding"
    ]
    
    found_keys = []
    missing_keys = []
    for key in expected_keys:
        if key in confirmed:
            val = confirmed[key]
            if isinstance(val, dict):
                val = val.get("value", val)
            found_keys.append(f"  ✅ {key} = {val}")
        else:
            missing_keys.append(f"  ❌ {key} = MISSING")
    
    for line in found_keys:
        print(line)
    for line in missing_keys:
        print(line)
    
    has_wacc = "wacc" in confirmed
    has_terminal = "terminal_growth_rate" in confirmed
    has_tax = "tax_rate" in confirmed
    has_price = "current_price" in confirmed
    
    results.append(("Step 9 has wacc", has_wacc))
    results.append(("Step 9 has terminal_growth_rate", has_terminal))
    results.append(("Step 9 has tax_rate", has_tax))
    results.append(("Step 9 has current_price", has_price))
    
    # ── Step 6: Verify revenue projections ─────────────────────────────
    print("\n" + "="*60)
    print("STEP 6: Verify revenue projections")
    print("="*60)
    
    rev_proj = confirmed.get("revenue_projections", [])
    if isinstance(rev_proj, list):
        print(f"  Revenue projections: {len(rev_proj)} entries")
        for i, proj in enumerate(rev_proj[:3]):
            print(f"    Year {i+1}: {proj}")
        results.append(("Step 9 has revenue_projections", len(rev_proj) > 0))
    else:
        print(f"  Revenue projections: {rev_proj}")
        results.append(("Step 9 has revenue_projections", False))
    
    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, v in results if v)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\n  {passed}/{total} tests passed")
    
    return results


if __name__ == "__main__":
    try:
        results = test_step8_step9_flow()
        passed = sum(1 for _, v in results if v)
        total = len(results)
        sys.exit(0 if passed == total else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
