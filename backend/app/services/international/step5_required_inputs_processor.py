"""Step 5: Data Retrieval Inputs - Shows required inputs that can be retrieved from APIs only"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class DataRetrievalField(BaseModel):
    """A field that can be retrieved from external APIs"""
    field_name: str
    description: str
    data_source: str  # yfinance, etc.
    is_required: bool
    api_endpoint: str  # Which API method to call
    example_response_key: str

class Step5DataRetrievalResponse(BaseModel):
    """Response showing what data needs to be retrieved from APIs"""
    ticker: str
    valuation_model: ValuationModel
    retrieval_groups: Dict[str, List[DataRetrievalField]]
    total_fields_to_retrieve: int
    retrieval_status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED
    message: str = "Click 'Retrieve Data' to fetch required inputs from external APIs"

class Step5RequiredInputsProcessor:
    """
    Step 5: Shows ONLY the inputs that can be retrieved from APIs.
    No calculations, no AI suggestions, no manual inputs.
    User clicks 'Retrieve' button to fetch data.
    """
    
    # DCF: Data that can be retrieved from yfinance
    # Based on Excel template requirements - ONLY fields retrievable from APIs
    DCF_RETRIEVABLE_INPUTS = {
        "historical_financials": [
            DataRetrievalField(
                field_name="Total Revenue",
                description="Annual revenue for past 4 years (historical)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Total Revenue"
            ),
            DataRetrievalField(
                field_name="EBITDA",
                description="Earnings Before Interest, Taxes, Depreciation and Amortization (historical)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="EBITDA"
            ),
            DataRetrievalField(
                field_name="Depreciation & Amortization",
                description="Non-cash expense for D&A (historical)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_cash_flow",
                example_response_key="Depreciation"
            ),
            DataRetrievalField(
                field_name="Capital Expenditures",
                description="Cash spent on fixed assets (historical)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_cash_flow",
                example_response_key="Capital Expenditure"
            ),
            DataRetrievalField(
                field_name="Working Capital Changes",
                description="Changes in net working capital (historical)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_cash_flow",
                example_response_key="Change In Working Capital"
            ),
            DataRetrievalField(
                field_name="Accounts Receivable",
                description="Outstanding receivables for AR Days calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Accounts Receivable"
            ),
            DataRetrievalField(
                field_name="Inventory",
                description="Inventory balance for Inventory Days calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Inventory"
            ),
            DataRetrievalField(
                field_name="Accounts Payable",
                description="Outstanding payables for AP Days calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Accounts Payable"
            ),
            DataRetrievalField(
                field_name="Cost of Goods Sold (COGS)",
                description="Direct costs of production (historical). Used for income statement and working capital (Inv/AP Days × COGS)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Cost Of Revenue"
            ),
            DataRetrievalField(
                field_name="SG&A Expenses",
                description="Selling, General & Administrative expenses (historical). Income statement line item",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Selling General And Administration"
            ),
            DataRetrievalField(
                field_name="Operating Expenses (Total)",
                description="Total operating expenses from income statement (historical). Other OpEx derived as: Total OpEx - SG&A - R&D - D&A",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="OperatingExpense / TotalOperatingExpenses"
            ),
            DataRetrievalField(
                field_name="Interest Expense",
                description="Historical interest expense. MUST be populated for ALL historical periods to prevent ghost cash on Balance Sheet",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Interest Expense"
            ),
            DataRetrievalField(
                field_name="Interest Income",
                description="Interest earned on cash and marketable securities (historical). Must be tracked separately from Other Income/Expense to prevent double-counting.",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Interest Income"
            ),
            DataRetrievalField(
                field_name="Other Income/Expense",
                description="Non-operating items ONLY (FX gains/losses, equity investment adjustments, legal settlements). MUST NOT include Interest Income or Interest Expense (already tracked separately). If your API pulled the consolidated SEC line, subtract Interest Income and Interest Expense to avoid double-counting.",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Other Income/Expense"
            ),
            DataRetrievalField(
                field_name="Tax Provision",
                description="Historical tax provision for effective tax rate calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Tax Provision"
            ),
            DataRetrievalField(
                field_name="Pre-Tax Income",
                description="Income before taxes for tax rate calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Pretax Income"
            ),
            DataRetrievalField(
                field_name="Net Income",
                description="Bottom-line net income (historical). Used for Retained Earnings roll (RE = Prior RE + NI - Dividends) and cross-check",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Net Income"
            ),
            DataRetrievalField(
                field_name="EBIT (Operating Income)",
                description="Earnings Before Interest and Taxes / Operating Income (historical). Used for Unlevered Tax schedule and NOPAT calculation",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Operating Income"
            ),
            DataRetrievalField(
                field_name="Gross Profit",
                description="Revenue minus COGS (historical). Used for income statement structure and margin analysis",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Gross Profit"
            ),
            DataRetrievalField(
                field_name="Deferred Tax",
                description="Deferred tax expense/benefit (historical). Used in Income Tax Schedule for deferred vs current tax split",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Deferred Income Tax"
            ),
            DataRetrievalField(
                field_name="Dividends Paid",
                description="Cash dividends paid to shareholders (historical). Used in Cash Flow Statement financing section and Retained Earnings roll",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_cash_flow",
                example_response_key="Cash Dividends Paid"
            ),
            DataRetrievalField(
                field_name="Change in Long-Term Debt",
                description="Net change in long-term debt (historical). Used in Cash Flow Statement financing section. Derived: LTD_current - LTD_prior",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Long Term Debt (current - prior year)"
            ),
            DataRetrievalField(
                field_name="Change in Common Equity",
                description="Net change in common equity (historical). Used in Cash Flow Statement financing section. Derived: Equity_current - Equity_prior",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Stockholders Equity (current - prior year)"
            ),
            DataRetrievalField(
                field_name="Change in Revolving Credit Line",
                description="Net change in revolving credit / short-term borrowings (historical). Used in Cash Flow Statement financing section",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Other Short Term Debt / Capital Debt (current - prior year)"
            ),
            DataRetrievalField(
                field_name="Share Buybacks / Repurchases",
                description="Cash paid to repurchase shares (historical). Used in Cash Flow Statement financing section and share count projections.",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_cash_flow",
                example_response_key="Repurchase Of Capital Stock"
            )
        ],
        "market_data": [
            DataRetrievalField(
                field_name="Current Stock Price",
                description="Latest market price",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="currentPrice"
            ),
            DataRetrievalField(
                field_name="Shares Outstanding",
                description="Number of shares outstanding",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="sharesOutstanding"
            ),
            DataRetrievalField(
                field_name="Beta",
                description="Stock beta vs market (5-year monthly)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="beta"
            ),
            DataRetrievalField(
                field_name="Total Debt",
                description="Short-term + Long-term debt",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Debt"
            ),
            DataRetrievalField(
                field_name="Cash & Equivalents",
                description="Cash and short-term investments",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_balance_sheet",
                example_response_key="Cash And Cash Equivalents"
            ),
            DataRetrievalField(
                field_name="Market Cap",
                description="Current market capitalization",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_company_info",
                example_response_key="marketCap"
            )
        ],
        "balance_sheet_opening": [
            DataRetrievalField(
                field_name="Net Debt",
                description="Calculated as Total Debt - Cash (can derive opening from prior year)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Debt, Cash And Cash Equivalents (prior year)"
            ),
            DataRetrievalField(
                field_name="PP&E (Gross)",
                description="Gross Property, Plant & Equipment for opening balance",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Gross PPE"
            ),
            DataRetrievalField(
                field_name="Accumulated Depreciation",
                description="Accumulated depreciation for PP&E net calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Accumulated Depreciation"
            ),
            DataRetrievalField(
                field_name="Deferred Tax Assets",
                description="Non-current deferred tax assets for tax basis roll schedule",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Non Current Deferred Taxes Assets"
            ),
            DataRetrievalField(
                field_name="Tax Loss Carryforwards",
                description="Operating loss carryforwards for NOL schedule (SEC EDGAR XBRL)",
                data_source="sec_edgar",
                is_required=False,
                api_endpoint="get_xbrl_companyfacts",
                example_response_key="DeferredTaxAssetsOperatingLossCarryforwards"
            ),
            DataRetrievalField(
                field_name="Tax Basis PP&E",
                description="Tax basis of Property, Plant & Equipment for tax depreciation schedule (declining balance method)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Net PPE (as proxy for tax basis)"
            ),
            DataRetrievalField(
                field_name="Long-Term Debt",
                description="Long-term debt at end of last historical year. Needed for projected Balance Sheet",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Long Term Debt"
            ),
            DataRetrievalField(
                field_name="Common Equity",
                description="Stockholders equity at end of last historical year. Needed for projected Balance Sheet",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Stockholders Equity"
            ),
            DataRetrievalField(
                field_name="Retained Earnings",
                description="Retained earnings at end of last historical year. Needed for projected Retained Earnings (RE = Prior RE + NI - Dividends)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Retained Earnings"
            ),
            DataRetrievalField(
                field_name="Cash",
                description="Cash and cash equivalents at end of last historical year. Needed as beginning balance for Cash Flow Statement",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Cash And Cash Equivalents"
            ),
            DataRetrievalField(
                field_name="PP&E (Net)",
                description="Net Property, Plant & Equipment at end of last historical year. Needed for Asset Schedule (PP&E roll: Begin + Capex - Depreciation = End)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Net PPE"
            ),
            DataRetrievalField(
                field_name="Revolving Credit Line",
                description="Short-term borrowings / revolving credit at end of last historical year. Needed for projected Balance Sheet and Cash Flow financing section",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Other Short Term Debt / Capital Debt"
            ),
            DataRetrievalField(
                field_name="Total Current Assets",
                description="Total current assets at end of last historical year. Needed for projected Balance Sheet structure",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Current Assets"
            ),
            DataRetrievalField(
                field_name="Total Current Liabilities",
                description="Total current liabilities at end of last historical year. Needed for projected Balance Sheet structure",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Current Liabilities"
            ),
            DataRetrievalField(
                field_name="Total Assets",
                description="Total assets at end of last historical year. Needed for projected Balance Sheet and DuPont asset turnover",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Assets"
            ),
            DataRetrievalField(
                field_name="Total Liabilities",
                description="Total liabilities at end of last historical year. Needed for projected Balance Sheet structure",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Liabilities Net Minority Interest"
            ),
            DataRetrievalField(
                field_name="Non-Current Marketable Securities",
                description="Long-term bond portfolio / non-current marketable securities. Critical for EV-to-Equity bridge: Equity Value = EV - Debt + Cash + ALL Securities",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Non Current Marketable Securities / Long Term Investments"
            ),
            DataRetrievalField(
                field_name="Other Current Liabilities",
                description="Accrued Expenses + Deferred Revenue (pre-paid services). Critical for accurate Change in Net Working Capital (ΔNWC) calculations",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Other Current Liabilities / Current Accrued Expenses"
            ),
            DataRetrievalField(
                field_name="Deferred Tax Liabilities",
                description="Net Deferred Tax Assets/Liabilities position. Non-cash timing differences between accounting and tax depreciation. Net DTA minus DTL.",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Net Non Current Deferred Tax Liabilities"
            ),
            DataRetrievalField(
                field_name="Current Accrued Expenses",
                description="Accrued expenses within current liabilities (e.g. accrued wages, accrued interest). Separate from Other Current Liabilities per balance sheet identity: CL = Payables + Accrued Expenses + Other CL + Current Debt + Deferred Liabilities",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="CurrentAccruedExpenses / Payables And Accrued Expenses"
            ),
            DataRetrievalField(
                field_name="Current Deferred Liabilities",
                description="Deferred revenue and other deferred items within current liabilities (pre-paid services to be recognized). Part of Current Liabilities identity: CL = Payables + Accrued Expenses + Other CL + Current Debt + Deferred Liabilities",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="CurrentDeferredRevenue / Deferred Revenue Current"
            ),
            DataRetrievalField(
                field_name="Trade and Other Payables Non Current",
                description="Non-current portion of trade payables and other long-term payables. Part of Non-Current Liabilities identity: NCL = LT Debt + Trade Payables NC + Other NC Liabilities",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="NonCurrentPayables / Non Current Payables"
            ),
            DataRetrievalField(
                field_name="Other Non Current Liabilities",
                description="All other non-current liabilities not classified as long-term debt or deferred taxes. Part of Non-Current Liabilities identity: NCL = LT Debt + Trade Payables NC + Other NC Liabilities",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="OtherNonCurrentLiabilities / Other Non Current Liabilities"
            ),
            DataRetrievalField(
                field_name="Other Short Term Investments",
                description="Short-term investments excluding cash equivalents (e.g. money market funds, T-bills, available-for-sale securities). Part of Current Assets identity: CA = Cash + ST Investments + Receivables + Inventory + Other CA",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="OtherShortTermInvestments / Available For Sale Securities"
            ),
            DataRetrievalField(
                field_name="Other Current Assets",
                description="Current assets not classified as cash, receivables, or inventory (e.g. prepaid expenses, deferred tax assets current). Part of Current Assets identity: CA = Cash + ST Investments + Receivables + Inventory + Other CA",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="OtherCurrentAssets / Other Current Assets"
            ),
            DataRetrievalField(
                field_name="Other Non Current Assets",
                description="Non-current assets not classified as PP&E, investments, or deferred taxes (e.g. goodwill, intangibles, long-term prepaids). Part of Non-Current Assets identity: NCA = Net PPE + Accum Dep + Investments + Other NCA + Deferred Assets",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="OtherNonCurrentAssets / Other Non Current Assets"
            ),
            DataRetrievalField(
                field_name="Common Stock",
                description="Par value of common stock issued. Part of Equity identity: Total Equity = Common Stock + Retained Earnings + Other Equity Adjustments",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="CommonStockEquity / Common Stock Equity"
            ),
            DataRetrievalField(
                field_name="Other Equity Adjustments",
                description="Accumulated Other Comprehensive Income (AOCI), treasury stock, and other equity adjustments. Calculated as: Total Equity - Common Stock - Retained Earnings. Part of Equity identity: Total Equity = Common Stock + RE + Other Equity",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Calculated: Total Equity - Common Stock - Retained Earnings"
            )
        ],
        "peer_comparables_for_wacc": [
            DataRetrievalField(
                field_name="Peer Market Caps",
                description="Market caps for 5 comparable companies (for WACC beta calculation)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_company_info",
                example_response_key="marketCap (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Betas",
                description="Levered betas for 5 comparable companies",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_company_info",
                example_response_key="beta (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Total Debt",
                description="Total debt for 5 comparable companies",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Debt (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Cash",
                description="Cash positions for 5 comparable companies",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Cash And Cash Equivalents (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Tax Rates",
                description="Effective tax rates for 5 comparable companies (calculated from Tax Provision / Pre-Tax Income)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Tax Provision, Pretax Income (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Company Names",
                description="Company names for 5 comparable companies (for identification and display in WACC peer table)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_company_info",
                example_response_key="longName / shortName (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Country",
                description="Country of incorporation for 5 comparable companies (needed for per-peer country risk premium in WACC calculation)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_company_info",
                example_response_key="country (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer EBITDA",
                description="EBITDA for 5 comparable companies (needed for relative valuation cross-check and peer comparison)",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="EBITDA (for each peer)"
            )
        ]
    }
    
    # DuPont: Data that can be retrieved from yfinance (18 total fields)
    DUPONT_RETRIEVABLE_INPUTS = {
        "income_statement": [
            DataRetrievalField(
                field_name="Net Income",
                description="Bottom line earnings (historical 4 years)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Net Income"
            ),
            DataRetrievalField(
                field_name="Total Revenue",
                description="Top line sales (historical 4 years)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Total Revenue"
            ),
            DataRetrievalField(
                field_name="Operating Income (EBIT)",
                description="Income from operations (historical 4 years)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Operating Income"
            ),
            DataRetrievalField(
                field_name="Interest Expense",
                description="Historical interest expense for interest burden calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Interest Expense"
            ),
            DataRetrievalField(
                field_name="Tax Provision",
                description="Historical tax provision for tax burden calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Tax Provision"
            ),
            DataRetrievalField(
                field_name="Pre-Tax Income",
                description="Income before taxes for tax burden calculation",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Pretax Income"
            )
        ],
        "balance_sheet": [
            DataRetrievalField(
                field_name="Total Assets",
                description="Sum of all assets (current and prior year for average)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Assets"
            ),
            DataRetrievalField(
                field_name="Shareholders Equity",
                description="Book value of equity (current and prior year for average)",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_balance_sheet",
                example_response_key="Stockholders Equity"
            ),
            DataRetrievalField(
                field_name="Total Liabilities",
                description="Sum of all liabilities",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Liabilities Net Minority Interest"
            ),
            DataRetrievalField(
                field_name="Long-Term Debt",
                description="Long-term debt for leverage analysis",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Long Term Debt"
            ),
            DataRetrievalField(
                field_name="Short-Term Debt",
                description="Short-term debt for leverage analysis",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Short Term Debt"
            ),
            DataRetrievalField(
                field_name="Cash & Equivalents",
                description="Cash and short-term investments",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Cash And Cash Equivalents"
            )
        ],
        "derived_components": [
            DataRetrievalField(
                field_name="Average Total Assets",
                description="Calculated as (Current Year Assets + Prior Year Assets) / 2",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Assets (current and prior year)"
            ),
            DataRetrievalField(
                field_name="Average Shareholders Equity",
                description="Calculated as (Current Year Equity + Prior Year Equity) / 2",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_balance_sheet",
                example_response_key="Stockholders Equity (current and prior year)"
            ),
            DataRetrievalField(
                field_name="Cost of Goods Sold (COGS)",
                description="Direct costs for margin analysis if available",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Cost Of Revenue"
            ),
            DataRetrievalField(
                field_name="SG&A Expenses",
                description="Selling, general & administrative expenses",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Selling General And Administrative"
            ),
            DataRetrievalField(
                field_name="Research & Development (R&D)",
                description="R&D expenses for operating analysis",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Research And Development"
            ),
            DataRetrievalField(
                field_name="Other Operating Expenses",
                description="Other operating expenses for detailed margin breakdown",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Other Operating Expenses"
            )
        ]
    }
    
    # Comps: Data that can be retrieved from yfinance (including peers)
    COMPS_RETRIEVABLE_INPUTS = {
        "target_company": [
            DataRetrievalField(
                field_name="Current Stock Price",
                description="Latest market price",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="currentPrice"
            ),
            DataRetrievalField(
                field_name="EPS (TTM)",
                description="Trailing twelve months earnings per share",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="trailingEps"
            ),
            DataRetrievalField(
                field_name="Market Cap",
                description="Current market capitalization",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="marketCap"
            ),
            DataRetrievalField(
                field_name="Enterprise Value",
                description="Market cap + debt - cash",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="enterpriseValue"
            ),
            DataRetrievalField(
                field_name="EBITDA (TTM)",
                description="Trailing EBITDA",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="ebitda"
            ),
            DataRetrievalField(
                field_name="Book Value",
                description="Shareholders equity per share",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="bookValue"
            ),
            DataRetrievalField(
                field_name="Revenue (TTM)",
                description="Trailing twelve months revenue",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="totalRevenue"
            )
        ],
        "peer_companies": [
            DataRetrievalField(
                field_name="Peer Stock Prices",
                description="Current prices for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="currentPrice (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer EPS",
                description="EPS for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="trailingEps (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Market Caps",
                description="Market caps for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="marketCap (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Enterprise Values",
                description="EV for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="enterpriseValue (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer EBITDA",
                description="EBITDA for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="ebitda (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Book Values",
                description="Book value for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="bookValue (for each peer)"
            ),
            DataRetrievalField(
                field_name="Peer Revenues",
                description="Revenue for all selected peers",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_company_info",
                example_response_key="totalRevenue (for each peer)"
            )
        ]
    }
    
    def process_data_retrieval_inputs(
        self,
        ticker: str,
        valuation_model: str,
        peer_tickers: Optional[List[str]] = None
    ) -> Step5DataRetrievalResponse:
        """
        Returns the list of inputs that need to be retrieved from APIs.
        No calculations performed here - purely showing what will be fetched.
        """
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return self._build_dcf_retrieval_response(ticker, peer_tickers or [])
        elif model_enum == ValuationModel.DUPONT:
            return self._build_dupont_retrieval_response(ticker)
        elif model_enum == ValuationModel.COMPS:
            return self._build_comps_retrieval_response(ticker, peer_tickers or [])
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    def _build_dcf_retrieval_response(self, ticker: str, peer_tickers: List[str]) -> Step5DataRetrievalResponse:
        """Build DCF data retrieval response"""
        # Count base fields
        total_fields = sum(len(fields) for fields in self.DCF_RETRIEVABLE_INPUTS.values())
        
        # Add note about peer count for WACC calculation
        message = f"Ready to retrieve {total_fields} data points from yfinance for DCF analysis"
        if peer_tickers:
            message += f" (including {len(peer_tickers)} peers for WACC beta calculation)"
        else:
            message += ". Note: Peer companies recommended for accurate WACC calculation."
        
        return Step5DataRetrievalResponse(
            ticker=ticker,
            valuation_model=ValuationModel.DCF,
            retrieval_groups=self.DCF_RETRIEVABLE_INPUTS,
            total_fields_to_retrieve=total_fields,
            retrieval_status="PENDING",
            message=message
        )
    
    def _build_dupont_retrieval_response(self, ticker: str) -> Step5DataRetrievalResponse:
        """Build DuPont data retrieval response"""
        total_fields = sum(len(fields) for fields in self.DUPONT_RETRIEVABLE_INPUTS.values())
        
        return Step5DataRetrievalResponse(
            ticker=ticker,
            valuation_model=ValuationModel.DUPONT,
            retrieval_groups=self.DUPONT_RETRIEVABLE_INPUTS,
            total_fields_to_retrieve=total_fields,
            retrieval_status="PENDING",
            message=f"Ready to retrieve {total_fields} data points from yfinance for DuPont analysis"
        )
    
    def _build_comps_retrieval_response(self, ticker: str, peer_tickers: List[str]) -> Step5DataRetrievalResponse:
        """Build Comps data retrieval response"""
        total_fields = sum(len(fields) for fields in self.COMPS_RETRIEVABLE_INPUTS.values())
        
        # Add note about peer count
        if peer_tickers:
            message = f"Ready to retrieve data for {ticker} and {len(peer_tickers)} peers ({total_fields} total data points)"
        else:
            message = "Warning: No peer tickers provided. Please select comparable companies before retrieving data."
        
        return Step5DataRetrievalResponse(
            ticker=ticker,
            valuation_model=ValuationModel.COMPS,
            retrieval_groups=self.COMPS_RETRIEVABLE_INPUTS,
            total_fields_to_retrieve=total_fields,
            retrieval_status="PENDING" if peer_tickers else "BLOCKED",
            message=message
        )
