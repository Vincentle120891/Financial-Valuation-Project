import React, { useState } from 'react';

/**
 * PeerSelectionStep - Step 3
 * Displays auto-discovered peer companies with similarity scores in table format
 * Allows users to select/deselect peers for DCF comparison
 */
const PeerSelectionStep = ({
  suggestedPeers,
  selectedPeers,
  onTogglePeer,
  onContinue,
  onBack,
  loading
}) => {
  const [localError, setLocalError] = useState(null);

  const handleTogglePeer = (peer) => {
    setLocalError(null);
    onTogglePeer(peer);
  };

  const handleSelectAll = () => {
    if (selectedPeers.length === suggestedPeers.length) {
      // Deselect all
      suggestedPeers.forEach(peer => {
        if (selectedPeers.find(p => p.symbol === peer.symbol)) {
          onTogglePeer(peer);
        }
      });
    } else {
      // Select all
      suggestedPeers.forEach(peer => {
        if (!selectedPeers.find(p => p.symbol === peer.symbol)) {
          onTogglePeer(peer);
        }
      });
    }
  };

  if (!suggestedPeers || suggestedPeers.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Step 3: Peer Selection
          </h2>
          <p className="text-gray-600">
            No peers discovered yet. Please go back to Step 2 and click "Auto-Find Peers".
          </p>
        </div>

        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
          <p className="text-yellow-700">
            ⚠️ No peer suggestions available. Try searching for a different company or manually add peers in later steps.
          </p>
        </div>

        <div className="mt-8">
          <button
            onClick={onBack}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            ← Back to Company Overview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0" style={{ minWidth: '40px', minHeight: '40px', maxWidth: '40px', maxHeight: '40px' }}>
            <svg className="text-green-600 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '24px', height: '24px', minWidth: '24px', minHeight: '24px', maxWidth: '24px', maxHeight: '24px' }}>
              <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            Step 3: Select Peer Companies
          </h2>
        </div>
        <p className="text-gray-600 ml-13">
          Review and select peer companies for comparable analysis. These peers will be used in DCF valuation for WACC calculation and trading multiples.
        </p>
      </div>

      {/* Summary Bar */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-blue-800 font-medium">
              {selectedPeers.length} of {suggestedPeers.length} peers selected
            </span>
          </div>
          <button
            onClick={handleSelectAll}
            className="text-blue-600 hover:text-blue-800 font-medium text-sm"
          >
            {selectedPeers.length === suggestedPeers.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>
      </div>

      {/* Peer Table */}
      <div className="border rounded-lg overflow-hidden mb-8 shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">Select</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Industry</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Market Cap</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">Similarity Score</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match Reasons</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-24">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {suggestedPeers.map((peer) => {
                const isSelected = selectedPeers.find(p => p.symbol === peer.symbol);
                
                // Detect invalid peers (indices, delisted, etc.)
                const isInvalidPeer = 
                  peer.symbol.startsWith('^') ||
                  peer.symbol.includes('INDEX') ||
                  peer.symbol.includes('IDX') ||
                  !peer.marketCap ||
                  peer.marketCap <= 0;

                return (
                  <tr 
                    key={peer.symbol}
                    className={`transition-all ${
                      isInvalidPeer
                        ? 'bg-red-50 opacity-60'
                        : isSelected
                        ? 'bg-green-50 hover:bg-green-100'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    {/* Select Checkbox */}
                    <td className="px-4 py-3">
                      <button
                        onClick={() => !isInvalidPeer && handleTogglePeer(peer)}
                        disabled={isInvalidPeer}
                        className={`w-6 h-6 rounded flex items-center justify-center transition-all ${
                          isInvalidPeer
                            ? 'bg-gray-200 cursor-not-allowed'
                            : isSelected
                            ? 'bg-green-600 text-white hover:bg-green-700 cursor-pointer'
                            : 'bg-gray-200 text-gray-400 hover:bg-gray-300 cursor-pointer'
                        }`}
                        title={isSelected ? 'Deselect peer' : 'Select peer'}
                      >
                        {isSelected ? (
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                          </svg>
                        )}
                      </button>
                    </td>

                    {/* Ticker */}
                    <td className="px-4 py-3">
                      <span className="text-sm font-semibold text-indigo-600">{peer.symbol}</span>
                    </td>

                    {/* Company Name */}
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">{peer.name}</span>
                    </td>

                    {/* Industry */}
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-700">{peer.industry || 'N/A'}</span>
                    </td>

                    {/* Market Cap */}
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-gray-900">
                        {peer.marketCap ? `$${(() => {
                          const marketCap = peer.marketCap;
                          if (marketCap >= 1e12) return `${(marketCap / 1e12).toFixed(2)}T`;
                          if (marketCap >= 1e9) return `${(marketCap / 1e9).toFixed(2)}B`;
                          if (marketCap >= 1e6) return `${(marketCap / 1e6).toFixed(2)}M`;
                          return marketCap.toLocaleString();
                        })()}` : 'N/A'}
                      </span>
                    </td>

                    {/* Similarity Score with Progress Bar */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className={`font-semibold ${
                            peer.score >= 80 ? 'text-green-600' :
                            peer.score >= 60 ? 'text-yellow-600' : 'text-gray-600'
                          }`}>
                            {peer.score}/100
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              peer.score >= 80 ? 'bg-green-500' :
                              peer.score >= 60 ? 'bg-yellow-500' : 'bg-gray-400'
                            }`}
                            style={{ width: `${peer.score}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Match Reasons */}
                    <td className="px-4 py-3">
                      {peer.match_reasons && peer.match_reasons.length > 0 ? (
                        <ul className="text-xs text-gray-600 space-y-1">
                          {peer.match_reasons.slice(0, 2).map((reason, idx) => (
                            <li key={idx} className="flex items-center gap-1">
                              <svg className="w-3 h-3 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                              <span className="truncate">{reason}</span>
                            </li>
                          ))}
                          {peer.match_reasons.length > 2 && (
                            <li className="text-gray-500">+{peer.match_reasons.length - 2} more</li>
                          )}
                        </ul>
                      ) : (
                        <span className="text-xs text-gray-400">No match reasons</span>
                      )}
                    </td>

                    {/* Status Badge */}
                    <td className="px-4 py-3 text-center">
                      {isInvalidPeer ? (
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-200 text-red-800">
                          ⚠️ Invalid
                        </span>
                      ) : (
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                          isSelected ? 'bg-green-200 text-green-800' : 'bg-gray-200 text-gray-800'
                        }`}>
                          {isSelected ? '✓ Selected' : '○ Not Selected'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Error Message */}
      {localError && (
        <div className="mb-6 bg-red-50 border-l-4 border-red-400 p-4 rounded">
          <p className="text-red-700">{localError}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between items-center mt-8 gap-4">
        <button
          onClick={onBack}
          className="px-6 py-3 border border-gray-300 text-gray-700 bg-white rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
          disabled={loading}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Company Overview
        </button>

        <button
          onClick={onContinue}
          disabled={selectedPeers.length === 0 || loading}
          className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-md"
        >
          Continue to Model Selection
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default PeerSelectionStep;
