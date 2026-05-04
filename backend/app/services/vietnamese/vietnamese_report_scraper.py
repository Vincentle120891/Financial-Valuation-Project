"""
Vietnamese Financial Report Scraper Service
Searches and downloads official BCTC (Báo cáo tài chính) from:
- HOSE (hsx.vn)
- HNX (hnx.vn)
- Company official websites
- Cafef/Vietstock (as fallbacks)

Supports: Annual Reports (Báo cáo thường niên), Financial Statements (BCTC)
"""

import os
import re
import time
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

logger = logging.getLogger(__name__)

class VietnameseReportScraper:
    """Automated scraper for Vietnamese financial reports."""
    
    def __init__(self, download_dir: str = "downloads/reports"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Official sources
        self.sources = {
            'hose': 'https://hsx.vn',
            'hnx': 'https://hnx.vn',
            'upcom': 'https://upcom.com.vn',
        }
        
        # Mapping ticker to exchange (simplified, can be expanded)
        self.ticker_exchange_map = {
            'VNM': 'hose', 'VCB': 'hose', 'HPG': 'hose', 'VIC': 'hose',
            'VRE': 'hose', 'MSN': 'hose', 'MWG': 'hose', 'FPT': 'hose',
            'SAB': 'hose', 'GAS': 'hose', 'VHM': 'hose', 'VNB': 'hose',
            'ACB': 'hose', 'TCB': 'hose', 'MBB': 'hose', 'STB': 'hose',
            'HNX_INDEX': 'hnx',  # Example HNX tickers would be added here
        }

    def search_reports(self, ticker: str, year: int, report_type: str = 'annual') -> List[Dict[str, Any]]:
        """
        Search for financial reports for a given ticker and year.
        
        Args:
            ticker: Stock ticker (e.g., 'VNM')
            year: Fiscal year (e.g., 2023)
            report_type: 'annual' (Báo cáo thường niên) or 'quarterly' (BCTC quý)
            
        Returns:
            List of found reports with metadata and download URLs
        """
        ticker_clean = ticker.replace('.VN', '').upper()
        results = []
        
        logger.info(f"Searching for {report_type} reports for {ticker_clean} ({year})")
        
        # Try different sources
        strategies = [
            self._search_company_website,
            self._search_hose_hnx,
            self._search_cafef_fallback,
        ]
        
        for strategy in strategies:
            try:
                found = strategy(ticker_clean, year, report_type)
                if found:
                    results.extend(found)
                    logger.info(f"Found {len(found)} reports via {strategy.__name__}")
                    break  # Stop after first successful source
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
                
        return results

    def _search_company_website(self, ticker: str, year: int, report_type: str) -> List[Dict]:
        """Search on the company's official investor relations page."""
        # Common IR URL patterns
        domains = {
            'VNM': 'https://www.vinamilk.com.vn',
            'VCB': 'https://www.vietcombank.com.vn',
            'FPT': 'https://fpt.com.vn',
            'VIC': 'https://www.vingroup.net',
            'MWG': 'https://www.thegioididong.com',
        }
        
        base_url = domains.get(ticker)
        if not base_url:
            return []
            
        logger.info(f"Searching {base_url} for {ticker} reports")
        
        # Search paths
        search_paths = [
            '/investor-relations', '/quan-he-co-dong', '/tai-chinh',
            '/bao-cao-tai-chinh', '/bao-cao-thuong-nien', '/financial-reports'
        ]
        
        found_reports = []
        
        for path in search_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for PDF links containing ticker and year
                    links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
                    for link in links:
                        href = link.get('href')
                        text = link.get_text().lower()
                        
                        # Check if link contains ticker and year
                        if (ticker.lower() in text or ticker.lower() in href.lower()) and \
                           str(year) in text:
                            
                            pdf_url = urljoin(base_url, href)
                            report_title = link.get_text().strip()
                            
                            found_reports.append({
                                'source': 'company_website',
                                'ticker': ticker,
                                'year': year,
                                'type': report_type,
                                'url': pdf_url,
                                'title': report_title,
                                'language': 'vi'
                            })
            except Exception as e:
                logger.debug(f"Failed to search {url}: {e}")
                
        return found_reports

    def _search_hose_hnx(self, ticker: str, year: int, report_type: str) -> List[Dict]:
        """Search HOSE/HNX official information disclosure portals."""
        # Note: Direct scraping of HOSE/HNX may require authentication or have CAPTCHA
        # This is a simplified implementation; in production, use official APIs if available
        
        exchange = self.ticker_exchange_map.get(ticker, 'hose')
        base_url = self.sources.get(exchange)
        
        if not base_url:
            return []
            
        logger.info(f"Searching {exchange.upper()} portal for {ticker}")
        
        # Construct search URL (these are example patterns, actual URLs may vary)
        search_url = f"{base_url}/modules/search.aspx?keyword={ticker}&year={year}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Parse results (structure varies by exchange)
                # This is a generic parser; specific selectors needed for each exchange
                results = []
                for item in soup.select('.report-item, .disclosure-item'):
                    title = item.get_text(strip=True)
                    link = item.find('a', href=True)
                    
                    if link and str(year) in title:
                        results.append({
                            'source': exchange,
                            'ticker': ticker,
                            'year': year,
                            'type': report_type,
                            'url': urljoin(base_url, link['href']),
                            'title': title,
                            'language': 'vi'
                        })
                return results
        except Exception as e:
            logger.warning(f"HOSE/HNX search failed: {e}")
            
        return []

    def _search_cafef_fallback(self, ticker: str, year: int, report_type: str) -> List[Dict]:
        """Fallback: Search Cafef.vn (popular financial news site)."""
        base_url = "https://cafef.vn"
        search_url = f"{base_url}/tim-kiem.chn?keyword={ticker}%20{year}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                found = []
                # Look for article links about financial reports
                for item in soup.select('.news-item, .article'):
                    title = item.get_text(strip=True)
                    link = item.find('a', href=True)
                    
                    if link and ('bctc' in title.lower() or 'bao cao' in title.lower()):
                        found.append({
                            'source': 'cafef',
                            'ticker': ticker,
                            'year': year,
                            'type': report_type,
                            'url': urljoin(base_url, link['href']),
                            'title': title,
                            'language': 'vi'
                        })
                return found[:5]  # Limit results
        except Exception as e:
            logger.warning(f"Cafef search failed: {e}")
            
        return []

    def download_report(self, report_info: Dict[str, Any]) -> Optional[Path]:
        """
        Download a report given its metadata.
        
        Args:
            report_info: Dictionary containing 'url', 'ticker', 'year', etc.
            
        Returns:
            Path to downloaded file or None if failed
        """
        url = report_info.get('url')
        if not url:
            return None
            
        ticker = report_info.get('ticker', 'UNKNOWN')
        year = report_info.get('year', 'UNKNOWN')
        
        # Generate filename
        filename = f"{ticker}_BCTC_{year}.pdf"
        filepath = self.download_dir / filename
        
        if filepath.exists():
            logger.info(f"File already exists: {filepath}")
            return filepath
            
        try:
            logger.info(f"Downloading {url} to {filepath}")
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Successfully downloaded: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def auto_fetch_and_extract(self, ticker: str, year: int, 
                               report_type: str = 'annual',
                               extractor_service=None) -> Dict[str, Any]:
        """
        Complete workflow: Search -> Download -> Extract
        
        Args:
            ticker: Stock ticker
            year: Fiscal year
            report_type: 'annual' or 'quarterly'
            extractor_service: Instance of VietnamesePDFExtractor
            
        Returns:
            Extraction results dictionary
        """
        # Step 1: Search
        reports = self.search_reports(ticker, year, report_type)
        if not reports:
            return {
                'success': False,
                'error': 'No reports found',
                'ticker': ticker,
                'year': year
            }
            
        # Step 2: Download first available report
        report_info = reports[0]
        filepath = self.download_report(report_info)
        
        if not filepath:
            return {
                'success': False,
                'error': 'Failed to download report',
                'report_info': report_info
            }
            
        # Step 3: Extract data
        if extractor_service:
            try:
                extraction_result = extractor_service.extract_from_file(str(filepath))
                return {
                    'success': True,
                    'file_path': str(filepath),
                    'report_info': report_info,
                    'data': extraction_result.to_dict() if hasattr(extraction_result, 'to_dict') else extraction_result
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Extraction failed: {str(e)}',
                    'file_path': str(filepath)
                }
        else:
            return {
                'success': True,
                'file_path': str(filepath),
                'report_info': report_info,
                'message': 'Downloaded successfully (no extractor provided)'
            }


# Convenience function
def fetch_vietnamese_report(ticker: str, year: int, report_type: str = 'annual'):
    """Quick helper to fetch a Vietnamese financial report."""
    scraper = VietnameseReportScraper()
    return scraper.search_reports(ticker, year, report_type)
