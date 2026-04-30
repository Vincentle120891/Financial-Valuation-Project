# Vietnamese Market Model - PDF Data Extraction Implementation Summary

## Overview

Complete implementation for extracting financial data from Vietnamese market PDF reports, including annual reports (Báo cáo thường niên), financial statements (Báo cáo tài chính), and prospectus documents (Bản cáo bạch).

## Files Created/Modified

### 1. Core Service (`/workspace/backend/app/services/pdf_extraction_service.py`)
**Main Components:**

#### `VietnamesePDFExtractor` Class
- **Multiple extraction methods:**
  - `pdfplumber`: Best for text-based PDFs with tables
  - `camelot-py`: Best for structured table extraction
  - `tabula-py`: Alternative table extraction
  - `pytesseract`: OCR for scanned documents
  
- **Vietnamese language support:**
  - Comprehensive term mapping (50+ Vietnamese financial terms)
  - Automatic number format handling (triệu, tỷ, nghìn)
  - Company name and fiscal year detection

- **Data extraction coverage:**
  - Income Statement (revenue, COGS, EBITDA, net income)
  - Balance Sheet (assets, liabilities, equity, working capital)
  - Cash Flow (operating, investing, financing, free cash flow)
  - Key ratios (ROE, ROA, profit margin, D/E)

#### `VietnameseReportDownloader` Class
- Download from multiple sources:
  - HOSE (Ho Chi Minh Stock Exchange)
  - Cafef.vn
  - Vietstock.vn
- Extensible architecture for additional sources

#### Convenience Functions
- `extract_financials_from_pdf()`: Single file extraction
- `process_vietnamese_reports()`: Batch processing

### 2. API Routes (`/workspace/backend/app/api/routes/v1/pdf_extraction_routes.py`)
**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pdf/extract` | POST | Extract data from single PDF |
| `/api/v1/pdf/extract/batch` | POST | Extract from multiple PDFs |
| `/api/v1/pdf/download` | POST | Download report from sources |
| `/api/v1/pdf/sources` | GET | List available data sources |
| `/api/v1/pdf/supported-companies` | GET | List supported Vietnamese companies |

**Request/Response Models:**
- `ExtractionRequest`: Method selection, raw tables option
- `ExtractionResponse`: Structured financial data with confidence scores
- `DownloadRequest`: Ticker, year, source selection
- `DownloadResponse`: Download results from multiple sources

### 3. Dependencies (`/workspace/backend/requirements.txt`)
**Added packages:**
```txt
# PDF Extraction
pdfplumber>=0.10.0
PyPDF2>=3.0.0
camelot-py[cv]>=0.11.0
tabula-py>=2.9.0
pdf2image>=1.16.0
pytesseract>=0.3.10

# Vietnamese Language
pyvi>=0.1.2
underthesea>=6.0.0

