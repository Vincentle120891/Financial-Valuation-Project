import React, { useState } from 'react';

/**
 * CompanySelectionStep - Step 2
 * Displays selected company details with sector, industry, and market cap information
 * Provides "Find Peers" button to trigger automatic peer discovery
 */
const CompanySelectionStep = ({ 
  selectedCompany, 
  onFindPeers, 
  onContinue, 
  loading,
  hasPeers = false
}) => {
  const [peerSearchLoading, setPeerSearchLoading] = useState(false);

  const handleFindPeers = async () => {
    setPeerSearchLoading(true);
    try {
      await onFindPeers(selectedCompany);
    } finally {
      setPeerSearchLoading(false);
    }
  };

  if (!selectedCompany) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
          <p className="text-yellow-700">No company selected. Please go back to Step 1.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Step 2: Company Overview
        </h2>
        <p className="text-gray-600">
          Review the selected company details before proceeding to peer selection.
        </p>
      </div>

      {/* Company Details Card */}
      <div className="bg-white shadow-lg rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              {selectedCompany.name || selectedCompany.symbol}
            </h3>
            <p className="text-gray-500 text-sm">{selectedCompany.symbol}</p>
          </div>
          {selectedCompany.exchange && (
            <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
              {selectedCompany.exchange}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          {selectedCompany.sector && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Sector</p>
              <p className="font-medium text-gray-900">{selectedCompany.sector}</p>
            </div>
          )}
          
          {selectedCompany.industry && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Industry</p>
              <p className="font-medium text-gray-900">{selectedCompany.industry}</p>
            </div>
          )}
          
          {selectedCompany.marketCap && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Market Cap</p>
              <p className="font-medium text-gray-900">
                ${selectedCompany.marketCap.toLocaleString()}M
              </p>
            </div>
          )}
          
          {selectedCompany.country && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Country</p>
              <p className="font-medium text-gray-900">{selectedCompany.country}</p>
            </div>
          )}
        </div>

        {selectedCompany.description && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500 mb-2">Description</p>
            <p className="text-gray-700 text-sm leading-relaxed">
              {selectedCompany.description}
            </p>
          </div>
        )}

        {/* Peer Found Success Message */}
        {hasPeers && (
          <div className="mt-6 bg-green-50 border-l-4 border-green-400 p-4 rounded">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-green-700 font-medium">
                Peers discovered! Review and select your peers in the next step.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center mt-8">
        <button
          onClick={() => window.history.back()}
          className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          disabled={loading}
        >
          ← Back to Search
        </button>
        
        <div className="flex gap-4">
          <button
            onClick={handleFindPeers}
            disabled={peerSearchLoading || loading}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {peerSearchLoading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Finding Peers...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Auto-Find Peers
              </>
            )}
          </button>
          
          <button
            onClick={onContinue}
            disabled={!hasPeers || loading}
            className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue to Peer Selection →
          </button>
        </div>
      </div>
    </div>
  );
};

export default CompanySelectionStep;
