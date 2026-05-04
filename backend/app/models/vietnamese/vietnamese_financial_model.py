"""
Vietnamese Financial Reporting Model - Thông Tư 99/2025/TT-BTC
Complete implementation of Mẫu số B 01, B 02, and B 03 - DN

This module provides:
1. Data structures aligned with TT99 chart of accounts (Mã số)
2. Validation rules for cross-statement linkages
3. Mapping to international equivalents (IFRS/US GAAP)
4. Support for both Direct and Indirect cash flow methods
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class ReportType(Enum):
    """Vietnamese financial report types per TT99"""
    BALANCE_SHEET = "B 01 - DN"
    INCOME_STATEMENT = "B 02 - DN"
    CASH_FLOW_DIRECT = "B 03 - DN (Direct)"
    CASH_FLOW_INDIRECT = "B 03 - DN (Indirect)"


class CurrencyUnit(Enum):
    """Currency units used in Vietnamese reports"""
    VND = "VND"
    TRIEU_DONG = "triệu đồng"  # Million VND
    TY_DONG = "tỷ đồng"  # Billion VND
    USD = "USD"
    EUR = "EUR"


@dataclass
class LineItem:
    """Represents a single line item in Vietnamese financial statements"""
    ma_so: str  # Mã số (line code - must NOT be renumbered)
    chi_tieu: str  # Chỉ tiêu (line item name in Vietnamese)
    chi_tieu_en: str  # English translation
    value_current: Optional[float] = None  # Current period value
    value_prior: Optional[float] = None  # Prior period value
    note_reference: Optional[str] = None  # Thuyết minh reference
    is_contra_account: bool = False  # Items marked (*) shown in parentheses
    parent_ma_so: Optional[str] = None  # Parent line item code for hierarchy


@dataclass
class BalanceSheetTT99:
    """
    Mẫu số B 01 - DN: Báo cáo Tình hình Tài chính (Balance Sheet)
    Vertical format: Assets (A+B), then Liabilities (C) and Equity (D)
    Balancing equation: Mã 280 = Mã 440
    """
    company_name: str = ""
    address: str = ""
    currency_unit: CurrencyUnit = CurrencyUnit.VND
    reporting_date: Optional[datetime] = None
    fiscal_year: int = 0
    
    # Section A - Short-term Assets (Tài sản ngắn hạn)
    assets_short_term: List[LineItem] = field(default_factory=list)
    # 110: Cash & Cash Equivalents
    # 120: Short-term Financial Investments
    # 130: Short-term Receivables
    # 140: Inventories
    # 150: Short-term Biological Assets
    # 160: Other Short-term Assets
    
    # Section B - Long-term Assets (Tài sản dài hạn)
    assets_long_term: List[LineItem] = field(default_factory=list)
    # 210: Long-term Receivables
    # 220: Fixed Assets
    # 230: Long-term Biological Assets
    # 240: Investment Property
    # 250: Long-term Work-in-Progress
    # 260: Long-term Financial Investments
    # 270: Other Long-term Assets
    
    # Totals
    total_assets: Optional[float] = None  # Mã 280 = 100 + 200
    
    # Section C - Liabilities (Nợ phải trả)
    liabilities_short_term: List[LineItem] = field(default_factory=list)
    # 310: Short-term Liabilities
    # 330: Long-term Liabilities
    
    liabilities_long_term: List[LineItem] = field(default_factory=list)
    total_liabilities: Optional[float] = None  # Mã 300
    
    # Section D - Owners' Equity (Vốn chủ sở hữu)
    equity: List[LineItem] = field(default_factory=list)
    # 411: Contributed Charter Capital
    # 412: Share Premium
    # 420: Retained Earnings (split into 420a and 420b)
    total_equity: Optional[float] = None  # Mã 400
    
    # Total Funding (Tổng cộng nguồn vốn)
    total_funding: Optional[float] = None  # Mã 440 = 300 + 400
    
    # Metadata
    extraction_method: str = ""
    confidence_score: float = 0.0
    source_file: str = ""
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate balance sheet balancing equation"""
        errors = []
        
        if self.total_assets is not None and self.total_funding is not None:
            tolerance = abs(self.total_assets) * 0.001  # 0.1% tolerance
            if abs(self.total_assets - self.total_funding) > tolerance:
                errors.append(
                    f"Balance sheet does not balance: "
                    f"Tổng tài sản (280)={self.total_assets} ≠ "
                    f"Tổng nguồn vốn (440)={self.total_funding}"
                )
        
        if self.total_liabilities is not None and self.total_equity is not None:
            expected_funding = self.total_liabilities + self.total_equity
            if self.total_funding is not None:
                tolerance = abs(expected_funding) * 0.001
                if abs(expected_funding - self.total_funding) > tolerance:
                    errors.append(
                        f"Total funding mismatch: "
                        f"Lợi nhuận + Vốn chủ sở hữu={expected_funding} ≠ "
                        f"Tổng nguồn vốn (440)={self.total_funding}"
                    )
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'company_name': self.company_name,
            'fiscal_year': self.fiscal_year,
            'currency': self.currency_unit.value,
            'reporting_date': self.reporting_date.isoformat() if self.reporting_date else None,
            'total_assets': self.total_assets,
            'total_liabilities': self.total_liabilities,
            'total_equity': self.total_equity,
            'validation_passed': self.validate()[0],
            'validation_errors': self.validate()[1],
        }