# HTTP Client
requests>=2.31.0
```

### 4. Application Integration (`/workspace/backend/app/main.py`)
- Imported PDF extraction router
- Registered endpoint: `/api/v1/pdf/*`

### 5. Router Exports (`/workspace/backend/app/api/routes/v1/__init__.py`)
- Added `pdf_extraction_router` to exports

### 6. Documentation (`/workspace/backend/VIETNAMESE_PDF_EXTRACTION_GUIDE.md`)
Comprehensive guide covering:
- Installation instructions
- API usage examples
- Vietnamese financial terms mapping
- Best practices
- Troubleshooting guide

## Vietnamese Financial Terms Mapping

### Income Statement
```python
'doanh_thu' → 'revenue'
'giá_vốn_hàng_bán' → 'cost_of_revenue'
'lợi_nhập_gộp' → 'gross_profit'
'chi_phí_hoạt_động' → 'operating_expenses'
'ebitda' → 'ebitda'
'lợi_nhập_sau_thuế' → 'net_income'
```

### Balance Sheet
```python
'tổng_tài_sản' → 'total_assets'
'tài_sản_ngắn_hạn' → 'current_assets'
'tổng_nợ_phải_trả' → 'total_liabilities'
'vốn_chủ_sở_hữu' → 'total_equity'
'tiền_và_tương_đương_tiền' → 'cash_and_equivalents'
'phải_thu_khách_hàng' → 'accounts_receivable'
'hàng_tồn_kho' → 'inventory'
'nợ_vay' → 'total_debt'
```

### Cash Flow
```python
'lưu_chuyển_tiền_từ_hoạt_động_kinh_doanh' → 'operating_cash_flow'
'lưu_chuyển_tiền_từ_hoạt_động_đầu_tư' → 'investing_cash_flow'
'lưu_chuyển_tiền_từ_hoạt_động_tài_chính' → 'financing_cash_flow'
'lưu_chuyển_tiền_tự_do' → 'free_cash_flow'
'mua_sắm_tscđ' → 'capex'
```

## Supported Vietnamese Companies

Predefined tickers (HOSE):
- **VNM.VN** - Vinamilk (Consumer Goods)
- **VCB.VN** - Vietcombank (Banking)
- **HPG.VN** - Hoa Phat Group (Steel)
- **VIC.VN** - Vingroup (Conglomerate)
- **VRE.VN** - Vincom Retail (Real Estate)
- **MSN.VN** - Masan Group (Consumer Goods)
- **MWG.VN** - Mobile World (Retail)
- **FPT.VN** - FPT Corporation (Technology)
- **SAB.VN** - Sabeco (Beverages)
- **GAS.VN** - PV Gas (Energy)

## Usage Examples

### Python SDK Usage
```python
from app.services.pdf_extraction_service import extract_financials_from_pdf

# Extract from single file
result = extract_financials_from_pdf(
    file_path="reports/VNM_2023.pdf",
    method="auto"
)

print(f"Revenue: {result['income_statement']['revenue']}")
print(f"Confidence: {result['metadata']['confidence_score']}")

# Batch processing
from app.services.pdf_extraction_service import process_vietnamese_reports

results = process_vietnamese_reports([
    "reports/VNM_2023.pdf",
    "reports/VCB_2023.pdf",
    "reports/HPG_2023.pdf"
])
```

### API Usage (curl)
```bash
# Single extraction
curl -X POST "http://localhost:8000/api/v1/pdf/extract" \
  -F "file=@VNM_Report_2023.pdf" \
  -F "method=auto"

# Batch extraction
curl -X POST "http://localhost:8000/api/v1/pdf/extract/batch" \
  -F "files=@VNM_2023.pdf" \
  -F "files=@VCB_2023.pdf" \
  -F "method=auto"

# List sources
curl "http://localhost:8000/api/v1/pdf/sources"
```

### Integration with DCF Model
```python
from app.services.pdf_extraction_service import VietnamesePDFExtractor
from app.services.dcf_input_manager import create_dcf_inputs

# Extract data from PDF
extractor = VietnamesePDFExtractor()
result = extractor.extract_from_file("VNM_2023.pdf")
pdf_data = extractor.to_dict(result)

# Use in DCF model
api_data = {
    "profile": {
        "symbol": "VNM.VN",
        "current_price": 85000,
    },
    "financials": {
        "revenue": {"2023": pdf_data['income_statement']['revenue']},
        "net_income": {"2023": pdf_data['income_statement']['net_income']},
    }
}

dcf_inputs = create_dcf_inputs(api_data=api_data)
```

## Data Sources

### Official Exchanges
1. **HOSE** (Ho Chi Minh Stock Exchange)
   - URL: https://hsx.vn
   - Coverage: Main board companies

2. **HNX** (Hanoi Stock Exchange)
   - URL: https://hnx.vn
   - Coverage: Secondary board companies

### Financial Portals
1. **Cafef.vn** - Popular financial news portal
2. **Vietstock.vn** - Comprehensive data provider
3. **FiinPro** - Professional platform

## Report Types Supported

1. **Annual Reports** (Báo cáo thường niên)
   - Full year financial statements
   - Management discussion & analysis
   - Corporate governance information

2. **Financial Statements** (Báo cáo tài chính)
   - Quarterly reports
   - Annual audited statements
   - Consolidated and separate statements

3. **Prospectus** (Bản cáo bạch)
   - IPO documentation
   - Detailed company information
   - Risk factors and use of proceeds

## Extraction Methods Comparison

| Method | Best For | Speed | Accuracy | Requirements |
|--------|----------|-------|----------|--------------|
| auto | General use | Fast | High | None |
| pdfplumber | Text-based PDFs | Fast | High | None |
| camelot | Structured tables | Medium | Very High | ghostscript |
| tabula | Simple tables | Medium | High | Java |
| ocr | Scanned docs | Slow | Medium | tesseract-ocr |

## Confidence Scoring

The system provides confidence scores (0.0 - 1.0):
- **> 0.8**: High confidence - suitable for automated processing
- **0.5 - 0.8**: Medium confidence - review recommended
- **< 0.5**: Low confidence - manual verification required

Factors affecting confidence:
- Number of fields successfully extracted
- Extraction method used (OCR has lower base confidence)
- Data consistency checks
- Format validation

## Error Handling

The implementation includes comprehensive error handling:
- File not found errors
- Invalid PDF format detection
- Library availability checks with fallbacks
- Graceful degradation when optional libraries missing
- Detailed error messages in response notes

## System Requirements

### Python Packages
All listed in `requirements.txt`

### System Dependencies (for OCR)
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-vie
sudo apt-get install poppler-utils
sudo apt-get install ghostscript

# macOS
brew install tesseract
brew install poppler
brew install ghostscript
```

## Testing

Verify installation:
```bash
cd backend
python -c "from app.services.pdf_extraction_service import VietnamesePDFExtractor; print('✓ Service loaded')"
python -c "from app.api.routes.v1.pdf_extraction_routes import router; print('✓ Routes loaded')"
python -c "from app.main import app; print('✓ App loaded')"
```

Check API endpoints:
```bash
# Start server
uvicorn app.main:app --reload

# Test in browser
http://localhost:8000/docs
```

## Future Enhancements

Potential improvements:
1. **Enhanced OCR**: Better Vietnamese language models
2. **Table structure recognition**: Deep learning-based table detection
3. **Direct API integrations**: partnerships with FiinPro, Vietstock
4. **Automated validation**: Cross-check with yFinance data
5. **Historical trend analysis**: Multi-year comparison
6. **Peer benchmarking**: Industry ratio comparisons
7. **Export formats**: Excel, CSV output options

## Support & Documentation

- **API Documentation**: http://localhost:8000/docs
- **User Guide**: `/workspace/backend/VIETNAMESE_PDF_EXTRACTION_GUIDE.md`
- **Logs**: `/workspace/backend/logs/`

---

*Implementation completed with full integration into existing valuation model infrastructure.*
