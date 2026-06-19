/**
 * historicalDataExtractor.ts
 *
 * Extracts historical actuals from the `complete_financial_statements` session object.
 * The merged financial statements have a nested structure organized by statement type
 * (income_statement, balance_sheet, cash_flow) with periods as keys.
 *
 * This extractor normalizes the data into flat arrays of the last 3 historical years,
 * which is the format required by the DCF calculator (Excel model columns F-H).
 */

export interface HistoricalActuals {
  revenue: number[];
  cogs: number[];
  sga: number[];
  otherOpex: number[];
  capex: number[];
  depreciation: number[];
  interestExpense: number[];
  ar: number[];
  inventory: number[];
  ap: number[];
  ppe: number[];
  taxBasis: number[];
  taxLosses: number[];
  // Additional income statement items
  grossProfit: number[];
  ebitda: number[];
  ebit: number[];
  netIncome: number[];
  taxProvision: number[];
  pretaxIncome: number[];
  // Additional balance sheet items
  cash: number[];
  totalDebt: number[];
  longTermDebt: number[];
  currentDebt: number[];
  shortTermDebt: number[];
  totalAssets: number[];
  totalEquity: number[];
  commonEquity: number[];  // Total Shareholders' Equity - Retained Earnings
  totalLiabilities: number[];
  currentAssets: number[];
  currentLiabilities: number[];
  deferredTax: number[];
  ppeNet: number[];
  accumulatedDepreciation: number[];
  retainedEarnings: number[];
  sharesOutstanding: number[];
  dividendsPaid: number[];
  marketCap: number[];
  // Additional income statement items (extracted but previously unused)
  interestIncome: number[];
  otherIncomeExpense: number[];
  researchDevelopment: number[];
  // Additional cash flow items (extracted but previously unused)
  operatingCashFlow: number[];
  shareBuybacks: number[];
  debtRepayments: number[];
  debtIssuance: number[];
  taxPaid: number[];
  interestPaid: number[];
  // Institution-grade balance sheet items (critical for DCF accuracy)
  nonCurrentMarketableSecurities: number[];  // Long-term bond portfolio
  otherCurrentLiabilities: number[];          // Accrued Expenses + Deferred Revenue
  deferredTaxLiabilities: number[];           // Net DTA/DTL position
  // New granularity balance sheet items (Steps 5-6-7 additions)
  currentAccruedExpenses: number[];           // Accrued expenses (component of other CL)
  currentDeferredLiabilities: number[];       // Deferred revenue (component of other CL)
  tradeAndOtherPayablesNonCurrent: number[];  // Non-current operating payables
  otherNonCurrentLiabilities: number[];       // Other non-current liabilities beyond LT debt & DTL
  otherShortTermInvestments: number[];        // Short-term investments (< 1 year)
  otherCurrentAssets: number[];               // Prepaid expenses, deferred tax assets (current)
  otherNonCurrentAssets: number[];            // Goodwill, intangibles, long-term deposits
  commonStock: number[];                      // Par value of issued shares
  otherEquityAdjustments: number[];           // AOCI, treasury stock, translation adjustments
  periods: string[]; // The period labels (e.g. "2022", "2023", "2024")
}

/**
 * Safely extract a numeric value from a period-keyed object.
 * Handles cases where the value might be an object with a `value` property
 * (DataField format from backend) or a plain number.
 */
function extractValue(
  source: Record<string, any> | undefined | null,
  period: string,
  fallback: number = 0
): number {
  if (!source) return fallback;
  const raw = source[period];
  if (raw === undefined || raw === null) return fallback;
  if (typeof raw === 'number') return raw;
  if (typeof raw === 'string') {
    const parsed = parseFloat(raw);
    return isNaN(parsed) ? fallback : parsed;
  }
  // DataField format: { value: number, status: string, ... }
  if (typeof raw === 'object' && raw.value !== undefined) {
    const val = parseFloat(raw.value);
    return isNaN(val) ? fallback : val;
  }
  return fallback;
}

/**
 * Get the sorted period keys from a statement section, taking the last N periods.
 */
