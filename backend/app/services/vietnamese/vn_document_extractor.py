"""
Vietnamese Financial Document Extractor
Handles OCR and LLM-based normalization of Vietnamese financial PDF reports.
Converts raw PDFs (scanned or text) into structured JSON for valuation engines.
"""
import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# OCR Imports
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logging.warning("PaddleOCR not installed. OCR functionality disabled.")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logging.warning("pdf2image not installed. PDF-to-image conversion disabled.")

# LLM Imports (Optional for advanced normalization)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Mapping of Vietnamese Financial Terms to Standard English Keys
VN_TERM_MAPPING = {
    # Income Statement
    "doanh thu thuần": "revenue",
    "doanh thu bán hàng và cung cấp dịch vụ": "revenue",
    "giá vốn hàng bán": "cost_of_goods_sold",
    "lợi nhuận gộp": "gross_profit",
    "chi phí bán hàng": "selling_expenses",
    "chi phí quản lý doanh nghiệp": "administrative_expenses",
    "lợi nhuận thuần từ hoạt động kinh doanh": "operating_profit",
    "doanh thu khác": "other_income",
    "chi phí khác": "other_expenses",
    "lợi nhuận khác": "other_profit",
    "tổng lợi nhuận kế toán trước thuế": "profit_before_tax",
    "chi phí thuế tndn hiện hành": "income_tax_expense",
    "lợi nhuận sau thuế thu nhập doanh nghiệp": "net_income",
    "lợi nhuận sau thuế cty mẹ": "net_income_parent",
    "lợi ích cổ đông không kiểm soát": "minority_interest",

    # Balance Sheet - Assets
    "tiền và tương đương tiền": "cash_and_equivalents",
    "đầu tư tài chính ngắn hạn": "short_term_investments",
    "phải thu ngắn hạn": "accounts_receivable",
    "hàng tồn kho": "inventory",
    "tài sản ngắn hạn khác": "other_current_assets",
    "tổng tài sản ngắn hạn": "total_current_assets",
    "tài sản dài hạn": "non_current_assets",
    "tài sản cố định": "fixed_assets",
    "nguyên giá": "gross_fixed_assets",
    "khấu hao lũy kế": "accumulated_depreciation",
    "đầu tư tài chính dài hạn": "long_term_investments",
    "tổng cộng tài sản": "total_assets",

    # Balance Sheet - Liabilities & Equity
    "phải trả người bán": "accounts_payable",
    "người mua trả tiền trước": "advances_from_customers",
    "thuế và các khoản phải nộp nhà nước": "taxes_payable",
    "phải trả người lao động": "employee_payables",
    "chi phí phải trả": "accrued_expenses",
    "vay và nợ ngắn hạn": "short_term_debt",
    "tổng nợ ngắn hạn": "total_current_liabilities",
    "vay và nợ dài hạn": "long_term_debt",
    "tổng cộng nợ phải trả": "total_liabilities",
    "vốn chủ sở hữu": "total_equity",
    "vốn góp của chủ sở hữu": "contributed_capital",
    "lợi nhuận chưa phân phối": "retained_earnings",
    "tổng nguồn vốn": "total_liabilities_and_equity",

    # Cash Flow
    "lưu chuyển tiền thuần từ hoạt động kinh doanh": "cfo",
    "lưu chuyển tiền thuần từ hoạt động đầu tư": "cfi",
    "lưu chuyển tiền thuần từ hoạt động tài chính": "cff",
    "lưu chuyển tiền thuần trong năm": "net_change_in_cash",
}

@dataclass
class ExtractedFinancialData:
    """Structured output from document extraction"""
    company_name: str
    report_type: str  # 'Annual' or 'Quarterly'
    fiscal_year: int
    currency: str = "VND"
    unit_multiplier: int = 1  # 1, 1000, 1000000, etc.

    # Financial Statements
    income_statement: Dict[str, float] = None
    balance_sheet: Dict[str, float] = None
    cash_flow: Dict[str, float] = None

    # Metadata
    source_file: str = ""
    extraction_confidence: float = 0.0
    validation_errors: List[str] = None

    def __post_init__(self):
        if self.income_statement is None:
            self.income_statement = {}
        if self.balance_sheet is None:
            self.balance_sheet = {}
        if self.cash_flow is None:
            self.cash_flow = {}
        if self.validation_errors is None:
            self.validation_errors = []

