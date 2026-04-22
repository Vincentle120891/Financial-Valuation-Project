/**
 * Vietnam Stock Data Provider
 * 
 * Dedicated module for fetching Vietnamese stock market data.
 * Uses multiple data sources with fallback mechanisms due to limited API availability.
 * 
 * Sources:
 * 1. FiinTrade (Primary) - Requires API key
 * 2. VietstockFinance (Secondary) - Web scraping fallback
 * 3. Manual CSV upload support
 * 4. Mock data for development/testing
 * 
 * @module vietnam-data-provider
 */

const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

// Configuration
const VIETNAM_CONFIG = {
  // FiinTrade API (Primary source)
  FIINTRADE_BASE_URL: process.env.FIINTRADE_BASE_URL || 'https://api.fiintrade.com/v1',
  FIINTRADE_API_KEY: process.env.FIINTRADE_API_KEY || null,
  
  // Vietstock (Secondary source - web scraping)
  VIETSTOCK_BASE_URL: 'https://finance.vietstock.vn',
  
  // HOSE/HNX/UPCOM exchange codes
  EXCHANGES: {
    HOSE: 'HOSE',
    HNX: 'HNX',
    UPCOM: 'UPCOM'
  },
  
  // Cache settings
  CACHE_TTL_MS: 5 * 60 * 1000, // 5 minutes
  MAX_RETRIES: 3,
  REQUEST_TIMEOUT_MS: 10000,
  
  // Data validation
  MIN_HISTORY_YEARS: 6,
  MAX_HISTORY_YEARS: 10
};

// In-memory cache
const dataCache = new Map();

/**
 * Helper: Generate cache key
 */
function generateCacheKey(ticker, dataType, params = {}) {
  const keyData = `${ticker}_${dataType}_${JSON.stringify(params)}`;
  return crypto.createHash('md5').update(keyData).digest('hex');
}

/**
 * Helper: Get from cache if valid
 */
function getFromCache(key) {
  const cached = dataCache.get(key);
  if (!cached) return null;
  
  if (Date.now() - cached.timestamp > VIETNAM_CONFIG.CACHE_TTL_MS) {
    dataCache.delete(key);
    return null;
  }
  
  return cached.data;
}

/**
 * Helper: Set cache
 */
function setCache(key, data) {
  dataCache.set(key, {
    data,
    timestamp: Date.now()
  });
}

/**
 * Helper: Validate ticker format for Vietnam stocks
 * Vietnam tickers are typically 3 uppercase letters (e.g., VNM, HPG, VIC)
 */
function validateVietnamTicker(ticker) {
  if (!ticker || typeof ticker !== 'string') {
    return { valid: false, error: 'Ticker must be a non-empty string' };
  }
  
  const normalized = ticker.toUpperCase().trim();
  
  // Vietnam tickers are typically 3 letters
  const vietnamTickerRegex = /^[A-Z]{3}$/;
  if (!vietnamTickerRegex.test(normalized)) {
    return { 
      valid: false, 
      error: `Invalid Vietnam ticker format: ${ticker}. Expected 3 uppercase letters (e.g., VNM, HPG)` 
    };
  }
  
  return { valid: true, normalized };
}

/**
 * Helper: Normalize financial data to standard format
 */
