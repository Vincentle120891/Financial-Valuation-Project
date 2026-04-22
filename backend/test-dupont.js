const { performDuPontAnalysis, validateInputLength } = require('./dupont-engine');

// Test Data: 6 Years of Financial Data (2019-2024) for Vinamilk Corporation
const testInputs = {
  ticker: 'VNM',
  company_name: 'Vinamilk Corporation',
  currency: 'VND',
  unit_scaling: 'millions',
  years: ['2019', '2020', '2021', '2022', '2023', '2024'],
  
  // Income Statement
  revenue: [50000, 52000, 55000, 58000, 60000, 62000],
  cogs: [30000, 31500, 33000, 35000, 36000, 37500],
  gross_profit: [20000, 20500, 22000, 23000, 24000, 24500],
  sga: [8000, 8200, 8500, 8800, 9000, 9200],
  other_opex: [2000, 2100, 2200, 2300, 2400, 2500],
  operating_income: [7000, 7200, 7500, 7800, 8000, 8200],
  depreciation: [3000, 3100, 3200, 3300, 3400, 3500],
  interest_expense: [500, 480, 460, 440, 420, 400],
  ebt: [6500, 6720, 7040, 7360, 7580, 7800],
  tax_expense: [2500, 2600, 2750, 2900, 3000, 3100],
  net_income: [4000, 4120, 4390, 4560, 4780, 4900],
  ebitda: [10000, 10300, 10700, 11100, 11400, 11700],
  ebit: [7000, 7200, 7500, 7800, 8000, 8200],
  
  // Balance Sheet
  total_assets: [80000, 82000, 85000, 88000, 90000, 92000],
  total_equity: [45000, 46500, 48000, 49500, 51000, 52500],
  total_liabilities: [35000, 35500, 37000, 38500, 39000, 39500],
  current_assets: [25000, 26000, 27000, 28000, 29000, 30000],
  current_liabilities: [15000, 15500, 16000, 16500, 17000, 17500],
  cash_and_equivalents: [10000, 10500, 11000, 11500, 12000, 12500],
  accounts_receivable: [5000, 5200, 5400, 5600, 5800, 6000],
  inventory: [6000, 6200, 6400, 6600, 6800, 7000],
  accounts_payable: [4000, 4100, 4200, 4300, 4400, 4500],
  debt_short_term: [5000, 4800, 4600, 4400, 4200, 4000],
  debt_long_term: [10000, 9500, 9000, 8500, 8000, 7500],
  total_debt: [15000, 14300, 13600, 12900, 12200, 11500],
  
  // Cash Flow
  operating_cash_flow: [7000, 7200, 7500, 7800, 8100, 8400],
  capex: [2000, 2100, 2200, 2300, 2400, 2500],
  free_cash_flow: [5000, 5100, 5300, 5500, 5700, 5900]
};

console.log('🧪 Testing DuPont Analysis Engine...\n');

// 1. Validate Inputs (check array lengths)
console.log('1️⃣ Validating inputs...');
try {
  const requiredFields = ['revenue', 'gross_profit', 'ebitda', 'operating_income', 'net_income', 
                          'total_assets', 'total_equity', 'accounts_receivable', 'inventory', 
                          'accounts_payable', 'cogs', 'total_debt', 'current_assets', 
                          'current_liabilities', 'interest_expense'];
  
  for (const field of requiredFields) {
    if (!Array.isArray(testInputs[field])) {
      throw new Error(`${field} must be an array`);
    }
    if (testInputs[field].length < 6 || testInputs[field].length > 10) {
      throw new Error(`${field} must have 6-10 values, got ${testInputs[field].length}`);
    }
  }
  console.log('✅ Validation passed: All fields have 6-10 years of data');
  console.log(`   Years analyzed: ${testInputs.years.length}`);
} catch (error) {
  console.error('❌ Validation failed:', error.message);
  process.exit(1);
}

// 2. Run DuPont Analysis
console.log('\n2️⃣ Running DuPont analysis...');
const results = performDuPontAnalysis(testInputs);

