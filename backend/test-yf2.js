const yahooFinance = require('yahoo-finance2');

async function testYahooFinance() {
  console.log('🧪 Testing yahoo-finance2 package (v2.11.3)...\n');
  console.log('Module type:', typeof yahooFinance);
  console.log('Module keys:', Object.keys(yahooFinance));
  
  try {
    // Try using default property
    const yf = yahooFinance.default || yahooFinance;
    console.log('\nyf type:', typeof yf);
    console.log('yf keys:', Object.keys(yf).slice(0, 20));
    
    // Test quote data
    console.log('\n📊 Fetching quote for AAPL...');
    const quote = await yf.quote('AAPL');
    console.log('✅ Quote fetched successfully!');
    console.log(`   Company: ${quote.longName || quote.symbol}`);
    console.log(`   Price: $${quote.regularMarketPrice?.toFixed(2)}`);
    
    console.log('\n✅ yahoo-finance2 test passed!');
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testYahooFinance();