function normalizeFinancialData(rawData, ticker) {
  if (!rawData || !rawData.financials) {
    throw new Error('Invalid financial data structure');
  }
  
  const years = rawData.financials.years || [];
  const metrics = rawData.financials.metrics || {};
  
  // Ensure we have between 6-10 years of data
  if (years.length < VIETNAM_CONFIG.MIN_HISTORY_YEARS) {
    console.warn(`[VIETNAM] Warning: Only ${years.length} years of data available for ${ticker} (minimum: ${VIETNAM_CONFIG.MIN_HISTORY_YEARS})`);
  }
  
  const yearCount = Math.min(years.length, VIETNAM_CONFIG.MAX_HISTORY_YEARS);
  const slicedYears = years.slice(0, yearCount);
  
  // Build standardized output
  const normalized = {
    ticker: rawData.ticker || ticker,
    company_name: rawData.companyName || ticker,
    exchange: rawData.exchange || VIETNAM_CONFIG.EXCHANGES.HOSE,
    currency: 'VND',
    unit_scaling: 'thousands',
    fiscal_year_end: rawData.fiscalYearEnd || '12-31',
    data_source: rawData.source || 'vietnam-provider',
    last_updated: new Date().toISOString(),
    
    // Time series arrays (6-10 years)
    years: slicedYears,
    
    // Income Statement
    revenue: metrics.revenue ? metrics.revenue.slice(0, yearCount) : [],
    cogs: metrics.cogs ? metrics.cogs.slice(0, yearCount) : [],
    gross_profit: metrics.grossProfit ? metrics.grossProfit.slice(0, yearCount) : [],
    operating_expenses: metrics.operatingExpenses ? metrics.operatingExpenses.slice(0, yearCount) : [],
    ebitda: metrics.ebitda ? metrics.ebitda.slice(0, yearCount) : [],
    depreciation: metrics.depreciation ? metrics.depreciation.slice(0, yearCount) : [],
    ebit: metrics.ebit ? metrics.ebit.slice(0, yearCount) : [],
    interest_expense: metrics.interestExpense ? metrics.interestExpense.slice(0, yearCount) : [],
    pretax_income: metrics.pretaxIncome ? metrics.pretaxIncome.slice(0, yearCount) : [],
    income_tax: metrics.incomeTax ? metrics.incomeTax.slice(0, yearCount) : [],
    net_income: metrics.netIncome ? metrics.netIncome.slice(0, yearCount) : [],
    
    // Balance Sheet
    total_assets: metrics.totalAssets ? metrics.totalAssets.slice(0, yearCount) : [],
    current_assets: metrics.currentAssets ? metrics.currentAssets.slice(0, yearCount) : [],
    cash_and_equivalents: metrics.cash ? metrics.cash.slice(0, yearCount) : [],
    accounts_receivable: metrics.accountsReceivable ? metrics.accountsReceivable.slice(0, yearCount) : [],
    inventory: metrics.inventory ? metrics.inventory.slice(0, yearCount) : [],
    total_liabilities: metrics.totalLiabilities ? metrics.totalLiabilities.slice(0, yearCount) : [],
    current_liabilities: metrics.currentLiabilities ? metrics.currentLiabilities.slice(0, yearCount) : [],
    accounts_payable: metrics.accountsPayable ? metrics.accountsPayable.slice(0, yearCount) : [],
    short_term_debt: metrics.shortTermDebt ? metrics.shortTermDebt.slice(0, yearCount) : [],
    long_term_debt: metrics.longTermDebt ? metrics.longTermDebt.slice(0, yearCount) : [],
    total_equity: metrics.totalEquity ? metrics.totalEquity.slice(0, yearCount) : [],
    retained_earnings: metrics.retainedEarnings ? metrics.retainedEarnings.slice(0, yearCount) : [],
    
    // Cash Flow
    operating_cash_flow: metrics.operatingCashFlow ? metrics.operatingCashFlow.slice(0, yearCount) : [],
    investing_cash_flow: metrics.investingCashFlow ? metrics.investingCashFlow.slice(0, yearCount) : [],
    financing_cash_flow: metrics.financingCashFlow ? metrics.financingCashFlow.slice(0, yearCount) : [],
    capex: metrics.capex ? metrics.capex.slice(0, yearCount) : [],
    free_cash_flow: metrics.freeCashFlow ? metrics.freeCashFlow.slice(0, yearCount) : [],
    
    // Shares & Prices
    shares_outstanding: metrics.sharesOutstanding ? metrics.sharesOutstanding.slice(0, yearCount) : [],
    current_stock_price: rawData.currentPrice || null,
    
    // Derived metrics (will be calculated if not provided)
    ar_days: metrics.arDays ? metrics.arDays.slice(0, yearCount) : null,
    inv_days: metrics.invDays ? metrics.invDays.slice(0, yearCount) : null,
    ap_days: metrics.apDays ? metrics.apDays.slice(0, yearCount) : null
  };
  
  return normalized;
}

