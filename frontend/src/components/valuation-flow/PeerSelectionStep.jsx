import React, { useState } from 'react';

/**
 * PeerSelectionStep - Step 3
 * Displays auto-discovered peer companies with similarity scores in table format
 * Allows users to select/deselect peers for valuation models
 * 
 * STYLED TO MATCH: ResultsStep.jsx (Step 8)
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
      suggestedPeers.forEach(peer => {
        const peerId = peer.symbol || peer.ticker;
        if (selectedPeers.find(p => (p.symbol || p.ticker) === peerId)) {
          onTogglePeer(peer);
        }
      });
    } else {
      suggestedPeers.forEach(peer => {
        const peerId = peer.symbol || peer.ticker;
        if (!selectedPeers.find(p => (p.symbol || p.ticker) === peerId)) {
          onTogglePeer(peer);
        }
      });
    }
  };

  if (!suggestedPeers || suggestedPeers.length === 0) {
    return (
      <div className="step-container">
        <h2>Step 3: Peer Selection</h2>
        <p className="text-gray-600" style={{ marginBottom: '24px' }}>
          No peers discovered yet. Please go back to Step 2 and click "Auto-Find Peers".
        </p>

        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
          <p className="text-yellow-700">
            ⚠️ No peer suggestions available. Try searching for a different company or manually add peers in later steps.
          </p>
        </div>

        <div className="mt-8">
          <button onClick={onBack} className="btn-secondary">
            ← Back to Company Overview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="step-container">
      <h2>Step 3: Select Peer Companies</h2>
      <p style={{ marginBottom: '24px', color: '#666' }}>
        Review and select peer companies for comparable analysis. These peers will be used in DCF valuation for WACC calculation and trading multiples.
      </p>

      {/* Summary Bar */}
      <div className="summary-box" style={{ marginBottom: '24px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
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
      <div className="summary-box" style={{ marginBottom: '24px', padding: '0', overflow: 'hidden' }}>
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
                const peerId = peer.symbol || peer.ticker;
                const isSelected = selectedPeers.find(p => (p.symbol || p.ticker) === peerId);
                
                const isInvalidPeer = 
                  peer.symbol?.startsWith('^') ||
                  peer.ticker?.startsWith('^') ||
                  peer.symbol?.includes('INDEX') ||
                  peer.ticker?.includes('INDEX') ||
                  peer.symbol?.includes('IDX') ||
                  peer.ticker?.includes('IDX') ||
                  !peer.marketCap ||
                  peer.marketCap <= 0;

                const ticker = peer.ticker || peer.symbol;
                const name = peer.company_name || peer.name;

                return (
                  <tr 
                    key={ticker}
                    className={`transition-all ${
                      isInvalidPeer
                        ? 'bg-red-50 opacity-60'
                        : isSelected
                        ? 'bg-green-50 hover:bg-green-100'
                        : 'hover:bg-gray-50'
                    }`}
                  >
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

                    <td className="px-4 py-3">
                      <span className="text-sm font-semibold text-indigo-600">{ticker}</span>
                    </td>

                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">{name}</span>
                    </td>

                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-700">{peer.industry || 'N/A'}</span>
                    </td>

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

      {localError && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded" style={{ marginBottom: '24px' }}>
          <p className="text-red-700">{localError}</p>
        </div>
      )}

      <div className="flex justify-between items-center mt-8 gap-4">
        <button
          onClick={onBack}
          className="btn-secondary"
          disabled={loading}
        >
          ← Back to Company Overview
        </button>

        <button
          onClick={onContinue}
          disabled={selectedPeers.length === 0 || loading}
          className="btn-success"
        >
          Continue to Step 4: Model Selection →
        </button>
      </div>
    </div>
  );
};

export default PeerSelectionStep;
