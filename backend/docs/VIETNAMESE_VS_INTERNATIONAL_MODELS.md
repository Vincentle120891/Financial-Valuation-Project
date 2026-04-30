# Vietnamese vs International Financial Input Models

## Overview

This system supports two distinct financial reporting standards based on market selection:

| Market | Standard | Currency | Model File |
|--------|----------|----------|------------|
| **Vietnamese** | Thông Tư 99/2025/TT-BTC (TT99) | VND (tỷ đồng) | `vietnamese_inputs_tt99.py` |
| **International** | IFRS / US GAAP | USD (default) | `international_inputs.py` |

---

## 🇻🇳 Vietnamese Market Model (TT99)

### Source Document
**Thông Tư 99/2025/TT-BTC** issued by Bộ Tài chính (Ministry of Finance) on 27/10/2025

### Report Forms
1. **Mẫu B 01 - DN**: Báo cáo Tình hình Tài chính (Balance Sheet)
2. **Mẫu B 02 - DN**: Báo cáo Kết quả Hoạt động Kinh doanh (Income Statement)

### Key Characteristics

#### Structure
- **Vertical format** for Balance Sheet
- **Waterfall structure** for Income Statement
- **Mã số (line codes)** embedded in field names (e.g., "110", "280", "440")
- **Contra-accounts** displayed in parentheses with negative values

#### Currency
- Default unit: **tỷ VND** (billion Vietnamese Dong)
- Can also be: triệu VND (million), nghìn VND (thousand)
- Field `currency_unit` specifies the reporting unit

#### Balance Sheet Formula
```
Mã 280 = Mã 440
Total Assets = Total Liabilities + Total Equity
```

#### Income Statement Formulas
```python
Mã 10 = 01 − 02          # Net Revenue
Mã 20 = 10 − 11          # Gross Profit
Mã 30 = 20 + 21 + 22 − (23 + 25 + 26)  # Operating Profit
Mã 40 = 31 − 32          # Other Profit
Mã 50 = 30 + 40          # Profit Before Tax
Mã 60 = 50 − 51 − 52     # Net Profit
```

### New Features in TT99 (vs TT200)
1. **Mã 21**: Separate line for investment property gains/losses
2. **Mã 124/266**: Provision for HTM investments
3. **Mã 164/325**: Government bond repo transactions
4. **Mã 341/411b**: Preference shares bifurcation (liability vs equity)
5. **Mã 420a/420b**: Split retained earnings (prior periods vs current)
6. **Biological assets**: Full sections (Mã 150, 230) aligned with IAS 41

### Example Usage

```python
from app.models.vietnamese_inputs_tt99 import VNFinancialInputs_TT99

vn_data = VNFinancialInputs_TT99(
    company_name="Công ty Cổ phần Sữa Việt Nam",
    ticker="VNM.VN",
    currency="VND",
    exchange="HOSE",
    balance_sheet={
        "reporting_entity": "VNM",
        "currency_unit": "tỷ VND",
        "reporting_date": "2023-12-31",
        "cash_and_equivalents": 8.5,
        "inventories": 6.8,
        "tangible_fixed_assets_net": 20.1,
        "total_assets": 50.5,
        "total_liabilities": 18.2,
        "total_equity": 32.3
    },
    income_statement={
        "reporting_entity": "VNM",
        "currency_unit": "tỷ VND",
        "period_from": "2023-01-01",
        "period_to": "2023-12-31",
        "net_revenue": 85.5,
        "gross_profit": 33.2,
        "operating_profit": 15.8,
        "net_profit": 12.7
    }
)
```

---

## 🌍 International Market Model (IFRS/US GAAP)

### Standards Supported
- **IFRS** (International Financial Reporting Standards)
- **US GAAP** (Generally Accepted Accounting Principles)

### Key Characteristics

#### Structure
- **Horizontal or vertical format** acceptable
- **No mandatory line codes** (flexible presentation)
- **Standard international terminology**

#### Currency
- Default: **USD**
- Can be any currency (EUR, GBP, JPY, etc.)
- Converted to USD for valuation if needed

#### Balance Sheet Equation
```
Total Assets = Total Liabilities + Shareholders' Equity
```

#### Income Statement Structure
```
Revenue
  − Cost of Goods Sold
= Gross Profit
  − Operating Expenses
= Operating Profit (EBIT)
  + Other Income
  − Other Expenses
= Profit Before Tax
  − Tax Expense
= Net Profit
```

### Example Usage

