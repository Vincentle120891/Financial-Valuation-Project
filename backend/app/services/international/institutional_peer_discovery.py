import os
import sqlite3
import logging
import requests

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("MARKET_DATABASE_PATH", "market_universe.db")
FMP_API_KEY = os.getenv("FMP_API_KEY", "meq65Y3F8YP1LRdtqHQHLu6s0RmHSISL")

def extract_market_context(symbol: str) -> tuple[str, str]:
    """
    Normalizes symbols into a clean ticker and country suffix for fallback alignment.
    e.g., '7203.T' -> ('7203', 'JP'), 'VNM.VN' -> ('VNM', 'VN'), 'F' -> ('F', 'US')
    """
    parts = symbol.upper().split('.')
    if len(parts) == 2:
        # Standard corporate syntax for international tracking
        ticker, ext = parts[0], parts[1]
        country = 'JP' if ext in ['T', 'TYO'] else ('VN' if ext in ['VN', 'HNX', 'HOSE'] else ext)
        return ticker, country
    return parts[0], 'US'

def _get_live_fmp_peers(symbol: str) -> list[str]:
    """Primary Option B Strategy: Hits the pre-computed relationships engine"""
    url = f"https://financialmodelingprep.com/stable/stock-peers?symbol={symbol}&apikey={FMP_API_KEY}"
    try:
        response = requests.get(url, timeout=7)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and "peers" in data[0]:
                peers = data[0]["peers"]
                if peers:
                    logger.info(f"Option B Succeeded: Retrieved {len(peers)} pre-computed peers for {symbol}")
                    return peers
        return []
    except Exception as e:
        logger.warning(f"Option B API Request failed for {symbol}: {str(e)}")
        return []

def _get_local_fallback_peers(symbol: str) -> list[str]:
    """Backup Option A Strategy: Scans local cross-market tables if FMP fails"""
    logger.info(f"Triggering Option A Fallback: Querying local market database for {symbol}")
    
    if not os.path.exists(DB_PATH):
        logger.error(f"Fallback Failed: Local database '{DB_PATH}' does not exist.")
        return []

    _, target_country = extract_market_context(symbol)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Fetch Target Metadata from Cache
        cursor.execute(
            "SELECT sector, industry, market_cap FROM market_universe WHERE symbol = ?", 
            (symbol.upper(),)
        )
        target = cursor.fetchone()
        
        if not target:
            logger.warning(f"Option A Aborted: Target {symbol} not found in local cache.")
            conn.close()
            return []
            
        sector, industry, target_cap = target
        
        # 2. Establish Gatekeeper Hard Ranges
        min_cap = target_cap * 0.5
        max_cap = target_cap * 2.0
        
        # 3. Query the localized neighborhood table
        query = """
            SELECT symbol FROM market_universe 
            WHERE sector = ? 
              AND industry = ? 
              AND country = ?
              AND market_cap BETWEEN ? AND ?
              AND symbol != ?
        """
        cursor.execute(query, (sector, industry, target_country, min_cap, max_cap, symbol.upper()))
        fallback_peers = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        logger.info(f"Option A Successful: Located {len(fallback_peers)} matching peers via SQL constraints.")
        return fallback_peers

    except Exception as e:
        logger.error(f"Fallback Execution Failure on Option A: {str(e)}")
        return []

def discover_institutional_peers(target_symbol: str) -> list[dict]:
    """
    Master Service Entry Point:
    Executes Pre-computed Peer Pulling (Option B) with Local SQL Caching (Option A) Failover.
    """
    target_symbol = target_symbol.upper()
    _, target_country = extract_market_context(target_symbol)
    
    # --- STEP 1: Execute Option B Strategy ---
    candidate_symbols = _get_live_fmp_peers(target_symbol)
    
    # --- STEP 2: Automated Hybrid Transition ---
    if not candidate_symbols:
        # Fall back to Option A if Option B hits a paywall, drops out, or lacks VN/JP density
        candidate_symbols = _get_local_fallback_peers(target_symbol)
        
    if not candidate_symbols:
        logger.error(f"Peer discovery pipeline completely exhausted for {target_symbol}. Returning 0 assets.")
        return []

    # --- STEP 3: Normalize Candidates & Prep for Profile Parsing ---
    verified_peer_profiles = []
    
    for symbol in candidate_symbols:
        # Prevent cross-contamination: Make sure peers align with target country boundaries
        _, peer_country = extract_market_context(symbol)
        if peer_country != target_country:
            continue
            
        # Call profile details array (Supported cleanly on Free Tiers)
        profile_url = f"https://financialmodelingprep.com/stable/profile/{symbol}?apikey={FMP_API_KEY}"
        try:
            p_resp = requests.get(profile_url, timeout=5).json()
            if p_resp and isinstance(p_resp, list):
                profile_data = p_resp[0]
                
                # Check for major listing requirements
                if profile_data.get("exchangeShortName") in ["NYSE", "NASDAQ", "HOSE", "HNX", "TSE"]:
                    verified_peer_profiles.append(profile_data)
        except Exception:
            continue

    # Clean data payload flows into Step 3 (Soft Scoring) unchanged
    logger.info(f"Pipeline complete. {len(verified_peer_profiles)} validated profiles passed to Soft Scoring.")
    return verified_peer_profiles
