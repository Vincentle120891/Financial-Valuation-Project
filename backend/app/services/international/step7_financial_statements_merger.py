"""
Financial Statements Merger - Combines Step 6 API data with Step 7 AI/PDF/SEC data

Creates complete Income Statement, Balance Sheet, and Cash Flow Statement
from merged Step 6 + Step 7 data. Called at the BEGINNING of Step 8.

Architecture:
- Step 6 provides API-fetched data (Revenue, EBITDA, Net Income, etc.)
- Step 7 provides gap-filled data (Cash & Equivalents, PP&E Gross, etc.)
- This merger combines them into a single, complete financial dataset
- Step 8 then builds trendlines and generates assumptions from this merged data

Data Flow:
    Step 6 financial_data ─┐
    Step 7 AI/PDF/SEC data ─┼─→ FinancialStatementsMerger.merge() → complete_financial_statements
    Step 7 automated gaps ──┘
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _normalize_period_key(period: str) -> str:
    """
    Normalize a period string to its year prefix for consistent matching.
    
    Handles multiple formats:
    - "2024" → "2024"
    - "2024-12-31" → "2024"
    - "FY2024" → "2024"
    - "2024Q4" → "2024"
    """
    if not period:
        return ""
    # Extract leading 4-digit year
    m = re.match(r"(\d{4})", period)
    return m.group(1) if m else period


def _match_period_to_target(source_period: str, target_keys: dict) -> Optional[str]:
    """
    Find a matching period key in the target dict, handling format differences.
    
    E.g. source_period="2024" matches target key "2024-12-31"
         source_period="2024-12-31" matches target key "2024"
    """
    # Direct match
    if source_period in target_keys:
        return source_period
    
    source_year = _normalize_period_key(source_period)
    
    # Try matching by year prefix
    for target_key in target_keys:
        if _normalize_period_key(target_key) == source_year:
            return target_key
    
    return None


# =============================================================================
# FIELD MAPPING: unified field name → (section, [yfinance key variants])
# =============================================================================

INCOME_STATEMENT_FIELDS = {
    "revenue": ["totalRevenue", "revenue", "Revenue"],
    "cogs": ["costOfRevenue", "cogs", "CostOfRevenue"],
    "gross_profit": ["grossProfit", "GrossProfit"],
    "operating_expenses": ["operatingExpense", "totalOperatingExpense", "OperatingExpense"],
    "other_opex": ["otherOperatingExpense", "otherOpex", "OtherOperatingExpense",
                    "other_operating_expenses", "Other Operating Expense"],
    "research_development": ["researchDevelopment", "ResearchDevelopment", "rdExpense"],
    "ebitda": ["ebitda", "EBITDA"],
    "ebit": ["operatingIncome", "ebit", "OperatingIncome"],
    "interest_expense": ["interestExpense", "InterestExpense"],
    "other_income": ["otherIncomeExpense", "nonOperatingIncome", "OtherIncomeExpense"],
    "pretax_income": ["pretaxIncome", "incomeBeforeTax", "PretaxIncome"],
    "tax_provision": ["taxProvision", "incomeTaxExpense", "TaxProvision"],
    "net_income": ["netIncome", "netIncomeCommonStockholders", "NetIncome"],
    "depreciation": ["depreciation", "depreciationAndAmortization", "Depreciation"],
    "sg_and_a": ["sellingGeneralAdministrative", "sgaExpense", "SellingGeneralAdministrative"],
    "interest_income": ["interestIncome", "InterestIncome"],
    "deferred_tax": ["deferredTax", "DeferredTax", "DeferredIncomeTax",
                      "deferred_tax", "Deferred Tax", "Deferred Income Tax"],
}

BALANCE_SHEET_FIELDS = {
    "total_assets": ["totalAssets", "TotalAssets", "total_assets"],
    "total_debt": ["totalDebt", "TotalDebt", "total_debt"],
    "long_term_debt": ["longTermDebt", "LongTermDebt", "long_term_debt"],
    "current_debt": ["currentDebt", "shortTermDebt", "CurrentDebt", "current_debt"],
    "cash_and_equivalents": ["cash", "cashAndEquivalents", "totalCash", "CashAndCashEquivalents",
                             "cash_and_cash_equivalents", "Cash And Cash Equivalents"],
    "inventory": ["inventory", "Inventory"],
    "accounts_receivable": ["netReceivables", "accountsReceivable", "NetReceivables", "accounts_receivable"],
    "accounts_payable": ["accountsPayable", "AccountsPayable", "accounts_payable"],
    "shareholders_equity": ["totalStockholdersEquity", "stockholdersEquity", "StockholdersEquity",
                            "shareholders_equity", "Total Equity Gross Minority Interest"],
    "retained_earnings": ["retainedEarnings", "RetainedEarnings", "retained_earnings"],
    "shares_outstanding": ["sharesOutstanding", "ordinarySharesNumber", "SharesOutstanding",
                           "shares_outstanding", "Ordinary Shares Number"],
    "net_debt_opening": ["net_debt_opening"],
    "ppe_gross": ["ppe_gross", "propertyPlantEquipment", "PropertyPlantAndEquipmentGross",
                  "gross_ppe", "Gross PPE"],
    "accumulated_depreciation": ["accumulated_depreciation", "accumulatedDepreciation",
                                 "AccumulatedDepreciation", "Accumulated Depreciation"],
    "deferred_tax_assets": ["deferredTaxAssets", "DeferredTaxAssets", "Non Current Deferred Taxes Assets",
                            "NonCurrentDeferredTaxesAssets", "deferred_tax_assets",
                            "DeferredIncomeTaxAssetsNet", "DeferredTaxAssetsNet"],
    "tax_loss_carryforward": ["taxLossCarryforward", "TaxLossCarryforward",
                              "DeferredTaxAssetsOperatingLossCarryforwards",
                              "OperatingLossCarryforwards", "tax_loss_carryforward"],
    "net_debt": ["netDebt", "NetDebt", "net_debt"],
    "non_current_marketable_securities": ["nonCurrentMarketableSecurities", "LongTermInvestments",
                                          "Non Current Available For Sale Securities",
                                          "non_current_marketable_securities", "Other Long Term Investments"],
    "other_current_liabilities": ["otherCurrentLiabilities", "OtherCurrentLiabilities",
                                  "Other Current Liabilities", "other_current_liabilities"],
    "deferred_tax_liabilities": ["deferredTaxLiabilities", "DeferredTaxLiabilities",
                                 "Net Non Current Deferred Tax Liabilities",
                                 "deferred_tax_liabilities"],
    "net_ppe": ["netPPE", "NetPPE", "net_ppe", "PropertyPlantAndEquipmentNet",
                "Property Plant And Equipment Net"],
    "total_liabilities": ["totalLiabilities", "TotalLiabilities", "total_liabilities",
                          "TotalLiabilitiesNetMinorityInterest"],
    "current_accrued_expenses": ["currentAccruedExpenses", "CurrentAccruedExpenses",
                                 "Current Accrued Expenses", "current_accrued_expenses"],
    "current_deferred_liabilities": ["currentDeferredRevenue", "CurrentDeferredRevenue",
                                     "Current Deferred Revenue", "current_deferred_liabilities"],
    "trade_and_other_payables_non_current": ["nonCurrentPayables", "NonCurrentPayables",
                                             "Non Current Payables",
                                             "trade_and_other_payables_non_current"],
    "other_non_current_liabilities": ["otherNonCurrentLiabilities", "OtherNonCurrentLiabilities",
                                      "Other Non Current Liabilities",
                                      "other_non_current_liabilities"],
    "other_short_term_investments": ["otherShortTermInvestments", "OtherShortTermInvestments",
                                     "Other Short Term Investments",
                                     "other_short_term_investments"],
    "other_current_assets": ["otherCurrentAssets", "OtherCurrentAssets",
                             "Other Current Assets", "other_current_assets"],
    "other_non_current_assets": ["otherNonCurrentAssets", "OtherNonCurrentAssets",
                                 "Other Non Current Assets", "other_non_current_assets"],
    "common_stock": ["commonStock", "CommonStock", "common_stock", "CommonStockEquity"],
    "other_equity_adjustments": ["otherEquityAdjustments", "OtherEquityAdjustments",
                                 "Other Equity Adjustments", "other_equity_adjustments",
                                 "AccumulatedOtherComprehensiveIncome"],
}

CASH_FLOW_FIELDS = {
    "operating_cash_flow": ["operatingCashflow", "totalCashFromOperatingActivities", "OperatingCashflow"],
    "capex": ["capitalExpenditure", "capitalExpenditures", "CapitalExpenditure"],
    "free_cash_flow": ["freeCashFlow", "FreeCashFlow"],
    "working_capital_changes": ["changeInWorkingCapital", "ChangeInWorkingCapital"],
    "interest_paid": ["interestPaid", "InterestPaid"],
    "tax_paid": ["incomeTaxesPaid", "IncomeTaxesPaid"],
    "dividends_paid": ["dividendsPaid", "DividendsPaid"],
    "share_buybacks": ["repurchaseOfCapitalStock", "RepurchaseOfCapitalStock"],
    "debt_repayments": ["repaymentOfDebt", "RepaymentOfDebt"],
    "debt_issuance": ["issuanceOfDebt", "IssuanceOfDebt"],
}

ALL_FIELDS = {
    "income_statement": INCOME_STATEMENT_FIELDS,
    "balance_sheet": BALANCE_SHEET_FIELDS,
    "cash_flow": CASH_FLOW_FIELDS,
}


class FinancialStatementsMerger:
    """
    Merges Step 6 API data with Step 7 AI/PDF/SEC data
    into complete Income Statement, Balance Sheet, Cash Flow Statement.
    
    Priority: Step 7 data fills gaps where Step 6 has MISSING/null values.
    Step 6 RETRIEVED data is never overwritten by Step 7.
    """

    def merge(
        self,
        step6_data: Optional[Dict[str, Any]],
        step7_data: Optional[Dict[str, Any]],
        ai_web_search_data: Optional[Dict[str, Any]] = None,
        pdf_extraction_data: Optional[Dict[str, Any]] = None,
        sec_edgar_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main merge method.
        
        Args:
            step6_data: Step 6 financial_data response (HistoricalFinancialsData format)
            step7_data: Step 7 automated gap-filled data (optional)
            ai_web_search_data: Step 7 AI web search results (optional)
            pdf_extraction_data: Step 7 PDF extraction results (optional)
            sec_edgar_data: Step 7 SEC EDGAR XBRL extraction results (optional)
            
        Returns:
            CompleteFinancialStatements dict with income_statement, balance_sheet, cash_flow, ratios
        """
        logger.info("Starting financial statements merge")
        
        # 1. Extract periods from Step 6 data
        periods = self._extract_periods(step6_data)
        logger.info(f"Found {len(periods)} periods: {periods}")
        
        # 2. Initialize empty statements
        income_statement = {p: {} for p in periods}
        balance_sheet = {p: {} for p in periods}
        cash_flow = {p: {} for p in periods}
        data_sources = {}
        
        # 3. Fill from Step 6 (primary source)
        if step6_data:
            hist = step6_data.get("historical_financials", {})
            if isinstance(hist, dict):
                self._fill_from_step6(income_statement, balance_sheet, cash_flow,
                                       data_sources, hist, periods)
            
            # 3b. Fill opening balance fields from forecast_drivers
            forecast_drivers = step6_data.get("forecast_drivers", {})
            if isinstance(forecast_drivers, dict):
                fd_fields = forecast_drivers.get("data_fields", [])
                if isinstance(fd_fields, list):
                    self._fill_from_forecast_drivers(
                        balance_sheet, data_sources, fd_fields, periods
                    )
        
        # 4. Fill gaps from Step 7 automated data
        if step7_data:
            self._fill_from_step7_gaps(income_statement, balance_sheet, cash_flow,
                                        data_sources, step7_data, periods)
        
        # 5. Fill gaps from AI web search
        if ai_web_search_data:
            self._fill_from_ai_web_search(income_statement, balance_sheet, cash_flow,
                                           data_sources, ai_web_search_data, periods)
        
        # 6. Fill gaps from PDF extraction
        if pdf_extraction_data:
            self._fill_from_pdf(income_statement, balance_sheet, cash_flow,
                                data_sources, pdf_extraction_data, periods)
        
        # 6b. Fill gaps from SEC EDGAR XBRL data
        if sec_edgar_data:
            self._fill_from_sec_edgar_xbrl(income_statement, balance_sheet, cash_flow, data_sources, sec_edgar_data, periods)
        
        # 7. Calculate derived fields (net_debt_opening = total_debt - cash)
        for period in periods:
            bs = balance_sheet.get(period, {})
            td = bs.get("total_debt")
            cash = bs.get("cash_and_equivalents")
            if td is not None and cash is not None:
                bs["net_debt_opening"] = td - cash
            elif td is not None:
                bs["net_debt_opening"] = td
        
        # 8. Calculate derived ratios
        ratios = self._calculate_ratios(income_statement, balance_sheet, cash_flow, periods)
        
        # 8. Calculate completeness
        completeness = self._calculate_completeness(income_statement, balance_sheet, cash_flow)
        
        # 9. Get ticker from Step 6 data
        ticker = ""
        if step6_data:
            meta = step6_data.get("metadata", {})
            ticker = meta.get("ticker", "") if isinstance(meta, dict) else ""
        
        result = {
            "ticker": ticker,
            "market": "",
            "method": "",
            "merge_timestamp": datetime.now().isoformat(),
            "data_sources": data_sources,
            "periods": periods,
            "income_statement": income_statement,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow,
            "ratios": ratios,
            "completeness": completeness,
        }
        
        logger.info(f"Merge complete: {len(periods)} periods, completeness: {completeness}")
        return result

    def _extract_periods(self, step6_data: Optional[Dict]) -> List[str]:
        """
        Extract fiscal year periods from Step 6 data.
        
        Handles multiple DataField.value formats:
        1. List of dicts: [{"period": "2024-12-31", "value": 176B}, ...]
        2. Plain list of floats: [176B, 158B, 149B] — fallback: generate periods from list length
        3. Single number: assigns to "Period_1"
        """
        periods = []
        if not step6_data:
            return periods
        
        hist = step6_data.get("historical_financials", {})
        if not isinstance(hist, dict):
            return periods
        
        # Strategy 1: Try to get periods from dict-based value lists
        for field_name, field_data in hist.items():
            if field_name in ("data_fields", "periods_covered"):
                continue
            if not isinstance(field_data, dict):
                continue
            value = field_data.get("value")
            if isinstance(value, list) and value:
                if len(periods) == 0:
                    logger.info(f"Step7Merger DEBUG: First field '{field_name}' value type={type(value).__name__}, "
                                f"len={len(value)}, first_item_type={type(value[0]).__name__}, "
                                f"first_item={str(value[0])[:200]}")
                for item in value:
                    if isinstance(item, dict):
                        period = item.get("period", "")
                        # Skip placeholder Period_X entries (should not exist after transformer fix)
                        if period and not str(period).startswith("Period_") and period not in periods:
                            periods.append(period)
                if periods:
                    break
        
        # Strategy 2: If no periods found from dict format, try plain list of numbers
        if not periods:
            for field_name, field_data in hist.items():
                if field_name in ("data_fields", "periods_covered", "revenue_cagr",
                                  "avg_ebitda_margin", "avg_roe", "avg_roa"):
                    continue
                if not isinstance(field_data, dict):
                    continue
                value = field_data.get("value")
                if isinstance(value, list) and value and not isinstance(value[0], dict):
                    # Plain list of numbers — infer periods from current year backwards
                    from datetime import datetime as _dt
                    current_year = _dt.now().year
                    count = len(value)
                    periods = [f"{current_year - i}" for i in range(count)]
                    logger.info(f"Inferred {len(periods)} periods from plain list: {periods}")
                    break
        
        # Sort descending (newest first)
        periods.sort(reverse=True)
        return periods

    def _fill_from_step6(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict,
        data_sources: Dict,
        hist_financials: Dict,
        periods: List[str]
    ):
        """Fill statements from Step 6 HistoricalFinancialsData.
        
        Handles TWO data formats:
        1. Flat dict: {"revenue": {"value": [...], "status": "RETRIEVED"}, ...}
        2. List format: {"years": [...], "data_fields": [{"field_name": "revenue", ...}, ...]}
        
        Uses period normalization to match different date formats:
        - "2024" matches target key "2024-12-31"
        - "2024-12-31" matches target key "2024"
        """
        # Convert data_fields list format to flat dict if needed
        flat_dict = self._normalize_hist_financials(hist_financials)
        
        for section_name, field_map in ALL_FIELDS.items():
            target = {"income_statement": income_statement,
                      "balance_sheet": balance_sheet,
                      "cash_flow": cash_flow}[section_name]
            
            for field_name, yfinance_keys in field_map.items():
                field_data = flat_dict.get(field_name)
                if not isinstance(field_data, dict):
                    # Try yfinance key variants
                    for key in yfinance_keys:
                        field_data = flat_dict.get(key)
                        if isinstance(field_data, dict):
                            break
                
                if not isinstance(field_data, dict):
                    continue
                
                value = field_data.get("value")
                status = field_data.get("status", "MISSING")
                
                # Extract values per period (handles dict-list, plain-list, and single-number formats)
                values_by_period = self._extract_values_per_period(value, periods)
                
                if not values_by_period and value is not None and status != "MISSING":
                    logger.warning(f"Step7Merger DEBUG: No values extracted for '{field_name}' "
                                   f"value_type={type(value).__name__}, "
                                   f"value_sample={str(value)[:200]}")
                
                for source_period, val in values_by_period.items():
                    if val is None:
                        continue
                    # Use period normalization to find matching key in target dict
                    matched_key = _match_period_to_target(source_period, target)
                    if matched_key is not None:
                        target[matched_key][field_name] = val
                        # Track source
                        source = field_data.get("source", "yfinance")
                        if field_name not in data_sources:
                            data_sources[field_name] = []
                        if source not in data_sources[field_name]:
                            data_sources[field_name].append(source)

    def _normalize_hist_financials(self, hist_financials: Dict) -> Dict:
        """Convert historical_financials to a flat dict keyed by field_name.
        
        Handles two formats:
        1. Already flat: {"revenue": {"value": [...], ...}, ...} → returned as-is
        2. List format: {"years": [...], "data_fields": [{"field_name": "revenue", ...}, ...]}
           → converted to flat dict with field_name as key
        
        Also indexes by yfinance key variants so that downstream lookups by
        variant keys (e.g. "InterestExpense") also succeed.
        """
        # Already flat dict format (old style)
        if "data_fields" not in hist_financials:
            return hist_financials
        
        data_fields = hist_financials.get("data_fields", [])
        if not isinstance(data_fields, list):
            return hist_financials
        
        flat = {}
        for field in data_fields:
            if not isinstance(field, dict):
                continue
            field_name = field.get("field_name", "")
            if not field_name:
                continue
            # Index by field_name
            flat[field_name] = field
            # Also index by common yfinance key variants so that
            # the yfinance_keys fallback in _fill_from_step6 can match
            display = (field.get("display_name") or "").replace(" ", "").replace("&", "")
            if display and display != field_name:
                flat.setdefault(display, field)
        
        return flat

    def _fill_from_forecast_drivers(
        self,
        balance_sheet: Dict,
        data_sources: Dict,
        fd_fields: List,
        periods: List[str]
    ):
        """Fill balance sheet from forecast_drivers data_fields (opening balances).
        
        forecast_drivers contains opening balance fields like net_debt_opening,
        ppe_gross, non_current_marketable_securities, etc. These should be
        placed into the balance sheet for the LATEST period (opening position).
        """
        if not periods:
            return
        
        # Opening balances apply to the LATEST period (first in list, newest)
        latest_period = periods[0]
        if latest_period not in balance_sheet:
            balance_sheet[latest_period] = {}
        target = balance_sheet[latest_period]
        
        for field in fd_fields:
            if not isinstance(field, dict):
                continue
            field_name = field.get("field_name", "")
            value = field.get("value")
            status = field.get("status", "MISSING")
            
            if not field_name or value is None:
                continue
            
            # For opening balances, value can be a single number or a list
            if isinstance(value, (int, float)):
                numeric_val = float(value)
            elif isinstance(value, list) and value:
                # Use the first (most recent) value
                first = value[0]
                if isinstance(first, dict):
                    numeric_val = first.get("value")
                elif isinstance(first, (int, float)):
                    numeric_val = float(first)
                else:
                    continue
            else:
                continue
            
            if numeric_val is None:
                continue
            
            # Only fill if not already set (Step 6 historical takes priority)
            if field_name not in target or target[field_name] is None:
                target[field_name] = numeric_val
                source = field.get("source", "opening_balance")
                data_sources.setdefault(field_name, [])
                if source not in data_sources[field_name]:
                    data_sources[field_name].append(source)

    def _fill_from_step7_gaps(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict,
        data_sources: Dict,
        step7_data: Dict,
        periods: List[str]
    ):
        """Fill gaps from Step 7 automated gap-filled data."""
        processed_periods = step7_data.get("processed_periods", [])
        if not processed_periods:
            return
        
        for period_data in processed_periods:
            if not isinstance(period_data, dict):
                continue
            period = period_data.get("period", "")
            if not period or period not in income_statement:
                continue
            
            metrics = period_data.get("metrics", {})
            for metric_name, metric_field in metrics.items():
                if not isinstance(metric_field, dict):
                    continue
                value = metric_field.get("value")
                if value is None:
                    continue
                
                # Find which section this metric belongs to
                section = self._find_section_for_metric(metric_name)
                if section == "income_statement" and metric_name not in income_statement[period]:
                    income_statement[period][metric_name] = value
                    data_sources.setdefault(metric_name, []).append("step7_gap_fill")
                elif section == "balance_sheet" and metric_name not in balance_sheet[period]:
                    balance_sheet[period][metric_name] = value
                    data_sources.setdefault(metric_name, []).append("step7_gap_fill")
                elif section == "cash_flow" and metric_name not in cash_flow[period]:
                    cash_flow[period][metric_name] = value
                    data_sources.setdefault(metric_name, []).append("step7_gap_fill")

    def _fill_from_ai_web_search(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict,
        data_sources: Dict,
        ai_data: Dict,
        periods: List[str]
    ):
        """Fill gaps from AI web search extracted data."""
        time_series = ai_data.get("time_series") or ai_data.get("data", {})
        if not isinstance(time_series, dict):
            return
        
        for date_key, metrics in time_series.items():
            if not isinstance(metrics, dict):
                continue
            # Match date_key to period
            matched_period = self._match_period(date_key, periods)
            if not matched_period:
                continue
            
            for metric_name, value in metrics.items():
                if value is None:
                    continue
                
                # Convert display name back to field name
                field_name = metric_name.lower().replace(" ", "_").replace("&", "").replace("(", "").replace(")", "")
                section = self._find_section_for_metric(field_name)
                
                if section == "income_statement" and field_name not in income_statement[matched_period]:
                    income_statement[matched_period][field_name] = value
                    data_sources.setdefault(field_name, []).append("ai_web_search")
                elif section == "balance_sheet" and field_name not in balance_sheet[matched_period]:
                    balance_sheet[matched_period][field_name] = value
                    data_sources.setdefault(field_name, []).append("ai_web_search")
                elif section == "cash_flow" and field_name not in cash_flow[matched_period]:
                    cash_flow[matched_period][field_name] = value
                    data_sources.setdefault(field_name, []).append("ai_web_search")

    def _fill_from_pdf(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict,
        data_sources: Dict,
        pdf_data: Dict,
        periods: List[str]
    ):
        """Fill gaps from PDF extraction results."""
        extracted = pdf_data.get("extracted_metrics", pdf_data)
        if not isinstance(extracted, dict):
            return
        
        for field_name, value in extracted.items():
            if value is None or field_name in ("metadata", "source", "confidence_score"):
                continue
            
            section = self._find_section_for_metric(field_name)
            # PDF data is typically for the latest period
            target_period = periods[0] if periods else None
            if not target_period:
                continue
            
            if section == "income_statement" and field_name not in income_statement[target_period]:
                income_statement[target_period][field_name] = value
                data_sources.setdefault(field_name, []).append("pdf_extraction")
            elif section == "balance_sheet" and field_name not in balance_sheet[target_period]:
                balance_sheet[target_period][field_name] = value
                data_sources.setdefault(field_name, []).append("pdf_extraction")
            elif section == "cash_flow" and field_name not in cash_flow[target_period]:
                cash_flow[target_period][field_name] = value
                data_sources.setdefault(field_name, []).append("pdf_extraction")

    def _fill_from_sec_edgar_xbrl(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict,
        data_sources: Dict,
        sec_edgar_data: Dict,
        periods: List[str]
    ):
        """Fill income statement, balance sheet, AND cash flow gaps from SEC EDGAR XBRL extraction.

        Handles both the new nested ``income_statement``/``balance_sheet``/``cash_flow``
        sections *and* the backward-compatible flat keys so that older callers still work.
        """
        xbrl = sec_edgar_data.get("xbrl_data") or sec_edgar_data
        if not isinstance(xbrl, dict):
            return

        # ------------------------------------------------------------------
        # Helper: fill a single field from year-keyed XBRL data
        # ------------------------------------------------------------------
        def _fill_field(target_section: Dict, field_name: str, year_data: Dict):
            """Fill *field_name* in *target_section* from XBRL year→value dict.
            
            Fills gaps: overwrites None/missing values from earlier data sources
            (e.g. yfinance) with SEC EDGAR XBRL data.
            """
            if not year_data or not isinstance(year_data, dict):
                return
            for year_str, value in year_data.items():
                if value is None:
                    continue
                matched_period = None
                for period in periods:
                    if period.startswith(year_str):
                        matched_period = period
                        break
                if not matched_period:
                    continue
                existing = target_section.get(matched_period, {})
                existing_val = existing.get(field_name)
                # Fill if: field missing, OR existing value is None/0 (gap from yfinance)
                if field_name not in existing or existing_val is None or existing_val == 0:
                    target_section.setdefault(matched_period, {})[field_name] = value
                    data_sources.setdefault(field_name, []).append("sec_edgar_xbrl")
                    logger.debug(f"SEC EDGAR XBRL: Filled {field_name}={value} for {matched_period}")

        # ------------------------------------------------------------------
        # 1. Fill from nested income_statement section
        # ------------------------------------------------------------------
        nested_is = xbrl.get("income_statement", {})
        if isinstance(nested_is, dict):
            for field_name, year_data in nested_is.items():
                _fill_field(income_statement, field_name, year_data)

        # ------------------------------------------------------------------
        # 2. Fill from nested balance_sheet section
        # ------------------------------------------------------------------
        nested_bs = xbrl.get("balance_sheet", {})
        if isinstance(nested_bs, dict):
            for field_name, year_data in nested_bs.items():
                _fill_field(balance_sheet, field_name, year_data)

        # ------------------------------------------------------------------
        # 3. Fill from nested cash_flow section
        # ------------------------------------------------------------------
        nested_cf = xbrl.get("cash_flow", {})
        if isinstance(nested_cf, dict):
            for field_name, year_data in nested_cf.items():
                _fill_field(cash_flow, field_name, year_data)

        # ------------------------------------------------------------------
        # 4. Backward-compatible flat keys (fill only if not already covered)
        #    These ensure older callers that only set flat keys still work.
        # ------------------------------------------------------------------
        flat_bs_fields = [
            ("ppe_gross", xbrl.get("ppe_gross", {})),
            ("accumulated_depreciation", xbrl.get("accumulated_depreciation", {})),
            ("total_assets", xbrl.get("total_assets", {})),
            ("tax_loss_carryforward", xbrl.get("tax_loss_carryforward", {})),
            ("deferred_tax_assets", xbrl.get("deferred_tax_assets", {})),
        ]
        for field_name, year_data in flat_bs_fields:
            _fill_field(balance_sheet, field_name, year_data)

        flat_cf_fields = [
            ("interest_paid", xbrl.get("interest_paid", {})),
            ("tax_paid", xbrl.get("taxes_paid", {})),
        ]
        for field_name, year_data in flat_cf_fields:
            _fill_field(cash_flow, field_name, year_data)

        flat_is_fields = [
            ("interest_expense", xbrl.get("interest_expense", {})),
            ("interest_income", xbrl.get("interest_income", {})),
            ("pretax_income", xbrl.get("pretax_income", {})),
        ]
        for field_name, year_data in flat_is_fields:
            _fill_field(income_statement, field_name, year_data)

    def _extract_values_per_period(self, value: Any, periods: List[str]) -> Dict[str, Optional[float]]:
        """
        Extract numeric values per period from a DataField value.
        
        Handles three formats:
        1. List of dicts: [{"period": "2024", "value": 176B}, ...]
        2. Plain list of floats: [176B, 158B, 149B] — mapped by index to periods
        3. Single int/float: assigned to the latest (first) period
        """
        result = {}
        if value is None:
            return result
        
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict):
                # Format 1: List of {"period": ..., "value": ...} dicts
                for item in value:
                    if isinstance(item, dict):
                        period = item.get("period", "")
                        val = item.get("value")
                        if period and val is not None:
                            try:
                                result[period] = float(val)
                            except (ValueError, TypeError):
                                pass
            elif isinstance(value[0], (int, float)):
                # Format 2: Plain list of numbers — map by index to periods
                for i, val in enumerate(value):
                    if i < len(periods) and val is not None:
                        try:
                            result[periods[i]] = float(val)
                        except (ValueError, TypeError):
                            pass
        elif isinstance(value, (int, float)):
            # Format 3: Single value — assign to latest period
            if periods:
                try:
                    result[periods[0]] = float(value)
                except (ValueError, TypeError):
                    pass
        
        return result

    def _match_period(self, date_key: str, periods: List[str]) -> Optional[str]:
        """Match a date key (e.g., '2023-12-31') to a period in the list."""
        if date_key in periods:
            return date_key
        # Try year extraction
        year = date_key[:4] if len(date_key) >= 4 else ""
        for period in periods:
            if period.startswith(year):
                return period
        return None

    def _find_section_for_metric(self, metric_name: str) -> str:
        """Determine which financial statement section a metric belongs to."""
        name_lower = metric_name.lower().replace(" ", "_")
        
        for field_name in INCOME_STATEMENT_FIELDS:
            if field_name in name_lower or name_lower in field_name:
                return "income_statement"
        
        for field_name in BALANCE_SHEET_FIELDS:
            if field_name in name_lower or name_lower in field_name:
                return "balance_sheet"
        
        for field_name in CASH_FLOW_FIELDS:
            if field_name in name_lower or name_lower in field_name:
                return "cash_flow"
        
        # Default to balance sheet for unknown fields
        return "balance_sheet"

    def _calculate_ratios(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict,
        periods: List[str]
    ) -> Dict[str, Dict[str, Optional[float]]]:
        """Calculate derived financial ratios for each period."""
        ratios = {}
        
        for period in periods:
            inc = income_statement.get(period, {})
            bs = balance_sheet.get(period, {})
            cf = cash_flow.get(period, {})
            
            rev = inc.get("revenue")
            gp = inc.get("gross_profit")
            ebit = inc.get("ebit")
            ebitda = inc.get("ebitda")
            ni = inc.get("net_income")
            cogs = inc.get("cogs")
            ta = bs.get("total_assets")
            eq = bs.get("shareholders_equity")
            td = bs.get("total_debt")
            
            r: Dict[str, Optional[float]] = {}
            
            # Margins
            if rev and rev != 0:
                if gp is not None:
                    r["gross_margin"] = gp / rev
                if ebit is not None:
                    r["operating_margin"] = ebit / rev
                if ni is not None:
                    r["net_margin"] = ni / rev
                if ebitda is not None:
                    r["ebitda_margin"] = ebitda / rev
                capex = cf.get("capex")
                if capex is not None:
                    r["capex_to_revenue"] = abs(capex) / rev
                dep = inc.get("depreciation")
                if dep is not None:
                    r["depreciation_to_revenue"] = abs(dep) / rev
            
            # Returns
            if eq and eq != 0:
                if ni is not None:
                    r["roe"] = ni / eq
            if ta and ta != 0:
                if ni is not None:
                    r["roa"] = ni / ta
                if rev is not None:
                    r["asset_turnover"] = rev / ta
            
            # Leverage
            if eq and eq != 0:
                if td is not None:
                    r["debt_to_equity"] = td / eq
                if ta is not None:
                    r["equity_multiplier"] = ta / eq
            
            # Working Capital Days
            if rev and rev != 0 and cogs:
                ar = bs.get("accounts_receivable")
                inv = bs.get("inventory")
                ap = bs.get("accounts_payable")
                if ar is not None:
                    r["dso"] = (ar / rev) * 365
                if inv is not None:
                    r["dio"] = (inv / cogs) * 365
                if ap is not None:
                    r["dpo"] = (ap / cogs) * 365
            
            ratios[period] = r
        
        return ratios

    def _calculate_completeness(
        self,
        income_statement: Dict,
        balance_sheet: Dict,
        cash_flow: Dict
    ) -> Dict[str, float]:
        """Calculate completeness percentage for each section.
        
        Counts how many fields have at least one non-null value across ALL periods,
        divided by total expected fields.
        """
        def section_completeness(data: Dict, field_map: Dict) -> float:
            if not data:
                return 0.0
            total_fields = len(field_map)
            if total_fields == 0:
                return 0.0
            filled = 0
            for field_name in field_map:
                # Check if this field has ANY non-null value across any period
                for period_data in data.values():
                    if period_data.get(field_name) is not None:
                        filled += 1
                        break
            return filled / total_fields
        
        return {
            "income_statement": section_completeness(income_statement, INCOME_STATEMENT_FIELDS),
            "balance_sheet": section_completeness(balance_sheet, BALANCE_SHEET_FIELDS),
            "cash_flow": section_completeness(cash_flow, CASH_FLOW_FIELDS),
        }
