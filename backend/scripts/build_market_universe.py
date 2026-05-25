import os
import sqlite3
import requests
import logging
from typing import List, Dict, Any

# Configuration
DB_PATH = os.getenv("MARKET_DATABASE_PATH", "market_universe.db")
FMP_API_KEY = os.getenv("FMP_API_KEY", "meq65Y3F8YP1LRdtqHQHLu6s0RmHSISL")

# Target Exchanges to keep (Free Tier friendly)
TARGET_EXCHANGES = ["NYSE", "NASDAQ", "TSE", "HOSE", "HNX"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_stock_list() -> List[Dict[str, Any]]:
    """Fetches the full list of stocks from FMP."""
    url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={FMP_API_KEY}"
    try:
        logger.info("Fetching global stock list from FMP...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Retrieved {len(data)} total symbols from FMP.")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch stock list: {e}")
        return []

def filter_stocks(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters for target exchanges and basic validity."""
    filtered = []
    for stock in raw_data:
        exchange = stock.get("exchangeShortName", "")
        if exchange in TARGET_EXCHANGES:
            # Map exchange to Country Code for our DB schema
            country_map = {
                "NYSE": "US", "NASDAQ": "US",
                "TSE": "JP", "TYO": "JP",
                "HOSE": "VN", "HNX": "VN", "UPCOM": "VN"
            }
            stock['country'] = country_map.get(exchange, "UNKNOWN")
            filtered.append(stock)
    
    logger.info(f"Filtered down to {len(filtered)} stocks in target markets: {TARGET_EXCHANGES}")
    return filtered

def enrich_with_profiles(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetches detailed profile (Sector, Industry, Market Cap) for each stock.
    NOTE: In a real production sync, you would batch this or use the 'profile' endpoint bulk download.
    For initial setup, we iterate. Be mindful of rate limits on free tiers.
    """
    enriched = []
    logger.info("Starting profile enrichment (this may take time)...")
    
    # Simple rate limiting helper could be added here if needed
    
    for i, stock in enumerate(stocks):
        symbol = stock['symbol']
        try:
            # Using the stable profile endpoint
            url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={FMP_API_KEY}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    profile = data[0]
                    stock['sector'] = profile.get('sector', 'Unknown')
                    stock['industry'] = profile.get('industry', 'Unknown')
                    stock['market_cap'] = profile.get('mktCap', 0)
                    stock['price'] = profile.get('price', 0)
                    enriched.append(stock)
                    
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(stocks)} processed...")
                
        except Exception as e:
            logger.warning(f"Could not fetch profile for {symbol}: {e}")
            continue
            
    return enriched

def init_database(db_path: str):
    """Creates the SQLite DB and table schema."""
    if os.path.exists(db_path):
        logger.warning(f"Database already exists at {db_path}. Overwriting...")
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_universe (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            exchange TEXT,
            country TEXT,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            price REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for faster peer discovery queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sector ON market_universe(sector)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_industry ON market_universe(industry)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON market_universe(country)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_cap ON market_universe(market_cap)")
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {db_path}")

def populate_database(db_path: str, data: List[Dict[str, Any]]):
    """Inserts enriched data into SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    insert_query = """
        INSERT OR REPLACE INTO market_universe 
        (symbol, name, exchange, country, sector, industry, market_cap, price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    rows = []
    for item in data:
        rows.append((
            item.get('symbol'),
            item.get('name'),
            item.get('exchangeShortName'),
            item.get('country'),
            item.get('sector'),
            item.get('industry'),
            item.get('market_cap'),
            item.get('price')
        ))
        
    logger.info(f"Inserting {len(rows)} records into database...")
    cursor.executemany(insert_query, rows)
    conn.commit()
    conn.close()
    logger.info("Database population complete.")

def main():
    # 1. Initialize DB
    init_database(DB_PATH)
    
    # 2. Fetch List
    raw_stocks = get_stock_list()
    if not raw_stocks:
        logger.error("Aborting: No stock data retrieved.")
        return

    # 3. Filter
    filtered_stocks = filter_stocks(raw_stocks)
    
    # 4. Enrich (Fetch Profiles)
    # WARNING: This loop hits the API for every stock. 
    # For a one-time setup, this is fine. For daily syncs, use bulk endpoints.
    enriched_stocks = enrich_with_profiles(filtered_stocks)
    
    if not enriched_stocks:
        logger.error("Aborting: No enriched data available.")
        return

    # 5. Populate DB
    populate_database(DB_PATH, enriched_stocks)
    
    logger.info(f"✅ Success! Market Universe ready at {DB_PATH}")
    logger.info(f"   Total records: {len(enriched_stocks)}")

if __name__ == "__main__":
    main()
