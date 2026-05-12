import React from 'react';

/**
 * InternationalMarketData Component - Step 2
 * Displays international market information in table format including:
 * - Market/exchange details
 * - Currency information
 * - Data availability status
 * - Regional peers
 */
const InternationalMarketData = ({ internationalData }) => {
  if (!internationalData) return null;

  const {
    ticker_info,
    market_info,
    currency_info,
    data_availability,
    regional_peers
  } = internationalData;

  // Helper to render status badge
  const getStatusBadge = (isAvailable) => {
    return isAvailable 
      ? <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">✓ Available</span>
      : <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">✗ Not Available</span>;
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Step 2: International Market Data</h2>
      
      {/* Ticker Basic Info Table */}
      {ticker_info && (
        <div className="border rounded-lg overflow-hidden mb-6 shadow-sm">
          <div className="bg-indigo-50 px-4 py-3 border-b border-indigo-200">
            <h3 className="font-semibold text-indigo-900">Company Information</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50 w-1/3">Ticker</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{ticker_info.symbol}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Company Name</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{ticker_info.name}</td>
                </tr>
                {ticker_info.sector && (
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Sector</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{ticker_info.sector}</td>
                  </tr>
                )}
                {ticker_info.industry && (
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Industry</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{ticker_info.industry}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Market Information Table */}
      {market_info && (
        <div className="border rounded-lg overflow-hidden mb-6 shadow-sm">
          <div className="bg-blue-50 px-4 py-3 border-b border-blue-200">
            <h3 className="font-semibold text-blue-900">Market Information</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50 w-1/3">Exchange</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{market_info.exchange_name}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Market Code</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{market_info.market_code}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Region</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{market_info.region}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Trading Hours</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{market_info.trading_hours}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Currency Information Table */}
      {currency_info && (
        <div className="border rounded-lg overflow-hidden mb-6 shadow-sm">
          <div className="bg-green-50 px-4 py-3 border-b border-green-200">
            <h3 className="font-semibold text-green-900">Currency Information</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50 w-1/3">Local Currency</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{currency_info.currency_code} ({currency_info.currency_name})</td>
                </tr>
                {currency_info.usd_exchange_rate && (
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">USD/{currency_info.currency_code} Rate</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{currency_info.usd_exchange_rate.toFixed(4)}</td>
                  </tr>
                )}
                {currency_info.market_cap_usd && (
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50">Market Cap (USD)</td>
                    <td className="px-4 py-3 text-sm text-gray-900">${currency_info.market_cap_usd.toLocaleString()}M</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Data Availability Table */}
      {data_availability && (
        <div className="border rounded-lg overflow-hidden mb-6 shadow-sm">
          <div className="bg-purple-50 px-4 py-3 border-b border-purple-200">
            <h3 className="font-semibold text-purple-900">Data Availability</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700">Financial Statements</td>
                  <td className="px-4 py-3 text-sm">{getStatusBadge(data_availability.financials)}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700">Analyst Estimates</td>
                  <td className="px-4 py-3 text-sm">{getStatusBadge(data_availability.estimates)}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700">Historical Prices</td>
                  <td className="px-4 py-3 text-sm">{getStatusBadge(data_availability.historical_prices)}</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-700">Key Statistics</td>
                  <td className="px-4 py-3 text-sm">{getStatusBadge(data_availability.key_stats)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          {data_availability.warnings && data_availability.warnings.length > 0 && (
            <div className="bg-yellow-50 border-t border-yellow-200 px-4 py-3">
              <p className="text-sm font-medium text-yellow-800 mb-2">Warnings:</p>
              <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                {data_availability.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Regional Peers Table */}
      {regional_peers && regional_peers.length > 0 && (
        <div className="border rounded-lg overflow-hidden mb-6 shadow-sm">
          <div className="bg-orange-50 px-4 py-3 border-b border-orange-200">
            <h3 className="font-semibold text-orange-900">Regional Peers ({regional_peers.length})</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company Name</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Market Cap</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {regional_peers.map((peer, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-indigo-600">{peer.symbol}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{peer.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">
                      {peer.market_cap ? `$${peer.market_cap.toLocaleString()}M` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default InternationalMarketData;