class VietnameseFinanceOCR:
    """
    Handles OCR processing of Vietnamese financial PDFs.
    Uses PaddleOCR optimized for Vietnamese text and table structures.
    """

    def __init__(self):
        if not PADDLE_AVAILABLE:
            raise RuntimeError("PaddleOCR is not installed. Please install paddlepaddle and paddleocr.")

        # Initialize PaddleOCR with Vietnamese language support
        # use_angle_cls=True helps with skewed scans
        # lang='vi' optimizes for Vietnamese characters
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='vi',
            show_log=False,
            det_db_thresh=0.3,
            det_db_box_thresh=0.5,
            rec_batch_num=6
        )
        logger.info("PaddleOCR initialized with Vietnamese language support")

    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from a PDF file.
        Returns a list of dictionaries representing rows/columns.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not PDF2IMAGE_AVAILABLE:
            raise RuntimeError("pdf2image is not installed. Cannot convert PDF to images.")

        logger.info(f"Starting OCR extraction for {pdf_path}")

        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=300)
            logger.info(f"Converted {len(images)} pages to images")

            all_tables = []

            for page_num, image in enumerate(images):
                # Save temp image for PaddleOCR (it expects a path or numpy array)
                # PaddleOCR can handle PIL images directly in newer versions
                result = self.ocr.ocr(image, cls=True)

                # Parse OCR result into structured text blocks
                # Result format: [([box_coords], (text, confidence)), ...]
                text_blocks = []
                if result and result[0]:
                    for line in result[0]:
                        box, (text, conf) = line
                        text_blocks.append({
                            "text": text.strip(),
                            "confidence": conf,
                            "box": box,
                            "page": page_num + 1
                        })

                # Group text blocks into potential tables based on y-coordinates
                tables = self._group_blocks_into_tables(text_blocks)
                all_tables.extend(tables)

            logger.info(f"Extracted {len(all_tables)} table structures from {pdf_path}")
            return all_tables

        except Exception as e:
            logger.error(f"OCR extraction failed for {pdf_path}: {str(e)}")
            raise

    def _group_blocks_into_tables(self, blocks: List[Dict]) -> List[Dict]:
        """
        Heuristic to group text blocks into rows and columns based on coordinates.
        This is a simplified version; production might need more robust table detection.
        """
        if not blocks:
            return []

        # Sort blocks by y-coordinate (rows) then x-coordinate (columns)
        # Tolerance for y-coordinate to group into same row
        y_tolerance = 20

        sorted_blocks = sorted(blocks, key=lambda k: k['box'][0][1]) # Sort by top-y

        rows = []
        current_row = []
        if sorted_blocks:
            current_y = sorted_blocks[0]['box'][0][1]

            for block in sorted_blocks:
                y_pos = block['box'][0][1]
                if abs(y_pos - current_y) <= y_tolerance:
                    current_row.append(block)
                else:
                    # Sort current row by x-coordinate and add to rows
                    current_row.sort(key=lambda k: k['box'][0][0])
                    rows.append(current_row)
                    current_row = [block]
                    current_y = y_pos

            # Add last row
            if current_row:
                current_row.sort(key=lambda k: k['box'][0][0])
                rows.append(current_row)

        # Convert rows to a simple dictionary structure
        # Assuming first row might be headers, but we'll return raw structure for LLM to parse
        return [{"rows": rows}]

