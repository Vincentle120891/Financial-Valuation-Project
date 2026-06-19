/**
 * DCF type definitions and input validation.
 *
 * Types define the shape of DCF inputs and outputs for TypeScript.
 * These are consumed by Step 9 (building block schedules) and Step 10 (valuation).
 *
 * Output interfaces are named to match backend dataclass field names exactly
 * (camelCase conversion of backend snake_case). This eliminates the need for
 * field-name mapping in the transform function — only case conversion is needed.
 *
 * Calculation logic lives in the backend DCFEngine:
 * - POST /step-9-calculate-building-blocks (Phases 1-19)
 * - POST /step-10-valuate (Phases 20-26)
 */

// ─── Input Types ──────────────────────────────────────────────────────────

export interface DCFInputs {
  // Forecast drivers (5yr arrays for forecast years)
  revenueGrowth: number[];
  cogsGrowthRate: number[];
  inflationRate: number[];
  opexGrowthRate: number[];
  taxRate: number;
  arDays: number;
  invDays: number;
  apDays: number;
  capex: number[];
  usefulLifeExisting: number;
  usefulLifeNew: number;
  firstYearDepreciationRate: number;

  // WACC components
  wacc: number;
  riskFreeRate: number;
  equityRiskPremium: number;
  beta: number;
  costOfDebt: number;
  debtToEquity: number;

  // Terminal value
  terminalGrowthRate: number;
  terminalEbitdaMultiple: number;

  // Financing assumptions
  changeInLtDebt: number[];
  changeInCommonEquity: number[];
  dividendPayoutRatio: number;

  // Interest rate schedule inputs
  cashInterestRate: number;
  revolvingCreditRate: number;
  ltDebtInterestRate: number;

  // Tax depreciation schedule inputs
  firstYearTaxDepRate: number;
  blendedTaxDepRate: number;
  firstYearAcctgDepRate: number;

  // Market data
  currentPrice: number;
  sharesOutstanding: number;
  netDebt: number;

  // DCF model parameters (hidden fields exposed in Step 9)
  ppeGrossBook: number;
  taxBasisPpe: number;
  taxLossesNol: number;
  revolvingCreditLine: number;
  taxLossUtilizationLimit: number;

  // Historical actuals (3+ years)
  historicalRevenue: number[];
  historicalCogs: number[];
  historicalSga: number[];
  historicalOtherOpex: number[];
  historicalGrossProfit: number[];
  historicalEbitda: number[];
  historicalEbit: number[];
  historicalNetIncome: number[];
  historicalTaxProvision: number[];
  historicalPretaxIncome: number[];
  historicalCapex: number[];
  historicalDepreciation: number[];
  historicalInterestExpense: number[];
  historicalAr: number[];
  historicalInventory: number[];
  historicalAp: number[];
  historicalPpe: number[];
  historicalTaxBasis: number[];
  historicalTaxLosses: number[];
  historicalAccumulatedDepreciation: number[];
  historicalCurrentDebt: number[];
  historicalPpeNet: number[];
  // Additional balance sheet items
  historicalCash: number[];
  historicalTotalDebt: number[];
  historicalTotalAssets: number[];
  historicalTotalEquity: number[];
  historicalTotalLiabilities: number[];
  historicalCurrentAssets: number[];
  historicalCurrentLiabilities: number[];
  historicalDeferredTax: number[];
  historicalRetainedEarnings: number[];
  historicalCommonEquity: number[];
  historicalDividendsPaid: number[];
  historicalShareBuybacks: number[];
  historicalMarketCap: number[];
  historicalResearchDevelopment: number[];
  historicalInterestIncome: number[];
  historicalOtherIncomeExpense: number[];
  historicalTaxPaid: number[];
  historicalInterestPaid: number[];
  historicalDebtIssuance: number[];
  historicalDebtRepayments: number[];
  // Institution-grade balance sheet items (critical for DCF accuracy)
  historicalNonCurrentMarketableSecurities: number[];  // Long-term bond portfolio (e.g., Apple ~$165B)
  historicalOtherCurrentLiabilities: number[];          // Accrued Expenses + Deferred Revenue
  historicalDeferredTaxLiabilities: number[];           // Net DTA/DTL position
  // New granularity balance sheet items (Steps 5-6-7 additions)
  historicalCurrentAccruedExpenses: number[];           // Accrued expenses (component of other CL)
  historicalCurrentDeferredLiabilities: number[];       // Deferred revenue (component of other CL)
  historicalTradeAndOtherPayablesNonCurrent: number[];  // Non-current operating payables
  historicalOtherNonCurrentLiabilities: number[];       // Other non-current liabilities beyond LT debt & DTL
  historicalOtherShortTermInvestments: number[];        // Short-term investments (< 1 year)
  historicalOtherCurrentAssets: number[];               // Prepaid expenses, deferred tax assets (current)
  historicalOtherNonCurrentAssets: number[];            // Goodwill, intangibles, long-term deposits
  historicalCommonStock: number[];                      // Par value of issued shares
  historicalOtherEquityAdjustments: number[];           // AOCI, treasury stock, translation adjustments
}

