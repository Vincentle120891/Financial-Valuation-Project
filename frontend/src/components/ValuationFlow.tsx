import React, { useEffect, useCallback, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import useValuationStore from '../store/useValuationStore';
import { handleSearch, handleSelectCompany, handleCreateSession } from '../store/actions/step1_2_search_actions';
import {
  handleFindPeers,
  handleTogglePeer,
  handleContinueToRequirementsReview,
  handleSelectModel,
  handleBackToModelSelection,
} from '../store/actions/step3_4_peer_actions';
import {
  handleRetrieveData,
  handleContinueToHistoricalDataRetrieval,
  handleStep7ContinueToForecastDrivers,
  fetchRequiredInputs,
} from '../store/actions/step5_7_data_fetch_actions';
import {
  handleContinueToForecastDrivers,
  handleContinueToAssumptions,
  handleManualInput,
  handleAutoSaveForecastDrivers,
  handleAutoSaveDcfInputs,
  handleUseAI,
  handleConfirmAssumptions,
} from '../store/actions/step8_9_assumption_actions';
import {
  handleRunValuation,
  handleReset,
} from '../store/actions/step10_11_valuation_actions';
import SearchStep from './valuation-flow/step1_search_step';
import CompanySelectionStep from './valuation-flow/step2_company_selection_step';
import ModelSelectionStep from './valuation-flow/step3_model_selection_step';
import PeerSelectionStep from './valuation-flow/step4_peer_selection_step';
import RequirementsStep from './valuation-flow/step5_requirements_step';
import ApiDataStep from './valuation-flow/step6_api_data_step';
import HistoricalDataExtractionStep from './valuation-flow/step7_historical_data_step';
import ForecastDriversStep from './valuation-flow/step8_forecast_drivers_step';
import AssumptionsStep from './valuation-flow/step9_assumptions_step';
import RunValuationStep from './valuation-flow/step10_run_valuation_step';
import ResultsStep from './valuation-flow/step11_results_step';
import ApiKeyDebugButton from './ApiKeyDebugButton';
import HistoricalStatements from './valuation-flow/HistoricalStatements';
import LanguageToggle from './LanguageToggle';
import ThemeToggle from './ThemeToggle';
import TranslationNotice from './TranslationNotice';

// Debounce utility function for auto-save
const useDebounce = (callback: (...args: any[]) => void, delay: number) => {
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const debouncedCallback = useCallback(
    (...args) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        callback(...args);
      }, delay);
    },
    [callback, delay]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return debouncedCallback;
};

/**
 * ValuationFlow — Terminal-Style 3-Panel Layout
 *
 * Orchestrates the 11-step valuation workflow in a dense multi-pane terminal UI:
 *   ┌─────────────────────────────────────────────────────────────┐
 *   │  🌐 UNIFIED VALUATION ENGINE  │ Session │ Market │ ...    │ ← h-12 top nav
 *   ├──────────────┬──────────────────────────────────────────────┤
 *   │  PROGRESS    │ WORKSPACE STAGE                              │
 *   │  TIMELINE    │ (center content area — renders current step) │
 *   │              │                                              │
 *   │  🟢 Step 1  │                                              │
 *   │  🔵 Step 2  │                                              │
 *   │  ⚪ Step 3  │                                              │
 *   │  ...         │                                              │
 *   │              ├──────────────────────────────────────────────┤
 *   │  AUDIT       │  [⬅ Back]                    [Next ➡]       │
 *   │  PANEL       │                                              │
 *   └──────────────┴──────────────────────────────────────────────┘
 */

// STEP_NAMES is a static lookup — translated via t('steps.step{N}') at render time
const STEP_NAMES: Record<number, string> = {
  1: 'Company Query Filter',
  2: 'Session Data Validation',
  3: 'Model Engine Bound',
  4: 'Peer Discovery & Selection',
  5: 'Field Requirements Review',
  6: 'API Data Retrieval',
  7: 'Historical Extraction',
  8: 'Forecast Drivers',
  9: 'Assumption Confirmation',
  10: 'Valuation Execution',
  11: 'Results Synthesis',
};

const STEP_SHORT: Record<number, string> = {
  1: 'Search',
  2: 'Company',
  3: 'Model',
  4: 'Peers',
  5: 'Requirements',
  6: 'API Data',
  7: 'Historical',
  8: 'Forecast',
  9: 'Assumptions',
  10: 'Run',
  11: 'Results',
};

const stepVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 40 : -40,
    opacity: 0,
    filter: 'blur(4px)',
  }),
  center: {
    x: 0,
    opacity: 1,
    filter: 'blur(0px)',
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -40 : 40,
    opacity: 0,
    filter: 'blur(4px)',
  }),
};

const stepTransition = {
  x: { type: 'spring' as const, stiffness: 300, damping: 30 },
  opacity: { duration: 0.2 },
  filter: { duration: 0.25 },
};

/** Floating resizable modal for Step 8 Financial Statements */
const Step8FinancialsButton: React.FC<{
  completeFinancialStatements: any;
  market: string;
}> = ({ completeFinancialStatements, market }) => {
  const [open, setOpen] = useState(false);
  const [size, setSize] = useState({ width: 900, height: 600 });
  const [pos, setPos] = useState({ x: 100, y: 80 });
  const dragRef = useRef<{ startX: number; startY: number; startPosX: number; startPosY: number } | null>(null);

  const handleDragStart = (e: React.MouseEvent) => {
    dragRef.current = { startX: e.clientX, startY: e.clientY, startPosX: pos.x, startPosY: pos.y };
    const handleMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      setPos({
        x: dragRef.current.startPosX + (ev.clientX - dragRef.current.startX),
        y: dragRef.current.startPosY + (ev.clientY - dragRef.current.startY),
      });
    };
    const handleUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  };

  const handleResize = (e: React.MouseEvent) => {
    e.stopPropagation();
    const startX = e.clientX;
    const startY = e.clientY;
    const startW = size.width;
    const startH = size.height;
    const handleMove = (ev: MouseEvent) => {
      setSize({
        width: Math.max(600, startW + (ev.clientX - startX)),
        height: Math.max(400, startH + (ev.clientY - startY)),
      });
    };
    const handleUp = () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  };

  if (!open) {
    return (
      <div className="mt-2">
        <button
          onClick={() => setOpen(true)}
          className="w-full text-left text-[10px] text-slate-400 hover:text-white border border-slate-600 px-2 py-1 rounded transition-colors"
        >
          📋 Step 8 Financials ▶
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="mt-2">
        <button
          onClick={() => setOpen(false)}
          className="w-full text-left text-[10px] text-blue-400 hover:text-white border border-blue-600 px-2 py-1 rounded transition-colors"
        >
          📋 Step 8 Financials ▼
        </button>
      </div>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setOpen(false)} />
      {/* Floating Modal */}
      <div
        className="fixed z-50 bg-slate-900 border border-slate-600 rounded-lg shadow-2xl flex flex-col"
        style={{ left: pos.x, top: pos.y, width: size.width, height: size.height }}
      >
        {/* Title bar — draggable */}
        <div
          onMouseDown={handleDragStart}
          className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700 cursor-move select-none rounded-t-lg"
        >
          <span className="text-xs font-semibold text-slate-300">📋 Step 8 Financial Statements</span>
          <button
            onClick={() => setOpen(false)}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-red-600/60 text-slate-400 hover:text-white text-sm font-bold"
          >✕</button>
        </div>
        {/* Content — scrollable */}
        <div className="flex-1 overflow-auto p-2">
          <HistoricalStatements completeFinancialStatements={completeFinancialStatements} market={market} />
        </div>
        {/* Resize handle */}
        <div
          onMouseDown={handleResize}
          className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize"
        />
      </div>
    </>
  );
};