// 3. Display Key Results
console.log('\n📊 === DUPONT ANALYSIS RESULTS ===\n');

console.log('📈 Supporting Ratios:');
console.log(`   Gross Margin:      [${results.supporting_ratios.gross_margin.map(r => r.toFixed(2) + '%').join(', ')}]`);
console.log(`   EBITDA Margin:     [${results.supporting_ratios.ebitda_margin.map(r => r.toFixed(2) + '%').join(', ')}]`);
console.log(`   Operating Margin:  [${results.supporting_ratios.operating_margin.map(r => r.toFixed(2) + '%').join(', ')}]`);
console.log(`   Net Profit Margin: [${results.supporting_ratios.net_profit_margin.map(r => r.toFixed(2) + '%').join(', ')}]`);
console.log(`   Asset Turnover:    [${results.supporting_ratios.asset_turnover.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   ROE (Direct):      [${results.supporting_ratios.roe.map(r => r.toFixed(2) + '%').join(', ')}]`);
console.log(`   ROA:               [${results.supporting_ratios.roa.map(r => r.toFixed(2) + '%').join(', ')}]`);
console.log(`   ROIC:              [${results.supporting_ratios.roic.map(r => r.toFixed(2) + '%').join(', ')}]`);

console.log('\n🔷 3-Step DuPont Analysis:');
console.log(`   Net Profit Margin: [${results.dupont_3step.net_profit_margin.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   Asset Turnover:    [${results.dupont_3step.asset_turnover.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   Equity Multiplier: [${results.dupont_3step.equity_multiplier.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   ROE Reconciled:    [${results.dupont_3step.roe_reconciled.map(r => r.toFixed(4)).join(', ')}]`);

console.log('\n🔶 5-Step DuPont Analysis:');
console.log(`   Tax Burden:        [${results.dupont_5step.tax_burden.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   Interest Burden:   [${results.dupont_5step.interest_burden.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   EBIT Margin:       [${results.dupont_5step.ebit_margin.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   Asset Turnover:    [${results.dupont_5step.asset_turnover.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   Equity Multiplier: [${results.dupont_5step.equity_multiplier.map(r => r.toFixed(3)).join(', ')}]`);
console.log(`   ROE Reconciled:    [${results.dupont_5step.roe_reconciled.map(r => r.toFixed(4)).join(', ')}]`);

console.log('\n📉 Growth Trends:');
console.log(`   Revenue Growth:    [${results.growth_trends.revenue_growth.map(r => r !== null ? r.toFixed(2) + '%' : 'N/A').join(', ')}]`);
console.log(`   EBITDA Growth:     [${results.growth_trends.ebitda_growth.map(r => r !== null ? r.toFixed(2) + '%' : 'N/A').join(', ')}]`);
console.log(`   Net Income Growth: [${results.growth_trends.net_income_growth.map(r => r !== null ? r.toFixed(2) + '%' : 'N/A').join(', ')}]`);

console.log('\n✅ Validation Checks:');
console.log(`   3-Step ROE Matches: [${results.validation.roe_3step_matches_direct.map(v => v ? '✓' : '✗').join(', ')}]`);
console.log(`   5-Step ROE Matches: [${results.validation.roe_5step_matches_direct.map(v => v ? '✓' : '✗').join(', ')}]`);

// 4. Verify all matches
const all3StepMatch = results.validation.roe_3step_matches_direct.every(v => v);
const all5StepMatch = results.validation.roe_5step_matches_direct.every(v => v);

console.log('\n🎯 Final Verification:');
if (all3StepMatch && all5StepMatch) {
  console.log('✅ ALL CALCULATIONS VERIFIED - Both 3-step and 5-step DuPont models are accurate!');
} else {
  console.log('❌ DISCREPANCIES DETECTED - Check calculations');
}

console.log('\n📋 Metadata:');
console.log(`   Years Analyzed: ${results.metadata.years_analyzed}`);
console.log(`   Currency: ${results.metadata.currency}`);
console.log(`   Unit Scaling: ${results.metadata.unit_scaling}`);
console.log('\n✨ DuPont Model Test Complete!');