function getPeriods(
  section: Record<string, any> | undefined | null,
  count: number = 5
): string[] {
  if (!section) return [];
  // Filter out non-period keys (metadata like 'source', 'currency', etc.)
  const periodKeys = Object.keys(section).filter((key) => {
    // Periods are typically year strings like "2022", "2023", "2024"
    // or "FY2022", "2022-12-31", etc.
    const val = section[key];
    if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
      // Check if it has numeric-like content (DataField or period data)
      return val.value !== undefined || typeof val === 'number';
    }
    return typeof val === 'number' || typeof val === 'string';
  });

  // Try to sort chronologically
  periodKeys.sort((a, b) => {
    // Extract year from period key
    const yearA = parseInt(a.replace(/\D/g, '').slice(0, 4), 10);
    const yearB = parseInt(b.replace(/\D/g, '').slice(0, 4), 10);
    if (!isNaN(yearA) && !isNaN(yearB)) return yearA - yearB;
    return a.localeCompare(b);
  });

  return periodKeys.slice(-count);
}

/**
 * Extract historical actuals from the complete_financial_statements object.
 *
 * @param statements - The merged financial statements from session
 * @returns HistoricalActuals with 3-year arrays for each metric
 */
/**
 * Transpose period-keyed data to field-keyed data.
 * Merger produces: { "2022": { revenue: 100, cogs: 50 }, "2023": { ... } }
 * Extractor expects: { revenue: { "2022": 100, "2023": 110 }, cogs: { ... } }
 */
function transposeIfNeeded(section: Record<string, any>): Record<string, any> {
  if (!section || typeof section !== 'object') return section || {};
  const keys = Object.keys(section);
  if (keys.length === 0) return {};
  
  // Check if keys look like years (period-keyed structure)
  const isPeriodKeyed = keys.some(k => /^\d{4}/.test(k));
  if (!isPeriodKeyed) return section; // Already field-keyed
  
  // Check if first value is an object with field names (period-keyed)
  const firstVal = section[keys[0]];
  if (typeof firstVal !== 'object' || firstVal === null || Array.isArray(firstVal)) {
    return section;
  }
  
  // Transpose: period-keyed → field-keyed
  const result: Record<string, any> = {};
  for (const period of keys) {
    const periodData = section[period];
    if (typeof periodData === 'object' && periodData !== null) {
      for (const [fieldName, fieldValue] of Object.entries(periodData)) {
        if (!result[fieldName]) result[fieldName] = {};
        result[fieldName][period] = fieldValue;
      }
    }
  }
  return result;
}

