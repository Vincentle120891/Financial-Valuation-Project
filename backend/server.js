const express = require('express');
const cors = require('cors');
const yfinance = require('yfinance');
require('dotenv').config();

// AI SDK imports
const { GoogleGenerativeAI } = require('@google/generative-ai');
const Groq = require('groq-sdk');

const app = express();
const PORT = process.env.PORT || 5000;

// API Keys from environment
const ALPHA_VANTAGE_KEY = process.env.ALPHA_VANTAGE_KEY || 'demo';
const YAHOO_FINANCE_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';
const GROQ_API_KEY = process.env.GROQ_API_KEY || '';

// Initialize AI clients
const genAI = GEMINI_API_KEY ? new GoogleGenerativeAI(GEMINI_API_KEY) : null;
const groqClient = GROQ_API_KEY ? new Groq({ apiKey: GROQ_API_KEY }) : null;

// AI Model configuration
const AI_CONFIG = {
  primary: 'gemini',
  fallback: 'groq',
  geminiModel: 'gemini-1.5-flash',
  groqModel: 'llama-3.1-70b-versatile',
  maxRetries: 2,
  timeoutMs: 30000,
  confidenceThreshold: 0.7
};

// In-memory state storage (in production, use a database)
let valuationState = {};

// Mock data for demonstration
const mockTickerSearch = {
  'AAPL': { ticker: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
  'TSLA': { ticker: 'TSLA', name: 'Tesla, Inc.', exchange: 'NASDAQ' },
  'MSFT': { ticker: 'MSFT', name: 'Microsoft Corporation', exchange: 'NASDAQ' },
  'GOOGL': { ticker: 'GOOGL', name: 'Alphabet Inc.', exchange: 'NASDAQ' },
  'AMZN': { ticker: 'AMZN', name: 'Amazon.com, Inc.', exchange: 'NASDAQ' }
};

const valuationModels = [
  { id: 'DCF', name: 'Discounted Cash Flow', description: 'Intrinsic value based on projected free cash flows' },
  { id: 'COMPS', name: 'Trading Comps', description: 'Relative valuation using peer company multiples' },
  { id: 'DUPONT', name: 'DuPont Analysis', description: 'ROE decomposition into profit margin, asset turnover, and leverage' },
  { id: 'REALESTATE', name: 'Real Estate', description: 'Property valuation using NOI and cap rates' }
];

// Middleware
app.use(cors());
app.use(express.json());

// ============================================
// API INTEGRATION FUNCTIONS (Alpha Vantage & Yahoo Finance)
// ============================================

/**
 * Fetch data from Alpha Vantage API
 */
async function fetchFromAlphaVantage(functionName, params = {}) {
  const baseUrl = 'https://www.alphavantage.co/query';
  const url = new URL(baseUrl);
  url.searchParams.append('function', functionName);
  url.searchParams.append('apikey', ALPHA_VANTAGE_KEY);
  
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.append(key, value);
  });
  
  try {
    const response = await fetch(url.toString());
    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Fetch quote data from Yahoo Finance via rapidapi or public endpoint
 * Note: In production, use a proper Yahoo Finance API wrapper or RapidAPI
 */
async function fetchFromYahooFinance(ticker) {
  // Mock implementation - in production use proper API
  const mockYahooData = {
    'AAPL': {
      currentPrice: 189.84,
      previousClose: 188.27,
      open: 189.00,
      dayHigh: 191.05,
      dayLow: 188.82,
      volume: 52436100,
      marketCap: 2950000000000,
      beta: 1.29,
      peRatio: 29.85,
      eps: 6.36,
      dividendYield: 0.0051,
      exDividendDate: '2024-02-09',
      fiftyTwoWeekHigh: 199.62,
      fiftyTwoWeekLow: 164.08
    },
    'TSLA': {
      currentPrice: 248.50,
      previousClose: 245.30,
      open: 246.00,
      dayHigh: 251.20,
      dayLow: 244.80,
      volume: 98234500,
      marketCap: 789000000000,
      beta: 2.31,
      peRatio: 78.45,
      eps: 3.17,
      dividendYield: 0,
      exDividendDate: null,
      fiftyTwoWeekHigh: 299.29,
      fiftyTwoWeekLow: 138.80
    },
    'MSFT': {
      currentPrice: 415.20,
      previousClose: 413.65,
      open: 414.00,
      dayHigh: 417.85,
      dayLow: 412.90,
      volume: 18567200,
      marketCap: 3090000000000,
      beta: 0.89,
      peRatio: 36.72,
      eps: 11.31,
      dividendYield: 0.0072,
      exDividendDate: '2024-02-14',
      fiftyTwoWeekHigh: 430.82,
      fiftyTwoWeekLow: 309.45
    },
    'GOOGL': {
      currentPrice: 172.35,
      previousClose: 171.20,
      open: 171.50,
      dayHigh: 173.45,
      dayLow: 170.85,
      volume: 21456300,
      marketCap: 2150000000000,
      beta: 1.05,
      peRatio: 26.18,
      eps: 6.58,
      dividendYield: 0,
      exDividendDate: null,
      fiftyTwoWeekHigh: 191.75,
      fiftyTwoWeekLow: 121.46
    },
    'AMZN': {
      currentPrice: 178.25,
      previousClose: 176.90,
      open: 177.20,
      dayHigh: 179.80,
      dayLow: 176.45,
      volume: 34567800,
      marketCap: 1850000000000,
      beta: 1.15,
      peRatio: 62.45,
      eps: 2.85,
      dividendYield: 0,
      exDividendDate: null,
      fiftyTwoWeekHigh: 201.20,
      fiftyTwoWeekLow: 118.35
    }
  };
  
  const data = mockYahooData[ticker] || mockYahooData['AAPL'];
  return { success: true, data, source: 'yfinance' };
}

/**
 * Get comprehensive financial data for a ticker (Step 5 - Required Inputs)
 * Combines data from both Alpha Vantage and Yahoo Finance
 */
async function getComprehensiveFinancialData(ticker) {
  const timestamp = new Date().toISOString();
  
  // Fetch from multiple sources in parallel
  const [yahooResult, incomeStatement, balanceSheet, cashFlow, overview] = await Promise.all([
    fetchFromYahooFinance(ticker),
    fetchFromAlphaVantage('INCOME_STATEMENT', { symbol: ticker }),
    fetchFromAlphaVantage('BALANCE_SHEET', { symbol: ticker }),
    fetchFromAlphaVantage('CASH_FLOW', { symbol: ticker }),
    fetchFromAlphaVantage('OVERVIEW', { symbol: ticker })
  ]);
  
  // Build unified data structure per schema
  const financialData = {
    metadata: {
      ticker: ticker,
      company_name: overview.data?.Name || `${ticker} Inc.`,
      exchange: overview.data?.Exchange || 'NASDAQ',
      currency: overview.data?.Currency || 'USD',
      fiscal_year_end_month: parseInt(overview.data?.FiscalYearEndMonth) || 12,
      data_timestamp: timestamp,
      data_source: 'multiple',
      model_usage: ['dcf', 'comps', 'dupont']
    },
    
    market_structure: {
      current_price: yahooResult.data?.currentPrice || 0,
      shares_outstanding_diluted: (yahooResult.data?.marketCap / yahooResult.data?.currentPrice) || 0,
      shares_outstanding_basic: (yahooResult.data?.marketCap / yahooResult.data?.currentPrice) * 0.98 || 0,
      market_capitalization: yahooResult.data?.marketCap || 0,
      enterprise_value: 0, // Calculated below
      total_debt: 0, // From balance sheet
      short_term_debt: 0,
      long_term_debt: 0,
      cash_and_equivalents: 0,
      net_debt: 0,
      beta_5y_monthly: yahooResult.data?.beta || 1.0,
      dividend_yield: yahooResult.data?.dividendYield || 0,
      dividend_per_share: yahooResult.data?.dividendYield * yahooResult.data?.currentPrice || 0
    },
    
    macro_indicators: {
      risk_free_rate_10y: 0.045, // From FRED DGS10
      equity_risk_premium: 0.055, // Damodaran US ERP
      inflation_expectations_10y: 0.023, // From FRED T10YIE
      gdp_growth_forecast: 0.021, // OECD forecast
      fx_rate_to_usd: 1.0,
      sector_credit_spread: 0.012,
      industry_capacity_utilization: 0.78
    },
    
    income_statement_raw: {
      revenue_total: parseFloat(overview.data?.RevenueTTM) || 394328000000,
      cost_of_revenue_cogs: parseFloat(overview.data?.GrossProfitTTM) ? 
        parseFloat(overview.data?.RevenueTTM) - parseFloat(overview.data?.GrossProfitTTM) : 220000000000,
      gross_profit: parseFloat(overview.data?.GrossProfitTTM) || 174328000000,
      sga_expense: 55000000000,
      research_and_development: 30000000000,
      other_operating_expenses: 5000000000,
      ebitda: parseFloat(overview.data?.EBITDATTM) || 125000000000,
      depreciation_and_amortization: 11519000000,
      ebit_operating_income: parseFloat(overview.data?.OperatingMarginTTM) * parseFloat(overview.data?.RevenueTTM) || 117000000000,
      interest_expense: 3500000000,
      interest_income: 3000000000,
      net_interest: 500000000,
      pre_tax_income_ebt: 116500000000,
      tax_provision: 16900000000,
      net_income: parseFloat(overview.data?.NetIncomeTTM) || 99600000000,
      eps_diluted: yahooResult.data?.eps || 6.36,
      eps_basic: (yahooResult.data?.eps || 6.36) * 1.02,
      weighted_avg_shares_diluted: (yahooResult.data?.marketCap / yahooResult.data?.eps) || 15552752000
    },
    
    balance_sheet_raw: {
      accounts_receivable: 29500000000,
      inventory: 6500000000,
      accounts_payable: 62000000000,
      net_ppe: 43700000000,
      gross_ppe: 114000000000,
      accumulated_depreciation: 70300000000,
      goodwill: 0,
      intangible_assets: 0,
      total_assets: 352755000000,
      total_current_assets: 143566000000,
      total_non_current_assets: 209189000000,
      total_liabilities: 290437000000,
      total_current_liabilities: 145308000000,
      total_equity: 62318000000,
      retained_earnings: 1408000000,
      common_stock: 73812000000,
      deferred_tax_assets: 0,
      deferred_tax_liabilities: 0,
      minority_interest_nci: 0
    },
    
    cash_flow_raw: {
      operating_cash_flow_cfo: 110543000000,
      capital_expenditures_capex: -10959000000,
      free_cash_flow: 99584000000,
      change_in_working_capital: -1688000000,
      dividends_paid: -15000000000,
      share_repurchases: -77550000000,
      debt_issuance: 5000000000,
      debt_repayment: -9500000000,
      other_financing_activities: -2000000000
    },
    
    calculated_metrics_common: {}, // Calculated below
    
    wacc_components: {}, // Calculated below
    
    comps_specific_calculated: {}, // Calculated below
    
    dupont_specific_components: {} // Calculated below
  };
  
  // Calculate derived market structure fields
  financialData.market_structure.total_debt = 
    financialData.balance_sheet_raw.total_liabilities - financialData.balance_sheet_raw.total_equity;
  financialData.market_structure.short_term_debt = financialData.market_structure.total_debt * 0.15;
  financialData.market_structure.long_term_debt = financialData.market_structure.total_debt * 0.85;
  financialData.market_structure.cash_and_equivalents = financialData.balance_sheet_raw.total_current_assets * 0.2;
  financialData.market_structure.net_debt = 
    financialData.market_structure.total_debt - financialData.market_structure.cash_and_equivalents;
  financialData.market_structure.enterprise_value = 
    financialData.market_structure.market_capitalization + financialData.market_structure.net_debt;
  
  // Calculate common metrics
  const ism = financialData.income_statement_raw;
  const bsr = financialData.balance_sheet_raw;
  const cfr = financialData.cash_flow_raw;
  const ms = financialData.market_structure;
  
  financialData.calculated_metrics_common = {
    gross_margin: ism.gross_profit / ism.revenue_total,
    ebitda_margin: ism.ebitda / ism.revenue_total,
    operating_margin: ism.ebit_operating_income / ism.revenue_total,
    net_profit_margin: ism.net_income / ism.revenue_total,
    effective_tax_rate: Math.abs(ism.tax_provision) / Math.abs(ism.pre_tax_income_ebt),
    ar_days: (bsr.accounts_receivable / ism.revenue_total) * 365,
    inventory_days: (bsr.inventory / ism.cost_of_revenue_cogs) * 365,
    ap_days: (bsr.accounts_payable / ism.cost_of_revenue_cogs) * 365,
    cash_conversion_cycle: 0, // Calculated below
    asset_turnover: ism.revenue_total / bsr.total_assets,
    roic: (ism.ebit_operating_income * (1 - financialData.calculated_metrics_common.effective_tax_rate)) / 
          (bsr.total_equity + ms.net_debt),
    roe: ism.net_income / bsr.total_equity,
    roa: ism.net_income / bsr.total_assets,
    debt_to_equity: ms.total_debt / bsr.total_equity,
    interest_coverage: ism.ebitda / ism.interest_expense,
    revenue_growth_yoy: 0.02, // Would come from historical comparison
    revenue_growth_3y_cagr: 0.078,
    net_debt_to_ebitda: ms.net_debt / ism.ebitda,
    fcf_margin: cfr.free_cash_flow / ism.revenue_total,
    payout_ratio: Math.abs(cfr.dividends_paid) / ism.net_income
  };
  
  financialData.calculated_metrics_common.cash_conversion_cycle = 
    financialData.calculated_metrics_common.ar_days + 
    financialData.calculated_metrics_common.inventory_days - 
    financialData.calculated_metrics_common.ap_days;
  
  // Calculate WACC components
  const rf = financialData.macro_indicators.risk_free_rate_10y;
  const erp = financialData.macro_indicators.equity_risk_premium;
  const beta = ms.beta_5y_monthly;
  const taxRate = financialData.calculated_metrics_common.effective_tax_rate;
  const E = ms.market_capitalization;
  const D = ms.net_debt;
  const V = E + D;
  const Rd = ism.interest_expense / ms.total_debt;
  
  financialData.wacc_components = {
    cost_of_debt_pre_tax: Rd,
    cost_of_debt_after_tax: Rd * (1 - taxRate),
    cost_of_equity_re: rf + beta * erp,
    equity_weight_e_v: E / V,
    debt_weight_d_v: D / V,
    wacc_calc_base: (E / V) * (rf + beta * erp) + (D / V) * Rd * (1 - taxRate)
  };
  
  // Calculate Comps-specific metrics
  financialData.comps_specific_calculated = {
    target_ev_ebitda: ms.enterprise_value / ism.ebitda,
    target_ev_sales: ms.enterprise_value / ism.revenue_total,
    target_ev_ebit: ms.enterprise_value / ism.ebit_operating_income,
    target_pe_diluted: ms.market_capitalization / ism.net_income,
    target_pb: ms.market_capitalization / bsr.total_equity,
    target_p_fcf: ms.market_capitalization / cfr.free_cash_flow,
    target_ev_fcf: ms.enterprise_value / cfr.free_cash_flow,
    peer_ev_ebitda_array: [12.5, 14.2, 11.8, 15.6, 13.1],
    peer_ev_sales_array: [4.2, 5.1, 3.8, 5.5, 4.6],
    peer_pe_array: [25.4, 28.9, 22.1, 31.2, 26.8],
    peer_pb_array: [8.5, 10.2, 7.1, 12.3, 9.4],
    peer_ev_ebitda_median: 13.1,
    peer_ev_ebitda_mean: 13.44,
    peer_ev_ebitda_25th_pct: 11.8,
    peer_ev_ebitda_75th_pct: 15.6,
    peer_ev_ebitda_std_dev: 1.52,
    peer_count_total: 5,
    peer_count_after_filtering: 5,
    weighted_avg_ev_ebitda: 13.8,
    trimmed_mean_ev_ebitda: 13.37
  };
  
  // Calculate DuPont components
  financialData.dupont_specific_components = {
    tax_burden: ism.net_income / ism.pre_tax_income_ebt,
    interest_burden: ism.pre_tax_income_ebt / ism.ebit_operating_income,
    roe_3step: financialData.calculated_metrics_common.net_profit_margin * 
               financialData.calculated_metrics_common.asset_turnover * 
               (bsr.total_assets / bsr.total_equity),
    roe_5step: (ism.net_income / ism.pre_tax_income_ebt) * 
               (ism.pre_tax_income_ebt / ism.ebit_operating_income) * 
               (ism.ebit_operating_income / ism.revenue_total) * 
               (ism.revenue_total / bsr.total_assets) * 
               (bsr.total_assets / bsr.total_equity),
    tangible_equity_multiplier: bsr.total_assets / (bsr.total_equity - bsr.goodwill - bsr.intangible_assets),
    current_ratio: bsr.total_current_assets / bsr.total_current_liabilities,
    quick_ratio: (bsr.total_current_assets - bsr.inventory) / bsr.total_current_liabilities
  };
  
  return financialData;
}

// ============================================
// AI INTEGRATION FUNCTIONS (Gemini + Groq Fallback)
// ============================================

/**
 * Fetch 3 years of historical financial data for DCF
 * Dynamically resolves FY-3, FY-2, FY-1 based on latest fiscal year end
 * Uses Alpha Vantage API as primary source
 */
async function fetchHistoricalFinancials3Y(ticker) {
  try {
    console.log(`Fetching historical data for ${ticker}`);
    
    // Get current quote for metadata
    const quoteResult = await fetchFromYahooFinance(ticker);
    const quote = quoteResult.data;
    
    // Determine fiscal year end (default December)
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth() + 1;
    const fiscalYearEndMonth = 12; // Default
    
    // Calculate last 3 completed fiscal years
    let lastCompletedYear = currentYear;
    if (currentMonth < fiscalYearEndMonth) {
      lastCompletedYear = currentYear - 1;
    }
    
    const fyMinus1 = lastCompletedYear;
    const fyMinus2 = lastCompletedYear - 1;
    const fyMinus3 = lastCompletedYear - 2;
    
    console.log(`Historical years: FY-${fyMinus3}, FY-${fyMinus2}, FY-${fyMinus1}`);
    
    // Fetch annual income statement from Alpha Vantage
    const incomeStatementResult = await fetchFromAlphaVantage('INCOME_STATEMENT', { symbol: ticker });
    const annualReports = incomeStatementResult.data?.annualReports || [];
    
    // Helper to find data by fiscal year
    const getAnnualData = (fiscalYear) => {
      return annualReports.find(r => r.fiscalDateEnding?.startsWith(fiscalYear.toString()));
    };
    
    const fy1Data = getAnnualData(fyMinus1);
    const fy2Data = getAnnualData(fyMinus2);
    const fy3Data = getAnnualData(fyMinus3);
    
    // Build historical financials for 3 years
    const historicalFinancials = {
      fy_minus_3: buildAnnualFinancials(fy3Data),
      fy_minus_2: buildAnnualFinancials(fy2Data),
      fy_minus_1: buildAnnualFinancials(fy1Data)
    };
    
    // Get base period balances (FY-1)
    const balanceSheetResult = await fetchFromAlphaVantage('BALANCE_SHEET', { symbol: ticker });
    const balanceReports = balanceSheetResult.data?.annualReports || [];
    const fy1Balance = balanceReports.find(r => r.fiscalDateEnding?.startsWith(fyMinus1.toString()));
    
    const cashFlowResult = await fetchFromAlphaVantage('CASH_FLOW', { symbol: ticker });
    const cashFlowReports = cashFlowResult.data?.annualReports || [];
    const fy1CashFlow = cashFlowReports.find(r => r.fiscalDateEnding?.startsWith(fyMinus1.toString()));
    
    const basePeriodBalances = {
      net_debt: calculateNetDebt(
        parseFloat(fy1Balance?.totalDebt || 0),
        parseFloat(fy1Balance?.cashAndShortTermInvestments || 0)
      ),
      ppe_net: parseFloat(fy1Balance?.propertyPlantEquipment || 0),
      tax_basis_pp_e: null, // Requires AI extraction from footnotes
      tax_losses_nol_carryforward: null, // Requires AI extraction from footnotes
      shares_outstanding_diluted: parseFloat(fy1Balance?.commonStockSharesOutstanding || 0),
      current_stock_price: quote.currentPrice || null,
      projected_interest_expense_annual: parseFloat(fy1Data?.interestExpense || 0),
      plant_capacity_units_per_day: null // Requires AI extraction from MD&A
    };
    
    return {
      _metadata: {
        valuation_date: new Date().toISOString().split('T')[0],
        currency: quote.currency || 'USD',
        fiscal_year_end_month: fiscalYearEndMonth,
        historical_years: [fyMinus3, fyMinus2, fyMinus1],
        data_source: 'alpha_vantage'
      },
      historical_financials_3y: historicalFinancials,
      base_period_balances_fy_minus_1: basePeriodBalances
    };
  } catch (error) {
    console.error(`Error fetching historical financials for ${ticker}:`, error.message);
    // Return mock data as fallback
    return getMockHistoricalFinancials(ticker);
  }
}

/**
 * Build annual financials object from Alpha Vantage data
 */
function buildAnnualFinancials(data) {
  if (!data) {
    return {
      revenue: null, cogs: null, gross_profit: null, sga: null, other_opex: null,
      ebitda: null, depreciation: null, ebit: null, interest_expense: null,
      ebt: null, current_tax: null, deferred_tax: null, total_tax: null,
      net_income: null, accounts_receivable: null, inventory: null,
      accounts_payable: null, net_working_capital: null, capital_expenditure: null
    };
  }
  
  return {
    revenue: parseFloat(data.totalRevenue || 0) || null,
    cogs: parseFloat(data.costOfRevenue || 0) || null,
    gross_profit: parseFloat(data.grossProfit || 0) || null,
    sga: parseFloat(data.sellingGeneralAndAdministrative || 0) || null,
    other_opex: parseFloat(data.operatingExpenses || 0) || null,
    ebitda: parseFloat(data.ebitda || 0) || null,
    depreciation: parseFloat(data.depreciationAndAmortization || 0) || null,
    ebit: parseFloat(data.operatingIncome || 0) || null,
    interest_expense: parseFloat(data.interestExpense || 0) || null,
    ebt: parseFloat(data.incomeBeforeTax || 0) || null,
    current_tax: parseFloat(data.currentDeferredIncomeTax || 0) || null,
    deferred_tax: parseFloat(data.deferredIncomeTax || 0) || null,
    total_tax: parseFloat(data.incomeTaxExpense || 0) || null,
    net_income: parseFloat(data.netIncome || 0) || null,
    accounts_receivable: null, // From balance sheet
    inventory: null, // From balance sheet
    accounts_payable: null, // From balance sheet
    net_working_capital: null, // Calculated from balance sheet
    capital_expenditure: Math.abs(parseFloat(data.capitalExpenditures || 0)) || null
  };
}

/**
 * Calculate Net Working Capital
 */
function calculateNWC(currentAssets, currentLiabilities) {
  if (currentAssets === null || currentLiabilities === null) return null;
  return currentAssets - currentLiabilities;
}

/**
 * Calculate Net Debt
 */
function calculateNetDebt(totalDebt, cash) {
  if (totalDebt === null || cash === null) return null;
  return totalDebt - cash;
}

/**
 * Call Gemini API with timeout and error handling
 */
async function callGeminiAI(prompt, systemInstruction = '') {
  if (!genAI) {
    throw new Error('Gemini API key not configured');
  }
  
  const model = genAI.getGenerativeModel({ 
    model: AI_CONFIG.geminiModel,
    systemInstruction: systemInstruction || 'You are a financial analysis expert. Provide structured, accurate data extracted from financial documents.'
  });
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AI_CONFIG.timeoutMs);
  
  try {
    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.3,
        topK: 40,
        topP: 0.95,
        maxOutputTokens: 4096,
      },
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    const response = await result.response;
    return { success: true, data: response.text(), source: 'gemini' };
  } catch (error) {
    clearTimeout(timeoutId);
    throw new Error(`Gemini API error: ${error.message}`);
  }
}

