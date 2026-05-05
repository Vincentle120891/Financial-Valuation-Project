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

class Step5AssumptionsProcessor:
    """
    Step 5: Shows ONLY the inputs that can be retrieved from APIs.
    No calculations, no AI suggestions, no manual inputs.
    User clicks 'Retrieve' button to fetch data.
    """
    
    # DCF: Data that can be retrieved from yfinance
    DCF_RETRIEVABLE_INPUTS = {
        "historical_financials": [
            DataRetrievalField(
                field_name="Total Revenue",
                description="Annual revenue for past 3-5 years",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Total Revenue"
            ),
            DataRetrievalField(
                field_name="EBITDA",
                description="Earnings Before Interest, Taxes, Depreciation and Amortization",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="EBITDA"
            ),
            DataRetrievalField(
                field_name="Depreciation & Amortization",
                description="Non-cash expense for D&A",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_cash_flow",
                example_response_key="Depreciation"
            ),
            DataRetrievalField(
                field_name="Capital Expenditures",
                description="Cash spent on fixed assets",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_cash_flow",
                example_response_key="Capital Expenditure"
            ),
            DataRetrievalField(
                field_name="Working Capital Changes",
                description="Changes in net working capital",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_cash_flow",
                example_response_key="Change In Working Capital"
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
                description="Stock beta vs market",
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
        ]
    }
    
    # DuPont: Data that can be retrieved from yfinance
    DUPONT_RETRIEVABLE_INPUTS = {
        "income_statement": [
            DataRetrievalField(
                field_name="Net Income",
                description="Bottom line earnings",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Net Income"
            ),
            DataRetrievalField(
                field_name="Total Revenue",
                description="Top line sales",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_financials",
                example_response_key="Total Revenue"
            ),
            DataRetrievalField(
                field_name="Operating Income",
                description="Income from operations",
                data_source="yfinance",
                is_required=False,
                api_endpoint="get_financials",
                example_response_key="Operating Income"
            )
        ],
        "balance_sheet": [
            DataRetrievalField(
                field_name="Total Assets",
                description="Sum of all assets",
                data_source="yfinance",
                is_required=True,
                api_endpoint="get_balance_sheet",
                example_response_key="Total Assets"
            ),
            DataRetrievalField(
                field_name="Shareholders Equity",
                description="Book value of equity",
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
            return self._build_dcf_retrieval_response(ticker)
        elif model_enum == ValuationModel.DUPONT:
            return self._build_dupont_retrieval_response(ticker)
        elif model_enum == ValuationModel.COMPS:
            return self._build_comps_retrieval_response(ticker, peer_tickers or [])
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    def _build_dcf_retrieval_response(self, ticker: str) -> Step5DataRetrievalResponse:
        """Build DCF data retrieval response"""
        total_fields = sum(len(fields) for fields in self.DCF_RETRIEVABLE_INPUTS.values())
        
        return Step5DataRetrievalResponse(
            ticker=ticker,
            valuation_model=ValuationModel.DCF,
            retrieval_groups=self.DCF_RETRIEVABLE_INPUTS,
            total_fields_to_retrieve=total_fields,
            retrieval_status="PENDING",
            message=f"Ready to retrieve {total_fields} data points from yfinance for DCF analysis"
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
