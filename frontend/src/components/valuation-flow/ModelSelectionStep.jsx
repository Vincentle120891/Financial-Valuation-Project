import React from 'react';

/**
 * ModelSelectionStep - Step 3
 * Select Valuation Model(s)
 * 
 * FIXED: Now uses Radio Buttons instead of checkboxes.
 * Per documentation: "MUST use Radio Buttons. Multi-select is forbidden."
 * This prevents AI context hallucination from multiple simultaneous model selections.
 * 
 * WORKFLOW CORRECTION:
 * Model selection happens FIRST (Step 3), then peers are discovered in Step 4
 * based on the selected model's specific criteria.
 * No peer requirement at this stage - peers will be auto-selected in Step 4.
 */
const ModelSelectionStep = ({ onSelectModel, selectedModels }) => {
  const models = [
    { 
      id: 'DCF', 
      name: 'Discounted Cash Flow', 
      desc: 'Intrinsic value based on projected free cash flows. Requires 3-year historical data + 6-period forecast.' 
    },
    { 
      id: 'DuPont', 
      name: 'DuPont Analysis', 
      desc: 'ROE decomposition into margins, turnover, and leverage. Analyzes 3-5 years of trends.' 
    },
    { 
      id: 'COMPS', 
      name: 'Trading Comps', 
      desc: 'Relative valuation using peer multiples. Automatically fetches 5+ comparable companies.' 
    }
  ];

  // GAP 2 FIX: Use single selection (radio button behavior) instead of array-based multi-select
  const handleSelectModel = (modelId) => {
    // Single selection - just pass the model ID directly (not an array)
    // Peers will be discovered in Step 4 based on the selected model
    onSelectModel(modelId);
  };

  // Helper to check if model is selected
  const isSelected = (modelId) => selectedModels === modelId;

  return (
    <div className="model-selection-step">
      <div className="model-options">
        {models.map((model) => (
          <div 
            key={model.id} 
            className={`model-card ${isSelected(model.id) ? 'selected' : ''}`}
            onClick={() => handleSelectModel(model.id)}
            style={{ cursor: 'pointer' }}
          >
            {/* GAP 2 FIX: Radio button instead of checkbox */}
            <div className={`absolute top-2.5 right-2.5 w-5 h-5 rounded-full border-2 border-indigo-500 flex items-center justify-center text-white text-sm transition-all ${
              isSelected(model.id) ? 'bg-indigo-500' : 'bg-white'
            }`}>
              {isSelected(model.id) && '●'}
            </div>
            <h3>{model.name}</h3>
            <p>{model.desc}</p>
          </div>
        ))}
      </div>
      <div className="mt-5 text-center">
        <p className="text-slate-600 text-sm">
          {!selectedModels
            ? 'Select one model to continue'
            : `1 model selected: ${selectedModels}`}
        </p>
      </div>
    </div>
  );
};

export default ModelSelectionStep;
