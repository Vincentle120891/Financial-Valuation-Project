/**
 * DuPont Analysis Engine
 * Comprehensive 3-step and 5-step DuPont decomposition with growth trends
 * Supports 6-10 years of historical and forecast data
 */

/**
 * Validate input data length (6-10 years)
 */
function validateInputLength(dataArray, fieldName) {
  if (!Array.isArray(dataArray)) {
    throw new Error(`${fieldName} must be an array`);
  }
  if (dataArray.length < 6 || dataArray.length > 10) {
    throw new Error(`${fieldName} must have 6-10 values, got ${dataArray.length}`);
  }
  return true;
}

/**
 * Module 1: Calculate Supporting Financial Ratios
 * @param {Object} financialData - Input financial data arrays (6-10 years)
 * @returns {Object} Supporting ratios for DuPont analysis
 */
function calculateSupportingRatios(financialData) {
  const {
    revenue,
    gross_profit,
    ebitda,
    operating_income,
    net_income,
    total_assets,
    accounts_receivable,
    inventory,
    accounts_payable,
    cogs,
    total_debt,
    total_equity,
    current_assets,
    current_liabilities,
    interest_expense
  } = financialData;

  // Validate all required arrays
  const requiredFields = [
    'revenue', 'gross_profit', 'ebitda', 'operating_income', 'net_income',
    'total_assets', 'accounts_receivable', 'inventory', 'accounts_payable',
    'cogs', 'total_debt', 'total_equity', 'current_assets', 'current_liabilities',
    'interest_expense'
  ];

  requiredFields.forEach(field => {
    if (!financialData[field]) {
      throw new Error(`Missing required field: ${field}`);
    }
    validateInputLength(financialData[field], field);
  });

  const years = revenue.length;
  const ratios = {
    gross_margin: [],
    ebitda_margin: [],
    operating_margin: [],
    net_profit_margin: [],
    asset_turnover: [],
    ar_days: [],
    inv_days: [],
    ap_days: [],
    cash_conversion_cycle: [],
    debt_to_equity: [],
    current_ratio: [],
    interest_coverage: [],
    roe: [],
    roa: [],
    roic: []
  };

  for (let i = 0; i < years; i++) {
    // Profitability Margins
    ratios.gross_margin.push(gross_profit[i] / revenue[i]);
    ratios.ebitda_margin.push(ebitda[i] / revenue[i]);
    ratios.operating_margin.push(operating_income[i] / revenue[i]);
    ratios.net_profit_margin.push(net_income[i] / revenue[i]);

    // Efficiency Ratios
    ratios.asset_turnover.push(revenue[i] / total_assets[i]);

    // Working Capital Days (assuming 365 days)
    const arDays = (accounts_receivable[i] / revenue[i]) * 365;
    const invDays = (inventory[i] / cogs[i]) * 365;
    const apDays = (accounts_payable[i] / cogs[i]) * 365;
    
    ratios.ar_days.push(arDays);
    ratios.inv_days.push(invDays);
    ratios.ap_days.push(apDays);
    ratios.cash_conversion_cycle.push(arDays + invDays - apDays);

    // Leverage Ratios
    ratios.debt_to_equity.push(total_debt[i] / total_equity[i]);
    ratios.current_ratio.push(current_assets[i] / current_liabilities[i]);
    ratios.interest_coverage.push(operating_income[i] / interest_expense[i]);

    // Return Ratios
    ratios.roe.push(net_income[i] / total_equity[i]);
    ratios.roa.push(net_income[i] / total_assets[i]);
    
    // ROIC (simplified: NOPAT / Invested Capital)
    const taxRate = i > 0 ? (net_income[i-1] / (operating_income[i-1])) : 0.25;
    const nopat = operating_income[i] * (1 - taxRate);
    const investedCapital = total_debt[i] + total_equity[i];
    ratios.roic.push(nopat / investedCapital);
  }

  return ratios;
}

/**
 * Module 2: Calculate 3-Step DuPont Analysis
 * ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
 * @param {Object} financialData - Input financial data
 * @returns {Object} 3-step DuPont decomposition
 */
