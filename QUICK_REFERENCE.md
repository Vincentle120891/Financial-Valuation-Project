# Quick Reference: Prop Naming Best Practices

## The Problem (You Had This)
```
✗ Parent: suggestedPeers={peers}
✗ Child:  discoveredPeers = []
↓
Result: Empty array, component breaks
```

## The Solution (You Have This Now)
```
✓ Central registry: componentPropTypes.js
✓ PropTypes validation: Component.propTypes = 
✓ Runtime warnings: Browser console catches errors
```

---

## Naming Standards (USE THESE)

### Peer Collections
| Use This | NOT This |
|----------|----------|
| `discoveredPeers` | suggestedPeers, foundPeers, recommendedPeers |
| `selectedPeers` | chosenPeers, pickedPeers, activePeers |
| `availablePeers` | allPeers, peerList, peers (ambiguous) |

### Callbacks
| Use This | NOT This |
|----------|----------|
| `onSelectPeer()` | handleSelect(), select() |
| `onFindPeers()` | find(), handleFind() |
| `onContinue()` | next(), handleNext() |
| `onTogglePeer()` | toggle(), select() |

### Booleans
| Use This | NOT This |
|----------|----------|
| `loading` | isLoading, isLoad, load |
| `disabled` | isDisabled, disable, isDisable |
| `error` | hasError, errors (ambiguous) |

### Collections
| Use This | NOT This |
|----------|----------|
| `peers` | peersList, peerArray, data |
| `companies` | companyList, items, list |
| `results` | resultsList, output, data |

---

## Checklist: Adding a Component

- [ ] Define props in `componentPropTypes.js`
- [ ] Import PropTypes in component
- [ ] Add `Component.propTypes =` assignment
- [ ] Add `Component.defaultProps =` for optional props
- [ ] Parent uses exact prop names from registry
- [ ] Run audit: `node frontend/scripts/audit-props.js`
- [ ] Test in browser console for warnings

---

## Template (Copy & Paste)

```javascript
import React from 'react';
import PropTypes from 'prop-types';
import { ComponentNameProps } from '@/types/componentPropTypes';

const ComponentName = ({ requiredProp, optionalProp = null }) => {
  return <div>{requiredProp}</div>;
};

ComponentName.propTypes = ComponentNameProps;
ComponentName.defaultProps = {
  optionalProp: null,
};

export default ComponentName;
```

---

## Debug: Prop Not Working?

1. **Check prop name spelling** - Must match componentPropTypes.js exactly
2. **Look at browser console** - Should show "Failed prop type" warning
3. **Verify parent passes it** - `<Component propName={value} />`
4. **Check PropTypes definition** - Is it `.isRequired`?

---

## Compliance Check

```bash
# See which components need PropTypes
node frontend/scripts/audit-props.js

# Build with validation
npm run build

# Test in browser
npm run dev
# Open F12 → Console → look for warnings
```

---

## Files to Know

| File | Purpose |
|------|---------|
| `componentPropTypes.js` | Central registry - all prop definitions |
| `PROP_CONTRACT_GUIDE.md` | Full developer guide |
| `IMPLEMENTATION_ROADMAP.md` | Step-by-step completion guide |
| `SOLUTION_SUMMARY.md` | Big picture overview |
| `COMPONENT_TEMPLATE.jsx` | Copy-paste template |

---

## Most Common Mistakes

❌ `suggestedPeers` in parent, `discoveredPeers` in child
→ **Use registry to keep names consistent**

❌ Forgetting `.propTypes =` on component
→ **No validation happens without this**

❌ Typo in prop name: `discoverd_Peers` vs `discoveredPeers`
→ **PropTypes catches these! Check console.**

❌ Required prop not passed by parent
→ **Browser console warns, check it!**

❌ Wrong type: passing string instead of array
→ **PropTypes validates types too**

---

## Success Criteria

✓ Zero naming mismatches between parent & child  
✓ Browser console shows NO prop warnings  
✓ `node frontend/scripts/audit-props.js` shows 100% compliance  
✓ New components follow template pattern  
✓ Code reviews check prop contracts  

---

Created: 2026-06-02  
Status: Ready for Implementation  
Next: See IMPLEMENTATION_ROADMAP.md
