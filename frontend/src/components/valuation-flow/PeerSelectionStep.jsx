import React, { useState } from 'react';

/**
 * PeerSelectionStep - Step 3
 * Displays auto-discovered peer companies with similarity scores
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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Step 3: Select Peer Companies
        </h2>
        <p className="text-gray-600">
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

      {/* Peer Cards Grid */}
      <div className="max-w-7xl grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-8">
        {suggestedPeers.map((peer) => {
          const isSelected = selectedPeers.find(p => p.symbol === peer.symbol);

          return (
            <div
              key={peer.symbol}
              onClick={() => handleTogglePeer(peer)}
              className={`w-full cursor-pointer rounded-lg p-4 border-2 transition-all ${
                isSelected
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{peer.symbol}</h3>
                  <p className="text-sm text-gray-500 truncate">{peer.name}</p>
                </div>
                {isSelected && (
                  <svg className="w-6 h-6 text-green-600 flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                )}
              </div>

              {/* Similarity Score */}
              <div className="mb-3">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-600">Similarity Score</span>
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

              {/* Match Reasons */}
              {peer.match_reasons && peer.match_reasons.length > 0 && (
                <div className="space-y-1 mb-3">
                  {peer.match_reasons.slice(0, 3).map((reason, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-gray-600">
                      <svg className="w-3 h-3 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      <span className="truncate">{reason}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Additional Info */}
              <div className="mt-auto pt-3 border-t border-gray-200 grid grid-cols-2 gap-2 text-xs">
                {peer.industry && (
                  <div className="min-w-0">
                    <span className="text-gray-500">Industry:</span>
                    <span className="ml-1 text-gray-700 truncate block">{peer.industry}</span>
                  </div>
                )}
                {peer.marketCap && (
                  <div className="min-w-0">
                    <span className="text-gray-500">Market Cap:</span>
                    <span className="ml-1 text-gray-700">
                      ${(() => {
                        const marketCap = peer.marketCap;
                        if (marketCap >= 1e12) return `${(marketCap / 1e12).toFixed(2)}T`;
                        if (marketCap >= 1e9) return `${(marketCap / 1e9).toFixed(2)}B`;
                        if (marketCap >= 1e6) return `${(marketCap / 1e6).toFixed(2)}M`;
                        return marketCap.toLocaleString();
                      })()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error Message */}
      {localError && (
        <div className="mb-6 bg-red-50 border-l-4 border-red-400 p-4 rounded">
          <p className="text-red-700">{localError}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between items-center mt-8">
        <button
          onClick={onBack}
          className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          disabled={loading}
        >
          ← Back to Company Overview
        </button>

        <button
          onClick={onContinue}
          disabled={selectedPeers.length === 0 || loading}
          className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue to Model Selection →
        </button>
      </div>
    </div>
  );
};

export default PeerSelectionStep;