class VietnameseLLMNormalizer:
    """
    Normalizes raw OCR text into standardized financial keys.
    Maps Vietnamese terms to English keys and handles unit conversions.
    """

    def __init__(self, use_llm: bool = False, api_key: Optional[str] = None):
        self.use_llm = use_llm and OPENAI_AVAILABLE
        if self.use_llm and api_key:
            openai.api_key = api_key

    def normalize_data(self, raw_tables: List[Dict], context: Dict[str, Any]) -> ExtractedFinancialData:
        """
        Process raw OCR tables into structured financial data.
        """
        company_name = context.get("company_name", "Unknown")
        fiscal_year = context.get("fiscal_year", 0)
        report_type = context.get("report_type", "Annual")

        extracted = ExtractedFinancialData(
            company_name=company_name,
            report_type=report_type,
            fiscal_year=fiscal_year,
            source_file=context.get("source_file", "")
        )

        # Flatten tables into a single list of (label, value) pairs
        items = []
        for table in raw_tables:
            for row in table.get("rows", []):
                if len(row) >= 2:
                    # Assume first block is label, second is value (simplified)
                    # Real implementation needs better column detection
                    label_block = row[0]
                    value_block = row[-1] # Take last block as value

                    label = label_block['text'].lower().strip()
                    value_str = value_block['text'].strip()

                    # Clean value string (remove commas, dots used as thousand separators)
                    # Vietnamese format: 1.000.000 or 1,000,000 depending on source
                    # Usually '.' is thousand separator in VN, ',' is decimal
                    value_clean = re.sub(r'[^\d,-]', '', value_str.replace('.', ''))
                    # If it looks like 1,23 (decimal), replace comma with dot
                    if ',' in value_clean and len(value_clean.split(',')[-1]) <= 2:
                         value_clean = value_clean.replace(',', '.')
                    else:
                         value_clean = value_clean.replace(',', '')

                    try:
                        value = float(value_clean) if value_clean else 0.0
                    except ValueError:
                        value = 0.0

                    items.append((label, value))

        # Map Vietnamese labels to standard keys
        detected_unit_multiplier = 1

        for label, value in items:
            standard_key = self._map_term(label)
            if standard_key:
                # Check for unit indicators in the label (e.g., "triệu đồng", "tỷ đồng")
                multiplier = self._detect_unit_multiplier(label)
                if multiplier > 1:
                    detected_unit_multiplier = max(detected_unit_multiplier, multiplier)

                # Store in appropriate section (heuristic based on key name)
                if any(k in standard_key for k in ["revenue", "cost", "profit", "expense", "income"]):
                    extracted.income_statement[standard_key] = value * multiplier
                elif any(k in standard_key for k in ["asset", "liability", "equity", "cash", "debt", "capital"]):
                    extracted.balance_sheet[standard_key] = value * multiplier
                elif any(k in standard_key for k in ["cfo", "cfi", "cff", "cash_flow"]):
                    extracted.cash_flow[standard_key] = value * multiplier

        extracted.unit_multiplier = detected_unit_multiplier
        extracted.extraction_confidence = 0.85 # Placeholder, real confidence from OCR

        # Validate accounting identities
        self._validate_accounting_identities(extracted)

        return extracted

    def _map_term(self, term: str) -> Optional[str]:
        """Map Vietnamese term to standard key."""
        term = term.lower().strip()
        # Direct match
        if term in VN_TERM_MAPPING:
            return VN_TERM_MAPPING[term]

        # Partial match (contains key)
        for vn_key, en_key in VN_TERM_MAPPING.items():
            if vn_key in term:
                return en_key

        return None

    def _detect_unit_multiplier(self, text: str) -> int:
        """Detect if values are in millions or billions."""
        text = text.lower()
        if "tỷ" in text or "tỉ" in text or "billion" in text:
            return 1_000_000_000
        elif "triệu" in text or "million" in text:
            return 1_000_000
        elif "nghìn" in text or "ngàn" in text or "thousand" in text:
            return 1_000
        return 1

    def _validate_accounting_identities(self, data: ExtractedFinancialData):
        """Check basic accounting equations to flag errors."""
        bs = data.balance_sheet

        # Assets = Liabilities + Equity
        total_assets = bs.get("total_assets", 0)
        total_liab_eq = bs.get("total_liabilities", 0) + bs.get("total_equity", 0)

        if total_assets > 0 and total_liab_eq > 0:
            diff_ratio = abs(total_assets - total_liab_eq) / total_assets
            if diff_ratio > 0.05: # 5% tolerance
                data.validation_errors.append(
                    f"Balance Sheet mismatch: Assets ({total_assets}) != Liab+Eq ({total_liab_eq}). Diff: {diff_ratio:.2%}"
                )

        # Net Income check (Profit Before Tax - Tax)
        is_stmt = data.income_statement
        pbt = is_stmt.get("profit_before_tax", 0)
        tax = is_stmt.get("income_tax_expense", 0)
        net_income = is_stmt.get("net_income", 0)

        if pbt > 0 and net_income > 0:
            expected_net = pbt - tax
            if abs(expected_net - net_income) / pbt > 0.05:
                data.validation_errors.append(
                    f"Income Statement mismatch: PBT ({pbt}) - Tax ({tax}) != Net Income ({net_income})"
                )

