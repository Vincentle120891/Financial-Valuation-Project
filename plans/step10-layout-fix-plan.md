# Step 10 Layout Fix Plan

## Issues Identified from Screenshot

1. **Football Field Chart**: Too tall (200px fixed height), massive empty space. The chart range scale shows negative values ($-26K to $3.7K) which indicates the data extraction is wrong.
2. **Forecast Horizon / Peer Comparison**: Side-by-side layout works but could be more compact.

## Fix Plan

### Fix 1: Football Field Chart height reduction
**File**: [`step10_run_valuation_step.tsx`](frontend/src/components/valuation-flow/step10_run_valuation_step.tsx:219)
- Change `h-[200px]` to `h-[140px]` for a more compact chart

### Fix 2: Football Field chart data extraction
The `deriveFootballRanges` function at the bottom of step10 may be extracting wrong data. Need to check how it maps `currentResults` to chart ranges.

### Fix 3: Forecast Horizon / Peer Comparison height
**File**: [`step10_run_valuation_step.tsx`](frontend/src/components/valuation-flow/step10_run_valuation_step.tsx:285)
- Change `h-[220px]` to `h-[180px]` for both chart panels

### Fix 4: Overall section spacing
The parent container uses `space-y-5` (20px gap between all sections). Could reduce to `space-y-3` (12px) for tighter layout.