/**
 * Call Groq API (Llama 3) with timeout and error handling
 */
async function callGroqAI(prompt, systemInstruction = '') {
  if (!groqClient) {
    throw new Error('Groq API key not configured');
  }
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AI_CONFIG.timeoutMs);
  
  try {
    const completion = await groqClient.chat.completions.create({
      messages: [
        { role: 'system', content: systemInstruction || 'You are a financial analysis expert. Provide structured, accurate data extracted from financial documents.' },
        { role: 'user', content: prompt }
      ],
      model: AI_CONFIG.groqModel,
      temperature: 0.3,
      max_tokens: 4096,
      top_p: 0.95,
    }, { signal: controller.signal });
    
    clearTimeout(timeoutId);
    return { success: true, data: completion.choices[0]?.message?.content || '', source: 'groq' };
  } catch (error) {
    clearTimeout(timeoutId);
    throw new Error(`Groq API error: ${error.message}`);
  }
}

/**
 * Smart AI call with automatic fallback from Gemini to Groq
 */
async function callAIWithFallback(prompt, systemInstruction = '', operationName = 'AI Operation') {
  let lastError = null;
  
  // Try primary (Gemini)
  if (genAI) {
    try {
      console.log(`[${operationName}] Trying Gemini API...`);
      const result = await callGeminiAI(prompt, systemInstruction);
      console.log(`[${operationName}] Gemini succeeded`);
      return result;
    } catch (error) {
      console.log(`[${operationName}] Gemini failed: ${error.message}`);
      lastError = error;
    }
  }
  
  // Try fallback (Groq)
  if (groqClient) {
    try {
      console.log(`[${operationName}] Trying Groq API (fallback)...`);
      const result = await callGroqAI(prompt, systemInstruction);
      console.log(`[${operationName}] Groq succeeded`);
      return result;
    } catch (error) {
      console.log(`[${operationName}] Groq failed: ${error.message}`);
      lastError = error;
    }
  }
  
  // Both failed - return mock data
  console.log(`[${operationName}] Both AI APIs failed, using mock data`);
  return { 
    success: true, 
    data: getMockAIData(operationName), 
    source: 'mock_fallback',
    warning: 'Using mock data - AI APIs unavailable'
  };
}

/**
 * Get mock AI data when both APIs fail
 */
function getMockAIData(operationName) {
  const mockData = {
    'footnote_extraction': {
      ai_footnote_extractions: {
        tax_basis_pp_e: 45000000000,
        nol_carryforward_amount: 0,
        nol_expiration_dates: [],
        useful_life_existing_assets: [
          { asset_class: 'Buildings', years: 30 },
          { asset_class: 'Machinery', years: 10 },
          { asset_class: 'Computer Equipment', years: 3 }
        ],
        useful_life_new_assets: [5, 7, 10],
        lease_liability_operating: 12000000000,
        lease_liability_finance: 1500000000,
        rent_expense_ltm: 2500000000,
        deferred_tax_assets: 8000000000,
        deferred_tax_liabilities: 5000000000,
        goodwill_and_intangibles: 0,
        pension_opeb_obligations: 3000000000,
        contingent_liabilities_litigation: 500000000,
        related_party_transaction_amount: 0,
        capital_commitments: {
          year_1: 15000000000,
          years_1_3: 25000000000,
          years_3_5: 10000000000,
          beyond_5: 5000000000
        },
        accounting_policy_differences: 'No significant deviations from standard GAAP treatment detected.',
        tax_jurisdiction_statutory_rates: [
          { jurisdiction: 'United States', rate: 0.21 },
          { jurisdiction: 'Ireland', rate: 0.125 },
          { jurisdiction: 'Singapore', rate: 0.17 }
        ],
        segment_revenue_breakdown: [
          { segment: 'Products', revenue: 298000000000, pct: 0.76 },
          { segment: 'Services', revenue: 96000000000, pct: 0.24 }
        ],
        segment_ebitda_breakdown: [
          { segment: 'Products', ebitda: 95000000000, pct: 0.76 },
          { segment: 'Services', ebitda: 30000000000, pct: 0.24 }
        ],
        m_and_a_pro_forma_adjustments: {
          pro_forma_revenue: null,
          pro_forma_ebitda: null
        }
      },
      confidence_score_overall: 0.85
    },
    'forward_guidance': {
      ai_contextual_forward_guidance: {
        plant_utilization_target: 0.85,
        projected_interest_rate_on_debt: 0.035,
        projected_depreciation_rate: 0.029,
        tax_loss_utilization_schedule: {
          year_1_pct: 0,
          year_2_pct: 0,
          year_3_pct: 0
        },
        working_capital_policy_change_days: -2,
        capex_as_pct_of_revenue_forecast: 0.035,
        revenue_growth_forecast_5y: [0.05, 0.06, 0.055, 0.05, 0.045],
        management_guidance_notes: 'Management expects continued growth in services segment with moderate products growth. Focus on margin expansion through operational efficiency.'
      },
      confidence_score_overall: 0.82
    },
    'hybrid_adjustments': {
      ai_api_hybrid_adjustments: {
        adjusted_ebitda: 127500000000,
        adjusted_net_income: 101000000000,
        lease_adjusted_enterprise_value: 2975000000000,
        ev_ebitda_ex_rent: 23.8,
        tangible_equity_multiplier: 5.66,
        lease_adjusted_asset_turnover: 1.12,
        normalized_tax_burden: 0.855,
        blended_tax_depreciation_rate: 0.032,
        net_debt_post_operating_leases: 115000000000,
        fye_aligned_ltm_metrics: {
          revenue: 394328000000,
          ebitda: 125000000000,
          net_income: 99600000000
        }
      },
      confidence_score_overall: 0.88
    },
    'peer_matching': {
      ai_peer_matching_analysis: {
        ai_suggested_peer_tickers: ['MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'],
        business_model_similarity_score: 0.78,
        geographic_exposure_match: {
          primary_regions: ['North America', 'Europe', 'Asia Pacific'],
          match_pct: 0.85
        },
        size_band_ratio: 1.15,
        growth_differential: 0.02,
        conglomerate_diversification_flag: false,
        exclusion_reasons_ai: [],
        peer_quality_score_composite: 87
      },
      confidence_score_overall: 0.91
    },
    'valuation_suggestions': {
      ai_hybrid_valuation_suggestions: {
        growth_adjusted_terminal_multiple_suggestion: 14.5,
        implied_credit_spread_from_guidance: 0.0095,
        forward_ebitda_margin_ai_adjusted: 0.325,
        scenario_weight_suggestions: {
          best_case_weight: 0.25,
          base_case_weight: 0.55,
          worst_case_weight: 0.20
        },
        quality_discount_premium_suggestion: 0.05
      },
      confidence_score_overall: 0.79
    }
  };
  
  return mockData[operationName] || mockData['footnote_extraction'];
}

