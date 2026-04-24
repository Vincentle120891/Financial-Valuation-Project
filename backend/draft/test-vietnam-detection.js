// Test Vietnam Ticker Detection Logic
function isVietnamTicker(ticker) {
  if (!ticker || typeof ticker !== 'string') return false;
  const upperTicker = ticker.toUpperCase().trim();
  const vietnamPattern = /^[A-Z]{3}$/;
  const vietnamPrefixes = ['V', 'H', 'G', 'S', 'D', 'N', 'P', 'T', 'M', 'F', 'K'];
  
  if (vietnamPattern.test(upperTicker)) {
    const usTickers = ['V', 'MA', 'WMT', 'DIS', 'NFLX', 'AMD', 'INTC', 'IBM', 'CRM', 'ORCL', 'BA', 'CAT', 'GE', 'GM', 'T', 'VZ', 'KO', 'PEP', 'MCD', 'SBUX', 'NKE', 'HD', 'LOW', 'TGT', 'COST', 'CVS', 'WBA', 'MRK', 'PFE', 'JNJ', 'UNH', 'ABBV', 'LLY', 'BMY', 'AMGN', 'GILD', 'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'VLO', 'PSX', 'NEE', 'DUK', 'SO', 'D', 'EXC', 'SRE', 'AEP', 'XEL', 'ED', 'ES', 'FE', 'ETR', 'WEC', 'PEG', 'SYY', 'ADM', 'BG', 'TSN', 'HRL', 'GIS', 'CAG', 'SJM', 'CPB', 'HSY', 'MKC', 'CL', 'PG', 'EL', 'AVP', 'CHD', 'CLX', 'TAP', 'STZ', 'SAM', 'BREW', 'COKE', 'MNST', 'F', 'K'];
    if (usTickers.includes(upperTicker)) return false;
    if (vietnamPrefixes.includes(upperTicker[0])) return true;
    return true;
  }
  return false;
}

const testCases = [
  { ticker: 'VNM', expected: true, desc: 'Vinamilk (Vietnam)' },
  { ticker: 'VIC', expected: true, desc: 'Vingroup (Vietnam)' },
  { ticker: 'HPG', expected: true, desc: 'Hoa Phat (Vietnam)' },
  { ticker: 'FPT', expected: true, desc: 'FPT Corp (Vietnam)' },
  { ticker: 'VFS', expected: true, desc: 'VinFast (Vietnam format)' },
  { ticker: 'MWG', expected: true, desc: 'Mobile World (Vietnam)' },
  { ticker: 'SAB', expected: true, desc: 'Sabeco (Vietnam)' },
  { ticker: 'TCB', expected: true, desc: 'Techcombank (Vietnam)' },
  { ticker: 'AAPL', expected: false, desc: 'Apple (US)' },
  { ticker: 'MSFT', expected: false, desc: 'Microsoft (US)' },
  { ticker: 'TSLA', expected: false, desc: 'Tesla (US)' },
  { ticker: 'V', expected: false, desc: 'Visa (US)' },
  { ticker: 'MA', expected: false, desc: 'Mastercard (US)' },
  { ticker: 'GOOGL', expected: false, desc: 'Alphabet (US - 4 letters)' },
  { ticker: 'AMZN', expected: false, desc: 'Amazon (US - 4 letters)' },
  { ticker: 'NVDA', expected: false, desc: 'NVIDIA (US - 4 letters)' }
];

console.log('🇻🇳 Vietnam Ticker Detection Test\n');
let passed = 0;
testCases.forEach(({ ticker, expected, desc }) => {
  const result = isVietnamTicker(ticker);
  const status = result === expected ? '✅' : '❌';
  if (result === expected) passed++;
  console.log(`${status} ${ticker.padEnd(6)}: ${String(result).padEnd(5)} (Expected: ${String(expected).padEnd(5)}) - ${desc}`);
});

console.log(`\n${passed}/${testCases.length} tests passed`);
if (passed === testCases.length) {
  console.log('\n✅ All tests passed! Vietnam ticker detection is working correctly.');
} else {
  console.log('\n❌ Some tests failed. Please review the detection logic.');
}
