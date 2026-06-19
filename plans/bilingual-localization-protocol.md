# Bilingual Vietnamese/English Localization Protocol — Implementation Plan

## Current State Analysis

- **i18n infrastructure exists but is UNUSED**: `i18next` + `react-i18next` installed, `vi.js` (336 lines) and `en.js` (130 lines) exist, `index.js` configured — but `useTranslation` is never imported in any component
- **`index.jsx` does not import i18n** — The module is never initialized
- **All text is hardcoded English in JSX** — Step components, DataFieldDisplay, buttons, headers all have inline English strings
- **Translation file structures are misaligned**: `en.js` uses flat keys, `vi.js` uses nested objects
- **ThemeToggle exists** at `components/ThemeToggle.jsx` — reference pattern for creating LanguageToggle

## Architecture Decisions

### 1. Translation Mask Law — Zero Data Contamination
The language layer is a **UI mask only**. Financial line items, data strings, currency values, formula names, ticker codes, and calculation states are NEVER translated. This is enforced by:
- Keeping all chart/data/financial status labels in English (RETRIEVED, CALCULATED, MISSING, etc.)
- Only wrapping structural UI wrappers (page headers, buttons, navigation, step titles, section labels) in translation functions
- Financial acronyms WACC, EBITDA, DCF, P/E, EPS, CAGR, Beta, VaR remain English uppercase in all views

### 2. Density Protection Law
Vietnamese text is 30-50% longer. To prevent layout breaking:
- Use concise Vietnamese corporate terminology (e.g., 'Doanh thu' not 'Tổng doanh thu bán hàng')
- Core acronyms stay English in data grids
- All financial table headers keep their English abbreviations (P/E, P/B, EV/EBITDA)

### 3. System No-Conversion Notice
Every localized view includes a low-contrast notice in Geist Mono at 10px:
- VN: "Lưu ý: Giao diện ngôn ngữ được bản địa hóa cho mục đích hiển thị. Các chỉ số tài chính, thuật ngữ chuyên ngành và tính toán số liệu được giữ nguyên theo tiêu chuẩn báo cáo quốc tế."
- EN: "Notice: Language translation applies to UI wrappers only. Core financial terminology, tickers, and mathematical outputs remain anchored to international reporting standards."

## Files to Create/Modify

### New Files to Create

#### 1. `frontend/src/i18n/en.js` — Complete Rewrite
Align structure with vi.js nested format. Add all UI wrapper strings used across components:
- `common.*` — General button/action labels
- `nav.*` — Navigation items
- `steps.*` — Step titles and descriptions (1-11)
- `sections.*` — Section headers (Balance Sheet → Bảng Cân đối Kế toán, etc.)
- `metrics.*` — Structural UI labels for financial metrics (NOT data values)
- `buttons.*` — Button labels (Search, Fetch, Confirm, etc.)
- `notices.*` — System notices including the Translation Mask disclaimer

#### 2. `frontend/src/i18n/vi.js` — Rewrite
Same nested structure as en.js. Add Vietnamese corporate finance terminology per the glossary mapping:
- Balance Sheet → Bảng Cân đối Kế toán
- Income Statement → Báo cáo Kết quả Kinh doanh
- Cash Flow Statement → Báo cáo Lưu chuyển Tiền tệ
- Assumptions / Inputs → Giả định Mô hình
- Growth Rate → Tốc độ Tăng trưởng
- Discount Factor → Hệ số Chiết khấu
- Watchlist → Danh mục Theo dõi

#### 3. `frontend/src/components/LanguageToggle.jsx` — New Component
Modeled after `ThemeToggle.jsx`:
- Globe/Flag icon toggle between EN ↔ VI
- Uses `i18n.changeLanguage()` from react-i18next
- Saves preference to `localStorage`
- Placed in the top nav bar next to ThemeToggle

#### 4. `frontend/src/components/TranslationNotice.jsx` — New Component
Renders the system no-conversion disclaimer:
- Font: Geist Mono (`var(--font-mono)`)
- Size: 10px
- Color: `var(--text-tertiary)` (low contrast)
- Rendered at the bottom of each step view or in the footer area