/**
 * Parse JSON from AI response with error handling
 */
function parseAIJsonResponse(aiText) {
  try {
    // Try to extract JSON from markdown code blocks
    const jsonMatch = aiText.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    const jsonString = jsonMatch ? jsonMatch[1] : aiText;
    
    const parsed = JSON.parse(jsonString);
    return { success: true, data: parsed };
  } catch (error) {
    return { success: false, error: `JSON parsing failed: ${error.message}`, rawText: aiText };
  }
}

/**
 * Extract footnote data from 10-K/10-Q filings using AI
 */
async function extractFootnoteData(ticker, filingText) {
  const prompt = `
Extract the following financial data from this ${ticker} SEC filing. Return ONLY valid JSON matching this exact schema:

{
  "tax_basis_pp_e": <number or null>,
  "nol_carryforward_amount": <number or null>,
  "useful_life_existing_assets": [{"asset_class": "<string>", "years": <number>}],
  "lease_liability_operating": <number>,
  "lease_liability_finance": <number>,
  "rent_expense_ltm": <number>,
  "deferred_tax_assets": <number>,
  "deferred_tax_liabilities": <number>,
  "goodwill_and_intangibles": <number>,
  "pension_opeb_obligations": <number>,
  "capital_commitments": {"year_1": <number>, "years_1_3": <number>, "years_3_5": <number>, "beyond_5": <number>},
  "tax_jurisdiction_statutory_rates": [{"jurisdiction": "<string>", "rate": <number>}],
  "segment_revenue_breakdown": [{"segment": "<string>", "revenue": <number>, "pct": <number>}],
  "confidence_score": <number 0-1>
}

Filing text excerpt:
${filingText.substring(0, 15000)}
`;

  const systemInstruction = 'You are an expert financial analyst specializing in SEC filing analysis. Extract precise numerical data from footnotes. If a value cannot be found, return null. Always respond with valid JSON only.';
  
  const result = await callAIWithFallback(prompt, systemInstruction, 'footnote_extraction');
  
  if (result.source !== 'mock_fallback') {
    const parsed = parseAIJsonResponse(result.data);
    if (parsed.success) {
      return { ...parsed.data, extraction_source: result.source };
    }
  }
  
  return getMockAIData('footnote_extraction').ai_footnote_extractions;
}

/**
 * Extract forward guidance from earnings calls and MD&A using AI
 */
async function extractForwardGuidance(ticker, transcriptText) {
  const prompt = `
Analyze this ${ticker} earnings call transcript and MD&A section. Extract forward-looking guidance and return ONLY valid JSON:

{
  "plant_utilization_target": <number 0-1 or null>,
  "projected_interest_rate_on_debt": <number or null>,
  "projected_depreciation_rate": <number or null>,
  "working_capital_policy_change_days": <number or null>,
  "capex_as_pct_of_revenue_forecast": <number or null>,
  "revenue_growth_forecast_5y": [<number>, <number>, <number>, <number>, <number>],
  "management_guidance_notes": "<string summary>",
  "confidence_score": <number 0-1>
}

Transcript/MD&A text:
${transcriptText.substring(0, 15000)}
`;

  const systemInstruction = 'You are an expert at analyzing earnings call transcripts. Identify quantitative guidance and qualitative forward statements. Summarize management outlook accurately.';
  
  const result = await callAIWithFallback(prompt, systemInstruction, 'forward_guidance');
  
  if (result.source !== 'mock_fallback') {
    const parsed = parseAIJsonResponse(result.data);
    if (parsed.success) {
      return { ...parsed.data, extraction_source: result.source };
    }
  }
  
  return getMockAIData('forward_guidance').ai_contextual_forward_guidance;
}

/**
 * Calculate hybrid adjustments combining API data with AI insights
 */
async function calculateHybridAdjustments(ticker, apiFinancialData, aiExtractions) {
  const prompt = `
Given this financial data for ${ticker} and AI-extracted footnote information, calculate adjusted metrics. Return ONLY valid JSON:

API Data Summary:
- Revenue: $${apiFinancialData.income_statement_raw.revenue_total.toLocaleString()}
- EBITDA: $${apiFinancialData.income_statement_raw.ebitda.toLocaleString()}
- Net Income: $${apiFinancialData.income_statement_raw.net_income.toLocaleString()}
- Total Assets: $${apiFinancialData.balance_sheet_raw.total_assets.toLocaleString()}
- Total Equity: $${apiFinancialData.balance_sheet_raw.total_equity.toLocaleString()}

AI Extractions:
- Operating Lease Liability: $${aiExtractions.lease_liability_operating?.toLocaleString() || 'N/A'}
- Deferred Tax Assets: $${aiExtractions.deferred_tax_assets?.toLocaleString() || 'N/A'}
- Deferred Tax Liabilities: $${aiExtractions.deferred_tax_liabilities?.toLocaleString() || 'N/A'}

Calculate and return:
{
  "adjusted_ebitda": <number>,
  "adjusted_net_income": <number>,
  "lease_adjusted_enterprise_value": <number>,
  "ev_ebitda_ex_rent": <number>,
  "tangible_equity_multiplier": <number>,
  "lease_adjusted_asset_turnover": <number>,
  "normalized_tax_burden": <number>,
  "net_debt_post_operating_leases": <number>,
  "confidence_score": <number 0-1>
}
`;

  const systemInstruction = 'You are a valuation expert. Calculate adjusted financial metrics by incorporating off-balance-sheet items and normalizing for one-time effects. Show your reasoning then provide JSON.';
  
  const result = await callAIWithFallback(prompt, systemInstruction, 'hybrid_adjustments');
  
  if (result.source !== 'mock_fallback') {
    const parsed = parseAIJsonResponse(result.data);
    if (parsed.success) {
      return { ...parsed.data, calculation_source: result.source };
    }
  }
  
  return getMockAIData('hybrid_adjustments').ai_api_hybrid_adjustments;
}

/**
 * AI-powered peer company matching and analysis
 */
async function analyzePeerMatching(ticker, sector, marketCap) {
  const prompt = `
Identify and analyze peer companies for ${ticker} (Sector: ${sector}, Market Cap: $${(marketCap/1e9).toFixed(1)}B). Return ONLY valid JSON:

{
  "ai_suggested_peer_tickers": ["<ticker1>", "<ticker2>", "<ticker3>", "<ticker4>", "<ticker5>"],
  "business_model_similarity_score": <number 0-1>,
  "geographic_exposure_match": {"primary_regions": ["<region1>", "<region2>"], "match_pct": <number>},
  "size_band_ratio": <number>,
  "growth_differential": <number>,
  "conglomerate_diversification_flag": <boolean>,
  "exclusion_reasons_ai": ["<reason>" or empty array],
  "peer_quality_score_composite": <number 0-100>,
  "confidence_score": <number 0-1>
}

Provide rationale for peer selection based on business model, geography, size, and growth profile.
`;

  const systemInstruction = 'You are an equity research analyst. Select appropriate comparable companies based on multiple dimensions. Justify exclusions clearly.';
  
  const result = await callAIWithFallback(prompt, systemInstruction, 'peer_matching');
  
  if (result.source !== 'mock_fallback') {
    const parsed = parseAIJsonResponse(result.data);
    if (parsed.success) {
      return { ...parsed.data, analysis_source: result.source };
    }
  }
  
  return getMockAIData('peer_matching').ai_peer_matching_analysis;
}

/**
 * Generate AI-powered valuation suggestions and scenario weights
 */
async function generateValuationSuggestions(ticker, financialData, peerAnalysis) {
  const prompt = `
Based on this analysis of ${ticker}, provide valuation recommendations. Return ONLY valid JSON:

Company Metrics:
- WACC: ${(financialData.wacc_components?.wacc_calc_base * 100)?.toFixed(2) || 'N/A'}%
- Current EV/EBITDA: ${financialData.comps_specific_calculated?.target_ev_ebitda?.toFixed(2) || 'N/A'}x
- Peer Median EV/EBITDA: ${peerAnalysis.peer_ev_ebitda_median || 'N/A'}x
- 5Y Revenue CAGR: ${(financialData.calculated_metrics_common?.revenue_growth_3y_cagr * 100)?.toFixed(1) || 'N/A'}%
- ROE: ${(financialData.calculated_metrics_common?.roe * 100)?.toFixed(1) || 'N/A'}%

Provide:
{
  "growth_adjusted_terminal_multiple_suggestion": <number>,
  "implied_credit_spread_from_guidance": <number>,
  "forward_ebitda_margin_ai_adjusted": <number>,
  "scenario_weight_suggestions": {"best_case_weight": <number>, "base_case_weight": <number>, "worst_case_weight": <number>},
  "quality_discount_premium_suggestion": <number>,
  "confidence_score": <number 0-1>,
  "rationale": "<brief explanation>"
}
`;

  const systemInstruction = 'You are a senior valuation analyst. Provide reasoned suggestions for key valuation inputs based on company fundamentals, peer comparisons, and industry dynamics.';
  
  const result = await callAIWithFallback(prompt, systemInstruction, 'valuation_suggestions');
  
  if (result.source !== 'mock_fallback') {
    const parsed = parseAIJsonResponse(result.data);
    if (parsed.success) {
      return { ...parsed.data, suggestion_source: result.source };
    }
  }
  
  return getMockAIData('valuation_suggestions').ai_hybrid_valuation_suggestions;
}

/**
 * Get comprehensive AI-powered inputs for Step 5 checklist
 */
async function getAIInputsForModel(ticker, modelType, financialData = null) {
  const timestamp = new Date().toISOString();
  const result = {
    ticker,
    model_type: modelType,
    extraction_timestamp: timestamp,
    validation_status: 'pending',
    ai_metadata_and_audit: {
      confidence_score_overall: 0,
      confidence_scores_by_field: {},
      extraction_timestamp: timestamp,
      validation_status: 'pending',
      parsing_model_version: AI_CONFIG.primary
    }
  };
  
  // Get all AI extractions in parallel where possible
  const [footnoteData, guidanceData] = await Promise.all([
    extractFootnoteData(ticker, getMockFilingText(ticker)),
    extractForwardGuidance(ticker, getMockTranscriptText(ticker))
  ]);
  
  result.ai_footnote_extractions = footnoteData;
  result.ai_contextual_forward_guidance = guidanceData;
  
  // Calculate hybrid adjustments if we have financial data
  if (financialData) {
    result.ai_api_hybrid_adjustments = await calculateHybridAdjustments(ticker, financialData, footnoteData);
  } else {
    result.ai_api_hybrid_adjustments = getMockAIData('hybrid_adjustments').ai_api_hybrid_adjustments;
  }
  
  // Model-specific AI analyses
  if (modelType === 'COMPS' || modelType === 'ALL') {
    result.ai_peer_matching_analysis = await analyzePeerMatching(ticker, 'Technology', financialData?.market_structure?.market_capitalization || 1000000000000);
  }
  
  if (financialData && (modelType === 'DCF' || modelType === 'COMPS' || modelType === 'ALL')) {
    result.ai_hybrid_valuation_suggestions = await generateValuationSuggestions(
      ticker, 
      financialData, 
      result.ai_peer_matching_analysis || { peer_ev_ebitda_median: 13.1 }
    );
  }
  
  // Calculate overall confidence
  const scores = [
    footnoteData.confidence_score_overall || 0.8,
    guidanceData.confidence_score_overall || 0.8,
    result.ai_api_hybrid_adjustments?.confidence_score_overall || 0.85
  ].filter(s => s > 0);
  
  result.ai_metadata_and_audit.confidence_score_overall = scores.reduce((a, b) => a + b, 0) / scores.length;
  result.ai_metadata_and_audit.validation_status = 
    result.ai_metadata_and_audit.confidence_score_overall >= AI_CONFIG.confidenceThreshold 
      ? 'verified' 
      : 'flagged_for_review';
  
  return result;
}

// Mock filing text for demonstration (in production, fetch from SEC EDGAR)
function getMockFilingText(ticker) {
  return `
    ${ticker} 10-K FILING EXCERPT
    
    NOTE 1 — SUMMARY OF SIGNIFICANT ACCOUNTING POLICIES
    
    Property, Plant and Equipment: The Company records PP&E at cost. For tax purposes, the Company utilizes accelerated depreciation methods. The estimated useful lives are: Buildings 30 years, Machinery and Equipment 10 years, Computer Equipment 3-5 years.
    
    Leases: The Company has operating leases for retail locations and corporate offices with remaining terms of 1-15 years. Operating lease liability as of fiscal year end: $12.0 billion. Finance lease liabilities: $1.5 billion. Rent expense for the trailing twelve months was $2.5 billion.
    
    Income Taxes: Deferred tax assets of $8.0 billion and deferred tax liabilities of $5.0 billion relate to temporary differences in depreciation methods and accrued liabilities. The Company has no material NOL carryforwards. Effective tax jurisdictions include United States (21%), Ireland (12.5%), and Singapore (17%).
    
    Segment Information: The Company operates in two reportable segments: Products ($298B revenue, 76%) and Services ($96B revenue, 24%).
    
    Commitments: Capital commitments for the next 5 years are approximately $55 billion, with $15B in Year 1, $25B in Years 1-3, $10B in Years 3-5, and $5B beyond Year 5.
    
    Pension and OPEB: Net pension and other post-employment benefit obligations total $3.0 billion.
    
    Contingencies: The Company is subject to various legal proceedings. Management estimates potential liabilities of approximately $500 million.
  `;
}

