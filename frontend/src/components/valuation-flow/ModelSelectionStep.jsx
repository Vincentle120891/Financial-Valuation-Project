import React from 'react';

/**
 * ModelSelectionStep Component
 * Step 4: Select Valuation Model(s)
 * 
 * Features:
 * - Three model options (DCF, DuPont, Trading Comps)
 * - Detailed descriptions for each model
 * - Multi-select support via checkboxes (P1 enhancement)
 * - Click-to-select interaction
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

  const handleToggleModel = (modelId) => {
    if (selectedModels && selectedModels.includes(modelId)) {
      // Deselect - remove from array
      const updated = selectedModels.filter(id => id !== modelId);
      onSelectModel(updated);
    } else {
      // Select - add to array
      const updated = selectedModels ? [...selectedModels, modelId] : [modelId];
      onSelectModel(updated);
    }
  };

  const isSelected = (modelId) => {
    return selectedModels && selectedModels.includes(modelId);
  };

  return (
    <div className="step-container">
      <h2>Step 4: Select Valuation Model(s)</h2>
      <p style={{ marginBottom: '20px', color: '#666' }}>
        Choose one or more valuation methodologies to apply. 
        <strong style={{ color: '#667eea' }}> Multi-select enables parallel valuation across all chosen methods.</strong>
      </p>
      <div className="model-options">
        {models.map((model) => (
          <div 
            key={model.id} 
            className={`model-card ${isSelected(model.id) ? 'selected' : ''}`}
            onClick={() => handleToggleModel(model.id)}
            style={{
              cursor: 'pointer',
              border: isSelected(model.id) ? '2px solid #667eea' : '2px solid #e0e0e0',
              background: isSelected(model.id) ? '#f8f9ff' : 'white',
              position: 'relative'
            }}
          >
            <div style={{ 
              position: 'absolute', 
              top: '10px', 
              right: '10px',
              width: '20px',
              height: '20px',
              borderRadius: '4px',
              border: '2px solid #667eea',
              background: isSelected(model.id) ? '#667eea' : 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '14px'
            }}>
              {isSelected(model.id) && '✓'}
            </div>
            <h3>{model.name}</h3>
            <p>{model.desc}</p>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <p style={{ color: '#666', fontSize: '14px' }}>
          {selectedModels?.length === 0 
            ? 'Select at least one model to continue'
            : `${selectedModels.length} model(s) selected`}
        </p>
      </div>
    </div>
  );
};

export default ModelSelectionStep;