### Files to Modify

#### 5. `frontend/src/index.jsx` — Add i18n Import
```js
import './i18n'; // Initialize i18n before app renders
```

#### 6. `frontend/src/i18n/index.js` — Update Config
- Add `localStorage` language persistence
- Ensure `react-i18next` language detector is configured
- Default language from browser or localStorage

#### 7. `frontend/src/components/ValuationFlow.tsx` — Integrate i18n
- Import `useTranslation`
- Wrap step titles, nav items, section headers with `t()` calls
- Add TranslationNotice at the bottom of each step
- Add LanguageToggle in the header/nav area

#### 8. Step Components (Priority Order)
Each step component gets `useTranslation` and replaces hardcoded UI strings:
- `step1_search_step.tsx` — Header, placeholder, market toggle labels
- `step2_company_selection_step.tsx` — Header, section titles
- `step3_model_selection_step.tsx` — Model names, selection labels
- `step4_peer_selection_step.tsx` — Headers, button labels
- `step5_requirements_step.tsx` — Section headers, input labels
- `step6_api_data_step.tsx` — Category labels, status labels (KEEP data status in English)
- `step7_historical_data_step.tsx` — Headers, action labels
- `step8_forecast_drivers_step.tsx` — Section headers, button labels
- `step9_assumptions_step.tsx` — Headers, field labels
- `step10_run_valuation_step.tsx` — Headers, action labels
- `step11_results_step.tsx` — Headers, summary labels

#### 9. Shared Components
- `DataFieldDisplay.tsx` — Keep status badges in English (RETRIEVED, CALCULATED, MISSING, etc.) per Translation Mask Law
- `FootballFieldChart.tsx` — Keep method names in English (DCF, COMPS, DUPONT)
- `SensitivityHeatmap.tsx` — No translation needed (pure data grid)
- `ProcessingOverlay.tsx` — Translate loading messages only

## UI Glossary Mapping (Translation Rules)

| English (UI Wrapper) | Vietnamese (UI Wrapper) | Translate? |
|---|---|---|
| Balance Sheet | Bảng Cân đối Kế toán | YES |
| Income Statement | Báo cáo Kết quả Kinh doanh | YES |
| Cash Flow Statement | Báo cáo Lưu chuyển Tiền tệ | YES |
| Assumptions / Inputs | Giả định Mô hình | YES |
| Growth Rate | Tốc độ Tăng trưởng | YES |
| Discount Factor | Hệ số Chiết khấu | YES |
| Watchlist | Danh mục Theo dõi | YES |
| Revenue | Doanh thu | YES |
| Net Income | Lợi nhuận ròng | YES |
| Market Cap | Vốn hóa | YES |
| WACC | WACC | NO — stays English |
| EBITDA | EBITDA | NO — stays English |
| DCF | DCF | NO — stays English |
| P/E | P/E | NO — stays English |
| Beta | Beta | NO — stays English |
| RETRIEVED | RETRIEVED | NO — data status |
| CALCULATED | CALCULATED | NO — data status |
| MISSING | MISSING | NO — data status |

## Implementation Order

1. Align `en.js` and `vi.js` structures (same nested keys)
2. Update `i18n/index.js` with language persistence
3. Add i18n import to `index.jsx`
4. Create `LanguageToggle.jsx`
5. Create `TranslationNotice.jsx`
6. Wire i18n into `ValuationFlow.tsx` (parent component)
7. Migrate step1 → step11 components (one at a time)
8. Add TranslationNotice to each step
9. Run `npm run build` to verify

## Verification

1. `npm run build` compiles with 0 errors
2. Toggle EN → VI: all structural UI text changes, financial data unchanged
3. Toggle VI → EN: all text reverts to English
4. Language persists across page reloads (localStorage)
5. Translation Notice visible in both languages at 10px Geist Mono
6. Financial data grids (sensitivity, historical statements) display identical values in both modes
7. Vietnamese text does not clip or overflow in high-density areas