// ─── Output Types (mirrors backend dataclass names — camelCase of snake_case) ──

/**
 * Income Statement — matches backend `IncomeStatement` dataclass.
 * Fields: revenue, cogs, gross_profit, sga, other_opex, ebitda, depreciation,
 *         ebit, interest_expense, ebt, current_tax, deferred_tax, total_tax, net_income
 */
export interface IncomeStatement {
  years: string[];
  revenue: number[];
  cogs: number[];
  grossProfit: number[];
  sga: number[];
  otherOpex: number[];
  ebitda: number[];
  depreciation: number[];
  ebit: number[];
  interestExpense: number[];
  ebt: number[];
  currentTax: number[];
  deferredTax: number[];
  totalTax: number[];
  netIncome: number[];
}

/**
 * Working Capital — matches backend `WorkingCapitalSchedule` dataclass.
 * Fields: ar_balance, inventory_balance, ap_balance, nwc, change_in_nwc,
 *         ar_days, inv_days, ap_days
 */
export interface WorkingCapital {
  years: string[];
  arBalance: number[];
  inventoryBalance: number[];
  apBalance: number[];
  nwc: number[];
  changeInNwc: number[];
  arDays: number[];
  invDays: number[];
  apDays: number[];
}

/**
 * Depreciation + Asset Schedule — matches backend `DepreciationSchedule` dataclass.
 * Fields: capex, existing_asset_dep, new_asset_dep, total_depreciation,
 *         gross_ppe_ending, tax_basis_ending, tax_depreciation
 *
 * Note: Backend puts PP&E roll and Tax Basis roll inside DepreciationSchedule.
 * The frontend previously split these into a separate AssetSchedule — now merged.
 */
export interface DepreciationSchedule {
  years: string[];
  capex: number[];
  existingAssetDep: number[];
  newAssetDep: number[];
  totalDepreciation: number[];
  grossPpeEnding: number[];
  taxBasisEnding: number[];
  taxDepreciation: number[];
}

/**
 * Tax Schedule — matches backend `TaxSchedule` dataclass.
 * Fields: ebt_ebit, accounting_dep, tax_dep, ebt_adjusted,
 *         nol_opening, nol_new, nol_used, nol_ending,
 *         taxable_income, current_tax, total_tax, deferred_tax
 *
 * Note: Backend uses `ebt_ebit` for both levered (EBT-based) and unlevered (EBIT-based).
 */
export interface TaxSchedule {
  years: string[];
  ebtEbit: number[];
  accountingDep: number[];
  taxDep: number[];
  ebtAdjusted: number[];
  nolOpening: number[];
  nolNew: number[];
  nolUsed: number[];
  nolEnding: number[];
  taxableIncome: number[];
  currentTax: number[];
  totalTax: number[];
  deferredTax: number[];
}

/**
 * Cash Flow Statement — matches backend `CashFlowStatement` dataclass.
 * Fields: net_income, deferred_taxes, depreciation, cash_from_ar, cash_from_inventory,
 *         cash_from_ap, subtotal_cfo, capital_expenditure, subtotal_cfi,
 *         change_in_lt_debt, change_in_common_equity, dividends, revolving_credit,
 *         subtotal_cff, beginning_cash, increase_decrease, ending_cash
 */
export interface CashFlowStatement {
  years: string[];
  netIncome: number[];
  deferredTaxes: number[];
  depreciation: number[];
  cashFromAr: number[];
  cashFromInventory: number[];
  cashFromAp: number[];
  subtotalCfo: number[];
  capitalExpenditure: number[];
  subtotalCfi: number[];
  changeInLtDebt: number[];
  changeInCommonEquity: number[];
  dividends: number[];
  revolvingCredit: number[];
  subtotalCff: number[];
  beginningCash: number[];
  increaseDecrease: number[];
  endingCash: number[];
}

/**
 * Balance Sheet — matches backend `BalanceSheet` dataclass.
 * Fields: cash, accounts_receivable, inventories, total_current_assets,
 *         ppe_gross, total_assets, accounts_payable, revolving_credit,
 *         total_current_liabilities, long_term_debt, total_liabilities,
 *         common_equity, retained_earnings, total_shareholders_equity,
 *         total_liabilities_equity, balance_check
 */
