/**
 * DCF Calculation Engine - Modular & Safe
 * Separates calculation logic from inputs to ensure model safety and reusability
 * Version: 1.0.0
 */

const crypto = require('crypto');

/**
 * Validation rules for critical calculations
 */
const VALIDATION_RULES = {
  terminalGrowthLessThanWACC: (terminalGrowth, wacc) => terminalGrowth < wacc,
  positiveRevenue: (revenue) => revenue > 0,
  positiveEBITDATerminal: (ebitda) => ebitda > 0,
  positiveSharesOutstanding: (shares) => shares > 0,
  terminalMultipleInRange: (multiple) => multiple >= 5.0 && multiple <= 15.0
};

/**
 * Helper: Round to specified decimal places
 */
function roundTo(num, decimals = 2) {
  const factor = Math.pow(10, decimals);
  return Math.round(num * factor) / factor;
}

/**
 * Helper: Calculate median of array
 */
function calculateMedian(arr) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Helper: Calculate percentile
 */
function calculatePercentile(arr, p) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.ceil(p * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

/**
 * Module 1: Revenue Schedule Calculator
 */
function calculateRevenueSchedule(baseRevenue, growthRates) {
  const revenue = [baseRevenue];
  const validationFlags = { allPositive: true };
  
  for (let i = 0; i < growthRates.length; i++) {
    const prevRevenue = revenue[revenue.length - 1];
    const newRevenue = prevRevenue * (1 + growthRates[i]);
    
    if (!VALIDATION_RULES.positiveRevenue(newRevenue)) {
      validationFlags.allPositive = false;
      console.warn(`[WARNING] Negative revenue detected in year ${i + 1}`);
    }
    
    revenue.push(newRevenue);
  }
  
  return { revenue, validationFlags };
}

/**
 * Module 2: COGS Schedule Calculator
 */
function calculateCOGSSchedule(baseCOGS, inflationRates) {
  const cogs = [baseCOGS];
  
  for (let i = 0; i < inflationRates.length; i++) {
    const prevCOGS = cogs[cogs.length - 1];
    const newCOGS = prevCOGS * (1 + inflationRates[i]);
    cogs.push(newCOGS);
  }
  
  return cogs;
}

/**
 * Module 3: Gross Profit Calculator
 */
function calculateGrossProfit(revenue, cogs) {
  const grossProfit = [];
  const grossMargin = [];
  
  for (let i = 0; i < revenue.length; i++) {
    const gp = revenue[i] - cogs[i];
    grossProfit.push(gp);
    grossMargin.push(gp / revenue[i]);
  }
  
  return { grossProfit, grossMargin };
}

/**
 * Module 4: OpEx Schedule Calculator
 */
function calculateOpExSchedule(baseSGA, baseOther, growthRates) {
  const sga = [baseSGA];
  const other = [baseOther];
  
  for (let i = 0; i < growthRates.length; i++) {
    sga.push(sga[sga.length - 1] * (1 + growthRates[i]));
    other.push(other[other.length - 1] * (1 + growthRates[i]));
  }
  
  return { sga, other };
}

/**
 * Module 5: EBITDA Calculator
 */
function calculateEBITDA(grossProfit, sga, other) {
  const ebitda = [];
  const ebitdaMargin = [];
  
  for (let i = 0; i < grossProfit.length; i++) {
    const ebd = grossProfit[i] - sga[i] - other[i];
    ebitda.push(ebd);
    ebitdaMargin.push(ebd / grossProfit[i]); // Note: typically margin is vs revenue
  }
  
  return { ebitda, ebitdaMargin };
}

/**
 * Module 6: Depreciation Schedule Calculator
 */
function calculateDepreciationSchedule(existingPPE, usefulLifeExisting, capexArray, usefulLifeNew) {
  const years = capexArray.length + 1; // Include base year
  const existingDepr = [];
  const newAssetsDepr = [];
  const totalDepreciation = [];
  
  // Existing assets: straight-line depreciation
  const annualExistingDepr = existingPPE / usefulLifeExisting;
  for (let i = 0; i < years; i++) {
    existingDepr.push(annualExistingDepr);
  }
  
  // New assets: half-year convention
  for (let i = 0; i < years; i++) {
    let yearDepr = 0;
    
    // Depreciation from CapEx in previous years (full year)
    for (let j = 0; j < i; j++) {
      if (j < capexArray.length) {
        yearDepr += capexArray[j] / usefulLifeNew;
      }
    }
    
    // Depreciation from CapEx in current year (half-year convention)
    if (i < capexArray.length) {
      yearDepr += (capexArray[i] / usefulLifeNew) * 0.5;
    }
    
    newAssetsDepr.push(yearDepr);
    totalDepreciation.push(existingDepr[i] + yearDepr);
  }
  
  // Terminal year: CapEx = Depreciation (steady-state)
  const terminalCapEx = totalDepreciation[totalDepreciation.length - 1];
  
  return { existingDepr, newAssetsDepr, totalDepreciation, terminalCapEx };
}

/**
 * Module 7: EBIT & Interest Calculator
 */
function calculateEBIT(ebitda, depreciation) {
  return ebitda.map((ebd, i) => ebd - depreciation[i]);
}

/**
 * Module 8: Tax Schedule Calculator (Levered)
 */
function calculateTaxScheduleLevered(ebt, accountingDepr, taxDepr, nolRemaining, taxRate, utilizationLimit = 0.80) {
  const currentTax = [];
  const deferredTax = [];
  const totalTax = [];
  const nolRollforward = [nolRemaining];
  
  for (let i = 0; i < ebt.length; i++) {
    // Adjust for depreciation differences
    const ebtAdjusted = ebt[i] + accountingDepr[i] - taxDepr[i];
    
    // NOL utilization
    const maxUtilization = Math.min(nolRemaining, ebtAdjusted * utilizationLimit);
    const taxableIncome = Math.max(0, ebtAdjusted - maxUtilization);
    
    // Update NOL remaining
    nolRemaining = nolRemaining - maxUtilization;
    nolRollforward.push(nolRemaining);
    
    // Current tax
    const currTax = taxableIncome * taxRate;
    currentTax.push(currTax);
    
    // Deferred tax
    const defTax = (ebtAdjusted - taxableIncome) * taxRate;
    deferredTax.push(defTax);
    
    // Total tax
    totalTax.push(currTax + defTax);
  }
  
  // Terminal year: no deferred taxes
  deferredTax[deferredTax.length - 1] = 0;
  totalTax[totalTax.length - 1] = currentTax[currentTax.length - 1];
  
  return { currentTax, deferredTax, totalTax, nolRollforward };
}

/**
 * Module 9: Tax Schedule Calculator (Unlevered)
 */
function calculateTaxScheduleUnlevered(ebit, accountingDepr, taxDepr, nolRemaining, taxRate, utilizationLimit = 0.80) {
  const currentTaxUnlevered = [];
  const deferredTaxUnlevered = [];
  
  for (let i = 0; i < ebit.length; i++) {
    const ebitAdjusted = ebit[i] + accountingDepr[i] - taxDepr[i];
    const maxUtilization = Math.min(nolRemaining, ebitAdjusted * utilizationLimit);
    const taxableIncome = Math.max(0, ebitAdjusted - maxUtilization);
    
    const currTax = taxableIncome * taxRate;
    const defTax = (ebitAdjusted - taxableIncome) * taxRate;
    
    currentTaxUnlevered.push(currTax);
    deferredTaxUnlevered.push(defTax);
  }
  
  // Terminal year: no deferred taxes
  deferredTaxUnlevered[deferredTaxUnlevered.length - 1] = 0;
  
  return { currentTaxUnlevered, deferredTaxUnlevered };
}

/**
 * Module 10: Working Capital Schedule Calculator
 */
function calculateWorkingCapitalSchedule(revenue, cogs, arDays, invDays, apDays, daysInPeriod = 365) {
  const ar = [];
  const inventory = [];
  const ap = [];
  const nwc = [];
  const changeNWC = [0]; // First year has no change
  
  for (let i = 0; i < revenue.length; i++) {
    const arVal = revenue[i] * (arDays[i] / daysInPeriod);
    const invVal = cogs[i] * (invDays[i] / daysInPeriod);
    const apVal = cogs[i] * (apDays[i] / daysInPeriod);
    
    ar.push(arVal);
    inventory.push(invVal);
    ap.push(apVal);
    
    const nwcVal = arVal + invVal - apVal;
    nwc.push(nwcVal);
    
    if (i > 0) {
      changeNWC.push(nwcVal - nwc[i - 1]);
    }
  }
  
  return { ar, inventory, ap, nwc, changeNWC };
}

/**
 * Module 11: UFCF Calculator (EBITDA Method)
 */
function calculateUFCF(ebitda, currentTaxUnlevered, capexArray, changeNWC, terminalCapEx) {
  const ufcf = [];
  const allCapex = [...capexArray, terminalCapEx];
  
  for (let i = 0; i < ebitda.length && i < allCapex.length && i < changeNWC.length; i++) {
    const ufcfVal = ebitda[i] - currentTaxUnlevered[i] - allCapex[i] - changeNWC[i];
    ufcf.push(ufcfVal);
  }
  
  return ufcf;
}

/**
 * Module 12: DCF Discounting Calculator (Perpetuity Method)
 */
function calculateDCFPerpetuity(ufcf, wacc, terminalGrowthRate, partialPeriodAdjustment = [0.75, 1.0, 1.0, 1.0, 1.0, 1.0]) {
  // Validate terminal growth < WACC
  if (!VALIDATION_RULES.terminalGrowthLessThanWACC(terminalGrowthRate, wacc)) {
    throw new Error(`Terminal growth rate (${terminalGrowthRate}) must be less than WACC (${wacc})`);
  }
  
  // Adjust UFCF for partial periods
  const adjustedUFCF = ufcf.map((val, i) => val * (partialPeriodAdjustment[i] || 1.0));
  
  // Discount factors with partial period adjustment
  const yearsForDiscounting = [0.25, 1.25, 2.25, 3.25, 4.25, 5.25];
  const discountFactors = yearsForDiscounting.map(y => Math.pow(1 + wacc, y));
  
  // Present value of discrete cash flows
  const pvDiscrete = adjustedUFCF.slice(0, -1).reduce((sum, ufcf, i) => {
    return sum + (ufcf / discountFactors[i]);
  }, 0);
  
  // Terminal value using Gordon Growth Model
  const terminalUFCF = ufcf[ufcf.length - 1];
  const terminalValue = terminalUFCF * (1 + terminalGrowthRate) / (wacc - terminalGrowthRate);
  const pvTerminal = terminalValue / discountFactors[discountFactors.length - 1];
  
  // Enterprise value
  const enterpriseValue = pvDiscrete + pvTerminal;
  
  return {
    adjustedUFCF,
    discountFactors,
    pvDiscrete,
    terminalValue,
    pvTerminal,
    enterpriseValue
  };
}

/**
 * Module 13: DCF Discounting Calculator (Multiple Method)
 */
function calculateDCFMultiple(ufcf, ebitdaTerminal, terminalMultiple, wacc, partialPeriodAdjustment = [0.75, 1.0, 1.0, 1.0, 1.0, 1.0]) {
  // Validate terminal multiple range
  if (!VALIDATION_RULES.terminalMultipleInRange(terminalMultiple)) {
    console.warn(`[WARNING] Terminal multiple (${terminalMultiple}) outside typical range [5.0, 15.0]`);
  }
  
  // Adjust UFCF for partial periods
  const adjustedUFCF = ufcf.map((val, i) => val * (partialPeriodAdjustment[i] || 1.0));
  
  // Discount factors
  const yearsForDiscounting = [0.25, 1.25, 2.25, 3.25, 4.25, 5.25];
  const discountFactors = yearsForDiscounting.map(y => Math.pow(1 + wacc, y));
  
  // Present value of discrete cash flows
  const pvDiscrete = adjustedUFCF.slice(0, -1).reduce((sum, ufcf, i) => {
    return sum + (ufcf / discountFactors[i]);
  }, 0);
  
  // Terminal value using EBITDA multiple
  const terminalValue = ebitdaTerminal * terminalMultiple;
  const pvTerminal = terminalValue / discountFactors[discountFactors.length - 1];
  
  // Enterprise value
  const enterpriseValue = pvDiscrete + pvTerminal;
  
  return {
    adjustedUFCF,
    discountFactors,
    pvDiscrete,
    terminalValue,
    pvTerminal,
    enterpriseValue
  };
}

/**
 * Module 14: Equity Value & Per Share Calculator
 */
function calculateEquityValue(enterpriseValuePerpetuity, enterpriseValueMultiple, netDebt, sharesOutstanding, currentStockPrice) {
  if (!VALIDATION_RULES.positiveSharesOutstanding(sharesOutstanding)) {
    throw new Error('Shares outstanding must be positive');
  }
  
  const equityValuePerpetuity = enterpriseValuePerpetuity - netDebt;
  const equityValueMultiple = enterpriseValueMultiple - netDebt;
  
  const equityPerSharePerpetuity = equityValuePerpetuity / sharesOutstanding;
  const equityPerShareMultiple = equityValueMultiple / sharesOutstanding;
  
  const upsidePerpetuity = (equityPerSharePerpetuity - currentStockPrice) / currentStockPrice;
  const upsideMultiple = (equityPerShareMultiple - currentStockPrice) / currentStockPrice;
  
  return {
    equityValuePerpetuity,
    equityValueMultiple,
    equityPerSharePerpetuity,
    equityPerShareMultiple,
    upsidePerpetuity,
    upsideMultiple
  };
}

/**
 * Module 15: Sensitivity Analysis Calculator
 */
function calculateSensitivityTables(baseInputs, scenarios) {
  const perpetuityMethod = {
    enterpriseValueTable: {},
    equityValuePerShareTable: {},
    upsideDownsideTable: {}
  };
  
  const multipleMethod = {
    enterpriseValueTable: {},
    equityValuePerShareTable: {},
    upsideDownsideTable: {}
  };
  
  // Perpetuity method sensitivity (WACC vs Terminal Growth)
  const waccRange = [0.077, 0.087, 0.097, 0.107, 0.117];
  const growthRange = [0.01, 0.015, 0.02, 0.025, 0.03];
  
  for (const wacc of waccRange) {
    perpetuityMethod.enterpriseValueTable[wacc] = {};
    perpetuityMethod.equityValuePerShareTable[wacc] = {};
    perpetuityMethod.upsideDownsideTable[wacc] = {};
    
    for (const growth of growthRange) {
      try {
        const result = runCompleteDCF({ ...baseInputs, wacc, terminalGrowthRate: growth });
        perpetuityMethod.enterpriseValueTable[wacc][growth] = roundTo(result.enterpriseValuePerpetuity, 0);
        perpetuityMethod.equityValuePerShareTable[wacc][growth] = roundTo(result.equityPerSharePerpetuity, 2);
        perpetuityMethod.upsideDownsideTable[wacc][growth] = roundTo(result.upsidePerpetuity * 100, 1);
      } catch (error) {
        perpetuityMethod.enterpriseValueTable[wacc][growth] = null;
        perpetuityMethod.equityValuePerShareTable[wacc][growth] = null;
        perpetuityMethod.upsideDownsideTable[wacc][growth] = null;
      }
    }
  }
  
  // Multiple method sensitivity (WACC vs Terminal Multiple)
  const multipleRange = [6.0, 6.5, 7.0, 7.5, 8.0];
  
  for (const wacc of waccRange) {
    multipleMethod.enterpriseValueTable[wacc] = {};
    multipleMethod.equityValuePerShareTable[wacc] = {};
    multipleMethod.upsideDownsideTable[wacc] = {};
    
    for (const multiple of multipleRange) {
      try {
        const result = runCompleteDCF({ ...baseInputs, wacc, terminalMultiple: multiple });
        multipleMethod.enterpriseValueTable[wacc][multiple] = roundTo(result.enterpriseValueMultiple, 0);
        multipleMethod.equityValuePerShareTable[wacc][multiple] = roundTo(result.equityPerShareMultiple, 2);
        multipleMethod.upsideDownsideTable[wacc][multiple] = roundTo(result.upsideMultiple * 100, 1);
      } catch (error) {
        multipleMethod.enterpriseValueTable[wacc][multiple] = null;
        multipleMethod.equityValuePerShareTable[wacc][multiple] = null;
        multipleMethod.upsideDownsideTable[wacc][multiple] = null;
      }
    }
  }
  
  return { perpetuityMethod, multipleMethod };
}

/**
 * Main DCF Engine: Orchestrates all modules
 */
function runCompleteDCF(inputs) {
  const {
    // Base period data (FY-1 / 2022A)
    baseRevenue,
    baseCOGS,
    baseSGA,
    baseOther,
    baseExistingPPE,
    baseNOL,
    baseNetDebt,
    baseCurrentStockPrice,
    baseSharesOutstanding,
    
    // Forecast drivers (6 values: 5 years + terminal)
    revenueGrowthRates,      // [2023F, 2024F, 2025F, 2026F, 2027F, Term]
    inflationRates,          // [2023F, 2024F, 2025F, 2026F, 2027F, Term]
    opexGrowthRates,         // [2023F, 2024F, 2025F, 2026F, 2027F, Term]
    capitalExpenditures,     // [2023F, 2024F, 2025F, 2026F, 2027F]
    arDays,                  // [2023F, 2024F, 2025F, 2026F, 2027F, Term]
    invDays,                 // [2023F, 2024F, 2025F, 2026F, 2027F, Term]
    apDays,                  // [2023F, 2024F, 2025F, 2026F, 2027F, Term]
    
    // Assumptions
    usefulLifeExisting = 10,
    usefulLifeNew = 5,
    taxRate = 0.21,
    nolUtilizationLimit = 0.80,
    wacc = 0.097,
    terminalGrowthRate = 0.02,
    terminalMultiple = 7.0,
    partialPeriodAdjustment = [0.75, 1.0, 1.0, 1.0, 1.0, 1.0],
    daysInPeriod = 365,
    
    // Metadata
    valuationDate = new Date().toISOString().split('T')[0],
    scenario = 'base_case'
  } = inputs;
  
  // Validate inputs
  if (revenueGrowthRates.length !== 6) {
    throw new Error(`revenueGrowthRates must have exactly 6 values (5 years + terminal), got ${revenueGrowthRates.length}`);
  }
  if (capitalExpenditures.length !== 5) {
    throw new Error(`capitalExpenditures must have exactly 5 values (forecast years only), got ${capitalExpenditures.length}`);
  }
  
  // Execute calculation modules
  const revenueSchedule = calculateRevenueSchedule(baseRevenue, revenueGrowthRates);
  const cogsSchedule = calculateCOGSSchedule(baseCOGS, inflationRates);
  const grossProfit = calculateGrossProfit(revenueSchedule.revenue, cogsSchedule);
  const opExSchedule = calculateOpExSchedule(baseSGA, baseOther, opexGrowthRates);
  const ebitda = calculateEBITDA(grossProfit.grossProfit, opExSchedule.sga, opExSchedule.other);
  const depreciation = calculateDepreciationSchedule(baseExistingPPE, usefulLifeExisting, capitalExpenditures, usefulLifeNew);
  const ebit = calculateEBIT(ebitda.ebitda, depreciation.totalDepreciation);
  
  // Assume fixed interest expense (simplified model)
  const interestExpense = new Array(6).fill(0); // Can be customized
  const ebt = ebit.map(e => e - interestExpense[0]);
  
  // Tax schedules (assume tax depr = accounting depr for simplicity)
  const taxLevered = calculateTaxScheduleLevered(ebt, depreciation.totalDepreciation, depreciation.totalDepreciation, baseNOL, taxRate, nolUtilizationLimit);
  const taxUnlevered = calculateTaxScheduleUnlevered(ebit, depreciation.totalDepreciation, depreciation.totalDepreciation, baseNOL, taxRate, nolUtilizationLimit);
  
  // Working capital
  const workingCapital = calculateWorkingCapitalSchedule(revenueSchedule.revenue, cogsSchedule, arDays, invDays, apDays, daysInPeriod);
  
  // UFCF
  const ufcf = calculateUFCF(ebitda.ebitda, taxUnlevered.currentTaxUnlevered, capitalExpenditures, workingCapital.changeNWC, depreciation.terminalCapEx);
  
  // DCF Valuation
  const dcfPerpetuity = calculateDCFPerpetuity(ufcf, wacc, terminalGrowthRate, partialPeriodAdjustment);
  const dcfMultiple = calculateDCFMultiple(ufcf, ebitda.ebitda[5], terminalMultiple, wacc, partialPeriodAdjustment);
  
  // Equity Value
  const equityValue = calculateEquityValue(
    dcfPerpetuity.enterpriseValue,
    dcfMultiple.enterpriseValue,
    baseNetDebt,
    baseSharesOutstanding,
    baseCurrentStockPrice
  );
  
  // Build output structure
  const output = {
    main_outputs: {
      enterprise_value_perpetuity: roundTo(dcfPerpetuity.enterpriseValue, 0),
      enterprise_value_multiple: roundTo(dcfMultiple.enterpriseValue, 0),
      equity_value_perpetuity: roundTo(equityValue.equityValuePerpetuity, 0),
      equity_value_multiple: roundTo(equityValue.equityValueMultiple, 0),
      equity_value_per_share_perpetuity: roundTo(equityValue.equityPerSharePerpetuity, 2),
      equity_value_per_share_multiple: roundTo(equityValue.equityPerShareMultiple, 2),
      current_stock_price: baseCurrentStockPrice,
      upside_downside_perpetuity_pct: roundTo(equityValue.upsidePerpetuity * 100, 1),
      upside_downside_multiple_pct: roundTo(equityValue.upsideMultiple * 100, 1)
    },
    
    supporting_schedules: {
      income_statement_forecast: {
        years: ['2022A', '2023F', '2024F', '2025F', '2026F', '2027F', 'Term'],
        revenue: revenueSchedule.revenue.map(r => roundTo(r, 2)),
        cogs: cogsSchedule.map(c => roundTo(c, 2)),
        gross_profit: grossProfit.grossProfit.map(gp => roundTo(gp, 2)),
        gross_margin: grossProfit.grossMargin.map(m => roundTo(m * 100, 2)),
        sga: opExSchedule.sga.map(s => roundTo(s, 2)),
        other: opExSchedule.other.map(o => roundTo(o, 2)),
        ebitda: ebitda.ebitda.map(e => roundTo(e, 2)),
        ebitda_margin: ebitda.ebitdaMargin.map(m => roundTo(m * 100, 2)),
        depreciation: depreciation.totalDepreciation.map(d => roundTo(d, 2)),
        ebit: ebit.map(e => roundTo(e, 2)),
        interest: interestExpense.map(i => roundTo(i, 2)),
        ebt: ebt.map(e => roundTo(e, 2)),
        current_tax: taxLevered.currentTax.map(t => roundTo(t, 2)),
        deferred_tax: taxLevered.deferredTax.map(t => roundTo(t, 2)),
        total_tax: taxLevered.totalTax.map(t => roundTo(t, 2)),
        net_income: ebt.map((e, i) => roundTo(e - taxLevered.totalTax[i], 2))
      },
      
      working_capital_forecast: {
        years: ['2022A', '2023F', '2024F', '2025F', '2026F', '2027F', 'Term'],
        ar: workingCapital.ar.map(v => roundTo(v, 2)),
        inventory: workingCapital.inventory.map(v => roundTo(v, 2)),
        ap: workingCapital.ap.map(v => roundTo(v, 2)),
        nwc: workingCapital.nwc.map(v => roundTo(v, 2)),
        change_nwc: workingCapital.changeNWC.map(v => roundTo(v, 2))
      },
      
      depreciation_forecast: {
        years: ['2022A', '2023F', '2024F', '2025F', '2026F', '2027F', 'Term'],
        existing_assets_depr: depreciation.existingDepr.map(d => roundTo(d, 2)),
        new_assets_depr: depreciation.newAssetsDepr.map(d => roundTo(d, 2)),
        total_depreciation: depreciation.totalDepreciation.map(d => roundTo(d, 2))
      },
      
      ufcf_forecast: ufcf.map((u, i) => ({
        year: ['2023F', '2024F', '2025F', '2026F', '2027F', 'Term'][i],
        ufcf: roundTo(u, 2)
      })),
      
      discounting_details: {
        pv_discrete_perpetuity: roundTo(dcfPerpetuity.pvDiscrete, 2),
        pv_terminal_perpetuity: roundTo(dcfPerpetuity.pvTerminal, 2),
        enterprise_value_perpetuity: roundTo(dcfPerpetuity.enterpriseValue, 2),
        pv_discrete_multiple: roundTo(dcfMultiple.pvDiscrete, 2),
        pv_terminal_multiple: roundTo(dcfMultiple.pvTerminal, 2),
        enterprise_value_multiple: roundTo(dcfMultiple.enterpriseValue, 2)
      }
    },
    
    metadata: {
      valuation_date: valuationDate,
      base_year: '2022A',
      scenario_used: scenario,
      wacc_used: wacc,
      terminal_growth_used: terminalGrowthRate,
      terminal_multiple_used: terminalMultiple,
      shares_outstanding_used: baseSharesOutstanding,
      net_debt_used: baseNetDebt,
      calculation_timestamp: new Date().toISOString(),
      model_version: '1.0.0',
      validation_flags: {
        terminal_growth_less_than_wacc: VALIDATION_RULES.terminalGrowthLessThanWACC(terminalGrowthRate, wacc),
        positive_revenue_all_years: revenueSchedule.validationFlags.allPositive,
        positive_ebitda_terminal: ebitda.ebitda[5] > 0,
        nol_fully_utilized: taxLevered.nolRollforward[taxLevered.nolRollforward.length - 1] === 0
      }
    }
  };
  
  return output;
}

/**
 * API-ready function: Run DCF with scenario support
 */
function runDCFWithScenarios(baseInputs, scenarios = ['best_case', 'base_case', 'worst_case']) {
  const results = {};
  
  for (const scenario of scenarios) {
    const scenarioInputs = {
      ...baseInputs,
      scenario
    };
    
    // Apply scenario-specific adjustments to forecast drivers
    if (scenario === 'best_case') {
      scenarioInputs.revenueGrowthRates = baseInputs.revenueGrowthRates.map(g => g * 1.2); // 20% higher growth
    } else if (scenario === 'worst_case') {
      scenarioInputs.revenueGrowthRates = baseInputs.revenueGrowthRates.map(g => g * 0.8); // 20% lower growth
    }
    
    try {
      results[scenario] = runCompleteDCF(scenarioInputs);
    } catch (error) {
      results[scenario] = { error: error.message };
    }
  }
  
  return results;
}

// Export all modules and main functions
module.exports = {
  // Main engine functions
  runCompleteDCF,
  runDCFWithScenarios,
  
  // Individual calculation modules (for testing and reuse)
  calculateRevenueSchedule,
  calculateCOGSSchedule,
  calculateGrossProfit,
  calculateOpExSchedule,
  calculateEBITDA,
  calculateDepreciationSchedule,
  calculateEBIT,
  calculateTaxScheduleLevered,
  calculateTaxScheduleUnlevered,
  calculateWorkingCapitalSchedule,
  calculateUFCF,
  calculateDCFPerpetuity,
  calculateDCFMultiple,
  calculateEquityValue,
  calculateSensitivityTables,
  
  // Helpers
  calculateMedian,
  calculatePercentile,
  roundTo,
  
  // Validation
  VALIDATION_RULES
};
