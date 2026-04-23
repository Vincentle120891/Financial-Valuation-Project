const vp = require('./vietnam-data-provider.js');

async function testVFS() {
  console.log('🚀 Complete VFS (VinFast) Test\n');
  
  const data = await vp.fetchVietnamStockData('VFS');
  
  if (!data || !data.financials) {
    console.log('❌ No data returned');
    return;
  }
  
  console.log('✅ Data Retrieved Successfully!');
  console.log('\n📊 Company Info:');
  console.log('   Name:', data.company_name);
  console.log('   Exchange:', data.exchange);
  console.log('   Sector:', data.sector);
  console.log('   Currency:', data.currency);
  
  const years = data.financials.years;
  console.log('\n📅 Data Coverage:', years.length, 'years');
  console.log('   Years:', years.join(', '));
  
  const lastIdx = years.length - 1;
  console.log('\n💰 Latest Financials (' + years[lastIdx] + '):');
  console.log('   Revenue:', (data.financials.revenue[lastIdx] / 1e9).toFixed(2) + 'B VND');
  console.log('   Gross Profit:', (data.financials.gross_profit[lastIdx] / 1e9).toFixed(2) + 'B VND');
  console.log('   EBITDA:', (data.financials.ebitda[lastIdx] / 1e9).toFixed(2) + 'B VND');
  console.log('   Net Income:', (data.financials.net_income[lastIdx] / 1e9).toFixed(2) + 'B VND');
  console.log('   Total Assets:', (data.financials.total_assets[lastIdx] / 1e9).toFixed(2) + 'B VND');
  console.log('   Total Equity:', (data.financials.total_equity[lastIdx] / 1e9).toFixed(2) + 'B VND');
  
  console.log('\n🔍 Data Quality Check:');
  const hasData = data.financials.revenue.every(v => v !== null && v !== undefined);
  console.log(hasData ? '✅ All data points present' : '⚠️ Some missing values');
  
  if (years.length >= 6) {
    console.log('\n🧮 DuPont Analysis Ready:');
    console.log('   Years available:', years.length);
    console.log('   Status: Ready for DCF/DuPont modeling');
  }
  
  console.log('\nℹ️ Note: VFS listed on NASDAQ in Aug 2023 via SPAC.');
  console.log('   Historical Vietnam data limited as it was privately held.');
  console.log('   Using mock data generator for demonstration.');
}

testVFS();
