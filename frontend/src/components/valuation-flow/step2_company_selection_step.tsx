import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import VietnameseMarketData from './VietnameseMarketData';
import InternationalMarketData from './InternationalMarketData';

interface CompanySelectionStepProps {
  selectedCompany: any;
  onFindPeers: (company: any) => Promise<void> | void;
  onContinue: () => void;
  onBack: () => void;
  loading: boolean;
  hasPeers?: boolean;
  market?: string;
  marketData?: any;
  showFindPeersButton?: boolean;
  currentStep?: number;
}

/**
 * CompanySelectionStep - Step 2 & Step 4
 * Displays selected company details with sector, industry, and market cap information
 * Provides "Find Peers" button to trigger automatic peer discovery
 * Uses market-specific components for Vietnamese and International markets
 */
const CompanySelectionStep: React.FC<CompanySelectionStepProps> = ({
  selectedCompany,
  onFindPeers,
  onContinue,
  onBack,
  loading,
  hasPeers = false,
  market = 'international',
  marketData = null,
  showFindPeersButton = false,
  currentStep = 2
}) => {
  const { t } = useTranslation();
  const [peerSearchLoading, setPeerSearchLoading] = useState(false);
  const [priceHistory, setPriceHistory] = useState<any>(null);
  const [chartLoading, setChartLoading] = useState(false);

  const handleFindPeers = async () => {
    // Check if onFindPeers is a valid function (not disabled)
    if (!onFindPeers || typeof onFindPeers !== 'function' || onFindPeers.toString().includes('() => {}')) {
      alert('Peer discovery is only available in Step 4 after selecting a valuation model in Step 3.');
      return;
    }
    
    setPeerSearchLoading(true);
    try {
      await onFindPeers(selectedCompany);
    } finally {
      setPeerSearchLoading(false);
    }
  };

  React.useEffect(() => {
    const fetchPriceHistory = async () => {
      const ticker = selectedCompany?.ticker || selectedCompany?.symbol;
      if (!ticker) return;

      setChartLoading(true);
      try {
        const marketCode = market === 'vietnam' ? 'VN' : 'US';
        const response = await fetch(`/api/market-data/${ticker}/price-history?market_code=${marketCode}`);
        if (response.ok) {
          const data = await response.json();
          // Extract the prices array from the response for the chart
          setPriceHistory(data.prices || []);
        } else if (response.status === 404) {
          console.warn(`Ticker ${ticker} not found or delisted`);
        } else if (response.status === 422) {
          console.warn(`Insufficient price data for ${ticker}`);
        }
      } catch (error) {
        // Error handled silently
      } finally {
        setChartLoading(false);
      }
    };

    fetchPriceHistory();
  }, [selectedCompany?.ticker || selectedCompany?.symbol, market]);

  if (!selectedCompany) {
    return (
      <div className="step-container">
        <h2>{t('steps.step2')}</h2>
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
          <p className="text-yellow-700">No company selected. Please go back to Step 1.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="step-container">
      <h2>{currentStep === 2 ? t('steps.step2') : t('steps.step4')}</h2>
      <p style={{ marginBottom: '24px', color: 'var(--text-secondary)' }}>
        {currentStep === 2 
          ? 'Review the selected company details before proceeding to model selection.'
          : 'Peer discovery will be performed automatically based on your selected valuation model.'
        }
      </p>

      {/* Company Details Card */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              {selectedCompany.company_name || selectedCompany.name || selectedCompany.ticker || selectedCompany.symbol}
            </h3>
            <p className="text-gray-500 text-sm">{selectedCompany.ticker || selectedCompany.symbol}</p>
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
              <p className="text-sm text-gray-500 mb-1">{t('marketData.sector')}</p>
              <p className="font-medium text-gray-900">{selectedCompany.sector}</p>
            </div>
          )}

          {selectedCompany.industry && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">{t('marketData.industry')}</p>
              <p className="font-medium text-gray-900">{selectedCompany.industry}</p>
            </div>
          )}

          {selectedCompany.marketCap && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">{t('marketData.market_cap')}</p>
              <p className="font-medium text-gray-900">
                ${(() => {
                  const marketCap = selectedCompany.marketCap;
                  if (marketCap >= 1e12) return `${(marketCap / 1e12).toFixed(2)}T`;
                  if (marketCap >= 1e9) return `${(marketCap / 1e9).toFixed(2)}B`;
                  if (marketCap >= 1e6) return `${(marketCap / 1e6).toFixed(2)}M`;
                  return marketCap.toLocaleString();
                })()}
              </p>
            </div>
          )}

          {selectedCompany.country && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">{t('marketData.region')}</p>
              <p className="font-medium text-gray-900">{selectedCompany.country}</p>
            </div>
          )}

          {selectedCompany.currentPrice !== undefined && (
            <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-500">
              <p className="text-sm text-gray-500 mb-1">{t('marketData.current_price')}</p>
              <p className="font-bold text-blue-900 text-lg">${selectedCompany.currentPrice.toFixed(2)}</p>
            </div>
          )}

          {selectedCompany.beta !== undefined && (
            <div className="bg-purple-50 p-4 rounded-lg border-l-4 border-purple-500">
              <p className="text-sm text-gray-500 mb-1">{t('metrics.beta')}</p>
              <p className="font-bold text-purple-900 text-lg">{selectedCompany.beta.toFixed(2)}</p>
            </div>
          )}

          {selectedCompany.riskFreeRate != null && (
            <div className="bg-green-50 p-4 rounded-lg border-l-4 border-green-500">
              <p className="text-sm text-gray-500 mb-1">{t('metrics.risk_free_rate')}</p>
              <p className="font-bold text-green-900 text-lg">{selectedCompany.riskFreeRate.toFixed(2)}%</p>
            </div>
          )}

          {selectedCompany.marketRiskPremium != null && (
            <div className="bg-orange-50 p-4 rounded-lg border-l-4 border-orange-500">
              <p className="text-sm text-gray-500 mb-1">{t('metrics.equity_risk_premium')}</p>
              <p className="font-bold text-orange-900 text-lg">{selectedCompany.marketRiskPremium.toFixed(2)}%</p>
            </div>
          )}
        </div>

        {selectedCompany.description && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500 mb-2">{t('messages.info')}</p>
            <p className="text-gray-700 text-sm leading-relaxed">
              {selectedCompany.description}
            </p>
          </div>
        )}

        {/* Market-Specific Data Display */}
        {marketData && (
          <div className="mt-6">
            {market === 'vietnam' ? (
              <VietnameseMarketData vietnamData={marketData} />
            ) : (
              <InternationalMarketData internationalData={marketData} />
            )}
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

      {/* Price History Chart */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>📈 Price History (3 Months)</h3>
        {chartLoading ? (
          <div className="flex items-center justify-center h-64">
            <svg className="animate-spin h-8 w-8 text-indigo-600" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
        ) : priceHistory && priceHistory.length > 0 ? (
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={priceHistory}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(date: string) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <YAxis
                  stroke="#6b7280"
                  fontSize={12}
                  tickFormatter={(value: number) => `$${value.toFixed(2)}`}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--canvas-surface)', border: '1px solid var(--border-default)', borderRadius: '8px' }}
                  formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
                  labelFormatter={(label: string) => new Date(label).toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'long', day: 'numeric' })}
                />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="#4f46e5"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorPrice)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
            <p className="text-gray-500">No price history available</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center mt-8 gap-4">
        <button
          onClick={onBack}
          className="btn-secondary"
          disabled={loading}
        >
          ← Back
        </button>

        <div className="flex gap-4">
          {/* Find Peers Button - Only visible when showFindPeersButton is true (Step 4) */}
          {showFindPeersButton && !hasPeers && (
            <button
              onClick={handleFindPeers}
              disabled={peerSearchLoading || loading || !onFindPeers || onFindPeers.toString().includes('() => {}')}
              className="btn-primary"
            >
              {peerSearchLoading ? (
                <>
                  <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Finding Peers...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Find Peers
                </>
              )}
            </button>
          )}

          <button
            onClick={onContinue}
            disabled={loading || (showFindPeersButton && !hasPeers)}
            className="btn-next-step"
          >
            {showFindPeersButton && !hasPeers ? 'Find Peers First →' : 'Continue →'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CompanySelectionStep;
