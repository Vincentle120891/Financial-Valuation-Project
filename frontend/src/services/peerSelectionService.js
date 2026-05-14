/**
 * PeerSelectionService - Centralized peer discovery and management
 * 
 * Purpose: Handle all peer-related operations including:
 * - Suggesting peers based on valuation method and company
 * - Validating manual peer tickers
 * - Saving peers to session with market data fetching
 * 
 * Architecture Principle: ValuationFlow.jsx should call these service methods
 * instead of directly calling API endpoints for peer operations.
 */

import { suggestPeers, savePeers, validateManualPeers } from './api';

/**
 * Suggest peers based on valuation method and company
 * Different valuation methods may require different peer selection criteria:
 * - DCF: Focus on companies with similar growth profiles and capital structure
 * - COMPS: Focus on recent M&A deals and comparable transactions
 * - DuPont: Focus on companies with similar operational efficiency metrics
 * 
 * @param {Object} params - Peer suggestion parameters
 * @param {string} params.ticker - Target company ticker
 * @param {string} params.market - Market type ('international' or 'vietnam')
 * @param {string} params.method - Valuation method (DCF, COMPS, DuPont)
 * @param {number} params.maxPeers - Maximum number of peers to suggest (default: 10)
 * 
 * @returns {Promise<Object>} Peer suggestion response with peers array
 */
export const findPeers = async ({ ticker, market, method, maxPeers = 10 }) => {
  try {
    // Note: Backend endpoint will be updated to accept method parameter
    // For now, we pass method as additional context (backend may ignore it currently)
    const response = await suggestPeers(ticker, market, maxPeers);
    
    if (response.peers && response.peers.length > 0) {
      // Sort peers by score and return top candidates
      const sortedPeers = [...response.peers].sort((a, b) => b.score - a.score);
      
      return {
        success: true,
        peers: sortedPeers,
        searchCriteria: response.search_criteria,
        warnings: response.warnings || [],
        message: response.message || `Found ${sortedPeers.length} peer candidates for ${ticker}`
      };
    } else {
      return {
        success: false,
        peers: [],
        message: 'No peers found for this company'
      };
    }
  } catch (error) {
    console.error('Peer suggestion failed:', error);
    return {
      success: false,
      peers: [],
      error: error.message
    };
  }
};

/**
 * Auto-select top peers based on score
 * 
 * @param {Array} peers - Array of peer objects with scores
 * @param {number} count - Number of peers to select (default: 5)
 * 
 * @returns {Array} Selected peers array
 */
export const autoSelectPeers = (peers, count = 5) => {
  if (!peers || peers.length === 0) {
    return [];
  }
  
  const sortedPeers = [...peers].sort((a, b) => b.score - a.score);
  return sortedPeers.slice(0, Math.min(count, sortedPeers.length));
};

/**
 * Save selected peers to backend session and fetch peer market data
 * 
 * @param {string} sessionId - Session ID from backend
 * @param {Array} peers - Array of selected peer objects
 * 
 * @returns {Promise<Object>} Save response with saved peer count and peer data
 */
export const saveSelectedPeers = async (sessionId, peers) => {
  try {
    const response = await savePeers(sessionId, peers);
    
    if (response.status === 'success') {
      return {
        success: true,
        peersSaved: response.peers_saved || peers.length,
        peerData: response.peer_data,
        message: response.message || `Successfully saved ${response.peers_saved} peers`
      };
    } else {
      return {
        success: false,
        error: response.message || 'Failed to save peers'
      };
    }
  } catch (error) {
    console.error('Save peers failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Validate manually entered peer tickers
 * 
 * @param {string} sessionId - Session ID from backend
 * @param {Array} tickers - Array of manually entered ticker symbols
 * @param {string} market - Market type ('international' or 'vietnam')
 * 
 * @returns {Promise<Object>} Validation response with valid/invalid tickers
 */
export const validateManualPeerTickers = async (sessionId, tickers, market = 'international') => {
  try {
    const response = await validateManualPeers(sessionId, tickers, market);
    
    return {
      success: true,
      validTickers: response.valid_tickers || [],
      invalidTickers: response.invalid_tickers || [],
      message: response.message || `Validated ${tickers.length} tickers`
    };
  } catch (error) {
    console.error('Manual peer validation failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

// Default export for convenience
export default {
  findPeers,
  autoSelectPeers,
  saveSelectedPeers,
  validateManualPeerTickers
};
