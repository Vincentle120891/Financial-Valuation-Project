"""Step 6: Data Review Layer - Pure Data Aggregation (No Final Calculations)"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

from .yfinance_service import YFinanceService

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class DataStatus(str, Enum):
    """Status of data field"""
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

class DataField(BaseModel):
    """A single data field with status tracking"""
    field_name: str
    display_name: Optional[str] = None
    value: Optional[Any] = None
    unit: str = ""
    status: DataStatus
    source: Optional[str] = None
    formula: Optional[str] = None
    is_critical: bool = False
    allow_override: bool = False

class HistoricalFinancialsDisplay(BaseModel):
    """Historical financial data display"""
    years: List[int] = []
    data_fields: List[DataField] = []

class ForecastDriversDisplay(BaseModel):
    """Forecast drivers display"""
    data_fields: List[DataField] = []

class MarketDataDisplay(BaseModel):
    """Market data display"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    beta: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash: Optional[DataField] = None
    currency: Optional[DataField] = None
    data_fields: List[DataField] = []

class CalculatedMetricsDisplay(BaseModel):
    """Calculated metrics from retrieved data (NOT final valuations)"""
    data_fields: List[DataField] = []

class MissingDataSummary(BaseModel):
    """Summary of missing data"""
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    total_missing: int = 0

