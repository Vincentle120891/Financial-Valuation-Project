/**
 * English Translations — Aligned Nested Structure
 * 
 * Translation Mask: Only UI wrappers are translated.
 * Financial data, acronyms, tickers, and calculation states stay English.
 * Financial acronyms (WACC, EBITDA, DCF, P/E, EPS, CAGR, Beta, VaR)
 * MUST remain in English uppercase in all views.
 */
export default {
  translation: {
    // Common Actions
    common: {
      loading: "Loading...",
      search: "Search",
      select: "Select",
      cancel: "Cancel",
      confirm: "Confirm",
      save: "Save",
      error: "Error",
      success: "Success",
      warning: "Warning",
      info: "Info",
      yes: "Yes",
      no: "No",
      ok: "OK",
      close: "Close",
      back: "Back",
      next: "Next",
      previous: "Previous",
      finish: "Finish",
      reset: "Reset",
      refresh: "Refresh",
      export: "Export",
      import: "Import",
      download: "Download",
      upload: "Upload",
      submit: "Submit",
      edit: "Edit",
      view: "View",
      delete: "Delete",
      fetch_data: "Fetch Data",
      retrieve_data: "Retrieve Data",
      run_valuation: "Run Valuation",
      generate_scenarios: "Generate Scenarios",
      apply: "Apply",
      remove: "Remove",
    },

    // Navigation
    nav: {
      home: "Home",
      dashboard: "Dashboard",
      valuation: "Valuation",
      stocks: "Stocks",
      portfolio: "Portfolio",
      reports: "Reports",
      settings: "Settings",
      help: "Help",
      watchlist: "Danh mục Theo dõi",
    },

    // Stock Types
    stockTypes: {
      vietnamese: "Vietnamese Company",
      international: "International Company",
      us: "US Company",
    },

    // Step Titles — Aligned with Backend Unified Schema
    steps: {
      step1: "Step 1: Company Search & Selection",
      step2: "Step 2: Market Confirmation & Market Data",
      step3: "Step 3: Valuation Method Selection",
      step4: "Step 4: Peer Company Selection",
      step5: "Step 5: Prepare Inputs/Assumptions",
      step6: "Step 6: Fetch API Data",
      step7: "Step 7: Process Historical Data",
      step8: "Step 8: Assumptions & AI Suggestion Studio",
      step9: "Step 9: Confirm Assumptions",
      step10: "Step 10: Execute Valuation",
      step11: "Step 11: Valuation Results & Analysis",
    },

    // Step Descriptions
    stepDescriptions: {
      step1: "Enter a company name or ticker symbol to fetch financial metrics and begin peer discovery.",
      step2: "Review market data and confirm the target company information.",
      step3: "Select the valuation methodology for this analysis.",
      step4: "Choose comparable peer companies for benchmarking.",
      step5: "Review and prepare required inputs for valuation models.",
      step6: "Financial data retrieved from APIs. Review accuracy before proceeding.",
      step7: "Review AI-extracted historical financial data.",
      step8: "Fine-tune revenue growth rates, margins, and other forecast drivers.",
      step9: "Confirm all assumptions before executing valuation models.",
      step10: "Execute DCF, Comparable Companies, and DuPont analysis models.",
      step11: "Comprehensive valuation output with multi-method comparison.",
    },

    // Financial Statements
    financialStatements: {
      income_statement: "Income Statement",
      balance_sheet: "Balance Sheet",
      cash_flow: "Cash Flow Statement",
      notes: "Financial Statement Notes",
      annual: "Annual",
      quarterly: "Quarterly",
      consolidated: "Consolidated",
      standalone: "Standalone",
      historical: "Historical Financial Statements",
      periods: "periods",
    },

    // Structural Financial Labels (UI wrappers — NOT data values)
    sections: {
      balance_sheet: "Balance Sheet",
      income_statement: "Income Statement",
      cash_flow_statement: "Cash Flow Statement",
      assumptions_inputs: "Assumptions / Inputs",
      growth_rate: "Growth Rate",
      discount_factor: "Discount Factor",
      revenue_drivers: "Revenue Drivers",
      cost_margins: "Cost & Margins",
      working_capital: "Working Capital",
      wacc_components: "WACC Components",
      terminal_value: "Terminal Value",
      dcf_model_inputs: "DCF Model Inputs",
      peer_comparison: "Peer Comparison Data",
      dupont_analysis: "DuPont Analysis Results",
      comps_analysis: "Comparable Companies Analysis",
      calculated_metrics: "Calculated Intermediate Metrics",
      valuation_results: "Valuation Results & Analysis",
      multi_method_summary: "Multi-Method Valuation Summary",
      historical_financials: "Historical Financials (from API)",
      forecast_drivers: "Forecast Drivers (from API)",
      extraction_methodology: "Extraction Methodology",
      key_financial_metrics: "Key Financial Metrics",
    },

    // Structural Metric Labels
    metrics: {
      revenue: "Revenue",
      cogs: "Cost of Goods Sold",
      gross_profit: "Gross Profit",
      operating_income: "Operating Income",
      net_income: "Net Income",
      total_assets: "Total Assets",
      total_liabilities: "Total Liabilities",
      equity: "Shareholders' Equity",
      cash: "Cash & Equivalents",
      debt: "Total Debt",
      accounts_receivable: "Accounts Receivable",
      inventory: "Inventory",
      accounts_payable: "Accounts Payable",
      operating_cf: "Operating Cash Flow",
      investing_cf: "Investing Cash Flow",
      financing_cf: "Financing Cash Flow",
      capex: "Capital Expenditure",
      depreciation: "Depreciation & Amortization",
      sga_opex: "SG&A / OpEx",
      free_cash_flow: "Free Cash Flow",
      shares_outstanding: "Shares Outstanding",
      risk_free_rate: "Risk-Free Rate",
      equity_risk_premium: "Equity Risk Premium",
      beta: "Beta",
      cost_of_debt: "Cost of Debt",
      terminal_growth_rate: "Terminal Growth Rate",
      terminal_ebitda_multiple: "Terminal EBITDA Multiple",
      useful_life: "Useful Life (Existing Assets)",
      avg_roe: "Avg ROE",
      roe_trend: "ROE Trend",
      latest_roe: "Latest ROE",
      revenue_cagr: "Revenue CAGR",
      avg_ebitda_margin: "Avg EBITDA Margin",
      avg_net_margin: "Avg Net Margin",
    },

    // Data Status Badges — NEVER TRANSLATED (Translation Mask Law)
    dataStatus: {
      retrieved: "RETRIEVED",
      fetched: "✓ FETCHED",
      calculated: "📊 CALCULATED",
      manual: "✏️ MANUAL",
      ai: "🤖 AI",
      missing: "⚠ MISSING",
      unknown: "? UNKNOWN",
      no_data: "No data available",
    },

    // Market & Exchange
    marketData: {
      ticker: "Ticker",
      company_name: "Company Name",
      current_price: "Current Price",
      market_cap: "Market Cap",
      change: "Change",
      change_percent: "% Change",
      volume: "Volume",
      value: "Trading Value",
      high_52w: "52-Week High",
      low_52w: "52-Week Low",
      avg_volume: "Avg Volume",
      dividend_yield: "Dividend Yield",
      sector: "Sector",
      exchange: "Exchange",
      industry: "Industry",
      market: "Market",
      region: "Region",
    },

    // Valuation Methods
    valuationMethods: {
      dcf: "DCF Engine",
      dupont: "DuPont Analysis",
      comps: "Trading Comps",
      vietnamese: "Vietnamese Model",
      international: "International Model",
    },

    // Buttons
    buttons: {
      search_company: "Search Company",
      fetch_data: "Fetch Data",
      retrieve_data: "Retrieve Data",
      continue_next: "Continue to Next Step",
      run_valuation: "Run Valuation",
      generate_scenarios: "Generate Scenarios",
      use_ai: "Use AI",
      ai_suggestion: "AI Suggestion",
      apply_suggestion: "Apply AI Suggestion",
      manual_override: "Manual Override",
      edit_inputs: "Edit",
      save_inputs: "Save",
      back_to_previous: "Back to Previous Step",
      upload_pdf: "Upload PDF Report",
      ai_web_search: "AI Web Search",
      sec_fetch: "Fetch from SEC EDGAR",
      toggle_edit_mode: "Toggle Edit Mode",
    },

    // Input Labels
    inputs: {
      search_placeholder_intl: "Enter ticker (e.g., AAPL, MSFT) or company name",
      search_placeholder_vn: "Enter ticker (e.g., VNM, VIC, HPG) or company name",
      select_market: "Select Market",
      select_model: "Select Valuation Model",
      select_peers: "Select Peer Companies",
      custom_prompt: "Custom AI Prompt",
    },

    // Messages & Notifications
    messages: {
      data_fetch_success: "Data retrieved successfully",
      data_fetch_error: "Failed to retrieve data",
      calculation_complete: "Calculation complete",
      calculation_error: "Calculation error",
      please_select_stock: "Please select a stock",
      invalid_ticker: "Invalid ticker symbol",
      loading_data: "Loading data...",
      processing: "Processing...",
      ready_to_valuate: "Ready to value",
      no_data_retrieved: "No Data Retrieved",
      no_data_description: "Unable to display inputs. Please check if data was successfully fetched from APIs.",
      please_go_back: "Please go back to Step 5 and click \"Retrieve Data\" first.",
      loading_statements: "Loading financial statements...",
      no_statements: "No financial statement data available yet. Complete earlier steps to populate this view.",
      about_step6: "This screen shows all financial data retrieved automatically from external APIs. Verify accuracy before proceeding.",
    },

    // Foreign Ownership (Vietnam)
    foreignOwnership: {
      fol: "Foreign Ownership Limit",
      fol_limit: "Foreign Ownership Limit",
      current_fol: "Current Foreign Ownership",
      fol_restricted: "Closed to Foreign Investors",
      available_fol: "Available for Foreign",
      status: "Status",
    },

    // Exchange Info
    exchangeInfo: {
      trading_hours: "Trading Hours",
      settlement: "Settlement",
      currency: "Currency",
      market_status: "Market Status",
      open: "Open",
      closed: "Closed",
    },

    // Time Periods
    timePeriods: {
      today: "Today",
      ytd: "Year to Date",
      one_month: "1 Month",
      three_months: "3 Months",
      six_months: "6 Months",
      one_year: "1 Year",
      three_years: "3 Years",
      five_years: "5 Years",
      ten_years: "10 Years",
      max: "Max",
    },

    // Table Headers
    tableHeaders: {
      ticker: "Ticker",
      company: "Company",
      sector: "Sector",
      price: "Price",
      change: "±",
      volume: "Volume",
      market_cap: "Market Cap",
      pe: "P/E",
      pb: "P/B",
      dividend_yield: "Yield",
      recommendation: "Rating",
    },

    // System Notice — Translation Mask Disclaimer
    notices: {
      translation_disclaimer: "Notice: Language translation applies to UI wrappers only. Core financial terminology, tickers, and mathematical outputs remain anchored to international reporting standards.",
    },
  },
};
