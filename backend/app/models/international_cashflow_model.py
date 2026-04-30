"""
================================================================================
INTERNATIONAL FINANCIAL REPORTING TEMPLATES — IFRS / US GAAP
Cash Flow Statement Model (IAS 7 / ASC 230)
Structured Documentation for AI Consumption
================================================================================

Two permitted methods for operating cash flows:
  - Direct Method (preferred by IASB, less common in practice)
  - Indirect Method (most commonly used, reconciles from net income)

Column structure (standard presentation):
  Line Item = Description
  Code = Reference code (flexible, not mandated like Vietnamese Mã số)
  Current Period = Current year/period figures
  Prior Period = Prior year/period figures
  Notes = Reference to financial statement notes

Outflow presentation: 
  - Parentheses (...) or negative sign for cash outflows
  - Consistent sign convention throughout statement

Master balancing formula:
  Net Change in Cash = CFO + CFI + CFF
  Ending Cash = Beginning Cash + Net Change in Cash + FX Effect

================================================================================
SECTION STRUCTURE (IFRS / US GAAP)
================================================================================

────────────────────────────────────────────────────────────────────────────────
I. CASH FLOWS FROM OPERATING ACTIVITIES (CFO)
────────────────────────────────────────────────────────────────────────────────

A. DIRECT METHOD (IAS 7 §18-19)
────────────────────────────────────────────────────────────────────────────────

  Cash Receipts:
    1. Cash received from customers
       → Revenue ± Change in Trade Receivables ± Change in Deferred Revenue
    
    2. Cash received from royalties, fees, commissions, and other revenue
       → Other operating income adjusted for related balance sheet changes
    
    3. Cash received from operating lease rentals (lessor)
    
    4. Other operating cash receipts
       → VAT refunds, insurance recoveries, lawsuit settlements, etc.

  Cash Payments:
    5. Cash paid to suppliers for goods and services
       → COGS + Operating Expenses ± Inventory Changes ± Payables Changes
    
    6. Cash paid to and on behalf of employees
       → Salaries, wages, bonuses, benefits, payroll taxes
    
    7. Cash paid for operating expenses
       → Selling, general & administrative expenses (excluding depreciation)
    
    8. Interest paid
       → Under IFRS: Can be classified as Operating OR Financing
       → Under US GAAP: MUST be classified as Operating
    
    9. Income taxes paid
       → Current tax expense ± Change in Tax Payable ± Change in Deferred Tax
    
    10. Other operating cash payments
        → Penalties, donations, miscellaneous operating outflows

  Net Cash from Operating Activities (Direct)
    = Sum of all cash receipts − Sum of all cash payments

B. INDIRECT METHOD (IAS 7 §20, ASC 230-10-45)
────────────────────────────────────────────────────────────────────────────────

STEP 1 — STARTING POINT:
  1. Net Income (Profit for the Period)
     → From Income Statement (bottom line)
     → Under US GAAP: Must start from Net Income
     → Under IFRS: Can start from Profit Before Tax or Net Income

STEP 2 — ADJUSTMENTS FOR NON-CASH ITEMS:
  2. Depreciation and Amortization
     → Add back: Non-cash expense reducing net income
     → Includes: PPE depreciation, intangible amortization, depletion
  
  3. Impairment losses / Asset write-downs
     → Add back: Non-cash impairment charges
     → Includes: Goodwill impairment, PPE impairment, inventory write-downs
  
  4. Provision movements (net)
     → Add: Increase in provisions (warranties, restructuring, etc.)
     → Deduct: Decrease in provisions (reversals, utilization)
  
  5. Unrealized foreign exchange gains/losses
     → Deduct: Unrealized FX gains (non-cash)
     → Add: Unrealized FX losses (non-cash)
  
  6. Gains/Losses on disposal of non-current assets
     → Deduct: Gains on asset sales (reclassify to investing)
     → Add: Losses on asset sales (non-cash portion)
  
  7. Gains/Losses on financial instruments at fair value
     → Deduct: Unrealized gains on trading securities
     → Add: Unrealized losses on trading securities
  
  8. Share-based compensation expense
     → Add back: Non-cash stock-based compensation
  
  9. Deferred income tax expense/(benefit)
     → Add: Deferred tax expense (non-cash)
     → Deduct: Deferred tax benefit
  
  10. Equity method investment income/loss
      → Deduct: Share of associate's profit (non-cash, reclassify to investing)
      → Add: Share of associate's loss
  
  11. Other non-cash adjustments
      → Amortization of bond discounts/premiums
      → Changes in fair value of investment property
      → Other non-cash items affecting net income

STEP 3 — OPERATING PROFIT BEFORE WORKING CAPITAL CHANGES:
  = Net Income + All non-cash adjustments above

STEP 4 — WORKING CAPITAL CHANGES:
  12. (Increase)/Decrease in Trade Receivables
      → Increase: Deduct (cash tied up in receivables)
      → Decrease: Add (cash collected from customers)
  
  13. (Increase)/Decrease in Inventories
      → Increase: Deduct (cash used to build inventory)
      → Decrease: Add (inventory converted to sales/cash)
  
  14. (Increase)/Decrease in Prepaid Expenses
      → Increase: Deduct (cash paid in advance)
      → Decrease: Add (amortization of prepaids)
  
  15. Increase/(Decrease) in Trade Payables
      → Increase: Add (suppliers financing operations)
      → Decrease: Deduct (paying down suppliers)
  
  16. Increase/(Decrease) in Accrued Liabilities
      → Increase: Add (expenses accrued but not yet paid)
      → Decrease: Deduct (payment of accrued expenses)
  
  17. Increase/(Decrease) in Deferred Revenue
      → Increase: Add (cash received in advance)
      → Decrease: Deduct (revenue recognized, cash received earlier)
  
  18. Other working capital changes
      → Changes in other operating assets/liabilities

STEP 5 — NET CASH FROM OPERATING ACTIVITIES:
  = Operating profit before WC changes ± Working capital changes
  
  Note: Under indirect method, interest and taxes paid may be:
    - Disclosed separately in notes (IFRS requirement)
    - Shown as separate line items within operating section (common practice)
    - Classified differently (interest paid can be financing under IFRS)

────────────────────────────────────────────────────────────────────────────────
II. CASH FLOWS FROM INVESTING ACTIVITIES (CFI)
────────────────────────────────────────────────────────────────────────────────

  Cash Outflows (Investments):
    1. Purchase of Property, Plant and Equipment (Capex)
       → Acquisition of tangible fixed assets
       → Construction in progress payments
    
    2. Purchase of Intangible Assets
       → Software development costs capitalized
       → Patent, trademark, license acquisitions
    
    3. Purchase of Investment Property
       → Real estate held for rental income or capital appreciation
    
    4. Acquisition of Subsidiaries, Associates, and Joint Ventures
       → Net of cash acquired in business combinations
       → Equity investments in associates/JVs
    
    5. Purchase of Equity Instruments (Financial Investments)
       → Shares in other entities (not subsidiaries/associates)
       → Available-for-sale securities, FVTPL securities
    
    6. Purchase of Debt Instruments
       → Corporate bonds, government bonds held as investments
       → Loans made to third parties
    
    7. Capitalized Development Expenditure
       → Internally developed intangibles meeting capitalization criteria

  Cash Inflows (Disinvestments):
    8. Proceeds from Sale of Property, Plant and Equipment
       → Disposal of tangible fixed assets
       → Sale-leaseback transactions (portion relating to asset sale)
    
    9. Proceeds from Sale of Intangible Assets
       → Sale of patents, trademarks, licenses
    
    10. Proceeds from Sale of Investment Property
    
    11. Proceeds from Sale/Dilution of Subsidiaries, Associates, JVs
        → Net of cash disposed
        → Partial disposal of equity method investments
    
    12. Proceeds from Sale of Equity Instruments
        → Sale of financial investments in other entities
    
    13. Proceeds from Sale/Redemption of Debt Instruments
        → Maturity or early redemption of bond investments
        → Collection of loans made to third parties
    
    14. Interest Received
        → Under IFRS: Can be Operating OR Investing
        → Under US GAAP: MUST be Operating
        → If classified as investing: Include here
    
    15. Dividends Received
        → Under IFRS: Can be Operating OR Investing
        → Under US GAAP: MUST be Operating
        → If classified as investing: Include here

  Net Cash from Investing Activities
    = Sum of investing inflows − Sum of investing outflows
    → Typically negative for growing companies (more capex than disposals)

────────────────────────────────────────────────────────────────────────────────
III. CASH FLOWS FROM FINANCING ACTIVITIES (CFF)
────────────────────────────────────────────────────────────────────────────────

  Cash Inflows (Financing):
    1. Proceeds from Issuance of Share Capital
       → IPO proceeds, secondary offerings
       → Exercise of stock options/warrants
    
    2. Proceeds from Borrowings
       → Bank loans, lines of credit drawn
       → Bond issuances, note issuances
       → Commercial paper issuances
    
    3. Proceeds from Finance Lease Obligations
       → Initial recognition of lease liabilities (IFRS 16 / ASC 842)

  Cash Outflows (Financing):
    4. Repayment of Borrowings
       → Principal repayments on bank loans
       → Bond redemptions, note repayments
       → Commercial paper maturities
    
    5. Repayment of Finance Lease Obligations
       → Principal portion of lease payments
       → Under IFRS 16 / ASC 842: Separate from interest
    
    6. Dividends Paid to Shareholders
       → Cash dividends distributed
       → Under IFRS: Can be Operating OR Financing
       → Under US GAAP: MUST be Financing
    
    7. Share Buybacks / Treasury Stock Purchases
       → Repurchase of own shares from market
       → Settlement of share-based payment awards
    
    8. Payment of Transaction Costs Related to Financing
       → Debt issuance costs, underwriting fees
       → Share issuance costs (netted against proceeds)

  Net Cash from Financing Activities
    = Sum of financing inflows − Sum of financing outflows
    → Can be positive (raising capital) or negative (returning capital)

────────────────────────────────────────────────────────────────────────────────
RECONCILIATION TO CLOSING CASH BALANCE
────────────────────────────────────────────────────────────────────────────────

  1. Net Increase/(Decrease) in Cash and Cash Equivalents
     = CFO + CFI + CFF
  
  2. Cash and Cash Equivalents at Beginning of Period
     → Should equal prior period closing balance
  
  3. Effect of Exchange Rate Changes on Cash and Cash Equivalents
     → Unrealized FX gains/losses on foreign currency cash balances
     → Not included in CFO/CFI/CFF (non-cash effect)
     → Calculated as: Closing FX rate − Opening/average FX rate applied to foreign cash
  
  4. Cash and Cash Equivalents at End of Period
     = Net Change + Beginning Balance + FX Effect
     → Must reconcile to Balance Sheet cash balance

================================================================================
CLASSIFICATION DECISIONS: IFRS vs. US GAAP
================================================================================

  Item                          IFRS (IAS 7)                US GAAP (ASC 230)
  ─────────────────────────────────────────────────────────────────────────────
  Interest PAID                 Operating OR Financing      MUST be Operating
  Interest RECEIVED             Operating OR Investing      MUST be Operating
  Dividends RECEIVED            Operating OR Investing      MUST be Operating
  Dividends PAID                Operating OR Financing      MUST be Financing
  CIT Paid                      Operating (typically)       Operating
  Finance Lease Payment         Split: Principal=Financing, Interest=Operating/Financing
                                Split: Principal=Financing, Interest=Operating
  Bank Overdrafts               Part of cash equivalents    Financing activity
                                if integral to cash mgmt    
  Restricted Cash               May be excluded from        Always included in
                                cash equivalents            reconciliation
  Taxes on Share-Based Comp     Financing (excess tax       Operating (all tax cash flows)
                                benefits)                   
  Trading Securities            Operating (WC change)       Investing (typically)
  Loan Origination Fees         Operating                   Investing (lender's view)

================================================================================
MAPPING: VIETNAMESE TT99 vs. INTERNATIONAL (IFRS/US GAAP)
================================================================================

  Vietnamese TT99 (B03)              International Equivalent
  ─────────────────────────────────────────────────────────────────────────────
  Mã 01 (Direct: Cash from customers)   Cash received from customers
  Mã 02 (Direct: Cash to suppliers)     Cash paid to suppliers and employees
  Mã 03 (Direct: Cash to employees)     Included in above (combined)
  Mã 04 (Direct: Interest paid)         Interest paid (Operating per US GAAP)
  Mã 05 (Direct: CIT paid)              Income taxes paid
  Mã 20 (Net CFO)                       Net cash from operating activities
  Mã 21 (Capex)                         Purchase of PP&E and intangibles
  Mã 22 (Proceeds from disposal)        Proceeds from sale of PP&E
  Mã 23-24 (Loans to/from others)       Loans made/collected (Investing)
  Mã 25-26 (Equity investments)         Acquisition/disposal of investments
  Mã 27 (Interest/Dividends received)   Interest/Dividends received (if Investing)
  Mã 30 (Net CFI)                       Net cash from investing activities
  Mã 31 (Share issuance)                Proceeds from issuance of shares
  Mã 32 (Share buyback)                 Purchase of treasury stock
  Mã 33-34 (Borrowings/Repayment)       Proceeds from/Repayment of borrowings
  Mã 35 (Finance lease principal)       Repayment of lease liabilities
  Mã 36 (Dividends paid)                Dividends paid (Financing per US GAAP)
  Mã 40 (Net CFF)                       Net cash from financing activities
  Mã 50 (Net cash flow)                 Net increase/decrease in cash
  Mã 60 (Opening cash)                  Cash at beginning of period
  Mã 61 (FX effect)                     Effect of exchange rate changes
  Mã 70 (Closing cash)                  Cash at end of period

================================================================================
KEY FORMULAS AND RECONCILIATIONS
================================================================================

INDIRECT METHOD CFO FORMULA:
  CFO = Net Income
      + Depreciation & Amortization
      + Impairment Charges
      + Share-based Compensation
      + Deferred Tax Expense
      − Gains on Asset Sales
      + Losses on Asset Sales
      − Investment Income (Equity Method)
      + Equity Method Losses
      − Δ Accounts Receivable
      − Δ Inventory
      − Δ Prepaid Expenses
      + Δ Accounts Payable
      + Δ Accrued Liabilities
      + Δ Deferred Revenue
      ± Other Working Capital Changes

CAPITAL EXPENDITURE (Capex) CALCULATION:
  Capex = Δ Gross PPE (from BS) + Depreciation Expense (from IS)
          − Book Value of Assets Sold
          + Δ Capitalized Development Costs

FREE CASH FLOW (FCF) CALCULATION:
  FCF = CFO − Capital Expenditures
  FCF to Firm (FCFF) = CFO + Interest Paid × (1 − Tax Rate) − Capex
  FCF to Equity (FCFE) = CFO − Capex + Net Borrowing

CASH RECONCILIATION CHECK:
  Δ Cash (Balance Sheet) = CFO + CFI + CFF + FX Effect
  Ending Cash (Statement) = Ending Cash (Balance Sheet)

================================================================================
DISCLOSURE REQUIREMENTS (IAS 7 / ASC 230)
================================================================================

MANDATORY DISCLOSURES:
  1. Components of cash and cash equivalents
     → Breakdown: Cash on hand, demand deposits, short-term investments
     → Policy for determining cash equivalents (maturity threshold)
  
  2. Reconciliation to Balance Sheet
     → Statement total must match Balance Sheet cash line
     → Any restricted cash must be explained
  
  3. Interest and Taxes Paid (IFRS only)
     → Total interest paid (separate from interest expense)
     → Total income taxes paid
     → Can be disclosed in notes or on face of statement
  
  4. Non-cash Investing and Financing Activities
     → Asset acquisitions through debt assumption
     → Conversion of debt to equity
     → Finance lease initial recognition
     → Must be disclosed in notes (not in main statement)
  
  5. Foreign Currency Cash Flows (IFRS)
     → Exchange rates used for translation
     → Separate disclosure of FX effect on cash
  
  6. Supplemental Cash Flow Information (US GAAP)
     → Cash paid for interest
     → Cash paid for income taxes
     → Required even if using direct method

VOLUNTARY DISCLOSURES:
  7. Free Cash Flow metrics
  8. Organic vs. inorganic cash flows
  9. Maintenance vs. growth Capex breakdown
  10. Segment-level cash flow information

================================================================================
END OF INTERNATIONAL CASH FLOW MODEL DOCUMENTATION
================================================================================
"""