export interface BalanceSheet {
  years: string[];
  // Assets
  cash: number[];
  accountsReceivable: number[];
  inventories: number[];
  otherShortTermInvestments: number[];        // Short-term investments (< 1 year)
  otherCurrentAssets: number[];               // Prepaid expenses, deferred tax assets (current), etc.
  nonCurrentMarketableSecurities: number[];   // Long-term bond portfolio
  otherNonCurrentAssets: number[];            // Goodwill, intangibles, long-term deposits, etc.
  nonCurrentDeferredAssets: number[];         // Long-term deferred charges, prepaid expenses
  totalCurrentAssets: number[];
  ppeGross: number[];
  accumulatedDepreciation: number[];
  ppeNet: number[];
  investmentsAndAdvances: number[];           // Long-term equity investments, joint ventures
  totalAssets: number[];
  // Liabilities
  accountsPayable: number[];
  currentAccruedExpenses: number[];           // Accrued expenses (component of other CL)
  currentDeferredLiabilities: number[];       // Deferred revenue (component of other CL)
  otherCurrentLiabilities: number[];          // Accrued Expenses + Deferred Revenue combined
  currentDebt: number[];
  revolvingCredit: number[];
  totalCurrentLiabilities: number[];
  tradeAndOtherPayablesNonCurrent: number[];  // Non-current operating payables
  deferredTaxLiabilities: number[];           // Net DTA/DTL position
  otherNonCurrentLiabilities: number[];       // Other non-current liabilities beyond LT debt & DTL
  longTermDebt: number[];
  totalLiabilities: number[];
  // Equity
  commonStock: number[];                      // Par value of issued shares
  commonEquity: number[];
  retainedEarnings: number[];
  otherEquityAdjustments: number[];           // AOCI, treasury stock, translation adjustments
  totalShareholdersEquity: number[];
  totalLiabilitiesEquity: number[];
  // Check
  balanceCheck: number[];
}

/**
 * Interest Schedule — combines Debt Part 1 & Part 2 interest items
 * plus historical reference data. Matches backend `InterestSchedule` dataclass.
 */
export interface InterestSchedule {
  years: string[];
  ltInterestHistorical: number[];
  totalInterestExpenseHistorical: number[];
  interestIncomeHistorical: number[];
  openingCash: number[];
  cashInterestRate: number[];
  cashInterestIncome: number[];
  ltDebtBalance: number[];
  ltDebtInterestRate: number[];
  ltDebtInterestExpense: number[];
  revolvingCreditBalance: number[];
  revolvingCreditRate: number[];
  revolvingInterestExpense: number[];
  netInterestExpense: number[];
  totalInterestExpense: number[];
}

/**
 * Historical Reference Rows — display-only rows from XBRL filings.
 * Matches backend `HistoricalReferenceRows` dataclass.
 */
export interface HistoricalReferenceRows {
  years: string[];
  interestIncome: number[];
  researchDevelopment: number[];
  otherIncomeExpense: number[];
  taxPaid: number[];
  interestPaid: number[];
  shareBuybacks: number[];
  debtIssuance: number[];
  debtRepayments: number[];
  dividendsPaid: number[];
}

// ─── Step 10 Output Types (valuation schedules) ──────────────────────────

export interface UFCFSchedule {
  currentTaxUnlevered: number[];
  currentTaxLevered: number[];
  taxShield: number[];
  ebitda: number[];
  ufcfEbitdaMethod: number[];
  netIncome: number[];
  depAddBack: number[];
  deferredTaxAddBack: number[];
  interestAddBack: number[];
  taxShieldSubtract: number[];
  capexSubtract: number[];
  wcChange: number[];
  ufcfNetIncomeMethod: number[];
  reconciliation: number[];
}

export interface DCFPerpetuity {
  terminalUfcf: number;
  terminalValue: number;
  discountFactors: number[];
  adjustedCfs: number[];
  pvDiscreteCfs: number[];
  pvTerminalValue: number;
  enterpriseValue: number;
  equityValue: number;
  fairValuePerShare: number;
}

export interface DCFExitMultiple {
  terminalEbitda: number;
  terminalValue: number;
  discountFactors: number[];
  adjustedCfs: number[];
  pvDiscreteCfs: number[];
  pvTerminalValue: number;
  enterpriseValue: number;
  equityValue: number;
  fairValuePerShare: number;
}

/**
 * WACC Calculation output
 */
export interface WaccCalculation {
  wacc: number;
  avgUnleveredBeta: number;
  leveredBeta: number;
  costOfEquity: number;
  afterTaxCostOfDebt: number;
}

/**
 * Complete DCF output — building block schedules (Step 9) + valuation (Step 10).
 * Field names match backend dataclass names (camelCase of snake_case).
 */