export function extractHistoricalActuals(
  statements: any
): HistoricalActuals {
  const incomeStatement = transposeIfNeeded(statements?.income_statement || {});
  const balanceSheet = transposeIfNeeded(statements?.balance_sheet || {});
  const cashFlow = transposeIfNeeded(statements?.cash_flow || {});

  // Determine common periods from revenue (most complete dataset)
  const periods = getPeriods(incomeStatement.revenue || incomeStatement, 3);

  // If no periods found, try from balance sheet
  const bsPeriods = getPeriods(
    balanceSheet.accounts_receivable || balanceSheet,
    3
  );
  const finalPeriods = periods.length > 0 ? periods : bsPeriods;

  // Helper to extract a time series from any statement section
  const extractSeries = (
    section: Record<string, any> | undefined,
    fieldName: string,
    ...altFields: string[]
  ): number[] => {
    if (!section || finalPeriods.length === 0) return [0, 0, 0];

    // Try the direct field name first
    let source = section[fieldName];

    // If not found, try alternative field names
    if (!source) {
      for (const alt of altFields) {
        if (alt && section[alt]) {
          source = section[alt];
          break;
        }
      }
    }

    // If the section itself is the field (flat period-keyed structure)
    if (!source && typeof section === 'object') {
      // Check if the section keys look like periods
      const keys = Object.keys(section);
      if (keys.length > 0 && keys.some((k) => /^\d{4}/.test(k))) {
        source = section;
      }
    }

    if (!source) return finalPeriods.map(() => 0);

    // source might be a period-keyed object like { "2022": 100, "2023": 110 }
    if (typeof source === 'object' && !Array.isArray(source)) {
      return finalPeriods.map((p) => extractValue(source, p));
    }

    // If it's already an array, take the last 3
    if (Array.isArray(source)) {
      return source.slice(-3);
    }

    return finalPeriods.map(() => 0);
  };

  // Extract revenue periods for fallback
  const revenuePeriods = getPeriods(incomeStatement.revenue, 3);
  const bsRevenuePeriods = getPeriods(
    balanceSheet.accounts_receivable || balanceSheet,
    3
  );
  const effectivePeriods =
    revenuePeriods.length > 0 ? revenuePeriods : bsRevenuePeriods;

  // Build the historical actuals
  const revenue = extractSeries(incomeStatement, 'revenue');
  const cogs = extractSeries(incomeStatement, 'cogs', 'cost_of_goods_sold');
  const sga = extractSeries(
    incomeStatement,
    'sga',
    'sg_and_a'
  );
  // operating_expenses is TOTAL (SG&A + R&D + Other) — do NOT use as SG&A fallback
  // Other OpEx = Operating Expenses − SG&A − R&D
  // yfinance's OperatingExpense = R&D + SG&A + OtherOperatingExpenses
  // (D&A is NOT in OperatingExpense — it's embedded inside COGS and SG&A)
  const opexRaw = extractSeries(incomeStatement, 'operating_expenses');
  const sgaRaw = extractSeries(incomeStatement, 'sg_and_a');
  const rdRaw = extractSeries(incomeStatement, 'research_development', 'research__development');
  const otherOpex = opexRaw.map((oe, i) => {
    if (!oe || oe === 0) return 0;
    return Math.max(oe - (sgaRaw[i] || 0) - (rdRaw[i] || 0), 0);
  });
  const grossProfit = extractSeries(incomeStatement, 'gross_profit');
  const ebitda = extractSeries(incomeStatement, 'ebitda');
  const ebit = extractSeries(incomeStatement, 'ebit', 'operating_income');
  const netIncome = extractSeries(incomeStatement, 'net_income');
  const taxProvision = extractSeries(incomeStatement, 'tax_provision', 'tax_expense');
  const pretaxIncome = extractSeries(incomeStatement, 'pretax_income', 'income_before_tax', 'pretax_income');
  const depreciation = extractSeries(
    incomeStatement,
    'depreciation',
    'depreciation_amortization'
  );
  const interestExpense = extractSeries(
    incomeStatement,
    'interest_expense',
    'interest_expenses',
    'interest expense',
    'total_interest_expense',
    'net_interest_expense',
    'finance_cost',
    'finance_costs',
    'borrowing_costs'
  );
  const interestIncome = extractSeries(incomeStatement, 'interest_income', 'interest_income_non_operating');
  const researchDevelopment = extractSeries(incomeStatement, 'research_development');
  // Other Income/Expense = Interest Income + Interest Expense (combined parent)
  // Compute from available interest data rather than relying on a single field
  const otherIncomeExpenseDirect = extractSeries(incomeStatement, 'other_income', 'other_income_expense');
  const otherIncomeExpense = otherIncomeExpenseDirect.length > 0 && otherIncomeExpenseDirect.some(v => v !== 0)
    ? otherIncomeExpenseDirect
    : interestIncome.map((ii, i) => (ii || 0) + (interestExpense[i] || 0));
  const capex = extractSeries(
    cashFlow,
    'capital_expenditure',
    'capex'
  );

  // Balance sheet items
  const ar = extractSeries(
    balanceSheet,
    'accounts_receivable',
    'trade_receivables'
  );
  const inventory = extractSeries(balanceSheet, 'inventory');
  const ap = extractSeries(
    balanceSheet,
    'accounts_payable',
    'trade_payables'
  );
  const ppe = extractSeries(
    balanceSheet,
    'ppe_gross',
    'property_plant_equipment',
  );

  // Tax basis and tax losses may not always be present
  const taxBasis = extractSeries(
    balanceSheet,
    'tax_basis',
    'deferred_tax_assets'
  );
  const taxLosses = extractSeries(
    balanceSheet,
    'tax_loss_carryforward',
    'tax_losses'
  );

  // Additional balance sheet items
  const cash = extractSeries(balanceSheet, 'cash', 'cash_and_equivalents');
  const totalDebt = extractSeries(balanceSheet, 'total_debt', 'total_liabilities');
  const longTermDebt = extractSeries(balanceSheet, 'long_term_debt', 'lt_debt');
  const currentDebt = extractSeries(balanceSheet, 'current_debt');
  const shortTermDebt = extractSeries(balanceSheet, 'short_term_debt');
  const totalAssets = extractSeries(balanceSheet, 'total_assets');
  const totalEquity = extractSeries(balanceSheet, 'total_equity', 'shareholders_equity');
  // Compute totalLiabilities = totalAssets - totalEquity (merger doesn't have this directly)
  const rawTotalLiabilities = extractSeries(balanceSheet, 'total_liabilities');
  // Compute totalCurrentAssets = cash + AR + inventory (merger doesn't have this directly)
  const rawCurrentAssets = extractSeries(balanceSheet, 'total_current_assets', 'current_assets');
  // Compute totalCurrentLiabilities = AP + current_debt (merger doesn't have this directly)
  const rawCurrentLiabilities = extractSeries(balanceSheet, 'total_current_liabilities', 'current_liabilities');
  // Deferred tax EXPENSE from income statement (not balance sheet DTA/DTL position).
  // Tax Provision = Current Tax + Deferred Tax.  If deferred_tax unavailable, treat provision as current tax.
  const deferredTaxFromIS = extractSeries(incomeStatement, 'deferred_tax', 'deferred_tax_expense');
  const taxProvisionFromIS = extractSeries(incomeStatement, 'tax_provision', 'income_tax_expense');
  // Defensive: if deferred_tax is empty/all-zero, set to zeros (tax_provision = current tax)
  const deferredTax = deferredTaxFromIS.length > 0 && deferredTaxFromIS.some(v => v !== 0)
    ? deferredTaxFromIS
    : taxProvisionFromIS.map(() => 0);  // All zeros = no deferred component
  const ppeNet = extractSeries(balanceSheet, 'ppe_net', 'net_ppe', 'property_plant_equipment_net');
  const accumulatedDepreciation = extractSeries(
    balanceSheet, 'accumulated_depreciation',
    'accumulated_impairment_losses',
    'less_accumulated_depreciation',
    'accumulated_depreciation_and_amortization'
  );
  const retainedEarnings = extractSeries(
    balanceSheet, 'retained_earnings', 'accumulated_retained_earnings', 'retained_profit'
  );
  const sharesOutstanding = extractSeries(balanceSheet, 'shares_outstanding');
  // Cash flow items
  const dividendsPaid = extractSeries(cashFlow, 'dividends_paid', 'dividends');
  const operatingCashFlow = extractSeries(cashFlow, 'operating_cash_flow');
  const freeCashFlow = extractSeries(cashFlow, 'free_cash_flow');
  const taxPaid = extractSeries(cashFlow, 'tax_paid');
  const shareBuybacks = extractSeries(cashFlow, 'share_buybacks');
  const debtRepayments = extractSeries(cashFlow, 'debt_repayments');
  const debtIssuance = extractSeries(cashFlow, 'debt_issuance');
  const interestPaid = extractSeries(cashFlow, 'interest_paid');
  const workingCapitalChanges = extractSeries(cashFlow, 'working_capital_changes');
  const marketCap = extractSeries(balanceSheet, 'market_cap', 'market_capitalization');
  // netIncome already declared above with grossProfit, ebitda, etc.

  // Common Equity: prefer the raw 'common_stock' field (par value + APIC) from balance sheet.
  // The backend now computes 'common_equity' = shareholders_equity - retained_earnings
  // and includes it in the historical summary. Try that first, then common_stock, then
  // fall back to computing Total Equity - Retained Earnings.
  const rawCommonEquity = extractSeries(balanceSheet, 'common_equity', 'common_stock', 'common_stock_equity');
  const commonEquity = rawCommonEquity.some(v => v !== 0)
    ? rawCommonEquity
    : totalEquity.map((te, i) => {
        const re = retainedEarnings[i] || 0;
        return te - re;
      });

  // New granularity balance sheet items (Steps 5-6-7 additions)
  const currentAccruedExpenses = extractSeries(balanceSheet, 'current_accrued_expenses', 'accrued_expenses');
  const currentDeferredLiabilities = extractSeries(balanceSheet, 'current_deferred_liabilities', 'deferred_revenue');
  const tradeAndOtherPayablesNonCurrent = extractSeries(balanceSheet, 'trade_and_other_payables_non_current', 'non_current_payables');
  const otherNonCurrentLiabilities = extractSeries(balanceSheet, 'other_non_current_liabilities');
  const otherShortTermInvestments = extractSeries(balanceSheet, 'other_short_term_investments', 'short_term_investments');
  const otherCurrentAssets = extractSeries(balanceSheet, 'other_current_assets', 'prepaid_expenses');
  const otherNonCurrentAssets = extractSeries(balanceSheet, 'other_non_current_assets', 'goodwill', 'intangible_assets');
  const commonStock = extractSeries(balanceSheet, 'common_stock', 'common_stock_equity');
  const otherEquityAdjustments = extractSeries(balanceSheet, 'other_equity_adjustments', 'aoci', 'treasury_stock');

  return {
    revenue,
    cogs,
    sga,
    otherOpex,
    grossProfit,
    ebitda,
    ebit,
    netIncome,
    taxProvision,
    pretaxIncome,
    capex,
    depreciation,
    interestExpense,
    ar,
    inventory,
    ap,
    ppe,
    taxBasis,
    taxLosses,
    cash,
    totalDebt,
    longTermDebt,
    currentDebt,
    shortTermDebt,
    totalAssets,
    totalEquity,
    commonEquity,
    // Compute totalLiabilities = totalAssets - totalEquity (accounting equation)
    totalLiabilities: rawTotalLiabilities.length > 0 && rawTotalLiabilities.some(v => v !== 0)
      ? rawTotalLiabilities
      : totalAssets.map((a, i) => a - (totalEquity[i] || 0)),
    // Compute totalCurrentAssets = cash + AR + inventory
    currentAssets: rawCurrentAssets.length > 0 && rawCurrentAssets.some(v => v !== 0)
      ? rawCurrentAssets
      : cash.map((c, i) => c + (ar[i] || 0) + (inventory[i] || 0)),
    // Compute totalCurrentLiabilities = AP (simplified; merger doesn't have this directly)
    currentLiabilities: rawCurrentLiabilities.length > 0 && rawCurrentLiabilities.some(v => v !== 0)
      ? rawCurrentLiabilities
      : ap.map((a) => a),
    deferredTax,
    ppeNet,
    accumulatedDepreciation,
    retainedEarnings,
    sharesOutstanding,
    dividendsPaid,
    interestIncome,
    otherIncomeExpense,
    researchDevelopment,
    operatingCashFlow,
    shareBuybacks,
    debtRepayments,
    debtIssuance,
    taxPaid,
    interestPaid,
    marketCap,
    // Institution-grade balance sheet items (extracted from balance sheet data)
    // Backend may use hyphens or underscores — try both
    // NCMS: Long-term bond portfolio (asset, should be positive)
    nonCurrentMarketableSecurities: extractSeries(balanceSheet, 'non_current_marketable_securities', 'non-current_marketable_securities'),
    otherCurrentLiabilities: extractSeries(balanceSheet, 'other_current_liabilities', 'other-current_liabilities'),
    deferredTaxLiabilities: extractSeries(balanceSheet, 'deferred_tax_liabilities', 'deferred-tax_liabilities'),
    // New granularity balance sheet items
    currentAccruedExpenses,
    currentDeferredLiabilities,
    tradeAndOtherPayablesNonCurrent,
    otherNonCurrentLiabilities,
    otherShortTermInvestments,
    otherCurrentAssets,
    otherNonCurrentAssets,
    commonStock,
    otherEquityAdjustments,
    periods: effectivePeriods,
  };
}
