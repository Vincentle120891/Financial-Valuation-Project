/**
 * CENTRALIZED COMPONENT PROP TYPE DEFINITIONS
 * 
 * This file serves as the single source of truth for prop contracts across the application.
 * Every component should import and use these definitions to ensure consistency.
 * 
 * BENEFITS:
 * - Single point to update shared prop structures
 * - Prevents naming mismatches (e.g., suggestedPeers vs discoveredPeers)
 * - Enables IDE autocomplete for prop names
 * - Catches missing/incorrect props at runtime
 * 
 * USAGE:
 * import PropTypes from 'prop-types';
 * import { PeerSelectionStepProps } from '@/types/componentPropTypes';
 * 
 * MyComponent.propTypes = PeerSelectionStepProps;
 */

import PropTypes from 'prop-types';

// ============================================================================
// PEER-RELATED PROPS
// ============================================================================

/**
 * Single peer object structure
 * Used by: PeerSelectionStep, PeerList, etc.
 */
export const PeerShape = PropTypes.shape({
  ticker: PropTypes.string,
  symbol: PropTypes.string,
  name: PropTypes.string,
  companyName: PropTypes.string,
  industry: PropTypes.string,
  matchScore: PropTypes.number,
  similarityScore: PropTypes.number,
  reasons: PropTypes.arrayOf(PropTypes.string),
  marketCap: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  country: PropTypes.string,
});

/**
 * Peer Selection Step Props
 * Parent: ValuationFlow.jsx
 * Used by: PeerSelectionStep.jsx
 * 
 * NOTE: Use 'discoveredPeers' consistently (not suggestedPeers, foundPeers, etc.)
 */
export const PeerSelectionStepProps = {
  discoveredPeers: PropTypes.arrayOf(PeerShape).isRequired,
  selectedPeers: PropTypes.arrayOf(PropTypes.string),
  onTogglePeer: PropTypes.func.isRequired,
  onSelectAll: PropTypes.func,
  onContinue: PropTypes.func.isRequired,
  onBack: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  onFindPeers: PropTypes.func,
  selectedCompany: PropTypes.shape({
    ticker: PropTypes.string,
    name: PropTypes.string,
  }),
  market: PropTypes.string,
};

// ============================================================================
// VALUATION STEP PROPS
// ============================================================================

/**
 * Valuation Results Step Props
 * Used by: ResultsStep.jsx
 */
export const ValuationResultsProps = {
  valuationData: PropTypes.shape({
    enterpriseValue: PropTypes.number,
    basePrice: PropTypes.number,
    valuationRange: PropTypes.shape({
      low: PropTypes.number,
      high: PropTypes.number,
    }),
    methods: PropTypes.arrayOf(PropTypes.string),
  }),
  selectedPeers: PropTypes.arrayOf(PropTypes.string),
  valuation: PropTypes.object,
  scenarioAnalysis: PropTypes.object,
};

// ============================================================================
// COMPANY DATA PROPS
// ============================================================================

/**
 * Company Selection Props
 * Used by: CompanySelectionStep.jsx, HistoricalDataExtractionStep.jsx
 */
export const CompanyShape = PropTypes.shape({
  ticker: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  exchange: PropTypes.string,
  country: PropTypes.string,
  industry: PropTypes.string,
  sector: PropTypes.string,
  marketCap: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
});

export const CompanySelectionProps = {
  selectedCompany: CompanyShape.isRequired,
  companies: PropTypes.arrayOf(CompanyShape),
  onSelectCompany: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string,
};

// ============================================================================
// COMMON STEP NAVIGATION PROPS
// ============================================================================

/**
 * Common props for all valuation flow steps
 * All steps should include these
 */
export const StepNavigationProps = {
  onContinue: PropTypes.func.isRequired,
  onBack: PropTypes.func,
  loading: PropTypes.bool,
  error: PropTypes.string,
  disabled: PropTypes.bool,
};

// ============================================================================
// FORM/INPUT PROPS
// ============================================================================

export const FormInputProps = {
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func,
  error: PropTypes.string,
  disabled: PropTypes.bool,
  placeholder: PropTypes.string,
  label: PropTypes.string,
  required: PropTypes.bool,
};

// ============================================================================
// DOCUMENTATION
// ============================================================================

/**
 * COMPONENT PROP NAMING CONVENTIONS
 * 
 * 1. PEER-RELATED TERMS (BE CONSISTENT!)
 *    ✓ USE: discoveredPeers, foundPeers, selectedPeers
 *    ✗ AVOID: suggestedPeers, recommendedPeers (use one consistently per context)
 * 
 * 2. CALLBACK NAMING
 *    - on{Action}: onSelectPeer, onFindPeers, onContinue, onBack
 *    - handle{Action}: Reserved for internal component methods
 * 
 * 3. BOOLEAN NAMING
 *    - Use present tense: isLoading, isSaving, hasError
 *    - Or: loading, saving, error (single word acceptable for common ones)
 * 
 * 4. ARRAY/COLLECTION NAMING
 *    - Use plural: peers, companies, results
 *    - Be specific: selectedPeers (not selectedPeersList, selectedPeerArray)
 * 
 * 5. OPTIONAL VS REQUIRED
 *    - Mark with .isRequired if truly required
 *    - Provide sensible defaults (e.g., loading = false, selectedPeers = [])
 * 
 * COMMON MISTAKES TO AVOID:
 * - ✗ suggestedPeers in parent, discoveredPeers in child
 * - ✗ onUpdate vs onchange vs onChange
 * - ✗ data vs results vs valuationData
 * - ✗ peer vs company (mixing entity types)
 */
