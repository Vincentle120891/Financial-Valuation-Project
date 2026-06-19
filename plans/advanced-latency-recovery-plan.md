# Advanced Latency Recovery & Visual Shifting Matrix — Implementation Plan

## Overview

Replace consumer-style overlay masks with in-place panel processing states that preserve the Bloomberg Modern grid structure. When a background API process triggers, the active panel transitions to a "Contrast Lock" state with a scanning border animation and monospaced micro-log stream.

## Three Law Summary

### A. Contrast Lock Surface Overrides
Panels processing background data switch to specific surface colors:

| Property | Light Mode (Financial Times) | Dark Mode (Deep Sapphire) |
|----------|-----|------|
| Panel BG | `#EAE2DA` (Concrete-Sand) | `#0C111C` (Obsidian Midnight) |
| Text/Labels | `#949A9F` (Static Slate) | `#475569` (Steel Core) |
| Border | `1px solid #BDB5AD` | `1px solid #1E293B` |

### B. Scanning Grid Line Animation
- NEVER animate text opacity during calculation
- ONLY animate the 1px border perimeter
- A 40px accent color segment travels around the border in 2s linear loop
- CSS: `linear-gradient(to right, transparent, var(--accent-primary) 50%, transparent)`

### C. Monospaced Progress Tick Stream
- Geist Mono at exactly 11px, line-height: 1.2
- Rolling micro-log with timestamped terminal statements
- Shows analytical trajectory of API processing

## Files to Modify

### 1. `frontend/src/styles/tokens.css` — Add Contrast Lock Tokens

Add to `:root` (Light Theme):
```css
/* Contrast Lock — Processing panel states */
--processing-bg: #EAE2DA;
--processing-text: #949A9F;
--processing-border: #BDB5AD;
```

Add to `[data-theme="dark"]`:
```css
/* Contrast Lock — Processing panel states */
--processing-bg: #0C111C;
--processing-text: #475569;
--processing-border: #1E293B;
```

### 2. `frontend/src/index.css` — Add Scanning Border Animation

```css
/* Scanning Border Animation — 40px accent segment travels perimeter in 2s */
@keyframes scanning-border {
  0% { background-position: 0 0, 100% 0, 100% 100%, 0 100%; }
  25% { background-position: 100% 0, 100% 100%, 0 100%, 0 0; }
  50% { background-position: 100% 100%, 0 100%, 0 0, 100% 0; }
  75% { background-position: 0 100%, 0 0, 100% 0, 100% 100%; }
  100% { background-position: 0 0, 100% 0, 100% 100%, 0 100%; }
}

.processing-panel {
  background: var(--processing-bg) !important;
  color: var(--processing-text) !important;
  border: 1px solid var(--processing-border) !important;
  background-image:
    linear-gradient(to right, transparent, var(--accent-primary) 50%, transparent),
    linear-gradient(to bottom, transparent, var(--accent-primary) 50%, transparent),
    linear-gradient(to right, transparent, var(--accent-primary) 50%, transparent),
    linear-gradient(to bottom, transparent, var(--accent-primary) 50%, transparent);
  background-size:
    40px 1px,
    1px 40px,
    40px 1px,
    1px 40px;
  background-position: 0 0, 100% 0, 100% 100%, 0 100%;
  background-repeat: no-repeat;
  animation: scanning-border 2s linear infinite;
}

.processing-panel * {
  color: inherit !important;
}
```

### 3. `frontend/src/components/ui/ProcessingPanel.tsx` — New Component

A reusable wrapper component that:
- Accepts `isProcessing: boolean` prop
- When `isProcessing=true`: applies `.processing-panel` class, renders micro-log stream
- When `isProcessing=false`: renders children normally
- Micro-log: Geist Mono 11px, line-height 1.2, rolling timestamped entries

Props:
```tsx
interface ProcessingPanelProps {
  isProcessing: boolean;
  title?: string;
  logLines?: string[];
  children: React.ReactNode;
}
```

### 4. Integration Points

The `ProcessingPanel` wraps existing step content areas:
- Step 6: `ApiDataStep` — wraps data fetch sections
- Step 7: `HistoricalDataExtractionStep` — wraps extraction results
- Step 9: `AssumptionsStep` — wraps schedule calculation areas
- Step 10: `RunValuationStep` — wraps valuation execution area

Usage pattern:
```tsx
<ProcessingPanel isProcessing={loading} title="FETCHING DATA..." logLines={logEntries}>
  <StepContent />
</ProcessingPanel>
```

## Implementation Order

1. Add Contrast Lock tokens to `tokens.css`
2. Add scanning border animation CSS to `index.css`
3. Create `ProcessingPanel.tsx` component
4. Run `npm run build` to verify

## Verification

1. Build compiles with 0 errors
2. Light mode: processing panel shows #EAE2DA background, #949A9F text, #BDB5AD border
3. Dark mode: processing panel shows #0C111C background, #475569 text, #1E293B border
4. Scanning border: 40px accent segment travels around perimeter continuously in 2s
5. No text opacity animations — only border perimeter animates
6. Micro-log: Geist Mono 11px, line-height 1.2, timestamped entries scroll
7. Panel restores to normal state when `isProcessing` becomes false
