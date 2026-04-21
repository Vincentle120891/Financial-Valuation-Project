const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// In-memory state storage (in production, use a database)
let valuationState = {};

// Mock data for demonstration
const mockTickerSearch = {
  'AAPL': { ticker: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
  'TSLA': { ticker: 'TSLA', name: 'Tesla, Inc.', exchange: 'NASDAQ' },
  'MSFT': { ticker: 'MSFT', name: 'Microsoft Corporation', exchange: 'NASDAQ' },
  'GOOGL': { ticker: 'GOOGL', name: 'Alphabet Inc.', exchange: 'NASDAQ' },
  'AMZN': { ticker: 'AMZN', name: 'Amazon.com, Inc.', exchange: 'NASDAQ' }
};

const valuationModels = [
  { id: 'DCF', name: 'Discounted Cash Flow', description: 'Intrinsic value based on projected free cash flows' },
  { id: 'COMPS', name: 'Trading Comps', description: 'Relative valuation using peer company multiples' },
  { id: 'DUPONT', name: 'DuPont Analysis', description: 'ROE decomposition into profit margin, asset turnover, and leverage' },
  { id: 'REALESTATE', name: 'Real Estate', description: 'Property valuation using NOI and cap rates' }
];

const modelRequiredFields = {
  DCF: [
    { name: 'revenue', status: 'pending' },
    { name: 'operatingMargin', status: 'pending' },
    { name: 'taxRate', status: 'pending' },
    { name: 'capex', status: 'pending' },
    { name: 'depreciation', status: 'pending' },
    { name: 'workingCapitalChange', status: 'pending' },
    { name: 'wacc', status: 'pending' },
    { name: 'terminalGrowthRate', status: 'pending' },
    { name: 'sharesOutstanding', status: 'pending' }
  ],
  COMPS: [
    { name: 'peRatio', status: 'pending' },
    { name: 'evEbitda', status: 'pending' },
    { name: 'priceToBook', status: 'pending' },
    { name: 'evSales', status: 'pending' },
    { name: 'peerMultiples', status: 'pending' }
  ],
  DUPONT: [
    { name: 'netIncome', status: 'pending' },
    { name: 'revenue', status: 'pending' },
    { name: 'totalAssets', status: 'pending' },
    { name: 'shareholderEquity', status: 'pending' },
    { name: 'profitMargin', status: 'pending' },
    { name: 'assetTurnover', status: 'pending' },
    { name: 'equityMultiplier', status: 'pending' }
  ],
  REALESTATE: [
    { name: 'noi', status: 'pending' },
    { name: 'capRate', status: 'pending' },
    { name: 'propertyValue', status: 'pending' },
    { name: 'occupancyRate', status: 'pending' }
  ]
};

const benchmarkRanges = {
  wacc: { min: 6.0, max: 12.0, median: 8.5, source: 'Damodaran Sector WACC' },
  terminalGrowthRate: { min: 1.5, max: 3.5, median: 2.5, source: 'Long-term GDP Growth' },
  operatingMargin: { min: 15.0, max: 30.0, median: 22.0, source: 'Sector Peer Analysis' },
  peRatio: { min: 15.0, max: 35.0, median: 22.0, source: 'S&P 500 Historical' },
  evEbitda: { min: 8.0, max: 18.0, median: 12.0, source: 'Industry Benchmarks' }
};

// API Routes

// Step 2: Search tickers
app.get('/api/search', (req, res) => {
  const query = req.query.q?.toUpperCase() || '';
  
  // Simulate API search
  const results = Object.values(mockTickerSearch)
    .filter(item => 
      item.ticker.includes(query) || 
      item.name.toUpperCase().includes(query)
    )
    .slice(0, 5);
  
  if (results.length === 0) {
    return res.json({ success: true, data: [], message: 'No results found' });
  }
  
  res.json({ success: true, data: results });
});

// Step 3: Select company
app.post('/api/select-company', (req, res) => {
  const { ticker, companyName, exchange } = req.body;
  
  valuationState = {
    ...valuationState,
    ticker,
    companyName,
    exchange,
    selectedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: `Selected: ${companyName} (${ticker})`,
    state: valuationState
  });
});

// Step 4: Get available models
app.get('/api/models', (req, res) => {
  res.json({ success: true, data: valuationModels });
});

// Step 4: Select model
app.post('/api/select-model', (req, res) => {
  const { modelType } = req.body;
  
  valuationState = {
    ...valuationState,
    modelType,
    selectedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: `Model selected: ${modelType}`,
    state: valuationState
  });
});

// Step 5: Get required fields for selected model
app.get('/api/required-fields', (req, res) => {
  const modelType = req.query.model || valuationState.modelType;
  
  if (!modelType || !modelRequiredFields[modelType]) {
    return res.status(400).json({ 
      success: false, 
      error: 'Invalid or missing model type' 
    });
  }
  
  res.json({ 
    success: true, 
    data: modelRequiredFields[modelType],
    modelType
  });
});

// Step 6: Retrieve live data (simulated)
app.post('/api/retrieve-data', async (req, res) => {
  const { modelType } = req.body;
  
  // Simulate API retrieval delay
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  // Mock retrieved data
  const retrievedData = {
    revenue: { value: 394328000000, source: 'yfinance', status: 'found' },
    operatingMargin: { value: 0.297, source: 'yfinance', status: 'found' },
    taxRate: { value: 0.145, source: 'calculated', status: 'found' },
    capex: { value: -10959000000, source: 'yfinance', status: 'found' },
    depreciation: { value: 11519000000, source: 'yfinance', status: 'found' },
    workingCapitalChange: { value: -1688000000, source: 'calculated', status: 'found' },
    wacc: { value: 0.089, source: 'calculated', status: 'found' },
    terminalGrowthRate: { value: 0.025, source: 'default', status: 'estimated' },
    sharesOutstanding: { value: 15552752000, source: 'yfinance', status: 'found' },
    currentPrice: { value: 189.84, source: 'yfinance', status: 'found' }
  };
  
  valuationState = {
    ...valuationState,
    apiData: retrievedData,
    dataRetrievedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    data: retrievedData,
    message: 'Data retrieved successfully'
  });
});

