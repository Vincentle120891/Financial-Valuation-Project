"""
Vietnamese Financial Report Inputs Model
Thông Tư 99/2025/TT-BTC (TT99) Standard Format
Used when market selection is 'vietnamese'
Currency: VND (in billions - tỷ đồng)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date


class VNBalanceSheet_B01_DN(BaseModel):
    """
    Mẫu số B 01 - DN: Báo cáo Tình hình Tài chính (Balance Sheet)
    Theo Thông Tư 99/2025/TT-BTC
    
    Vertical format: Assets (A + B), then Liabilities (C) and Equity (D)
    Balancing equation: Mã 280 = Mã 440 (Total Assets = Total Funding)
    
    Currency unit: Typically in billion VND (tỷ đồng) or million VND (triệu đồng)
    """
    
    # Reporting metadata
    reporting_entity: str = Field(..., description="Đơn vị báo cáo - Reporting entity name")
    address: Optional[str] = Field(None, description="Địa chỉ - Address")
    currency_unit: str = Field("tỷ VND", description="Đơn vị tính - Currency unit")
    reporting_date: Optional[date] = Field(None, description="As at date (31.12.X)")
    
    # ──────────────────────────────────────────────────────────────────────────────
    # A - TÀI SẢN NGẮN HẠN (SHORT-TERM ASSETS) | Mã 100
    # ──────────────────────────────────────────────────────────────────────────────
    
    # I. Tiền và các khoản tương đương tiền (Cash & Cash Equivalents) | 110
    cash_and_equivalents: Optional[float] = Field(None, alias="110", description="Tiền và các khoản tương đương tiền")
    cash: Optional[float] = Field(None, alias="111", description="Tiền - Cash")
    cash_equivalents: Optional[float] = Field(None, alias="112", description="Các khoản tương đương tiền")
    
    # II. Đầu tư tài chính ngắn hạn (Short-term financial investments) | 120
    short_term_financial_investments: Optional[float] = Field(None, alias="120", description="Đầu tư tài chính ngắn hạn")
    trading_securities: Optional[float] = Field(None, alias="121", description="Chứng khoán kinh doanh")
    provision_trading_securities: Optional[float] = Field(None, alias="122", description="Dự phòng giảm giá CKKD (*)", le=0)
    htm_investments_short_term: Optional[float] = Field(None, alias="123", description="Đầu tư nắm giữ đến ngày đáo hạn ngắn hạn")
    provision_htm_st: Optional[float] = Field(None, alias="124", description="Dự phòng ĐT nắm giữ đến ngày đáo hạn ST (*)", le=0)
    other_short_term_investments: Optional[float] = Field(None, alias="125", description="Đầu tư ngắn hạn khác")
    provision_other_st_investments: Optional[float] = Field(None, alias="126", description="Dự phòng tổn thất các khoản ĐT ngắn hạn khác (*)", le=0)
    
    # III. Các khoản phải thu ngắn hạn (Short-term receivables) | 130
    short_term_receivables: Optional[float] = Field(None, alias="130", description="Các khoản phải thu ngắn hạn")
    trade_receivables_short_term: Optional[float] = Field(None, alias="131", description="Phải thu ngắn hạn của khách hàng")
    prepaid_to_suppliers_short_term: Optional[float] = Field(None, alias="132", description="Trả trước cho người bán ngắn hạn")
    intra_group_receivables_short_term: Optional[float] = Field(None, alias="133", description="Phải thu nội bộ ngắn hạn")
    construction_receivables: Optional[float] = Field(None, alias="134", description="Phải thu theo tiến độ hợp đồng xây dựng")
    other_receivables_short_term: Optional[float] = Field(None, alias="135", description="Phải thu ngắn hạn khác")
    provision_doubtful_debts_short_term: Optional[float] = Field(None, alias="136", description="Dự phòng phải thu ngắn hạn khó đòi (*)", le=0)
    missing_assets_pending: Optional[float] = Field(None, alias="137", description="Tài sản thiếu chờ xử lý")
    
    # IV. Hàng tồn kho (Inventories) | 140
    inventories: Optional[float] = Field(None, alias="140", description="Hàng tồn kho")
    inventories_gross: Optional[float] = Field(None, alias="141", description="Hàng tồn kho (gross)")
    provision_inventory_write_down: Optional[float] = Field(None, alias="142", description="Dự phòng giảm giá hàng tồn kho (*)", le=0)
    
    # V. Tài sản sinh học ngắn hạn (Short-term biological assets) | 150
    short_term_biological_assets: Optional[float] = Field(None, alias="150", description="Tài sản sinh học ngắn hạn")
    livestock_one_cycle_short_term: Optional[float] = Field(None, alias="151", description="Súc vật nuôi lấy sản phẩm một lần ngắn hạn")
    crops_seasonal_short_term: Optional[float] = Field(None, alias="152", description="Cây trồng theo mùa vụ/lấy sản phẩm một lần ngắn hạn")
    provision_biological_assets_st: Optional[float] = Field(None, alias="153", description="Dự phòng tổn thất TSSH ngắn hạn (*)", le=0)
    
    # VI. Tài sản ngắn hạn khác (Other short-term assets) | 160
    other_short_term_assets: Optional[float] = Field(None, alias="160", description="Tài sản ngắn hạn khác")
    deferred_expenses_short_term: Optional[float] = Field(None, alias="161", description="Chi phí chờ phân bổ ngắn hạn")
    vat_deductible: Optional[float] = Field(None, alias="162", description="Thuế GTGT được khấu trừ")
    state_tax_receivables: Optional[float] = Field(None, alias="163", description="Thuế và các khoản khác phải thu Nhà nước")
    government_bond_repos_asset: Optional[float] = Field(None, alias="164", description="Giao dịch mua bán lại trái phiếu Chính phủ")
    other_st_assets_detail: Optional[float] = Field(None, alias="165", description="Tài sản ngắn hạn khác")
    
    # Tổng cộng Tài sản ngắn hạn (Total Short-term Assets)
    total_short_term_assets: Optional[float] = Field(None, alias="100", description="Tổng cộng tài sản ngắn hạn")
    
    # ──────────────────────────────────────────────────────────────────────────────
    # B - TÀI SẢN DÀI HẠN (LONG-TERM ASSETS) | Mã 200
    # ──────────────────────────────────────────────────────────────────────────────
    
    # I. Các khoản phải thu dài hạn (Long-term receivables) | 210
    long_term_receivables: Optional[float] = Field(None, alias="210", description="Các khoản phải thu dài hạn")
    trade_receivables_long_term: Optional[float] = Field(None, alias="211", description="Phải thu dài hạn của khách hàng")
    prepaid_to_suppliers_long_term: Optional[float] = Field(None, alias="212", description="Trả trước cho người bán dài hạn")
    capital_in_subsidiaries: Optional[float] = Field(None, alias="213", description="Vốn kinh doanh ở đơn vị trực thuộc")
    intra_group_receivables_long_term: Optional[float] = Field(None, alias="214", description="Phải thu nội bộ dài hạn")
    other_receivables_long_term: Optional[float] = Field(None, alias="215", description="Phải thu dài hạn khác")
    provision_doubtful_debts_long_term: Optional[float] = Field(None, alias="216", description="Dự phòng phải thu dài hạn khó đòi (*)", le=0)
    
    # II. Tài sản cố định (Fixed assets) | 220
    fixed_assets: Optional[float] = Field(None, alias="220", description="Tài sản cố định")
    tangible_fixed_assets_net: Optional[float] = Field(None, alias="221", description="Tài sản cố định hữu hình (net)")
    tangible_fa_gross: Optional[float] = Field(None, alias="222", description="Nguyên giá TSCĐ hữu hình")
    tangible_fa_accumulated_depreciation: Optional[float] = Field(None, alias="223", description="Giá trị hao mòn lũy kế (*)", le=0)
    finance_lease_assets_net: Optional[float] = Field(None, alias="224", description="Tài sản cố định thuê tài chính (net)")
    fla_gross: Optional[float] = Field(None, alias="225", description="Nguyên giá TSCĐ thuê tài chính")
    fla_accumulated_depreciation: Optional[float] = Field(None, alias="226", description="Giá trị hao mòn lũy kế (*)", le=0)
    intangible_fixed_assets_net: Optional[float] = Field(None, alias="227", description="Tài sản cố định vô hình (net)")
    intangible_fa_gross: Optional[float] = Field(None, alias="228", description="Nguyên giá TSCĐ vô hình")
    intangible_fa_accumulated_amortization: Optional[float] = Field(None, alias="229", description="Giá trị hao mòn lũy kế (*)", le=0)
    
    # III. Tài sản sinh học dài hạn (Long-term biological assets) | 230
    long_term_biological_assets: Optional[float] = Field(None, alias="230", description="Tài sản sinh học dài hạn")
    livestock_periodic_immature: Optional[float] = Field(None, alias="232", description="Súc vật nuôi chưa đến giai đoạn trưởng thành")
    livestock_periodic_mature_net: Optional[float] = Field(None, alias="233", description="Súc vật nuôi đến giai đoạn trưởng thành (net)")
    livestock_mature_gross: Optional[float] = Field(None, alias="234", description="Nguyên giá súc vật nuôi trưởng thành")
    livestock_mature_accumulated_depreciation: Optional[float] = Field(None, alias="235", description="Giá trị khấu hao lũy kế (*)", le=0)
    livestock_one_cycle_long_term: Optional[float] = Field(None, alias="236", description="Súc vật nuôi lấy sản phẩm một lần dài hạn")
    crops_long_term: Optional[float] = Field(None, alias="237", description="Cây trồng theo mùa vụ/lấy sản phẩm một lần dài hạn")
    provision_biological_assets_lt: Optional[float] = Field(None, alias="238", description="Dự phòng tổn thất TSSH dài hạn (*)", le=0)
    
    # IV. Bất động sản đầu tư (Investment property) | 240
    investment_property_net: Optional[float] = Field(None, alias="240", description="Bất động sản đầu tư (net)")
    investment_property_gross: Optional[float] = Field(None, alias="241", description="Nguyên giá BĐS đầu tư")
    investment_property_accumulated_depreciation: Optional[float] = Field(None, alias="242", description="Giá trị hao mòn lũy kế (*)", le=0)
    
    # V. Tài sản dở dang dài hạn (Long-term work-in-progress) | 250
    long_term_wip: Optional[float] = Field(None, alias="250", description="Tài sản dở dang dài hạn")
    production_costs_wip: Optional[float] = Field(None, alias="251", description="Chi phí SXKD dở dang dài hạn")
    capital_construction_wip: Optional[float] = Field(None, alias="252", description="Chi phí xây dựng cơ bản dở dang")
    
    # VI. Đầu tư tài chính dài hạn (Long-term financial investments) | 260
    long_term_financial_investments: Optional[float] = Field(None, alias="260", description="Đầu tư tài chính dài hạn")
    investment_in_subsidiaries: Optional[float] = Field(None, alias="261", description="Đầu tư vào công ty con")
    investment_in_jv_associates: Optional[float] = Field(None, alias="262", description="Đầu tư vào công ty liên doanh, liên kết")
    other_equity_investments: Optional[float] = Field(None, alias="263", description="Đầu tư góp vốn vào đơn vị khác")
    provision_other_equity_investments: Optional[float] = Field(None, alias="264", description="Dự phòng tổn thất đầu tư vào đơn vị khác (*)", le=0)
    htm_investments_long_term: Optional[float] = Field(None, alias="265", description="Đầu tư nắm giữ đến ngày đáo hạn dài hạn")
    provision_htm_lt: Optional[float] = Field(None, alias="266", description="Dự phòng ĐT nắm giữ đến ngày đáo hạn DT (*)", le=0)
    
    # VII. Tài sản dài hạn khác (Other long-term assets) | 270
    other_long_term_assets: Optional[float] = Field(None, alias="270", description="Tài sản dài hạn khác")
    deferred_expenses_long_term: Optional[float] = Field(None, alias="271", description="Chi phí chờ phân bổ dài hạn")
    deferred_tax_assets: Optional[float] = Field(None, alias="272", description="Tài sản thuế thu nhập hoãn lại")
    spare_parts_long_term: Optional[float] = Field(None, alias="273", description="Thiết bị, vật tư, phụ tùng thay thế dài hạn")
    other_lt_assets_detail: Optional[float] = Field(None, alias="274", description="Tài sản dài hạn khác")
    
    # Tổng cộng Tài sản dài hạn (Total Long-term Assets)
    total_long_term_assets: Optional[float] = Field(None, alias="200", description="Tổng cộng tài sản dài hạn")
    
    # ──────────────────────────────────────────────────────────────────────────────
    # TỔNG CỘNG TÀI SẢN (TOTAL ASSETS) | Mã 280 = 100 + 200
    # ──────────────────────────────────────────────────────────────────────────────
    total_assets: Optional[float] = Field(None, alias="280", description="Tổng cộng tài sản")
    
    # ──────────────────────────────────────────────────────────────────────────────
    # C - NỢ PHẢI TRẢ (LIABILITIES) | Mã 300
    # ──────────────────────────────────────────────────────────────────────────────
    
    # I. Nợ ngắn hạn (Short-term liabilities) | 310
    short_term_liabilities: Optional[float] = Field(None, alias="310", description="Nợ ngắn hạn")
    trade_payables_short_term: Optional[float] = Field(None, alias="311", description="Phải trả người bán ngắn hạn")
    customer_advances_short_term: Optional[float] = Field(None, alias="312", description="Người mua trả tiền trước ngắn hạn")
    dividends_payable: Optional[float] = Field(None, alias="313", description="Phải trả cổ tức, lợi nhuận")
    taxes_payable_short_term: Optional[float] = Field(None, alias="314", description="Thuế và các khoản phải nộp Nhà nước ngắn hạn")
    salaries_payable: Optional[float] = Field(None, alias="315", description="Phải trả người lao động")
    accrued_expenses_short_term: Optional[float] = Field(None, alias="316", description="Chi phí phải trả ngắn hạn")
    intra_group_payables_short_term: Optional[float] = Field(None, alias="317", description="Phải trả nội bộ ngắn hạn")
    construction_payables_short_term: Optional[float] = Field(None, alias="318", description="Phải trả theo tiến độ hợp đồng xây dựng ngắn hạn")
    deferred_revenue_short_term: Optional[float] = Field(None, alias="319", description="Doanh thu chờ phân bổ ngắn hạn")
    other_payables_short_term: Optional[float] = Field(None, alias="320", description="Phải trả ngắn hạn khác")
    short_term_borrowings: Optional[float] = Field(None, alias="321", description="Vay và nợ thuê tài chính ngắn hạn")
    provisions_short_term: Optional[float] = Field(None, alias="322", description="Dự phòng phải trả ngắn hạn")
    reward_welfare_fund: Optional[float] = Field(None, alias="323", description="Quỹ khen thưởng, phúc lợi")
    price_stabilisation_fund: Optional[float] = Field(None, alias="324", description="Quỹ bình ổn giá")
    government_bond_repos_liability: Optional[float] = Field(None, alias="325", description="Giao dịch mua bán lại trái phiếu Chính phủ")
    
    # II. Nợ dài hạn (Long-term liabilities) | 330
    long_term_liabilities: Optional[float] = Field(None, alias="330", description="Nợ dài hạn")
    trade_payables_long_term: Optional[float] = Field(None, alias="331", description="Phải trả người bán dài hạn")
    customer_advances_long_term: Optional[float] = Field(None, alias="332", description="Người mua trả tiền trước dài hạn")
    taxes_payable_long_term: Optional[float] = Field(None, alias="333", description="Thuế và các khoản phải nộp Nhà nước dài hạn")
    accrued_expenses_long_term: Optional[float] = Field(None, alias="334", description="Chi phí phải trả dài hạn")
    intra_group_business_capital: Optional[float] = Field(None, alias="335", description="Phải trả nội bộ về vốn kinh doanh")
    intra_group_payables_long_term: Optional[float] = Field(None, alias="336", description="Phải trả nội bộ dài hạn")
    deferred_revenue_long_term: Optional[float] = Field(None, alias="337", description="Doanh thu chờ phân bổ dài hạn")
    other_payables_long_term: Optional[float] = Field(None, alias="338", description="Phải trả dài hạn khác")
    long_term_borrowings: Optional[float] = Field(None, alias="339", description="Vay và nợ thuê tài chính dài hạn")
    convertible_bonds: Optional[float] = Field(None, alias="340", description="Trái phiếu chuyển đổi")
    preference_shares_liability: Optional[float] = Field(None, alias="341", description="Cổ phiếu ưu đãi (liability component)")
    deferred_tax_liabilities: Optional[float] = Field(None, alias="342", description="Thuế thu nhập hoãn lại phải trả")
    provisions_long_term: Optional[float] = Field(None, alias="343", description="Dự phòng phải trả dài hạn")
    rd_fund: Optional[float] = Field(None, alias="344", description="Quỹ phát triển khoa học và công nghệ")
    
    # Tổng cộng Nợ phải trả (Total Liabilities)
    total_liabilities: Optional[float] = Field(None, alias="300", description="Tổng cộng nợ phải trả")
    
    # ──────────────────────────────────────────────────────────────────────────────
    # D - VỐN CHỦ SỞ HỮU (OWNERS' EQUITY) | Mã 400
    # ──────────────────────────────────────────────────────────────────────────────
    
    # Owners' Equity components
    owners_equity: Optional[float] = Field(None, alias="400", description="Vốn chủ sở hữu")
    contributed_charter_capital: Optional[float] = Field(None, alias="411", description="Vốn góp của chủ sở hữu")
    ordinary_shares: Optional[float] = Field(None, alias="411a", description="Cổ phiếu phổ thông có quyền biểu quyết")
    preference_shares_equity: Optional[float] = Field(None, alias="411b", description="Cổ phiếu ưu đãi (equity component)")
    share_premium: Optional[float] = Field(None, alias="412", description="Thặng dư vốn cổ phần")
    bond_conversion_option: Optional[float] = Field(None, alias="413", description="Quyền chọn chuyển đổi trái phiếu")
    other_owner_capital: Optional[float] = Field(None, alias="414", description="Vốn khác của chủ sở hữu")
    treasury_shares: Optional[float] = Field(None, alias="415", description="Cổ phiếu mua lại của chính mình (*)", le=0)
    asset_revaluation_surplus: Optional[float] = Field(None, alias="416", description="Chênh lệch đánh giá lại tài sản")
    fx_translation_reserve: Optional[float] = Field(None, alias="417", description="Chênh lệch tỷ giá hối đoái")
    development_investment_fund: Optional[float] = Field(None, alias="418", description="Quỹ đầu tư phát triển")
    other_equity_reserves: Optional[float] = Field(None, alias="419", description="Quỹ khác thuộc vốn chủ sở hữu")
    retained_earnings: Optional[float] = Field(None, alias="420", description="Lợi nhuận sau thuế chưa phân phối")
    retained_earnings_prior_periods: Optional[float] = Field(None, alias="420a", description="LNST chưa phân phối lũy kế đến cuối kỳ trước")
    retained_earnings_current_period: Optional[float] = Field(None, alias="420b", description="LNST chưa phân phối kỳ này")
    
    # Tổng cộng Nguồn vốn (Total Funding/Equity) | Mã 440 = 300 + 400
    total_equity: Optional[float] = Field(None, alias="440", description="Tổng cộng nguồn vốn")
    non_controlling_interest: Optional[float] = Field(None, description="Lợi ích cổ đông không kiểm soát")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "reporting_entity": "Công ty Cổ phần Sữa Việt Nam (VNM)",
                "address": "10 Tân Trào, Quận 7, TP.HCM",
                "currency_unit": "tỷ VND",
                "reporting_date": "2023-12-31",
                "cash_and_equivalents": 8.5,
                "inventories": 6.8,
                "tangible_fixed_assets_net": 20.1,
                "total_assets": 50.5,
                "short_term_borrowings": 5.2,
                "long_term_borrowings": 8.3,
                "total_liabilities": 18.2,
                "contributed_charter_capital": 10.0,
                "retained_earnings": 20.5,
                "total_equity": 32.3
            }
        }


class VNIncomeStatement_B02_DN(BaseModel):
    """
    Mẫu số B 02 - DN: Báo cáo Kết quả Hoạt động Kinh doanh (Income Statement)
    Theo Thông Tư 99/2025/TT-BTC
    
    Waterfall structure from revenue to net profit, then per-share data.
    Key formulas embedded in Mã số (line codes).
    
    Currency unit: Typically in billion VND (tỷ đồng) or million VND (triệu đồng)
    """
    
    # Reporting metadata
    reporting_entity: str = Field(..., description="Đơn vị báo cáo - Reporting entity name")
    address: Optional[str] = Field(None, description="Địa chỉ - Address")
    currency_unit: str = Field("tỷ VND", description="Đơn vị tính - Currency unit")
    period_from: Optional[date] = Field(None, description="From date")
    period_to: Optional[date] = Field(None, description="To date")
    
    # ──────────────────────────────────────────────────────────────────────────────
    # LINE ITEMS
    # ──────────────────────────────────────────────────────────────────────────────
    
    # 1. Doanh thu bán hàng và cung cấp dịch vụ | 01
    gross_revenue: Optional[float] = Field(None, alias="01", description="Doanh thu bán hàng và cung cấp dịch vụ")
    
    # 2. Các khoản giảm trừ doanh thu | 02
    revenue_deductions: Optional[float] = Field(None, alias="02", description="Các khoản giảm trừ doanh thu")
    sales_returns: Optional[float] = Field(None, description="Giảm giá hàng bán")
    trade_discounts: Optional[float] = Field(None, description="Chiết khấu thương mại")
    special_tax: Optional[float] = Field(None, description="Thuế tiêu thụ đặc biệt")
    
    # 3. Doanh thu thuần về bán hàng và cung cấp dịch vụ | 10
    # Formula: Mã 10 = 01 − 02
    net_revenue: Optional[float] = Field(None, alias="10", description="Doanh thu thuần về bán hàng và cung cấp dịch vụ")
    
    # 4. Giá vốn hàng bán | 11
    cost_of_goods_sold: Optional[float] = Field(None, alias="11", description="Giá vốn hàng bán")
    
    # 5. Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | 20
    # Formula: Mã 20 = 10 − 11
    gross_profit: Optional[float] = Field(None, alias="20", description="Lợi nhuận gộp về bán hàng và cung cấp dịch vụ")
    
    # 6. Lãi/lỗ của hoạt động bán, thanh lý bất động sản đầu tư | 21 (NEW in TT99)
    investment_property_gain_loss: Optional[float] = Field(None, alias="21", description="Lãi/lỗ của hoạt động bán, thanh lý BĐS đầu tư")
    
    # 7. Doanh thu hoạt động tài chính | 22
    financial_income: Optional[float] = Field(None, alias="22", description="Doanh thu hoạt động tài chính")
    interest_income: Optional[float] = Field(None, description="Thu từ lãi cho vay")
    dividend_income: Optional[float] = Field(None, description="Thu từ cổ tức, lợi nhuận được chia")
    fx_gain: Optional[float] = Field(None, description="Lãi tỷ giá hối đoái")
    
    # 8. Chi phí tài chính | 23
    financial_expenses: Optional[float] = Field(None, alias="23", description="Chi phí tài chính")
    # Trong đó: Chi phí đi vay | 24
    borrowing_costs: Optional[float] = Field(None, alias="24", description="Trong đó: Chi phí đi vay")
    interest_expense: Optional[float] = Field(None, description="Chi phí lãi vay")
    fx_loss: Optional[float] = Field(None, description="Lỗ tỷ giá hối đoái")
    
    # 9. Chi phí bán hàng | 25
    selling_expenses: Optional[float] = Field(None, alias="25", description="Chi phí bán hàng")
    
    # 10. Chi phí quản lý doanh nghiệp | 26
    general_administrative_expenses: Optional[float] = Field(None, alias="26", description="Chi phí quản lý doanh nghiệp")
    
    # 11. Lợi nhuận thuần từ hoạt động kinh doanh | 30
    # Formula: Mã 30 = 20 + 21 + 22 − (23 + 25 + 26)
    operating_profit: Optional[float] = Field(None, alias="30", description="Lợi nhuận thuần từ hoạt động kinh doanh")
    
    # 12. Thu nhập khác | 31
    other_income: Optional[float] = Field(None, alias="31", description="Thu nhập khác")
    gain_on_asset_disposal: Optional[float] = Field(None, description="Thu từ thanh lý, nhượng bán TSCĐ")
    fines_received: Optional[float] = Field(None, description="Tiền phạt vi phạm hợp đồng")
    
    # 13. Chi phí khác | 32
    other_expenses: Optional[float] = Field(None, alias="32", description="Chi phí khác")
    loss_on_asset_disposal: Optional[float] = Field(None, description="Chi phí thanh lý, nhượng bán TSCĐ")
    fines_paid: Optional[float] = Field(None, description="Tiền phạt vi phạm hợp đồng")
    
    # 14. Lợi nhuận khác | 40
    # Formula: Mã 40 = 31 − 32
    other_profit_loss: Optional[float] = Field(None, alias="40", description="Lợi nhuận khác")
    
    # 15. Tổng lợi nhuận kế toán trước thuế | 50
    # Formula: Mã 50 = 30 + 40
    profit_before_tax: Optional[float] = Field(None, alias="50", description="Tổng lợi nhuận kế toán trước thuế")
    
    # 16. Chi phí thuế TNDN hiện hành | 51
    current_cit_expense: Optional[float] = Field(None, alias="51", description="Chi phí thuế TNDN hiện hành")
    
    # 17. Chi phí thuế TNDN hoãn lại | 52
    deferred_cit_expense: Optional[float] = Field(None, alias="52", description="Chi phí thuế TNDN hoãn lại")
    
    # 18. Lợi nhuận sau thuế thu nhập doanh nghiệp | 60
    # Formula: Mã 60 = 50 − 51 − 52
    net_profit: Optional[float] = Field(None, alias="60", description="Lợi nhuận sau thuế thu nhập doanh nghiệp")
    
    # 19. Lãi cơ bản trên cổ phiếu (*) | 70 (joint-stock companies only)
    basic_eps: Optional[float] = Field(None, alias="70", description="Lãi cơ bản trên cổ phiếu")
    
    # 20. Lãi suy giảm trên cổ phiếu (*) | 71 (joint-stock companies only)
    diluted_eps: Optional[float] = Field(None, alias="71", description="Lãi suy giảm trên cổ phiếu")
    
    # Additional calculated metrics
    ebitda: Optional[float] = Field(None, description="EBITDA (lợi nhuận trước thuế, lãi vay, khấu hao)")
    operating_margin: Optional[float] = Field(None, description="Biên lợi nhuận thuần (%)")
    net_margin: Optional[float] = Field(None, description="Biên lợi nhuận ròng (%)")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "reporting_entity": "Công ty Cổ phần Sữa Việt Nam (VNM)",
                "address": "10 Tân Trào, Quận 7, TP.HCM",
                "currency_unit": "tỷ VND",
                "period_from": "2023-01-01",
                "period_to": "2023-12-31",
                "gross_revenue": 87.5,
                "revenue_deductions": 2.0,
                "net_revenue": 85.5,
                "cost_of_goods_sold": 52.3,
                "gross_profit": 33.2,
                "financial_income": 1.2,
                "financial_expenses": 0.8,
                "selling_expenses": 12.5,
                "general_administrative_expenses": 5.3,
                "operating_profit": 15.8,
                "other_income": 0.5,
                "other_expenses": 0.3,
                "profit_before_tax": 16.0,
                "current_cit_expense": 3.2,
                "deferred_cit_expense": 0.1,
                "net_profit": 12.7,
                "basic_eps": 12500,
                "diluted_eps": 12450
            }
        }


class VNFinancialInputs_TT99(BaseModel):
    """
    Complete Vietnamese Financial Inputs Package (Thông Tư 99/2025/TT-BTC)
    Used for Vietnamese market valuation models
    Currency: VND (typically in billions - tỷ đồng)
    """
    
    company_name: str = Field(..., description="Tên công ty - Company name")
    ticker: str = Field(..., description="Mã chứng khoán - Stock ticker (e.g., VNM.VN)")
    currency: str = Field("VND", description="Reporting currency (always VND for Vietnamese market)")
    fiscal_year_end: Optional[date] = Field(None, description="Ngày kết thúc năm tài chính")
    reporting_period: Optional[str] = Field(None, description="Kỳ báo cáo (e.g., 'FY2023', 'Q1 2024')")
    
    balance_sheet: Optional[VNBalanceSheet_B01_DN] = Field(None, description="Báo cáo tình hình tài chính (B01-DN)")
    income_statement: Optional[VNIncomeStatement_B02_DN] = Field(None, description="Báo cáo kết quả HĐKD (B02-DN)")
    
    # Market Data (Vietnamese market specific)
    market_cap_vnd: Optional[float] = Field(None, description="Vốn hóa thị trường (tỷ VND)")
    shares_outstanding: Optional[float] = Field(None, description="Số lượng cổ phiếu đang lưu hành")
    current_stock_price_vnd: Optional[float] = Field(None, description="Giá cổ phiếu hiện tại (VND)")
    exchange: Optional[str] = Field(None, description="Sở giao dịch (HOSE/HNX)")
    
    # Metadata
    data_source: Optional[str] = Field(None, description="Nguồn dữ liệu (e.g., HOSE, Cafef, Vietstock)")
    last_updated: Optional[date] = Field(None, description="Ngày cập nhật cuối cùng")
    accounting_standard: str = Field("VAS_TT99", description="Chuẩn kế toán (VAS theo TT99/2025/TT-BTC)")
    auditor: Optional[str] = Field(None, description="Đơn vị kiểm toán")
    audit_opinion: Optional[str] = Field(None, description="Ý kiến kiểm toán")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Công ty Cổ phần Sữa Việt Nam",
                "ticker": "VNM.VN",
                "currency": "VND",
                "fiscal_year_end": "2023-12-31",
                "reporting_period": "FY2023",
                "accounting_standard": "VAS_TT99",
                "exchange": "HOSE",
                "market_cap_vnd": 250.5,
                "shares_outstanding": 1000000000,
                "current_stock_price_vnd": 75000,
                "balance_sheet": {
                    "reporting_entity": "Công ty Cổ phần Sữa Việt Nam",
                    "currency_unit": "tỷ VND",
                    "reporting_date": "2023-12-31",
                    "cash_and_equivalents": 8.5,
                    "inventories": 6.8,
                    "tangible_fixed_assets_net": 20.1,
                    "total_assets": 50.5,
                    "total_liabilities": 18.2,
                    "total_equity": 32.3
                },
                "income_statement": {
                    "reporting_entity": "Công ty Cổ phần Sữa Việt Nam",
                    "currency_unit": "tỷ VND",
                    "period_from": "2023-01-01",
                    "period_to": "2023-12-31",
                    "net_revenue": 85.5,
                    "gross_profit": 33.2,
                    "operating_profit": 15.8,
                    "net_profit": 12.7,
                    "basic_eps": 12500
                }
            }
        }


# Helper functions for calculations per TT99 formulas
class TT99_Calculations:
    """
    Helper class implementing calculation formulas from Thông Tư 99/2025/TT-BTC
    """
    
    @staticmethod
    def calculate_net_revenue(gross_revenue: float, revenue_deductions: float) -> float:
        """Mã 10 = 01 − 02"""
        return gross_revenue - revenue_deductions
    
    @staticmethod
    def calculate_gross_profit(net_revenue: float, cogs: float) -> float:
        """Mã 20 = 10 − 11"""
        return net_revenue - cogs
    
    @staticmethod
    def calculate_operating_profit(
        gross_profit: float,
        investment_property_gl: float,
        financial_income: float,
        financial_expenses: float,
        selling_expenses: float,
        admin_expenses: float
    ) -> float:
        """Mã 30 = 20 + 21 + 22 − (23 + 25 + 26)"""
        return gross_profit + investment_property_gl + financial_income - (
            financial_expenses + selling_expenses + admin_expenses
        )
    
    @staticmethod
    def calculate_other_profit(other_income: float, other_expenses: float) -> float:
        """Mã 40 = 31 − 32"""
        return other_income - other_expenses
    
    @staticmethod
    def calculate_profit_before_tax(operating_profit: float, other_profit: float) -> float:
        """Mã 50 = 30 + 40"""
        return operating_profit + other_profit
    
    @staticmethod
    def calculate_net_profit(
        profit_before_tax: float,
        current_tax: float,
        deferred_tax: float
    ) -> float:
        """Mã 60 = 50 − 51 − 52"""
        return profit_before_tax - current_tax - deferred_tax
    
    @staticmethod
    def validate_balance_sheet(total_assets: float, total_liabilities: float, 
                               total_equity: float) -> bool:
        """
        Validate balancing equation: Mã 280 = Mã 440
        Total Assets = Total Liabilities + Total Equity
        """
        total_funding = total_liabilities + total_equity
        return abs(total_assets - total_funding) < 0.01  # Allow small rounding differences
    
    @staticmethod
    def calculate_basic_eps(net_profit: float, weighted_avg_shares: float) -> float:
        """Calculate basic earnings per share (Mã 70)"""
        if weighted_avg_shares == 0:
            return 0.0
        return net_profit / weighted_avg_shares
    
    @staticmethod
    def calculate_ebitda(
        operating_profit: float,
        depreciation: float,
        amortization: float
    ) -> float:
        """Calculate EBITDA"""
        return operating_profit + depreciation + amortization