@dataclass
class IncomeStatementTT99:
    """
    Mẫu số B 02 - DN: Báo cáo Kết quả Hoạt động Kinh doanh (Income Statement)
    Waterfall structure from revenue to net profit
    Includes embedded formulas via Mã số
    """
    company_name: str = ""
    currency_unit: CurrencyUnit = CurrencyUnit.VND
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    fiscal_year: int = 0
    
    # Revenue section
    gross_revenue: Optional[float] = None  # Mã 01: Doanh thu bán hàng và cung cấp dịch vụ
    revenue_deductions: Optional[float] = None  # Mã 02: Các khoản giảm trừ doanh thu
    net_revenue: Optional[float] = None  # Mã 10 = 01 - 02
    
    # Cost and Gross Profit
    cost_of_goods_sold: Optional[float] = None  # Mã 11: Giá vốn hàng bán
    gross_profit: Optional[float] = None  # Mã 20 = 10 - 11
    
    # Operating items
    investment_property_gain_loss: Optional[float] = None  # Mã 21 (NEW in TT99)
    financial_income: Optional[float] = None  # Mã 22: Doanh thu hoạt động tài chính
    financial_expenses: Optional[float] = None  # Mã 23: Chi phí tài chính
    borrowing_costs: Optional[float] = None  # Mã 24: Trong đó: Chi phí đi vay
    selling_expenses: Optional[float] = None  # Mã 25: Chi phí bán hàng
    administrative_expenses: Optional[float] = None  # Mã 26: Chi phí quản lý doanh nghiệp
    
    # Operating Profit
    operating_profit: Optional[float] = None  # Mã 30 = 20 + 21 + 22 - (23 + 25 + 26)
    
    # Other items
    other_income: Optional[float] = None  # Mã 31: Thu nhập khác
    other_expenses: Optional[float] = None  # Mã 32: Chi phí khác
    other_profit: Optional[float] = None  # Mã 40 = 31 - 32
    
    # Pre-tax and Tax
    profit_before_tax: Optional[float] = None  # Mã 50 = 30 + 40
    current_income_tax: Optional[float] = None  # Mã 51: Chi phí thuế TNDN hiện hành
    deferred_income_tax: Optional[float] = None  # Mã 52: Chi phí thuế TNDN hoãn lại
    
    # Net Profit
    net_profit: Optional[float] = None  # Mã 60 = 50 - 51 - 52
    
    # Per-share data (joint-stock companies only)
    basic_eps: Optional[float] = None  # Mã 70: Lãi cơ bản trên cổ phiếu
    diluted_eps: Optional[float] = None  # Mã 71: Lãi suy giảm trên cổ phiếu
    
    # Metadata
    extraction_method: str = ""
    confidence_score: float = 0.0
    source_file: str = ""
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate income statement calculations"""
        errors = []
        
        # Check Net Revenue calculation
        if self.gross_revenue is not None and self.revenue_deductions is not None:
            expected_net = self.gross_revenue - self.revenue_deductions
            if self.net_revenue is not None:
                tolerance = abs(expected_net) * 0.001
                if abs(self.net_revenue - expected_net) > tolerance:
                    errors.append(f"Mã 10 mismatch: {self.net_revenue} ≠ {expected_net}")
        
        # Check Gross Profit calculation
        if self.net_revenue is not None and self.cost_of_goods_sold is not None:
            expected_gross = self.net_revenue - self.cost_of_goods_sold
            if self.gross_profit is not None:
                tolerance = abs(expected_gross) * 0.001
                if abs(self.gross_profit - expected_gross) > tolerance:
                    errors.append(f"Mã 20 mismatch: {self.gross_profit} ≠ {expected_gross}")
        
        # Check Operating Profit calculation
        if all([
            self.gross_profit,
            self.financial_income,
            self.financial_expenses,
            self.selling_expenses,
            self.administrative_expenses
        ]):
            expected_operating = (
                self.gross_profit + 
                (self.investment_property_gain_loss or 0) + 
                self.financial_income - 
                self.financial_expenses - 
                self.selling_expenses - 
                self.administrative_expenses
            )
            if self.operating_profit is not None:
                tolerance = abs(expected_operating) * 0.001
                if abs(self.operating_profit - expected_operating) > tolerance:
                    errors.append(f"Mã 30 mismatch: {self.operating_profit} ≠ {expected_operating}")
        
        # Check Pre-tax Profit calculation
        if self.operating_profit is not None:
            expected_pbt = self.operating_profit + (self.other_profit or 0)
            if self.profit_before_tax is not None:
                tolerance = abs(expected_pbt) * 0.001
                if abs(self.profit_before_tax - expected_pbt) > tolerance:
                    errors.append(f"Mã 50 mismatch: {self.profit_before_tax} ≠ {expected_pbt}")
        
        # Check Net Profit calculation
        if all([self.profit_before_tax, self.current_income_tax, self.deferred_income_tax]):
            expected_net = self.profit_before_tax - self.current_income_tax - self.deferred_income_tax
            if self.net_profit is not None:
                tolerance = abs(expected_net) * 0.001
                if abs(self.net_profit - expected_net) > tolerance:
                    errors.append(f"Mã 60 mismatch: {self.net_profit} ≠ {expected_net}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'company_name': self.company_name,
            'fiscal_year': self.fiscal_year,
            'currency': self.currency_unit.value,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'net_revenue': self.net_revenue,
            'gross_profit': self.gross_profit,
            'operating_profit': self.operating_profit,
            'profit_before_tax': self.profit_before_tax,
            'net_profit': self.net_profit,
            'basic_eps': self.basic_eps,
            'diluted_eps': self.diluted_eps,
            'validation_passed': self.validate()[0],
            'validation_errors': self.validate()[1],
        }


@dataclass
class CashFlowStatementTT99:
    """
    Mẫu số B 03 - DN: Báo cáo Lưu chuyển Tiền tệ
    Supports both Direct Method (Phương pháp trực tiếp) and 
    Indirect Method (Phương pháp gián tiếp)
    
    Master balancing formula:
    Mã 50 = Mã 20 + Mã 30 + Mã 40
    Mã 70 = Mã 50 + Mã 60 + Mã 61
    """
    company_name: str = ""
    currency_unit: CurrencyUnit = CurrencyUnit.VND
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    fiscal_year: int = 0
    method: str = "indirect"  # "direct" or "indirect"
    
    # ========== SECTION I: OPERATING ACTIVITIES ==========
    # Direct Method lines (01-07)
    direct_cash_from_customers: Optional[float] = None  # Mã 01
    direct_cash_to_suppliers: Optional[float] = None  # Mã 02 (...)
    direct_cash_to_employees: Optional[float] = None  # Mã 03 (...)
    direct_interest_paid: Optional[float] = None  # Mã 04 (...)
    direct_cit_paid: Optional[float] = None  # Mã 05 (...)
    direct_other_operating_receipts: Optional[float] = None  # Mã 06
    direct_other_operating_payments: Optional[float] = None  # Mã 07 (...)
    
    # Indirect Method lines (01-17)
    indirect_profit_before_tax: Optional[float] = None  # Mã 01
    indirect_depreciation: Optional[float] = None  # Mã 02
    indirect_provisions: Optional[float] = None  # Mã 03
    indirect_unrealized_fx: Optional[float] = None  # Mã 04
    indirect_investment_gains_losses: Optional[float] = None  # Mã 05
    indirect_borrowing_costs: Optional[float] = None  # Mã 06
    indirect_other_adjustments: Optional[float] = None  # Mã 07
    indirect_operating_profit_before_wc: Optional[float] = None  # Mã 08
    indirect_change_in_receivables: Optional[float] = None  # Mã 09
    indirect_change_in_inventory: Optional[float] = None  # Mã 10
    indirect_change_in_payables: Optional[float] = None  # Mã 11
    indirect_change_in_prepaid: Optional[float] = None  # Mã 12
    indirect_change_in_trading_securities: Optional[float] = None  # Mã 13
    indirect_interest_paid: Optional[float] = None  # Mã 14 (...)
    indirect_cit_paid: Optional[float] = None  # Mã 15 (...)
    indirect_other_operating_receipts: Optional[float] = None  # Mã 16
    indirect_other_operating_payments: Optional[float] = None  # Mã 17 (...)
    
    # Net Operating Cash Flow
    operating_cash_flow: Optional[float] = None  # Mã 20
    
    # ========== SECTION II: INVESTING ACTIVITIES ==========
    investing_capex: Optional[float] = None  # Mã 21 (...)
    investing_proceeds_from_disposal: Optional[float] = None  # Mã 22
    investing_loans_given: Optional[float] = None  # Mã 23 (...)
    investing_loans_repaid: Optional[float] = None  # Mã 24
    investing_equity_investments: Optional[float] = None  # Mã 25 (...)
    investing_divestment_proceeds: Optional[float] = None  # Mã 26
    investing_interest_dividends_received: Optional[float] = None  # Mã 27
    
    # Net Investing Cash Flow
    investing_cash_flow: Optional[float] = None  # Mã 30
    
    # ========== SECTION III: FINANCING ACTIVITIES ==========
    financing_share_issuance: Optional[float] = None  # Mã 31
    financing_share_repurchase: Optional[float] = None  # Mã 32 (...)
    financing_borrowings_proceeds: Optional[float] = None  # Mã 33
    financing_loan_repayments: Optional[float] = None  # Mã 34 (...)
    financing_lease_repayments: Optional[float] = None  # Mã 35 (...)
    financing_dividends_paid: Optional[float] = None  # Mã 36 (...)
    
    # Net Financing Cash Flow
    financing_cash_flow: Optional[float] = None  # Mã 40
    
    # ========== RECONCILIATION ==========
    net_cash_flow: Optional[float] = None  # Mã 50 = 20 + 30 + 40
    opening_cash: Optional[float] = None  # Mã 60
    fx_effect: Optional[float] = None  # Mã 61
    closing_cash: Optional[float] = None  # Mã 70 = 50 + 60 + 61
    
    # Metadata
    extraction_method: str = ""
    confidence_score: float = 0.0
    source_file: str = ""
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate cash flow statement calculations"""
        errors = []
        
        # Validate Net Operating Cash Flow
        if self.method == "direct":
            if all([
                self.direct_cash_from_customers,
                self.direct_cash_to_suppliers,
                self.direct_cash_to_employees,
                self.direct_interest_paid,
                self.direct_cit_paid
            ]):
                expected_cfo = (
                    (self.direct_cash_from_customers or 0) +
                    (self.direct_cash_to_suppliers or 0) +
                    (self.direct_cash_to_employees or 0) +
                    (self.direct_interest_paid or 0) +
                    (self.direct_cit_paid or 0) +
                    (self.direct_other_operating_receipts or 0) +
                    (self.direct_other_operating_payments or 0)
                )
                if self.operating_cash_flow is not None:
                    tolerance = abs(expected_cfo) * 0.001
                    if abs(self.operating_cash_flow - expected_cfo) > tolerance:
                        errors.append(f"Mã 20 (Direct) mismatch: {self.operating_cash_flow} ≠ {expected_cfo}")
        
        elif self.method == "indirect":
            if self.indirect_operating_profit_before_wc is not None:
                expected_cfo = (
                    self.indirect_operating_profit_before_wc +
                    (self.indirect_change_in_receivables or 0) +
                    (self.indirect_change_in_inventory or 0) +
                    (self.indirect_change_in_payables or 0) +
                    (self.indirect_change_in_prepaid or 0) +
                    (self.indirect_change_in_trading_securities or 0) +
                    (self.indirect_interest_paid or 0) +
                    (self.indirect_cit_paid or 0) +
                    (self.indirect_other_operating_receipts or 0) +
                    (self.indirect_other_operating_payments or 0)
                )
                if self.operating_cash_flow is not None:
                    tolerance = abs(expected_cfo) * 0.001
                    if abs(self.operating_cash_flow - expected_cfo) > tolerance:
                        errors.append(f"Mã 20 (Indirect) mismatch: {self.operating_cash_flow} ≠ {expected_cfo}")
        
        # Validate Net Cash Flow
        if all([self.operating_cash_flow, self.investing_cash_flow, self.financing_cash_flow]):
            expected_net = self.operating_cash_flow + self.investing_cash_flow + self.financing_cash_flow
            if self.net_cash_flow is not None:
                tolerance = abs(expected_net) * 0.001
                if abs(self.net_cash_flow - expected_net) > tolerance:
                    errors.append(f"Mã 50 mismatch: {self.net_cash_flow} ≠ {expected_net}")
        
        # Validate Closing Cash
        if all([self.net_cash_flow, self.opening_cash]):
            expected_closing = self.net_cash_flow + self.opening_cash + (self.fx_effect or 0)
            if self.closing_cash is not None:
                tolerance = abs(expected_closing) * 0.001
                if abs(self.closing_cash - expected_closing) > tolerance:
                    errors.append(f"Mã 70 mismatch: {self.closing_cash} ≠ {expected_closing}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'company_name': self.company_name,
            'fiscal_year': self.fiscal_year,
            'currency': self.currency_unit.value,
            'method': self.method,
            'operating_cash_flow': self.operating_cash_flow,
            'investing_cash_flow': self.investing_cash_flow,
            'financing_cash_flow': self.financing_cash_flow,
            'net_cash_flow': self.net_cash_flow,
            'opening_cash': self.opening_cash,
            'closing_cash': self.closing_cash,
            'fx_effect': self.fx_effect,
            'validation_passed': self.validate()[0],
            'validation_errors': self.validate()[1],
        }


