# Bloomberg Modern / High-Density Precision — Design System Implementation Plan

## Overview

Transform the frontend from Inter/JetBrains Mono SaaS aesthetic to a Bloomberg Terminal-grade precision interface using Geist Sans + Geist Mono, razor-sharp borders, zero-animation transitions, and high-density layouts.

## Critical Design Laws

1. **Dual-Font System**: Geist Sans for UI text, Geist Mono for ALL numeric/data/timestamp/formula values
2. **Tabular Alignment Law**: Every numeric element must have `font-variant-numeric: tabular-nums lining-nums` and `font-feature-settings: "tnum" on, "lnum" on`
3. **Razor-Sharp Borders**: 1px solid lines only — Dark: `#2d3139`, Light: `#e2e8f0`
4. **Zero Shadows**: Remove ALL box-shadow and backdrop-filter blur. Use borders for depth.
5. **Zero-Delay Interactions**: Instant color cuts on hover, no cubic-bezier curves
6. **High Density**: 4px/8px/12px max inner padding, maximize data per viewport
7. **Restricted Palette**: Colors ONLY for data variance, risk states, or performance deltas

## Files to Modify

### 1. `frontend/index.html`
- **Action**: Replace Google Fonts Inter/JetBrains Mono imports with Geist Sans/Geist Mono from jsDelivr CDN
- **Status**: DONE (already applied)

### 2. `frontend/src/styles/tokens.css` — Complete Rewrite
Changes:
- Swap `--font-sans` from `'Inter'` → `'Geist Sans'`
- Swap `--font-mono` from `'JetBrains Mono'` → `'Geist Mono'`
- Dark theme becomes the DEFAULT (`:root`), light theme is `[data-theme="light"]`
- Dark `--border-default`: `#1e293b` → `#2d3139`
- Dark `--border-strong`: `#334155` → `#3d434d`
- Dark `--canvas-bg`: `#090d16` → `#080c14`
- Dark `--canvas-surface`: `#0f172a` → `#0d1320`
- Dark `--canvas-surface-elevated`: `#1e293b` → `#151d2e`
- Set ALL `--shadow-*` to `none`
- Reduce `--radius-*` values to 4/6/6/8px
- Reduce `--space-md` from 16px → 12px
- Set `--backdrop-blur` to `none`
- Light theme: `--border-default: #e2e8f0`, shadows none

### 3. `frontend/src/styles/typography.css` — Rewrite
Changes:
- Add `lining-nums` alongside `tabular-nums` everywhere
- Update `font-feature-settings` to `"tnum" on, "lnum" on` everywhere
- `.financial-value` and `.financial-value-mono`: update font stack to Geist
- `.data-cell`: change to use `var(--font-mono)` for data ledger values
- `.data-cell-mono`: already mono, just update font stack
- Ensure `.section-header` uses `var(--font-sans)` (Geist Sans)

### 4. `frontend/src/index.css` — Major Overhaul
Changes:
- Remove ALL hardcoded hex colors — use CSS custom properties from tokens
- `body` background: use `var(--canvas-bg)`
- `.terminal-app` grid: tighten sidebar from 320px → 280px
- `.terminal-nav`: height from 48px → 40px, padding compact
- `.terminal-sidebar`: use `var(--canvas-surface)` for bg
- `.terminal-stage`: padding from 24px → 16px
- `.step-item`: remove `transition: color 0.15s` → instant
- `.btn-terminal`: remove `transition: all 0.15s`, use instant hover
- `.btn-next-step`: 
  - Remove `linear-gradient` → flat `var(--accent-primary)` background
  - Remove `box-shadow` → none
  - Remove `transform: translateY(-1px)` on hover
  - Remove `transition: all 0.2s ease` → instant
  - Border-radius from 8px → 6px
- `.summary-box`: padding from 20px 24px → 12px 16px, margin-bottom from 20px → 12px
- `.terminal-table`: border colors use tokens
- `.loading-overlay`: remove `backdrop-filter: blur(4px)` → none
- `.loading-spinner`: border 3px → 2px (thinner)
- Mobile responsive: update hardcoded colors to token references
- All `.transition-*` classes: reduce to `transition-duration: 0s` or remove

### 5. `frontend/src/components/ui/card.tsx`
Changes:
- Remove `shadow-[var(--shadow-md)]` → no shadow class
- Keep `border border-[var(--border-default)]` — this is the depth indicator
- Reduce CardHeader padding from `p-4` → `p-3`
- Reduce CardContent padding from `p-4 pt-0` → `p-3 pt-0`

### 6. `frontend/src/components/ui/table.tsx`
Changes:
- Add `lining-nums` to `fontVariantNumeric` inline style: `'tabular-nums lining-nums'`
- Update `fontFeatureSettings` to `"tnum" on, "lnum" on`
- Reduce TableHead height from `h-8` → `h-7`
- Reduce TableCell padding from `px-3 py-2` → `px-2.5 py-1.5`
- TableRow hover: use `border-subtle` token (already does, confirm)

### 7. `frontend/src/components/ui/badge.tsx`
- Already minimal, no changes needed. Uses token colors correctly.

### 8. `frontend/src/components/ui/skeleton.tsx`
- Remove any animation/transition if present

### 9. `frontend/src/components/ui/tooltip.tsx`
- Ensure uses token borders, no shadows

## Implementation Order

1. `tokens.css` — Foundation of all visual parameters
2. `typography.css` — Font system and numeric alignment
3. `index.css` — Shell layout, buttons, tables, overlays
4. `card.tsx` — Remove shadows
5. `table.tsx` — Enforce tabular alignment + compact
6. Verify build compiles clean

## Verification

After all changes:
1. Run `cd frontend && npm run build` to ensure no compilation errors
2. Visual check: all borders should be 1px sharp lines at `#2d3139`
3. Visual check: all numbers should use Geist Mono with tabular-nums lining-nums
4. Visual check: zero box-shadows anywhere in the rendered DOM
5. Visual check: hover states are instant (no transition delay)