// Mock transcript text for demonstration
function getMockTranscriptText(ticker) {
  return `
    ${ticker} Q4 2024 EARNINGS CALL TRANSCRIPT EXCERPT
    
    CEO REMARKS:
    We delivered strong results in Q4, capping off a successful year. Looking ahead to 2025, we expect revenue growth of approximately 5%, accelerating to 6% in 2026 as our new product categories gain traction. We anticipate moderating to 5% and 4.5% growth in the outer years as we lap comparables.
    
    Our capacity utilization currently stands at 82%, and we're targeting 85% utilization through operational efficiency initiatives planned for next year.
    
    CFO REMARKS:
    For capital expenditures, we expect CapEx to remain around 3.5% of revenue as we continue investing in infrastructure and R&D facilities. Depreciation and amortization should run at approximately 2.9% of gross PPE annually.
    
    On working capital, we're implementing initiatives to reduce our cash conversion cycle by about 2 days per year through better inventory management and receivables collection.
    
    Regarding financing costs, with our current credit profile and expected debt paydown, we project our effective interest rate on debt to stabilize around 3.5%.
    
    Our focus remains on margin expansion, targeting EBITDA margins of 32.5% over the medium term through mix shift toward higher-margin services and operational leverage.
    
    Q&A HIGHLIGHTS:
    Analyst Question: Can you provide more color on your capital allocation priorities?
    Management Response: We remain committed to balanced capital allocation: reinvesting in the business, returning cash to shareholders through buybacks and dividends, and pursuing strategic M&A where appropriate. Our strong cash flow generation supports all these priorities.
  `;
}

const modelRequiredFields = {
  DCF: [
    { name: 'revenue', status: 'pending' },
    { name: 'operatingMargin', status: 'pending' },
    { name: 'taxRate', status: 'pending' },
    { name: 'capex', status: 'pending' },
    { name: 'depreciation', status: 'pending' },
    { name: 'workingCapitalChange', status: 'pending' },
    { name: 'wacc', status: 'pending' },
    { name: 'terminalGrowthRate', status: 'pending' },
    { name: 'sharesOutstanding', status: 'pending' }
  ],
  COMPS: [
    { name: 'peRatio', status: 'pending' },
    { name: 'evEbitda', status: 'pending' },
    { name: 'priceToBook', status: 'pending' },
    { name: 'evSales', status: 'pending' },
    { name: 'peerMultiples', status: 'pending' }
  ],
  DUPONT: [
    { name: 'netIncome', status: 'pending' },
    { name: 'revenue', status: 'pending' },
    { name: 'totalAssets', status: 'pending' },
    { name: 'shareholderEquity', status: 'pending' },
    { name: 'profitMargin', status: 'pending' },
    { name: 'assetTurnover', status: 'pending' },
    { name: 'equityMultiplier', status: 'pending' }
  ],
  REALESTATE: [
    { name: 'noi', status: 'pending' },
    { name: 'capRate', status: 'pending' },
    { name: 'propertyValue', status: 'pending' },
    { name: 'occupancyRate', status: 'pending' }
  ]
};

const benchmarkRanges = {
  wacc: { min: 6.0, max: 12.0, median: 8.5, source: 'Damodaran Sector WACC' },
  terminalGrowthRate: { min: 1.5, max: 3.5, median: 2.5, source: 'Long-term GDP Growth' },
  operatingMargin: { min: 15.0, max: 30.0, median: 22.0, source: 'Sector Peer Analysis' },
  peRatio: { min: 15.0, max: 35.0, median: 22.0, source: 'S&P 500 Historical' },
  evEbitda: { min: 8.0, max: 18.0, median: 12.0, source: 'Industry Benchmarks' }
};

// API Routes

// Step 2: Search tickers
app.get('/api/search', (req, res) => {
  const query = req.query.q?.toUpperCase() || '';
  
  // Simulate API search
  const results = Object.values(mockTickerSearch)
    .filter(item => 
      item.ticker.includes(query) || 
      item.name.toUpperCase().includes(query)
    )
    .slice(0, 5);
  
  if (results.length === 0) {
    return res.json({ success: true, data: [], message: 'No results found' });
  }
  
  res.json({ success: true, data: results });
});

// Step 3: Select company
app.post('/api/select-company', (req, res) => {
  const { ticker, companyName, exchange } = req.body;
  
  valuationState = {
    ...valuationState,
    ticker,
    companyName,
    exchange,
    selectedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: `Selected: ${companyName} (${ticker})`,
    state: valuationState
  });
});

// Step 4: Get available models
app.get('/api/models', (req, res) => {
  res.json({ success: true, data: valuationModels });
});

// Step 4: Select model
app.post('/api/select-model', (req, res) => {
  const { modelType } = req.body;
  
  valuationState = {
    ...valuationState,
    modelType,
    selectedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: `Model selected: ${modelType}`,
    state: valuationState
  });
});

// ============================================
// NEW AI-POWERED ENDPOINTS (Step 5 - AI Inputs)
// ============================================

/**
 * Get AI-extracted inputs for a specific model
 * Combines footnote extractions, forward guidance, and hybrid adjustments
 */