# Standard line items per TT99 templates
STANDARD_LINE_ITEMS_B01 = {
    # Section A - Short-term Assets
    '100': {'vi': 'TÀI SẢN NGẮN HẠN', 'en': 'Short-term Assets'},
    '110': {'vi': 'Tiền và các khoản tương đương tiền', 'en': 'Cash and Cash Equivalents'},
    '111': {'vi': 'Tiền', 'en': 'Cash'},
    '112': {'vi': 'Các khoản tương đương tiền', 'en': 'Cash equivalents'},
    '120': {'vi': 'Đầu tư tài chính ngắn hạn', 'en': 'Short-term Financial Investments'},
    '130': {'vi': 'Các khoản phải thu ngắn hạn', 'en': 'Short-term Receivables'},
    '140': {'vi': 'Hàng tồn kho', 'en': 'Inventories'},
    '150': {'vi': 'Tài sản sinh học ngắn hạn', 'en': 'Short-term Biological Assets'},
    '160': {'vi': 'Tài sản ngắn hạn khác', 'en': 'Other Short-term Assets'},
    
    # Section B - Long-term Assets
    '200': {'vi': 'TÀI SẢN DÀI HẠN', 'en': 'Long-term Assets'},
    '210': {'vi': 'Các khoản phải thu dài hạn', 'en': 'Long-term Receivables'},
    '220': {'vi': 'Tài sản cố định', 'en': 'Fixed Assets'},
    '221': {'vi': 'Tài sản cố định hữu hình', 'en': 'Tangible Fixed Assets'},
    '227': {'vi': 'Tài sản cố định vô hình', 'en': 'Intangible Fixed Assets'},
    '230': {'vi': 'Tài sản sinh học dài hạn', 'en': 'Long-term Biological Assets'},
    '240': {'vi': 'Bất động sản đầu tư', 'en': 'Investment Property'},
    '250': {'vi': 'Tài sản dở dang dài hạn', 'en': 'Long-term Work-in-Progress'},
    '260': {'vi': 'Đầu tư tài chính dài hạn', 'en': 'Long-term Financial Investments'},
    '270': {'vi': 'Tài sản dài hạn khác', 'en': 'Other Long-term Assets'},
    '280': {'vi': 'TỔNG CỘNG TÀI SẢN', 'en': 'TOTAL ASSETS'},
    
    # Section C - Liabilities
    '300': {'vi': 'NỢ PHẢI TRẢ', 'en': 'LIABILITIES'},
    '310': {'vi': 'Nợ ngắn hạn', 'en': 'Short-term Liabilities'},
    '330': {'vi': 'Nợ dài hạn', 'en': 'Long-term Liabilities'},
    
    # Section D - Equity
    '400': {'vi': 'VỐN CHỦ SỞ HỮU', 'en': 'OWNERS\' EQUITY'},
    '411': {'vi': 'Vốn góp của chủ sở hữu', 'en': 'Contributed Charter Capital'},
    '412': {'vi': 'Thặng dư vốn', 'en': 'Share Premium'},
    '420': {'vi': 'Lợi nhuận sau thuế chưa phân phối', 'en': 'Retained Earnings'},
    '440': {'vi': 'TỔNG CỘNG NGUỒN VỐN', 'en': 'TOTAL FUNDING'},
}