```python
from app.models.international_inputs import InternationalFinancialInputs

intl_data = InternationalFinancialInputs(
    company_name="Apple Inc.",
    ticker="AAPL",
    currency="USD",
    accounting_standard="US GAAP",
    balance_sheet={
        "cash_and_cash_equivalents": 29965000000,
        "accounts_receivable": 29508000000,
        "inventory": 6331000000,
        "property_plant_equipment": 43715000000,
        "total_assets": 352755000000,
        "accounts_payable": 62611000000,
        "long_term_debt": 95281000000,
        "share_capital": 73812000000,
        "retained_earnings": -214000000
    },
    income_statement={
        "gross_revenue": 383285000000,
        "net_revenue": 383285000000,
        "cost_of_goods_sold": 214137000000,
        "gross_profit": 169148000000,
        "operating_profit": 114301000000,
        "net_profit": 96995000000,
        "basic_eps": 6.16,
        "diluted_eps": 6.13
    }
)
```

---

## Mapping Between Standards

### Balance Sheet Mapping

| Vietnamese (TT99) | Mã | International (IFRS) |
|-------------------|----|---------------------|
| Tiền và tương đương tiền | 110 | Cash and cash equivalents |
| Đầu tư tài chính ngắn hạn | 120 | Short-term investments |
| Phải thu ngắn hạn | 130 | Accounts receivable |
| Hàng tồn kho | 140 | Inventory |
| TSCĐ hữu hình | 221 | Property, plant & equipment |
| BĐS đầu tư | 240 | Investment property |
| Vay ngắn hạn | 321 | Short-term debt |
| Vay dài hạn | 339 | Long-term debt |
| Vốn góp chủ sở hữu | 411 | Share capital |
| Lợi nhuận chưa phân phối | 420 | Retained earnings |

### Income Statement Mapping

| Vietnamese (TT99) | Mã | International (IFRS) |
|-------------------|----|---------------------|
| Doanh thu thuần | 10 | Revenue |
| Giá vốn hàng bán | 11 | Cost of sales |
| Lợi nhuận gộp | 20 | Gross profit |
| Lãi/lỗ BĐS đầu tư | 21 | Gain/loss on investment property |
| Doanh thu tài chính | 22 | Finance income |
| Chi phí tài chính | 23 | Finance expenses |
| Chi phí bán hàng | 25 | Selling expenses |
| Chi phí quản lý DN | 26 | G&A expenses |
| Lợi nhuận thuần HĐKD | 30 | Operating profit (EBIT) |
| Thuế TNDN hiện hành | 51 | Current tax expense |
| Thuế TNDN hoãn lại | 52 | Deferred tax expense |
| Lợi nhuận sau thuế | 60 | Net profit |

---

## API Integration

### Selecting Market

```python
# In your valuation route or service
if market == "vietnamese":
    from app.models.vietnamese_inputs_tt99 import VNFinancialInputs_TT99
    inputs = VNFinancialInputs_TT99(**data)
    currency = "VND"
else:  # international
    from app.models.international_inputs import InternationalFinancialInputs
    inputs = InternationalFinancialInputs(**data)
    currency = "USD"
```

### Currency Display Logic

```python
# In API response
response = {
    "company_name": inputs.company_name,
    "ticker": inputs.ticker,
    "currency": "VND" if market == "vietnamese" else "USD",
    "financials": {...},
    "valuation": {...}
}
```

---

## Validation Rules

### Vietnamese TT99
1. **Balance sheet must balance**: `abs(total_assets - (total_liabilities + total_equity)) < 0.01`
2. **Provision accounts must be negative**: Fields with `(*)` have `le=0` constraint
3. **Formulas must hold**: All calculated fields (Mã 10, 20, 30, etc.) can be validated

### International
1. **Balance sheet equation**: Standard accounting equation
2. **EPS calculation**: `basic_eps = net_profit / weighted_avg_shares`
3. **Consistency checks**: Prior period comparatives when available

---

## Files Structure

```
backend/app/models/
├── __init__.py                    # Package exports
├── vietnamese_inputs_tt99.py      # TT99 standard models
└── international_inputs.py        # IFRS/US GAAP models
```

---

## References

### Vietnamese Regulations
- **Thông tư 99/2025/TT-BTC**: Chế độ báo cáo tài chính cho doanh nghiệp
- Issued: 27/10/2025 by Bộ Tài chính
- Effective: Fiscal year 2025 onwards

### International Standards
- **IFRS**: International Financial Reporting Standards (IFRS Foundation)
- **US GAAP**: Financial Accounting Standards Board (FASB)

---

## Support

For questions about:
- **Vietnamese TT99 implementation**: See `vietnamese_inputs_tt99.py`
- **International standards**: See `international_inputs.py`
- **Mapping between standards**: See `VN_to_International_Mapping` class
