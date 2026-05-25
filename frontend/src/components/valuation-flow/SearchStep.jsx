import React, { useState } from 'react';
import { searchVietnameseStocks } from '../../services/api';
import ApiKeyModal from '../ApiKeyModal';

/**
 * SearchStep Component
 * Step 1: Input Company Name or Ticker
 *
 * Features:
 * - Market toggle (International/Vietnamese)
 * - Search input with enter key support
 * - Search results display
 * - Error handling
 * - Vietnamese stock search integration
 * - API Key configuration modal
 */
const SearchStep = ({
  searchQuery,
  setSearchQuery,
  searchResults,
  loading,
  error,
  market,
  setMarket,
  onSearch,
  onSelectCompany,
  marketValidation
}) => {
  const [vietnamSearchLoading, setVietnameseSearchLoading] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);

  const handleKeyPress = async (e) => {
    if (e.key === 'Enter') {
      await performSearch();
    }
  };

  const performSearch = async () => {
    if (market === 'vietnam' && searchQuery.trim()) {
      // Use Vietnamese-specific search - results will be handled by parent's handleSearch
      setVietnameseSearchLoading(true);
      try {
        // Call onSearch which triggers parent's handleSearch to fetch and set results
        await onSearch();
      } catch (err) {
        console.error('Vietnamese search error:', err);
      } finally {
        setVietnameseSearchLoading(false);
      }
    } else {
      // Use international search
      await onSearch();
    }
  };

  const isSearching = loading || vietnamSearchLoading;

  return (
    <div className="w-full max-w-2xl mx-auto bg-white rounded-2xl shadow-md border border-slate-100 p-6 md:p-8 space-y-6">
      
      {/* Step Header */}
      <div className="text-center md:text-left space-y-2">
        <h2 className="text-2xl font-bold text-slate-800 tracking-tight">
          Select Target Company
        </h2>
        <p className="text-sm text-slate-500">
          Enter a company name or ticker symbol to fetch financial metrics and begin peer discovery.
        </p>
      </div>

      {/* Market Selector */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        {/* Segmented Control Market Toggle */}
        <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200/50">
          <button
            type="button"
            onClick={() => setMarket('international')}
            className={`flex-1 sm:flex-initial px-4 py-2 text-sm font-medium rounded-lg transition-all cursor-pointer ${
              market !== 'vietnam'
                ? 'bg-white text-indigo-600 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            International
          </button>
          <button
            type="button"
            onClick={() => setMarket('vietnam')}
            className={`flex-1 sm:flex-initial px-4 py-2 text-sm font-medium rounded-lg transition-all cursor-pointer ${
              market === 'vietnam'
                ? 'bg-white text-indigo-600 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Vietnam (HOSE/HNX)
          </button>
        </div>
      </div>

      {/* API Configuration Button - Centered & Prominent */}
      <div className="flex justify-center">
        <button
          type="button"
          onClick={() => setShowApiKeyModal(true)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition-all cursor-pointer shadow-sm hover:shadow-md"
        >
          <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
          Configure API Keys
        </button>
      </div>

      {/* Main Search Input Form Group */}
      <div className="relative flex items-stretch gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={market === 'vietnam' ? "e.g., FPT, VNM, HPG..." : "e.g., Apple, AAPL, Microsoft..."}
            disabled={isSearching}
            className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
          />
          {searchQuery && !isSearching && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded-md bg-transparent border-0 cursor-pointer text-xs font-semibold"
            >
              Clear
            </button>
          )}
        </div>
        <button
          onClick={performSearch}
          disabled={isSearching || !searchQuery.trim()}
          className="px-5 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-medium text-sm rounded-xl inline-flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50 disabled:bg-indigo-600 disabled:cursor-not-allowed cursor-pointer"
        >
          {isSearching ? (
            <>
              <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Searching...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.608 10.608Z" />
              </svg>
              Search
            </>
          )}
        </button>
      </div>

      {/* Market Input Validation Alert Notice */}
      {marketValidation && marketValidation.message && (
        <div className={`flex items-start gap-3 p-3 rounded-xl border text-xs ${
          marketValidation.isValid 
            ? 'bg-emerald-50 border-emerald-200/60 text-emerald-800' 
            : 'bg-amber-50 border-amber-200/60 text-amber-800'
        }`}>
          <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d={marketValidation.isValid 
              ? "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
              : "M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
            } />
          </svg>
          <div>{marketValidation.message}</div>
        </div>
      )}

      {/* Search Results Display Area */}
      {searchResults && searchResults.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            Matching Results ({searchResults.length})
          </h3>
          <div className="border border-slate-100 rounded-xl overflow-hidden divide-y divide-slate-100 bg-white shadow-sm max-h-72 overflow-y-auto">
            {searchResults.map((result, index) => {
              // Backward compatibility lookups for legacy and current key schemas
              const ticker = result.ticker || result.symbol;
              const companyName = result.company_name || result.name;
              const uniqueKey = `${ticker}-${companyName}-${index}`;

              return (
                <div 
                  key={uniqueKey} 
                  className="flex items-center justify-between p-4 bg-white hover:bg-slate-50 transition-colors group"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-slate-900 truncate">
                        {companyName}
                      </span>
                      <span className="inline-flex px-2 py-0.5 text-xs font-bold bg-slate-100 text-slate-600 rounded-md tracking-wide shrink-0">
                        {ticker}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400 mt-1 flex-wrap">
                      {result.sector && (
                        <span className="truncate">{result.sector}</span>
                      )}
                      {result.sector && result.exchange && (
                        <span className="text-slate-200">•</span>
                      )}
                      {result.exchange && (
                        <span className="uppercase font-medium tracking-wide text-slate-400">
                          {result.exchange}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => onSelectCompany(result)}
                    className="inline-flex items-center justify-center px-4 py-2 border border-slate-200 rounded-lg bg-white hover:bg-indigo-50 active:bg-indigo-100 text-slate-700 hover:text-indigo-600 font-medium text-sm shadow-sm hover:border-indigo-200 transition-all cursor-pointer whitespace-nowrap"
                  >
                    Select
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Fallback Empty Results Slate */}
      {searchResults && searchResults.length === 0 && !isSearching && searchQuery && (
        <div className="text-center p-8 bg-slate-50 border border-dashed border-slate-200 rounded-xl space-y-2">
          <p className="text-sm font-medium text-slate-600">No companies found</p>
          <p className="text-xs text-slate-400">Try adjusting your query, checks, or verify the selected market criteria.</p>
        </div>
      )}

      {/* Global Error Banner Display */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 text-red-800 border border-red-100 rounded-xl text-sm font-medium animate-pulse">
          <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z" />
          </svg>
          <div className="flex-1">{error}</div>
        </div>
      )}

      {/* Embedded API Configuration Portal View Modal overlay */}
      <ApiKeyModal 
        isOpen={showApiKeyModal} 
        onClose={() => setShowApiKeyModal(false)} 
      />
    </div>
  );
};

export default SearchStep;