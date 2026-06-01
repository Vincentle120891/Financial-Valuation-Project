# Implementation Roadmap: Prevent Prop Naming Mismatches

## Executive Summary

Your project had **14 components without PropTypes validation** and only **1 with validation** (7% compliance). This led to the `suggestedPeers` vs `discoveredPeers` bug.

**Solution**: Add PropTypes to all components using the centralized registry in `src/types/componentPropTypes.js`.

**Time to implement**: ~2-3 hours (one person) or ~30 min with parallel work

---

## What's Already Done ✅

- ✅ Installed `prop-types` package
- ✅ Created centralized `src/types/componentPropTypes.js` with shared prop definitions
- ✅ Updated `PeerSelectionStep.jsx` with PropTypes validation
- ✅ Created `COMPONENT_TEMPLATE.jsx` as a reference
- ✅ Created audit script `frontend/scripts/audit-props.js`

---

## Implementation Steps

### Phase 1: Extend componentPropTypes.js (Add Missing Prop Definitions)

For each component below, add its prop types to `src/types/componentPropTypes.js`:

```javascript
// Example: Adding CompanySelectionStep props
export const CompanySelectionStepProps = {
  companies: PropTypes.arrayOf(CompanyShape),
  selectedCompany: CompanyShape.isRequired,
  onSelectCompany: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string,
};

export const ApiDataStepProps = {
  selectedCompany: CompanyShape,
  onDataLoad: PropTypes.func.isRequired,
  onContinue: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  // ... etc
};
```

**Components needing prop definitions:**
1. ✓ PeerSelectionStep (DONE)
2. ApiKeyModal
3. ApiDataStep
4. AssumptionsStep
5. CompanySelectionStep
6. DataFieldDisplay
7. ForecastDriversStep
8. HistoricalDataExtractionStep
9. InternationalMarketData
10. ModelSelectionStep
11. RequirementsStep
12. ResultsStep
13. RunValuationStep
14. SearchStep
15. VietnameseMarketData

### Phase 2: Add PropTypes to Each Component

For each component file, add these 3 lines at the bottom:

```javascript
// 1. Import at top
import PropTypes from 'prop-types';
import { ComponentNameProps } from '@/types/componentPropTypes';

// 2. At bottom of file before export
ComponentName.propTypes = ComponentNameProps;
ComponentName.defaultProps = {
  optionalField: null,
  // ...
};

// 3. Export
export default ComponentName;
```

### Phase 3: Verify & Test

After each component:
1. Run the audit script: `node frontend/scripts/audit-props.js`
2. Open browser console while running the app
3. Look for PropTypes warnings (e.g., "Failed prop type: ...")
4. Fix any mismatches between parent and child

---

## Before & After Examples

### Example 1: ApiKeyModal.jsx

**BEFORE (No validation)**
```javascript
const ApiKeyModal = ({ 
  isOpen,  // Maybe it's called 'open' in parent?
  onClose, // Maybe it's called 'handleClose' in parent?
  onSave   // Maybe it's called 'onApiKey' in parent?
}) => {
  return <div>...</div>;
};

export default ApiKeyModal;
```

**AFTER (With validation)**
```javascript
import PropTypes from 'prop-types';
import { ApiKeyModalProps } from '@/types/componentPropTypes';

const ApiKeyModal = ({ isOpen, onClose, onSave }) => {
  return <div>...</div>;
};

ApiKeyModal.propTypes = ApiKeyModalProps;
ApiKeyModal.defaultProps = {
  isOpen: false,
};

export default ApiKeyModal;
```

**componentPropTypes.js**
```javascript
export const ApiKeyModalProps = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
};
```

### Example 2: CompanySelectionStep.jsx

**BEFORE**
```javascript
const CompanySelectionStep = ({
  companies,
  selected,  // ❌ Is it 'selected', 'selectedCompany', 'activeCompany'?
  onSelect,
  loading
}) => {
  // ...
};

export default CompanySelectionStep;
```

**AFTER**
```javascript
import PropTypes from 'prop-types';
import { CompanySelectionStepProps } from '@/types/componentPropTypes';

const CompanySelectionStep = ({
  companies,
  selectedCompany,  // ✓ Clear, consistent naming
  onSelectCompany,
  loading
}) => {
  // ...
};

CompanySelectionStep.propTypes = CompanySelectionStepProps;
CompanySelectionStep.defaultProps = {
  companies: [],
  selectedCompany: null,
  loading: false,
};

export default CompanySelectionStep;
```

**componentPropTypes.js**
```javascript
export const CompanySelectionStepProps = {
  companies: PropTypes.arrayOf(CompanyShape),
  selectedCompany: CompanyShape,
  onSelectCompany: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};
```

---

## Step-by-Step: Add PropTypes to One Component

Let's add PropTypes to `CompanySelectionStep.jsx`:

