"""
SEC EDGAR Service for fetching 10-K and 10-Q filings.

SEC EDGAR does not require an API key, but requires a proper User-Agent header
with company name and email to avoid rate limiting.

Example User-Agent: "Your Company Name admin@yourcompany.com"
"""

import aiohttp
import asyncio
from typing import Optional, Dict, List, Any
from loguru import logger


class SecEdgarService:
    """Service for interacting with SEC EDGAR database."""
    
    BASE_URL = "https://data.sec.gov"
    SEARCH_URL = "https://search.sec.gov/api/search"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self, email: str, company_name: str = "Company") -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper User-Agent."""
        if self.session is None or self.session.closed:
            # SEC requires User-Agent in format: "Company Name (email)"
            user_agent = f"{company_name} ({email})"
            
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": user_agent,
                    "Accept": "application/json",
                    "Host": "data.sec.gov"
                }
            )
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
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
        
        # Filter for 10-K and 10-Q only
        for i, form_type in enumerate(forms[:min(limit, len(forms))]):
            if form_type in ["10-K", "10-Q", "10-K/A", "10-Q/A"]:
                accession = accessions[i] if i < len(accessions) else ""
                filing_date = dates[i] if i < len(dates) else ""
                report_date = reports[i] if i < len(reports) else ""
                
                # Build document URL
                # Accession number format: XXXXXXXXXX-XX-XXXXXX
                # URL format: https://www.sec.gov/Archives/edgar/data/CIK/XXXXXXXXXX-XX-XXXXXX.txt
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
