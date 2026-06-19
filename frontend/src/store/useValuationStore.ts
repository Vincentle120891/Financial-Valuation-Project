/**
 * useValuationStore - Zustand Store for ValuationFlow
 *
 * 3 Slices:
 *   1. Workflow: currentStep, market, loading, errors, etc.
 *   2. Session & Company: selectedCompany, peers, requiredFields, etc.
 *   3. Data Matrix: valuationsData, forecastDriversData, dcfInputsData, valuationResults
 *
 * Matrix helpers are methods on the store, not stored state.
 * Action modules import this store and use getState()/setState().
 */

import { create } from 'zustand';

// ─── Types ──────────────────────────────────────────────────────────────────

interface MatrixSlot {
  dcf: any;
  dupont: any;
  comps: any;
}

interface MatrixStore {
  international: MatrixSlot;
  vietnam: MatrixSlot;
}

interface MarketValidation {
  isValid: boolean;
  message: string;
  selectedMarket: string;
  isLocked: boolean;
}

interface ValuationState {
  // ─── Slice 1: Workflow ──────────────────────────────────────────────────
  currentStep: number;
  maxReachedStep: number;
  market: 'international' | 'vietnam';
  marketValidation: MarketValidation;
  searchQuery: string;
  searchResults: any[];
  selectedModel: string; // alias kept for component convenience (same as selectedModels)
  selectedModels: string; // single model string: 'DCF' | 'DuPont' | 'COMPS' | ''
  selectedScenario: string;
  loading: boolean;
  error: string | null;
  aiError: string | null;
  validationErrors: string[];
  forecastYears: number;
  sessionId: string | null;

  // ─── Slice 2: Session & Company ────────────────────────────────────────
  selectedCompany: any;
  suggestedPeers: any[];
  selectedPeers: string[];
  requiredFields: any[];
  manualPeerInput: string;
  manualPeerError: string | null;
  manualPeerLoading: boolean;

  // ─── Slice 3: Data Matrix ──────────────────────────────────────────────
  valuationsData: MatrixStore;
  forecastDriversData: MatrixStore;
  dcfInputsData: MatrixStore;
  valuationResults: MatrixStore;
  peerData: any;
  calculatedMetrics: any;
  confirmedValues: Record<string, any>;

  // ─── Matrix Helpers ────────────────────────────────────────────────────
  getValuationData: (method: string | undefined | null) => any;
  setValuationData: (method: string | undefined | null, data: any) => void;
  getForecastDrivers: (method: string | undefined | null) => any;
  setForecastDrivers: (method: string | undefined | null, data: any) => void;
  getDcfInputs: (method: string | undefined | null) => any;
  setDcfInputs: (method: string | undefined | null, data: any) => void;
  getResult: (method: string | undefined | null) => any;
  setResult: (method: string | undefined | null, data: any) => void;
}

// ─── Deep Merge Helper ──────────────────────────────────────────────────────

function deepMergeMatrix(
  prev: MatrixStore,
  market: string,
  method: string | undefined | null,
  data: any
): MatrixStore {
  return {
    ...prev,
    [market]: {
      ...prev[market],
      [method?.toLowerCase() as keyof MatrixSlot]: data,
    },
  };
}

function emptyMatrix(): MatrixStore {
  return {
    international: { dcf: null, dupont: null, comps: null },
    vietnam: { dcf: null, dupont: null, comps: null },
  };
}

// ─── Store ──────────────────────────────────────────────────────────────────

const useValuationStore = create<ValuationState>((set, get) => ({
  // ─── Slice 1: Workflow (defaults) ─────────────────────────────────────
  currentStep: 1,
  maxReachedStep: 1,
  market: 'international',
  marketValidation: {
    isValid: true,
    message: '',
    selectedMarket: 'international',
    isLocked: false,
  },
  searchQuery: '',
  searchResults: [],
  selectedModel: '',
  selectedModels: '',
  selectedScenario: 'base_case',
  loading: false,
  error: null,
  aiError: null,
  validationErrors: [],
  forecastYears: 5,
  sessionId: null,

  // ─── Slice 2: Session & Company (defaults) ────────────────────────────
  selectedCompany: null,
  suggestedPeers: [],
  selectedPeers: [],
  requiredFields: [],
  manualPeerInput: '',
  manualPeerError: null,
  manualPeerLoading: false,

  // ─── Slice 3: Data Matrix (defaults) ──────────────────────────────────
  valuationsData: emptyMatrix(),
  forecastDriversData: emptyMatrix(),
  dcfInputsData: emptyMatrix(),
  valuationResults: emptyMatrix(),
  peerData: null,
  calculatedMetrics: null,
  confirmedValues: {},

  // ─── Matrix Helpers ────────────────────────────────────────────────────

  getValuationData: (method) => {
    const { market, valuationsData } = get();
    return valuationsData[market]?.[method?.toLowerCase() as keyof MatrixSlot] ?? null;
  },

  setValuationData: (method, data) => {
    const { market } = get();
    set((state) => ({
      valuationsData: deepMergeMatrix(state.valuationsData, market, method, data),
    }));
  },

  getForecastDrivers: (method) => {
    const { market, forecastDriversData } = get();
    return forecastDriversData[market]?.[method?.toLowerCase() as keyof MatrixSlot] ?? null;
  },

  setForecastDrivers: (method, data) => {
    const { market } = get();
    set((state) => ({
      forecastDriversData: deepMergeMatrix(state.forecastDriversData, market, method, data),
    }));
  },

  getDcfInputs: (method) => {
    const { market, dcfInputsData } = get();
    return dcfInputsData[market]?.[method?.toLowerCase() as keyof MatrixSlot] ?? null;
  },

  setDcfInputs: (method, data) => {
    const { market } = get();
    set((state) => ({
      dcfInputsData: deepMergeMatrix(state.dcfInputsData, market, method, data),
    }));
  },

  getResult: (method) => {
    const { market, valuationResults } = get();
    return valuationResults[market]?.[method?.toLowerCase() as keyof MatrixSlot] ?? null;
  },

  setResult: (method, data) => {
    const { market } = get();
    set((state) => ({
      valuationResults: deepMergeMatrix(state.valuationResults, market, method, data),
    }));
  },
}));

export default useValuationStore;
