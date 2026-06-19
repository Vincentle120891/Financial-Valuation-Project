# Debt & Equity Schedules — Excel Model vs DCFEngine Implementation

> Analysis of how the Excel model's Debt Schedule Part 1, Debt Schedule Part 2,
> and Equity Schedule map to the current DCFEngine implementation.

---

## EXCEL MODEL: DEBT SCHEDULE PART 1 (rows 331-345)

### CASH Section
```
Row 331: Beginning Balance:  [F] =Prior year ending
Row 332: Increase/(Decrease): [F] =linked from Cash Flow Statement
Row 333: Ending Balance:     [F] =Beginning + Change
Row 334: Interest Rate:      [H] =1% (from Inputs row 77)
Row 335: Interest Income:    [F] =Cash Balance x Interest Rate
```

### LONG TERM DEBT Section
```
Row 338: Beginning Balance:  [F] =Prior year ending
Row 339: Increase/(Decrease): [H] =hardcoded from Inputs row 23
Row 340: Ending Balance:     [F] =Beginning + Change
Row 341: Interest Rate:      [H] =6% (from Inputs row 79)
Row 342: Interest Expense:   [F] =LT Debt Balance x Interest Rate
```

**Key insight:** Interest is DYNAMIC — it depends on the debt balance each year, not a constant.

---

## EXCEL MODEL: DEBT SCHEDULE PART 2 (rows 347-368)

### AVAILABLE CASH
```
Row 350: Beginning Cash:       [L] =linked from Part 1 Cash
Row 351: Cash from Operations:  [L] =linked from CF Statement
Row 352: Cash from Investing:   [L] =linked from CF Statement
Row 353: Change in LT Debt:     [H] =hardcoded from Inputs row 23
Row 354: Change in Common Equity: [H] =hardcoded from Inputs row 24
Row 355: Dividends:             [L] =linked from Equity Schedule
Row 356: Cash Available:        [F] =SUM(all above)
```

### REVOLVING CREDIT LINE
```
Row 359: Beginning Balance:     [F] =Prior year ending
Row 360: Increase/(Decrease):   [F] =-MIN(Available Cash, Beginning Balance)
Row 361: Ending Balance:        [IF] =IF(SUM(Beginning+Change)>0, SUM, 0)
Row 362: Interest Rate:         [H] =5% (from Inputs row 78)
Row 363: Interest Expense:      [IF] =IF(CircularityFlag, AVG(Beg,End)xRate, EndxRate)
```

### NET INTEREST
```
Row 366: Total Interest:        [F] =LT Interest + Revolving Interest
Row 367: Less: Interest Income: [F] =-(from Part 1 Cash Interest Income)
Row 368: Net Interest Expense:  [F] =Total - Interest Income
```

**Key insight:** Revolving credit is DYNAMIC — it draws down when cash is insufficient and repays when cash is available. Net Interest feeds back into the Income Statement.

---

## EXCEL MODEL: EQUITY SCHEDULE (rows 370-385)

### COMMON EQUITY
```
Row 372: Beginning:  [F] =Prior year ending
Row 373: Change:     [H] =hardcoded from Inputs row 24
Row 374: Ending:     [F] =Beginning + Change
```

### DIVIDENDS
```
Row 377: Net Income:   [L] =linked from Income Statement
Row 378: Payout Ratio: [H] =from Inputs row 80
Row 379: Dividend:     [F] =Net Income x Payout Ratio
```

### RETAINED EARNINGS
```
Row 382: Beginning:  [F] =Prior year ending
Row 383: Net Income: [L] =linked from Income Statement
Row 384: Dividends:  [F] =-(from Dividend row)
Row 385: Ending:     [F] =Beginning + Net Income - Dividends
```

**Key insight:** Dividends = Net Income x Payout Ratio. Retained Earnings feeds into the Balance Sheet equity section.

---

## CURRENT DCFEngine IMPLEMENTATION

### What exists:
- **Cash balance tracking** in `_build_cash_flow_statement()` — beginning/ending cash
- **LT Debt tracking** in `_build_balance_sheet()` — ending LT debt balance
- **Revolving credit** stored as a fixed array `revolving_credit_line` in DCFInputs
- **Interest** is CONSTANT: `projected_interest_expense` (line 1632)
- **Dividends** is CONSTANT or fixed array: `projected_dividends` in DCFInputs
- **Equity** tracked in `_build_balance_sheet()` — common_equity and retained_earnings

### What's MISSING vs Excel model:

| Feature | Excel | DCFEngine | Gap |
|---------|-------|-----------|-----|
| Cash Interest Income | Dynamic: Cash_Balance x 1% | Not computed | MISSING |
| LT Debt Interest | Dynamic: LT_Debt_Balance x 6% | Constant `projected_interest_expense` | SIMPLIFIED |
| Revolving Credit Draw/Repay | Dynamic: -MIN(Available, Beginning) | Fixed array from DCFInputs | SIMPLIFIED |
| Revolving Interest | Dynamic: Balance x 5% | Not computed | MISSING |
| Net Interest | Total - Interest Income | Not computed | MISSING |
| Dividends | Dynamic: NI x Payout Ratio | Constant or fixed array | SIMPLIFIED |

---

## CORRECT IMPLEMENTATION NEEDED

To match the Excel model exactly, the debt and equity schedules need these dynamic calculations:

### Debt Schedule Part 1 (Cash + LT Debt):
```python
# For each period:
cash_ending = cash_beginning + cash_from_operations + cash_from_investing
interest_income = cash_ending * 0.01  # 1% cash rate

lt_debt_ending = lt_debt_beginning + change_in_lt_debt  # from Inputs
interest_expense_lt = lt_debt_ending * 0.06  # 6% LT rate
```

### Debt Schedule Part 2 (Revolving + Net Interest):
```python
# Available Cash (feeds into revolving credit decision)
cash_available = (cash_beginning + cfo + cfi + change_lt_debt 
                  + change_equity - dividends)

# Revolving Credit Line
revolver_beginning = prior_revolver
revolver_change = -min(cash_available, revolver_beginning)
revolver_ending = max(revolver_beginning + revolver_change, 0)
interest_expense_revolver = revolver_ending * 0.05  # 5% revolving rate

# Net Interest
total_interest = interest_expense_lt + interest_expense_revolver
net_interest = total_interest - interest_income
```

### Equity Schedule:
```python
# Common Equity
common_equity_ending = common_equity_beginning + change_in_equity

# Dividends (dynamic from Net Income)
dividends = net_income * payout_ratio

# Retained Earnings
re_ending = re_beginning + net_income - dividends
```

### Feed-back into Income Statement:
```python
# Interest in IS comes from Debt Schedules, NOT a constant
interest_expense = net_interest  # from Debt Schedule Part 2
ebt = ebit - net_interest  # EBT uses dynamic interest
```

---

## CIRCULAR DEPENDENCY NOTE

The Excel model has a circular reference:
- Interest Expense depends on Debt Balances
- Debt Balances depend on Cash Flow
- Cash Flow depends on Net Income
- Net Income depends on Interest Expense (via EBT)

Excel handles this with iterative calculation. The DCFEngine currently avoids this by using constant interest. To implement dynamic interest, we would need either:
1. Iterative calculation (like Excel)
2. Two-pass approach: first pass with constant interest, second pass with dynamic interest from first-pass balances