function calculateDuPont3Step(financialData) {
  const {
    net_income,
    revenue,
    total_assets,
    total_equity
  } = financialData;

  validateInputLength(net_income, 'net_income');
  validateInputLength(revenue, 'revenue');
  validateInputLength(total_assets, 'total_assets');
  validateInputLength(total_equity, 'total_equity');

  const years = net_income.length;
  const result = {
    net_profit_margin: [],
    asset_turnover: [],
    equity_multiplier: [],
    roe_reconciled: []
  };

  for (let i = 0; i < years; i++) {
    const netProfitMargin = net_income[i] / revenue[i];
    const assetTurnover = revenue[i] / total_assets[i];
    const equityMultiplier = total_assets[i] / total_equity[i];
    
    // ROE via DuPont formula
    const roeViaDupont = netProfitMargin * assetTurnover * equityMultiplier;
    
    // Direct ROE calculation for validation
    const directROE = net_income[i] / total_equity[i];

    result.net_profit_margin.push(netProfitMargin);
    result.asset_turnover.push(assetTurnover);
    result.equity_multiplier.push(equityMultiplier);
    result.roe_reconciled.push(roeViaDupont);
  }

  return result;
}

/**
 * Module 3: Calculate 5-Step DuPont Analysis
 * ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
 * @param {Object} financialData - Input financial data with EBT and EBIT
 * @returns {Object} 5-step DuPont decomposition
 */
function calculateDuPont5Step(financialData) {
  const {
    net_income,
    ebt,
    ebit,
    revenue,
    total_assets,
    total_equity,
    interest_expense
  } = financialData;

  validateInputLength(net_income, 'net_income');
  validateInputLength(ebt, 'ebt');
  validateInputLength(ebit, 'ebit');
  validateInputLength(revenue, 'revenue');
  validateInputLength(total_assets, 'total_assets');
  validateInputLength(total_equity, 'total_equity');
  validateInputLength(interest_expense, 'interest_expense');

  const years = net_income.length;
  const result = {
    tax_burden: [],
    interest_burden: [],
    ebit_margin: [],
    asset_turnover: [],
    equity_multiplier: [],
    roe_reconciled: []
  };

  for (let i = 0; i < years; i++) {
    // Tax Burden = Net Income / EBT
    const taxBurden = ebt[i] !== 0 ? net_income[i] / ebt[i] : 0;
    
    // Interest Burden = EBT / EBIT
    const interestBurden = ebit[i] !== 0 ? ebt[i] / ebit[i] : 0;
    
    // EBIT Margin = EBIT / Revenue
    const ebitMargin = ebit[i] / revenue[i];
    
    // Asset Turnover = Revenue / Total Assets
    const assetTurnover = revenue[i] / total_assets[i];
    
    // Equity Multiplier = Total Assets / Total Equity
    const equityMultiplier = total_assets[i] / total_equity[i];
    
    // ROE via 5-step DuPont formula
    const roeViaDupont = taxBurden * interestBurden * ebitMargin * assetTurnover * equityMultiplier;

    result.tax_burden.push(taxBurden);
    result.interest_burden.push(interestBurden);
    result.ebit_margin.push(ebitMargin);
    result.asset_turnover.push(assetTurnover);
    result.equity_multiplier.push(equityMultiplier);
    result.roe_reconciled.push(roeViaDupont);
  }

  return result;
}

/**
 * Module 4: Calculate Growth Trends and Leverage Metrics
 * @param {Object} financialData - Input financial data
 * @returns {Object} Growth rates and leverage metrics
 */