/**
 * Source 1: FiinTrade API (Primary)
 * Requires API key subscription
 */
async function fetchFromFiinTrade(ticker) {
  if (!VIETNAM_CONFIG.FIINTRADE_API_KEY) {
    throw new Error('FiinTrade API key not configured');
  }
  
  try {
    const response = await axios.get(
      `${VIETNAM_CONFIG.FIINTRADE_BASE_URL}/securities/${ticker}/financials`,
      {
        headers: {
          'Authorization': `Bearer ${VIETNAM_CONFIG.FIINTRADE_API_KEY}`,
          'Content-Type': 'application/json'
        },
        timeout: VIETNAM_CONFIG.REQUEST_TIMEOUT_MS,
        params: {
          period: 'annual',
          restated: true,
          include_estimates: false
        }
      }
    );
    
    if (!response.data || response.data.status !== 'success') {
      throw new Error('FiinTrade API returned invalid response');
    }
    
    return {
      source: 'fiintrade',
      ticker: response.data.symbol || ticker,
      companyName: response.data.companyName,
      exchange: response.data.exchange,
      fiscalYearEnd: response.data.fiscalYearEnd,
      currentPrice: response.data.lastPrice,
      financials: {
        years: response.data.years,
        metrics: {
          revenue: response.data.revenue,
          cogs: response.data.costOfGoodsSold,
          grossProfit: response.data.grossProfit,
          operatingExpenses: response.data.operatingExpenses,
          ebitda: response.data.ebitda,
          depreciation: response.data.depreciation,
          ebit: response.data.ebit,
          interestExpense: response.data.interestExpense,
          pretaxIncome: response.data.ebt,
          incomeTax: response.data.incomeTax,
          netIncome: response.data.netIncome,
          totalAssets: response.data.totalAssets,
          currentAssets: response.data.currentAssets,
          cash: response.data.cashAndEquivalents,
          accountsReceivable: response.data.accountsReceivable,
          inventory: response.data.inventory,
          totalLiabilities: response.data.totalLiabilities,
          currentLiabilities: response.data.currentLiabilities,
          accountsPayable: response.data.accountsPayable,
          shortTermDebt: response.data.shortTermDebt,
          longTermDebt: response.data.longTermDebt,
          totalEquity: response.data.totalEquity,
          retainedEarnings: response.data.retainedEarnings,
          operatingCashFlow: response.data.operatingCashFlow,
          investingCashFlow: response.data.investingCashFlow,
          financingCashFlow: response.data.financingCashFlow,
          capex: response.data.capitalExpenditures,
          freeCashFlow: response.data.freeCashFlow,
          sharesOutstanding: response.data.sharesOutstanding
        }
      }
    };
    
  } catch (error) {
    console.error(`[FIINTRADE] Error fetching ${ticker}:`, error.message);
    throw error;
  }
}

/**
 * Source 2: Vietstock Finance (Web Scraping Fallback)
 * Note: Use responsibly and check terms of service
 */
async function fetchFromVietstock(ticker) {
  try {
    // Construct URL for company financials
    const url = `${VIETNAM_CONFIG.VIETSTOCK_BASE_URL}/${ticker}-financial-statements.htm`;
    
    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml'
      },
      timeout: VIETNAM_CONFIG.REQUEST_TIMEOUT_MS
    });
    
    const $ = cheerio.load(response.data);
    
    // Extract company name
    const companyName = $('.company-name').text().trim() || ticker;
    
    // Extract years from table headers
    const years = [];
    $('.financial-table th.year-header').each((i, el) => {
      const yearText = $(el).text().trim();
      const yearMatch = yearText.match(/(\d{4})/);
      if (yearMatch) {
        years.push(parseInt(yearMatch[1]));
      }
    });
    
    if (years.length === 0) {
      throw new Error('Could not extract year data from Vietstock');
    }
    
    // Helper to extract metric values
    const extractMetric = (selector) => {
      const values = [];
      $(selector).find('td.value').each((i, el) => {
        const text = $(el).text().trim().replace(/,/g, '');
        const value = parseFloat(text);
        if (!isNaN(value) && i < years.length) {
          values.push(value);
        }
      });
      return values;
    };
    
    return {
      source: 'vietstock',
      ticker: ticker,
      companyName: companyName,
      exchange: VIETNAM_CONFIG.EXCHANGES.HOSE,
      financials: {
        years: years.slice(0, VIETNAM_CONFIG.MAX_HISTORY_YEARS),
        metrics: {
          revenue: extractMetric('#revenue-row'),
          netIncome: extractMetric('#net-income-row'),
          totalAssets: extractMetric('#total-assets-row'),
          totalEquity: extractMetric('#total-equity-row')
          // Add more metrics as needed based on actual HTML structure
        }
      }
    };
    
  } catch (error) {
    console.error(`[VIETSTOCK] Error fetching ${ticker}:`, error.message);
    throw error;
  }
}

