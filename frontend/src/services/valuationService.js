/**
 * ValuationService - Unified Data Retrieval Service
 * 
 * Purpose: Centralize all data retrieval logic for Steps 5 & 6
 * This service handles:
 * - API calls for data retrieval
 * - Market-specific data transformation (International vs Vietnamese)
 * - Unified Schema normalization
 * 
 * Architecture Principle: ValuationFlow.jsx should ONLY call retrieveData()
 * and pass results to step components - no direct API calls or transformation logic.
 */

import {
  fetchApiData,
  retrieveHistoricalData,
  initializeStep8Assumptions,
  prepareAssumptions
} from './api';

/**
 * Transforms Vietnamese market response to Unified Schema format
 * Vietnamese API returns flat structure; we need to wrap it in the expected format
 */
const transformVietnameseResponse = (response, method) => {
  if (!response || !response.success) {
    return null;
  }

  return {
    historical_financials: {
      years: response.periods_fetched || [],
      data_fields: [], // Will be populated from cached session data on next step
      source: response.source_provider,
      currency: response.currency_unit
    },
    metadata: {
      ticker: response.ticker,
      source_provider: response.source_provider,
      fetch_timestamp: response.fetch_timestamp,
      currency_unit: response.currency_unit,
      periods_fetched: response.periods_fetched,
      missing_periods: response.missing_periods,
      data_quality_flags: response.data_quality_flags,
      pdf_sources_used: response.pdf_sources_used
    },
    calculated_metrics: {
      dataRetrieved: true,
      source: response.source_provider,
      periodsCovered: response.periods_fetched
    }
  };
};

/**
 * Transforms International market response to Unified Schema format
 * International API already returns unified format; we normalize it for consistency
 */
const transformInternationalResponse = (response) => {
  if (!response) {
    return null;
  }

  return {
    historical_financials: response.historical_financials,
    forecast_drivers: response.forecast_drivers,
    market_data: response.market_data,
    dupont_metrics: response.dupont_metrics,
    comps_multiples: response.comps_multiples,
    peer_comparables: response.peer_comparables,
    dcf_inputs: response.dcf_inputs,
    dupont_ratios: response.dupont_ratios,
    comps_results: response.comps_results,
    calculated_metrics: {
      dataRetrieved: true,
      source: response.data_source,
      periodsCovered: response.periods_covered,
      cache_used: response.cache_used,
      missing_data_summary: response.missing_data_summary
    },
    metadata: {
      ticker: response.ticker,
      market: response.market,
      method: response.method,
      data_source: response.data_source,
      fetch_timestamp: response.fetch_timestamp,
      status: response.status,
      message: response.message,
      warnings: response.warnings,
      data_quality_flags: response.data_quality_flags
    }
  };
};

/**
 * Main data retrieval function for Step 5/6
 * 
 * @param {Object} params - Retrieval parameters
 * @param {string} params.sessionId - Session ID from backend
 * @param {string} params.method - Valuation method (DCF, DuPont, COMPS)
 * @param {string} params.market - Market type ('international' or 'vietnam')
 * @param {boolean} params.includeHistoricalAI - Whether to include AI-based historical gap filling
 * 
 * @returns {Promise<Object>} Unified Schema data object
 */
export const retrieveData = async ({
  sessionId,
  method,
  market = 'international',
  includeHistoricalAI = false
}) => {
  try {
    // Step 1: Fetch API data (required for both markets)
    const fetchDataResponse = await fetchApiData(sessionId, method, market);
    
    // Step 2: Transform based on market type
    let transformedData;
    if (market && market.toLowerCase() === 'vietnam') {
      transformedData = transformVietnameseResponse(fetchDataResponse, method);
    } else {
      transformedData = transformInternationalResponse(fetchDataResponse);
    }

    // Step 3: Optionally retrieve historical data with AI gap-filling
    if (includeHistoricalAI && transformedData) {
      try {
        const historicalDataResponse = await retrieveHistoricalData(sessionId, method, market);
        
        if (historicalDataResponse.suggestions) {
          // Merge AI-generated suggestions into the transformed data
          transformedData = {
            ...transformedData,
            ...historicalDataResponse.suggestions,
            ai_metadata: {
              gaps_filled: historicalDataResponse.suggestions.total_gaps_filled || 0,
              completeness_score: historicalDataResponse.suggestions.data_completeness_score || 1.0,
              status: historicalDataResponse.status
            }
          };
        }
      } catch (aiError) {
        // AI retrieval is optional - log error but continue with API data
        console.warn('AI historical data retrieval failed:', aiError.message);
        transformedData.ai_metadata = {
          error: aiError.message,
          fallback_used: true
        };
      }
    }

    return {
      success: true,
      data: transformedData,
      market,
      method
    };
  } catch (error) {
    console.error('Data retrieval failed:', error);
    return {
      success: false,
      error: error.message,
      market,
      method
    };
  }
};

/**
 * Initialize Step 8 assumptions with historical trendlines
 * Wrapper around initializeStep8Assumptions API call
 */
export const initializeAssumptions = async (sessionId, method, market = 'international') => {
  try {
    const response = await initializeStep8Assumptions(sessionId, method, market);
    return {
      success: true,
      data: response
    };
  } catch (error) {
    console.error('Failed to initialize assumptions:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Prepare assumptions for Step 5 requirements display
 * Wrapper around prepareAssumptions API call
 */
export const prepareRequirements = async (sessionId, method, market = 'international', generateAi = true) => {
  try {
    const response = await prepareAssumptions(sessionId, method, market, generateAi);
    
    // Transform categories into requiredFields format
    if (response.status && response.categories) {
      const transformedFields = [];
      
      response.categories.forEach(category => {
        if (category.assumptions) {
          Object.entries(category.assumptions).forEach(([key, field]) => {
            transformedFields.push({
              category: category.category_name,
              name: field.description || key,
              fieldName: key,
              requiresInput: category.requires_user_input,
              status: field.status,
              value: field.value,
              isMissing: field.is_missing
            });
          });
        }
      });
      
      return {
        success: true,
        fields: transformedFields,
        categories: response.categories
      };
    }
    
    return {
      success: true,
      fields: [],
      categories: []
    };
  } catch (error) {
    console.error('Failed to prepare requirements:', error);
    return {
      success: false,
      error: error.message,
      fields: [],
      categories: []
    };
  }
};

/**
 * Helper: Deep merge valuations data into matrix structure
 */
export const deepMergeValuations = (prev, market, method, data) => {
  return {
    ...prev,
    [market]: {
      ...prev[market],
      [method?.toLowerCase()]: data
    }
  };
};

/**
 * Helper: Deep merge forecast drivers into matrix structure
 */
export const deepMergeForecastDrivers = (prev, market, method, data) => {
  return {
    ...prev,
    [market]: {
      ...prev[market],
      [method?.toLowerCase()]: data
    }
  };
};

/**
 * Helper: Deep merge DCF inputs into matrix structure
 */
export const deepMergeDcfInputs = (prev, market, method, data) => {
  return {
    ...prev,
    [market]: {
      ...prev[market],
      [method?.toLowerCase()]: data
    }
  };
};

// Default export for convenience
export default {
  retrieveData,
  initializeAssumptions,
  prepareRequirements,
  deepMergeValuations,
  deepMergeForecastDrivers,
  deepMergeDcfInputs
};
