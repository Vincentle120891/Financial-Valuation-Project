# Vietnamese Financial Report Auto-Fetch Feature

## Overview

Automated search, download, and extraction of Vietnamese financial reports (Báo cáo tài chính - BCTC) from official sources.

## Features

### 1. Multi-Source Search
- **Company Websites**: Direct search on investor relations pages
- **HOSE/HNX Portals**: Official exchange information disclosure
- **Cafef/Vietstock**: Fallback financial news sites

### 2. TT99 Compliance
- Follows Thông Tư 99/2025/TT-BTC standards
- Supports both report types:
  - **Báo cáo thường niên** (Annual Reports)
  - **Báo cáo tài chính quý** (Quarterly Reports)

### 3. Complete Pipeline
Search → Download → Extract → Validate

## API Endpoints

### Search for Reports
```bash
POST /api/v1/vietnamese-reports/search
Content-Type: application/json

{
  "ticker": "VNM",
  "year": 2023,
  "report_type": "annual"
}
```

**Response:**
```json
{
  "success": true,
  "ticker": "VNM",
  "year": 2023,
  "count": 2,
  "reports": [
    {
      "source": "company_website",
      "ticker": "VNM",
      "year": 2023,
      "type": "annual",
      "url": "https://www.vinamilk.com.vn/...",
      "title": "Báo cáo thường niên 2023",
      "language": "vi"
    }
  ]
}
```

### Fetch and Extract
```bash
POST /api/v1/vietnamese-reports/fetch
Content-Type: application/json

{
  "ticker": "VNM",
  "year": 2023,
  "report_type": "annual",
  "extract_data": true
}
```

**Response:**
```json
{
  "success": true,
  "file_path": "downloads/reports/VNM_BCTC_2023.pdf",
  "report_info": {...},
  "message": "Report downloaded successfully",
  "extraction": {
    "success": true,
    "data": {
      "balance_sheet": {...},
      "income_statement": {...},
      "cash_flow": {...}
    }
  }
}
```

### Auto Fetch & Extract (All-in-One)
```bash
POST /api/v1/vietnamese-reports/auto-fetch-extract
Content-Type: application/json

{
  "ticker": "VCB",
  "year": 2023,
  "report_type": "annual"
}
```

### Get Supported Tickers
```bash
GET /api/v1/vietnamese-reports/supported-tickers
```

### Get Report Types
```bash
GET /api/v1/vietnamese-reports/report-types
```

## Supported Companies

### HOSE (Ho Chi Minh Stock Exchange)
- **VNM** - Vinamilk
- **VCB** - Vietcombank
- **HPG** - Hoa Phat Group
- **VIC** - Vingroup
- **VRE** - Vincom Retail
- **MSN** - Masan Group
- **MWG** - Mobile World
- **FPT** - FPT Corporation
- **SAB** - Sabeco
- **GAS** - PV Gas
- **VHM** - Vinhomes
- **ACB** - Asia Commercial Bank
- **TCB** - Techcombank
- **MBB** - MB Bank
- **STB** - Sacombank

### HNX & UPCOM
Additional tickers can be searched via HOSE/HNX portals.

## Usage Examples

### Python SDK Example
```python
from app.services.vietnamese_report_scraper import VietnameseReportScraper
from app.services.pdf_extraction_service import VietnamesePDFExtractor

# Initialize services
scraper = VietnameseReportScraper()
extractor = VietnamesePDFExtractor(extraction_method="auto")

# Search for reports
reports = scraper.search_reports("VNM", 2023, "annual")
print(f"Found {len(reports)} reports")

# Download and extract
result = scraper.auto_fetch_and_extract(
    ticker="VNM",
    year=2023,
    report_type="annual",
    extractor_service=extractor
)

if result["success"]:
    print(f"Extracted data: {result['data']['income_statement']['revenue']}")
```

### cURL Examples

#### Search
```bash
curl -X POST "http://localhost:8000/api/v1/vietnamese-reports/search" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "VNM", "year": 2023, "report_type": "annual"}'
```

#### Fetch with Extraction
```bash
curl -X POST "http://localhost:8000/api/v1/vietnamese-reports/fetch" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "VNM", "year": 2023, "extract_data": true}'
```

#### Auto Fetch & Extract
```bash
curl -X POST "http://localhost:8000/api/v1/vietnamese-reports/auto-fetch-extract" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "FPT", "year": 2023}'
```

## TT99 Data Structure

Extracted data follows the official Vietnamese reporting template:

### Balance Sheet (B 01 - DN)
- Mã 100: Short-term Assets
- Mã 200: Long-term Assets
- Mã 280: Total Assets
- Mã 300: Liabilities
- Mã 400: Equity
- Mã 440: Total Funding

### Income Statement (B 02 - DN)
- Mã 01: Gross Revenue
- Mã 10: Net Revenue
- Mã 11: COGS
- Mã 20: Gross Profit
- Mã 30: Operating Profit
- Mã 50: Pre-tax Profit
- Mã 60: Net Profit

### Cash Flow Statement (B 03 - DN)
- Mã 20: Operating Cash Flow
- Mã 30: Investing Cash Flow
- Mã 40: Financing Cash Flow
- Mã 50: Net Cash Flow
- Mã 70: Closing Cash Balance

## Validation Rules

The system automatically validates:
1. **Balance Sheet**: Mã 280 = Mã 440 (Assets = Liabilities + Equity)
2. **Cash Flow**: Mã 50 = Mã 20 + Mã 30 + Mã 40
3. **Cash Reconciliation**: Mã 70 = Mã 50 + Mã 60 + Mã 61
4. **Income Statement**: All formula-based codes (e.g., Mã 10 = 01 - 02)

## Requirements

### Python Dependencies
```bash
pip install requests beautifulsoup4 pdfplumber camelot-py tabula-py
```

### System Dependencies (for OCR)
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-vie poppler-utils
```

## Limitations

1. **HOSE/HNX Access**: Direct scraping may require authentication or have CAPTCHA protection
2. **Website Changes**: Company website structures may change, requiring selector updates
3. **PDF Quality**: Scanned PDFs may require OCR for accurate extraction
4. **Language**: Currently optimized for Vietnamese-language reports only

## Future Enhancements

- [ ] Official HOSE/HNX API integration
- [ ] Support for English-language reports
- [ ] Historical data archive
- [ ] Real-time report monitoring
- [ ] Bulk download for multiple years
- [ ] Excel export functionality
