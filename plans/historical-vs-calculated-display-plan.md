# Plan: Show Historical Data vs Calculated Values in Step 9 Schedules

## Overview

For historical periods (e.g., 2023-09, 2024-09, 2025-09), there are TWO sets of values:
1. **Historical Data** — Actual reported values from XBRL/API (fetched and mapped)
2. **Calculated Values** — What the DCF engine computes for those same periods using model formulas

The user wants BOTH displayed: historical as the main value, calculated in red small font below when they differ.

## Data Sources

| Source | What It Contains | Where It Lives |
|--------|-----------------|----------------|
| **Historical XBRL** | Actual company-reported values | `historical.*` (from `extractHistoricalActuals`) |
| **Backend Engine Output** | Model-calculated values for ALL periods | `output.*` (from `transformBackendToFrontend`) |

For historical periods, the backend engine output contains the model's reconstruction of what the values WOULD be using the same formulas applied to historical inputs.

## Implementation

### Step 1: Extend ScheduleTable Row Type

Add optional `calculatedValues` to the row interface:

```typescript
rows: {
  label: string;
  values: number[];           // Historical actuals (primary display)
  calculatedValues?: number[]; // Engine-calculated values (red small font)
  isHighlight?: boolean;
  isReference?: boolean;
  formula?: string;
  fieldId?: string;
}[];
```

### Step 2: Modify ScheduleTable Cell Rendering

For each cell in a historical column (index < histLen):
- Show `values[idx]` as the main number (normal style)
- If `calculatedValues[idx]` exists AND differs from `values[idx]`, show it below in red small font

```tsx
<td>
  <div>{values[idx].toLocaleString(...)}</div>
  {calculatedValues?.[idx] && Math.abs(calculatedValues[idx] - values[idx]) > 1 && (
    <div className="text-[8px] text-red-400">
      Calc: {calculatedValues[idx].toLocaleString(...)}
    </div>
  )}
</td>
```

### Step 3: Add calculatedValues to Each Schedule Row

For each schedule, the `calculatedValues` array comes from the backend engine output (`output.*`), while `values` comes from the historical XBRL data (padded into the schedule).

**Income Statement [3A]:**
| Row | `values` (Historical) | `calculatedValues` (Engine) |
|-----|----------------------|---------------------------|
| Revenue | `historical.revenue` | `output.incomeStatement.revenue` |
| COGS | `historical.cogs` | `output.incomeStatement.cogs` |
| Gross Profit | computed | `output.incomeStatement.grossProfit` |
| SG&A | `historical.sga` | `output.incomeStatement.sga` |
| R&D | `historical.researchDevelopment` | computed from engine |
| Depreciation | `historical.depreciation` | `output.incomeStatement.depreciation` |
| EBIT | computed | `output.incomeStatement.ebit` |
| Interest Expense | `historical.interestExpense` | `output.incomeStatement.interestExpense` |
| Net Income | `historical.netIncome` | `output.incomeStatement.netIncome` |

**Working Capital [3B]:**
| Row | `values` (Historical) | `calculatedValues` (Engine) |
|-----|----------------------|---------------------------|
| AR Days | computed from BS | `output.workingCapital.arDays` |
| Inventory Days | computed from BS | `output.workingCapital.invDays` |
| AP Days | computed from BS | `output.workingCapital.apDays` |
| AR Balance | `historical.ar` | `output.workingCapital.arBalance` |
| Inventory | `historical.inventory` | `output.workingCapital.inventoryBalance` |
| AP Balance | `historical.ap` | `output.workingCapital.apBalance` |

**Depreciation [3C]:**
| Row | `values` (Historical) | `calculatedValues` (Engine) |
|-----|----------------------|---------------------------|
| CapEx | `historical.capex` | `output.depreciation.capex` |
| Total Depreciation | `historical.depreciation` | `output.depreciation.totalDepreciation` |
| PP&E Gross | `historical.ppe` | `output.depreciation.grossPpeEnding` |

**Balance Sheet [3H]:**
| Row | `values` (Historical) | `calculatedValues` (Engine) |
|-----|----------------------|---------------------------|
| Cash | `historical.cash` | `output.balanceSheet.cash` |
| AR | `historical.ar` | `output.balanceSheet.accountsReceivable` |
| Inventory | `historical.inventory` | `output.balanceSheet.inventories` |
| Total Assets | `historical.totalAssets` | `output.balanceSheet.totalAssets` |
| LT Debt | `historical.longTermDebt` | `output.balanceSheet.longTermDebt` |
| Common Equity | `historical.commonEquity` | `sharedEquity.ceAll` |
| Retained Earnings | `historical.retainedEarnings` | `sharedEquity.reAll` |

**CFS [3G]:**
| Row | `values` (Historical) | `calculatedValues` (Engine) |
|-----|----------------------|---------------------------|
| Net Income | `historical.netIncome` | `output.cashFlowStatement.netIncome` |
| Depreciation | `historical.depreciation` | `output.cashFlowStatement.depreciation` |
| CapEx | `historical.capex` | `output.cashFlowStatement.capitalExpenditure` |

### Step 4: Visual Design

- **Historical column header**: Blue text (already exists)
- **Main value**: Normal white text (already exists)
- **Calculated value**: Red small font (8px) below the main value, only shown when:
  - Column is historical (index < histLen)
  - `calculatedValues[idx]` exists
  - Difference exceeds threshold (> 1 or > 1% of value)

### Step 5: Threshold Logic

Show calculated value only when the difference is meaningful:
```typescript
const showCalculated = (actual: number, calculated: number): boolean => {
  if (!calculated || calculated === 0) return false;
  const diff = Math.abs(actual - calculated);
  const pctDiff = diff / Math.max(Math.abs(actual), 1);
  return diff > 1 && pctDiff > 0.01; // > $1 AND > 1% difference
};
```

## Files to Modify

1. **`step9_assumptions_step.tsx`** — ScheduleTable component + all schedule row definitions
2. No backend changes needed — all data already available

## Priority

- High: IS [3A], BS [3H], CFS [3G] — most visible discrepancies
- Medium: WC [3B], Dep [3C], Tax [3E/3F]
- Low: Debt [3I/3J], Equity [3K], Asset [3D]