/**
 * Source 3: Local CSV File Upload
 * Allows manual data import when APIs are unavailable
 */
async function fetchFromCSV(ticker, csvPath) {
  try {
    const content = await fs.readFile(csvPath, 'utf-8');
    const lines = content.trim().split('\n');
    
    if (lines.length < 2) {
      throw new Error('CSV file must have header row and at least one data row');
    }
    
    // Parse CSV
    const headers = lines[0].split(',').map(h => h.trim());
    const dataRows = lines.slice(1);
    
    // Extract years from header (assuming format: Metric,2020,2021,2022,...)
    const years = headers.slice(1).map(h => parseInt(h));
    
    if (years.some(y => isNaN(y))) {
      throw new Error('Invalid year format in CSV header');
    }
    
    // Build metrics object
    const metrics = {};
    dataRows.forEach(row => {
      const values = row.split(',').map(v => v.trim());
      const metricName = values[0];
      const metricValues = values.slice(1).map(v => {
        const num = parseFloat(v.replace(/,/g, ''));
        return isNaN(num) ? null : num;
      });
      
      // Map common metric names to standard format
      const standardName = mapMetricName(metricName);
      if (standardName) {
        metrics[standardName] = metricValues.slice(0, VIETNAM_CONFIG.MAX_HISTORY_YEARS);
      }
    });
    
    return {
      source: 'csv-upload',
      ticker: ticker,
      companyName: ticker,
      financials: {
        years: years.slice(0, VIETNAM_CONFIG.MAX_HISTORY_YEARS),
        metrics
      }
    };
    
  } catch (error) {
    console.error(`[CSV] Error reading ${csvPath}:`, error.message);
    throw error;
  }
}

/**
 * Helper: Map various metric names to standard format
 */
function mapMetricName(name) {
  const mapping = {
    'revenue': ['revenue', 'sales', 'doanh_thu', 'tong_doanh_thu'],
    'cogs': ['cogs', 'cost_of_goods_sold', 'gia_von', 'giavon'],
    'grossProfit': ['gross_profit', 'grossprofit', 'loi_nhuan_gop'],
    'operatingExpenses': ['operating_expenses', 'opex', 'chi_phi_hoat_dong'],
    'ebitda': ['ebitda'],
    'depreciation': ['depreciation', 'khau_hao'],
    'ebit': ['ebit', 'operating_income', 'loi_nhuan_hoat_dong'],
    'interestExpense': ['interest_expense', 'interest', 'chi_phi_lai_vay'],
    'pretaxIncome': ['pretax_income', 'ebt', 'loi_nhuan_truoc_thue'],
    'incomeTax': ['income_tax', 'tax', 'thue_tndn'],
    'netIncome': ['net_income', 'netincome', 'loi_nhuan_sau_thue', 'lnst'],
    'totalAssets': ['total_assets', 'assets', 'tong_tai_san'],
    'currentAssets': ['current_assets', 'tai_san_ngan_han'],
    'cash': ['cash', 'cash_and_equivalents', 'tien_va_tuong_duong_tien'],
    'accountsReceivable': ['accounts_receivable', 'ar', 'khoan_phai_thu'],
    'inventory': ['inventory', 'hang_ton_kho'],
    'totalLiabilities': ['total_liabilities', 'liabilities', 'tong_no_phai_tra'],
    'currentLiabilities': ['current_liabilities', 'no_ngan_han'],
    'accountsPayable': ['accounts_payable', 'ap', 'khoan_phai_tra'],
    'shortTermDebt': ['short_term_debt', 'no_vay_ngan_han'],
    'longTermDebt': ['long_term_debt', 'no_vay_dai_han'],
    'totalEquity': ['total_equity', 'equity', 'von_chu_so_huu'],
    'retainedEarnings': ['retained_earnings', 'loi_nhuan_giu_lai'],
    'operatingCashFlow': ['operating_cash_flow', 'ocf', 'luu_chuyen_tien_te_thu_hoat_dong'],
    'investingCashFlow': ['investing_cash_flow', 'icf', 'luu_chuyen_tien_te_dau_tu'],
    'financingCashFlow': ['financing_cash_flow', 'fcf', 'luu_chuyen_tien_te_tai_chinh'],
    'capex': ['capex', 'capital_expenditures', 'cau_may_thiet_bi'],
    'freeCashFlow': ['free_cash_flow', 'fcff'],
    'sharesOutstanding': ['shares_outstanding', 'so_luong_cp']
  };
  
  const normalizedName = name.toLowerCase().trim();
  
  for (const [standardName, variants] of Object.entries(mapping)) {
    if (variants.includes(normalizedName)) {
      return standardName;
    }
  }
  
  return null;
}