class VietnameseDocumentExtractor:
    """
    Main facade for extracting financial data from Vietnamese PDF reports.
    Orchestrates OCR and Normalization.
    """

    def __init__(self, use_llm: bool = False, api_key: Optional[str] = None):
        self.ocr_engine = None
        self.normalizer = VietnameseLLMNormalizer(use_llm=use_llm, api_key=api_key)

        if PADDLE_AVAILABLE and PDF2IMAGE_AVAILABLE:
            try:
                self.ocr_engine = VietnameseFinanceOCR()
                logger.info("VietnameseDocumentExtractor initialized with OCR capabilities")
            except Exception as e:
                logger.warning(f"Failed to initialize OCR engine: {e}")
        else:
            logger.warning("VietnameseDocumentExtractor initialized without OCR. Manual fallback required.")

    def extract_from_pdf(self, pdf_path: str, metadata: Dict[str, Any]) -> ExtractedFinancialData:
        """
        Full pipeline: PDF -> OCR -> Normalized JSON
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Starting extraction pipeline for {pdf_path}")

        # Step 1: Check if file is text-searchable (skip OCR if possible)
        if self._is_text_pdf(pdf_path):
            logger.info("PDF is text-searchable. Attempting direct text extraction...")
            # TODO: Implement direct text extraction for born-digital PDFs
            # For now, fall through to OCR as it handles layout better
            pass

        # Step 2: OCR Extraction
        if not self.ocr_engine:
            raise RuntimeError("OCR engine not available. Cannot process scanned PDFs.")

        raw_tables = self.ocr_engine.extract_tables_from_pdf(pdf_path)

        if not raw_tables:
            raise ValueError("No tables extracted from PDF. The document may be too blurry or non-financial.")

        # Step 3: Normalization
        normalized_data = self.normalizer.normalize_data(raw_tables, metadata)

        logger.info(f"Extraction complete. Confidence: {normalized_data.extraction_confidence}")
        if normalized_data.validation_errors:
            logger.warning(f"Validation errors found: {normalized_data.validation_errors}")

        return normalized_data

    def _is_text_pdf(self, pdf_path: str) -> bool:
        """Heuristic to check if PDF contains selectable text."""
        try:
            from pdf2image import convert_from_path
            # If we can extract text using a simple library like pdfplumber, it's text-based
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    if page.extract_text():
                        return True
            return False
        except ImportError:
            return False
        except Exception:
            return False

# Helper function for easy usage
def extract_vietnamese_financials(pdf_path: str, company_name: str, year: int) -> Dict[str, Any]:
    """
    Convenience function to extract data from a single PDF.
    """
    extractor = VietnameseDocumentExtractor()
    metadata = {
        "company_name": company_name,
        "fiscal_year": year,
        "report_type": "Annual",
        "source_file": pdf_path
    }

    result = extractor.extract_from_pdf(pdf_path, metadata)
    return asdict(result)