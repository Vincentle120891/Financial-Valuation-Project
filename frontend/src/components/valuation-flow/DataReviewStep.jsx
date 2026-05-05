import React from 'react';

const DataReviewStep = ({ reviewedData, modelType, onBack, onContinue, loading }) => {
  if (!reviewedData) {
    return <div className="p-6">Loading data review...</div>;
  }

  const renderDCFData = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">DCF Model - Retrieved Data</h3>
      
      {/* Historical Financials */}
      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Historical Financials</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {reviewedData.historical_financials?.map((year, idx) => (
            <div key={idx} className="text-sm">
              <p className="font-bold">{year.year}</p>
              <p>Revenue: ${year.revenue?.toLocaleString()}</p>
              <p>EBITDA: ${year.ebitda?.toLocaleString()}</p>
              <p>D&A: ${year.depreciation_amortization?.toLocaleString()}</p>
              <p>CapEx: ${year.capex?.toLocaleString()}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Market Data */}
      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Market Data</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>Stock Price: ${reviewedData.market_data?.stock_price}</div>
          <div>Shares: {reviewedData.market_data?.shares_outstanding?.toLocaleString()}</div>
          <div>Beta: {reviewedData.market_data?.beta}</div>
          <div>Total Debt: ${reviewedData.market_data?.total_debt?.toLocaleString()}</div>
          <div>Cash: ${reviewedData.market_data?.cash?.toLocaleString()}</div>
          <div>Market Cap: ${reviewedData.market_data?.market_cap?.toLocaleString()}</div>
        </div>
      </div>

      {/* Calculated Metrics */}
      <div className="border rounded p-4 bg-blue-50">
        <h4 className="font-medium mb-2">Calculated Intermediate Metrics</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>Net Debt: ${reviewedData.calculated_metrics?.net_debt?.toLocaleString()}</div>
          <div>Enterprise Value: ${reviewedData.calculated_metrics?.enterprise_value?.toLocaleString()}</div>
          <div>Avg EBITDA Margin: {reviewedData.calculated_metrics?.avg_ebitda_margin}%</div>
          <div>Revenue Growth: {reviewedData.calculated_metrics?.revenue_growth}%</div>
        </div>
      </div>
    </div>
  );

  const renderDuPontData = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">DuPont Model - Retrieved Data</h3>
      
      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Income Statement</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>Net Income: ${reviewedData.income_statement?.net_income?.toLocaleString()}</div>
          <div>Revenue: ${reviewedData.income_statement?.revenue?.toLocaleString()}</div>
          <div>Operating Income: ${reviewedData.income_statement?.operating_income?.toLocaleString()}</div>
        </div>
      </div>

      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Balance Sheet</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>Total Assets: ${reviewedData.balance_sheet?.total_assets?.toLocaleString()}</div>
          <div>Equity: ${reviewedData.balance_sheet?.equity?.toLocaleString()}</div>
          <div>Liabilities: ${reviewedData.balance_sheet?.liabilities?.toLocaleString()}</div>
        </div>
      </div>

      <div className="border rounded p-4 bg-blue-50">
        <h4 className="font-medium mb-2">Calculated Ratios</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>Net Margin: {reviewedData.calculated_ratios?.net_margin}%</div>
          <div>Asset Turnover: {reviewedData.calculated_ratios?.asset_turnover}</div>
          <div>Equity Multiplier: {reviewedData.calculated_ratios?.equity_multiplier}</div>
          <div>ROE: {reviewedData.calculated_ratios?.roe}%</div>
        </div>
      </div>
    </div>
  );

  const renderCompsData = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Comps Model - Retrieved Data</h3>
      
      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Target Company</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>Market Cap: ${reviewedData.target_company?.market_cap?.toLocaleString()}</div>
          <div>EV: ${reviewedData.target_company?.enterprise_value?.toLocaleString()}</div>
          <div>P/E: {reviewedData.target_company?.pe_ratio}</div>
          <div>EV/EBITDA: {reviewedData.target_company?.ev_ebitda}</div>
        </div>
      </div>

      <div className="border rounded p-4">
        <h4 className="font-medium mb-2">Peer Companies</h4>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">Peer</th>
                <th className="text-right p-2">P/E</th>
                <th className="text-right p-2">EV/EBITDA</th>
                <th className="text-right p-2">P/B</th>
                <th className="text-right p-2">P/S</th>
              </tr>
            </thead>
            <tbody>
              {reviewedData.peers?.map((peer, idx) => (
                <tr key={idx} className="border-b">
                  <td className="p-2">{peer.name}</td>
                  <td className="text-right p-2">{peer.pe_ratio}</td>
                  <td className="text-right p-2">{peer.ev_ebitda}</td>
                  <td className="text-right p-2">{peer.pb_ratio}</td>
                  <td className="text-right p-2">{peer.ps_ratio}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Step 6: Data Review</h2>
      
      {modelType === 'DCF' && renderDCFData()}
      {modelType === 'DuPont' && renderDuPontData()}
      {modelType === 'Comps' && renderCompsData()}

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
          Continue to Baselines →
        </button>
      </div>
    </div>
  );
};

export default DataReviewStep;