// Step 7: Get AI suggestions and benchmarks
app.get('/api/ai-suggestions', (req, res) => {
  const { field } = req.query;
  
  const aiSuggestions = {
    wacc: {
      apiValue: 0.089,
      aiSuggestion: 0.085,
      benchmark: benchmarkRanges.wacc,
      confidence: 0.87,
      source: 'Footnote parsing from 10-K'
    },
    terminalGrowthRate: {
      apiValue: 0.025,
      aiSuggestion: 0.025,
      benchmark: benchmarkRanges.terminalGrowthRate,
      confidence: 0.92,
      source: 'Management guidance extraction'
    },
    operatingMargin: {
      apiValue: 0.297,
      aiSuggestion: 0.285,
      benchmark: benchmarkRanges.operatingMargin,
      confidence: 0.78,
      source: 'Peer comparison analysis'
    }
  };
  
  if (field && aiSuggestions[field]) {
    res.json({ success: true, data: aiSuggestions[field] });
  } else {
    res.json({ success: true, data: aiSuggestions });
  }
});

// Step 7: Submit user-confirmed values
app.post('/api/confirm-values', (req, res) => {
  const { confirmedValues, auditLog } = req.body;
  
  valuationState = {
    ...valuationState,
    confirmedValues,
    auditLog: [...(valuationState.auditLog || []), ...auditLog],
    valuesConfirmedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: 'Values confirmed',
    state: valuationState
  });
});

// Step 8: Get scenario presets
app.get('/api/scenarios', (req, res) => {
  const scenarios = {
    best: {
      name: 'Best Case',
      description: 'Optimistic assumptions based on management guidance',
      overrides: {
        revenueGrowth: 0.15,
        operatingMargin: 0.32,
        terminalGrowthRate: 0.035
      }
    },
    base: {
      name: 'Base Case',
      description: 'Most likely scenario based on consensus estimates',
      overrides: {
        revenueGrowth: 0.08,
        operatingMargin: 0.28,
        terminalGrowthRate: 0.025
      }
    },
    worst: {
      name: 'Worst Case',
      description: 'Conservative assumptions considering downside risks',
      overrides: {
        revenueGrowth: 0.02,
        operatingMargin: 0.22,
        terminalGrowthRate: 0.015
      }
    }
  };
  
  res.json({ success: true, data: scenarios });
});

// Step 8: Select scenario
app.post('/api/select-scenario', (req, res) => {
  const { scenarioType, customOverrides } = req.body;
  
  valuationState = {
    ...valuationState,
    scenarioType,
    customOverrides: customOverrides || null,
    scenarioSelectedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    message: `Scenario selected: ${scenarioType}`,
    state: valuationState
  });
});

// Step 9: Run valuation model
app.post('/api/run-valuation', async (req, res) => {
  const { modelType, confirmedValues, scenario } = req.body;
  
  // Simulate calculation delay
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Mock valuation results
  const results = {
    primaryResult: {
      impliedSharePrice: 215.50,
      currentValue: 189.84,
      upside: 0.135,
      recommendation: 'BUY'
    },
    scenarioComparison: {
      best: { impliedSharePrice: 265.00, upside: 0.396 },
      base: { impliedSharePrice: 215.50, upside: 0.135 },
      worst: { impliedSharePrice: 165.00, upside: -0.131 }
    },
    sensitivityAnalysis: {
      waccSensitivity: [
        { wacc: 0.07, price: 245.00 },
        { wacc: 0.08, price: 228.00 },
        { wacc: 0.09, price: 215.50 },
        { wacc: 0.10, price: 205.00 },
        { wacc: 0.11, price: 195.00 }
      ],
      growthSensitivity: [
        { growth: 0.015, price: 195.00 },
        { growth: 0.020, price: 205.00 },
        { growth: 0.025, price: 215.50 },
        { growth: 0.030, price: 228.00 },
        { growth: 0.035, price: 245.00 }
      ]
    },
    auditTrail: {
      dataSources: {
        api: ['revenue', 'operatingMargin', 'sharesOutstanding'],
        ai: ['wacc', 'terminalGrowthRate'],
        benchmark: [],
        manual: []
      },
      confidenceScores: {
        overall: 0.85,
        byField: {
          wacc: 0.87,
          terminalGrowthRate: 0.92,
          operatingMargin: 0.78
        }
      },
      userOverrides: []
    }
  };
  
  valuationState = {
    ...valuationState,
    valuationResults: results,
    completedAt: new Date().toISOString()
  };
  
  res.json({ 
    success: true, 
    data: results,
    message: 'Valuation completed successfully'
  });
});

// Step 10: Get final results
app.get('/api/results', (req, res) => {
  if (!valuationState.valuationResults) {
    return res.status(404).json({ 
      success: false, 
      error: 'No valuation results found' 
    });
  }
  
  res.json({ 
    success: true, 
    data: valuationState.valuationResults,
    fullState: valuationState
  });
});

// Reset state
app.post('/api/reset', (req, res) => {
  valuationState = {};
  res.json({ success: true, message: 'State reset successfully' });
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});
