# Component Prop Contract Standards

## Problem: Prop Naming Mismatches

Your project had a recurring bug where parent and child components used different prop names:

```jsx
// ❌ WRONG - Parent and child don't match
// ValuationFlow.jsx (parent)
<PeerSelectionStep suggestedPeers={suggestedPeers} />

// PeerSelectionStep.jsx (child)
const PeerSelectionStep = ({ discoveredPeers = [] }) => { ... }

// Result: discoveredPeers is always empty! 🐛
```

This happens because components are developed independently without a shared interface contract.

---

## Solution: Centralized Prop Type Registry

### Step 1: Define All Props in One Place

All component prop types are centralized in: **`src/types/componentPropTypes.js`**

```javascript
// ✓ CORRECT - Consistent naming across the app
export const PeerSelectionStepProps = {
  discoveredPeers: PropTypes.arrayOf(PeerShape).isRequired,
  selectedPeers: PropTypes.arrayOf(PropTypes.string),
  onTogglePeer: PropTypes.func.isRequired,
  // ... rest of props
};
```

### Step 2: Use PropTypes on All Components

Every component MUST declare prop validation:

```javascript
import PropTypes from 'prop-types';
import { PeerSelectionStepProps } from '@/types/componentPropTypes';

const PeerSelectionStep = ({ discoveredPeers, selectedPeers, ... }) => {
  // Component logic
};

// ✓ ADD THIS
PeerSelectionStep.propTypes = PeerSelectionStepProps;
PeerSelectionStep.defaultProps = {
  discoveredPeers: [],
  selectedPeers: [],
  // ...
};

export default PeerSelectionStep;
```

### Step 3: Use Consistent Prop Names

**Parent → Child Prop Naming Must Match:**

```javascript
// ✓ CORRECT
// Parent (ValuationFlow.jsx)
<PeerSelectionStep discoveredPeers={suggestedPeers} />

// Child (PeerSelectionStep.jsx)
const PeerSelectionStep = ({ discoveredPeers = [] }) => { ... }
```

---

## Naming Conventions

### Peer-Related Props (Choose ONE - use consistently!)

| Purpose | Use This | ❌ NOT This |
|---------|----------|-----------|
| Peers found by algorithm | `discoveredPeers` | suggestedPeers, foundPeers, recommendedPeers |
| User-selected peers | `selectedPeers` | chosenPeers, pickedPeers |
| All peer options | `availablePeers` | peerList, peers (ambiguous) |

### Callback Functions (Action Verbs)

```javascript
// ✓ CORRECT patterns
onTogglePeer()      // Toggle selection of single peer
onSelectAll()       // Select all peers
onFindPeers()       // Trigger peer search
onContinue()        // Move to next step
onBack()            // Go back to previous step
onUpdateValue()     // Generic update handler

// ❌ WRONG patterns
handleSelectPeer()           // Use 'on' prefix for props
toggle()                     // Vague - toggle what?
findPeersAgain()            // Use 'on' for callbacks
updatePeers()               // Which peers? How update?
```

### Boolean Props

```javascript
// ✓ CORRECT
loading, isLoading
error, hasError
disabled, isDisabled
visible, isVisible

// ❌ WRONG
load, isLoad
errors (array vs boolean confusion)
disable
show
```

### Arrays/Collections

```javascript
// ✓ CORRECT - clear, singular concept
discoveredPeers, selectedPeers, companies, results

// ❌ WRONG - ambiguous or redundant
peerList, peersArray, data, list, items
```

---

## Quick Checklist: Adding a New Component

Before adding a component to the valuation flow, follow this checklist:

- [ ] **Define prop types** in `src/types/componentPropTypes.js`
  ```javascript
  export const MyComponentProps = {
    requiredProp: PropTypes.string.isRequired,
    optionalProp: PropTypes.number,
  };
  ```

- [ ] **Add PropTypes validation** to component
  ```javascript
  MyComponent.propTypes = MyComponentProps;
  MyComponent.defaultProps = { optionalProp: 0 };
  ```

- [ ] **Document in JSDoc** what each prop does
  ```javascript
  /**
   * MyComponent
   * 
   * @prop {string} requiredProp - Description of what this does
   * @prop {number} optionalProp - Optional description
   */
  ```

- [ ] **Use exact prop names** when passing from parent
  ```javascript
  // Match the prop name EXACTLY from componentPropTypes
  <MyComponent requiredProp="value" optionalProp={123} />
  ```

- [ ] **Test prop validation** by temporarily passing wrong types
  ```javascript
  // In development only - verify console warns about prop type errors
  <MyComponent requiredProp={123} /> // Should warn: expected string
  <MyComponent /> // Should warn: required prop missing
  ```

---

## Runtime Validation In Action

PropTypes will show **console warnings** (development only) if:

1. **Required prop missing**
   ```
   Warning: Failed prop type: The prop `discoveredPeers` is marked as required in `PeerSelectionStep`, but its value is `undefined`.
   ```

2. **Wrong prop type**
   ```
   Warning: Failed prop type: Invalid prop `selectedPeers` of type `object` supplied to `PeerSelectionStep`, expected an array.
   ```

3. **Typo in prop name** (gets ignored silently, component won't work)
   ```javascript
   // ❌ WRONG - typo in prop name
   <PeerSelectionStep discoverd_Peers={[]} />  // Will be ignored!
   <PeerSelectionStep discoveredPeers={[]} />   // ✓ Correct
   ```

---

## Before & After: The Fix

### BEFORE (Bug)
```javascript
// ValuationFlow.jsx
<PeerSelectionStep suggestedPeers={suggestedPeers} />

// PeerSelectionStep.jsx
const PeerSelectionStep = ({ discoveredPeers = [] }) => {
  // discoveredPeers is undefined! Shows "No Peers Discovered Yet"
};
```

### AFTER (Fixed)
```javascript
// componentPropTypes.js - Define once
export const PeerSelectionStepProps = {
  discoveredPeers: PropTypes.arrayOf(PeerShape).isRequired,
  // ...
};

// PeerSelectionStep.jsx - Use definition
PeerSelectionStep.propTypes = PeerSelectionStepProps;

// ValuationFlow.jsx - Pass with correct name
<PeerSelectionStep discoveredPeers={suggestedPeers} />  // ✓ Works!
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Component shows nothing / renders empty | Check browser console for prop type warnings; verify prop names match `componentPropTypes.js` |
| "Cannot read property X of undefined" | A required prop is missing; check it's passed from parent |
| Props not updating component | Check prop name spelling matches exactly |
| PropTypes warnings in console | Types don't match definition; fix type or data source |

---

## References

- **PropTypes Docs**: https://github.com/facebook/prop-types
- **Centralized Types**: `src/types/componentPropTypes.js`
- **Example Component**: `src/components/valuation-flow/PeerSelectionStep.jsx`
- **Example Parent**: `src/components/ValuationFlow.jsx` (lines 1080-1090)

---

## For Code Reviews

When reviewing PRs with component changes:

✓ Do the prop names match the registry in `componentPropTypes.js`?
✓ Are PropTypes declared on the component?
✓ Are all required props provided by the parent?
✓ Do types match (array vs string, callback vs value, etc.)?
✓ Are defaults provided for optional props?

Use this checklist to catch mismatches **before** they cause bugs!
