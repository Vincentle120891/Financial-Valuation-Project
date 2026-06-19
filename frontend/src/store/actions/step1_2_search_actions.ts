/**
 * searchActions - Step 1-2 handlers (Search + Select Company)
 *
 * Plain async functions that import useValuationStore and call getState()/setState().
 */

import useValuationStore from '../useValuationStore';
import { searchCompanies, selectCompany } from '../../services/api';

// ─── Step 1: Handle Search ──────────────────────────────────────────────────

export const handleSearch = async () => {
  const { searchQuery, market } = useValuationStore.getState();

  if (!searchQuery?.trim()) return;

  // Validate market selection before search
  if (!['international', 'vietnam'].includes(market)) {
    useValuationStore.setState({
      marketValidation: {
        isValid: false,
        message: 'Invalid market selection. Please select either International or Vietnam market.',
        selectedMarket: market,
        isLocked: false,
      },
      error: 'Invalid market selection',
    });
    return;
  }

  // Update validation state
  useValuationStore.setState({
    marketValidation: {
      isValid: true,
      message: `Searching in ${market === 'international' ? 'International' : 'Vietnamese'} market`,
      selectedMarket: market,
      isLocked: useValuationStore.getState().marketValidation.isLocked,
    },
    loading: true,
    error: null,
  });

  try {
    const data = await searchCompanies(searchQuery, market);
    console.log('Search response:', data);

    if (data.results && data.results.length > 0) {
      useValuationStore.setState({ searchResults: data.results, error: null });
    } else {
      useValuationStore.setState({
        searchResults: [],
        error: 'No results found. Try an exact ticker symbol.',
      });
    }
  } catch (err) {
    console.error('Search error:', err);
    useValuationStore.setState({
      error: 'Search failed. Please ensure the backend server is running on port 8000.',
      searchResults: [],
    });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};

// ─── Step 1: Handle Select Company (UI only — no API call) ─────────────────

export const handleSelectCompany = (company: any) => {
  const { market } = useValuationStore.getState();

  // Validate market selection before selecting company
  if (!['international', 'vietnam'].includes(market)) {
    useValuationStore.setState({
      marketValidation: {
        isValid: false,
        message: 'Invalid market selection. Please select either International or Vietnam market.',
        selectedMarket: market,
        isLocked: false,
      },
      error: 'Invalid market selection',
    });
    return;
  }

  // Store the selected company in state (session will be created on step-2 navigation)
  useValuationStore.setState({
    selectedCompany: company,
    marketValidation: {
      isValid: true,
      message: `Company ${company.ticker || company.symbol} selected in ${market === 'international' ? 'International' : 'Vietnamese'} market`,
      selectedMarket: market,
      isLocked: true,
    },
    error: null,
  });
};

// ─── Step 2: Create Session (API call — triggered on "Continue to Step 2") ──

let _createSessionInFlight: string | null = null;

export const handleCreateSession = async () => {
  const { selectedCompany, market } = useValuationStore.getState();
  if (!selectedCompany) return;

  const ticker = selectedCompany.ticker || selectedCompany.symbol;

  // Guard against double-calls (React StrictMode, rapid clicks)
  if (_createSessionInFlight === ticker) return;
  _createSessionInFlight = ticker;

  useValuationStore.setState({ loading: true });

  try {
    const data = await selectCompany('', ticker, selectedCompany.market || market);
    console.log('Create session response:', data);

    _createSessionInFlight = null;

    if (data.session_id) {
      const isConfirmed = data.confirmed !== undefined ? data.confirmed : true;
      const responseMarket = data.market || market;
      const dataQualityScore =
        data.data_quality_score !== undefined ? data.data_quality_score : 0;

      // Merge backend company data with selected company
      const enrichedCompany: any = { ...selectedCompany };
      if (data.company_name) {
        enrichedCompany.name = data.company_name;
      }
      enrichedCompany.dataQualityScore = dataQualityScore;

      // Map unified schema market_data array to flat properties
      if (data.market_data && Array.isArray(data.market_data)) {
        data.market_data.forEach((item: any) => {
          if (item.metric === 'current_price' && item.value !== undefined) {
            enrichedCompany.currentPrice = item.value;
          }
          if (item.metric === 'market_cap' && item.value !== undefined) {
            enrichedCompany.marketCap = item.value;
          }
          if (item.metric === 'shares_outstanding' && item.value !== undefined) {
            enrichedCompany.sharesOutstanding = item.value;
          }
          if (item.metric === 'beta' && item.value !== undefined) {
            enrichedCompany.beta = item.value;
          }
          if (item.metric === 'risk_free_rate' && item.value !== undefined) {
            enrichedCompany.riskFreeRate = item.value;
          }
          if (item.metric === 'market_risk_premium' && item.value !== undefined) {
            enrichedCompany.marketRiskPremium = item.value;
          }
        });
      }

      // Also check ticker_info for shares_outstanding
      if (data.ticker_info) {
        if (data.ticker_info.sharesOutstanding !== undefined) {
          enrichedCompany.sharesOutstanding = data.ticker_info.sharesOutstanding;
        }
        if (data.ticker_info.shares_outstanding !== undefined) {
          enrichedCompany.sharesOutstanding = data.ticker_info.shares_outstanding;
        }
      }

      // Also check risk_metrics object for any missing values
      if (data.risk_metrics) {
        if (
          data.risk_metrics.beta?.value !== undefined &&
          enrichedCompany.beta === undefined
        ) {
          enrichedCompany.beta = data.risk_metrics.beta.value;
        }
        if (
          data.risk_metrics.risk_free_rate?.value !== undefined &&
          enrichedCompany.riskFreeRate === undefined
        ) {
          enrichedCompany.riskFreeRate = data.risk_metrics.risk_free_rate.value;
        }
        if (
          data.risk_metrics.market_risk_premium?.value !== undefined &&
          enrichedCompany.marketRiskPremium === undefined
        ) {
          enrichedCompany.marketRiskPremium =
            data.risk_metrics.market_risk_premium.value;
        }
      }

      // Get sector/industry from ticker_info if available
      if (data.ticker_info) {
        if (data.ticker_info.sector !== undefined) {
          enrichedCompany.sector = data.ticker_info.sector;
        }
        if (data.ticker_info.industry !== undefined) {
          enrichedCompany.industry = data.ticker_info.industry;
        }
        if (data.ticker_info.country !== undefined) {
          enrichedCompany.country = data.ticker_info.country;
        }
      }

      useValuationStore.setState({
        sessionId: data.session_id,
        selectedCompany: enrichedCompany,
        marketValidation: {
          isValid: true,
          message: `Company ${ticker} selected in ${responseMarket === 'international' ? 'International' : 'Vietnamese'} market${isConfirmed ? '' : ' (partial data)'}`,
          selectedMarket: responseMarket,
          isLocked: true,
        },
      });
    }
  } catch (err) {
    console.error('Create session error:', err);
    _createSessionInFlight = null;
    useValuationStore.setState({ error: 'Failed to create session. Please try again.' });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};
