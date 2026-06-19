"""
SEC EDGAR Service for fetching 10-K and 10-Q filings.

SEC EDGAR does not require an API key, but requires a proper User-Agent header
with company name and email to avoid rate limiting.

Example User-Agent: "Your Company Name admin@yourcompany.com"
"""

import aiohttp
import asyncio
import os
from typing import Optional, Dict, List, Any
from fastapi import Request
from loguru import logger


# =============================================================================
# XBRL TAG DEFINITIONS: comprehensive financial data extraction
# =============================================================================

INCOME_STATEMENT_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "cogs": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "sg_and_a": ["SellingGeneralAndAdministrativeExpense"],
    "research_development": ["ResearchAndDevelopmentExpense"],
    "depreciation": ["DepreciationAndAmortization", "DepreciationDepletionAndAmortization"],
    "interest_expense": ["InterestExpense", "InterestExpenseDebt", "InterestAndDebtExpense"],
    "interest_income": [
        "InterestIncome",
        "InterestIncomeExpenseNetNonoperating",
        "InterestIncomeOther",
        "InterestAndDividendIncomeOperating",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "PretaxIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
    ],
    "income_tax_expense": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss"],
    "ebitda": [],  # Computed from components, not directly in XBRL
}

BALANCE_SHEET_TAGS = {
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"],
    "accounts_receivable": ["AccountsReceivableNetCurrent"],
    "inventory": ["InventoryNet"],
    "total_current_assets": ["AssetsCurrent"],
    "ppe_gross": ["PropertyPlantAndEquipmentGross"],
    "accumulated_depreciation": [
        "PropertyPlantAndEquipmentAccumulatedDepreciation",
        "AccumulatedDepreciation",
    ],
    "total_assets": ["Assets"],
    "accounts_payable": ["AccountsPayableCurrent"],
    "total_current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": ["LongTermDebtNoncurrent"],
    "short_term_debt": ["LongTermDebtCurrent", "DebtCurrent"],
    "total_debt": [],  # Computed: long_term + short_term
    "deferred_tax_assets": ["DeferredTaxAssetsNet", "DeferredIncomeTaxAssetsNet"],
    "deferred_tax_liabilities": ["DeferredIncomeTaxLiabilitiesNet"],
    "total_liabilities": ["Liabilities"],
    "common_equity": ["CommonStocksIncludingAdditionalPaidInCapital", "CommonStockValue"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "total_equity": ["StockholdersEquity"],
    "tax_loss_carryforward": ["DeferredTaxAssetsOperatingLossCarryforwards"],
}

CASH_FLOW_TAGS = {
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditure": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "dividends_paid": ["PaymentsOfDividends"],
    "debt_repayments": ["RepaymentsOfLongTermDebt"],
    "debt_issuance": ["ProceedsFromIssuanceOfLongTermDebt"],
    "stock_buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "interest_paid": [
        "InterestPaidSupplementalData",
        "InterestPaid",
        "InterestPaidCash",
        "PaymentsOfInterest",
        "CashPaidForInterest",
        "InterestExpenseDebt",
    ],
    "taxes_paid": ["IncomeTaxesPaid", "IncomeTaxesRefundPaid"],
}

OTHER_TAGS = {
    "shares_outstanding": ["EntityCommonStockSharesOutstanding"],
    "earnings_per_share": ["EarningsPerShareBasic"],
}