class Step6DataReviewResponse(BaseModel):
    """
    Step 6 Response: Shows all retrieved inputs, missing inputs,
    and calculated intermediate metrics. NO FINAL VALUATIONS.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    forecast_drivers: Optional[ForecastDriversDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    data_complete: bool = False
    message: str = ""


class Step6DataReviewProcessor:
    """
    Step 6: Data Review Layer
    - Collects Historical Financials (Step 3)
    - Collects Market Data (Step 2)
    - Collects Forecast Drivers (Step 4)
    - Collects Assumptions (Step 5 - retrieved data only)
    - Calculates ONLY intermediate metrics that can be derived from retrieved data
    - NO WACC, NO Terminal Value, NO Enterprise Value, NO Fair Value calculations
    """

    def __init__(self):
        pass

    async def process_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        forecast_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
        valuation_model: Optional[str] = None
    ) -> Step6DataReviewResponse:
        """
        Main entry point for Step 6 data review.
        Aggregates all retrieved data without performing final calculations.

        Args can be passed directly or will be fetched if not provided.
        """
        # If data is not provided, fetch it
        if historical_data is None or market_data is None or forecast_data is None or retrieved_assumptions is None:
            # Fetch all required data
            yfinance_service = YFinanceService()
            all_data = yfinance_service.fetch_all_data(ticker, market)

            # Convert dict format to DataFrame format expected by _process_dcf_historical
            # fetch_all_data returns dicts, but the processor expects DataFrames
            import pandas as pd

            income_stmt_dict = all_data.get('income_statement', {})
            balance_sheet_dict = all_data.get('balance_sheet', {})
            cash_flow_dict = all_data.get('cash_flow', {})

            # Convert to DataFrame and transpose to match expected format (rows=metrics, cols=years)
            financials_df = pd.DataFrame(income_stmt_dict).T if income_stmt_dict else None
            balance_sheet_df = pd.DataFrame(balance_sheet_dict).T if balance_sheet_dict else None
            cashflow_df = pd.DataFrame(cash_flow_dict).T if cash_flow_dict else None

            # Convert column strings to datetime for proper year extraction
            if financials_df is not None:
                financials_df.columns = pd.to_datetime(financials_df.columns)
            if balance_sheet_df is not None:
                balance_sheet_df.columns = pd.to_datetime(balance_sheet_df.columns)
            if cashflow_df is not None:
                cashflow_df.columns = pd.to_datetime(cashflow_df.columns)

            historical_data = historical_data or {
                'financials': financials_df,
                'balance_sheet': balance_sheet_df,
                'cashflow': cashflow_df
            }
            market_data = market_data or all_data.get('key_stats', {})
            forecast_data = forecast_data or all_data.get('analyst_estimates', {})
            retrieved_assumptions = retrieved_assumptions or {}

        user_overrides = user_overrides or {}
        valuation_model = valuation_model or "DCF"
        model_enum = ValuationModel(valuation_model.upper())

        if model_enum == ValuationModel.DCF:
            return await self._process_dcf_data_review(
                ticker, historical_data, market_data, forecast_data, retrieved_assumptions, user_overrides
            )
        elif model_enum == ValuationModel.DUPONT:
            return await self._process_dupont_data_review(
                ticker, historical_data, market_data, retrieved_assumptions, user_overrides
            )
        elif model_enum == ValuationModel.COMPS:
            return await self._process_comps_data_review(
                ticker, historical_data, market_data, retrieved_assumptions, user_overrides
            )
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")

    async def _process_dcf_data_review(
        self,
        ticker: str,
        historical_data: Dict,
        market_data: Dict,
        forecast_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> Step6DataReviewResponse:
        """Process DCF data review - aggregate only, no final calculations"""

        # Process Historical Financials (11 fields)
        historical_display = self._process_dcf_historical(historical_data, user_overrides)

        # Process Market Data (6 fields)
        market_display = self._process_dcf_market_data(market_data, user_overrides)

        # Process Balance Sheet Opening Balances (3 fields)
        opening_display = self._process_dcf_opening_balances(historical_data, user_overrides)

        # Process Peer Comparables for WACC (5 fields × N peers)
        peer_display = self._process_dcf_peer_comparables(retrieved_assumptions, user_overrides)

        # Calculate ONLY intermediate metrics (growth rates, margins, etc.) - NOT WACC/TV/Fair Value
        calculated_display = self._calculate_dcf_intermediate_metrics(
            historical_display, market_display, opening_display, peer_display
        )

        # Aggregate missing data
        all_displays = [historical_display, market_display, opening_display, peer_display, calculated_display]
        missing_summary = self._aggregate_missing_data(all_displays)

        ready = len(missing_summary.critical_missing) == 0

        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            historical_financials=historical_display,
            forecast_drivers=ForecastDriversDisplay(data_fields=opening_display.data_fields + peer_display.data_fields),
            market_data=market_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            data_complete=ready,
            message="Data aggregated successfully. Ready for next steps." if ready else "Missing critical data. Please retrieve missing inputs."
        )

    async def _process_dupont_data_review(
        self,
        ticker: str,
        historical_data: Dict,
        market_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> Step6DataReviewResponse:
        """Process DuPont data review - aggregate only, no ROE calculations"""

        # Process Income Statement Data
        income_display = self._process_dupont_income_data(historical_data, user_overrides)

        # Process Balance Sheet Data
        balance_display = self._process_dupont_balance_data(historical_data, user_overrides)

        # Calculate ONLY intermediate ratios (not final ROE decomposition)
        calculated_display = self._calculate_dupont_intermediate_metrics(income_display, balance_display)

        # Aggregate missing data
        missing_summary = self._aggregate_missing_data([income_display, balance_display, calculated_display])

        ready = len(missing_summary.critical_missing) == 0

        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            historical_financials=income_display,
            forecast_drivers=ForecastDriversDisplay(data_fields=balance_display.data_fields if balance_display else []),
            market_data=MarketDataDisplay(data_fields=[]),  # Empty MarketDataDisplay for DuPont
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            data_complete=ready,
            message="Data aggregated successfully. Ready for next steps." if ready else "Missing critical data. Please retrieve missing inputs."
        )

    async def _process_comps_data_review(
        self,
        ticker: str,
        historical_data: Dict,
        market_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> Step6DataReviewResponse:
        """Process Comps data review - aggregate only, no valuation calculations"""

        # Process Target Company Data
        target_display = self._process_comps_target_data(historical_data, market_data, user_overrides)

        # Process Peer Data
        peer_display = self._process_comps_peer_data(retrieved_assumptions, user_overrides)

        # Calculate ONLY intermediate metrics (not median/mean multiples or implied valuation)
        calculated_display = self._calculate_comps_intermediate_metrics(target_display, peer_display)

        # Aggregate missing data
        missing_summary = self._aggregate_missing_data([target_display, peer_display, calculated_display])

        ready = len(missing_summary.critical_missing) == 0

        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            historical_financials=target_display,
            forecast_drivers=ForecastDriversDisplay(data_fields=peer_display.data_fields if peer_display else []),
            market_data=MarketDataDisplay(data_fields=[]),  # Empty MarketDataDisplay for Comps
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            data_complete=ready,
            message="Data aggregated successfully. Ready for next steps." if ready else "Missing critical data. Please retrieve missing inputs."
        )

    # === Helper Methods for DCF ===

    def _process_dcf_historical(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process historical financials for DCF (11 fields)"""
        years = []
        data_fields = []

        financials = historical_data.get("financials")
        cashflow = historical_data.get("cashflow")
        balance_sheet = historical_data.get("balance_sheet")

        if financials is not None:
            # Sort columns by year ascending (oldest first) for correct growth calculations
            sorted_columns = sorted(financials.columns, key=lambda x: x.year)
            
            for col in sorted_columns:
                year = int(col.year)
                if year not in years:  # Avoid duplicate years
                    years.append(year)

                # 1. Total Revenue - try multiple possible field names (snake_case from yfinance_service)
                rev_val = None
                for rev_key in ['total_revenue', 'revenue', 'Total Revenue', 'Operating Revenue', 'operating_revenue']:
                    if rev_key in financials.index:
                        rev_val = financials.loc[rev_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Revenue_{year}",
                    display_name="Total Revenue",
                    value=rev_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rev_val else DataStatus.MISSING,
                    source="yfinance" if rev_val else None,
                    is_critical=True
                ))

                # 2. EBITDA - try multiple possible field names
                ebitda_val = None
                for ebitda_key in ['ebitda', 'EBITDA', 'Normalized EBITDA', 'normalized_ebitda']:
                    if ebitda_key in financials.index:
                        ebitda_val = financials.loc[ebitda_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"EBITDA_{year}",
                    display_name="EBITDA",
                    value=ebitda_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ebitda_val else DataStatus.MISSING,
                    source="yfinance" if ebitda_val else None,
                    is_critical=True
                ))

                # 3. Depreciation & Amortization - try multiple possible field names (income stmt + cashflow)
                da_val = None
                # First try income statement (snake_case first from yfinance_service)
                if financials is not None:
                    for dep_key in ['depreciation_amortization', 'd_and_a', 'Reconciled Depreciation', 'Depreciation Amortization Depletion', 'Depreciation And Amortization']:
                        if dep_key in financials.index:
                            da_val = financials.loc[dep_key, col]
                            break
                # Then try cashflow if not found in income statement
                if da_val is None and cashflow is not None:
                    for dep_key in ['Depreciation Amortization Depletion', 'Depreciation And Amortization', 'Depreciation', 'depreciation_amortization_depletion']:
                        if dep_key in cashflow.index:
                            da_val = cashflow.loc[dep_key, col]
                            break
                data_fields.append(DataField(
                    field_name=f"Depreciation_Amortization_{year}",
                    display_name="Depreciation & Amortization",
                    value=da_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if da_val else DataStatus.MISSING,
                    source="yfinance" if da_val else None,
                    is_critical=False
                ))

                # 4. Capital Expenditures - try multiple possible field names (snake_case first)
                capex_val = None
                if cashflow is not None:
                    for capex_key in ['capital_expenditure', 'capex', 'Capital Expenditure', 'Purchase Of PPE', 'Capital Expenditure Reported']:
                        if capex_key in cashflow.index:
                            capex_val = cashflow.loc[capex_key, col] * -1  # Convert to positive
                            break
                data_fields.append(DataField(
                    field_name=f"CapEx_{year}",
                    display_name="Capital Expenditures (CapEx)",
                    value=capex_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if capex_val else DataStatus.MISSING,
                    source="yfinance" if capex_val else None,
                    is_critical=True
                ))

                # 5. Working Capital Changes - try multiple possible field names (snake_case first)
                wc_val = None
                if cashflow is not None:
                    for wc_key in ['change_in_working_capital', 'changes_in_working_capital', 'Change In Working Capital', 'Changes In Working Capital']:
                        if wc_key in cashflow.index:
                            wc_val = cashflow.loc[wc_key, col]
                            break
                data_fields.append(DataField(
                    field_name=f"Working_Capital_Change_{year}",
                    display_name="Working Capital Changes",
                    value=wc_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if wc_val else DataStatus.MISSING,
                    source="yfinance" if wc_val else None,
                    is_critical=False
                ))

                # 6. Accounts Receivable - try multiple possible field names
                ar_val = None
                if balance_sheet is not None:
                    for ar_key in ['Accounts Receivable', 'Receivables', 'Gross Accounts Receivable', 'accounts_receivable', 'ar', 'receivables']:
                        if ar_key in balance_sheet.index:
                            ar_val = balance_sheet.loc[ar_key, col]
                            break
                data_fields.append(DataField(
                    field_name=f"Accounts_Receivable_{year}",
                    display_name="Accounts Receivable",
                    value=ar_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ar_val else DataStatus.MISSING,
                    source="yfinance" if ar_val else None,
                    is_critical=False
                ))

                # 7. Inventory - try multiple possible field names
                inv_val = None
                if balance_sheet is not None:
                    for inv_key in ['Inventory', 'Inventories', 'inventory', 'inventories']:
                        if inv_key in balance_sheet.index:
                            inv_val = balance_sheet.loc[inv_key, col]
                            break
                data_fields.append(DataField(
                    field_name=f"Inventory_{year}",
                    display_name="Inventory",
                    value=inv_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if inv_val else DataStatus.MISSING,
                    source="yfinance" if inv_val else None,
                    is_critical=False
                ))

                # 8. Accounts Payable (for AP Days) - try multiple possible field names
                ap_val = None
                if balance_sheet is not None:
                    for ap_key in ['Accounts Payable', 'Payables', 'Payables And Accrued Expenses', 'accounts_payable', 'ap', 'payables']:
                        if ap_key in balance_sheet.index:
                            ap_val = balance_sheet.loc[ap_key, col]
                            break
                data_fields.append(DataField(
                    field_name=f"Accounts_Payable_{year}",
                    display_name="Accounts Payable",
                    value=ap_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ap_val else DataStatus.MISSING,
                    source="yfinance" if ap_val else None,
                    is_critical=False
                ))

                # 9. Interest Expense - try multiple possible field names (snake_case first)
                int_val = None
                for int_key in ['interest_expense', 'Interest Expense', 'Interest Expense Non Operating', 'Interest Income Net Operating', 'net_interest_income']:
                    if int_key in financials.index:
                        int_val = financials.loc[int_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Interest_Expense_{year}",
                    display_name="Interest Expense",
                    value=int_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if int_val else DataStatus.MISSING,
                    source="yfinance" if int_val else None,
                    is_critical=False
                ))

                # 10. Tax Provision (for effective tax rate) - try multiple possible field names (snake_case first)
                tax_val = None
                for tax_key in ['tax_provision', 'tax_expense', 'income_tax', 'Tax Provision', 'Income Tax', 'Tax Expense']:
                    if tax_key in financials.index:
                        tax_val = financials.loc[tax_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Tax_Provision_{year}",
                    display_name="Tax Provision",
                    value=tax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if tax_val else DataStatus.MISSING,
                    source="yfinance" if tax_val else None,
                    is_critical=False
                ))

                # 11. Pre-Tax Income (for effective tax rate) - try multiple possible field names (snake_case first)
                pretax_val = None
                for pretax_key in ['pretax_income', 'pre_tax_income', 'income_before_tax', 'Pretax Income', 'Pre Tax Income', 'Income Before Tax']:
                    if pretax_key in financials.index:
                        pretax_val = financials.loc[pretax_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Pre_Tax_Income_{year}",
                    display_name="Pre-Tax Income",
                    value=pretax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if pretax_val else DataStatus.MISSING,
                    source="yfinance" if pretax_val else None,
                    is_critical=False
                ))

                # 12. Cost of Revenue (COGS) - try multiple possible field names (snake_case first)
                cogs_val = None
                for cogs_key in ['cost_of_revenue', 'cogs', 'Cost Of Revenue', 'Reconciled Cost Of Revenue']:
                    if cogs_key in financials.index:
                        cogs_val = financials.loc[cogs_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"COGS_{year}",
                    display_name="Cost of Revenue (COGS)",
                    value=cogs_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if cogs_val else DataStatus.MISSING,
                    source="yfinance" if cogs_val else None,
                    is_critical=False
                ))

                # 13. Gross Profit
                gp_val = None
                for gp_key in ['Gross Profit', 'gross_profit']:
                    if gp_key in financials.index:
                        gp_val = financials.loc[gp_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Gross_Profit_{year}",
                    display_name="Gross Profit",
                    value=gp_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if gp_val else DataStatus.MISSING,
                    source="yfinance" if gp_val else None,
                    is_critical=False
                ))

                # 14. Operating Expenses
                opex_val = None
                for opex_key in ['Operating Expense', 'Total Expenses', 'operating_expense', 'operating_expenses']:
                    if opex_key in financials.index:
                        opex_val = financials.loc[opex_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Operating_Expenses_{year}",
                    display_name="Operating Expenses",
                    value=opex_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if opex_val else DataStatus.MISSING,
                    source="yfinance" if opex_val else None,
                    is_critical=False
                ))

                # 15. Research & Development
                rd_val = None
                for rd_key in ['Research And Development', 'Research Development', 'research_development']:
                    if rd_key in financials.index:
                        rd_val = financials.loc[rd_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"RD_{year}",
                    display_name="Research & Development",
                    value=rd_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rd_val else DataStatus.MISSING,
                    source="yfinance" if rd_val else None,
                    is_critical=False
                ))

                # 16. EBIT / Operating Income
                ebit_val = None
                for ebit_key in ['EBIT', 'Operating Income', 'Total Operating Income As Reported', 'ebit', 'operating_income']:
                    if ebit_key in financials.index:
                        ebit_val = financials.loc[ebit_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"EBIT_{year}",
                    display_name="EBIT",
                    value=ebit_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ebit_val else DataStatus.MISSING,
                    source="yfinance" if ebit_val else None,
                    is_critical=False
                ))

                # 17. Other Income/Expense
                other_val = None
                for other_key in ['Other Income Expense', 'Other Non Operating Income Expenses', 'other_income_expense']:
                    if other_key in financials.index:
                        other_val = financials.loc[other_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Other_Income_Expense_{year}",
                    display_name="Other Income/Expense",
                    value=other_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if other_val else DataStatus.MISSING,
                    source="yfinance" if other_val else None,
                    is_critical=False
                ))

                # 18. Net Income
                ni_val = None
                for ni_key in ['Net Income Common Stockholders', 'Net Income', 'Diluted NI Availto Com Stockholders', 'net_income']:
                    if ni_key in financials.index:
                        ni_val = financials.loc[ni_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Net_Income_{year}",
                    display_name="Net Income",
                    value=ni_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ni_val else DataStatus.MISSING,
                    source="yfinance" if ni_val else None,
                    is_critical=False
                ))

                # 19. Operating Cash Flow - try multiple possible field names (snake_case first)
                ocf_val = None
                for ocf_key in ['operating_cash_flow', 'ocf', 'Operating Cash Flow', 'Cash Flow From Continuing Operating Activities']:
                    if ocf_key in cashflow.index:
                        ocf_val = cashflow.loc[ocf_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Operating_Cash_Flow_{year}",
                    display_name="Operating Cash Flow",
                    value=ocf_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ocf_val else DataStatus.MISSING,
                    source="yfinance" if ocf_val else None,
                    is_critical=False
                ))

                # 20. Free Cash Flow - try multiple possible field names (snake_case first)
                fcf_val = None
                for fcf_key in ['free_cash_flow', 'fcf', 'Free Cash Flow']:
                    if fcf_key in cashflow.index:
                        fcf_val = cashflow.loc[fcf_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Free_Cash_Flow_{year}",
                    display_name="Free Cash Flow",
                    value=fcf_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if fcf_val else DataStatus.MISSING,
                    source="yfinance" if fcf_val else None,
                    is_critical=False
                ))

                # 21. Cash & Equivalents - try multiple field name variations
                cash_val = None
                for cash_key in ['Cash Cash Equivalents And Short Term Investments', 'Cash And Cash Equivalents', 'Cash Equivalents', 'cash_and_equivalents', 'cash']:
                    if cash_key in balance_sheet.index:
                        cash_val = balance_sheet.loc[cash_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Cash_Equivalents_{year}",
                    display_name="Cash & Equivalents",
                    value=cash_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if cash_val else DataStatus.MISSING,
                    source="yfinance" if cash_val else None,
                    is_critical=False
                ))

                # 22. Total Assets
                assets_val = None
                for assets_key in ['Total Assets', 'total_assets']:
                    if assets_key in balance_sheet.index:
                        assets_val = balance_sheet.loc[assets_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Total_Assets_{year}",
                    display_name="Total Assets",
                    value=assets_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if assets_val else DataStatus.MISSING,
                    source="yfinance" if assets_val else None,
                    is_critical=False
                ))

                # 23. Total Debt
                debt_val = None
                for debt_key in ['Total Debt', 'Long Term Debt And Capital Lease Obligation', 'total_debt']:
                    if debt_key in balance_sheet.index:
                        debt_val = balance_sheet.loc[debt_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Total_Debt_{year}",
                    display_name="Total Debt",
                    value=debt_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if debt_val else DataStatus.MISSING,
                    source="yfinance" if debt_val else None,
                    is_critical=False
                ))

                # 24. Shareholders Equity
                equity_val = None
                for equity_key in ['Stockholders Equity', 'Total Equity Gross Minority Interest', 'Common Stock Equity', 'stockholders_equity', 'total_equity']:
                    if equity_key in balance_sheet.index:
                        equity_val = balance_sheet.loc[equity_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Shareholders_Equity_{year}",
                    display_name="Shareholders Equity",
                    value=equity_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if equity_val else DataStatus.MISSING,
                    source="yfinance" if equity_val else None,
                    is_critical=False
                ))

                # 25. Retained Earnings
                re_val = None
                for re_key in ['Retained Earnings', 'retained_earnings']:
                    if re_key in balance_sheet.index:
                        re_val = balance_sheet.loc[re_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Retained_Earnings_{year}",
                    display_name="Retained Earnings",
                    value=re_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if re_val else DataStatus.MISSING,
                    source="yfinance" if re_val else None,
                    is_critical=False
                ))

                # 26. Shares Outstanding
                shares_val = None
                for shares_key in ['Ordinary Shares Number', 'Share Issued', 'ordinary_shares_number', 'shares_outstanding']:
                    if shares_key in balance_sheet.index:
                        shares_val = balance_sheet.loc[shares_key, col]
                        break
                data_fields.append(DataField(
                    field_name=f"Shares_Outstanding_{year}",
                    display_name="Shares Outstanding",
                    value=shares_val,
                    unit="shares",
                    status=DataStatus.RETRIEVED if shares_val else DataStatus.MISSING,
                    source="yfinance" if shares_val else None,
                    is_critical=False
                ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _process_dcf_market_data(self, market_data: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process market data for DCF (6 fields)"""
        # market_data is already the key_stats dict from yfinance_service (flat structure)
        # No nested "info" key - use market_data directly
        info = market_data if market_data else {}
        data_fields = []

        # 1. Current Stock Price
        current_price = info.get('current_price', info.get('currentPrice'))
        price_field = DataField(
            field_name="Current Stock Price",
            display_name="Current Stock Price",
            value=current_price,
            unit="USD",
            status=DataStatus.RETRIEVED if current_price else DataStatus.MISSING,
            source="yfinance" if current_price else None,
            is_critical=True
        ) if current_price else None
        data_fields.append(price_field) if price_field else None

        # 2. Shares Outstanding
        shares = info.get('sharesOutstanding')
        shares_field = DataField(
            field_name="Shares Outstanding",
            display_name="Shares Outstanding",
            value=shares,
            unit="shares",
            status=DataStatus.RETRIEVED if shares else DataStatus.MISSING,
            source="yfinance" if shares else None,
            is_critical=True
        ) if shares else None
        data_fields.append(shares_field) if shares_field else None

        # 3. Beta
        beta = overrides.get("beta", info.get('beta', 1.0))
        beta_field = DataField(
            field_name="Beta",
            display_name="Beta",
            value=beta,
            status=DataStatus.MANUAL_OVERRIDE if "beta" in overrides else DataStatus.RETRIEVED,
            source="User Input" if "beta" in overrides else "yfinance",
            is_critical=True,
            allow_override=True
        )
        data_fields.append(beta_field)

        # 4. Total Debt - use snake_case key from yfinance_service
        total_debt = info.get("total_debt")
        debt_field = DataField(
            field_name="Total Debt",
            display_name="Total Debt",
            value=total_debt,
            unit="USD",
            status=DataStatus.RETRIEVED if total_debt else DataStatus.MISSING,
            source="yfinance" if total_debt else None,
            is_critical=True
        ) if total_debt else None
        data_fields.append(debt_field) if debt_field else None

        # 5. Cash & Equivalents - use snake_case key from yfinance_service
        cash = info.get("total_cash")
        cash_field = DataField(
            field_name="Cash & Equivalents",
            display_name="Cash & Equivalents",
            value=cash,
            unit="USD",
            status=DataStatus.RETRIEVED if cash else DataStatus.MISSING,
            source="yfinance" if cash else None,
            is_critical=True
        ) if cash else None
        data_fields.append(cash_field) if cash_field else None

        # 6. Market Cap
        mcap = info.get('marketCap')
        mcap_field = DataField(
            field_name="Market Cap",
            display_name="Market Cap",
            value=mcap,
            unit="USD",
            status=DataStatus.RETRIEVED if mcap else DataStatus.MISSING,
            source="yfinance" if mcap else None,
            is_critical=True
        ) if mcap else None
        data_fields.append(mcap_field) if mcap_field else None

        return MarketDataDisplay(
            current_stock_price=price_field,
            shares_outstanding=shares_field,
            beta=beta_field,
            total_debt=debt_field,
            cash=cash_field,
            market_cap=mcap_field,
            currency=DataField(field_name="Currency", display_name="Currency", value="USD", status=DataStatus.RETRIEVED, source="yfinance"),
            data_fields=data_fields
        )

    def _process_dcf_opening_balances(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process opening balances for DCF (3 fields)"""
        years = []
        data_fields = []

        balance_sheet = historical_data.get("balance_sheet")
        if balance_sheet is not None:
            # Get most recent year for opening balances
            if len(balance_sheet.columns) > 0:
                latest_col = balance_sheet.columns[0]
                year = int(latest_col.year)
                years.append(year)

                # 1. Net Debt Opening Balance (calculated from Debt - Cash)
                total_debt = balance_sheet.loc['Total Debt', latest_col] if 'Total Debt' in balance_sheet.index else None
                if total_debt is None:
                    total_debt = balance_sheet.loc['Long Term Debt', latest_col] if 'Long Term Debt' in balance_sheet.index else None
                cash = balance_sheet.loc['Cash And Cash Equivalents', latest_col] if 'Cash And Cash Equivalents' in balance_sheet.index else None
                if cash is None:
                    cash = balance_sheet.loc['Cash', latest_col] if 'Cash' in balance_sheet.index else None

                net_debt = (total_debt - cash) if (total_debt and cash) else None
                data_fields.append(DataField(
                    field_name=f"Net_Debt_Opening_{year}",
                    value=net_debt,
                    unit="USD",
                    status=DataStatus.CALCULATED if net_debt else DataStatus.MISSING,
                    source="Calculated from Balance Sheet",
                    formula="Total Debt - Cash",
                    is_critical=False
                ))

                # 2. PP&E (Gross) Opening Balance
                ppe_val = balance_sheet.loc['Property Plant Equipment', latest_col] if 'Property Plant Equipment' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"PPnE_Gross_Opening_{year}",
                    value=ppe_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ppe_val else DataStatus.MISSING,
                    source="yfinance" if ppe_val else None,
                    is_critical=False
                ))

                # 3. Accumulated Depreciation
                accum_dep_val = balance_sheet.loc['Accumulated Depreciation', latest_col] if 'Accumulated Depreciation' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Accumulated_Depreciation_Opening_{year}",
                    value=accum_dep_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if accum_dep_val else DataStatus.MISSING,
                    source="yfinance" if accum_dep_val else None,
                    is_critical=False
                ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _process_dcf_peer_comparables(self, retrieved_assumptions: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process peer comparables for WACC calculation (6 fields × N peers)
        
        The 6 key WACC inputs per peer:
        1. Market Cap - for capital structure weights
        2. Beta - levered equity beta
        3. Total Debt - for D/E ratio and cost of debt calculation
        4. Cash - for net debt calculation
        5. Effective Tax Rate - for after-tax cost of debt
        6. Cost of Debt - pre-tax cost of debt (NEW)
        
        Note: Risk-free rate is a global input, not peer-specific
        """
        years = [2024]  # Current year for peer data
        data_fields = []

        peers = retrieved_assumptions.get("peers", [])
        if not peers:
            peers = overrides.get("peers", [])

        for i, peer_ticker in enumerate(peers[:5]):  # Limit to 5 peers
            peer_info = retrieved_assumptions.get(f"peer_{peer_ticker}_info", {})

            # 1. Peer Market Cap
            peer_mcap = peer_info.get('marketCap')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_MarketCap",
                value=peer_mcap,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_mcap else DataStatus.MISSING,
                source="yfinance" if peer_mcap else None,
                is_critical=False
            ))

            # 2. Peer Beta
            peer_beta = peer_info.get('beta')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_Beta",
                value=peer_beta,
                status=DataStatus.RETRIEVED if peer_beta else DataStatus.MISSING,
                source="yfinance" if peer_beta else None,
                is_critical=False
            ))

            # 3. Peer Total Debt
            peer_debt = peer_info.get('totalDebt')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_TotalDebt",
                value=peer_debt,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_debt else DataStatus.MISSING,
                source="yfinance" if peer_debt else None,
                is_critical=False
            ))

            # 4. Peer Cash
            peer_cash = peer_info.get('cash')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_Cash",
                value=peer_cash,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_cash else DataStatus.MISSING,
                source="yfinance" if peer_cash else None,
                is_critical=False
            ))

            # 5. Peer Tax Rate (calculated from financials)
            peer_tax_rate = peer_info.get('effectiveTaxRate')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_TaxRate",
                value=peer_tax_rate,
                unit="%",
                status=DataStatus.CALCULATED if peer_tax_rate else DataStatus.MISSING,
                source="Calculated from yfinance" if peer_tax_rate else None,
                formula="Tax Provision / Pre-Tax Income",
                is_critical=False
            ))

            # 6. Peer Cost of Debt (NEW - calculated from Interest Expense / Total Debt)
            peer_cost_of_debt = peer_info.get('costOfDebt')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_CostOfDebt",
                value=peer_cost_of_debt,
                unit="%",
                status=DataStatus.CALCULATED if peer_cost_of_debt else DataStatus.MISSING,
                source="Calculated from yfinance" if peer_cost_of_debt else None,
                formula="Interest Expense / Total Debt",
                is_critical=False
            ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _calculate_dcf_intermediate_metrics(self, hist: HistoricalFinancialsDisplay, market: MarketDataDisplay, opening: HistoricalFinancialsDisplay, peers: HistoricalFinancialsDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics (margins, growth rates, ratios) - NOT WACC/TV/Fair Value"""
        fields = []

        # Initialize revenues list at the start to avoid unbound local error
        revenues = []

        # Calculate historical EBITDA margins (if data available)
        if hist.data_fields:
            revenues = [f.value for f in hist.data_fields if 'Revenue' in f.field_name and f.value]
            ebitdas = [f.value for f in hist.data_fields if 'EBITDA' in f.field_name and f.value]

            if revenues and ebitdas and len(revenues) == len(ebitdas):
                avg_margin = sum(e/r for e, r in zip(ebitdas, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average EBITDA Margin",
                    value=avg_margin,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(EBITDA / Revenue)",
                    is_critical=False
                ))

        # Calculate Net Debt (if debt and cash available)
        net_debt = None
        if market.total_debt and market.cash:
            net_debt = market.total_debt.value - market.cash.value
            fields.append(DataField(
                field_name="Net Debt",
                value=net_debt,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="Total Debt - Cash",
                is_critical=False
            ))

        # Calculate historical growth rates (YoY)
        # Note: revenues list is now in ascending order (oldest first) due to sorted columns
        if len(revenues) >= 2:
            # revenues[0] = oldest year, revenues[-1] = most recent year
            revenue_growth = (revenues[-1] - revenues[0]) / revenues[0]
            fields.append(DataField(
                field_name="Revenue Growth Rate (Period)",
                value=revenue_growth,
                unit="%",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="(Latest Revenue - Earliest Revenue) / Earliest Revenue",
                is_critical=False
            ))

        # Calculate D&A % of Revenue
        if hist.data_fields:
            da_values = [f.value for f in hist.data_fields if 'Depreciation_Amortization' in f.field_name and f.value]
            if da_values and revenues and len(da_values) == len(revenues):
                avg_da_pct = sum(d/r for d, r in zip(da_values, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average D&A % of Revenue",
                    value=avg_da_pct,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(D&A / Revenue)",
                    is_critical=False
                ))

        # Calculate CapEx % of Revenue
        if hist.data_fields:
            capex_values = [f.value for f in hist.data_fields if 'CapEx' in f.field_name and f.value]
            if capex_values and revenues and len(capex_values) == len(revenues):
                avg_capex_pct = sum(c/r for c, r in zip(capex_values, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average CapEx % of Revenue",
                    value=avg_capex_pct,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(CapEx / Revenue)",
                    is_critical=False
                ))

        # Calculate Working Capital % of Revenue
        if hist.data_fields:
            wc_values = [f.value for f in hist.data_fields if 'Working_Capital_Change' in f.field_name and f.value]
            if wc_values and revenues and len(wc_values) == len(revenues):
                avg_wc_pct = sum(w/r for w, r in zip(wc_values, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average WC Change % of Revenue",
                    value=avg_wc_pct,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(WC Change / Revenue)",
                    is_critical=False
                ))

        # Calculate implied effective tax rate
        if hist.data_fields:
            tax_values = [f.value for f in hist.data_fields if 'Tax_Provision' in f.field_name and f.value]
            pretax_values = [f.value for f in hist.data_fields if 'Pre_Tax_Income' in f.field_name and f.value]
            if tax_values and pretax_values and len(tax_values) == len(pretax_values):
                avg_tax_rate = sum(t/p for t, p in zip(tax_values, pretax_values) if p != 0) / len(tax_values)
                fields.append(DataField(
                    field_name="Average Effective Tax Rate",
                    value=avg_tax_rate,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(Tax Provision / Pre-Tax Income)",
                    is_critical=False
                ))

        return CalculatedMetricsDisplay(data_fields=fields)

    # === Helper Methods for DuPont ===

    def _process_dupont_income_data(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process income statement data for DuPont (6 fields)"""
        years = []
        data_fields = []

        financials = historical_data.get("financials")
        if financials is not None:
            for col in financials.columns:
                year = int(col.year)
                years.append(year)

                # 1. Net Income - try multiple field name variations
                ni_key = self._find_field_key(financials.index, ['Net Income Common Stockholders', 'Net Income', 'Diluted NI Availto Com Stockholders'])
                ni_val = financials.loc[ni_key, col] if ni_key else None
                data_fields.append(DataField(
                    field_name=f"Net_Income_{year}",
                    display_name="Net Income",
                    value=ni_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ni_val else DataStatus.MISSING,
                    source="yfinance" if ni_val else None,
                    is_critical=True
                ))

                # 2. Total Revenue - try multiple field name variations
                rev_key = self._find_field_key(financials.index, ['Total Revenue', 'Operating Revenue'])
                rev_val = financials.loc[rev_key, col] if rev_key else None
                data_fields.append(DataField(
                    field_name=f"Total_Revenue_{year}",
                    display_name="Total Revenue",
                    value=rev_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rev_val else DataStatus.MISSING,
                    source="yfinance" if rev_val else None,
                    is_critical=True
                ))

                # 3. Operating Income (EBIT) - try multiple field name variations
                op_key = self._find_field_key(financials.index, ['Operating Income', 'EBIT', 'Total Operating Income As Reported'])
                op_val = financials.loc[op_key, col] if op_key else None
                data_fields.append(DataField(
                    field_name=f"Operating_Income_{year}",
                    display_name="Operating Income (EBIT)",
                    value=op_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if op_val else DataStatus.MISSING,
                    source="yfinance" if op_val else None,
                    is_critical=True
                ))

                # 4. Interest Expense - try multiple field name variations
                int_key = self._find_field_key(financials.index, ['Interest Expense', 'Interest Expense Non Operating'])
                int_val = financials.loc[int_key, col] if int_key else None
                data_fields.append(DataField(
                    field_name=f"Interest_Expense_{year}",
                    display_name="Interest Expense",
                    value=int_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if int_val else DataStatus.MISSING,
                    source="yfinance" if int_val else None,
                    is_critical=False
                ))

                # 5. Tax Provision - try multiple field name variations
                tax_key = self._find_field_key(financials.index, ['Tax Provision', 'Tax Expense'])
                tax_val = financials.loc[tax_key, col] if tax_key else None
                data_fields.append(DataField(
                    field_name=f"Tax_Provision_{year}",
                    display_name="Tax Provision",
                    value=tax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if tax_val else DataStatus.MISSING,
                    source="yfinance" if tax_val else None,
                    is_critical=False
                ))

                # 6. Pre-Tax Income - try multiple field name variations
                pretax_key = self._find_field_key(financials.index, ['Pretax Income', 'Pre-Tax Income'])
                pretax_val = financials.loc[pretax_key, col] if pretax_key else None
                data_fields.append(DataField(
                    field_name=f"Pre_Tax_Income_{year}",
                    display_name="Pre-Tax Income",
                    value=pretax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if pretax_val else DataStatus.MISSING,
                    source="yfinance" if pretax_val else None,
                    is_critical=False
                ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _find_field_key(self, index, possible_names: List[str]) -> Optional[str]:
        """Find a field key from a list of possible names.

        Args:
            index: The DataFrame index to search
            possible_names: List of possible field names to try in order

        Returns:
            The matching field name if found, None otherwise
        """
        for name in possible_names:
            if name in index:
                return name
        return None

    def _process_dupont_balance_data(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process balance sheet data for DuPont (6 fields)"""
        years = []
        data_fields = []

        balance_sheet = historical_data.get("balance_sheet")
        if balance_sheet is not None:
            for col in balance_sheet.columns:
                year = int(col.year)
                years.append(year)

                # 1. Total Assets - try multiple field name variations
                assets_key = self._find_field_key(balance_sheet.index, ['Total Assets'])
                assets_val = balance_sheet.loc[assets_key, col] if assets_key else None
                data_fields.append(DataField(
                    field_name=f"Total_Assets_{year}",
                    display_name="Total Assets",
                    value=assets_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if assets_val else DataStatus.MISSING,
                    source="yfinance" if assets_val else None,
                    is_critical=True
                ))

                # 2. Shareholders Equity - try multiple field name variations
                equity_key = self._find_field_key(balance_sheet.index, ['Stockholders Equity', 'Total Equity Gross Minority Interest', 'Common Stock Equity'])
                equity_val = balance_sheet.loc[equity_key, col] if equity_key else None
                data_fields.append(DataField(
                    field_name=f"Shareholders_Equity_{year}",
                    display_name="Shareholders Equity",
                    value=equity_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if equity_val else DataStatus.MISSING,
                    source="yfinance" if equity_val else None,
                    is_critical=True
                ))

                # 3. Total Liabilities - try multiple field name variations
                liab_key = self._find_field_key(balance_sheet.index, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
                liab_val = balance_sheet.loc[liab_key, col] if liab_key else None
                data_fields.append(DataField(
                    field_name=f"Total_Liabilities_{year}",
                    display_name="Total Liabilities",
                    value=liab_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if liab_val else DataStatus.MISSING,
                    source="yfinance" if liab_val else None,
                    is_critical=False
                ))

                # 4. Long-Term Debt - try multiple field name variations
                ltd_key = self._find_field_key(balance_sheet.index, ['Long Term Debt', 'Non Current Debt'])
                ltd_val = balance_sheet.loc[ltd_key, col] if ltd_key else None
                data_fields.append(DataField(
                    field_name=f"Long_Term_Debt_{year}",
                    display_name="Long-Term Debt",
                    value=ltd_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ltd_val else DataStatus.MISSING,
                    source="yfinance" if ltd_val else None,
                    is_critical=False
                ))

                # 5. Short-Term Debt - try multiple field name variations
                std_key = self._find_field_key(balance_sheet.index, ['Current Debt', 'Short Term Debt'])
                std_val = balance_sheet.loc[std_key, col] if std_key else None
                data_fields.append(DataField(
                    field_name=f"Short_Term_Debt_{year}",
                    display_name="Short-Term Debt",
                    value=std_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if std_val else DataStatus.MISSING,
                    source="yfinance" if std_val else None,
                    is_critical=False
                ))

                # 6. Cash & Equivalents - try multiple field name variations
                cash_key = self._find_field_key(balance_sheet.index, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments', 'Cash'])
                cash_val = balance_sheet.loc[cash_key, col] if cash_key else None
                data_fields.append(DataField(
                    field_name=f"Cash_And_Equivalents_{year}",
                    display_name="Cash & Equivalents",
                    value=cash_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if cash_val else DataStatus.MISSING,
                    source="yfinance" if cash_val else None,
                    is_critical=False
                ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _calculate_dupont_intermediate_metrics(self, income: HistoricalFinancialsDisplay, balance: HistoricalFinancialsDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics for DuPont - NOT final ROE"""
        fields = []

        # Extract data by year for calculations
        income_by_year = {}
        for field in income.data_fields:
            year = field.field_name.split('_')[-1]
            if year not in income_by_year:
                income_by_year[year] = {}
            income_by_year[year][field.field_name.rsplit('_', 1)[0]] = field.value

        balance_by_year = {}
        for field in balance.data_fields:
            year = field.field_name.split('_')[-1]
            if year not in balance_by_year:
                balance_by_year[year] = {}
            balance_by_year[year][field.field_name.rsplit('_', 1)[0]] = field.value

        years = sorted(income_by_year.keys())

        # Calculate trends for each year (where prior year data exists)
        for i, year in enumerate(years):
            curr = income_by_year.get(year, {})
            prev = income_by_year.get(str(int(year)-1), {}) if i > 0 else {}

            # Net Profit Margin
            ni = curr.get('Net_Income')
            rev = curr.get('Total_Revenue')
            if ni and rev and rev != 0:
                margin = ni / rev
                fields.append(DataField(
                    field_name=f"Net_Profit_Margin_{year}",
                    display_name="Net Profit Margin",
                    value=margin,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    formula="Net Income / Revenue",
                    is_critical=False
                ))

            # Operating Margin
            op = curr.get('Operating_Income')
            if op and rev and rev != 0:
                op_margin = op / rev
                fields.append(DataField(
                    field_name=f"Operating_Margin_{year}",
                    display_name="Operating Margin",
                    value=op_margin,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    formula="Operating Income / Revenue",
                    is_critical=False
                ))

            # Asset Turnover (requires average assets)
            if i > 0:
                curr_assets = balance_by_year.get(year, {}).get('Total_Assets')
                prev_assets = balance_by_year.get(str(int(year)-1), {}).get('Total_Assets')
                if curr_assets and prev_assets:
                    avg_assets = (curr_assets + prev_assets) / 2
                    if avg_assets != 0:
                        turnover = rev / avg_assets
                        fields.append(DataField(
                            field_name=f"Asset_Turnover_{year}",
                            display_name="Asset Turnover",
                            value=turnover,
                            unit="x",
                            status=DataStatus.CALCULATED,
                            formula="Revenue / Average Total Assets",
                            is_critical=False
                        ))

                # Equity Multiplier
                curr_equity = balance_by_year.get(year, {}).get('Shareholders_Equity')
                prev_equity = balance_by_year.get(str(int(year)-1), {}).get('Shareholders_Equity')
                if curr_equity and prev_equity:
                    avg_equity = (curr_equity + prev_equity) / 2
                    if avg_equity != 0:
                        multiplier = avg_assets / avg_equity
                        fields.append(DataField(
                            field_name=f"Equity_Multiplier_{year}",
                            display_name="Equity Multiplier",
                            value=multiplier,
                            unit="x",
                            status=DataStatus.CALCULATED,
                            formula="Average Total Assets / Average Shareholders Equity",
                            is_critical=False
                        ))

                # Debt-to-Equity Ratio
                curr_debt = (balance_by_year.get(year, {}).get('Long_Term_Debt') or 0) + \
                           (balance_by_year.get(year, {}).get('Short_Term_Debt') or 0)
                if curr_equity and curr_equity != 0:
                    dte = curr_debt / curr_equity
                    fields.append(DataField(
                        field_name=f"Debt_to_Equity_{year}",
                        display_name="Debt-to-Equity Ratio",
                        value=dte,
                        unit="x",
                        status=DataStatus.CALCULATED,
                        formula="(Long Term Debt + Short Term Debt) / Shareholders Equity",
                        is_critical=False
                    ))

            # Interest Burden
            ebit = curr.get('Operating_Income')
            pretax = curr.get('Pre_Tax_Income')
            if ebit and pretax and ebit != 0:
                interest_burden = pretax / ebit
                fields.append(DataField(
                    field_name=f"Interest_Burden_{year}",
                    display_name="Interest Burden",
                    value=interest_burden,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Pre-Tax Income / Operating Income",
                    is_critical=False
                ))

            # Tax Burden
            if pretax and ni and pretax != 0:
                tax_burden = ni / pretax
                fields.append(DataField(
                    field_name=f"Tax_Burden_{year}",
                    display_name="Tax Burden",
                    value=tax_burden,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Net Income / Pre-Tax Income",
                    is_critical=False
                ))

        return CalculatedMetricsDisplay(data_fields=fields)

    # === Helper Methods for Comps ===

    def _process_comps_target_data(self, historical_data: Dict, market_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process target company data for Comps - extract market data and trading metrics"""
        years = []
        data_fields = []

        # market_data is already the key_stats dict from yfinance_service (flat structure)
        info = market_data if market_data else {}

        # 1. Current Stock Price
        current_price = info.get('current_price') or info.get('currentPrice')
        data_fields.append(DataField(
            field_name="Current Stock Price",
            display_name="Current Stock Price",
            value=current_price,
            unit="USD",
            status=DataStatus.RETRIEVED if current_price else DataStatus.MISSING,
            source="yfinance" if current_price else None,
            is_critical=True
        ))

        # 2. Market Cap
        mcap = info.get('market_cap') or info.get('marketCap')
        data_fields.append(DataField(
            field_name="Market Cap",
            display_name="Market Cap",
            value=mcap,
            unit="USD",
            status=DataStatus.RETRIEVED if mcap else DataStatus.MISSING,
            source="yfinance" if mcap else None,
            is_critical=True
        ))

        # 3. Enterprise Value
        ev = info.get('enterprise_value') or info.get('enterpriseValue')
        data_fields.append(DataField(
            field_name="Enterprise Value",
            display_name="Enterprise Value",
            value=ev,
            unit="USD",
            status=DataStatus.RETRIEVED if ev else DataStatus.MISSING,
            source="yfinance" if ev else None,
            is_critical=True
        ))

        # 4. EBITDA (TTM)
        ebitda = info.get('ebitda') or info.get('EBITDA')
        data_fields.append(DataField(
            field_name="EBITDA",
            display_name="EBITDA (TTM)",
            value=ebitda,
            unit="USD",
            status=DataStatus.RETRIEVED if ebitda else DataStatus.MISSING,
            source="yfinance" if ebitda else None,
            is_critical=True
        ))

        # 5. EPS (Trailing)
        eps = info.get('trailing_eps') or info.get('trailingEps') or info.get('eps')
        data_fields.append(DataField(
            field_name="EPS",
            display_name="EPS (TTM)",
            value=eps,
            unit="USD",
            status=DataStatus.RETRIEVED if eps else DataStatus.MISSING,
            source="yfinance" if eps else None,
            is_critical=True
        ))

        # 6. Beta
        beta = overrides.get("beta", info.get('beta', 1.0))
        data_fields.append(DataField(
            field_name="Beta",
            display_name="Beta",
            value=beta,
            status=DataStatus.MANUAL_OVERRIDE if "beta" in overrides else DataStatus.RETRIEVED,
            source="User Input" if "beta" in overrides else "yfinance",
            is_critical=True,
            allow_override=True
        ))

        # 7. Total Debt
        total_debt = info.get('total_debt') or info.get('totalDebt')
        data_fields.append(DataField(
            field_name="Total Debt",
            display_name="Total Debt",
            value=total_debt,
            unit="USD",
            status=DataStatus.RETRIEVED if total_debt else DataStatus.MISSING,
            source="yfinance" if total_debt else None,
            is_critical=True
        ))

        # 8. Cash & Equivalents
        cash = info.get('total_cash') or info.get('totalCash') or info.get('cash')
        data_fields.append(DataField(
            field_name="Cash & Equivalents",
            display_name="Cash & Equivalents",
            value=cash,
            unit="USD",
            status=DataStatus.RETRIEVED if cash else DataStatus.MISSING,
            source="yfinance" if cash else None,
            is_critical=True
        ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _process_comps_peer_data(self, retrieved_assumptions: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process peer company data for Comps - extract market data and multiples for each peer"""
        data_fields = []

        # Get peer list from retrieved assumptions or overrides
        peers = retrieved_assumptions.get("peers", [])
        if not peers:
            peers = overrides.get("peers", [])

        # Process up to 5 peers (matching DCF pattern)
        for peer_ticker in peers[:5]:
            # Peer info is stored as peer_{ticker}_info in retrieved_assumptions
            peer_info = retrieved_assumptions.get(f"peer_{peer_ticker}_info", {})

            if not peer_info:
                continue

            # 1. Peer Current Price
            peer_price = peer_info.get('currentPrice') or peer_info.get('current_price')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_Price",
                display_name=f"{peer_ticker} Stock Price",
                value=peer_price,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_price else DataStatus.MISSING,
                source="yfinance" if peer_price else None,
                is_critical=True
            ))

            # 2. Peer Market Cap
            peer_mcap = peer_info.get('marketCap') or peer_info.get('market_cap')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_MarketCap",
                display_name=f"{peer_ticker} Market Cap",
                value=peer_mcap,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_mcap else DataStatus.MISSING,
                source="yfinance" if peer_mcap else None,
                is_critical=True
            ))

            # 3. Peer Enterprise Value
            peer_ev = peer_info.get('enterpriseValue') or peer_info.get('enterprise_value')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_EV",
                display_name=f"{peer_ticker} Enterprise Value",
                value=peer_ev,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_ev else DataStatus.MISSING,
                source="yfinance" if peer_ev else None,
                is_critical=True
            ))

            # 4. Peer EBITDA
            peer_ebitda = peer_info.get('ebitda') or peer_info.get('EBITDA')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_EBITDA",
                display_name=f"{peer_ticker} EBITDA",
                value=peer_ebitda,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_ebitda else DataStatus.MISSING,
                source="yfinance" if peer_ebitda else None,
                is_critical=True
            ))

            # 5. Peer EPS (Trailing)
            peer_eps = peer_info.get('trailingEps') or peer_info.get('trailing_eps') or peer_info.get('eps')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_EPS",
                display_name=f"{peer_ticker} EPS (TTM)",
                value=peer_eps,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_eps else DataStatus.MISSING,
                source="yfinance" if peer_eps else None,
                is_critical=True
            ))

            # 6. Peer Book Value
            peer_book = peer_info.get('bookValue') or peer_info.get('book_value')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_BookValue",
                display_name=f"{peer_ticker} Book Value",
                value=peer_book,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_book else DataStatus.MISSING,
                source="yfinance" if peer_book else None,
                is_critical=False
            ))

            # 7. Peer Revenue
            peer_revenue = peer_info.get('totalRevenue') or peer_info.get('total_revenue') or peer_info.get('revenue')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_Revenue",
                display_name=f"{peer_ticker} Revenue (TTM)",
                value=peer_revenue,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_revenue else DataStatus.MISSING,
                source="yfinance" if peer_revenue else None,
                is_critical=False
            ))

        return MarketDataDisplay(data_fields=data_fields)

    def _calculate_comps_intermediate_metrics(self, target: HistoricalFinancialsDisplay, peers: MarketDataDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics for Comps - individual peer multiples AND target company multiples (NOT median/mean)"""
        fields = []

        # Extract peer data for multiple calculations
        peer_data = {}  # ticker -> {price, mcap, ev, ebitda, eps}

        for field in peers.data_fields:
            if field.value is None:
                continue

            # Parse field name: Peer_{TICKER}_{METRIC}
            parts = field.field_name.split('_')
            if len(parts) >= 3 and parts[0] == 'Peer':
                ticker = parts[1]
                metric = '_'.join(parts[2:])  # e.g., "MarketCap", "EV", "EBITDA"

                if ticker not in peer_data:
                    peer_data[ticker] = {}
                peer_data[ticker][metric] = field.value

        # Calculate EV/EBITDA and P/E multiples for each peer
        ev_ebitda_values = []
        pe_values = []
        pb_values = []
        ps_values = []
        
        for ticker, data in peer_data.items():
            ev = data.get('EV')
            ebitda = data.get('EBITDA')
            price = data.get('Price')
            eps = data.get('EPS')
            book = data.get('BookValue')
            revenue = data.get('Revenue')

            # EV/EBITDA LTM
            if ev and ebitda and ebitda > 0:
                ev_ebitda = ev / ebitda
                ev_ebitda_values.append(ev_ebitda)
                fields.append(DataField(
                    field_name=f"Peer_{ticker}_EV_EBITDA_LTM",
                    display_name=f"{ticker} EV/EBITDA (LTM)",
                    value=round(ev_ebitda, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Enterprise Value / EBITDA",
                    is_critical=False
                ))

            # P/E LTM
            if price and eps and eps > 0:
                pe = price / eps
                pe_values.append(pe)
                fields.append(DataField(
                    field_name=f"Peer_{ticker}_PE_LTM",
                    display_name=f"{ticker} P/E (LTM)",
                    value=round(pe, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Stock Price / EPS",
                    is_critical=False
                ))
            
            # P/B LTM
            if price and book and book > 0:
                pb = price / book
                pb_values.append(pb)
                fields.append(DataField(
                    field_name=f"Peer_{ticker}_PB_LTM",
                    display_name=f"{ticker} P/B (LTM)",
                    value=round(pb, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Stock Price / Book Value",
                    is_critical=False
                ))
            
            # P/S LTM
            if price and revenue and revenue > 0:
                ps = price / revenue
                ps_values.append(ps)
                fields.append(DataField(
                    field_name=f"Peer_{ticker}_PS_LTM",
                    display_name=f"{ticker} P/S (LTM)",
                    value=round(ps, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Stock Price / Revenue",
                    is_critical=False
                ))

        # Calculate peer median multiples for Step 8 AI suggestions
        def calculate_median(values):
            if not values:
                return None
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            mid = n // 2
            if n % 2 == 0:
                return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            else:
                return sorted_vals[mid]
        
        # Add peer median multiples to calculated metrics
        if ev_ebitda_values:
            median_ev_ebitda = calculate_median(ev_ebitda_values)
            if median_ev_ebitda:
                fields.append(DataField(
                    field_name="Peer_Median_EV_EBITDA",
                    display_name="Peer Median EV/EBITDA",
                    value=round(median_ev_ebitda, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Median of peer EV/EBITDA multiples",
                    is_critical=False
                ))
        
        if pe_values:
            median_pe = calculate_median(pe_values)
            if median_pe:
                fields.append(DataField(
                    field_name="Peer_Median_PE",
                    display_name="Peer Median P/E",
                    value=round(median_pe, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Median of peer P/E multiples",
                    is_critical=False
                ))
        
        if pb_values:
            median_pb = calculate_median(pb_values)
            if median_pb:
                fields.append(DataField(
                    field_name="Peer_Median_PB",
                    display_name="Peer Median P/B",
                    value=round(median_pb, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Median of peer P/B multiples",
                    is_critical=False
                ))
        
        if ps_values:
            median_ps = calculate_median(ps_values)
            if median_ps:
                fields.append(DataField(
                    field_name="Peer_Median_PS",
                    display_name="Peer Median P/S",
                    value=round(median_ps, 2),
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Median of peer P/S multiples",
                    is_critical=False
                ))

        # Calculate target company multiples from target data
        target_data = {}
        for field in target.data_fields:
            if field.value is not None:
                target_data[field.field_name] = field.value

        target_ev = target_data.get('Enterprise Value')
        target_ebitda = target_data.get('EBITDA')
        target_price = target_data.get('Current Stock Price')
        target_eps = target_data.get('EPS')

        # Target EV/EBITDA LTM
        if target_ev and target_ebitda and target_ebitda > 0:
            target_ev_ebitda = target_ev / target_ebitda
            fields.append(DataField(
                field_name="Target_EV_EBITDA_LTM",
                display_name="Target EV/EBITDA (LTM)",
                value=round(target_ev_ebitda, 2),
                unit="x",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="Enterprise Value / EBITDA",
                is_critical=True
            ))

        # Target P/E LTM
        if target_price and target_eps and target_eps > 0:
            target_pe = target_price / target_eps
            fields.append(DataField(
                field_name="Target_PE_LTM",
                display_name="Target P/E (LTM)",
                value=round(target_pe, 2),
                unit="x",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="Stock Price / EPS",
                is_critical=True
            ))

        return CalculatedMetricsDisplay(data_fields=fields)

    # === Common Helper Methods ===

    def _aggregate_missing_data(self, displays: List) -> MissingDataSummary:
        """Aggregate missing data from all displays"""
        critical_missing = []
        optional_missing = []

        for display in displays:
            if hasattr(display, 'data_fields'):
                for field in display.data_fields:
                    if field.status == DataStatus.MISSING:
                        if field.is_critical:
                            critical_missing.append(field.field_name)
                        else:
                            optional_missing.append(field.field_name)

        return MissingDataSummary(
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            total_missing=len(critical_missing) + len(optional_missing)
        )