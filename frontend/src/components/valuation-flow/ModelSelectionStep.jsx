import React from 'react';

/**
 * ModelSelectionStep - Step 3
 * Select Valuation Model (Single Selection Only)
 * 
 * DESIGN PRINCIPLES:
 * - Clean card-based layout with clear visual hierarchy
 * - Radio button selection (NOT checkboxes) - single model only
 * - Detailed descriptions for each method
 * - Matches ResultsStep.jsx polish
 * 
 * WORKFLOW:
 * - User selects ONE model in Step 3
 * - Peers are auto-discovered in Step 4 based on selected model
 */
const ModelSelectionStep = ({ onSelectModel, selectedModel, onContinue, onBack, loading }) => {
  const models = [
    { 
      id: 'DCF', 
      name: 'Discounted Cash Flow (DCF)', 
      icon: '💰',
      desc: 'Calculate intrinsic value based on projected free cash flows discounted to present value.',
      requirements: 'Requires 3-year historical data + 6-period forecast',
      bestFor: 'Mature companies with stable, predictable cash flows'
    },
    { 
      id: 'DuPont', 
      name: 'DuPont Analysis', 
      icon: '📊',
      desc: 'Decompose Return on Equity (ROE) into profit margin, asset turnover, and financial leverage.',
      requirements: 'Analyzes 3-5 years of historical trends',
      bestFor: 'Understanding drivers of profitability and operational efficiency'
    },
    { 
      id: 'COMPS', 
      name: 'Trading Comps', 
      icon: '🏢',
      desc: 'Relative valuation using peer company multiples (EV/EBITDA, P/E, P/B).',
      requirements: 'Automatically fetches 5+ comparable companies',
      bestFor: 'Quick relative valuation and M&A comparables analysis'
    }
  ];

  const handleSelectModel = (modelId) => {
    onSelectModel(modelId);
  };

  const isSelected = (modelId) => selectedModel === modelId;

  return (
    <div className="step-container">
      {/* Header Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Step 3: Select Valuation Model</h2>
        <p className="text-gray-600">
          Choose one valuation methodology. Each model provides unique insights into company value.
        </p>
      </div>

      {/* Model Selection Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {models.map((model) => (
          <div
            key={model.id}
            onClick={() => handleSelectModel(model.id)}
            className={`relative cursor-pointer rounded-xl border-2 transition-all duration-200 overflow-hidden ${
              isSelected(model.id)
                ? 'border-indigo-500 bg-indigo-50 shadow-lg ring-2 ring-indigo-500 ring-opacity-50'
                : 'border-gray-200 bg-white hover:border-indigo-300 hover:shadow-md'
            }`}
          >
            {/* Selected Indicator */}
            {isSelected(model.id) && (
              <div className="absolute top-0 right-0 bg-indigo-500 text-white px-3 py-1 rounded-bl-lg text-sm font-semibold">
                ✓ Selected
              </div>
            )}

            {/* Card Content */}
            <div className="p-6">
              {/* Icon & Name */}
              <div className="flex items-center gap-3 mb-4">
                <span className="text-4xl">{model.icon}</span>
                <h3 className={`text-lg font-bold ${isSelected(model.id) ? 'text-indigo-900' : 'text-gray-900'}`}>
                  {model.name}
                </h3>
              </div>

              {/* Description */}
              <p className="text-gray-600 text-sm mb-4 leading-relaxed">
                {model.desc}
              </p>

              {/* Requirements */}
              <div className="bg-white/50 rounded-lg p-3 mb-3">
                <div className="flex items-start gap-2">
                  <svg className="w-4 h-4 text-indigo-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-xs text-gray-700">
                    <span className="font-semibold">Data Required:</span> {model.requirements}
                  </p>
                </div>
              </div>

              {/* Best For */}
              <div className="bg-white/50 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <svg className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <p className="text-xs text-gray-700">
                    <span className="font-semibold">Best For:</span> {model.bestFor}
                  </p>
                </div>
              </div>
            </div>

            {/* Radio Button Indicator */}
            <div className={`absolute bottom-4 right-4 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
              isSelected(model.id)
                ? 'border-indigo-500 bg-indigo-500'
                : 'border-gray-300 bg-white'
            }`}>
              {isSelected(model.id) && (
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Selection Summary */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 mb-8">
        <div className="flex items-center gap-3 mb-2">
          <svg className="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h4 className="text-sm font-semibold text-gray-700">Current Selection</h4>
        </div>
        {selectedModel ? (
          <p className="text-gray-900">
            <span className="font-bold text-indigo-600">{selectedModel}</span>
            {' '}model selected. Peer discovery will be performed automatically in Step 4 based on this model's criteria.
          </p>
        ) : (
          <p className="text-gray-500 italic">No model selected yet. Please choose one above to continue.</p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center mt-8">
        <button
          onClick={onBack}
          disabled={loading}
          className="px-6 py-3 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          ← Back to Company Overview
        </button>
        <button
          onClick={onContinue}
          disabled={!selectedModel || loading}
          className="px-6 py-3 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
        >
          Continue to Peer Discovery →
        </button>
      </div>
    </div>
  );
};

export default ModelSelectionStep;
