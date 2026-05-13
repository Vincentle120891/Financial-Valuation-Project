import React from 'react';

/**
 * ModelSelectionStep Component
 * Step 4: Select Valuation Model(s)
 * 
 * FIXED: Now uses Radio Buttons instead of checkboxes.
 * Per documentation: "MUST use Radio Buttons. Multi-select is forbidden."
 * This prevents AI context hallucination from multiple simultaneous model selections.
 * 
 * UNIFIED SCHEMA REQUIREMENT:
 * Requires selectedPeers prop to ensure peers are selected before model selection.
 * UnifiedStep4Request schema requires either suggested_peers or custom_peers.
 */
const ModelSelectionStep = ({ onSelectModel, selectedModels, selectedPeers }) => {
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
    // Client-side validation: Prevent model selection without peers (Unified Schema Requirement)
    if (!selectedPeers || selectedPeers.length === 0) {
      alert('⚠️ No peers selected! Please go back to Step 3 and select at least one peer company.');
      return;
    }
    
    // Single selection - just pass the model ID directly (not an array)
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
            style={{
              cursor: 'pointer',
              border: isSelected(model.id) ? '2px solid #667eea' : '2px solid #e0e0e0',
              background: isSelected(model.id) ? '#f8f9ff' : 'white',
              position: 'relative'
            }}
          >
            {/* GAP 2 FIX: Radio button instead of checkbox */}
            <div style={{ 
              position: 'absolute', 
              top: '10px', 
              right: '10px',
              width: '20px',
              height: '20px',
              borderRadius: '50%',  // Circle for radio button
              border: '2px solid #667eea',
              background: isSelected(model.id) ? '#667eea' : 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '14px'
            }}>
              {isSelected(model.id) && '●'}  // Filled circle for selected radio
            </div>
            <h3>{model.name}</h3>
            <p>{model.desc}</p>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <p style={{ color: '#666', fontSize: '14px' }}>
          {!selectedModels
            ? 'Select one model to continue'
            : `1 model selected: ${selectedModels}`}
        </p>
      </div>
    </div>
  );
};

export default ModelSelectionStep;
