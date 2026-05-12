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
    const historicalFinancials = reviewedData.historical_financials || {};
    const marketData = reviewedData.market_data || {};
    const calculatedMetrics = reviewedData.calculated_metrics || {};

    // Extract years from any available field in historical_financials
    const getYearsFromHistoricalData = () => {
      const firstField = Object.values(historicalFinancials).find(
        field => field && field.value && Array.isArray(field.value)
      );
      if (firstField && firstField.value) {
        return firstField.value.map(pv => pv.period).filter(Boolean);
      }
      return [];
    };

    const years = getYearsFromHistoricalData();

    // Helper to extract value for a specific year from DataField structure
    const getValueForYear = (fieldData, year) => {
      if (!fieldData || !fieldData.value) return null;
      if (Array.isArray(fieldData.value)) {
        const periodValue = fieldData.value.find(pv => pv.period === year);
        return periodValue ? periodValue.value : null;
      }
      return fieldData.value;
    };

    // Helper to get status for a field
    const getStatusForField = (fieldData) => {
      if (!fieldData) return 'MISSING';
      if (fieldData.is_missing) return 'MISSING';
      return fieldData.status || 'RETRIEVED';
    };

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold">DCF Model - Retrieved Data</h3>

        {/* Historical Financials */}
        <div className="border rounded p-4">
          <h4 className="font-medium mb-3 flex items-center">
            Historical Financials
            {(historicalFinancials.revenue?.is_missing || historicalFinancials.ebitda?.is_missing) && (
              <span className="ml-2 px-2 py-1 text-xs rounded bg-red-100 text-red-800">Has Missing Data</span>
            )}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {years.length === 0 ? (
              <div className="text-sm text-gray-500 italic p-4">No historical data available</div>
            ) : (
              years.map((year, idx) => (
                <div key={idx} className={`border rounded p-3 ${getStatusForField(historicalFinancials.revenue) === 'MISSING' ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
                  <p className="font-bold mb-2">{year}</p>
                  {renderField('Revenue', getValueForYear(historicalFinancials.revenue, year) ? `$${getValueForYear(historicalFinancials.revenue, year).toLocaleString()}` : 'N/A', getStatusForField(historicalFinancials.revenue))}
                  {renderField('EBITDA', getValueForYear(historicalFinancials.ebitda, year) ? `$${getValueForYear(historicalFinancials.ebitda, year).toLocaleString()}` : 'N/A', getStatusForField(historicalFinancials.ebitda))}
                  {renderField('D&A', getValueForYear(historicalFinancials.depreciation, year) ? `$${getValueForYear(historicalFinancials.depreciation, year).toLocaleString()}` : 'N/A', getStatusForField(historicalFinancials.depreciation))}
                  {renderField('CapEx', getValueForYear(historicalFinancials.capex, year) ? `$${getValueForYear(historicalFinancials.capex, year).toLocaleString()}` : 'N/A', getStatusForField(historicalFinancials.capex))}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Market Data */}
        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Market Data</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Stock Price', marketData.current_stock_price?.value ? `$${marketData.current_stock_price.value}` : 'N/A', marketData.current_stock_price?.status)}
            {renderField('Shares Outstanding', marketData.shares_outstanding?.value ? marketData.shares_outstanding.value.toLocaleString() : 'N/A', marketData.shares_outstanding?.status)}
            {renderField('Beta', marketData.beta?.value, marketData.beta?.status)}
            {renderField('Total Debt', marketData.total_debt?.value ? `$${marketData.total_debt.value.toLocaleString()}` : 'N/A', marketData.total_debt?.status)}
            {renderField('Cash', marketData.cash?.value ? `$${marketData.cash.value.toLocaleString()}` : 'N/A', marketData.cash?.status)}
            {renderField('Market Cap', marketData.market_cap?.value ? `$${marketData.market_cap.value.toLocaleString()}` : 'N/A', marketData.market_cap?.status)}
          </div>
        </div>

        {/* Calculated Metrics */}
        <div className="border rounded p-4 bg-blue-50">
          <h4 className="font-medium mb-3">Calculated Intermediate Metrics</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {renderField('Net Debt', calculatedMetrics.net_debt?.value ? `$${calculatedMetrics.net_debt.value.toLocaleString()}` : 'N/A', calculatedMetrics.net_debt?.status)}
            {renderField('Enterprise Value', calculatedMetrics.enterprise_value?.value ? `$${calculatedMetrics.enterprise_value.value.toLocaleString()}` : 'N/A', calculatedMetrics.enterprise_value?.status)}
            {renderField('Avg EBITDA Margin', calculatedMetrics.avg_ebitda_margin?.value ? `${calculatedMetrics.avg_ebitda_margin.value}%` : 'N/A', calculatedMetrics.avg_ebitda_margin?.status)}
            {renderField('Revenue Growth', calculatedMetrics.revenue_growth?.value ? `${calculatedMetrics.revenue_growth.value}%` : 'N/A', calculatedMetrics.revenue_growth?.status)}
          </div>
        </div>
      </div>
    );
  };

  const renderDuPontData = () => {
    const dupontMetrics = reviewedData.dupont_metrics || {};

    // Helper to extract value from DataField structure
    const getValueFromDataField = (fieldData) => {
      if (!fieldData) return null;
      if (fieldData.value !== undefined) return fieldData.value;
      return null;
    };

    const getStatusFromDataField = (fieldData) => {
      if (!fieldData) return 'MISSING';
      if (fieldData.is_missing) return 'MISSING';
      return fieldData.status || 'RETRIEVED';
    };

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold">DuPont Model - Retrieved Data</h3>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Income Statement Components</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Net Income', getValueFromDataField(dupontMetrics.net_income) ? `$${getValueFromDataField(dupontMetrics.net_income).toLocaleString()}` : 'N/A', getStatusFromDataField(dupontMetrics.net_income))}
            {renderField('Revenue', getValueFromDataField(dupontMetrics.revenue) ? `$${getValueFromDataField(dupontMetrics.revenue).toLocaleString()}` : 'N/A', getStatusFromDataField(dupontMetrics.revenue))}
            {renderField('Operating Income', getValueFromDataField(dupontMetrics.operating_income) ? `$${getValueFromDataField(dupontMetrics.operating_income).toLocaleString()}` : 'N/A', getStatusFromDataField(dupontMetrics.operating_income))}
          </div>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Balance Sheet Components</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Total Assets', getValueFromDataField(dupontMetrics.total_assets) ? `$${getValueFromDataField(dupontMetrics.total_assets).toLocaleString()}` : 'N/A', getStatusFromDataField(dupontMetrics.total_assets))}
            {renderField('Equity', getValueFromDataField(dupontMetrics.equity) ? `$${getValueFromDataField(dupontMetrics.equity).toLocaleString()}` : 'N/A', getStatusFromDataField(dupontMetrics.equity))}
            {renderField('Liabilities', getValueFromDataField(dupontMetrics.liabilities) ? `$${getValueFromDataField(dupontMetrics.liabilities).toLocaleString()}` : 'N/A', getStatusFromDataField(dupontMetrics.liabilities))}
          </div>
        </div>

        <div className="border rounded p-4 bg-blue-50">
          <h4 className="font-medium mb-3">Calculated Ratios</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {renderField('Net Margin', getValueFromDataField(dupontMetrics.net_margin) ? `${getValueFromDataField(dupontMetrics.net_margin)}%` : 'N/A', getStatusFromDataField(dupontMetrics.net_margin))}
            {renderField('Asset Turnover', getValueFromDataField(dupontMetrics.asset_turnover), getStatusFromDataField(dupontMetrics.asset_turnover))}
            {renderField('Equity Multiplier', getValueFromDataField(dupontMetrics.equity_multiplier), getStatusFromDataField(dupontMetrics.equity_multiplier))}
            {renderField('ROE', getValueFromDataField(dupontMetrics.roe) ? `${getValueFromDataField(dupontMetrics.roe)}%` : 'N/A', getStatusFromDataField(dupontMetrics.roe))}
          </div>
        </div>
      </div>
    );
  };

  const renderCompsData = () => {
    const compsMultiples = reviewedData.comps_multiples || {};
    const targetCompany = compsMultiples.target_company || {};
    const peerCompanies = compsMultiples.peer_companies || [];

    // Helper to extract value from DataField structure
    const getValueFromDataField = (fieldData) => {
      if (!fieldData) return null;
      if (fieldData.value !== undefined) return fieldData.value;
      return null;
    };

    const getStatusFromDataField = (fieldData) => {
      if (!fieldData) return 'MISSING';
      if (fieldData.is_missing) return 'MISSING';
      return fieldData.status || 'RETRIEVED';
    };

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold">Comps Model - Retrieved Data</h3>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Target Company</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {renderField('Market Cap', getValueFromDataField(targetCompany.market_cap) ? `$${getValueFromDataField(targetCompany.market_cap).toLocaleString()}` : 'N/A', getStatusFromDataField(targetCompany.market_cap))}
            {renderField('Enterprise Value', getValueFromDataField(targetCompany.enterprise_value) ? `$${getValueFromDataField(targetCompany.enterprise_value).toLocaleString()}` : 'N/A', getStatusFromDataField(targetCompany.enterprise_value))}
            {renderField('P/E Ratio', getValueFromDataField(targetCompany.pe_ratio), getStatusFromDataField(targetCompany.pe_ratio))}
            {renderField('EV/EBITDA', getValueFromDataField(targetCompany.ev_ebitda), getStatusFromDataField(targetCompany.ev_ebitda))}
          </div>
        </div>

        <div className="border rounded p-4">
          <h4 className="font-medium mb-3">Peer Companies</h4>
          {peerCompanies.length === 0 ? (
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
                  {peerCompanies.map((peer, idx) => {
                    const peRatio = getValueFromDataField(peer.pe_ratio);
                    const evEbitda = getValueFromDataField(peer.ev_ebitda);
                    const pbRatio = getValueFromDataField(peer.pb_ratio);
                    const psRatio = getValueFromDataField(peer.ps_ratio);
                    const status = getStatusFromDataField(peer.pe_ratio) || getStatusFromDataField(peer.ev_ebitda);

                    return (
                      <tr key={idx} className={`border-b ${status === 'MISSING' ? 'bg-red-50' : ''}`}>
                        <td className="p-2 font-medium">{peer.name || peer.ticker}</td>
                        <td className={`text-right p-2 ${status === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                          {peRatio !== null && peRatio !== undefined ? peRatio : 'N/A'}
                        </td>
                        <td className={`text-right p-2 ${getStatusFromDataField(peer.ev_ebitda) === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                          {evEbitda !== null && evEbitda !== undefined ? evEbitda : 'N/A'}
                        </td>
                        <td className={`text-right p-2 ${getStatusFromDataField(peer.pb_ratio) === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                          {pbRatio !== null && pbRatio !== undefined ? pbRatio : 'N/A'}
                        </td>
                        <td className={`text-right p-2 ${getStatusFromDataField(peer.ps_ratio) === 'MISSING' ? 'text-red-600 font-semibold' : ''}`}>
                          {psRatio !== null && psRatio !== undefined ? psRatio : 'N/A'}
                        </td>
                        <td className="text-right p-2">
                          {getStatusBadge(status)}
                        </td>
                      </tr>
                    );
                  })}
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