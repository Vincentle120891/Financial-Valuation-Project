# Vietnamese Market PDF Extraction Guide

## Overview

This guide explains how to extract financial data from Vietnamese market reports (PDF files) using the implemented PDF extraction service.

## Installation

### Required Dependencies

Install all required packages:

```bash
cd backend
pip install -r requirements.txt
```

### System Dependencies (for OCR)

For scanned documents, you'll need Tesseract OCR:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install libtesseract-dev
sudo apt-get install poppler-utils  # for pdf2image
```

**macOS:**
```bash
brew install tesseract
brew install poppler
```

**Windows:**
Download and install from: https://github.com/tesseract-ocr/tesseract/releases

## API Endpoints

### 1. Extract Data from Single PDF

**Endpoint:** `POST /api/v1/pdf/extract`

**Request:**
- `file`: PDF file (multipart/form-data)
- `method`: Extraction method (default: "auto")
- `include_raw_tables`: Include raw table data (default: false)

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/pdf/extract" \
  -F "file=@/path/to/report.pdf" \
  -F "method=auto" \
  -F "include_raw_tables=false"
```

**Example with Python requests:**
```python
import requests

files = {'file': open('VNM_Annual_Report_2023.pdf', 'rb')}
data = {
    'method': 'auto',
    'include_raw_tables': False
}

response = requests.post(
    'http://localhost:8000/api/v1/pdf/extract',
    files=files,
    data=data
)

print(response.json())
```

**Response:**
```json
{
  "success": true,
  "company_name": "Công ty Cổ phần Sữa Việt Nam",
  "ticker": "VNM",
  "fiscal_year": 2023,
  "currency": "VND",
  "revenue": 75000000000000,
  "net_income": 12000000000000,
  "ebitda": 15000000000000,
  "total_assets": 90000000000000,
  "extraction_method": "pdfplumber",
  "confidence_score": 0.85,
  "notes": []
}
```

### 2. Batch Extract Multiple PDFs

**Endpoint:** `POST /api/v1/pdf/extract/batch`

**Example:**
```python
import requests

files = [
    ('files', open('VNM_2023.pdf', 'rb')),
    ('files', open('VCB_2023.pdf', 'rb')),
    ('files', open('HPG_2023.pdf', 'rb')),
]

response = requests.post(
    'http://localhost:8000/api/v1/pdf/extract/batch',
    files=files,
    data={'method': 'auto'}
)

for result in response.json():
    print(f"{result['ticker']}: Revenue = {result['revenue']}")
```

### 3. Download Reports from Sources

**Endpoint:** `POST /api/v1/pdf/download`

**Request Body:**
```json
{
  "ticker": "VNM",
  "year": 2023,
  "sources": ["all"]
}
```

**Sources Available:**
- `hose` - HOSE (Ho Chi Minh Stock Exchange)
- `cafef` - Cafef.vn
- `vietstock` - Vietstock.vn
- `all` - Try all sources

### 4. List Available Sources

**Endpoint:** `GET /api/v1/pdf/sources`

Returns information about:
- Stock exchanges (HOSE, HNX)
- Financial portals (Cafef, Vietstock, FiinPro)
- Report types (Annual Reports, Financial Statements, Prospectus)
- Extraction methods

### 5. List Supported Companies

**Endpoint:** `GET /api/v1/pdf/supported-companies`

Returns predefined Vietnamese companies with tickers.

## Extraction Methods

### 1. Auto (Recommended)
Automatically detects the best extraction method based on PDF structure.

```python
extractor = VietnamesePDFExtractor(extraction_method="auto")
```

### 2. PDFPlumber
Best for text-based PDFs with tables. Fast and accurate for modern reports.

```python
extractor = VietnamesePDFExtractor(extraction_method="pdfplumber")
```

### 3. Camelot
Best for structured table extraction with borders.

```python
extractor = VietnamesePDFExtractor(extraction_method="camelot")
```

### 4. Tabula
Alternative table extraction tool.

```python
extractor = VietnamesePDFExtractor(extraction_method="tabula")
```

### 5. OCR
For scanned documents or image-based PDFs. Requires Tesseract installation.

```python
extractor = VietnamesePDFExtractor(extraction_method="ocr")
```

## Vietnamese Financial Terms Mapping

The system automatically recognizes Vietnamese financial terms:

### Income Statement (Báo cáo kết quả hoạt động kinh doanh)
| Vietnamese | English |
|------------|---------|
| Doanh thu | Revenue |
| Giá vốn hàng bán | Cost of Revenue |
| Lợi nhuận gộp | Gross Profit |
| Chi phí hoạt động | Operating Expenses |
| EBITDA | EBITDA |
| Lợi nhuận sau thuế | Net Income |