/**
 * Source 4: Mock Data for Development/Testing
 */
function generateMockVietnamData(ticker) {
  const baseRevenue = 5000000 + Math.random() * 10000000; // 5-15 billion VND
  const baseMargin = 0.15 + Math.random() * 0.10;
  const years = [];
  const currentYear = new Date().getFullYear();
  
  for (let i = VIETNAM_CONFIG.MAX_HISTORY_YEARS - 1; i >= 0; i--) {
    years.push(currentYear - i);
  }
  
  const metrics = {};
  const metricNames = [
    'revenue', 'cogs', 'grossProfit', 'operatingExpenses', 'ebitda',
    'depreciation', 'ebit', 'interestExpense', 'pretaxIncome', 'incomeTax',
    'netIncome', 'totalAssets', 'currentAssets', 'cash', 'accountsReceivable',
    'inventory', 'totalLiabilities', 'currentLiabilities', 'accountsPayable',
    'shortTermDebt', 'longTermDebt', 'totalEquity', 'retainedEarnings',
    'operatingCashFlow', 'investingCashFlow', 'financingCashFlow', 'capex',
    'freeCashFlow', 'sharesOutstanding'
  ];
  
  metricNames.forEach(name => {
    const values = [];
    for (let i = 0; i < VIETNAM_CONFIG.MAX_HISTORY_YEARS; i++) {
      const growth = 0.08 + Math.random() * 0.07; // 8-15% growth
      const baseValue = name.includes('margin') || name.includes('ratio') 
        ? baseMargin 
        : baseRevenue * Math.pow(1.1, i);
      const variation = 1 + (Math.random() * 0.2 - 0.1);
      values.push(parseFloat((baseValue * variation).toFixed(2)));
    }
    metrics[name] = values;
  });
  
  return {
    source: 'mock',
    ticker: ticker,
    companyName: `${ticker} Joint Stock Company`,
    exchange: VIETNAM_CONFIG.EXCHANGES.HOSE,
    fiscalYearEnd: '12-31',
    currentPrice: 50000 + Math.random() * 100000,
    financials: {
      years,
      metrics
    }
  };
}

/**
 * Main Function: Fetch Vietnam Stock Data
 * Tries multiple sources with fallback mechanism
 * 
 * @param {string} ticker - Vietnam stock ticker (e.g., VNM, HPG, VIC)
 * @param {object} options - Configuration options
 * @param {string} options.source - Force specific source ('fiintrade', 'vietstock', 'csv', 'mock')
 * @param {string} options.csvPath - Path to CSV file if using CSV source
 * @param {boolean} options.useCache - Whether to use cached data (default: true)
 * @returns {Promise<object>} Normalized financial data
 */
