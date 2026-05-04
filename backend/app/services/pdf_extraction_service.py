"""
PDF Extraction Service for Vietnamese Market Reports

Supports extraction of financial data from:
- Annual Reports (Báo cáo thường niên)
- Financial Statements (Báo cáo tài chính) - TT99 compliant
- Prospectus (Bản cáo bạch)
- HOSE/HNX official filings

Sources:
- HOSE (Ho Chi Minh Stock Exchange)
- HNX (Hanoi Stock Exchange)
- Cafef.vn, Vietstock.vn, FiinPro
- Company websites

Implementation Options:
1. Text-based PDF parsing (pdfplumber, PyPDF2)
2. Table extraction (camelot-py, tabula-py)
3. OCR for scanned documents (pytesseract, pdf2image)
4. Vietnamese language processing (pyvi, underthesea)

TT99 Compliance:
- Maps extracted data to Thông Tư 99/2025/TT-BTC templates
- Supports Mẫu số B 01, B 02, B 03 - DN
- Validates cross-statement linkages
- Preserves Mã số (line codes) without renumbering
"""

import os
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import io

logger = logging.getLogger(__name__)

# Import TT99 models for validation and mapping
try:
    from app.models.vietnamese.vietnamese_financial_model import (
        BalanceSheetTT99,
        IncomeStatementTT99,
        CashFlowStatementTT99,
        LineItem,
        CurrencyUnit,
        STANDARD_LINE_ITEMS_B01,
        STANDARD_LINE_ITEMS_B02,
        STANDARD_LINE_ITEMS_B03,
        create_vietnamese_line_item,
        INTERNATIONAL_MAPPING
    )
    TT99_AVAILABLE = True
except ImportError:
    TT99_AVAILABLE = False
    logger.warning("TT99 models not available. Install with: pip install vietnamese-financial-model")


