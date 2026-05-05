import React, { useState, useEffect } from 'react';

const AssumptionStudioStep = ({ 
  selectedModel, 
  historicalData, 
  assumptions, 
  onUpdateAssumptions,
  onNext,
  onBack 
}) => {
  const [localAssumptions, setLocalAssumptions] = useState({ ...assumptions });
  const [validationErrors, setValidationErrors] = useState({});
  const [whatIfPreview, setWhatIfPreview] = useState(null);

  // Calculate historical trends from historicalData
  const calculateHistoricalTrend = (metric) => {
    if (!historicalData || historicalData.length < 3) return 'N/A';
    const values = historicalData.slice(-3).map(year => year[metric] || 0);
    return values.map(v => `${(v * 100).toFixed(0)}%`).join(' → ');
  };

  // Validate inputs based on model type
  const validateInputs = (key, value) => {
    const errors = {};
    
    if (selectedModel === 'DCF') {
      if (key === 'terminalGrowthRate' && parseFloat(value) >= parseFloat(localAssumptions.wacc)) {
        errors[key] = 'Terminal Growth Rate must be less than WACC';
      }
      if (key === 'wacc' && (parseFloat(value) <= 0 || parseFloat(value) > 1)) {
        errors[key] = 'WACC must be between 0% and 100%';
      }
      if (key === 'revenueGrowth' && parseFloat(value) < -1) {
        errors[key] = 'Revenue Growth cannot be less than -100%';
      }
    }
    
    if (selectedModel === 'DuPont') {
      if (['netMargin', 'assetTurnover', 'equityMultiplier'].includes(key)) {
        if (parseFloat(value) < 0) {
          errors[key] = 'Value cannot be negative';
        }
      }
    }
    
    if (selectedModel === 'Comps') {
      if (key === 'discountRate' && (parseFloat(value) < 0 || parseFloat(value) > 1)) {
        errors[key] = 'Discount Rate must be between 0% and 100%';
      }
    }
    
    setValidationErrors(prev => ({ ...prev, ...errors }));
    return Object.keys(errors).length === 0;
  };

  // Handle manual input changes
  const handleInputChange = (key, value) => {
    const updated = { ...localAssumptions, [key]: value };
    setLocalAssumptions(updated);
    validateInputs(key, value);
    onUpdateAssumptions?.(updated);
    
    // Update what-if preview
    calculateWhatIfImpact(updated);
  };

  // Mock AI suggestion generator
  const generateAISuggestion = (category) => {
    const suggestions = {
      DCF: {
        revenueGrowth: (Math.random() * 0.15 + 0.05).toFixed(3),
        costRatio: (Math.random() * 0.2 + 0.6).toFixed(3),
        workingCapitalRatio: (Math.random() * 0.1 + 0.15).toFixed(3),
        wacc: (Math.random() * 0.05 + 0.08).toFixed(3),
        terminalGrowthRate: (Math.random() * 0.03 + 0.02).toFixed(3)
      },
      DuPont: {
        netMargin: (Math.random() * 0.15 + 0.1).toFixed(3),
        assetTurnover: (Math.random() * 0.5 + 0.8).toFixed(2),
        equityMultiplier: (Math.random() * 0.5 + 1.5).toFixed(2)
      },
      Comps: {
        peerMultiple: (Math.random() * 5 + 10).toFixed(1),
        suggestedMultiple: (Math.random() * 4 + 8).toFixed(1),
        discountRate: (Math.random() * 0.15 + 0.2).toFixed(3)
      }
    };
    
    const suggestion = suggestions[selectedModel]?.[category];
    if (suggestion) {
      handleInputChange(category, suggestion);
    }
  };

  // Calculate what-if impact (mocked)
  const calculateWhatIfImpact = (updatedAssumptions) => {
    // Mock calculation - ready for backend integration
    const baseValue = 100;
    const change = Math.random() * 20 - 10;
    const newValue = baseValue + change;
    
    setWhatIfPreview({
      baseValue: baseValue.toFixed(2),
      newValue: newValue.toFixed(2),
      change: change.toFixed(2),
      direction: change >= 0 ? 'up' : 'down'
    });
  };

  // Render DCF-specific inputs
  const renderDCFInputs = () => (
    <div className="space-y-6">
      {/* Revenue Growth */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Revenue Growth Rate</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('revenueGrowth')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="-1"
            max="2"
            value={localAssumptions.revenueGrowth || ''}
            onChange={(e) => handleInputChange('revenueGrowth', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.revenueGrowth ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter growth rate (e.g., 0.15 for 15%)"
          />
          <button
            onClick={() => generateAISuggestion('revenueGrowth')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
        {validationErrors.revenueGrowth && (
          <p className="text-red-500 text-sm mt-1">{validationErrors.revenueGrowth}</p>
        )}
      </div>

      {/* Cost Ratio */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Cost of Revenue Ratio</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('costRatio')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={localAssumptions.costRatio || ''}
            onChange={(e) => handleInputChange('costRatio', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.costRatio ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter ratio (e.g., 0.65 for 65%)"
          />
          <button
            onClick={() => generateAISuggestion('costRatio')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
      </div>

      {/* Working Capital Ratio */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Working Capital Ratio</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('workingCapitalRatio')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={localAssumptions.workingCapitalRatio || ''}
            onChange={(e) => handleInputChange('workingCapitalRatio', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.workingCapitalRatio ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter ratio (e.g., 0.20 for 20%)"
          />
          <button
            onClick={() => generateAISuggestion('workingCapitalRatio')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
      </div>

      {/* WACC */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">WACC (Weighted Average Cost of Capital)</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('wacc')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.001"
            min="0"
            max="1"
            value={localAssumptions.wacc || ''}
            onChange={(e) => handleInputChange('wacc', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.wacc ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter WACC (e.g., 0.10 for 10%)"
          />
          <button
            onClick={() => generateAISuggestion('wacc')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
        {validationErrors.wacc && (
          <p className="text-red-500 text-sm mt-1">{validationErrors.wacc}</p>
        )}
      </div>

      {/* Terminal Growth Rate */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Terminal Growth Rate</label>
          <span className="text-sm text-gray-500">Industry Avg: ~2-3%</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.001"
            min="0"
            max="0.1"
            value={localAssumptions.terminalGrowthRate || ''}
            onChange={(e) => handleInputChange('terminalGrowthRate', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.terminalGrowthRate ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter terminal growth (e.g., 0.025 for 2.5%)"
          />
          <button
            onClick={() => generateAISuggestion('terminalGrowthRate')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
        {validationErrors.terminalGrowthRate && (
          <p className="text-red-500 text-sm mt-1">{validationErrors.terminalGrowthRate}</p>
        )}
      </div>
    </div>
  );

  // Render DuPont-specific inputs
  const renderDuPontInputs = () => (
    <div className="space-y-6">
      {/* Net Profit Margin */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Net Profit Margin</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('netMargin')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={localAssumptions.netMargin || ''}
            onChange={(e) => handleInputChange('netMargin', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.netMargin ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter margin (e.g., 0.15 for 15%)"
          />
          <button
            onClick={() => generateAISuggestion('netMargin')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
      </div>

      {/* Asset Turnover */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Asset Turnover</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('assetTurnover')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="0"
            value={localAssumptions.assetTurnover || ''}
            onChange={(e) => handleInputChange('assetTurnover', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.assetTurnover ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter turnover ratio"
          />
          <button
            onClick={() => generateAISuggestion('assetTurnover')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
      </div>

      {/* Equity Multiplier */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Equity Multiplier</label>
          <span className="text-sm text-gray-500">Historical: {calculateHistoricalTrend('equityMultiplier')}</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="1"
            value={localAssumptions.equityMultiplier || ''}
            onChange={(e) => handleInputChange('equityMultiplier', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.equityMultiplier ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter multiplier"
          />
          <button
            onClick={() => generateAISuggestion('equityMultiplier')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 AI Suggest
          </button>
        </div>
      </div>
    </div>
  );

  // Render Comps-specific inputs
  const renderCompsInputs = () => (
    <div className="space-y-6">
      {/* Peer Multiple */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Peer Group Average Multiple</label>
          <span className="text-sm text-gray-500">Based on selected peers</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.1"
            min="0"
            value={localAssumptions.peerMultiple || ''}
            onChange={(e) => handleInputChange('peerMultiple', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.peerMultiple ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter multiple (e.g., 12.5x)"
          />
          <button
            onClick={() => generateAISuggestion('peerMultiple')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 Refine Peers
          </button>
        </div>
      </div>

      {/* Suggested Multiple */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Suggested Valuation Multiple</label>
          <span className="text-sm text-gray-500">AI-adjusted for company specifics</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.1"
            min="0"
            value={localAssumptions.suggestedMultiple || ''}
            onChange={(e) => handleInputChange('suggestedMultiple', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.suggestedMultiple ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter multiple"
          />
          <button
            onClick={() => generateAISuggestion('suggestedMultiple')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 Suggest
          </button>
        </div>
      </div>

      {/* Discount Rate */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-2">
          <label className="font-semibold text-gray-700">Private Company Discount</label>
          <span className="text-sm text-gray-500">For illiquidity and size</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={localAssumptions.discountRate || ''}
            onChange={(e) => handleInputChange('discountRate', e.target.value)}
            className={`flex-1 p-2 border rounded ${validationErrors.discountRate ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="Enter discount (e.g., 0.25 for 25%)"
          />
          <button
            onClick={() => generateAISuggestion('discountRate')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            🤖 Apply Discount
          </button>
        </div>
        {validationErrors.discountRate && (
          <p className="text-red-500 text-sm mt-1">{validationErrors.discountRate}</p>
        )}
      </div>
    </div>
  );

  // Render appropriate inputs based on selected model
  const renderModelInputs = () => {
    switch (selectedModel) {
      case 'DCF':
        return renderDCFInputs();
      case 'DuPont':
        return renderDuPontInputs();
      case 'Comps':
        return renderCompsInputs();
      default:
        return <p className="text-gray-500">Please select a valuation model first.</p>;
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-2 text-gray-800">
        Assumption Studio - {selectedModel || 'Select Model'}
      </h2>
      <p className="text-gray-600 mb-6">
        Fine-tune your valuation assumptions with AI assistance or manual overrides
      </p>

      {/* Model-specific inputs */}
      <div className="mb-8">
        {renderModelInputs()}
      </div>

      {/* What-If Preview */}
      {whatIfPreview && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg shadow-md mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">📊 What-If Impact Preview</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-600">Base Value</p>
              <p className="text-xl font-bold text-gray-800">${whatIfPreview.baseValue}M</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">New Value</p>
              <p className={`text-xl font-bold ${whatIfPreview.direction === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                ${whatIfPreview.newValue}M
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">Change</p>
              <p className={`text-xl font-bold ${whatIfPreview.direction === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                {whatIfPreview.direction === 'up' ? '+' : ''}{whatIfPreview.change}%
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3 italic">
            * Preview is mocked - actual calculations will be performed after backend integration
          </p>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8">
        <button
          onClick={onBack}
          className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition"
        >
          ← Back
        </button>
        <button
          onClick={onNext}
          disabled={Object.keys(validationErrors).length > 0}
          className={`px-6 py-3 rounded-lg transition ${
            Object.keys(validationErrors).length > 0
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          Next Step →
        </button>
      </div>
    </div>
  );
};

export default AssumptionStudioStep;