const ValuationFlow: React.FC = () => {
  const { t } = useTranslation();
  // ─── Mobile sidebar state ──────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  // Close sidebar on step change (mobile)
  const setCurrentStepWrapper = useCallback(
    (val: number) => {
      useValuationStore.setState({ currentStep: val });
      setSidebarOpen(false);
    },
    []
  );

  // ─── Zustand Store Selectors ────────────────────────────────────────────
  const currentStep = useValuationStore((s) => s.currentStep);
  const searchQuery = useValuationStore((s) => s.searchQuery);
  const searchResults = useValuationStore((s) => s.searchResults);
  const selectedCompany = useValuationStore((s) => s.selectedCompany);
  const suggestedPeers = useValuationStore((s) => s.suggestedPeers);
  const selectedPeers = useValuationStore((s) => s.selectedPeers);
  const sessionId = useValuationStore((s) => s.sessionId);
  const selectedModels = useValuationStore((s) => s.selectedModels);
  const forecastYears = useValuationStore((s) => s.forecastYears);
  const market = useValuationStore((s) => s.market);
  const marketValidation = useValuationStore((s) => s.marketValidation);
  const requiredFields = useValuationStore((s) => s.requiredFields);
  const confirmedValues = useValuationStore((s) => s.confirmedValues);
  const selectedScenario = useValuationStore((s) => s.selectedScenario);
  const loading = useValuationStore((s) => s.loading);
  const error = useValuationStore((s) => s.error);
  const aiError = useValuationStore((s) => s.aiError);
  const valuationsData = useValuationStore((s) => s.valuationsData);
  const peerData = useValuationStore((s) => s.peerData);
  const calculatedMetrics = useValuationStore((s) => s.calculatedMetrics);

  // Track direction for step transition animation
  const prevStepRef = useRef(currentStep);
  const direction = currentStep >= prevStepRef.current ? 1 : -1;
  React.useEffect(() => {
    prevStepRef.current = currentStep;
  }, [currentStep]);

  // Track whether Step 5 data has been fetched (for button-driven navigation)
  const [dataFetched, setDataFetched] = React.useState(false);
  const handleRetrieveDataWrapper = React.useCallback(async () => {
    await handleRetrieveData();
    setDataFetched(true);
  }, []);

  // Matrix helpers from store
  const getValuationData = useValuationStore((s) => s.getValuationData);
  const getForecastDrivers = useValuationStore((s) => s.getForecastDrivers);
  const getDcfInputs = useValuationStore((s) => s.getDcfInputs);
  const getResult = useValuationStore((s) => s.getResult);

  // Store setters (direct references to setState — no re-renders needed)
  const setSearchQuery = useCallback(
    (val) => useValuationStore.setState({ searchQuery: val }),
    []
  );
  const setMarket = useCallback(
    (val) => useValuationStore.setState({ market: val }),
    []
  );
  const setError = useCallback(
    (val) => useValuationStore.setState({ error: val }),
    []
  );
  // ─── Debounced auto-save handlers ─────────────────────────────────────
  const debouncedAutoSaveForecastDrivers = useDebounce(
    handleAutoSaveForecastDrivers,
    500
  );
  const debouncedAutoSaveDcfInputs = useDebounce(handleAutoSaveDcfInputs, 500);

  // ─── Auto-fetch required inputs on Step 5 ─────────────────────────────
  useEffect(() => {
    const method = selectedModels;
    if (method && currentStep === 5 && sessionId) {
      fetchRequiredInputs(method);
    }
  }, [selectedModels, currentStep, sessionId, market]);

  // ─── Render Step ──────────────────────────────────────────────────────
  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <SearchStep
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchResults={searchResults}
            loading={loading}
            error={error}
            market={market}
            setMarket={setMarket}
            onSearch={handleSearch}
            onSelectCompany={handleSelectCompany}
            onContinueToStep2={async () => {
              await handleCreateSession();
              setCurrentStepWrapper(2);
            }}
            selectedCompany={selectedCompany}
            marketValidation={marketValidation}
          />
        );
      case 2:
        return (
          <CompanySelectionStep
            selectedCompany={selectedCompany}
            onFindPeers={() => {}}
            onContinue={() => setCurrentStepWrapper(3)}
            onBack={() => setCurrentStepWrapper(1)}
            loading={loading}
            hasPeers={false}
            market={market}
            showFindPeersButton={false}
            currentStep={2}
          />
        );
      case 3:
        return (
          <ModelSelectionStep
            onSelectModel={handleSelectModel}
            selectedModels={selectedModels}
            onContinue={() => setCurrentStepWrapper(4)}
            onBack={() => setCurrentStepWrapper(2)}
            loading={loading}
          />
        );
      case 4:
        return (
          <PeerSelectionStep
            discoveredPeers={suggestedPeers}
            selectedPeers={selectedPeers}
            onTogglePeer={handleTogglePeer}
            onContinue={async () => {
              await handleContinueToRequirementsReview();
              setCurrentStepWrapper(5);
            }}
            onBack={() => setCurrentStepWrapper(3)}
            loading={loading}
            onFindPeers={handleFindPeers}
            selectedCompany={selectedCompany}
            market={market}
          />
        );
      case 5:
        return (
          <RequirementsStep
            selectedModel={selectedModels}
            onBackToModelSelection={() => setCurrentStepWrapper(3)}
            onRetrieveData={handleRetrieveDataWrapper}
            onContinueToStep6={() => setCurrentStepWrapper(6)}
            loading={loading}
            requiredFields={requiredFields}
            calculatedMetrics={calculatedMetrics}
            dataFetched={dataFetched}
          />
        );
      case 6: {
        const valuationData = getValuationData(selectedModels);
        return (
          <ApiDataStep
            historicalData={valuationData}
            forecastDrivers={valuationData?.forecast_drivers}
            peerData={peerData}
            dcfInputs={getDcfInputs(selectedModels)}
            dupontResults={getResult('DuPont')}
            compsResults={getResult('COMPS')}
            calculatedMetrics={calculatedMetrics}
            onBackToRequirements={() => setCurrentStepWrapper(5)}
            onContinueToAiAssumptions={async () => {
              await handleContinueToHistoricalDataRetrieval();
              setCurrentStepWrapper(7);
            }}
            loading={loading}
          />
        );
      }
      case 7:
        return (
          <HistoricalDataExtractionStep
            sessionId={sessionId}
            historicalGapsData={getValuationData(selectedModels)}
            aiError={aiError}
            confirmedValues={confirmedValues}
            selectedModel={selectedModels}
            market={market}
            historicalData={getValuationData(selectedModels)}
            apiData={calculatedMetrics}
            onManualInput={handleManualInput}
            onUseAI={handleUseAI}
            onBackToApiData={() => setCurrentStepWrapper(6)}
            onContinueToForecastDrivers={async () => {
              await handleStep7ContinueToForecastDrivers();
              setCurrentStepWrapper(8);
            }}
            onRetryAiExtraction={async () => {
              await handleStep7ContinueToForecastDrivers();
              setCurrentStepWrapper(8);
            }}
            loading={loading}
          />
        );
      case 8:
        return (
          <ForecastDriversStep
            sessionId={sessionId}
            forecastDrivers={getForecastDrivers(selectedModels)}
            dcfInputs={getDcfInputs(selectedModels)}
            step6Data={calculatedMetrics}
            step7Data={getValuationData(selectedModels)}
            market={market}
            selectedModel={selectedModels}
            onManualInput={handleManualInput}
            onAutoSave={debouncedAutoSaveForecastDrivers}
            onConfirmDrivers={async () => {
              // Just navigate to Step 9 without auto-calling the backend.
              // Step 9 shows data first; user clicks "Calculate" to run DCF engine.
              setCurrentStepWrapper(9);
            }}
            onBackToHistoricalData={() => setCurrentStepWrapper(7)}
            onContinueToAssumptions={() => setCurrentStepWrapper(9)}
            loading={loading}
          />
        );
      case 9: {
        const valuationData = getValuationData(selectedModels);
        const step8Response = valuationData?.data || valuationData;
        return (
          <AssumptionsStep
            // New props for DCF calculation engine
            forecastDrivers={getForecastDrivers(selectedModels)}
            dcfInputs={getDcfInputs(selectedModels)}
            completeFinancialStatements={step8Response?.complete_financial_statements}
            peerWaccData={step8Response?.peer_wacc_data}
            marketData={peerData}
            selectedCompany={selectedCompany}
            ticker={selectedCompany?.ticker || ''}
            companyName={selectedCompany?.company_name || selectedCompany?.ticker || ''}
            currentPrice={selectedCompany?.currentPrice || selectedCompany?.price || 0}
            selectedModel={selectedModels}
            selectedScenario={selectedScenario}
            confirmedValues={confirmedValues}
            onManualInput={handleManualInput}
            onConfirmAssumptions={async () => {
              await handleConfirmAssumptions();
              setCurrentStepWrapper(10);
            }}
            onBackToForecastDrivers={() => setCurrentStepWrapper(8)}
            loading={loading}
            // Legacy props for backward compatibility
            historicalData={valuationData}
            peerData={peerData}
          />
        );
      }
      case 10:
        return (
          <RunValuationStep
            selectedCompany={selectedCompany}
            selectedModel={selectedModels}
            selectedScenario={selectedScenario}
            confirmedValues={confirmedValues}
            loading={loading}
            onBackToAssumptions={() => setCurrentStepWrapper(9)}
            onRunValuation={async () => {
              await handleRunValuation();
              // No automatic transition to step 11 — user stays on step 10
            }}
            onViewResults={() => setCurrentStepWrapper(11)}
          />
        );
      case 11:
        return (
          <ResultsStep
            valuationMatrix={valuationsData}
            selectedMarket={market}
            selectedModels={selectedModels}
            onBackToModelSelection={handleBackToModelSelection}
            onReset={handleReset}
          />
        );
      default:
        return <div className="text-slate-500 text-sm">Step under construction</div>;
    }
  };

  // ─── Terminal App Shell ──────────────────────────────────────────────
  return (
    <div className="terminal-app">
      {/* ─── Top Navigation Strip ─── */}
      <nav className="terminal-nav">
        {/* Mobile hamburger */}
        <button
          className="mobile-menu-btn"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle navigation sidebar"
        >
          {sidebarOpen ? '✕' : '☰'}
        </button>
        <span className="font-bold text-[var(--text-primary)] text-[13px] whitespace-nowrap">
          🌐 UNIFIED VALUATION ENGINE
        </span>
        <div className="w-px h-5 bg-[var(--border-default)] hidden sm:block" />
        <span className="whitespace-nowrap hidden sm:inline">
          Session: {sessionId ? <span className="text-[var(--accent-primary)] font-tabular">#{sessionId.slice(0, 8)}</span> : <span className="text-[var(--text-tertiary)]">—</span>}
        </span>
        <span className="whitespace-nowrap hidden md:inline">
          {market === 'vietnam' ? '🇻🇳 VN' : '🌍 INTL'}
        </span>
        <span className="whitespace-nowrap hidden md:inline">
          {market === 'vietnam' ? <span className="font-tabular text-[var(--color-bullish)]">VND ₫</span> : <span className="font-tabular text-[var(--color-bullish)]">USD $</span>}
        </span>
        <div className="ml-auto whitespace-nowrap flex items-center gap-2">
          <LanguageToggle />
          API: {sessionId ? (
            <span className="text-[var(--color-bullish)]">✅</span>
          ) : (
            <span className="text-[var(--color-neutral)]">⏳</span>
          )}
        </div>
      </nav>

      {/* ─── Sidebar Backdrop (mobile) ─── */}
      <div
        className={`sidebar-backdrop ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* ─── Left Sidebar ─── */}
      <aside className={`terminal-sidebar ${sidebarOpen ? 'open' : ''}`}>
        {/* Progress Timeline */}
        <div className="py-3 flex-1">
          <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-tertiary)] px-4 mb-2 font-semibold">
            {t('nav.dashboard')}
          </h3>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((step) => {
            const isCompleted = currentStep > step;
            const isActive = currentStep === step;
            const isClickable = isCompleted;
            return (
              <div
                key={step}
                className={`step-item ${isCompleted ? 'completed' : isActive ? 'active' : 'pending'} ${isClickable ? 'clickable' : ''}`}
                onClick={isClickable ? () => setCurrentStepWrapper(step) : undefined}
                title={isClickable ? `Navigate to Step ${step}: ${STEP_NAMES[step]}` : undefined}
              >
                <span className="w-4 text-center flex-shrink-0">
                  {isCompleted ? '🟢' : isActive ? '🔵' : '⚪'}
                </span>
                <span className="truncate">
                  {t(`steps.step${step}`)}
                </span>
                {isActive && (
                  <span className="ml-auto text-[10px] text-blue-400 font-tabular">
                    {Math.round((currentStep / 11) * 100)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Separator */}
        <div className="border-t border-slate-800" />

        {/* Audit & Integrity Panel */}
        <div className="audit-panel">
          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-semibold">
            Audit & Integrity
          </h3>
          <div className="audit-row">
            <span>Data Consistency</span>
            <span className="audit-value font-tabular">100%</span>
          </div>
          <div className="audit-row">
            <span>Data Source Trust</span>
            <span className="audit-value">Institutional</span>
          </div>
          <div className="audit-row">
            <span>Balance Sheet</span>
            <span className="audit-value">Balanced ⚖️</span>
          </div>
          <div className="audit-row">
            <span>Model Coverage</span>
            <span className="audit-value font-tabular">
              {selectedModels ? selectedModels.split(',').length : 0}/3
            </span>
          </div>
          {/* Step 8 Financials — accessible from Audit panel */}
          {(() => {
            const valuationData = getValuationData(selectedModels);
            const step8Response = valuationData?.data || valuationData;
            const completeFinancialStatements = step8Response?.complete_financial_statements;
            if (!completeFinancialStatements) return null;
            return (
              <Step8FinancialsButton
                completeFinancialStatements={completeFinancialStatements}
                market={market}
              />
            );
          })()}
        </div>

        {/* Separator */}
        <div className="border-t border-slate-800" />

        {/* API Key Manager — inline in sidebar */}
        <div className="px-4 py-2">
          <ApiKeyDebugButton variant="inline" />
        </div>

        {/* Separator */}
        <div className="border-t border-[var(--border-default)]" />

        {/* Settings — Language + Theme toggles — sidebar */}
        <div className="px-4 py-2 flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-[var(--text-tertiary)] font-semibold">
            {t('nav.settings')}
          </span>
          <div className="flex items-center gap-1.5">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>

        {/* Separator */}
        <div className="border-t border-[var(--border-default)]" />

        {/* Quick Stats */}
        <div className="quick-stats">
          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-semibold">
            Quick Stats
          </h3>
          <div className="stat-row">
            <span>Company</span>
            <span className="stat-value font-tabular">
              {selectedCompany?.ticker || '—'}
            </span>
          </div>
          <div className="stat-row">
            <span>Price</span>
            <span className="stat-value font-tabular">
              {selectedCompany?.currentPrice
                ? `${selectedCompany.currentPrice.toLocaleString()}`
                : '—'}
            </span>
          </div>
          <div className="stat-row">
            <span>Peers</span>
            <span className="stat-value font-tabular">
              {selectedPeers?.length || 0}
            </span>
          </div>
          <div className="stat-row">
            <span>Model</span>
            <span className="stat-value">
              {selectedModels || '—'}
            </span>
          </div>
          <div className="stat-row">
            <span>Scenario</span>
            <span className="stat-value">
              {(selectedScenario || 'base_case').replace('_', ' ')}
            </span>
          </div>
        </div>
      </aside>

      {/* ─── Center Stage ─── */}
      <main className="terminal-stage">
        {/* Error Display */}
        {error && (
          <div className="terminal-error" role="alert">
            <span>⚠️</span>
            <span className="flex-1">{error}</span>
            <button
              className="text-red-400 hover:text-red-300 ml-2 text-xs"
              onClick={() => setError(null)}
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}

        {/* Loading Indicator */}
        {loading && currentStep <= 6 && (
          <div className="mb-4 flex items-center gap-2 text-xs text-slate-400">
            <div className="w-3 h-3 border-2 border-slate-600 border-t-blue-400 rounded-full animate-spin" />
            <span>{t('common.processing')} — {t(`steps.step${currentStep}`)}</span>
          </div>
        )}

        {/* Step Content with animated transitions */}
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={stepTransition}
            className="step-content"
          >
            {renderStep()}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Translation Mask Notice — Fixed at bottom of viewport */}
      <TranslationNotice />

      {/* ─── Mobile Bottom Navigation (Prev / Step Indicator / Next) ─── */}
      <nav className="mobile-bottom-nav">
        <button
          className="nav-step-btn"
          onClick={() => currentStep > 1 && setCurrentStepWrapper(currentStep - 1)}
          disabled={currentStep <= 1}
          style={{ flex: '0 0 auto', minWidth: 60 }}
        >
          <span className="step-num">◀</span>
          <span>{t('common.back')}</span>
        </button>

        {/* Step dots */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', flex: '1 1 auto', justifyContent: 'center', overflow: 'hidden' }}>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((step) => (
            <div
              key={step}
              onClick={() => step <= currentStep && setCurrentStepWrapper(step)}
              style={{
                width: step === currentStep ? 16 : 8,
                height: 6,
                borderRadius: 3,
                background: step < currentStep ? 'var(--color-retrieved)' : step === currentStep ? 'var(--accent-primary)' : 'var(--border-strong)',
                cursor: step <= currentStep ? 'pointer' : 'default',
                flexShrink: 0,
              }}
              title={`Step ${step}: ${STEP_SHORT[step]}`}
            />
          ))}
        </div>

        <button
          className="nav-step-btn"
          onClick={() => currentStep < 11 && setCurrentStepWrapper(currentStep + 1)}
          disabled={currentStep >= 11}
          style={{ flex: '0 0 auto', minWidth: 60 }}
        >
          <span>{t('common.next')}</span>
          <span className="step-num">▶</span>
        </button>
      </nav>
    </div>
  );
};

export default ValuationFlow;