app.get('/api/ai-inputs/:ticker', async (req, res) => {
  const { ticker } = req.params;
  const { model = 'ALL' } = req.query;
  
  try {
    console.log(`[API] Fetching AI inputs for ${ticker} (model: ${model})`);
    
    // First get API financial data if available
    let financialData = null;
    try {
      financialData = await getComprehensiveFinancialData(ticker);
    } catch (error) {
      console.log(`[API] Could not fetch financial data: ${error.message}`);
    }
    
    // Get AI-powered inputs
    const aiInputs = await getAIInputsForModel(ticker, model.toUpperCase(), financialData);
    
    res.json({
      success: true,
      data: aiInputs,
      metadata: {
        api_used: aiInputs.ai_metadata_and_audit.parsing_model_version,
        confidence: aiInputs.ai_metadata_and_audit.confidence_score_overall,
        status: aiInputs.ai_metadata_and_audit.validation_status
      }
    });
  } catch (error) {
    console.error(`[API Error] AI inputs failed: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message,
      fallback_available: true
    });
  }
});

/**
 * Get combined API + AI inputs for Step 5 checklist
 * Shows which fields are populated by API vs AI vs manual entry required
 */
app.get('/api/combined-inputs/:ticker', async (req, res) => {
  const { ticker } = req.params;
  const { model = 'DCF' } = req.query;
  
  try {
    console.log(`[API] Fetching combined inputs for ${ticker} (model: ${model})`);
    
    // Get API financial data
    const [financialData, aiInputs] = await Promise.all([
      getComprehensiveFinancialData(ticker),
      getAIInputsForModel(ticker, model.toUpperCase(), null)
    ]);
    
    // Build unified checklist showing data sources
    const combinedInputs = {
      ticker,
      model_type: model.toUpperCase(),
      timestamp: new Date().toISOString(),
      
      // API-retrievable fields (Step 5 - Category A)
      api_inputs: {
        source: 'Alpha Vantage + Yahoo Finance',
        reliability: 'Very High',
        data: {
          market_structure: financialData.market_structure,
          income_statement: financialData.income_statement_raw,
          balance_sheet: financialData.balance_sheet_raw,
          cash_flow: financialData.cash_flow_raw,
          calculated_metrics: financialData.calculated_metrics_common,
          wacc_components: financialData.wacc_components
        },
        field_count: Object.keys(financialData.market_structure).length +
                     Object.keys(financialData.income_statement_raw).length +
                     Object.keys(financialData.balance_sheet_raw).length +
                     Object.keys(financialData.cash_flow_raw).length
      },
      
      // AI-retrievable fields (Step 5 - Category B)
      ai_inputs: {
        source: aiInputs.ai_metadata_and_audit.parsing_model_version,
        reliability: aiInputs.ai_metadata_and_audit.validation_status,
        confidence: aiInputs.ai_metadata_and_audit.confidence_score_overall,
        data: {
          footnote_extractions: aiInputs.ai_footnote_extractions,
          forward_guidance: aiInputs.ai_contextual_forward_guidance,
          hybrid_adjustments: aiInputs.ai_api_hybrid_adjustments,
          peer_analysis: aiInputs.ai_peer_matching_analysis,
          valuation_suggestions: aiInputs.ai_hybrid_valuation_suggestions
        },
        field_count: Object.keys(aiInputs.ai_footnote_extractions || {}).length +
                     Object.keys(aiInputs.ai_contextual_forward_guidance || {}).length +
                     Object.keys(aiInputs.ai_api_hybrid_adjustments || {}).length
      },
      
      // Manual entry required (Step 5 - Category C)
      manual_inputs_required: {
        source: 'User Input Required',
        fields: [
          { name: 'scenario_assumptions', description: 'Best/Base/Worst case growth rates', required_for: ['DCF'] },
          { name: 'terminal_growth_rate_override', description: 'Override AI suggestion if needed', required_for: ['DCF'] },
          { name: 'peer_selection_override', description: 'Customize peer group', required_for: ['COMPS'] },
          { name: 'multiple_selection_weights', description: 'Weight different multiples', required_for: ['COMPS'] },
          { name: 'duPont_improvement_initiatives', description: 'Specific operational initiatives', required_for: ['DUPONT'] }
        ].filter(f => !f.required_for.includes(model.toUpperCase()) || f.required_for.includes(model.toUpperCase()))
      }
    };
    
    res.json({
      success: true,
      data: combinedInputs,
      summary: {
        total_api_fields: combinedInputs.api_inputs.field_count,
        total_ai_fields: combinedInputs.ai_inputs.field_count,
        manual_fields_required: combinedInputs.manual_inputs_required.fields.length,
        auto_population_pct: Math.round(
          (combinedInputs.api_inputs.field_count + combinedInputs.ai_inputs.field_count) / 
          (combinedInputs.api_inputs.field_count + combinedInputs.ai_inputs.field_count + combinedInputs.manual_inputs_required.fields.length) * 100
        )
      }
    });
  } catch (error) {
    console.error(`[API Error] Combined inputs failed: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/historical-financials/:ticker
 * Fetch 3 years of historical financial data for DCF model
 * Dynamically resolves FY-3, FY-2, FY-1 based on latest fiscal year end
 */
app.get('/api/historical-financials/:ticker', async (req, res) => {
  const { ticker } = req.params;
  
  try {
    console.log(`[API] Fetching historical financials for ${ticker}`);
    
    const historicalData = await fetchHistoricalFinancials3Y(ticker.toUpperCase());
    
    res.json({
      success: true,
      data: historicalData
    });
  } catch (error) {
    console.error(`[API Error] Historical financials failed: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Extract data from custom filing text (user-provided SEC filing excerpt)
 */
app.post('/api/extract-from-filing', async (req, res) => {
  const { ticker, filingText, extractionType = 'all' } = req.body;
  
  if (!ticker || !filingText) {
    return res.status(400).json({
      success: false,
      error: 'Missing required fields: ticker and filingText'
    });
  }
  
  try {
    console.log(`[API] Extracting from custom filing for ${ticker}`);
    
    const result = {
      ticker,
      extraction_timestamp: new Date().toISOString(),
      extractions: {}
    };
    
    if (extractionType === 'all' || extractionType === 'footnotes') {
      result.extractions.footnotes = await extractFootnoteData(ticker, filingText);
    }
    
    if (extractionType === 'all' || extractionType === 'guidance') {
      result.extractions.guidance = await extractForwardGuidance(ticker, filingText);
    }
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error(`[API Error] Filing extraction failed: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Get AI peer analysis with customizable parameters
 */
app.get('/api/ai-peer-analysis/:ticker', async (req, res) => {
  const { ticker } = req.params;
  const { sector = 'Technology', customPeers } = req.query;
  
  try {
    console.log(`[API] Analyzing peers for ${ticker}`);
    
    // Get market cap from financial data
    let marketCap = 1000000000000; // Default $1T
    try {
      const financialData = await getComprehensiveFinancialData(ticker);
      marketCap = financialData.market_structure.market_capitalization;
    } catch (error) {
      console.log('Using default market cap');
    }
    
    const peerAnalysis = await analyzePeerMatching(ticker, sector, marketCap);
    
    res.json({
      success: true,
      data: {
        ticker,
        sector,
        market_cap_billions: (marketCap / 1e9).toFixed(1),
        analysis: peerAnalysis,
        confidence: peerAnalysis.confidence_score_overall
      }
    });
  } catch (error) {
    console.error(`[API Error] Peer analysis failed: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Generate valuation suggestions with scenario weights
 */
app.get('/api/ai-valuation-suggestions/:ticker', async (req, res) => {
  const { ticker } = req.params;
  
  try {
    console.log(`[API] Generating valuation suggestions for ${ticker}`);
    
    const [financialData, peerAnalysis] = await Promise.all([
      getComprehensiveFinancialData(ticker),
      analyzePeerMatching(ticker, 'Technology', 1000000000000)
    ]);
    
    const suggestions = await generateValuationSuggestions(ticker, financialData, peerAnalysis);
    
    res.json({
      success: true,
      data: {
        ticker,
        current_metrics: {
          wacc: (financialData.wacc_components?.wacc_calc_base * 100)?.toFixed(2) + '%',
          ev_ebitda: financialData.comps_specific_calculated?.target_ev_ebitda?.toFixed(2) + 'x',
          roe: (financialData.calculated_metrics_common?.roe * 100)?.toFixed(1) + '%'
        },
        ai_suggestions: suggestions,
        confidence: suggestions.confidence_score_overall
      }
    });
  } catch (error) {
    console.error(`[API Error] Valuation suggestions failed: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Step 5: Get required fields for selected model
app.get('/api/required-fields', (req, res) => {
  const modelType = req.query.model || valuationState.modelType;
  
  if (!modelType || !modelRequiredFields[modelType]) {
    return res.status(400).json({ 
      success: false, 
      error: 'Invalid or missing model type' 
    });
  }
  
  res.json({ 
    success: true, 
    data: modelRequiredFields[modelType],
    modelType
  });
});

// Step 6: Retrieve live data (simulated)
app.post('/api/retrieve-data', async (req, res) => {
  const { modelType } = req.body;
  
  // Simulate API retrieval delay
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  // Mock retrieved data
  const retrievedData = {
    revenue: { value: 394328000000, source: 'yfinance', status: 'found' },
    operatingMargin: { value: 0.297, source: 'yfinance', status: 'found' },
    taxRate: { value: 0.145, source: 'calculated', status: 'found' },
    capex: { value: -10959000000, source: 'yfinance', status: 'found' },
    depreciation: { value: 11519000000, source: 'yfinance', status: 'found' },
    workingCapitalChange: { value: -1688000000, source: 'calculated', status: 'found' },
    wacc: { value: 0.089, source: 'calculated', status: 'found' },
    terminalGrowthRate: { value: 0.025, source: 'default', status: 'estimated' },
    sharesOutstanding: { value: 15552752000, source: 'yfinance', status: 'found' },
    currentPrice: { value: 189.84, source: 'yfinance', status: 'found' }
  };
  
  valuationState = {
    ...valuationState,
    apiData: retrievedData,
    dataRetrievedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    data: retrievedData,
    message: 'Data retrieved successfully'
  });
});

// ============================================
// NEW STEP 5 ENDPOINTS: API-RETRIEVABLE REQUIRED INPUTS
// ============================================

/**
 * Step 5: Get comprehensive financial data for selected company
 * Returns all API-retrievable fields per the Unified Valuation API Schema
 */
app.get('/api/financial-data/:ticker', async (req, res) => {
  const { ticker } = req.params;
  
  try {
    const financialData = await getComprehensiveFinancialData(ticker.toUpperCase());
    
    valuationState = {
      ...valuationState,
      ticker: ticker.toUpperCase(),
      financialData,
      dataRetrievedAt: new Date().toISOString()
    };
    
    res.json({
      success: true,
      data: financialData,
      message: `Financial data retrieved for ${ticker.toUpperCase()}`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      message: 'Failed to retrieve financial data'
    });
  }
});

/**
 * Step 5: Get required inputs checklist with API-retrievable status
 * Shows which fields can be auto-populated from APIs vs need manual input
 */
app.get('/api/required-inputs-checklist', (req, res) => {
  const modelType = req.query.model || valuationState.modelType || 'DCF';
  
  const checklistByModel = {
    DCF: {
      category: 'Discounted Cash Flow',
      inputs: [
        { field: 'revenue_total', label: 'Total Revenue (TTM)', apiRetrievable: true, source: 'Alpha Vantage OVERVIEW', status: 'pending', value: null },
        { field: 'ebit_operating_income', label: 'Operating Income (EBIT)', apiRetrievable: true, source: 'Alpha Vantage INCOME_STATEMENT', status: 'pending', value: null },
        { field: 'tax_provision', label: 'Tax Provision', apiRetrievable: true, source: 'Alpha Vantage INCOME_STATEMENT', status: 'pending', value: null },
        { field: 'capital_expenditures_capex', label: 'Capital Expenditures', apiRetrievable: true, source: 'Alpha Vantage CASH_FLOW', status: 'pending', value: null },
        { field: 'depreciation_and_amortization', label: 'Depreciation & Amortization', apiRetrievable: true, source: 'Alpha Vantage CASH_FLOW', status: 'pending', value: null },
        { field: 'change_in_working_capital', label: 'Change in Working Capital', apiRetrievable: true, source: 'Calculated from Balance Sheet', status: 'pending', value: null },
        { field: 'wacc_calc_base', label: 'WACC', apiRetrievable: true, source: 'Calculated (CAPM)', status: 'pending', value: null },
        { field: 'terminal_growth_rate', label: 'Terminal Growth Rate', apiRetrievable: false, source: 'Manual/Default', status: 'pending', value: null },
        { field: 'shares_outstanding_diluted', label: 'Shares Outstanding (Diluted)', apiRetrievable: true, source: 'Yahoo Finance', status: 'pending', value: null },
        { field: 'current_price', label: 'Current Stock Price', apiRetrievable: true, source: 'Yahoo Finance', status: 'pending', value: null },
        { field: 'risk_free_rate_10y', label: 'Risk-Free Rate (10Y)', apiRetrievable: true, source: 'FRED DGS10', status: 'pending', value: null },
        { field: 'equity_risk_premium', label: 'Equity Risk Premium', apiRetrievable: false, source: 'Damodaran/Manual', status: 'pending', value: null },
        { field: 'beta_5y_monthly', label: 'Beta (5Y Monthly)', apiRetrievable: true, source: 'Yahoo Finance', status: 'pending', value: null }
      ]
    },
    COMPS: {
      category: 'Trading Comps',
      inputs: [
        { field: 'current_price', label: 'Current Stock Price', apiRetrievable: true, source: 'Yahoo Finance', status: 'pending', value: null },
        { field: 'market_capitalization', label: 'Market Cap', apiRetrievable: true, source: 'Yahoo Finance', status: 'pending', value: null },
        { field: 'enterprise_value', label: 'Enterprise Value', apiRetrievable: true, source: 'Calculated', status: 'pending', value: null },
        { field: 'ebitda', label: 'EBITDA (TTM)', apiRetrievable: true, source: 'Alpha Vantage OVERVIEW', status: 'pending', value: null },
        { field: 'revenue_total', label: 'Revenue (TTM)', apiRetrievable: true, source: 'Alpha Vantage OVERVIEW', status: 'pending', value: null },
        { field: 'ebit_operating_income', label: 'EBIT', apiRetrievable: true, source: 'Alpha Vantage INCOME_STATEMENT', status: 'pending', value: null },
        { field: 'net_income', label: 'Net Income', apiRetrievable: true, source: 'Alpha Vantage OVERVIEW', status: 'pending', value: null },
        { field: 'total_equity', label: 'Total Equity', apiRetrievable: true, source: 'Alpha Vantage BALANCE_SHEET', status: 'pending', value: null },
        { field: 'free_cash_flow', label: 'Free Cash Flow', apiRetrievable: true, source: 'Calculated', status: 'pending', value: null },
        { field: 'peer_ev_ebitda_median', label: 'Peer EV/EBITDA Median', apiRetrievable: false, source: 'Manual/Analysis', status: 'pending', value: null },
        { field: 'peer_pe_array', label: 'Peer P/E Multiples', apiRetrievable: false, source: 'Manual/Analysis', status: 'pending', value: null }
      ]
    },
    DUPONT: {
      category: 'DuPont Analysis',
      inputs: [
        { field: 'net_income', label: 'Net Income', apiRetrievable: true, source: 'Alpha Vantage OVERVIEW', status: 'pending', value: null },
        { field: 'revenue_total', label: 'Total Revenue', apiRetrievable: true, source: 'Alpha Vantage OVERVIEW', status: 'pending', value: null },
        { field: 'total_assets', label: 'Total Assets', apiRetrievable: true, source: 'Alpha Vantage BALANCE_SHEET', status: 'pending', value: null },
        { field: 'total_equity', label: 'Total Equity', apiRetrievable: true, source: 'Alpha Vantage BALANCE_SHEET', status: 'pending', value: null },
        { field: 'pre_tax_income_ebt', label: 'Pre-Tax Income', apiRetrievable: true, source: 'Alpha Vantage INCOME_STATEMENT', status: 'pending', value: null },
        { field: 'ebit_operating_income', label: 'EBIT', apiRetrievable: true, source: 'Alpha Vantage INCOME_STATEMENT', status: 'pending', value: null },
        { field: 'gross_profit', label: 'Gross Profit', apiRetrievable: true, source: 'Alpha Vantage INCOME_STATEMENT', status: 'pending', value: null },
        { field: 'current_ratio', label: 'Current Ratio', apiRetrievable: true, source: 'Calculated', status: 'pending', value: null },
        { field: 'quick_ratio', label: 'Quick Ratio', apiRetrievable: true, source: 'Calculated', status: 'pending', value: null }
      ]
    }
  };
  
  const checklist = checklistByModel[modelType] || checklistByModel.DCF;
  
  res.json({
    success: true,
    data: checklist,
    modelType,
    summary: {
      totalInputs: checklist.inputs.length,
      apiRetrievable: checklist.inputs.filter(i => i.apiRetrievable).length,
      manualRequired: checklist.inputs.filter(i => !i.apiRetrievable).length
    }
  });
});

/**
 * Step 5: Auto-populate retrievable fields from APIs
 * Fetches all available data and marks fields as 'found'
 */
app.post('/api/auto-populate-inputs', async (req, res) => {
  const { modelType, ticker } = req.body;
  const targetTicker = ticker || valuationState.ticker;
  
  if (!targetTicker) {
    return res.status(400).json({
      success: false,
      error: 'No ticker specified. Please select a company first.'
    });
  }
  
  try {
    // Fetch comprehensive data
    const financialData = await getComprehensiveFinancialData(targetTicker);
    
    // Map to simplified key-value format for frontend consumption
    const populatedInputs = {
      // Market Structure
      current_price: { value: financialData.market_structure.current_price, source: 'yfinance', status: 'found' },
      shares_outstanding_diluted: { value: financialData.market_structure.shares_outstanding_diluted, source: 'yfinance', status: 'found' },
      market_capitalization: { value: financialData.market_structure.market_capitalization, source: 'yfinance', status: 'found' },
      enterprise_value: { value: financialData.market_structure.enterprise_value, source: 'calculated', status: 'found' },
      beta_5y_monthly: { value: financialData.market_structure.beta_5y_monthly, source: 'yfinance', status: 'found' },
      dividend_yield: { value: financialData.market_structure.dividend_yield, source: 'yfinance', status: 'found' },
      
      // Income Statement
      revenue_total: { value: financialData.income_statement_raw.revenue_total, source: 'alpha_vantage', status: 'found' },
      ebitda: { value: financialData.income_statement_raw.ebitda, source: 'alpha_vantage', status: 'found' },
      ebit_operating_income: { value: financialData.income_statement_raw.ebit_operating_income, source: 'alpha_vantage', status: 'found' },
      net_income: { value: financialData.income_statement_raw.net_income, source: 'alpha_vantage', status: 'found' },
      gross_profit: { value: financialData.income_statement_raw.gross_profit, source: 'alpha_vantage', status: 'found' },
      tax_provision: { value: financialData.income_statement_raw.tax_provision, source: 'alpha_vantage', status: 'found' },
      pre_tax_income_ebt: { value: financialData.income_statement_raw.pre_tax_income_ebt, source: 'alpha_vantage', status: 'found' },
      eps_diluted: { value: financialData.income_statement_raw.eps_diluted, source: 'yfinance', status: 'found' },
      
      // Balance Sheet
      total_assets: { value: financialData.balance_sheet_raw.total_assets, source: 'alpha_vantage', status: 'found' },
      total_equity: { value: financialData.balance_sheet_raw.total_equity, source: 'alpha_vantage', status: 'found' },
      total_liabilities: { value: financialData.balance_sheet_raw.total_liabilities, source: 'alpha_vantage', status: 'found' },
      total_current_assets: { value: financialData.balance_sheet_raw.total_current_assets, source: 'alpha_vantage', status: 'found' },
      total_current_liabilities: { value: financialData.balance_sheet_raw.total_current_liabilities, source: 'alpha_vantage', status: 'found' },
      inventory: { value: financialData.balance_sheet_raw.inventory, source: 'alpha_vantage', status: 'found' },
      accounts_receivable: { value: financialData.balance_sheet_raw.accounts_receivable, source: 'alpha_vantage', status: 'found' },
      accounts_payable: { value: financialData.balance_sheet_raw.accounts_payable, source: 'alpha_vantage', status: 'found' },
      
      // Cash Flow
      operating_cash_flow_cfo: { value: financialData.cash_flow_raw.operating_cash_flow_cfo, source: 'alpha_vantage', status: 'found' },
      capital_expenditures_capex: { value: financialData.cash_flow_raw.capital_expenditures_capex, source: 'alpha_vantage', status: 'found' },
      free_cash_flow: { value: financialData.cash_flow_raw.free_cash_flow, source: 'calculated', status: 'found' },
      change_in_working_capital: { value: financialData.cash_flow_raw.change_in_working_capital, source: 'calculated', status: 'found' },
      dividends_paid: { value: financialData.cash_flow_raw.dividends_paid, source: 'alpha_vantage', status: 'found' },
      
      // Calculated Metrics
      gross_margin: { value: financialData.calculated_metrics_common.gross_margin, source: 'calculated', status: 'found' },
      operating_margin: { value: financialData.calculated_metrics_common.operating_margin, source: 'calculated', status: 'found' },
      net_profit_margin: { value: financialData.calculated_metrics_common.net_profit_margin, source: 'calculated', status: 'found' },
      effective_tax_rate: { value: financialData.calculated_metrics_common.effective_tax_rate, source: 'calculated', status: 'found' },
      roe: { value: financialData.calculated_metrics_common.roe, source: 'calculated', status: 'found' },
      roa: { value: financialData.calculated_metrics_common.roa, source: 'calculated', status: 'found' },
      roic: { value: financialData.calculated_metrics_common.roic, source: 'calculated', status: 'found' },
      debt_to_equity: { value: financialData.calculated_metrics_common.debt_to_equity, source: 'calculated', status: 'found' },
      interest_coverage: { value: financialData.calculated_metrics_common.interest_coverage, source: 'calculated', status: 'found' },
      asset_turnover: { value: financialData.calculated_metrics_common.asset_turnover, source: 'calculated', status: 'found' },
      fcf_margin: { value: financialData.calculated_metrics_common.fcf_margin, source: 'calculated', status: 'found' },
      
      // WACC Components
      risk_free_rate_10y: { value: financialData.macro_indicators.risk_free_rate_10y, source: 'fred', status: 'found' },
      equity_risk_premium: { value: financialData.macro_indicators.equity_risk_premium, source: 'damodaran', status: 'found' },
      cost_of_equity_re: { value: financialData.wacc_components.cost_of_equity_re, source: 'calculated', status: 'found' },
      cost_of_debt_pre_tax: { value: financialData.wacc_components.cost_of_debt_pre_tax, source: 'calculated', status: 'found' },
      wacc_calc_base: { value: financialData.wacc_components.wacc_calc_base, source: 'calculated', status: 'found' },
      
      // Comps Specific
      target_ev_ebitda: { value: financialData.comps_specific_calculated.target_ev_ebitda, source: 'calculated', status: 'found' },
      target_ev_sales: { value: financialData.comps_specific_calculated.target_ev_sales, source: 'calculated', status: 'found' },
      target_pe_diluted: { value: financialData.comps_specific_calculated.target_pe_diluted, source: 'calculated', status: 'found' },
      target_pb: { value: financialData.comps_specific_calculated.target_pb, source: 'calculated', status: 'found' },
      peer_ev_ebitda_median: { value: financialData.comps_specific_calculated.peer_ev_ebitda_median, source: 'analysis', status: 'found' },
      
      // DuPont Specific
      tax_burden: { value: financialData.dupont_specific_components.tax_burden, source: 'calculated', status: 'found' },
      interest_burden: { value: financialData.dupont_specific_components.interest_burden, source: 'calculated', status: 'found' },
      roe_3step: { value: financialData.dupont_specific_components.roe_3step, source: 'calculated', status: 'found' },
      roe_5step: { value: financialData.dupont_specific_components.roe_5step, source: 'calculated', status: 'found' },
      current_ratio: { value: financialData.dupont_specific_components.current_ratio, source: 'calculated', status: 'found' },
      quick_ratio: { value: financialData.dupont_specific_components.quick_ratio, source: 'calculated', status: 'found' },
      
      // Manual/Estimated (not directly from API)
      terminal_growth_rate: { value: 0.025, source: 'default', status: 'estimated' },
      peer_ev_ebitda_array: { value: financialData.comps_specific_calculated.peer_ev_ebitda_array, source: 'analysis', status: 'found' },
      peer_pe_array: { value: financialData.comps_specific_calculated.peer_pe_array, source: 'analysis', status: 'found' }
    };
    
    valuationState = {
      ...valuationState,
      ticker: targetTicker,
      financialData,
      populatedInputs,
      dataRetrievedAt: new Date().toISOString()
    };
    
    res.json({
      success: true,
      data: populatedInputs,
      fullData: financialData,
      summary: {
        totalFields: Object.keys(populatedInputs).length,
        foundFromAPI: Object.values(populatedInputs).filter(i => i.status === 'found').length,
        estimated: Object.values(populatedInputs).filter(i => i.status === 'estimated').length
      },
      message: `Auto-populated ${Object.keys(populatedInputs).length} fields for ${targetTicker}`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      message: 'Failed to auto-populate inputs'
    });
  }
});

// Step 7: Get AI suggestions and benchmarks
app.get('/api/ai-suggestions', (req, res) => {
  const { field } = req.query;
  
  const aiSuggestions = {
    wacc: {
      apiValue: 0.089,
      aiSuggestion: 0.085,
      benchmark: benchmarkRanges.wacc,
      confidence: 0.87,
      source: 'Footnote parsing from 10-K'
    },
    terminalGrowthRate: {
      apiValue: 0.025,
      aiSuggestion: 0.025,
      benchmark: benchmarkRanges.terminalGrowthRate,
      confidence: 0.92,
      source: 'Management guidance extraction'
    },
    operatingMargin: {
      apiValue: 0.297,
      aiSuggestion: 0.285,
      benchmark: benchmarkRanges.operatingMargin,
      confidence: 0.78,
      source: 'Peer comparison analysis'
    }
  };
  
  if (field && aiSuggestions[field]) {
    res.json({ success: true, data: aiSuggestions[field] });
  } else {
    res.json({ success: true, data: aiSuggestions });
  }
});

// Step 7: Submit user-confirmed values
app.post('/api/confirm-values', (req, res) => {
  const { confirmedValues, auditLog } = req.body;
  
  valuationState = {
    ...valuationState,
    confirmedValues,
    auditLog: [...(valuationState.auditLog || []), ...auditLog],
    valuesConfirmedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: 'Values confirmed',
    state: valuationState
  });
});

// Step 8: Get scenario presets
app.get('/api/scenarios', (req, res) => {
  const scenarios = {
    best: {
      name: 'Best Case',
      description: 'Optimistic assumptions based on management guidance',
      overrides: {
        revenueGrowth: 0.15,
        operatingMargin: 0.32,
        terminalGrowthRate: 0.035
      }
    },
    base: {
      name: 'Base Case',
      description: 'Most likely scenario based on consensus estimates',
      overrides: {
        revenueGrowth: 0.08,
        operatingMargin: 0.28,
        terminalGrowthRate: 0.025
      }
    },
    worst: {
      name: 'Worst Case',
      description: 'Conservative assumptions considering downside risks',
      overrides: {
        revenueGrowth: 0.02,
        operatingMargin: 0.22,
        terminalGrowthRate: 0.015
      }
    }
  };
  
  res.json({ success: true, data: scenarios });
});

// Step 8: Select scenario
app.post('/api/select-scenario', (req, res) => {
  const { scenarioType, customOverrides } = req.body;
  
  valuationState = {
    ...valuationState,
    scenarioType,
    customOverrides: customOverrides || null,
    scenarioSelectedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: `Scenario selected: ${scenarioType}`,
    state: valuationState
  });
});

// Step 9: Run valuation model
app.post('/api/run-valuation', async (req, res) => {
  const { modelType, confirmedValues, scenario } = req.body;
  
  // Simulate calculation delay
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Mock valuation results
  const results = {
    primaryResult: {
      impliedSharePrice: 215.50,
      currentValue: 189.84,
      upside: 0.135,
      recommendation: 'BUY'
    },
    scenarioComparison: {
      best: { impliedSharePrice: 265.00, upside: 0.396 },
      base: { impliedSharePrice: 215.50, upside: 0.135 },
      worst: { impliedSharePrice: 165.00, upside: -0.131 }
    },
    sensitivityAnalysis: {
      waccSensitivity: [
        { wacc: 0.07, price: 245.00 },
        { wacc: 0.08, price: 228.00 },
        { wacc: 0.09, price: 215.50 },
        { wacc: 0.10, price: 205.00 },
        { wacc: 0.11, price: 195.00 }
      ],
      growthSensitivity: [
        { growth: 0.015, price: 195.00 },
        { growth: 0.020, price: 205.00 },
        { growth: 0.025, price: 215.50 },
        { growth: 0.030, price: 228.00 },
        { growth: 0.035, price: 245.00 }
      ]
    },
    auditTrail: {
      dataSources: {
        api: ['revenue', 'operatingMargin', 'sharesOutstanding'],
        ai: ['wacc', 'terminalGrowthRate'],
        benchmark: [],
        manual: []
      },
      confidenceScores: {
        overall: 0.85,
        byField: {
          wacc: 0.87,
          terminalGrowthRate: 0.92,
          operatingMargin: 0.78
        }
      },
      userOverrides: []
    }
  };
  
  valuationState = {
    ...valuationState,
    valuationResults: results,
    completedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    data: results,
    message: 'Valuation completed successfully'
  });
});

// Step 10: Get final results
app.get('/api/results', (req, res) => {
  if (!valuationState.valuationResults) {
    return res.status(404).json({ 
      success: false, 
      error: 'No valuation results found' 
    });
  }
  
  res.json({ 
    success: true, 
    data: valuationState.valuationResults,
    fullState: valuationState
  });
});

// Reset state
app.post('/api/reset', (req, res) => {
  valuationState = {};
  res.json({ success: true, message: 'State reset successfully' });
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ============================================================================
// SECTION 9: MANUAL INPUTS WITH AI BENCHMARK ASSISTANCE
// ============================================================================

/**
 * Manual inputs that require human judgment but are assisted by AI benchmarks
 */
const manualInputCategories = {
  dcf: [
    {
      field: 'terminal_growth_rate',
      label: 'Terminal Growth Rate (%)',
      description: 'Perpetual growth rate beyond forecast period',
      ai_benchmark_source: 'sector_gdp_long_term + industry_lifecycle',
      typical_range: [0.5, 3.5],
      requires_justification: true
    },
    {
      field: 'wacc_override',
      label: 'WACC Override (%)',
      description: 'Manual WACC adjustment (leave empty for calculated)',
      ai_benchmark_source: 'sector_wacc_distribution',
      typical_range: [6, 15],
      requires_justification: false
    },
    {
      field: 'forecast_capex_percent',
      label: 'CapEx as % of Revenue (Forecast Years)',
      description: 'Planned capital expenditure intensity',
      ai_benchmark_source: 'management_guidance + peer_capex_intensity',
      typical_range: [2, 25],
      requires_justification: true
    },
    {
      field: 'scenario_probabilities',
      label: 'Scenario Probabilities (%)',
      description: 'Best/Base/Worst case weights (must sum to 100)',
      ai_benchmark_source: 'historical_forecast_accuracy',
      typical_range: [10, 60],
      requires_justification: false
    },
    {
      field: 'specific_risk_premium',
      label: 'Company-Specific Risk Premium (%)',
      description: 'Additional premium for unique risks',
      ai_benchmark_source: 'size_premium + company_risk_factors',
      typical_range: [0, 5],
      requires_justification: true
    }
  ],
  comps: [
    {
      field: 'final_peer_selection',
      label: 'Final Peer Companies',
      description: 'Selected comparable companies for analysis',
      ai_benchmark_source: 'ai_peer_matching_analysis',
      typical_range: null,
      requires_justification: true
    },
    {
      field: 'control_premium_discount',
      label: 'Control Premium/Discount (%)',
      description: 'Adjustment for control vs minority interest',
      ai_benchmark_source: 'transaction_database_benchmarks',
      typical_range: [-25, 40],
      requires_justification: true
    },
    {
      field: 'illiquidity_discount',
      label: 'Illiquidity Discount (%)',
      description: 'Discount for lack of marketability',
      ai_benchmark_source: 'restricted_stock_studies',
      typical_range: [0, 35],
      requires_justification: false
    },
    {
      field: 'multiple_normalization_adjustments',
      label: 'Multiple Normalization Adjustments',
      description: 'Adjustments for accounting differences',
      ai_benchmark_source: 'accounting_policy_comparison',
      typical_range: [-20, 20],
      requires_justification: true
    },
    {
      field: 'outlier_exclusion_rationale',
      label: 'Outlier Exclusion Rationale',
      description: 'Justification for excluding certain peers',
      ai_benchmark_source: 'statistical_outlier_detection',
      typical_range: null,
      requires_justification: true
    }
  ],
  dupont: [
    {
      field: 'target_roe_improvement',
      label: 'Target ROE Improvement (bps)',
      description: 'Desired ROE enhancement through strategic initiatives',
      ai_benchmark_source: 'peer_roe_trajectory',
      typical_range: [50, 500],
      requires_justification: true
    },
    {
      field: 'margin_improvement_initiatives',
      label: 'Margin Improvement Initiatives',
      description: 'Expected impact from cost optimization',
      ai_benchmark_source: 'industry_margin_benchmarks',
      typical_range: [0.5, 5],
      requires_justification: true
    },
    {
      field: 'asset_turnover_target',
      label: 'Target Asset Turnover',
      description: 'Desired asset efficiency ratio',
      ai_benchmark_source: 'best_in_class_turnover',
      typical_range: [0.5, 3.0],
      requires_justification: false
    },
    {
      field: 'leverage_strategy',
      label: 'Leverage Strategy Adjustment',
      description: 'Planned change in financial leverage',
      ai_benchmark_source: 'optimal_capital_structure_analysis',
      typical_range: [-0.5, 1.0],
      requires_justification: true
    }
  ],
  common: [
    {
      field: 'esg_adjustment_factor',
      label: 'ESG Adjustment Factor (%)',
      description: 'Valuation adjustment for ESG considerations',
      ai_benchmark_source: 'esg_rating_impact_studies',
      typical_range: [-10, 15],
      requires_justification: true
    },
    {
      field: 'one_time_event_impact',
      label: 'One-Time Event Impact',
      description: 'Adjustment for M&A, restructuring, or unusual items',
      ai_benchmark_source: 'similar_transaction_analysis',
      typical_range: null,
      requires_justification: true
    },
    {
      field: 'geographic_risk_adjustment',
      label: 'Geographic Risk Adjustment (%)',
      description: 'Premium/discount for geographic exposure',
      ai_benchmark_source: 'country_risk_premiums',
      typical_range: [-5, 20],
      requires_justification: false
    },
    {
      field: 'management_quality_assessment',
      label: 'Management Quality Score',
      description: 'Qualitative assessment (1-10 scale)',
      ai_benchmark_source: 'executive_track_record_analysis',
      typical_range: [3, 10],
      requires_justification: true
    }
  ]
};

// Cache for manual inputs
const manualInputCache = new Map();

/**
 * Get trending peers based on recent analyst coverage, news sentiment, and sector momentum
 */
async function getTrendingPeers(ticker, sector, limit = 10) {
  const prompt = `Analyze current market trends and identify trending peer companies for ${ticker} in the ${sector || 'Technology'} sector. Consider: 1. Recent analyst upgrades/downgrades 2. News sentiment (last 30 days) 3. Sector rotation trends 4. Similar business models 5. Market cap comparability (0.5x to 2.0x) 6. Growth profile alignment. Return JSON: {"trending_peers": [{"ticker": "string", "company_name": "string", "market_cap": number, "similarity_score": number, "trend_reason": "string", "sentiment_score": number, "analyst_coverage_change": "string", "relevance_score": number}], "analysis_date": "ISO date", "sector_momentum": "string", "total_candidates_analyzed": number}`;

  try {
    const aiResponse = await callAIService(prompt, 'trending_peers_analysis');
    
    if (aiResponse && aiResponse.trending_peers) {
      return { success: true, data: aiResponse, source: 'ai_analysis', timestamp: new Date().toISOString() };
    }
  } catch (error) {
    console.log(`[TRENDING PEERS] AI failed for ${ticker}, using fallback:`, error.message);
  }

  // Fallback: Static trending peers based on sector
  const fallbackTrendingPeers = {
    Technology: ['MSFT', 'GOOGL', 'NVDA', 'META', 'AAPL', 'AMZN', 'CRM', 'ORCL', 'ADBE', 'INTC'],
    Healthcare: ['JNJ', 'UNH', 'PFE', 'MRK', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY'],
    Financials: ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V'],
    Consumer: ['AMZN', 'WMT', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'SBUX', 'HD'],
    Energy: ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL'],
    Industrials: ['CAT', 'BA', 'HON', 'UPS', 'RTX', 'LMT', 'GE', 'MMM', 'DE', 'UNP']
  };

  const sectorPeers = fallbackTrendingPeers[sector] || fallbackTrendingPeers.Technology;
  const selectedPeers = sectorPeers.slice(0, limit).map(t => ({
    ticker: t,
    company_name: t,
    market_cap: Math.floor(Math.random() * 500 + 50) * 1e9,
    similarity_score: parseFloat((Math.random() * 0.4 + 0.6).toFixed(2)),
    trend_reason: 'Sector leader with strong momentum',
    sentiment_score: parseFloat((Math.random() * 0.6 + 0.2).toFixed(2)),
    analyst_coverage_change: 'unchanged',
    relevance_score: Math.floor(Math.random() * 30 + 70)
  }));

  return {
    success: true,
    data: { trending_peers: selectedPeers, analysis_date: new Date().toISOString(), sector_momentum: 'neutral', total_candidates_analyzed: 50 },
    source: 'fallback_static',
    timestamp: new Date().toISOString()
  };
}

/**
 * Get AI-powered benchmark ranges for manual inputs
 */
async function getManualInputBenchmarks(ticker, model, userInputField) {
  const modelLower = model === 'DUPONT' ? 'dupont' : model.toLowerCase();
  const category = manualInputCategories[modelLower] || [];
  const fieldConfig = category.find(f => f.field === userInputField) || 
                      [...manualInputCategories.common, ...category].find(f => f.field === userInputField);

  if (!fieldConfig) {
    return { success: false, error: 'Field not found in manual input categories' };
  }

  const prompt = `Provide benchmark data for manual valuation input: Company=${ticker}, Model=${model}, Field=${fieldConfig.label}, Description=${fieldConfig.description}, Typical Range=${fieldConfig.typical_range ? fieldConfig.typical_range.join('-') : 'N/A'}%. Return JSON: {"field": "${userInputField}", "benchmark_percentiles": {"p5": number, "p25": number, "median": number, "p75": number, "p95": number}, "peer_average": number, "peer_median": number, "historical_trend_3y": [number, number, number], "recommended_value": number, "recommendation_confidence": number, "justification": "string", "red_flag_thresholds": {"low_warning": number, "high_warning": number}, "sector_context": "string"}`;

  try {
    const aiResponse = await callAIService(prompt, 'manual_input_benchmark');
    
    if (aiResponse && aiResponse.benchmark_percentiles) {
      return {
        success: true,
        data: { ...aiResponse, field_config: fieldConfig, requires_justification: fieldConfig.requires_justification },
        source: 'ai_analysis',
        timestamp: new Date().toISOString()
      };
    }
  } catch (error) {
    console.log(`[BENCHMARK] AI failed for ${userInputField}, using fallback:`, error.message);
  }

  // Fallback: Generate reasonable benchmark based on typical ranges
  const [minRange, maxRange] = fieldConfig.typical_range || [0, 10];
  const median = (minRange + maxRange) / 2;
  
  return {
    success: true,
    data: {
      field: userInputField,
      benchmark_percentiles: { p5: minRange * 0.5, p25: minRange + (maxRange - minRange) * 0.25, median, p75: minRange + (maxRange - minRange) * 0.75, p95: maxRange * 1.2 },
      peer_average: median,
      peer_median: median,
      historical_trend_3y: [median - 0.5, median, median + 0.3],
      recommended_value: median,
      recommendation_confidence: 0.65,
      justification: `Based on typical ${fieldConfig.label.toLowerCase()} ranges. AI analysis unavailable - recommend manual verification.`,
      red_flag_thresholds: { low_warning: minRange * 0.7, high_warning: maxRange * 1.3 },
      sector_context: 'General industry benchmark (AI analysis pending)',
      field_config: fieldConfig,
      requires_justification: fieldConfig.requires_justification
    },
    source: 'fallback_heuristic',
    timestamp: new Date().toISOString()
  };
}

/**
 * Validate manual input against benchmarks and flag issues
 */
function validateManualInput(field, userInput, benchmark) {
  const issues = [];
  const warnings = [];

  if (!benchmark || !benchmark.benchmark_percentiles) {
    return { valid: true, issues, warnings };
  }

  const { p5, p25, median, p75, p95 } = benchmark.benchmark_percentiles;
  const { low_warning, high_warning } = benchmark.red_flag_thresholds || {};

  if (low_warning && userInput < low_warning) {
    issues.push(`Value (${userInput}) is below warning threshold (${low_warning})`);
  } else if (p5 && userInput < p5) {
    warnings.push(`Value (${userInput}) is below 5th percentile (${p5}) - verify justification`);
  }

  if (high_warning && userInput > high_warning) {
    issues.push(`Value (${userInput}) exceeds warning threshold (${high_warning})`);
  } else if (p95 && userInput > p95) {
    warnings.push(`Value (${userInput}) exceeds 95th percentile (${p95}) - verify justification`);
  }

  if (benchmark.recommended_value && Math.abs(userInput - benchmark.recommended_value) > Math.abs(median - userInput) * 2) {
    warnings.push(`Value deviates significantly from recommended (${benchmark.recommended_value})`);
  }

  return {
    valid: issues.length === 0,
    issues,
    warnings,
    deviation_from_median: userInput - median,
    percentile_rank: calculatePercentileRank(userInput, p5, p25, median, p75, p95)
  };
}

function calculatePercentileRank(value, p5, p25, median, p75, p95) {
  if (value <= p5) return 5;
  if (value <= p25) return 15;
  if (value <= median) return 35;
  if (value <= p75) return 65;
  if (value <= p95) return 85;
  return 95;
}

// ============================================================================
// EXPRESS ROUTES FOR MANUAL INPUTS WITH AI ASSISTANCE
// ============================================================================

/**
 * GET /api/manual-inputs/:ticker?model=DCF|COMPS|DUPONT
 * Get all manual inputs required for a model with AI benchmarks
 */
app.get('/api/manual-inputs/:ticker', async (req, res) => {
  const { ticker } = req.params;
  const { model } = req.query;

  if (!model || !['DCF', 'COMPS', 'DUPONT'].includes(model.toUpperCase())) {
    return res.status(400).json({ success: false, error: 'Invalid model. Must be DCF, COMPS, or DUPONT' });
  }

  try {
    const modelLower = model.toLowerCase();
    const categoryInputs = manualInputCategories[modelLower] || [];
    const commonInputs = manualInputCategories.common;
    const allInputs = [...categoryInputs, ...commonInputs];

    const benchmarks = await Promise.all(
      allInputs.map(async (input) => {
        const benchmark = await getManualInputBenchmarks(ticker, model, input.field);
        return { ...input, benchmark: benchmark.success ? benchmark.data : null, benchmark_source: benchmark.source };
      })
    );

    const trendingPeers = await getTrendingPeers(ticker, 'Technology');

    res.json({
      success: true,
      data: {
        ticker,
        model,
        manual_inputs: benchmarks,
        trending_peers: trendingPeers.data,
        total_manual_inputs: allInputs.length,
        inputs_requiring_justification: benchmarks.filter(i => i.requires_justification).length
      },
      metadata: { timestamp: new Date().toISOString(), cache_duration: 3600 }
    });
  } catch (error) {
    console.error('[MANUAL INPUTS] Error:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch manual inputs with benchmarks', details: error.message });
  }
});

/**
 * GET /api/manual-input-benchmark/:ticker/:model/:field
 * Get benchmark for a specific manual input field
 */
app.get('/api/manual-input-benchmark/:ticker/:model/:field', async (req, res) => {
  const { ticker, model, field } = req.params;

  try {
    const benchmark = await getManualInputBenchmarks(ticker, model, field);

    if (!benchmark.success) {
      return res.status(404).json(benchmark);
    }

    res.json({ success: true, data: benchmark.data, source: benchmark.source, timestamp: benchmark.timestamp });
  } catch (error) {
    console.error('[BENCHMARK] Error:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch benchmark', details: error.message });
  }
});

/**
 * POST /api/validate-manual-input
 * Validate a manual input value against benchmarks
 */
app.post('/api/validate-manual-input', async (req, res) => {
  const { ticker, model, field, value, justification } = req.body;

  if (!ticker || !model || !field || value === undefined) {
    return res.status(400).json({ success: false, error: 'Missing required fields: ticker, model, field, value' });
  }

  try {
    const benchmark = await getManualInputBenchmarks(ticker, model, field);
    
    if (!benchmark.success) {
      return res.status(404).json(benchmark);
    }

    const validation = validateManualInput(field, value, benchmark.data);

    res.json({
      success: true,
      data: {
        field,
        user_value: value,
        benchmark: benchmark.data,
        validation,
        justification_required: benchmark.data.requires_justification,
        justification_provided: !!justification,
        overall_status: validation.valid && (!benchmark.data.requires_justification || justification) ? 'approved' : 'review_needed'
      },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('[VALIDATE INPUT] Error:', error);
    res.status(500).json({ success: false, error: 'Failed to validate input', details: error.message });
  }
});

/**
 * GET /api/trending-peers/:ticker?sector=Technology&limit=10
 * Get trending peer companies for comparison
 */
app.get('/api/trending-peers/:ticker', async (req, res) => {
  const { ticker } = req.params;
  const { sector, limit } = req.query;

  try {
    const trendingPeers = await getTrendingPeers(ticker, sector, parseInt(limit) || 10);

    res.json({ success: true, data: trendingPeers.data, source: trendingPeers.source, timestamp: trendingPeers.timestamp });
  } catch (error) {
    console.error('[TRENDING PEERS] Error:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch trending peers', details: error.message });
  }
});

/**
 * POST /api/save-manual-inputs
 * Save user's manual input selections with audit trail
 */
app.post('/api/save-manual-inputs', (req, res) => {
  const { ticker, model, inputs, user_id } = req.body;

  if (!ticker || !model || !inputs) {
    return res.status(400).json({ success: false, error: 'Missing required fields: ticker, model, inputs' });
  }

  const auditEntry = {
    ticker,
    model,
    inputs: inputs.map(input => ({
      field: input.field,
      value: input.value,
      benchmark_value: input.benchmark_value,
      deviation: input.value - (input.benchmark_value || 0),
      justification: input.justification || null,
      validation_status: input.validation_status,
      timestamp: new Date().toISOString()
    })),
    user_id: user_id || 'anonymous',
    saved_at: new Date().toISOString(),
    session_id: req.sessionID || crypto.randomUUID()
  };

  manualInputCache.set(`${ticker}_${model}_${Date.now()}`, auditEntry);

  console.log(`[SAVE MANUAL INPUTS] Saved ${inputs.length} inputs for ${ticker} (${model})`);

  res.json({
    success: true,
    message: 'Manual inputs saved successfully',
    data: { audit_id: crypto.randomUUID(), saved_count: inputs.length, timestamp: auditEntry.saved_at }
  });
});

console.log('✅ Section 9 loaded: Manual inputs with AI benchmark assistance');

// ============================================================================
// SECTION 10: FORECAST BENCHMARKS WITH 5Y HISTORY + PEER COMPARISON
// ============================================================================

/**
 * Helper: Calculate median of an array
 */
function calculateMedian(arr) {
  if (!arr.length) return 0;
  const sorted = arr.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Helper: Calculate percentile
 */
function calculatePercentile(arr, p) {
  if (!arr.length) return 0;
  const sorted = arr.slice().sort((a, b) => a - b);
  const idx = Math.ceil(p * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

/**
 * Helper: Mock 5-year historical data generator (Replace with real API calls)
 */
function generateMockHistoricalData(ticker, years) {
  const data = [];
  const baseRevenue = 100000 + (Math.random() * 50000);
  const baseMargin = 0.20 + (Math.random() * 0.10);
  
  for (let i = 0; i < years; i++) {
    const year = new Date().getFullYear() - (years - i);
    const growth = 0.05 + (Math.random() * 0.10); // 5-15% growth
    const revenue = baseRevenue * Math.pow(1 + growth, i);
    const margin = baseMargin + (Math.random() * 0.04 - 0.02); // Fluctuate slightly
    
    data.push({
      year,
      revenue: parseFloat(revenue.toFixed(2)),
      revenue_growth: parseFloat((growth * 100).toFixed(2)),
      ebitda_margin: parseFloat((margin * 100).toFixed(2)),
      operating_margin: parseFloat(((margin - 0.05) * 100).toFixed(2)),
      capex_as_percent_revenue: parseFloat(((0.05 + Math.random() * 0.05) * 100).toFixed(2)),
      working_capital_days: Math.floor(30 + Math.random() * 60)
    });
  }
  return data;
}

/**
 * Generates forecast suggestions based on 5-year historical trends and peer benchmarks.
 * Returns 6 values: [Year+1, Year+2, Year+3, Year+4, Year+5, Terminal]
 */
async function generateForecastSuggestions(ticker, metric, historicalData, peerData) {
  try {
    // 1. Analyze Target History (Last 5 Years)
    const history = historicalData.slice(-5); // Ensure last 5 years
    if (history.length < 3) {
      return { error: "Insufficient historical data (need min 3 years)" };
    }

    const values = history.map(h => h[metric] || 0);
    if (values.length < 3) return { error: `Insufficient data for ${metric}` };

    // Calculate Historical CAGR or Average
    let historicalGrowthRate = 0;
    let historicalAverage = 0;
    
    if (metric.includes('revenue') || metric.includes('income') || metric.includes('growth')) {
      // CAGR for growth metrics
      const start = values[0];
      const end = values[values.length - 1];
      historicalGrowthRate = start > 0 ? Math.pow(end / start, 1 / (values.length - 1)) - 1 : 0;
    } else {
      // Average for margins/ratios
      historicalAverage = values.reduce((a, b) => a + b, 0) / values.length;
    }

    // 2. Analyze Peer Benchmarks
    const peerValues = peerData.map(p => p[metric] || 0);
    const peerMedian = peerValues.length > 0 ? calculateMedian(peerValues) : historicalAverage;
    const peer25th = peerValues.length > 0 ? calculatePercentile(peerValues, 0.25) : historicalAverage * 0.8;
    const peer75th = peerValues.length > 0 ? calculatePercentile(peerValues, 0.75) : historicalAverage * 1.2;

    // 3. Generate 6-Year Forecast Array [FY+1 ... FY+5, Terminal]
    const forecast = [];
    const terminalValue = {};

    if (metric.includes('revenue') || metric.includes('growth')) {
      // Growth Rate Logic: Converge from historical trend to peer median over 5 years
      const startRate = Math.max(-0.20, Math.min(0.50, historicalGrowthRate)); // Cap extremes
      const endRate = Math.max(0.01, Math.min(0.15, peerMedian > 1 ? peerMedian / 100 : peerMedian)); // Terminal cap
      
      const step = (endRate - startRate) / 5;
      
      for (let i = 1; i <= 5; i++) {
        let rate = startRate + (step * i);
        forecast.push(parseFloat((rate * 100).toFixed(2))); // Return as %
      }
      
      // Terminal Year (Year 6) -> Converge to Risk Free Rate or GDP (e.g., 2-3%)
      const terminalRate = Math.min(forecast[4] / 100, 0.03); 
      forecast.push(parseFloat((terminalRate * 100).toFixed(2)));
      
      terminalValue.type = "Converging Growth";
      terminalValue.rationale = `Converges from hist. ${(startRate*100).toFixed(1)}% to peer ${(peerMedian).toFixed(1)}%, terminal capped at ${terminalRate*100}%`;

    } else if (metric.includes('margin') || metric.includes('return')) {
      // Margin Logic: Mean reversion towards peer median
      const current = values[values.length - 1] / 100; // Convert from % to decimal
      const targetPeer = peerMedian > 1 ? peerMedian / 100 : peerMedian;
      const target = (current * 0.4) + (targetPeer * 0.6); // Weighted towards peer
      const step = (target - current) / 5;

      for (let i = 1; i <= 5; i++) {
        let val = current + (step * i);
        // Clamp within reasonable bounds (0-50% for margins)
        val = Math.max(0, Math.min(0.50, val));
        forecast.push(parseFloat((val * 100).toFixed(2))); // Return as %
      }

      // Terminal = Peer Median
      forecast.push(parseFloat((targetPeer * 100).toFixed(2)));

      terminalValue.type = "Mean Reversion";
      terminalValue.rationale = `Reverts from current ${(current*100).toFixed(1)}% to peer median ${(targetPeer*100).toFixed(1)}%`;

    } else if (metric === 'working_capital_days') {
      // Days metrics: Average of historical and peer
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      const peerAvg = peerMedian;
      const suggestion = (avg + peerAvg) / 2;
      
      for (let i = 0; i < 6; i++) {
        forecast.push(parseFloat(suggestion.toFixed(2)));
      }
      terminalValue.type = "Steady State";
      terminalValue.rationale = `Average of historical (${(avg*100).toFixed(1)}%) and peer (${(peerAvg*100).toFixed(1)}%)`;
    } else {
      // Default: flat forecast based on last year
      const lastVal = values[values.length - 1];
      for (let i = 0; i < 6; i++) {
        forecast.push(parseFloat(lastVal.toFixed(2)));
      }
      terminalValue.type = "Flat Projection";
      terminalValue.rationale = `Based on last year value of ${lastVal}`;
    }

    return {
      metric,
      suggestion: forecast,
      historical_context: {
        cagr: parseFloat((historicalGrowthRate * 100).toFixed(2)),
        average: parseFloat((historicalAverage).toFixed(2)),
        last_year: values[values.length - 1]
      },
      peer_context: {
        median: parseFloat(peerMedian.toFixed(2)),
        p25: parseFloat(peer25th.toFixed(2)),
        p75: parseFloat(peer75th.toFixed(2))
      },
      terminal_assumption: terminalValue,
      confidence: "High"
    };

  } catch (error) {
    console.error(`Error generating forecast for ${ticker}.${metric}:`, error);
    return { error: error.message };
  }
}

/**
 * Endpoint: Get comprehensive forecast benchmarks for all DCF drivers
 * Compares ticker's 5-year history vs 5+ peers to generate 6-year forecast suggestions
 */
app.get('/api/forecast-benchmarks/:ticker', async (req, res) => {
  const { ticker } = req.params;
  const { peers } = req.query; // Comma-separated list of peer tickers
  
  try {
    // 1. Get Target Historical Data (5 Years)
    const mockHistory = generateMockHistoricalData(ticker, 5); 
    
    // 2. Get Peer Data (minimum 5 peers)
    const peerTickers = peers ? peers.split(',') : ['MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'];
    const peerData = peerTickers.map(t => generateMockHistoricalData(t, 1)[0]); // Current year snapshot

    // 3. Generate Suggestions for Key DCF Drivers
    const drivers = [
      'revenue_growth', 
      'ebitda_margin', 
      'operating_margin', 
      'capex_as_percent_revenue',
      'working_capital_days'
    ];

    const benchmarks = {};
    
    for (const driver of drivers) {
      const result = await generateForecastSuggestions(ticker, driver, mockHistory, peerData);
      benchmarks[driver] = result;
    }

    res.json({
      ticker,
      valuation_date: new Date().toISOString(),
      historical_years: 5,
      peer_count: peerData.length,
      peer_tickers: peerTickers,
      forecast_horizon: "5 Years + Terminal (6 values total)",
      benchmarks,
      generated_at: new Date().toISOString()
    });

  } catch (error) {
    console.error("Forecast Benchmark Error:", error);
    res.status(500).json({ error: "Failed to generate forecast benchmarks", details: error.message });
  }
});

/**
 * Endpoint: Get single forecast suggestion for a specific driver
 */
app.get('/api/forecast-suggestion/:ticker/:driver', async (req, res) => {
  const { ticker, driver } = req.params;
  const { peers } = req.query;
  
  try {
    const mockHistory = generateMockHistoricalData(ticker, 5);
    const peerTickers = peers ? peers.split(',') : ['MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'];
    const peerData = peerTickers.map(t => generateMockHistoricalData(t, 1)[0]);
    
    const result = await generateForecastSuggestions(ticker, driver, mockHistory, peerData);
    
    res.json({
      ticker,
      driver,
      forecast_values: result.suggestion,
      forecast_labels: ["Year+1", "Year+2", "Year+3", "Year+4", "Year+5", "Terminal"],
      rationale: result.terminal_assumption,
      peer_comparison: result.peer_context,
      historical_trend: result.historical_context
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

console.log('✅ Section 10 loaded: Forecast benchmarks with 5Y history + peer comparison');

// ============================================================================
// SECTION 11: DCF CALCULATION ENGINE API
// Modular DCF calculations with separated inputs for safety and reusability
// ============================================================================

const dcfEngine = require('./dcf-engine');

/**
 * Endpoint: Run complete DCF valuation
 * POST /api/dcf/calculate
 * Body: {
 *   ticker: string,
 *   base_period_data: { ... },
 *   forecast_drivers: { ... },
 *   assumptions: { ... }
 * }
 */
app.post('/api/dcf/calculate', async (req, res) => {
  const {
    ticker,
    base_period_data,
    forecast_drivers,
    assumptions = {}
  } = req.body;
  
  try {
    // Validate required inputs
    if (!base_period_data || !forecast_drivers) {
      return res.status(400).json({
        error: 'Missing required fields: base_period_data and forecast_drivers'
      });
    }
    
    // Ensure forecast drivers have exactly 6 values (5 years + terminal)
    const drivers = ['revenue_growth', 'inflation_rate', 'opex_growth', 'ar_days', 'inv_days', 'ap_days'];
    for (const driver of drivers) {
      if (!forecast_drivers[driver] || forecast_drivers[driver].length !== 6) {
        return res.status(400).json({
          error: `${driver} must have exactly 6 values (5 forecast years + terminal year)`,
          received: forecast_drivers[driver]?.length || 0
        });
      }
    }
    
    // Ensure capital_expenditure has exactly 5 values (forecast years only, no terminal)
    if (!forecast_drivers.capital_expenditure || forecast_drivers.capital_expenditure.length !== 5) {
      return res.status(400).json({
        error: 'capital_expenditure must have exactly 5 values (forecast years only)',
        received: forecast_drivers.capital_expenditure?.length || 0
      });
    }
    
    // Map input schema to engine schema
    const engineInputs = {
      // Base period data (FY-1 / 2022A)
      baseRevenue: base_period_data.revenue,
      baseCOGS: base_period_data.cogs,
      baseSGA: base_period_data.sga,
      baseOther: base_period_data.other_opex || 0,
      baseExistingPPE: base_period_data.ppe_gross || 0,
      baseNOL: base_period_data.nol_remaining || 0,
      baseNetDebt: base_period_data.net_debt || 0,
      baseCurrentStockPrice: base_period_data.current_stock_price,
      baseSharesOutstanding: base_period_data.shares_outstanding,
      
      // Forecast drivers (6 values each)
      revenueGrowthRates: forecast_drivers.revenue_growth.map(g => g / 100), // Convert % to decimal
      inflationRates: forecast_drivers.inflation_rate.map(g => g / 100),
      opexGrowthRates: forecast_drivers.opex_growth.map(g => g / 100),
      capitalExpenditures: forecast_drivers.capital_expenditure,
      arDays: forecast_drivers.ar_days,
      invDays: forecast_drivers.inv_days,
      apDays: forecast_drivers.ap_days,
      
      // Assumptions
      usefulLifeExisting: assumptions.useful_life_existing || 10,
      usefulLifeNew: assumptions.useful_life_new || 5,
      taxRate: assumptions.tax_rate || 0.21,
      nolUtilizationLimit: assumptions.nol_utilization_limit || 0.80,
      wacc: assumptions.wacc || 0.097,
      terminalGrowthRate: assumptions.terminal_growth_rate || 0.02,
      terminalMultiple: assumptions.terminal_multiple || 7.0,
      
      // Metadata
      valuationDate: assumptions.valuation_date || new Date().toISOString().split('T')[0],
      scenario: assumptions.scenario || 'base_case'
    };
    
    // Run DCF calculation
    const result = dcfEngine.runCompleteDCF(engineInputs);
    
    // Add ticker and additional metadata
    result.metadata.ticker = ticker || 'UNKNOWN';
    result.calculation_id = crypto.randomUUID();
    
    res.json({
      success: true,
      data: result,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('[DCF CALCULATION ERROR]:', error);
    res.status(500).json({
      error: 'DCF calculation failed',
      details: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
});

/**
 * Endpoint: Run DCF with multiple scenarios
 * POST /api/dcf/calculate-scenarios
 */
app.post('/api/dcf/calculate-scenarios', async (req, res) => {
  const {
    ticker,
    base_period_data,
    forecast_drivers,
    assumptions = {}
  } = req.body;
  
  try {
    // Reuse validation from single calculation
    const singleReq = { body: { ticker, base_period_data, forecast_drivers, assumptions } };
    const mockRes = {
      status: (code) => ({
        json: (data) => { throw new Error(data.error || 'Validation failed'); }
      }),
      json: () => {}
    };
    
    // Map inputs
    const engineInputs = {
      baseRevenue: base_period_data.revenue,
      baseCOGS: base_period_data.cogs,
      baseSGA: base_period_data.sga,
      baseOther: base_period_data.other_opex || 0,
      baseExistingPPE: base_period_data.ppe_gross || 0,
      baseNOL: base_period_data.nol_remaining || 0,
      baseNetDebt: base_period_data.net_debt || 0,
      baseCurrentStockPrice: base_period_data.current_stock_price,
      baseSharesOutstanding: base_period_data.shares_outstanding,
      revenueGrowthRates: forecast_drivers.revenue_growth.map(g => g / 100),
      inflationRates: forecast_drivers.inflation_rate.map(g => g / 100),
      opexGrowthRates: forecast_drivers.opex_growth.map(g => g / 100),
      capitalExpenditures: forecast_drivers.capital_expenditure,
      arDays: forecast_drivers.ar_days,
      invDays: forecast_drivers.inv_days,
      apDays: forecast_drivers.ap_days,
      usefulLifeExisting: assumptions.useful_life_existing || 10,
      usefulLifeNew: assumptions.useful_life_new || 5,
      taxRate: assumptions.tax_rate || 0.21,
      nolUtilizationLimit: assumptions.nol_utilization_limit || 0.80,
      wacc: assumptions.wacc || 0.097,
      terminalGrowthRate: assumptions.terminal_growth_rate || 0.02,
      terminalMultiple: assumptions.terminal_multiple || 7.0
    };
    
    // Run scenarios
    const scenarios = assumptions.scenarios || ['best_case', 'base_case', 'worst_case'];
    const results = dcfEngine.runDCFWithScenarios(engineInputs, scenarios);
    
    res.json({
      success: true,
      data: {
        ticker: ticker || 'UNKNOWN',
        scenarios: results,
        comparison: {
          enterprise_values: {
            best_case: results.best_case?.main_outputs?.enterprise_value_perpetuity || null,
            base_case: results.base_case?.main_outputs?.enterprise_value_perpetuity || null,
            worst_case: results.worst_case?.main_outputs?.enterprise_value_perpetuity || null
          },
          equity_per_share: {
            best_case: results.best_case?.main_outputs?.equity_value_per_share_perpetuity || null,
            base_case: results.base_case?.main_outputs?.equity_value_per_share_perpetuity || null,
            worst_case: results.worst_case?.main_outputs?.equity_value_per_share_perpetuity || null
          }
        }
      },
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('[DCF SCENARIOS ERROR]:', error);
    res.status(500).json({
      error: 'Scenario calculation failed',
      details: error.message
    });
  }
});

/**
 * Endpoint: Generate sensitivity tables
 * POST /api/dcf/sensitivity
 */
app.post('/api/dcf/sensitivity', async (req, res) => {
  const {
    ticker,
    base_period_data,
    forecast_drivers,
    assumptions = {}
  } = req.body;
  
  try {
    // Map inputs
    const engineInputs = {
      baseRevenue: base_period_data.revenue,
      baseCOGS: base_period_data.cogs,
      baseSGA: base_period_data.sga,
      baseOther: base_period_data.other_opex || 0,
      baseExistingPPE: base_period_data.ppe_gross || 0,
      baseNOL: base_period_data.nol_remaining || 0,
      baseNetDebt: base_period_data.net_debt || 0,
      baseCurrentStockPrice: base_period_data.current_stock_price,
      baseSharesOutstanding: base_period_data.shares_outstanding,
      revenueGrowthRates: forecast_drivers.revenue_growth.map(g => g / 100),
      inflationRates: forecast_drivers.inflation_rate.map(g => g / 100),
      opexGrowthRates: forecast_drivers.opex_growth.map(g => g / 100),
      capitalExpenditures: forecast_drivers.capital_expenditure,
      arDays: forecast_drivers.ar_days,
      invDays: forecast_drivers.inv_days,
      apDays: forecast_drivers.ap_days,
      usefulLifeExisting: assumptions.useful_life_existing || 10,
      usefulLifeNew: assumptions.useful_life_new || 5,
      taxRate: assumptions.tax_rate || 0.21,
      nolUtilizationLimit: assumptions.nol_utilization_limit || 0.80,
      wacc: assumptions.wacc || 0.097,
      terminalGrowthRate: assumptions.terminal_growth_rate || 0.02,
      terminalMultiple: assumptions.terminal_multiple || 7.0
    };
    
    // Generate sensitivity tables
    const sensitivityTables = dcfEngine.calculateSensitivityTables(engineInputs);
    
    res.json({
      success: true,
      data: {
        ticker: ticker || 'UNKNOWN',
        base_wacc: assumptions.wacc || 0.097,
        base_terminal_growth: assumptions.terminal_growth_rate || 0.02,
        base_terminal_multiple: assumptions.terminal_multiple || 7.0,
        perpetuity_method: sensitivityTables.perpetuityMethod,
        multiple_method: sensitivityTables.multipleMethod
      },
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('[DCF SENSITIVITY ERROR]:', error);
    res.status(500).json({
      error: 'Sensitivity analysis failed',
      details: error.message
    });
  }
});

/**
 * Endpoint: Validate DCF inputs
 * POST /api/dcf/validate
 */
app.post('/api/dcf/validate', async (req, res) => {
  const { base_period_data, forecast_drivers, assumptions = {} } = req.body;
  
  const validations = {
    critical: [],
    warnings: []
  };
  
  try {
    // Check forecast driver lengths
    const drivers = ['revenue_growth', 'inflation_rate', 'opex_growth', 'ar_days', 'inv_days', 'ap_days'];
    for (const driver of drivers) {
      if (!forecast_drivers[driver]) {
        validations.critical.push({
          field: driver,
          rule: 'required',
          message: `${driver} is required`
        });
      } else if (forecast_drivers[driver].length !== 6) {
        validations.critical.push({
          field: driver,
          rule: 'length',
          message: `${driver} must have exactly 6 values (5 years + terminal), got ${forecast_drivers[driver].length}`
        });
      }
    }
    
    // Check capital expenditure length
    if (!forecast_drivers.capital_expenditure) {
      validations.critical.push({
        field: 'capital_expenditure',
        rule: 'required',
        message: 'capital_expenditure is required'
      });
    } else if (forecast_drivers.capital_expenditure.length !== 5) {
      validations.critical.push({
        field: 'capital_expenditure',
        rule: 'length',
        message: `capital_expenditure must have exactly 5 values, got ${forecast_drivers.capital_expenditure.length}`
      });
    }
    
    // Check WACC and terminal growth relationship
    const wacc = assumptions.wacc || 0.097;
    const terminalGrowth = assumptions.terminal_growth_rate || 0.02;
    if (terminalGrowth >= wacc) {
      validations.critical.push({
        field: 'terminal_growth_rate',
        rule: 'terminal_growth_less_than_wacc',
        message: `Terminal growth rate (${terminalGrowth}) must be less than WACC (${wacc})`
      });
    }
    
    // Check base period data
    if (!base_period_data) {
      validations.critical.push({
        field: 'base_period_data',
        rule: 'required',
        message: 'base_period_data is required'
      });
    } else {
      if (base_period_data.shares_outstanding <= 0) {
        validations.critical.push({
          field: 'shares_outstanding',
          rule: 'positive',
          message: 'shares_outstanding must be positive'
        });
      }
      if (base_period_data.revenue <= 0) {
        validations.warnings.push({
          field: 'revenue',
          rule: 'positive',
          message: 'Revenue is not positive'
        });
      }
    }
    
    // Check terminal multiple range
    const terminalMultiple = assumptions.terminal_multiple || 7.0;
    if (terminalMultiple < 5.0 || terminalMultiple > 15.0) {
      validations.warnings.push({
        field: 'terminal_multiple',
        rule: 'reasonable_range',
        message: `Terminal multiple (${terminalMultiple}) is outside typical range [5.0, 15.0]`
      });
    }
    
    const isValid = validations.critical.length === 0;
    
    res.json({
      success: true,
      valid: isValid,
      validations,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('[DCF VALIDATION ERROR]:', error);
    res.status(500).json({
      error: 'Validation failed',
      details: error.message
    });
  }
});

console.log('✅ Section 11 loaded: DCF Calculation Engine API with modular design');

app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});
