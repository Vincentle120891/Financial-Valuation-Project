import React from 'react';

/**
 * ModelSelectionStep Component
 * Step 4: Select Valuation Model
 * 
 * Features:
 * - Three model options (DCF, DuPont, Trading Comps)
 * - Detailed descriptions for each model
 * - Click-to-select interaction
 */
const ModelSelectionStep = ({ onSelectModel }) => {
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

  return (
    <div className="step-container">
      <h2>Step 4: Select Valuation Model</h2>
      <div className="model-options">
        {models.map((model) => (
          <div 
            key={model.id} 
            className="model-card" 
            onClick={() => onSelectModel(model.id)}
          >
            <h3>{model.name}</h3>
            <p>{model.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ModelSelectionStep;
