import React from 'react';

const DataReviewStep = ({ reviewedData, modelType, onBack, onContinue, loading }) => {
  if (!reviewedData) {
    return <div className="p-6">Loading data review...</div>;
  }

  // Helper to determine status badge color and label
  const getStatusBadge = (status) => {
    switch (status) {
      case 'RETRIEVED':
        return <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">Retrieved</span>;
      case 'CALCULATED':
        return <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">Calculated</span>;
      case 'MISSING':
        return <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">Missing</span>;
      case 'MANUAL_OVERRIDE':
        return <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">Manual</span>;
      default:
        return <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-800">Unknown</span>;
    }
  };

  // Helper to render a data field with status
  const renderField = (label, value, status, isMissing = false) => {
    const baseClasses = "text-sm p-2 rounded";
    const missingClasses = isMissing || status === 'MISSING' 
      ? "bg-red-50 border border-red-200" 
      : "bg-white";
    
    return (
      <div className={`${baseClasses} ${missingClasses}`}>
        <div className="flex justify-between items-center mb-1">
          <span className="font-medium text-gray-700">{label}</span>
          {status && getStatusBadge(status)}
        </div>
        <div className={isMissing || status === 'MISSING' ? "text-red-600 font-semibold" : "text-gray-900"}>
          {value !== null && value !== undefined ? value : 'N/A'}
        </div>
      </div>
    );
  };

  // Render missing data summary alert
  const renderMissingDataSummary = () => {
    const missingData = reviewedData.missing_data_summary || [];
    if (missingData.length === 0) {
      return (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-green-800 font-medium">All required data retrieved successfully!</span>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-center mb-3">
          <svg className="w-5 h-5 text-red-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-red-800 font-semibold">
            Missing Data Alert: {missingData.length} field(s) require attention
          </span>
        </div>
        <p className="text-red-700 text-sm mb-3">
          The following fields could not be retrieved or calculated. You will be able to provide manual inputs in Step 9.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {missingData.map((item, idx) => (
            <div key={idx} className="bg-white border border-red-200 rounded px-3 py-2 text-sm">
              <span className="font-medium text-red-700">{item.field_name || item}</span>
              {item.category && (
                <span className="text-gray-500 ml-2">({item.category})</span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderDCFData = () => {
    const historicalFinancials = reviewedData.historical_financials || [];
    const marketData = reviewedData.market_data || {};
    const calculatedMetrics = reviewedData.calculated_metrics || {};

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold">DCF Model - Retrieved Data</h3>
        
        {/* Historical Financials */}
        <div className="border rounded p-4">
          <h4 className="font-medium mb-3 flex items-center">
            Historical Financials
            {historicalFinancials.some(y => y.data_status?.revenue === 'MISSING' || y.data_status?.ebitda === 'MISSING') && (
              <span className="ml-2 px-2 py-1 text-xs rounded bg-red-100 text-red-800">Has Missing Data</span>
            )}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {historicalFinancials.map((year, idx) => (
              <div key={idx} className={`border rounded p-3 ${year.data_status?.revenue === 'MISSING' ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
                <p className="font-bold mb-2">{year.year}</p>
                {renderField('Revenue', year.revenue ? `$${year.revenue.toLocaleString()}` : 'N/A', year.data_status?.revenue)}
                {renderField('EBITDA', year.ebitda ? `$${year.ebitda.toLocaleString()}` : 'N/A', year.data_status?.ebitda)}
                {renderField('D&A', year.depreciation_amortization ? `$${year.depreciation_amortization.toLocaleString()}` : 'N/A', year.data_status?.depreciation_amortization)}
                {renderField('CapEx', year.capex ? `$${year.capex.toLocaleString()}` : 'N/A', year.data_status?.capex)}
              </div>
            ))}
          </div>
        </div>

        {/* Market Data */}
        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Market Data</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Stock Price', marketData.stock_price ? `$${marketData.stock_price}` : 'N/A', marketData.status_stock_price)}
            {renderField('Shares Outstanding', marketData.shares_outstanding ? marketData.shares_outstanding.toLocaleString() : 'N/A', marketData.status_shares_outstanding)}
            {renderField('Beta', marketData.beta, marketData.status_beta)}
            {renderField('Total Debt', marketData.total_debt ? `$${marketData.total_debt.toLocaleString()}` : 'N/A', marketData.status_total_debt)}
            {renderField('Cash', marketData.cash ? `$${marketData.cash.toLocaleString()}` : 'N/A', marketData.status_cash)}
            {renderField('Market Cap', marketData.market_cap ? `$${marketData.market_cap.toLocaleString()}` : 'N/A', marketData.status_market_cap)}
          </div>
        </div>

        {/* Calculated Metrics */}
        <div className="border rounded p-4 bg-blue-50">
          <h4 className="font-medium mb-3">Calculated Intermediate Metrics</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {renderField('Net Debt', calculatedMetrics.net_debt ? `$${calculatedMetrics.net_debt.toLocaleString()}` : 'N/A', calculatedMetrics.status_net_debt)}
            {renderField('Enterprise Value', calculatedMetrics.enterprise_value ? `$${calculatedMetrics.enterprise_value.toLocaleString()}` : 'N/A', calculatedMetrics.status_enterprise_value)}
            {renderField('Avg EBITDA Margin', calculatedMetrics.avg_ebitda_margin ? `${calculatedMetrics.avg_ebitda_margin}%` : 'N/A', calculatedMetrics.status_avg_ebitda_margin)}
            {renderField('Revenue Growth', calculatedMetrics.revenue_growth ? `${calculatedMetrics.revenue_growth}%` : 'N/A', calculatedMetrics.status_revenue_growth)}
          </div>
        </div>
      </div>
    );
  };

  const renderDuPontData = () => {
    const incomeStatement = reviewedData.income_statement || {};
    const balanceSheet = reviewedData.balance_sheet || {};
    const calculatedRatios = reviewedData.calculated_ratios || {};

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold">DuPont Model - Retrieved Data</h3>
        
        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Income Statement</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Net Income', incomeStatement.net_income ? `$${incomeStatement.net_income.toLocaleString()}` : 'N/A', incomeStatement.status_net_income)}
            {renderField('Revenue', incomeStatement.revenue ? `$${incomeStatement.revenue.toLocaleString()}` : 'N/A', incomeStatement.status_revenue)}
            {renderField('Operating Income', incomeStatement.operating_income ? `$${incomeStatement.operating_income.toLocaleString()}` : 'N/A', incomeStatement.status_operating_income)}
          </div>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Balance Sheet</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Total Assets', balanceSheet.total_assets ? `$${balanceSheet.total_assets.toLocaleString()}` : 'N/A', balanceSheet.status_total_assets)}
            {renderField('Equity', balanceSheet.equity ? `$${balanceSheet.equity.toLocaleString()}` : 'N/A', balanceSheet.status_equity)}
            {renderField('Liabilities', balanceSheet.liabilities ? `$${balanceSheet.liabilities.toLocaleString()}` : 'N/A', balanceSheet.status_liabilities)}
          </div>
        </div>

        <div className="border rounded p-4 bg-blue-50">
          <h4 className="font-medium mb-3">Calculated Ratios</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Net Margin', calculatedRatios.net_margin ? `${calculatedRatios.net_margin}%` : 'N/A', calculatedRatios.status_net_margin)}
            {renderField('Asset Turnover', calculatedRatios.asset_turnover, calculatedRatios.status_asset_turnover)}
            {renderField('Equity Multiplier', calculatedRatios.equity_multiplier, calculatedRatios.status_equity_multiplier)}
            {renderField('ROE', calculatedRatios.roe ? `${calculatedRatios.roe}%` : 'N/A', calculatedRatios.status_roe)}
          </div>
        </div>
      </div>
    );
  };

  const renderCompsData = () => {
    const targetCompany = reviewedData.target_company || {};
    const peers = reviewedData.peers || [];

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold">Comps Model - Retrieved Data</h3>
        
        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Target Company</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {renderField('Market Cap', targetCompany.market_cap ? `$${targetCompany.market_cap.toLocaleString()}` : 'N/A', targetCompany.status_market_cap)}
            {renderField('Enterprise Value', targetCompany.enterprise_value ? `$${targetCompany.enterprise_value.toLocaleString()}` : 'N/A', targetCompany.status_enterprise_value)}
            {renderField('P/E Ratio', targetCompany.pe_ratio, targetCompany.status_pe_ratio)}
            {renderField('EV/EBITDA', targetCompany.ev_ebitda, targetCompany.status_ev_ebitda)}
          </div>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Peer Companies</h4>
          {peers.length === 0 ? (
            <div className="text-sm text-gray-500 italic p-4">No peer companies data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Peer</th>
                    <th className="text-right p-2">P/E</th>
                    <th className="text-right p-2">EV/EBITDA</th>
                    <th className="text-right p-2">P/B</th>
                    <th className="text-right p-2">P/S</th>
                    <th className="text-right p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {peers.map((peer, idx) => (
                    <tr key={idx} className={`border-b ${peer.data_status === 'MISSING' ? 'bg-red-50' : ''}`}>
                      <td className="p-2 font-medium">{peer.name}</td>
                      <td className={`text-right p-2 ${peer.status_pe_ratio === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                        {peer.pe_ratio !== null && peer.pe_ratio !== undefined ? peer.pe_ratio : 'N/A'}
                      </td>
                      <td className={`text-right p-2 ${peer.status_ev_ebitda === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                        {peer.ev_ebitda !== null && peer.ev_ebitda !== undefined ? peer.ev_ebitda : 'N/A'}
                      </td>
                      <td className={`text-right p-2 ${peer.status_pb_ratio === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                        {peer.pb_ratio !== null && peer.pb_ratio !== undefined ? peer.pb_ratio : 'N/A'}
                      </td>
                      <td className={`text-right p-2 ${peer.status_ps_ratio === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                        {peer.ps_ratio !== null && peer.ps_ratio !== undefined ? peer.ps_ratio : 'N/A'}
                      </td>
                      <td className="text-right p-2">
                        {getStatusBadge(peer.data_status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Step 6: Data Review</h2>
      
      {/* Missing Data Summary - Always shown at top */}
      {renderMissingDataSummary()}
      
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