STANDARD_LINE_ITEMS_B02 = {
    '01': {'vi': 'Doanh thu bán hàng và cung cấp dịch vụ', 'en': 'Gross Revenue'},
    '02': {'vi': 'Các khoản giảm trừ doanh thu', 'en': 'Revenue Deductions'},
    '10': {'vi': 'Doanh thu thuần', 'en': 'Net Revenue', 'formula': '01 - 02'},
    '11': {'vi': 'Giá vốn hàng bán', 'en': 'Cost of Goods Sold'},
    '20': {'vi': 'Lợi nhuận gộp', 'en': 'Gross Profit', 'formula': '10 - 11'},
    '21': {'vi': 'Lãi/lỗ từ hoạt động BĐS đầu tư', 'en': 'Gain/Loss on Investment Property'},
    '22': {'vi': 'Doanh thu hoạt động tài chính', 'en': 'Financial Income'},
    '23': {'vi': 'Chi phí tài chính', 'en': 'Financial Expenses'},
    '24': {'vi': 'Trong đó: Chi phí đi vay', 'en': 'Borrowing Costs'},
    '25': {'vi': 'Chi phí bán hàng', 'en': 'Selling Expenses'},
    '26': {'vi': 'Chi phí quản lý doanh nghiệp', 'en': 'Administrative Expenses'},
    '30': {'vi': 'Lợi nhuận thuần từ HĐKD', 'en': 'Operating Profit', 
           'formula': '20 + 21 + 22 - (23 + 25 + 26)'},
    '31': {'vi': 'Thu nhập khác', 'en': 'Other Income'},
    '32': {'vi': 'Chi phí khác', 'en': 'Other Expenses'},
    '40': {'vi': 'Lợi nhuận khác', 'en': 'Other Profit', 'formula': '31 - 32'},
    '50': {'vi': 'Tổng lợi nhuận kế toán trước thuế', 'en': 'Profit Before Tax', 
           'formula': '30 + 40'},
    '51': {'vi': 'Chi phí thuế TNDN hiện hành', 'en': 'Current Income Tax'},
    '52': {'vi': 'Chi phí thuế TNDN hoãn lại', 'en': 'Deferred Income Tax'},
    '60': {'vi': 'Lợi nhuận sau thuế', 'en': 'Net Profit', 'formula': '50 - 51 - 52'},
    '70': {'vi': 'Lãi cơ bản trên cổ phiếu', 'en': 'Basic EPS'},
    '71': {'vi': 'Lãi suy giảm trên cổ phiếu', 'en': 'Diluted EPS'},
}