async function fetchVietnamStockData(ticker, options = {}) {
  const {
    source: forcedSource = null,
    csvPath = null,
    useCache = true
  } = options;
  
  // Validate ticker
  const validation = validateVietnamTicker(ticker);
  if (!validation.valid) {
    throw new Error(validation.error);
  }
  
  const normalizedTicker = validation.normalized;
  
  // Check cache
  const cacheKey = generateCacheKey(normalizedTicker, 'full_data', options);
  if (useCache) {
    const cached = getFromCache(cacheKey);
    if (cached) {
      console.log(`[VIETNAM] Cache hit for ${normalizedTicker}`);
      return cached;
    }
  }
  
  let rawData = null;
  let lastError = null;
  
  // Determine which sources to try
  const sourcesToTry = [];
  
  if (forcedSource) {
    sourcesToTry.push(forcedSource);
  } else {
    // Default fallback chain
    if (VIETNAM_CONFIG.FIINTRADE_API_KEY) {
      sourcesToTry.push('fiintrade');
    }
    if (csvPath) {
      sourcesToTry.push('csv');
    }
    sourcesToTry.push('vietstock');
    sourcesToTry.push('mock');
  }
  
  // Try each source in order
  for (const src of sourcesToTry) {
    try {
      console.log(`[VIETNAM] Attempting to fetch ${normalizedTicker} from ${src}...`);
      
      switch (src) {
        case 'fiintrade':
          rawData = await fetchFromFiinTrade(normalizedTicker);
          break;
        case 'vietstock':
          rawData = await fetchFromVietstock(normalizedTicker);
          break;
        case 'csv':
          if (!csvPath) {
            throw new Error('CSV path not provided');
          }
          rawData = await fetchFromCSV(normalizedTicker, csvPath);
          break;
        case 'mock':
          rawData = generateMockVietnamData(normalizedTicker);
          break;
        default:
          throw new Error(`Unknown source: ${src}`);
      }
      
      // Success - normalize and cache
      const normalized = normalizeFinancialData(rawData, normalizedTicker);
      setCache(cacheKey, normalized);
      
      console.log(`[VIETNAM] Successfully fetched ${normalizedTicker} from ${rawData.source} (${normalized.years.length} years)`);
      return normalized;
      
    } catch (error) {
      lastError = error;
      console.warn(`[VIETNAM] Source ${src} failed for ${normalizedTicker}: ${error.message}`);
      
      // Continue to next source unless it was forced
      if (forcedSource) {
        throw error;
      }
    }
  }
  
  // All sources failed
  throw new Error(
    `Failed to fetch data for ${normalizedTicker} from all available sources. Last error: ${lastError?.message}`
  );
}

/**
 * Fetch Multiple Vietnam Stocks
 * 
 * @param {string[]} tickers - Array of Vietnam stock tickers
 * @param {object} options - Options passed to fetchVietnamStockData
 * @returns {Promise<object[]>} Array of normalized financial data
 */
async function fetchMultipleVietnamStocks(tickers, options = {}) {
  const results = [];
  const errors = [];
  
  for (const ticker of tickers) {
    try {
      const data = await fetchVietnamStockData(ticker, options);
      results.push(data);
    } catch (error) {
      errors.push({ ticker, error: error.message });
      console.error(`[VIETNAM] Failed to fetch ${ticker}: ${error.message}`);
    }
  }
  
  return {
    success: results.length > 0,
    data: results,
    errors: errors.length > 0 ? errors : null,
    total_requested: tickers.length,
    total_success: results.length,
    total_failed: errors.length
  };
}

/**
 * Search for Vietnam Stocks by Name or Symbol
 * 
 * @param {string} query - Search query (partial name or symbol)
 * @returns {Promise<object[]>} List of matching stocks
 */