@dataclass
class ExtractedFinancialData:
    """Container for extracted financial data from PDF"""
    company_name: str = ""
    ticker: str = ""
    fiscal_year: int = 0
    currency: str = "VND"
    report_type: str = ""  # Annual Report, Financial Statement, etc.
    
    # Income Statement
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_expenses: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    net_income: Optional[float] = None
    
    # Balance Sheet
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    non_current_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    property_plant_equipment: Optional[float] = None
    total_debt: Optional[float] = None
    
    # Cash Flow
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    
    # Key Ratios
    roe: Optional[float] = None
    roa: Optional[float] = None
    profit_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    
    # Metadata
    extraction_method: str = ""
    confidence_score: float = 0.0
    source_file: str = ""
    extraction_date: str = ""
    raw_tables: List[Dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class VietnamesePDFExtractor:
    """
    Main class for extracting financial data from Vietnamese PDF reports.
    
    Supports multiple extraction methods:
    - pdfplumber: Best for text-based PDFs with tables
    - camelot-py: Best for structured table extraction
    - tabula-py: Alternative table extraction
    - pytesseract: OCR for scanned documents
    """
    
    # Vietnamese financial terms mapping (with diacritics and common variations)
    VIETNAMESE_TERMS = {
        # Income Statement
        'doanh_thu': 'revenue',
        'doanh_thu_thuan': 'net_revenue',
        'giá_vốn_hàng_bán': 'cost_of_revenue',
        'loi_nhuan_gop': 'gross_profit',  # Without diacritics variant
        'lợi_nhập_gộp': 'gross_profit',
        'chi_phí_bán_hàng': 'selling_expenses',
        'chi_phi_ban_hang': 'selling_expenses',  # Without diacritics
        'chi_phí_quản_lý_doanh_nghiệp': 'administrative_expenses',
        'chi_phi_quan_ly_doanh_nghiep': 'administrative_expenses',  # Without diacritics
        'chi_phí_hoạt_động': 'operating_expenses',
        'lợi_nhập_từ_hoạt_động_kinh_doanh': 'operating_profit',
        'ebitda': 'ebitda',
        'lợi_nhập_trước_thuế': 'profit_before_tax',
        'thuế_thu_nhập_doanh_nghiệp': 'income_tax',
        'loi_nhuan_sau_thue': 'net_income',  # Without diacritics variant
        'lợi_nhập_sau_thuế': 'net_income',
        'loi_nhuan_rong': 'net_income',
        'lợi_nhập_ròng': 'net_income',
        
        # Balance Sheet
        'tổng_tài_sản': 'total_assets',
        'tong_tai_san': 'total_assets',  # Without diacritics
        'tài_sản_ngắn_hạn': 'current_assets',
        'tai_san_ngan_han': 'current_assets',  # Without diacritics
        'tài_sản_dài_hạn': 'non_current_assets',
        'tai_san_dai_han': 'non_current_assets',  # Without diacritics
        'tổng_nợ_phải_trả': 'total_liabilities',
        'tong_no_phai_tra': 'total_liabilities',  # Without diacritics
        'nợ_ngắn_hạn': 'current_liabilities',
        'no_ngan_han': 'current_liabilities',  # Without diacritics
        'nợ_dài_hạn': 'long_term_debt',
        'no_dai_han': 'long_term_debt',  # Without diacritics
        'vốn_chủ_sở_hữu': 'total_equity',
        'von_chu_so_huu': 'total_equity',  # Without diacritics
        'tien_va_tuong_duong_tien': 'cash_and_equivalents',  # Full phrase without diacritics
        'tiền_và_tương_đương_tiền': 'cash_and_equivalents',
        'phải_thu_khách_hàng': 'accounts_receivable',
        'phai_thu_khach_hang': 'accounts_receivable',  # Without diacritics
        'hàng_tồn_kho': 'inventory',
        'hang_ton_kho': 'inventory',  # Without diacritics
        'tai_san_co_dinh': 'property_plant_equipment',  # Without diacritics
        'tài_sản_cố_định': 'property_plant_equipment',
        'nợ_vay': 'total_debt',
        'no_vay': 'total_debt',  # Without diacritics
        
        # Cash Flow
        'lưu_chuyển_tiền_từ_hoạt_động_kinh_doanh': 'operating_cash_flow',
        'lưu_chuyển_tiền_từ_hoạt_động_đầu_tư': 'investing_cash_flow',
        'lưu_chuyển_tiền_từ_hoạt_động_tài_chính': 'financing_cash_flow',
        'lưu_chuyển_tiền_tự_do': 'free_cash_flow',
        'mua_sắm_tscđ': 'capex',
        
        # Ratios
        'tỷ_suất_lợi_nhận_trên_vốn_chủ_sở_hữu': 'roe',
        'tỷ_suất_lợi_nhận_trên_tổng_tài_sản': 'roa',
        'biên_lợi_nhận': 'profit_margin',
    }
    
    def __init__(self, extraction_method: str = "auto"):
        """
        Initialize the extractor.
        
        Args:
            extraction_method: One of 'auto', 'pdfplumber', 'camelot', 'tabula', 'ocr'
        """
        self.extraction_method = extraction_method
        self._initialize_libraries()
    
    def _initialize_libraries(self):
        """Initialize required libraries with fallback handling."""
        self.pdfplumber = None
        self.camelot = None
        self.tabula = None
        self.pytesseract = None
        self.pdf2image = None
        self.pyvi = None
        
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            logger.debug("pdfplumber loaded successfully")
        except ImportError:
            logger.warning("pdfplumber not available. Install with: pip install pdfplumber")
        
        try:
            import camelot
            self.camelot = camelot
            logger.debug("camelot loaded successfully")
        except ImportError:
            logger.warning("camelot not available. Install with: pip install camelot-py[cv]")
        
        try:
            import tabula
            self.tabula = tabula
            logger.debug("tabula loaded successfully")
        except ImportError:
            logger.warning("tabula not available. Install with: pip install tabula-py")
        
        try:
            import pytesseract
            self.pytesseract = pytesseract
            logger.debug("pytesseract loaded successfully")
        except ImportError:
            logger.warning("pytesseract not available. Install with: pip install pytesseract")
        
        try:
            from pdf2image import pdf2page
            self.pdf2image = pdf2page
            logger.debug("pdf2image loaded successfully")
        except ImportError:
            logger.warning("pdf2image not available. Install with: pip install pdf2image")
        
        try:
            from pyvi import VITokenizer
            self.pyvi = VITokenizer
            logger.debug("pyvi loaded successfully")
        except ImportError:
            logger.warning("pyvi not available. Install with: pip install pyvi")
    
    def extract_from_file(self, file_path: str) -> ExtractedFinancialData:
        """
        Extract financial data from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            ExtractedFinancialData object with TT99 validation if available
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        logger.info(f"Extracting data from: {file_path}")
        
        # Determine best extraction method
        method = self.extraction_method
        if method == "auto":
            method = self._detect_best_method(file_path)
        
        # Extract based on method
        if method == "pdfplumber" and self.pdfplumber:
            return self._extract_with_pdfplumber(file_path)
        elif method == "camelot" and self.camelot:
            return self._extract_with_camelot(file_path)
        elif method == "tabula" and self.tabula:
            return self._extract_with_tabula(file_path)
        elif method == "ocr" and self.pytesseract:
            return self._extract_with_ocr(file_path)
        else:
            # Fallback to pdfplumber if available
            if self.pdfplumber:
                return self._extract_with_pdfplumber(file_path)
            else:
                raise RuntimeError(
                    "No suitable extraction method available. "
                    "Please install at least one of: pdfplumber, camelot-py, tabula-py"
                )
    
    def extract_to_tt99_format(self, file_path: str) -> Dict[str, Any]:
        """
        Extract financial data and convert to TT99 standardized format.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing:
            - balance_sheet: BalanceSheetTT99 object
            - income_statement: IncomeStatementTT99 object
            - cash_flow: CashFlowStatementTT99 object (if cash flow data found)
            - validation_results: Validation status for each statement
        """
        if not TT99_AVAILABLE:
            raise ImportError("TT99 models not available. Please install vietnamese-financial-model")
        
        # First extract raw data
        extracted_data = self.extract_from_file(file_path)
        
        # Convert to TT99 format
        result = {
            'balance_sheet': self._convert_to_balance_sheet_tt99(extracted_data),
            'income_statement': self._convert_to_income_statement_tt99(extracted_data),
            'cash_flow': self._convert_to_cash_flow_tt99(extracted_data),
            'validation_results': {}
        }
        
        # Validate each statement
        if result['balance_sheet']:
            is_valid, errors = result['balance_sheet'].validate()
            result['validation_results']['balance_sheet'] = {'valid': is_valid, 'errors': errors}
        
        if result['income_statement']:
            is_valid, errors = result['income_statement'].validate()
            result['validation_results']['income_statement'] = {'valid': is_valid, 'errors': errors}
        
        if result['cash_flow']:
            is_valid, errors = result['cash_flow'].validate()
            result['validation_results']['cash_flow'] = {'valid': is_valid, 'errors': errors}
        
        return result
    
    def _convert_to_balance_sheet_tt99(self, data: ExtractedFinancialData) -> Optional[BalanceSheetTT99]:
        """Convert extracted data to TT99 Balance Sheet format"""
        if not TT99_AVAILABLE or not any([
            data.total_assets, data.total_liabilities, data.total_equity
        ]):
            return None
        
        bs = BalanceSheetTT99(
            company_name=data.company_name,
            fiscal_year=data.fiscal_year,
            currency_unit=CurrencyUnit.VND,
            total_assets=data.total_assets,
            total_liabilities=data.total_liabilities,
            total_equity=data.total_equity,
            extraction_method=data.extraction_method,
            confidence_score=data.confidence_score,
            source_file=data.source_file
        )
        
        # Map extracted fields to TT99 line items
        if data.cash_and_equivalents:
            bs.assets_short_term.append(create_vietnamese_line_item('110', data.cash_and_equivalents))
        if data.accounts_receivable:
            bs.assets_short_term.append(create_vietnamese_line_item('131', data.accounts_receivable))
        if data.inventory:
            bs.assets_short_term.append(create_vietnamese_line_item('141', data.inventory))
        if data.property_plant_equipment:
            bs.assets_long_term.append(create_vietnamese_line_item('221', data.property_plant_equipment))
        
        return bs
    
    def _convert_to_income_statement_tt99(self, data: ExtractedFinancialData) -> Optional[IncomeStatementTT99]:
        """Convert extracted data to TT99 Income Statement format"""
        if not TT99_AVAILABLE or not any([
            data.revenue, data.gross_profit, data.net_income
        ]):
            return None
        
        is_stmt = IncomeStatementTT99(
            company_name=data.company_name,
            fiscal_year=data.fiscal_year,
            currency_unit=CurrencyUnit.VND,
            net_revenue=data.revenue,
            cost_of_goods_sold=data.cost_of_revenue,
            gross_profit=data.gross_profit,
            operating_profit=data.ebit,
            net_profit=data.net_income,
            extraction_method=data.extraction_method,
            confidence_score=data.confidence_score,
            source_file=data.source_file
        )
        
        return is_stmt
    
    def _convert_to_cash_flow_tt99(self, data: ExtractedFinancialData) -> Optional[CashFlowStatementTT99]:
        """Convert extracted data to TT99 Cash Flow Statement format"""
        if not TT99_AVAILABLE or not any([
            data.operating_cash_flow, data.investing_cash_flow, data.financing_cash_flow
        ]):
            return None
        
        cf = CashFlowStatementTT99(
            company_name=data.company_name,
            fiscal_year=data.fiscal_year,
            currency_unit=CurrencyUnit.VND,
            method='indirect',  # Default assumption
            operating_cash_flow=data.operating_cash_flow,
            investing_cash_flow=data.investing_cash_flow,
            financing_cash_flow=data.financing_cash_flow,
            capex=data.capex,
            extraction_method=data.extraction_method,
            confidence_score=data.confidence_score,
            source_file=data.source_file
        )
        
        return cf
    
    def _detect_best_method(self, file_path: str) -> str:
        """Detect the best extraction method for a given PDF."""
        # Check if PDF is text-based or scanned
        try:
            if self.pdfplumber:
                with self.pdfplumber.open(file_path) as pdf:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text()
                    if text and len(text.strip()) > 100:
                        # Has substantial text, check for tables
                        tables = first_page.find_tables()
                        if tables and len(tables) > 0:
                            return "pdfplumber"
                        return "pdfplumber"
            
            # If pdfplumber finds little text, might be scanned
            return "ocr"
        except Exception as e:
            logger.warning(f"Error detecting method: {e}")
            return "pdfplumber"
    
    def _extract_with_pdfplumber(self, file_path: str) -> ExtractedFinancialData:
        """Extract data using pdfplumber."""
        result = ExtractedFinancialData(
            extraction_method="pdfplumber",
            source_file=file_path,
            extraction_date=datetime.now().isoformat()
        )
        
        all_tables = []
        full_text = []
        
        try:
            with self.pdfplumber.open(file_path) as pdf:
                logger.info(f"Processing {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                    
                    # Extract tables
                    tables = page.find_tables()
                    if tables:
                        for table in tables:
                            table_data = table.extract()
                            if table_data:
                                all_tables.append({
                                    'page': page_num + 1,
                                    'data': table_data
                                })
                                result.raw_tables.append({
                                    'page': page_num + 1,
                                    'rows': table_data
                                })
            
            # Process extracted data
            full_text_str = "\n".join(full_text)
            self._parse_financial_data(result, full_text_str, all_tables)
            
            # Calculate confidence score
            fields_found = sum(1 for f in result.__dict__.values() 
                             if f is not None and isinstance(f, (int, float)))
            result.confidence_score = min(1.0, fields_found / 10.0)
            
        except Exception as e:
            logger.error(f"Error extracting with pdfplumber: {e}")
            result.notes.append(f"Extraction error: {str(e)}")
        
        return result
    
    def _extract_with_camelot(self, file_path: str) -> ExtractedFinancialData:
        """Extract tables using camelot."""
        result = ExtractedFinancialData(
            extraction_method="camelot",
            source_file=file_path,
            extraction_date=datetime.now().isoformat()
        )
        
        try:
            # Try lattice mode first (for tables with borders)
            tables = self.camelot.read_pdf(file_path, flavor='lattice', pages='all')
            
            if len(tables) == 0:
                # Try stream mode (for tables without borders)
                tables = self.camelot.read_pdf(file_path, flavor='stream', pages='all')
            
            logger.info(f"Extracted {len(tables)} tables with camelot")
            
            for i, table in enumerate(tables):
                table_data = table.df.values.tolist()
                result.raw_tables.append({
                    'table_index': i,
                    'page': table.page,
                    'rows': table_data
                })
            
            # Parse financial data from tables
            self._parse_financial_data(result, "", result.raw_tables)
            
            fields_found = sum(1 for f in result.__dict__.values() 
                             if f is not None and isinstance(f, (int, float)))
            result.confidence_score = min(1.0, fields_found / 10.0)
            
        except Exception as e:
            logger.error(f"Error extracting with camelot: {e}")
            result.notes.append(f"Camelot extraction error: {str(e)}")
        
        return result
    
    def _extract_with_tabula(self, file_path: str) -> ExtractedFinancialData:
        """Extract tables using tabula-py."""
        result = ExtractedFinancialData(
            extraction_method="tabula",
            source_file=file_path,
            extraction_date=datetime.now().isoformat()
        )
        
        try:
            # Extract all tables
            tables = self.tabula.read_pdf(file_path, pages='all', multiple_tables=True)
            
            logger.info(f"Extracted {len(tables)} tables with tabula")
            
            for i, table in enumerate(tables):
                table_data = table.values.tolist()
                result.raw_tables.append({
                    'table_index': i,
                    'rows': table_data
                })
            
            # Parse financial data
            self._parse_financial_data(result, "", result.raw_tables)
            
            fields_found = sum(1 for f in result.__dict__.values() 
                             if f is not None and isinstance(f, (int, float)))
            result.confidence_score = min(1.0, fields_found / 10.0)
            
        except Exception as e:
            logger.error(f"Error extracting with tabula: {e}")
            result.notes.append(f"Tabula extraction error: {str(e)}")
        
        return result
    
    def _extract_with_ocr(self, file_path: str) -> ExtractedFinancialData:
        """Extract text using OCR (for scanned documents)."""
        result = ExtractedFinancialData(
            extraction_method="ocr",
            source_file=file_path,
            extraction_date=datetime.now().isoformat()
        )
        
        if not self.pytesseract or not self.pdf2image:
            result.notes.append("OCR libraries not available")
            return result
        
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300)
            logger.info(f"Converted {len(images)} pages to images for OCR")
            
            full_text = []
            
            for i, image in enumerate(images):
                # Perform OCR
                text = pytesseract.image_to_string(image, lang='vie+eng')
                full_text.append(text)
            
            full_text_str = "\n".join(full_text)
            
            # Parse financial data from OCR text
            self._parse_financial_data(result, full_text_str, [])
            
            # OCR typically has lower confidence
            fields_found = sum(1 for f in result.__dict__.values() 
                             if f is not None and isinstance(f, (int, float)))
            result.confidence_score = min(0.8, fields_found / 15.0)
            
        except Exception as e:
            logger.error(f"Error extracting with OCR: {e}")
            result.notes.append(f"OCR extraction error: {str(e)}")
        
        return result
    
    def _parse_financial_data(self, result: ExtractedFinancialData, 
                             text: str, tables: List[Dict]):
        """Parse financial data from extracted text and tables."""
        
        # Helper function to parse Vietnamese numbers
        def parse_number(value: str) -> Optional[float]:
            if not value:
                return None
            try:
                # Remove commas, spaces, and common Vietnamese formatting
                cleaned = re.sub(r'[,\s]', '', str(value))
                # Handle Vietnamese decimal notation (comma as decimal separator)
                if ',' in cleaned and '.' not in cleaned:
                    cleaned = cleaned.replace(',', '.')
                return float(cleaned)
            except (ValueError, TypeError):
                return None
        
        # Search in text for key-value patterns
        if text:
            # Look for company name and ticker
            company_patterns = [
                r'Công ty (?:Cổ phần|TNHH)?\s+([^\n]+)',
                r'Tên công ty:\s*([^\n]+)',
            ]
            for pattern in company_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.company_name = match.group(1).strip()
                    break
            
            # Look for fiscal year
            year_patterns = [
                r'Năm tài chính[:\s]*(\d{4})',
                r'Kỳ báo cáo[:\s]*(\d{4})',
                r'cho năm kết thúc (\d{4})',
            ]
            for pattern in year_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.fiscal_year = int(match.group(1))
                    break
            
            # Search for financial values using Vietnamese terms
            for vi_term, en_field in self.VIETNAMESE_TERMS.items():
                # Pattern: term followed by number
                pattern = rf'{vi_term}[:\s]*([\d,.]+\s*(?:triệu|tỷ|nghìn|billion|million)?)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1)
                    multiplier = 1
                    
                    # Handle Vietnamese units
                    if 'tỷ' in value_str.lower() or 'billion' in value_str.lower():
                        multiplier = 1e9
                    elif 'triệu' in value_str.lower() or 'million' in value_str.lower():
                        multiplier = 1e6
                    elif 'nghìn' in value_str.lower() or 'thousand' in value_str.lower():
                        multiplier = 1e3
                    
                    value = parse_number(value_str)
                    if value:
                        setattr(result, en_field, value * multiplier)
        
        # Search in tables
        for table_info in tables:
            table_data = table_info.get('data', table_info.get('rows', []))
            self._parse_table_for_financials(result, table_data, parse_number)
    
    def _parse_table_for_financials(self, result: ExtractedFinancialData, 
                                   table_data: List[List[str]],
                                   parse_number=None):
        """Parse a table for financial data."""
        import unicodedata
        
        if parse_number is None:
            def parse_number(value: str) -> Optional[float]:
                if not value:
                    return None
                try:
                    cleaned = re.sub(r'[,\s]', '', str(value))
                    if ',' in cleaned and '.' not in cleaned:
                        cleaned = cleaned.replace(',', '.')
                    return float(cleaned)
                except (ValueError, TypeError):
                    return None
                    
        def remove_diacritics(text):
            """Remove Vietnamese diacritics for matching"""
            if not text:
                return ''
            text = str(text).replace('_', ' ')
            normalized = unicodedata.normalize('NFKD', text)
            return ''.join(c for c in normalized if not unicodedata.combining(c)).lower()
        
        if not table_data or len(table_data) < 2:
            return
        
        # Try to identify column headers
        headers = [str(h).lower().strip() if h else '' for h in table_data[0]]
        
        # Find year columns
        year_cols = []
        for i, header in enumerate(headers):
            if re.match(r'\d{4}', str(header)):
                year_cols.append(i)
        
        if not year_cols and len(headers) > 1:
            # Assume last column(s) contain values
            year_cols = list(range(1, len(headers)))
        
        # Process each row
        for row in table_data[1:]:
            if not row:
                continue
            
            row_label = str(row[0]).lower().strip() if row else ''
            row_label_normalized = remove_diacritics(row_label)
            
            # Match row label to financial fields (with diacritic normalization)
            for vi_term, en_field in self.VIETNAMESE_TERMS.items():
                vi_term_normalized = remove_diacritics(vi_term)
                if vi_term_normalized in row_label_normalized or en_field.replace('_', ' ') in row_label_normalized:
                    # Found matching field, extract values
                    for col_idx in year_cols:
                        if col_idx < len(row):
                            value = parse_number(row[col_idx])
                            if value is not None:
                                current_value = getattr(result, en_field, None)
                                if current_value is None:
                                    setattr(result, en_field, value)
                                break
    
    def to_dict(self, data: ExtractedFinancialData) -> Dict[str, Any]:
        """Convert extracted data to dictionary format."""
        return {
            'company_name': data.company_name,
            'ticker': data.ticker,
            'fiscal_year': data.fiscal_year,
            'currency': data.currency,
            'report_type': data.report_type,
            'income_statement': {
                'revenue': data.revenue,
                'cost_of_revenue': data.cost_of_revenue,
                'gross_profit': data.gross_profit,
                'operating_expenses': data.operating_expenses,
                'ebitda': data.ebitda,
                'ebit': data.ebit,
                'net_income': data.net_income,
            },
            'balance_sheet': {
                'total_assets': data.total_assets,
                'current_assets': data.current_assets,
                'total_liabilities': data.total_liabilities,
                'total_equity': data.total_equity,
                'cash_and_equivalents': data.cash_and_equivalents,
                'accounts_receivable': data.accounts_receivable,
                'inventory': data.inventory,
                'property_plant_equipment': data.property_plant_equipment,
                'total_debt': data.total_debt,
            },
            'cash_flow': {
                'operating_cash_flow': data.operating_cash_flow,
                'investing_cash_flow': data.investing_cash_flow,
                'financing_cash_flow': data.financing_cash_flow,
                'free_cash_flow': data.free_cash_flow,
                'capex': data.capex,
            },
            'ratios': {
                'roe': data.roe,
                'roa': data.roa,
                'profit_margin': data.profit_margin,
                'debt_to_equity': data.debt_to_equity,
                'current_ratio': data.current_ratio,
            },
            'metadata': {
                'extraction_method': data.extraction_method,
                'confidence_score': data.confidence_score,
                'source_file': data.source_file,
                'extraction_date': data.extraction_date,
                'notes': data.notes,
            }
        }


class VietnameseReportDownloader:
    """
    Download Vietnamese financial reports from various sources.
    
    Sources:
    - HOSE (hsx.vn)
    - HNX (hnx.vn)
    - Cafef.vn
    - Vietstock.vn
    - Company websites
    """
    
    def __init__(self):
        self.session = None
        self._initialize_http()
    
    def _initialize_http(self):
        """Initialize HTTP client."""
        try:
            import requests
            self.requests = requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            logger.debug("requests library initialized")
        except ImportError:
            logger.warning("requests library not available")
    
    def download_from_hose(self, ticker: str, year: int) -> Optional[str]:
        """
        Download report from HOSE (Ho Chi Minh Stock Exchange).
        
        Args:
            ticker: Stock ticker (e.g., VNM, VCB)
            year: Fiscal year
            
        Returns:
            Path to downloaded file or None
        """
        logger.info(f"Searching HOSE for {ticker} {year}")
        
        # HOSE filing search URL pattern
        # Note: This is a placeholder - actual implementation would need
        # to handle HOSE's specific API or web scraping
        
        urls_to_try = [
            f"https://hsx.vn/Modules/ListedCompany/Profile?symbol={ticker}",
            f"https://hsx.vn/Modules/Disclosure/ListingDocumentList?symbol={ticker}",
        ]
        
        for url in urls_to_try:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Parse response for PDF links
                    # Implementation depends on HOSE's actual structure
                    pass
            except Exception as e:
                logger.warning(f"Error accessing HOSE: {e}")
        
        return None
    
    def download_from_cafef(self, ticker: str, year: int) -> Optional[str]:
        """
        Download report from Cafef.vn.
        
        Args:
            ticker: Stock ticker
            year: Fiscal year
            
        Returns:
            Path to downloaded file or None
        """
        logger.info(f"Searching Cafef for {ticker} {year}")
        
        url = f"https://finance.cafef.vn/{ticker}.chn"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Parse HTML for report links
                # Look for annual report (Báo cáo thường niên) links
                pass
        except Exception as e:
            logger.warning(f"Error accessing Cafef: {e}")
        
        return None
    
    def download_from_vietstock(self, ticker: str, year: int) -> Optional[str]:
        """
        Download report from Vietstock.vn.
        
        Args:
            ticker: Stock ticker
            year: Fiscal year
            
        Returns:
            Path to downloaded file or None
        """
        logger.info(f"Searching Vietstock for {ticker} {year}")
        
        url = f"https://finance.vietstock.vn/{ticker}.htm"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Parse HTML for report links
                pass
        except Exception as e:
            logger.warning(f"Error accessing Vietstock: {e}")
        
        return None
    
    def download_all_sources(self, ticker: str, year: int, 
                            output_dir: str = "./reports") -> List[Dict]:
        """
        Try downloading from all sources.
        
        Args:
            ticker: Stock ticker
            year: Fiscal year
            output_dir: Directory to save downloaded files
            
        Returns:
            List of download results
        """
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        
        sources = [
            ("HOSE", self.download_from_hose),
            ("Cafef", self.download_from_cafef),
            ("Vietstock", self.download_from_vietstock),
        ]
        
        for source_name, download_func in sources:
            try:
                file_path = download_func(ticker, year)
                results.append({
                    'source': source_name,
                    'success': file_path is not None,
                    'file_path': file_path,
                })
            except Exception as e:
                results.append({
                    'source': source_name,
                    'success': False,
                    'error': str(e),
                })
        
        return results


# Convenience functions
def extract_financials_from_pdf(file_path: str, method: str = "auto") -> Dict[str, Any]:
    """
    Quick helper to extract financials from a PDF.
    
    Args:
        file_path: Path to PDF file
        method: Extraction method ('auto', 'pdfplumber', 'camelot', 'tabula', 'ocr')
        
    Returns:
        Dictionary with extracted financial data
    """
    extractor = VietnamesePDFExtractor(extraction_method=method)
    result = extractor.extract_from_file(file_path)
    return extractor.to_dict(result)


def process_vietnamese_reports(report_paths: List[str], 
                              output_format: str = "dict") -> List[Dict]:
    """
    Process multiple Vietnamese financial reports.
    
    Args:
        report_paths: List of PDF file paths
        output_format: Output format ('dict', 'json', 'dataframe')
        
    Returns:
        List of extracted data dictionaries
    """
    extractor = VietnamesePDFExtractor(extraction_method="auto")
    results = []
    
    for path in report_paths:
        try:
            extracted = extractor.extract_from_file(path)
            results.append(extractor.to_dict(extracted))
        except Exception as e:
            logger.error(f"Failed to process {path}: {e}")
            results.append({
                'source_file': path,
                'error': str(e),
                'success': False
            })
    
    return results