class SecEdgarService:
    """Service for interacting with SEC EDGAR database."""

    BASE_URL = "https://data.sec.gov"
    SEARCH_URL = "https://search.sec.gov/api/search"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    @staticmethod
    def get_email(request: Optional[Request] = None) -> Optional[str]:
        """
        Get SEC EDGAR email with priority: request header > environment variable.

        Args:
            request: FastAPI request object (optional)

        Returns:
            Email from request header if available, else from environment, else None
        """
        # Priority 1: Check request state (from header)
        if request:
            api_keys = getattr(request.state, 'api_keys', {})
            request_email = api_keys.get('sec_edgar')
            if request_email:
                logger.debug("Using SEC EDGAR email from request header")
                return request_email

        # Priority 2: Fallback to environment variable
        env_email = os.getenv('SEC_EDGAR_EMAIL')
        if env_email:
            logger.debug("Using SEC EDGAR email from environment variable")
            return env_email

        # No email available
        logger.warning("SEC EDGAR email not configured (neither in request header nor environment)")
        return None

    async def _get_session(self, email: str, company_name: str = "Company") -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper User-Agent."""
        if self.session is None or self.session.closed:
            # SEC requires User-Agent in format: "Company Name (email)"
            user_agent = f"{company_name} ({email})"

            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": user_agent,
                    "Accept": "application/json",
                }
            )
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    # -------------------------------------------------------------------------
    # XBRL extraction helper
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_xbrl_field(us_gaap: dict, tags: list, max_years: int = 4) -> Dict[str, Any]:
        """
        Extract a financial field from XBRL data, trying multiple tag fallbacks.

        Returns a dict keyed by fiscal-year string (e.g. ``{"2024": 12345, …}``),
        limited to *max_years* most recent years, deduplicated by end date.
        """
        data: list = []
        for tag in tags:
            data = us_gaap.get(tag, {}).get("units", {}).get("USD", [])
            if data:
                break

        yearly: Dict[int, Dict[str, Any]] = {}
        for item in data:
            fy = item.get("fy")
            if fy and item.get("val") is not None:
                end_date = item.get("end", "")
                if fy not in yearly or end_date > yearly[fy].get("end", ""):
                    yearly[fy] = {"value": item["val"], "end": end_date}

        return {str(fy): d["value"] for fy, d in sorted(yearly.items(), reverse=True)[:max_years]}

    # -------------------------------------------------------------------------
    # Main XBRL fetch — comprehensive extraction
    # -------------------------------------------------------------------------

    async def fetch_company_facts_xbrl(
        self,
        ticker: str,
        email: str,
        company_name: str = "Company"
    ) -> Dict[str, Any]:
        """
        Fetch comprehensive XBRL company facts for all key financial fields.

        Uses SEC EDGAR Company Facts API to extract Income Statement, Balance Sheet,
        Cash Flow, and Other data for up to 4 historical fiscal years.

        Args:
            ticker: Stock ticker symbol
            email: Contact email for rate limit compliance
            company_name: Company name for User-Agent header

        Returns:
            Dictionary with nested ``income_statement``, ``balance_sheet``,
            ``cash_flow``, ``other`` sections plus backward-compatible flat keys.
        """
        try:
            session = await self._get_session(email, company_name)

            # Get CIK for the ticker
            cik = await self._get_cik(ticker, email, company_name)
            if not cik:
                logger.warning(f"Could not find CIK for ticker: {ticker}")
                return {"success": False, "error": f"CIK not found for {ticker}"}

            # Fetch company facts (XBRL data)
            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

            async with session.get(facts_url) as response:
                if response.status != 200:
                    logger.warning(f"SEC EDGAR returned status {response.status} for {ticker}")
                    return {"success": False, "error": f"SEC EDGAR returned status {response.status}"}

                data = await response.json()
                us_gaap = data.get("facts", {}).get("us-gaap", {})

                # --- Extract all sections using the helper ---
                income_statement = {}
                for field_name, tags in INCOME_STATEMENT_TAGS.items():
                    if not tags:
                        continue
                    extracted = self._extract_xbrl_field(us_gaap, tags)
                    if extracted:
                        income_statement[field_name] = extracted

                balance_sheet = {}
                for field_name, tags in BALANCE_SHEET_TAGS.items():
                    if not tags:
                        continue
                    extracted = self._extract_xbrl_field(us_gaap, tags)
                    if extracted:
                        balance_sheet[field_name] = extracted

                cash_flow = {}
                for field_name, tags in CASH_FLOW_TAGS.items():
                    if not tags:
                        continue
                    extracted = self._extract_xbrl_field(us_gaap, tags)
                    if extracted:
                        cash_flow[field_name] = extracted
                    elif field_name in ("interest_paid", "taxes_paid"):
                        logger.info(
                            f"SEC EDGAR XBRL: No data found for '{field_name}' "
                            f"(tried tags: {tags}) for {ticker}"
                        )

                other = {}
                for field_name, tags in OTHER_TAGS.items():
                    if not tags:
                        continue
                    extracted = self._extract_xbrl_field(us_gaap, tags)
                    if extracted:
                        other[field_name] = extracted

                # --- Compute derived fields ---

                # total_debt = long_term_debt + short_term_debt
                lt_debt = balance_sheet.get("long_term_debt", {})
                st_debt = balance_sheet.get("short_term_debt", {})
                all_years = set(lt_debt.keys()) | set(st_debt.keys())
                total_debt = {}
                for yr in all_years:
                    lt = lt_debt.get(yr)
                    st = st_debt.get(yr)
                    if lt is not None or st is not None:
                        total_debt[yr] = (lt or 0) + (st or 0)
                if total_debt:
                    balance_sheet["total_debt"] = total_debt

                # ebitda ≈ net_income + interest_expense + income_tax_expense + depreciation
                ni = income_statement.get("net_income", {})
                ie = income_statement.get("interest_expense", {})
                ite = income_statement.get("income_tax_expense", {})
                dep = income_statement.get("depreciation", {})
                all_years = set()
                for d in (ni, ie, ite, dep):
                    all_years |= set(d.keys())
                ebitda = {}
                for yr in all_years:
                    components = [ni.get(yr), ie.get(yr), ite.get(yr), dep.get(yr)]
                    if all(c is not None for c in components):
                        ebitda[yr] = sum(components)
                if ebitda:
                    income_statement["ebitda"] = ebitda

                # --- Build result ---
                total_fields = (
                    len(income_statement)
                    + len(balance_sheet)
                    + len(cash_flow)
                    + len(other)
                )
                logger.info(
                    f"SEC EDGAR: Extracted {len(income_statement)} income, "
                    f"{len(balance_sheet)} balance sheet, {len(cash_flow)} cash flow, "
                    f"{len(other)} other fields for {ticker}"
                )

                return {
                    "success": True,
                    # Nested sections (new comprehensive data)
                    "income_statement": income_statement,
                    "balance_sheet": balance_sheet,
                    "cash_flow": cash_flow,
                    "other": other,
                    # Backward-compatible flat keys for existing consumers
                    "ppe_gross": balance_sheet.get("ppe_gross", {}),
                    "accumulated_depreciation": balance_sheet.get("accumulated_depreciation", {}),
                    "total_assets": balance_sheet.get("total_assets", {}),
                    "tax_loss_carryforward": balance_sheet.get("tax_loss_carryforward", {}),
                    "deferred_tax_assets": balance_sheet.get("deferred_tax_assets", {}),
                    "interest_expense": income_statement.get("interest_expense", {}),
                    "interest_income": income_statement.get("interest_income", {}),
                    "pretax_income": income_statement.get("pretax_income", {}),
                    "interest_paid": cash_flow.get("interest_paid", {}),
                    "source": "SEC EDGAR XBRL",
                    "total_fields_extracted": total_fields,
                }

        except Exception as e:
            logger.error(f"Error fetching SEC EDGAR XBRL for {ticker}: {e}")
            return {"success": False, "error": str(e)}

    async def search_company_filings(
        self,
        ticker: str,
        email: str,
        company_name: str = "Company",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for company filings by ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., AAPL, MSFT)
            email: Contact email for rate limit compliance
            company_name: Company name for User-Agent header
            limit: Maximum number of filings to return

        Returns:
            Dictionary containing filing metadata and access URLs
        """
        try:
            session = await self._get_session(email, company_name)

            # Search for company by ticker
            search_params = {
                "ticker": ticker,
                "start": 0,
                "count": limit
            }

            # Use SEC EDGAR Company Facts API
            # First get CIK (Central Index Key) for the ticker
            cik = await self._get_cik(ticker, email, company_name)

            if not cik:
                logger.warning(f"Could not find CIK for ticker: {ticker}")
                return {
                    "success": False,
                    "error": f"No SEC filings found for ticker: {ticker}",
                    "filings": [],
                    "filings_count": 0
                }

            # Get recent filings for this CIK
            filings_url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            async with session.get(filings_url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract recent 10-K and 10-Q filings
                    filings = self._parse_filings(data, limit)

                    return {
                        "success": True,
                        "cik": cik,
                        "company_name": data.get("name", ""),
                        "filings": filings,
                        "filings_count": len(filings),
                        "source": "SEC EDGAR"
                    }
                else:
                    logger.error(f"SEC EDGAR API error: {response.status}")
                    return {
                        "success": False,
                        "error": f"SEC EDGAR API returned status {response.status}",
                        "filings": [],
                        "filings_count": 0
                    }

        except Exception as e:
            logger.error(f"SEC EDGAR search error for {ticker}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "filings": [],
                "filings_count": 0
            }

    async def _get_cik(self, ticker: str, email: str, company_name: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker symbol.

        Args:
            ticker: Stock ticker symbol
            email: Contact email
            company_name: Company name

        Returns:
            CIK string or None if not found
        """
        try:
            session = await self._get_session(email, company_name)

            # Use tickersymbol lookup
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&Find=Search&owner=exclude&action=getcompany"

            # Alternative: Use the company tickers JSON file
            async with session.get("https://www.sec.gov/files/company_tickers.json") as response:
                if response.status == 200:
                    data = await response.json()

                    # Search for ticker in the data
                    for key, value in data.items():
                        if value.get("ticker", "").upper() == ticker.upper():
                            cik = str(value.get("cik_str", "")).zfill(10)
                            logger.info(f"Found CIK {cik} for ticker {ticker}")
                            return cik

            # Fallback: Try direct CIK lookup
            async with session.get(
                f"https://www.sec.gov/cgi-bin/browse-edgar",
                params={"CIK": ticker, "action": "getcompany"}
            ) as response:
                if response.status == 200:
                    # Parse HTML to extract CIK (simplified)
                    html = await response.text()
                    # This is a simplified approach - in production, use proper HTML parsing
                    if "CIK" in html:
                        # Extract CIK from HTML
                        import re
                        match = re.search(r'CIK\s+(\d+)', html)
                        if match:
                            return match.group(1).zfill(10)

            return None

        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {e}")
            return None

    def _parse_filings(self, data: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """
        Parse SEC EDGAR response to extract relevant filings.

        Args:
            data: Raw SEC EDGAR JSON response
            limit: Maximum number of filings to return

        Returns:
            List of filing dictionaries
        """
        filings = []

        # SEC EDGAR submissions format
        recent_filings = data.get("filings", {}).get("recent", {})

        accessions = recent_filings.get("accessionNumber", [])
        forms = recent_filings.get("form", [])
        dates = recent_filings.get("filingDate", [])
        reports = recent_filings.get("reportDate", [])

        logger.debug(f"SEC EDGAR: {len(forms)} total forms in submissions, scanning up to {limit}")

        # Filter for 10-K and 10-Q only
        for i, form_type in enumerate(forms[:min(limit, len(forms))]):
            if not isinstance(form_type, str):
                continue
            if form_type in ["10-K", "10-Q", "10-K/A", "10-Q/A"]:
                accession = accessions[i] if i < len(accessions) else ""
                filing_date = dates[i] if i < len(dates) else ""
                report_date = reports[i] if i < len(reports) else ""

                # Build document URL
                cik = data.get("cik", "")
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}.txt"

                filings.append({
                    "accession_number": accession,
                    "form_type": form_type,
                    "filing_date": filing_date,
                    "report_date": report_date,
                    "document_url": doc_url,
                    "is_amended": "/A" in form_type
                })

        logger.info(f"SEC EDGAR: Found {len(filings)} 10-K/10-Q filings out of {len(forms)} total forms")
        return filings

    async def fetch_filing_details(
        self,
        accession_number: str,
        cik: str,
        email: str,
        company_name: str = "Company"
    ) -> Dict[str, Any]:
        """
        Fetch detailed content of a specific filing.

        Args:
            accession_number: SEC accession number
            cik: Company CIK
            email: Contact email
            company_name: Company name

        Returns:
            Filing content and metadata
        """
        try:
            session = await self._get_session(email, company_name)

            # Remove dashes from accession number for URL
            clean_accession = accession_number.replace("-", "")

            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{clean_accession}.txt"

            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()

                    return {
                        "success": True,
                        "accession_number": accession_number,
                        "content": content,
                        "content_length": len(content)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch filing: {response.status}"
                    }

        except Exception as e:
            logger.error(f"Error fetching filing {accession_number}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_sec_edgar_service: Optional[SecEdgarService] = None


def get_sec_edgar_service() -> SecEdgarService:
    """Get singleton instance of SecEdgarService."""
    global _sec_edgar_service
    if _sec_edgar_service is None:
        _sec_edgar_service = SecEdgarService()
    return _sec_edgar_service