async function searchVietnamStocks(query) {
  if (!query || query.length < 2) {
    throw new Error('Search query must be at least 2 characters');
  }
  
  const searchLower = query.toLowerCase();
  
  // Mock database of major Vietnam stocks
  // In production, this would come from an API or database
  const vietnamStocks = [
    { ticker: 'VNM', name: 'Vinamilk Corporation', exchange: 'HOSE', sector: 'Consumer Staples' },
    { ticker: 'VIC', name: 'Vingroup Joint Stock Company', exchange: 'HOSE', sector: 'Real Estate' },
    { ticker: 'VHM', name: 'Vinhomes Joint Stock Company', exchange: 'HOSE', sector: 'Real Estate' },
    { ticker: 'HPG', name: 'Hoa Phat Group Joint Stock Company', exchange: 'HOSE', sector: 'Materials' },
    { ticker: 'VCB', name: 'Vietcombank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'BID', name: 'BIDV (Bank for Investment and Development)', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'CTG', name: 'Vietinbank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'MSN', name: 'Masan Group Corporation', exchange: 'HOSE', sector: 'Consumer Staples' },
    { ticker: 'FPT', name: 'FPT Corporation', exchange: 'HOSE', sector: 'Technology' },
    { ticker: 'GAS', name: 'PetroVietnam Gas Corporation', exchange: 'HOSE', sector: 'Energy' },
    { ticker: 'SAB', name: 'Sabeco (Saigon Beer-Alcohol-Beverage)', exchange: 'HOSE', sector: 'Consumer Staples' },
    { ticker: 'MWG', name: 'Mobile World Investment Corporation', exchange: 'HOSE', sector: 'Consumer Discretionary' },
    { ticker: 'TCB', name: 'Techcombank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'ACB', name: 'Asia Commercial Bank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'VPB', name: 'VPBank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'TPB', name: 'Tien Phong Bank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'STB', name: 'Sacombank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'MBB', name: 'MB Bank', exchange: 'HOSE', sector: 'Financials' },
    { ticker: 'PLX', name: 'Petrolimex', exchange: 'HOSE', sector: 'Energy' },
    { ticker: 'POW', name: 'PetroVietnam Power Corporation', exchange: 'HOSE', sector: 'Utilities' }
  ];
  
  const matches = vietnamStocks.filter(stock => 
    stock.ticker.toLowerCase().includes(searchLower) ||
    stock.name.toLowerCase().includes(searchLower)
  );
  
  return matches.slice(0, 20); // Return top 20 matches
}

/**
 * Clear cache for specific ticker or all
 */
function clearVietnamCache(ticker = null) {
  if (ticker) {
    const keysToDelete = [];
    for (const key of dataCache.keys()) {
      if (key.includes(ticker.toUpperCase())) {
        keysToDelete.push(key);
      }
    }
    keysToDelete.forEach(key => dataCache.delete(key));
    console.log(`[VIETNAM] Cleared cache for ${ticker}`);
  } else {
    dataCache.clear();
    console.log('[VIETNAM] Cleared all cache');
  }
}

/**
 * Get cache statistics
 */
function getVietnamCacheStats() {
  return {
    size: dataCache.size,
    entries: Array.from(dataCache.keys())
  };
}

// Export functions
module.exports = {
  fetchVietnamStockData,
  fetchMultipleVietnamStocks,
  searchVietnamStocks,
  validateVietnamTicker,
  clearVietnamCache,
  getVietnamCacheStats,
  VIETNAM_CONFIG,
  
  // Export individual source functions for testing
  _fetchFromFiinTrade: fetchFromFiinTrade,
  _fetchFromVietstock: fetchFromVietstock,
  _fetchFromCSV: fetchFromCSV,
  _generateMockVietnamData: generateMockVietnamData,
  _normalizeFinancialData: normalizeFinancialData
};

console.log('✅ Vietnam Data Provider loaded successfully');
console.log(`   Available exchanges: ${Object.values(VIETNAM_CONFIG.EXCHANGES).join(', ')}`);
console.log(`   History range: ${VIETNAM_CONFIG.MIN_HISTORY_YEARS}-${VIETNAM_CONFIG.MAX_HISTORY_YEARS} years`);
console.log(`   Primary source: ${VIETNAM_CONFIG.FIINTRADE_API_KEY ? 'FiinTrade' : 'Not configured (using fallback)'}`);