STANDARD_LINE_ITEMS_B03 = {
    # Operating Activities (Direct)
    '01': {'vi': 'Tiền thu từ bán hàng, cung cấp dịch vụ', 'en': 'Cash from Customers'},
    '02': {'vi': 'Tiền chi trả cho người cung cấp', 'en': 'Cash to Suppliers', 'contra': True},
    '03': {'vi': 'Tiền chi trả cho người lao động', 'en': 'Cash to Employees', 'contra': True},
    '04': {'vi': 'Chi phí đi vay đã trả', 'en': 'Interest Paid', 'contra': True},
    '05': {'vi': 'Thuế TNDN đã nộp', 'en': 'CIT Paid', 'contra': True},
    '06': {'vi': 'Tiền thu khác từ HĐKD', 'en': 'Other Operating Receipts'},
    '07': {'vi': 'Tiền chi khác cho HĐKD', 'en': 'Other Operating Payments', 'contra': True},
    
    # Operating Activities (Indirect)
    'I-01': {'vi': 'Lợi nhuận trước thuế', 'en': 'Profit Before Tax'},
    'I-02': {'vi': 'Khấu hao TSCĐ và BĐSĐT', 'en': 'Depreciation'},
    'I-08': {'vi': 'LN từ HĐKD trước thay đổi VLĐ', 'en': 'Operating Profit before WC Changes'},
    'I-09': {'vi': 'Tăng/giảm các khoản phải thu', 'en': 'Change in Receivables'},
    'I-10': {'vi': 'Tăng/giảm hàng tồn kho', 'en': 'Change in Inventory'},
    'I-11': {'vi': 'Tăng/giảm các khoản phải trả', 'en': 'Change in Payables'},
    
    # All sections
    '20': {'vi': 'Lưu chuyển tiền thuần từ HĐKD', 'en': 'Net Operating Cash Flow'},
    '21': {'vi': 'Tiền chi mua sắm TSCĐ', 'en': 'Capex', 'contra': True},
    '27': {'vi': 'Tiền thu lãi cho vay, cổ tức', 'en': 'Interest/Dividends Received'},
    '30': {'vi': 'Lưu chuyển tiền thuần từ HĐ đầu tư', 'en': 'Net Investing Cash Flow'},
    '31': {'vi': 'Tiền thu từ phát hành cổ phiếu', 'en': 'Share Issuance Proceeds'},
    '34': {'vi': 'Tiền trả nợ gốc vay', 'en': 'Loan Repayments', 'contra': True},
    '36': {'vi': 'Cổ tức đã trả', 'en': 'Dividends Paid', 'contra': True},
    '40': {'vi': 'Lưu chuyển tiền thuần từ HĐ tài chính', 'en': 'Net Financing Cash Flow'},
    '50': {'vi': 'Lưu chuyển tiền thuần trong kỳ', 'en': 'Net Cash Flow'},
    '60': {'vi': 'Tiền và TĐTT đầu kỳ', 'en': 'Opening Cash'},
    '61': {'vi': 'Ảnh hưởng tỷ giá hối đoái', 'en': 'FX Effect'},
    '70': {'vi': 'Tiền và TĐTT cuối kỳ', 'en': 'Closing Cash'},
}