class InternationalCashFlowModel:
    """
    International Cash Flow Statement Model (IFRS / US GAAP compliant)
    
    Supports both Direct and Indirect methods for operating activities.
    Provides mapping to Vietnamese TT99 standard for comparison.
    """
    
    # Section codes for reference
    SECTION_OPERATING = "CFO"
    SECTION_INVESTING = "CFI"
    SECTION_FINANCING = "CFF"
    
    # Standard line item codes (flexible, unlike Vietnamese Mã số)
    OPERATING_LINES = {
        "direct": [
            "OC01",  # Cash received from customers
            "OC02",  # Cash received from other operating revenue
            "OC03",  # Cash paid to suppliers and employees
            "OC04",  # Interest paid
            "OC05",  # Income taxes paid
            "OC06",  # Other operating cash flows, net
        ],
        "indirect": [
            "OI01",  # Net income
            "OI02",  # Depreciation and amortization
            "OI03",  # Impairment and provisions
            "OI04",  # Deferred taxes
            "OI05",  # Gains/losses on asset sales
            "OI06",  # Share-based compensation
            "OI07",  # Working capital changes
            "OI08",  # Other non-cash adjustments
        ]
    }
    
    INVESTING_LINES = {
        "CI01",  # Purchase of PP&E and intangibles (Capex)
        "CI02",  # Proceeds from sale of PP&E and intangibles
        "CI03",  # Acquisition of businesses, net of cash
        "CI04",  # Proceeds from disposal of businesses
        "CI05",  # Purchase of financial investments
        "CI06",  # Proceeds from sale of financial investments
        "CI07",  # Loans made to third parties
        "CI08",  # Collection of loans
        "CI09",  # Interest/dividends received (if classified as investing)
        "CI10",  # Other investing cash flows, net
    }
    
    FINANCING_LINES = {
        "CF01",  # Proceeds from share issuance
        "CF02",  # Share buybacks / treasury stock
        "CF03",  # Proceeds from borrowings
        "CF04",  # Repayment of borrowings
        "CF05",  # Principal payments on finance leases
        "CF06",  # Dividends paid
        "CF07",  # Debt issuance costs
        "CF08",  # Other financing cash flows, net
    }
    
    RECONCILIATION_LINES = {
        "RC01",  # Net change in cash (CFO + CFI + CFF)
        "RC02",  # Cash at beginning of period
        "RC03",  # Effect of exchange rate changes
        "RC04",  # Cash at end of period
    }
    
    def __init__(self, method="indirect", standard="IFRS"):
        """
        Initialize International Cash Flow Model
        
        Args:
            method: "direct" or "indirect" for operating activities
            standard: "IFRS" or "US_GAAP" for classification rules
        """
        self.method = method
        self.standard = standard
        self.data = {}
    
    def set_operating_cash_flow(self, line_items: dict):
        """Set operating cash flow line items"""
        self.data["operating"] = line_items
    
    def set_investing_cash_flow(self, line_items: dict):
        """Set investing cash flow line items"""
        self.data["investing"] = line_items
    
    def set_financing_cash_flow(self, line_items: dict):
        """Set financing cash flow line items"""
        self.data["financing"] = line_items
    
    def calculate_net_cash_flow(self) -> dict:
        """
        Calculate net cash flows for each section and total
        
        Returns:
            Dictionary with CFO, CFI, CFF, and total net change
        """
        cfo = sum(self.data.get("operating", {}).values())
        cfi = sum(self.data.get("investing", {}).values())
        cff = sum(self.data.get("financing", {}).values())
        
        return {
            "cfo": cfo,
            "cfi": cfi,
            "cff": cff,
            "net_change": cfo + cfi + cff
        }
    
    def reconcile_to_closing_cash(
        self, 
        opening_cash: float, 
        fx_effect: float = 0.0
    ) -> dict:
        """
        Reconcile from opening to closing cash balance
        
        Args:
            opening_cash: Cash balance at beginning of period
            fx_effect: Impact of foreign exchange rate changes
        
        Returns:
            Dictionary with reconciliation details
        """
        net_flows = self.calculate_net_cash_flow()
        closing_cash = opening_cash + net_flows["net_change"] + fx_effect
        
        return {
            "opening_cash": opening_cash,
            "net_change": net_flows["net_change"],
            "fx_effect": fx_effect,
            "closing_cash": closing_cash,
            "reconciled": True
        }
    
    def get_classification_rule(self, item_type: str) -> str:
        """
        Get classification rule for specific item type based on standard
        
        Args:
            item_type: Type of cash flow item (e.g., "interest_paid")
        
        Returns:
            Classification according to selected standard
        """
        rules = {
            "interest_paid": {
                "IFRS": "Operating or Financing (entity choice)",
                "US_GAAP": "Operating (required)"
            },
            "interest_received": {
                "IFRS": "Operating or Investing (entity choice)",
                "US_GAAP": "Operating (required)"
            },
            "dividends_received": {
                "IFRS": "Operating or Investing (entity choice)",
                "US_GAAP": "Operating (required)"
            },
            "dividends_paid": {
                "IFRS": "Operating or Financing (entity choice)",
                "US_GAAP": "Financing (required)"
            },
            "income_taxes_paid": {
                "IFRS": "Operating (unless specifically identified)",
                "US_GAAP": "Operating (required)"
            }
        }
        
        return rules.get(item_type, "Classification depends on nature")
    
    def convert_from_vietnamese_tt99(self, tt99_data: dict) -> dict:
        """
        Convert Vietnamese TT99 cash flow data to international format
        
        Args:
            tt99_data: Dictionary with Vietnamese Mã số codes and values
        
        Returns:
            Dictionary mapped to international line items
        """
        mapping = {
            # Operating activities
            "01": "Cash received from customers",
            "02": "Cash paid to suppliers",
            "03": "Cash paid to employees",
            "04": "Interest paid",
            "05": "Income taxes paid",
            "06": "Other operating receipts",
            "07": "Other operating payments",
            "20": "Net cash from operating activities",
            
            # Investing activities
            "21": "Purchase of fixed assets",
            "22": "Proceeds from sale of fixed assets",
            "23": "Loans made to others",
            "24": "Collection of loans",
            "25": "Equity investments made",
            "26": "Proceeds from equity investments",
            "27": "Interest/dividends received",
            "30": "Net cash from investing activities",
            
            # Financing activities
            "31": "Proceeds from share issuance",
            "32": "Share buybacks",
            "33": "Proceeds from borrowings",
            "34": "Repayment of borrowings",
            "35": "Finance lease principal payments",
            "36": "Dividends paid",
            "40": "Net cash from financing activities",
            
            # Reconciliation
            "50": "Net change in cash",
            "60": "Opening cash balance",
            "61": "FX effect on cash",
            "70": "Closing cash balance"
        }
        
        international_data = {}
        for ma_so, value in tt99_data.items():
            line_name = mapping.get(ma_so, f"Vietnamese item {ma_so}")
            international_data[line_name] = value
        
        return international_data
    
    def validate_reconciliation(
        self, 
        balance_sheet_cash_start: float,
        balance_sheet_cash_end: float,
        fx_effect: float = 0.0
    ) -> dict:
        """
        Validate that cash flow statement reconciles to balance sheet
        
        Args:
            balance_sheet_cash_start: Cash from opening balance sheet
            balance_sheet_cash_end: Cash from closing balance sheet
            fx_effect: Foreign exchange impact
        
        Returns:
            Validation result with any discrepancies
        """
        net_flows = self.calculate_net_cash_flow()
        calculated_end = balance_sheet_cash_start + net_flows["net_change"] + fx_effect
        
        discrepancy = abs(calculated_end - balance_sheet_cash_end)
        is_valid = discrepancy < 0.01  # Allow small rounding differences
        
        return {
            "valid": is_valid,
            "opening_balance": balance_sheet_cash_start,
            "net_change": net_flows["net_change"],
            "fx_effect": fx_effect,
            "calculated_closing": calculated_end,
            "actual_closing": balance_sheet_cash_end,
            "discrepancy": discrepancy
        }


