import React from 'react';

const BaselineStep = ({ baselines, modelType, onBack, onContinue, loading }) => {
  if (!baselines) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <h2 className="text-2xl font-bold mb-6">Step 7: Generate Baselines</h2>
        <p className="mb-4">Click below to calculate historical static inputs required for valuation.</p>
        <button
          onClick={onContinue}
          className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
          disabled={loading}
        >
          Generate Baselines
        </button>
      </div>
    );
  }

  const renderDCFBaselines = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">DCF Model - Historical Baselines</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Tax Rate</h4>
          <p className="text-2xl font-bold">{baselines.effective_tax_rate?.value}%</p>
          <p className="text-sm text-gray-600">Range: {baselines.effective_tax_rate?.min}% - {baselines.effective_tax_rate?.max}%</p>
          <p className="text-xs text-gray-500 mt-1">Trend: {baselines.effective_tax_rate?.trend}</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Working Capital % Revenue</h4>
          <p className="text-2xl font-bold">{baselines.working_capital_percent?.value}%</p>
          <p className="text-sm text-gray-600">Range: {baselines.working_capital_percent?.min}% - {baselines.working_capital_percent?.max}%</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">D&A % Revenue</h4>
          <p className="text-2xl font-bold">{baselines.depreciation_percent?.value}%</p>
          <p className="text-sm text-gray-600">Avg: {baselines.depreciation_percent?.avg}%</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">CapEx % Revenue</h4>
          <p className="text-2xl font-bold">{baselines.capex_percent?.value}%</p>
          <p className="text-sm text-gray-600">Avg: {baselines.capex_percent?.avg}%</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Unlevered Beta</h4>
          <p className="text-2xl font-bold">{baselines.unlevered_beta?.value}</p>
          <p className="text-sm text-gray-600">From {baselines.unlevered_beta?.peer_count} peers</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Risk-Free Rate</h4>
          <p className="text-2xl font-bold">{baselines.risk_free_rate?.value}%</p>
          <p className="text-sm text-gray-600">10Y Treasury</p>
        </div>
      </div>
    </div>
  );

  const renderDuPontBaselines = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">DuPont Model - Historical Baselines</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Net Profit Margin</h4>
          <p className="text-2xl font-bold">{baselines.net_margin?.value}%</p>
          <p className="text-sm text-gray-600">Trend: {baselines.net_margin?.trend}</p>
          <p className="text-xs text-gray-500 mt-1">5Y Avg: {baselines.net_margin?.avg}%</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Asset Turnover</h4>
          <p className="text-2xl font-bold">{baselines.asset_turnover?.value}x</p>
          <p className="text-sm text-gray-600">Trend: {baselines.asset_turnover?.trend}</p>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-2">Equity Multiplier</h4>
          <p className="text-2xl font-bold">{baselines.equity_multiplier?.value}x</p>
          <p className="text-sm text-gray-600">Trend: {baselines.equity_multiplier?.trend}</p>
        </div>

        <div className="border rounded p-4 bg-blue-50">
          <h4 className="font-medium mb-2">Historical ROE</h4>
          <p className="text-2xl font-bold">{baselines.historical_roe?.value}%</p>
          <p className="text-xs text-gray-500 mt-1">Decomposition: {baselines.historical_roe?.breakdown}</p>
        </div>
      </div>
    </div>
  );

  const renderCompsBaselines = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Comps Model - Historical Baselines</h3>
      
      <div className="border rounded p-4 mb-4">
        <h4 className="font-medium mb-2">Peer Median Multiples</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-600">P/E Median</p>
            <p className="text-xl font-bold">{baselines.peer_median_pe?.value}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">EV/EBITDA Median</p>
            <p className="text-xl font-bold">{baselines.peer_median_ev_ebitda?.value}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">P/B Median</p>
            <p className="text-xl font-bold">{baselines.peer_median_pb?.value}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">P/S Median</p>
            <p className="text-xl font-bold">{baselines.peer_median_ps?.value}</p>
          </div>
        </div>
      </div>

      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Target Company Current Multiples</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-600">Current P/E</p>
            <p className="text-xl font-bold">{baselines.target_pe?.value}</p>
            <p className="text-xs text-green-600">{baselines.target_pe?.premium_discount}% vs peers</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Current EV/EBITDA</p>
            <p className="text-xl font-bold">{baselines.target_ev_ebitda?.value}</p>
            <p className="text-xs text-green-600">{baselines.target_ev_ebitda?.premium_discount}% vs peers</p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Step 7: Historical Baselines</h2>
      <p className="mb-6 text-gray-600">These are static inputs calculated from historical data. They will be used as starting points for assumptions in Step 8.</p>
      
      {modelType === 'DCF' && renderDCFBaselines()}
      {modelType === 'DuPont' && renderDuPontBaselines()}
      {modelType === 'Comps' && renderCompsBaselines()}

      <div className="flex justify-between mt-8">
        <button
          onClick={onBack}
          className="px-6 py-2 border rounded hover:bg-gray-100"
          disabled={loading}
        >
          ← Back
        </button>
        <button
          onClick={onContinue}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          disabled={loading}
        >
          Continue to Assumption Studio →
        </button>
      </div>
    </div>
  );
};

export default BaselineStep;