### Balance Sheet (Bảng cân đối kế toán)
| Vietnamese | English |
|------------|---------|
| Tổng tài sản | Total Assets |
| Tài sản ngắn hạn | Current Assets |
| Tổng nợ phải trả | Total Liabilities |
| Vốn chủ sở hữu | Total Equity |
| Tiền và tương đương tiền | Cash & Equivalents |
| Phải thu khách hàng | Accounts Receivable |
| Hàng tồn kho | Inventory |
| Nợ vay | Total Debt |

### Cash Flow (Báo cáo lưu chuyển tiền tệ)
| Vietnamese | English |
|------------|---------|
| Lưu chuyển tiền từ HĐKD | Operating Cash Flow |
| Lưu chuyển tiền từ HĐĐT | Investing Cash Flow |
| Lưu chuyển tiền từ HĐTC | Financing Cash Flow |
| Lưu chuyển tiền tự do | Free Cash Flow |

## Usage Examples

### Example 1: Extract from Local File

```python
from app.services.pdf_extraction_service import extract_financials_from_pdf

result = extract_financials_from_pdf(
    file_path="reports/VNM_Annual_Report_2023.pdf",
    method="auto"
)

print(f"Company: {result['company_name']}")
print(f"Revenue: {result['income_statement']['revenue']}")
print(f"Net Income: {result['income_statement']['net_income']}")
print(f"Confidence: {result['metadata']['confidence_score']}")
```

### Example 2: Process Multiple Reports

```python
from app.services.pdf_extraction_service import process_vietnamese_reports

report_files = [
    "reports/VNM_2023.pdf",
    "reports/VNM_2022.pdf",
    "reports/VNM_2021.pdf",
]

results = process_vietnamese_reports(report_files)

for report in results:
    if report.get('success'):
        print(f"Year {report['fiscal_year']}: Revenue = {report['income_statement']['revenue']}")
```

### Example 3: Integration with DCF Model

```python
from app.services.pdf_extraction_service import VietnamesePDFExtractor
from app.services.dcf_input_manager import create_dcf_inputs

# Extract data from PDF
extractor = VietnamesePDFExtractor()
result = extractor.extract_from_file("VNM_Report_2023.pdf")
pdf_data = extractor.to_dict(result)

# Use extracted data as API source for DCF
api_data = {
    "profile": {
        "symbol": "VNM.VN",
        "current_price": 85000,
        "sharesOutstanding": 2300000000,
    },
    "financials": {
        "revenue": {"2023": pdf_data['income_statement']['revenue']},
        "net_income": {"2023": pdf_data['income_statement']['net_income']},
    }
}

# Create DCF inputs
dcf_inputs = create_dcf_inputs(api_data=api_data)
```

## Report Sources

### Official Sources

1. **HOSE (Ho Chi Minh Stock Exchange)**
   - URL: https://hsx.vn
   - Contains: Official filings, annual reports, financial statements

2. **HNX (Hanoi Stock Exchange)**
   - URL: https://hnx.vn
   - Contains: Official filings for HNX-listed companies

### Financial Portals

1. **Cafef.vn**
   - URL: https://finance.cafef.vn
   - Popular portal with company profiles and reports

2. **Vietstock.vn**
   - URL: https://finance.vietstock.vn
   - Comprehensive financial data provider

3. **FiinPro**
   - URL: https://fiinpro.com
   - Professional financial data platform

## Best Practices

### 1. Choose the Right Method
- **Text-based PDFs**: Use `pdfplumber` or `auto`
- **Scanned documents**: Use `ocr` (requires Tesseract)
- **Complex tables**: Try `camelot` first

### 2. Validate Extracted Data
Always check the `confidence_score`:
- > 0.8: High confidence, likely accurate
- 0.5 - 0.8: Medium confidence, review recommended
- < 0.5: Low confidence, manual verification needed

### 3. Handle Vietnamese Number Formats
The system handles:
- Commas as thousand separators: `1,000,000`
- Vietnamese units: `tỷ` (billion), `triệu` (million), `nghìn` (thousand)
- Decimal commas: `10,5` → `10.5`

### 4. Store Raw Tables
Set `include_raw_tables=True` for debugging or manual review.

## Troubleshooting

### Issue: Low Confidence Score
**Solutions:**
- Try different extraction method
- Check if PDF is scanned (use OCR)
- Verify PDF quality

### Issue: Missing Data Fields
**Solutions:**
- Check if report uses different terminology
- Review raw tables for data location
- Consider manual data entry for critical fields

### Issue: OCR Not Working
**Solutions:**
- Install Tesseract OCR
- Install language pack: `sudo apt-get install tesseract-ocr-vie`
- Increase DPI in OCR settings

### Issue: Library Import Errors
**Solutions:**
```bash
# Reinstall dependencies
pip uninstall pdfplumber camelot-py tabula-py
pip install pdfplumber camelot-py[cv] tabula-py

# For camelot, may need ghostscript
sudo apt-get install ghostscript
```

## API Reference

Complete API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For issues or questions:
1. Check logs in `/workspace/backend/logs/`
2. Review extraction notes in API response
3. Verify PDF file integrity
