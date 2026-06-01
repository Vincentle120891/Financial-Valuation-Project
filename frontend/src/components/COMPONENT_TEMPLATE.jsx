/**
 * COMPONENT TEMPLATE WITH PROPTYPES
 * 
 * Copy this template for all new components to ensure prop validation
 * from day one. This prevents naming mismatches like suggestedPeers vs
 * discoveredPeers.
 */

import React from 'react';
import PropTypes from 'prop-types';
import { ComponentNameProps } from '@/types/componentPropTypes';

/**
 * ComponentName - Description
 * 
 * Purpose: What does this component do?
 * Parent: Which component renders this?
 * Integration: How does it fit in the flow?
 * 
 * PROP CONTRACT: Uses centralized types from componentPropTypes.js
 * This ensures consistency and prevents naming mismatches.
 */
const ComponentName = ({ 
  requiredProp, 
  optionalProp = defaultValue,
  onAction,
}) => {
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
};

// ============================================================================
// PROP TYPE VALIDATION
// ============================================================================

// Option A: Use centralized prop types (PREFERRED)
ComponentName.propTypes = ComponentNameProps;

// Option B: Define inline (if prop types don't exist in registry yet)
// ComponentName.propTypes = {
//   requiredProp: PropTypes.string.isRequired,
//   optionalProp: PropTypes.number,
//   onAction: PropTypes.func.isRequired,
// };

// Default values for optional props
ComponentName.defaultProps = {
  optionalProp: 0,
  // Don't provide defaults for required props!
};

export default ComponentName;

// ============================================================================
// MIGRATION CHECKLIST
// ============================================================================
// 
// When adding PropTypes to existing component:
// 
// [ ] Import PropTypes and types
// [ ] Add ComponentName.propTypes assignment
// [ ] Add ComponentName.defaultProps if needed
// [ ] Test in browser - check console for prop warnings
// [ ] Update componentPropTypes.js if types don't exist yet
// [ ] Update parent component to pass all required props
// [ ] Remove any prop destructuring defaults that are now in defaultProps
// [ ] Test component with wrong prop types to verify warnings appear
//