### Step 1: Identify all props the component accepts
```javascript
const CompanySelectionStep = ({
  companies,           // Array of companies
  selectedCompany,    // Currently selected company
  onSelectCompany,    // Callback when user selects a company
  loading,            // Is data loading?
  error,              // Error message if any
}) => {
  // ...
};
```

### Step 2: Add to componentPropTypes.js
```javascript
export const CompanySelectionStepProps = {
  companies: PropTypes.arrayOf(CompanyShape),
  selectedCompany: CompanyShape,
  onSelectCompany: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string,
};
```

### Step 3: Import in component
```javascript
import PropTypes from 'prop-types';
import { CompanySelectionStepProps } from '@/types/componentPropTypes';
```

### Step 4: Add validation at bottom of file
```javascript
CompanySelectionStep.propTypes = CompanySelectionStepProps;
CompanySelectionStep.defaultProps = {
  companies: [],
  selectedCompany: null,
  loading: false,
  error: null,
};

export default CompanySelectionStep;
```

### Step 5: Test
```bash
# Run the app
npm run dev

# Open browser console - look for PropTypes warnings
# Update parent component if props don't match

# Run audit script
node frontend/scripts/audit-props.js
```

---

## Quick Reference: Common Prop Patterns

### Arrays
```javascript
companies: PropTypes.arrayOf(CompanyShape),
selectedPeers: PropTypes.arrayOf(PropTypes.string),
```

### Objects
```javascript
selectedCompany: CompanyShape,
valuation: PropTypes.shape({
  basePrice: PropTypes.number,
  range: PropTypes.shape({ low: PropTypes.number, high: PropTypes.number }),
}),
```

### Callbacks
```javascript
onSelectCompany: PropTypes.func.isRequired,
onContinue: PropTypes.func,
```

### Booleans
```javascript
loading: PropTypes.bool,
disabled: PropTypes.bool,
isOpen: PropTypes.bool,
```

### Strings & Numbers
```javascript
error: PropTypes.string,
title: PropTypes.string.isRequired,
percentage: PropTypes.number,
```

### Optional vs Required
```javascript
PropTypes.string           // Optional
PropTypes.string.isRequired // Required (must be provided)
```

---

## Rollout Plan

### Option A: One Person (Parallel)
- Session 1: Add prop types to componentPropTypes.js (30 min)
- Session 2: Batch add PropTypes to all 14 components (90 min)
- Session 3: Test and fix any mismatches (30 min)

### Option B: Team (Parallel)
- Developer 1: Defines prop types in componentPropTypes.js
- Developers 2-4: Each take 4-5 components and add PropTypes
- Leads to 90% faster completion

---

## Verification Checklist

Before considering this complete:

- [ ] Installed prop-types: `npm list prop-types`
- [ ] All 14 components have PropTypes validation
- [ ] Audit script shows 100% compliance: `node frontend/scripts/audit-props.js`
- [ ] Browser console shows NO PropTypes warnings
- [ ] App runs without errors
- [ ] All valuation flow steps work end-to-end
- [ ] No prop mismatches between parent and children

---

## Prevention Going Forward

### For New Components:
1. Copy `src/components/COMPONENT_TEMPLATE.jsx`
2. Add prop type definition to `componentPropTypes.js`
3. Use PropTypes in component
4. Test in browser

### For Code Reviews:
Checklist for reviewing components:
- [ ] Does component import PropTypes?
- [ ] Are PropTypes defined at bottom of file?
- [ ] Are prop names consistent with registry?
- [ ] Are required props marked `.isRequired`?
- [ ] Are defaults provided where needed?
- [ ] Does parent pass all required props?

### For Debugging Prop Issues:
1. Open browser console (F12)
2. Look for red "Warning: Failed prop type" messages
3. Message shows which prop is wrong and why
4. Fix the parent component or child definition

---

## Files Modified/Created

- ✅ `frontend/src/types/componentPropTypes.js` - Centralized prop definitions
- ✅ `frontend/src/components/valuation-flow/PeerSelectionStep.jsx` - Added PropTypes
- ✅ `frontend/src/components/COMPONENT_TEMPLATE.jsx` - Reference template
- ✅ `frontend/scripts/audit-props.js` - Compliance audit script
- ✅ `PROP_CONTRACT_GUIDE.md` - Developer guide
- ✅ `IMPLEMENTATION_ROADMAP.md` - This file (you are here)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| PropTypes warnings still appearing | Check prop names match componentPropTypes.js exactly |
| Component won't render | Check browser console for "Failed prop type" messages |
| Can't find component PropTypes | May not be defined yet in componentPropTypes.js |
| Old components still broken | PropTypes only warns, doesn't fix existing bugs - also check parent passes correct props |

---

## Resources

- [PropTypes Official Docs](https://github.com/facebook/prop-types)
- [PROP_CONTRACT_GUIDE.md](./PROP_CONTRACT_GUIDE.md)
- [Centralized Prop Types](./frontend/src/types/componentPropTypes.js)
- [Example Component](./frontend/src/components/valuation-flow/PeerSelectionStep.jsx)
