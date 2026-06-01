import React, { useState } from 'react';
import { ArrowRight, Users, CheckCircle, XCircle, AlertCircle, Search } from 'lucide-react';

/**
 * PeerSelectionStep - Step 4 (Part 2)
 * Displays discovered peers with similarity scores and allows selection
 * Shows match reasons and filters out invalid index tickers
 *
 * STYLED TO MATCH: ResultsStep.jsx (Step 11)
 */
const PeerSelectionStep = ({
  discoveredPeers = [],
  selectedPeers = [],
  onTogglePeer,
  onSelectAll,
  onContinue,
  onBack,
  loading = false,
  onFindPeers = null,
  selectedCompany = null
}) => {
  const [localLoading, setLocalLoading] = useState(false);
  
  // Debug logging for component render
  console.log('[PeerSelectionStep] Render:', {
    selectedCompany: selectedCompany ? selectedCompany.ticker || selectedCompany.symbol : null,
    hasOnFindPeers: !!onFindPeers,
    discoveredPeersCount: discoveredPeers.length,
    loading
  });

  const handleFindPeersAgain = async () => {
    console.log('[PeerSelectionStep] handleFindPeersAgain called:', {
      hasOnFindPeers: !!onFindPeers,
      selectedCompany: selectedCompany ? selectedCompany.ticker || selectedCompany.symbol : null,
      selectedCompanyFull: selectedCompany
    });
    
    if (!onFindPeers) {
      console.error('[PeerSelectionStep] onFindPeers callback is missing');
      return;
    }
    
    if (!selectedCompany) {
      console.error('[PeerSelectionStep] selectedCompany is null or undefined');
      return;
    }

    setLocalLoading(true);
    try {
      console.log('[PeerSelectionStep] Calling onFindPeers with:', selectedCompany.ticker || selectedCompany.symbol);
      await onFindPeers(selectedCompany);
    } catch (err) {
      console.error('[PeerSelectionStep] Failed to find peers:', err);
    } finally {
      setLocalLoading(false);
    }
  };


  const isInvalidPeer = (ticker) => {
    const invalidPatterns = ['^VNI', '^VNINDEX', '^HNX', '^UPCOM'];
    return invalidPatterns.some(pattern => ticker.toUpperCase().includes(pattern));
  };

  const validPeers = discoveredPeers.filter(peer => !isInvalidPeer(peer.ticker || peer.symbol));
  const invalidPeers = discoveredPeers.filter(peer => isInvalidPeer(peer.ticker || peer.symbol));

  const allValidSelected = validPeers.length > 0 &&
    validPeers.every(peer => selectedPeers.includes(peer.ticker || peer.symbol));

  if (discoveredPeers.length === 0 && !loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Step 4: Select Peers</h2>
          <p className="text-slate-600">Review and select comparable companies for your valuation analysis.</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
          <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Users size={40} className="text-slate-400" />
          </div>
          <h3 className="text-xl font-semibold text-slate-900 mb-2">No Peers Discovered Yet</h3>
          <p className="text-slate-600 mb-6 max-w-md mx-auto">
            Click "Find Peers" to automatically discover comparable companies based on your selected valuation model.
          </p>
          {onFindPeers && (
            <button
              onClick={handleFindPeersAgain}
              disabled={localLoading}
              className="px-6 py-3 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-medium hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2 mx-auto disabled:opacity-50"
            >
              {localLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Finding Peers...
                </>
              ) : (
                <>
                  <Search size={18} />
                  Find Peers Now
                </>
              )}
            </button>
          )}
        </div>

        <div className="flex justify-between pt-4">
          <button
            onClick={onBack}
            disabled={loading}
            className="px-6 py-2.5 rounded-lg border border-slate-300 text-slate-700 font-medium hover:bg-slate-50 transition-colors disabled:opacity-50"
          >
            ← Back
          </button>
          <button
            onClick={onContinue}
            disabled={true}
            className="px-6 py-2.5 rounded-lg bg-slate-300 text-slate-500 font-medium cursor-not-allowed flex items-center gap-2"
          >
            Select Peers First
            <ArrowRight size={18} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-slate-900 mb-2">Step 4: Select Peers</h2>
        <p className="text-slate-600">
          Review the discovered peers and select the most comparable companies for your analysis.
        </p>
      </div>

      {/* Summary Bar */}
      {discoveredPeers.length > 0 && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Users size={20} className="text-blue-600" />
              <div>
                <p className="text-sm font-medium text-blue-900">
                  {selectedPeers.length} of {validPeers.length} valid peers selected
                </p>
                {invalidPeers.length > 0 && (
                  <p className="text-xs text-blue-600 mt-1">
                    {invalidPeers.length} invalid index ticker(s) excluded
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onSelectAll}
              className="text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
            >
              {allValidSelected ? 'Deselect All' : 'Select All Valid'}
            </button>
          </div>
        </div>
      )}

      {/* Peers Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Select
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Ticker
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Company Name
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Industry
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Market Cap
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Similarity
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Match Reasons
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {validPeers.map((peer) => {
                const ticker = peer.ticker || peer.symbol;
                const isSelected = selectedPeers.includes(ticker);
                const isInvalid = isInvalidPeer(ticker);

                return (
                  <tr
                    key={ticker}
                    className={`hover:bg-slate-50 transition-colors ${isInvalid ? 'bg-slate-50 opacity-50' : ''}`}
                  >
                    <td className="px-6 py-4">
                      {!isInvalid && (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => onTogglePeer(ticker)}
                          className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                        />
                      )}
                      {isInvalid && (
                        <XCircle size={16} className="text-slate-400" />
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`font-mono text-sm font-semibold ${isInvalid ? 'text-slate-400' : 'text-slate-900'}`}>
                        {ticker}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm ${isInvalid ? 'text-slate-400' : 'text-slate-900'}`}>
                        {peer.company_name || peer.name || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-slate-600">
                        {peer.industry || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-medium text-slate-900">
                        {(() => {
                          const cap = peer.market_cap || peer.marketCap;
                          if (!cap) return 'N/A';
                          if (cap >= 1e12) return `$${(cap / 1e12).toFixed(2)}T`;
                          if (cap >= 1e9) return `$${(cap / 1e9).toFixed(2)}B`;
                          if (cap >= 1e6) return `$${(cap / 1e6).toFixed(2)}M`;
                          return `$${cap.toLocaleString()}`;
                        })()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden max-w-[100px]">
                          <div
                            className={`h-full rounded-full transition-all ${
                              peer.similarity_score >= 80 ? 'bg-green-500' :
                              peer.similarity_score >= 60 ? 'bg-yellow-500' :
                              'bg-orange-500'
                            }`}
                            style={{ width: `${Math.min(peer.similarity_score || 0, 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-slate-700 min-w-[3rem]">
                          {peer.similarity_score?.toFixed(0) || 0}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {(peer.match_reasons || []).slice(0, 2).map((reason, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700"
                          >
                            {reason}
                          </span>
                        ))}
                        {(peer.match_reasons || []).length > 2 && (
                          <span className="text-xs text-slate-500">
                            +{(peer.match_reasons || []).length - 2} more
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Invalid Peers Warning */}
        {invalidPeers.length > 0 && (
          <div className="bg-slate-50 border-t border-slate-200 px-6 py-4">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="text-slate-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-700">
                  {invalidPeers.length} Invalid Ticker(s) Excluded
                </p>
                <p className="text-sm text-slate-600 mt-1">
                  The following tickers appear to be market indices and cannot be used as peers:{' '}
                  <span className="font-mono text-slate-900">
                    {invalidPeers.map(p => p.ticker || p.symbol).join(', ')}
                  </span>
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between items-center pt-4">
        <button
          onClick={onBack}
          disabled={loading}
          className="px-6 py-2.5 rounded-lg border border-slate-300 text-slate-700 font-medium hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          ← Back
        </button>

        <div className="flex gap-4">
          {!loading && discoveredPeers.length > 0 && (
            <button
              onClick={handleFindPeersAgain}
              disabled={localLoading}
              className="px-6 py-2.5 rounded-lg border border-purple-300 text-purple-700 font-medium hover:bg-purple-50 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <Search size={18} />
              Find Peers Again
            </button>
          )}

          <button
            onClick={onContinue}
            disabled={loading || selectedPeers.length === 0}
            className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2 disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {selectedPeers.length === 0 ? (
              <>
                Select at Least One Peer
                <ArrowRight size={18} />
              </>
            ) : (
              <>
                Continue to Requirements
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PeerSelectionStep;