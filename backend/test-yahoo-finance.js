const yahooFinance = require('yahoo-finance');

async function testYahooFinance() {
  console.log('🧪 Testing yahoo-finance package...\n');
  
  try {
    // Test quote data
    console.log('📊 Fetching quote for AAPL...');
    const quote = await yahooFinance.quote('AAPL');
    console.log('✅ Quote fetched successfully!');
    console.log(`   Company: ${quote.longName || quote.symbol}`);
    console.log(`   Price: $${quote.regularMarketPrice?.toFixed(2) || quote.previousClose?.toFixed(2)}`);
    console.log(`   Market Cap: $${((quote.marketCap || 0) / 1e9).toFixed(2)}B`);
    
    console.log('\n✅ yahoo-finance test passed!');
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testYahooFinance();