export interface DCFOutput {
  incomeStatement: IncomeStatement;
  workingCapital: WorkingCapital;
  depreciation: DepreciationSchedule;
  taxLevered: TaxSchedule;
  taxUnlevered: TaxSchedule;
  cashFlowStatement: CashFlowStatement;
  balanceSheet: BalanceSheet;
  dcfPerpetuity: DCFPerpetuity;
  dcfExitMultiple: DCFExitMultiple;
  wacc: WaccCalculation;

  // Full-period schedules from backend (historical + forecast)
  interestSchedule?: InterestSchedule;
  historicalReferences?: HistoricalReferenceRows;
  fullWorkingCapital?: WorkingCapital;

  // Period labels
  historicalYears?: string[];
  forecastYears?: string[];
  allYears?: string[];
}

// ─── Validation ───────────────────────────────────────────────────────────

export interface ValidationWarning {
  field: string;
  message: string;
  value: number;
}

export interface ValidationResult {
  warnings: ValidationWarning[];
  missingRequired: string[];
}

/**
 * Validate DCF inputs and return warnings + missing required fields.
 * Used by Step 9 for client-side validation before display.
 */
export function validateDCFInputs(inputs: DCFInputs): ValidationResult {
  const warnings: ValidationWarning[] = [];
  const missingRequired: string[] = [];

  // Revenue growth
  inputs.revenueGrowth.forEach((v, i) => {
    if (v === undefined || v === null) missingRequired.push(`revenueGrowth[${i}]`);
  });

  // Inflation rate
  inputs.inflationRate.forEach((v, i) => {
    if (v === undefined || v === null) missingRequired.push(`inflationRate[${i}]`);
  });

  // Tax rate
  if (inputs.taxRate === undefined || inputs.taxRate === null) {
    missingRequired.push('taxRate');
  } else if (inputs.taxRate < 0 || inputs.taxRate > 0.5) {
    warnings.push({ field: 'taxRate', message: 'Tax rate outside 0-50%', value: inputs.taxRate });
  }

  // Working capital days
  if (!inputs.arDays && inputs.arDays !== 0) missingRequired.push('arDays');
  else if (inputs.arDays > 90) warnings.push({ field: 'arDays', message: 'Slow collections (>90 days)', value: inputs.arDays });

  if (!inputs.invDays && inputs.invDays !== 0) missingRequired.push('invDays');
  else if (inputs.invDays > 60) warnings.push({ field: 'invDays', message: 'Slow turnover (>60 days)', value: inputs.invDays });

  if (!inputs.apDays && inputs.apDays !== 0) missingRequired.push('apDays');
  else if (inputs.apDays > 120) warnings.push({ field: 'apDays', message: 'Very slow payments (>120 days)', value: inputs.apDays });

  // Capex
  inputs.capex.forEach((v, i) => {
    if (v === undefined || v === null) missingRequired.push(`capex[${i}]`);
  });

  // WACC
  if (!inputs.riskFreeRate && inputs.riskFreeRate !== 0) missingRequired.push('riskFreeRate');
  if (!inputs.equityRiskPremium && inputs.equityRiskPremium !== 0) missingRequired.push('equityRiskPremium');
  if (inputs.beta === undefined || inputs.beta === null) missingRequired.push('beta');
  else if (inputs.beta > 3) warnings.push({ field: 'beta', message: 'Very volatile (beta > 3)', value: inputs.beta });

  if (!inputs.costOfDebt && inputs.costOfDebt !== 0) missingRequired.push('costOfDebt');

  // Terminal value
  if (!inputs.terminalGrowthRate && inputs.terminalGrowthRate !== 0) missingRequired.push('terminalGrowthRate');
  else if (inputs.terminalGrowthRate > 0.05) warnings.push({ field: 'terminalGrowthRate', message: 'Aggressive terminal growth (>5%)', value: inputs.terminalGrowthRate });

  if (!inputs.terminalEbitdaMultiple && inputs.terminalEbitdaMultiple !== 0) missingRequired.push('terminalEbitdaMultiple');
  else if (inputs.terminalEbitdaMultiple > 20) warnings.push({ field: 'terminalEbitdaMultiple', message: 'Very high multiple (>20x)', value: inputs.terminalEbitdaMultiple });

  // Market data
  if (!inputs.currentPrice) missingRequired.push('currentPrice');
  if (!inputs.sharesOutstanding) missingRequired.push('sharesOutstanding');

  // Useful life
  if (!inputs.usefulLifeExisting) missingRequired.push('usefulLifeExisting');
  if (!inputs.usefulLifeNew) missingRequired.push('usefulLifeNew');
  if (inputs.firstYearDepreciationRate === undefined) missingRequired.push('firstYearDepreciationRate');

  return { warnings, missingRequired };
}