# Example usage and test data
if __name__ == "__main__":
    # Create model with indirect method (most common)
    model = InternationalCashFlowModel(method="indirect", standard="IFRS")
    
    # Sample operating cash flows (indirect method)
    operating_data = {
        "OI01": 1000000,    # Net income
        "OI02": 250000,     # Depreciation & amortization
        "OI03": 50000,      # Provisions
        "OI04": 30000,      # Deferred tax
        "OI05": -20000,     # Gain on asset sale
        "OI06": 40000,      # Share-based comp
        "OI07": -150000,    # Working capital changes (net)
        "OI08": 10000,      # Other adjustments
    }
    
    # Sample investing cash flows
    investing_data = {
        "CI01": -500000,    # Capex
        "CI02": 50000,      # Asset sale proceeds
        "CI03": 0,          # No acquisitions
        "CI05": -100000,    # Financial investments
        "CI09": 35000,      # Interest/dividends received
    }
    
    # Sample financing cash flows
    financing_data = {
        "CF01": 200000,     # Share issuance
        "CF03": 300000,     # New borrowings
        "CF04": -250000,    # Debt repayment
        "CF06": -150000,    # Dividends paid
    }
    
    # Set data
    model.set_operating_cash_flow(operating_data)
    model.set_investing_cash_flow(investing_data)
    model.set_financing_cash_flow(financing_data)
    
    # Calculate net flows
    net_flows = model.calculate_net_cash_flow()
    print(f"CFO: {net_flows['cfo']:,}")
    print(f"CFI: {net_flows['cfi']:,}")
    print(f"CFF: {net_flows['cff']:,}")
    print(f"Net Change: {net_flows['net_change']:,}")
    
    # Reconcile to closing cash
    reconciliation = model.reconcile_to_closing_cash(
        opening_cash=800000,
        fx_effect=-5000
    )
    print(f"\nReconciliation:")
    print(f"Opening Cash: {reconciliation['opening_cash']:,}")
    print(f"Net Change: {reconciliation['net_change']:,}")
    print(f"FX Effect: {reconciliation['fx_effect']:,}")
    print(f"Closing Cash: {reconciliation['closing_cash']:,}")
    
    # Validate against balance sheet
    validation = model.validate_reconciliation(
        balance_sheet_cash_start=800000,
        balance_sheet_cash_end=reconciliation['closing_cash'],
        fx_effect=-5000
    )
    print(f"\nValidation: {'PASSED' if validation['valid'] else 'FAILED'}")
    print(f"Discrepancy: {validation['discrepancy']:,.2f}")
    
    # Show classification rules
    print(f"\nClassification Rules ({model.standard}):")
    for item in ["interest_paid", "dividends_paid", "interest_received"]:
        rule = model.get_classification_rule(item)
        print(f"  {item}: {rule}")