def create_vietnamese_line_item(ma_so: str, value_current: float = None, 
                                value_prior: float = None) -> LineItem:
    """Factory function to create standardized line items per TT99"""
    
    # Try B01 first, then B02, then B03
    standard_items = (STANDARD_LINE_ITEMS_B01.get(ma_so) or 
                     STANDARD_LINE_ITEMS_B02.get(ma_so) or 
                     STANDARD_LINE_ITEMS_B03.get(ma_so))
    
    if not standard_items:
        raise ValueError(f"Unknown Mã số: {ma_so}")
    
    return LineItem(
        ma_so=ma_so,
        chi_tieu=standard_items['vi'],
        chi_tieu_en=standard_items['en'],
        value_current=value_current,
        value_prior=value_prior,
        is_contra_account=standard_items.get('contra', False)
    )


# International mapping reference
INTERNATIONAL_MAPPING = {
    # Balance Sheet
    '280': 'Total Assets (IFRS)',
    '440': 'Total Liabilities & Equity (IFRS)',
    '110': 'Cash and Cash Equivalents (IAS 7)',
    '221': 'Property, Plant & Equipment (IAS 16)',
    '227': 'Intangible Assets (IAS 38)',
    '240': 'Investment Property (IAS 40)',
    '150/230': 'Biological Assets (IAS 41)',
    '411': 'Share Capital (IAS 32)',
    '420': 'Retained Earnings (IAS 1)',
    
    # Income Statement
    '10': 'Revenue (IFRS 15)',
    '11': 'Cost of Sales',
    '20': 'Gross Profit',
    '30': 'Operating Profit / EBIT',
    '50': 'Profit Before Tax',
    '60': 'Profit for the Period',
    '70/71': 'Basic/Diluted EPS (IAS 33)',
    
    # Cash Flow
    '20': 'Cash Flows from Operating Activities (IAS 7)',
    '30': 'Cash Flows from Investing Activities (IAS 7)',
    '40': 'Cash Flows from Financing Activities (IAS 7)',
    '50': 'Net Increase/Decrease in Cash (IAS 7)',
    '70': 'Cash and Cash Equivalents at End of Period (IAS 7)',
}