function calculateGrowthTrends(financialData) {
  const {
    revenue,
    ebitda,
    net_income,
    operating_income
  } = financialData;

  validateInputLength(revenue, 'revenue');
  validateInputLength(ebitda, 'ebitda');
  validateInputLength(net_income, 'net_income');

  const years = revenue.length;
  const result = {
    revenue_growth: [],
    ebitda_growth: [],
    net_income_growth: [],
    dol: [], // Degree of Operating Leverage
    dfl: [], // Degree of Financial Leverage
    dtl: []  // Degree of Total Leverage
  };

  for (let i = 0; i < years; i++) {
    // Year-over-year growth rates
    if (i === 0) {
      result.revenue_growth.push(null);
      result.ebitda_growth.push(null);
      result.net_income_growth.push(null);
      result.dol.push(null);
      result.dfl.push(null);
      result.dtl.push(null);
    } else {
      const revGrowth = (revenue[i] - revenue[i-1]) / revenue[i-1];
      const ebitdaGrowth = (ebitda[i] - ebitda[i-1]) / ebitda[i-1];
      const niGrowth = (net_income[i] - net_income[i-1]) / net_income[i-1];

      result.revenue_growth.push(revGrowth);
      result.ebitda_growth.push(ebitdaGrowth);
      result.net_income_growth.push(niGrowth);

      // DOL = % Change in EBIT / % Change in Revenue
      const ebitGrowth = i > 0 && operating_income[i-1] !== 0 
        ? (operating_income[i] - operating_income[i-1]) / operating_income[i-1] 
        : 0;
      const dol = revGrowth !== 0 ? ebitGrowth / revGrowth : null;

      // DFL = % Change in Net Income / % Change in EBIT
      const dfl = ebitGrowth !== 0 ? niGrowth / ebitGrowth : null;

      // DTL = DOL × DFL
      const dtl = (dol !== null && dfl !== null) ? dol * dfl : null;

      result.dol.push(dol);
      result.dfl.push(dfl);
      result.dtl.push(dtl);
    }
  }

  return result;
}

/**
 * Module 5: Validate DuPont Calculations
 * Compares calculated ROE vs direct ROE
 * @param {Object} dupont3Step - 3-step DuPont results
 * @param {Object} dupont5Step - 5-step DuPont results
 * @param {Object} financialData - Original financial data
 * @returns {Object} Validation flags
 */
function validateDuPontCalculations(dupont3Step, dupont5Step, financialData) {
  const { net_income, total_equity } = financialData;
  const years = net_income.length;
  
  const validation = {
    roe_3step_matches_direct: [],
    roe_5step_matches_direct: []
  };

  const tolerance = 0.0001; // 0.01% tolerance for floating point comparison

  for (let i = 0; i < years; i++) {
    const directROE = net_income[i] / total_equity[i];
    const roe3Step = dupont3Step.roe_reconciled[i];
    const roe5Step = dupont5Step.roe_reconciled[i];

    validation.roe_3step_matches_direct.push(Math.abs(directROE - roe3Step) < tolerance);
    validation.roe_5step_matches_direct.push(Math.abs(directROE - roe5Step) < tolerance);
  }

  return validation;
}

/**
 * Main DuPont Analysis Function
 * @param {Object} inputData - Complete financial data for 6-10 years
 * @returns {Object} Complete DuPont analysis output matching schema
 */
function performDuPontAnalysis(inputData) {
  try {
    // Calculate all components
    const supportingRatios = calculateSupportingRatios(inputData);
    const dupont3Step = calculateDuPont3Step(inputData);
    const dupont5Step = calculateDuPont5Step(inputData);
    const growthTrends = calculateGrowthTrends(inputData);
    const validation = validateDuPontCalculations(dupont3Step, dupont5Step, inputData);

    // Determine number of years analyzed
    const yearsAnalyzed = inputData.revenue.length;

    return {
      supporting_ratios: supportingRatios,
      dupont_3step: dupont3Step,
      dupont_5step: dupont5Step,
      growth_trends: growthTrends,
      validation: validation,
      metadata: {
        years_analyzed: yearsAnalyzed,
        currency: inputData.currency || 'USD',
        unit_scaling: inputData.unit_scaling || 'thousands'
      }
    };
  } catch (error) {
    throw new Error(`DuPont Analysis failed: ${error.message}`);
  }
}

// Export functions for use in server.js
module.exports = {
  performDuPontAnalysis,
  calculateSupportingRatios,
  calculateDuPont3Step,
  calculateDuPont5Step,
  calculateGrowthTrends,
  validateDuPontCalculations,
  validateInputLength
};

console.log('✅ DuPont Analysis Engine loaded: 5 modular calculation functions');
