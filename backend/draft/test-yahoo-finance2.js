const yahooFinance = require('yahoo-finance2');

async function testYahooFinance() {
  console.log('🧪 Testing yahoo-finance2 package...\n');
  
  try {
    // Test quote data - using named export
    console.log('📊 Fetching quote for AAPL...');
    const quote = await yahooFinance.default.quote('AAPL');
    console.log('✅ Quote fetched successfully!');
    console.log(`   Company: ${quote.longName}`);
    console.log(`   Price: $${quote.regularMarketPrice?.toFixed(2)}`);
    console.log(`   Market Cap: $${(quote.marketCap / 1e9).toFixed(2)}B`);
    console.log(`   Beta: ${quote.beta?.toFixed(2)}`);
    
    console.log('\n✅ yahoo-finance2 test passed!');
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testYahooFinance();
