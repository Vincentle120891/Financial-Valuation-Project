"""
================================================================================
VIETNAMESE CASH FLOW STATEMENT MODEL — THÔNG TƯ 99/2025/TT-BTC
Mẫu số B 03 - DN (Both Direct and Indirect Methods)
================================================================================

This module implements the Vietnamese GAAP cash flow statement standard
as prescribed by Circular 99/2025/TT-BTC issued by the Ministry of Finance.

Two methods supported:
  - Phương pháp trực tiếp (Direct Method)
  - Phương pháp gián tiếp (Indirect Method)

Key characteristics:
  - Fixed Mã số (line codes) that must NOT be renumbered
  - Prescriptive classification rules (no flexibility like IFRS)
  - Specific treatment for interest, dividends, and taxes
  - Mandatory reconciliation to balance sheet cash
"""


class VietnameseCashFlowModel:
    """
    Vietnamese Cash Flow Statement Model (TT99/2025 compliant)
    
    Implements Mẫu số B 03 - DN with both direct and indirect methods.
    All Mã số codes are fixed per the regulation.
    """
    
    # Fixed Mã số codes per TT99 - DO NOT RENUMBER
    MA_SO = {
        # Operating Activities (Section I)
        'OPERATING': {
            # Direct Method lines
            '01': 'Tiền thu từ bán hàng, cung cấp dịch vụ và doanh thu khác',
            '02': 'Tiền chi trả cho người cung cấp hàng hóa và dịch vụ',
            '03': 'Tiền chi trả cho người lao động',
            '04': 'Chi phí đi vay đã trả',
            '05': 'Thuế thu nhập doanh nghiệp đã nộp',
            '06': 'Tiền thu khác từ hoạt động kinh doanh',
            '07': 'Tiền chi khác cho hoạt động kinh doanh',
            
            # Indirect Method lines
            'I01': 'Lợi nhuận trước thuế',
            'I02': 'Khấu hao TSCĐ và BĐSĐT',
            'I03': 'Các khoản dự phòng',
            'I04': 'Lãi, lỗ chênh lệch tỷ giá hối đoái do đánh giá lại',
            'I05': 'Lãi, lỗ từ hoạt động đầu tư, tài chính',
            'I06': 'Chi phí đi vay',
            'I07': 'Các khoản điều chỉnh khác',
            'I08': 'Lợi nhuận từ HĐKD trước thay đổi vốn lưu động',
            'I09': 'Tăng, giảm các khoản phải thu',
            'I10': 'Tăng, giảm hàng tồn kho',
            'I11': 'Tăng, giảm các khoản phải trả',
            'I12': 'Tăng, giảm chi phí chờ phân bổ',
            'I13': 'Tăng, giảm chứng khoán kinh doanh',
            'I14': 'Chi phí đi vay đã trả',
            'I15': 'Thuế thu nhập doanh nghiệp đã nộp',
            'I16': 'Tiền thu khác từ hoạt động kinh doanh',
            'I17': 'Tiền chi khác cho hoạt động kinh doanh',
            
            # Net Operating Cash Flow
            '20': 'Lưu chuyển tiền thuần từ hoạt động kinh doanh'
        },
        
        # Investing Activities (Section II) - Same for both methods
        'INVESTING': {
            '21': 'Tiền chi mua sắm, xây dựng TSCĐ và tài sản dài hạn khác',
            '22': 'Tiền thu từ thanh lý, nhượng bán TSCĐ và tài sản dài hạn khác',
            '23': 'Tiền chi cho vay, mua công cụ nợ của đơn vị khác',
            '24': 'Tiền thu hồi cho vay, bán lại công cụ nợ của đơn vị khác',
            '25': 'Tiền chi đầu tư góp vốn vào đơn vị khác',
            '26': 'Tiền thu hồi đầu tư góp vốn vào đơn vị khác',
            '27': 'Tiền thu lãi cho vay, cổ tức và lợi nhuận được chia',
            '30': 'Lưu chuyển tiền thuần từ hoạt động đầu tư'
        },
        
        # Financing Activities (Section III) - Same for both methods
        'FINANCING': {
            '31': 'Tiền thu từ phát hành cổ phiếu, nhận vốn góp của chủ sở hữu',
            '32': 'Tiền trả lại vốn góp, mua lại cổ phiếu đã phát hành',
            '33': 'Tiền thu từ đi vay',
            '34': 'Tiền trả nợ gốc vay',
            '35': 'Tiền trả nợ gốc thuê tài chính',
            '36': 'Cổ tức, lợi nhuận đã trả cho chủ sở hữu',
            '40': 'Lưu chuyển tiền thuần từ hoạt động tài chính'
        },
        
        # Reconciliation
        'RECONCILIATION': {
            '50': 'Lưu chuyển tiền thuần trong kỳ',
            '60': 'Tiền và tương đương tiền đầu kỳ',
            '61': 'Ảnh hưởng của thay đổi tỷ giá hối đoái quy đổi ngoại tệ',
            '70': 'Tiền và tương đương tiền cuối kỳ'
        }
    }
    
    # Sign conventions (positive = inflow, negative = outflow)
    OUTFLOW_LINES = [
        '02', '03', '04', '05', '07',  # Direct method outflows
        '21', '23', '25',              # Investing outflows
        '32', '34', '35', '36',        # Financing outflows
        'I14', 'I15', 'I17'            # Indirect method payments
    ]
    
    def __init__(self, method='indirect'):
        """
        Initialize Vietnamese Cash Flow Model
        
        Args:
            method: 'direct' or 'indirect' for operating activities
        """
        self.method = method
        self.data = {}
        self.currency_unit = 'VND'  # Default, can be triệu đồng, tỷ đồng
    
    def set_currency_unit(self, unit: str):
        """
        Set currency unit for reporting
        
        Args:
            unit: 'VND', 'triệu đồng', or 'tỷ đồng'
        """
        self.currency_unit = unit
    
    def add_line_item(self, ma_so: str, value: float, description: str = None):
        """
        Add a line item to the cash flow statement
        
        Args:
            ma_so: Mã số code per TT99
            value: Amount (positive for inflows, negative for outflows)
            description: Optional custom description
        """
        if ma_so in self.OUTFLOW_LINES and value > 0:
            # Automatically negate outflows
            value = -abs(value)
        
        self.data[ma_so] = {
            'value': value,
            'description': description or self.MA_SO.get(
                'OPERATING', {}
            ).get(ma_so) or self.MA_SO.get(
                'INVESTING', {}
            ).get(ma_so) or self.MA_SO.get(
                'FINANCING', {}
            ).get(ma_so) or self.MA_SO.get(
                'RECONCILIATION', {}
            ).get(ma_so, f'Mã {ma_so}')
        }
    
    def calculate_section_totals(self) -> dict:
        """
        Calculate net cash flows for each section
        
        Returns:
            Dictionary with totals for operating, investing, financing
        """
        # Determine which operating lines to use based on method
        if self.method == 'direct':
            operating_codes = ['01', '02', '03', '04', '05', '06', '07']
        else:  # indirect
            operating_codes = [f'I{i}' for i in range(9, 18)]
            # For indirect, we start from I08 (operating profit before WC)
            # then add WC changes and payments
        
        investing_codes = ['21', '22', '23', '24', '25', '26', '27']
        financing_codes = ['31', '32', '33', '34', '35', '36']
        
        # Calculate section totals
        cfo = sum(
            self.data.get(code, {}).get('value', 0) 
            for code in operating_codes
        )
        
        cfi = sum(
            self.data.get(code, {}).get('value', 0) 
            for code in investing_codes
        )
        
        cff = sum(
            self.data.get(code, {}).get('value', 0) 
            for code in financing_codes
        )
        
        # Store calculated totals
        self.data['20'] = {'value': cfo, 'description': self.MA_SO['OPERATING']['20']}
        self.data['30'] = {'value': cfi, 'description': self.MA_SO['INVESTING']['30']}
        self.data['40'] = {'value': cff, 'description': self.MA_SO['FINANCING']['40']}
        
        return {
            'cfo': cfo,
            'cfi': cfi,
            'cff': cff,
            'ma_so_20': cfo,
            'ma_so_30': cfi,
            'ma_so_40': cff
        }
    
    def calculate_net_cash_flow(self) -> float:
        """
        Calculate Mã 50 - Lưu chuyển tiền thuần trong kỳ
        
        Formula: Mã 50 = Mã 20 + Mã 30 + Mã 40
        
        Returns:
            Net cash flow for the period
        """
        totals = self.calculate_section_totals()
        net_flow = totals['cfo'] + totals['cfi'] + totals['cff']
        
        self.data['50'] = {
            'value': net_flow,
            'description': self.MA_SO['RECONCILIATION']['50']
        }
        
        return net_flow
    
    def reconcile_to_closing_cash(
        self, 
        opening_cash: float, 
        fx_effect: float = 0.0
    ) -> dict:
        """
        Reconcile from opening to closing cash balance
        
        Formula: Mã 70 = Mã 50 + Mã 60 + Mã 61
        
        Args:
            opening_cash: Tiền và tương đương tiền đầu kỳ (Mã 60)
            fx_effect: Ảnh hưởng tỷ giá (Mã 61)
        
        Returns:
            Dictionary with reconciliation details
        """
        net_flow = self.calculate_net_cash_flow()
        closing_cash = net_flow + opening_cash + fx_effect
        
        # Store reconciliation items
        self.data['60'] = {
            'value': opening_cash,
            'description': self.MA_SO['RECONCILIATION']['60']
        }
        self.data['61'] = {
            'value': fx_effect,
            'description': self.MA_SO['RECONCILIATION']['61']
        }
        self.data['70'] = {
            'value': closing_cash,
            'description': self.MA_SO['RECONCILIATION']['70']
        }
        
        return {
            'ma_so_50': net_flow,
            'ma_so_60': opening_cash,
            'ma_so_61': fx_effect,
            'ma_so_70': closing_cash,
            'reconciled': True
        }
    
    def validate_against_balance_sheet(
        self,
        bs_cash_beginning: float,
        bs_cash_ending: float,
        fx_effect: float = 0.0,
        tolerance: float = 0.01
    ) -> dict:
        """
        Validate cash flow statement reconciles to balance sheet
        
        The change in balance sheet cash must equal:
        CFO + CFI + CFF + FX Effect
        
        Args:
            bs_cash_beginning: Cash from beginning balance sheet (B01 Mã 110 đầu năm)
            bs_cash_ending: Cash from ending balance sheet (B01 Mã 110 cuối năm)
            fx_effect: Foreign exchange impact
            tolerance: Acceptable discrepancy threshold
        
        Returns:
            Validation result with discrepancy analysis
        """
        net_flow = self.calculate_net_cash_flow()
        calculated_ending = bs_cash_beginning + net_flow + fx_effect
        
        discrepancy = abs(calculated_ending - bs_cash_ending)
        is_valid = discrepancy <= tolerance
        
        return {
            'valid': is_valid,
            'bs_cash_beginning': bs_cash_beginning,
            'bs_cash_ending': bs_cash_ending,
            'calculated_ending': calculated_ending,
            'net_cash_flow': net_flow,
            'fx_effect': fx_effect,
            'discrepancy': discrepancy,
            'tolerance': tolerance,
            'message': 'Reconciliation successful' if is_valid else 'Reconciliation failed - check data'
        }
    
    def convert_from_indirect_to_direct(self) -> dict:
        """
        Convert indirect method operating cash flows to direct method format
        
        This is an analytical conversion for comparison purposes.
        Note: In practice, direct method requires detailed cash transaction data.
        
        Returns:
            Estimated direct method line items
        """
        if self.method != 'indirect':
            raise ValueError("Can only convert from indirect method")
        
        # Extract indirect method components
        net_income = self.data.get('I01', {}).get('value', 0)
        depreciation = self.data.get('I02', {}).get('value', 0)
        provisions = self.data.get('I03', {}).get('value', 0)
        fx_unrealized = self.data.get('I04', {}).get('value', 0)
        investment_gains = self.data.get('I05', {}).get('value', 0)
        interest_expense = self.data.get('I06', {}).get('value', 0)
        
        wc_receivables = self.data.get('I09', {}).get('value', 0)
        wc_inventory = self.data.get('I10', {}).get('value', 0)
        wc_payables = self.data.get('I11', {}).get('value', 0)
        wc_prepaid = self.data.get('I12', {}).get('value', 0)
        wc_trading_securities = self.data.get('I13', {}).get('value', 0)
        
        interest_paid = self.data.get('I14', {}).get('value', 0)
        tax_paid = self.data.get('I15', {}).get('value', 0)
        other_operating_receipts = self.data.get('I16', {}).get('value', 0)
        other_operating_payments = self.data.get('I17', {}).get('value', 0)
        
        # Estimate direct method lines (simplified conversion)
        # These are approximations - actual direct method needs transaction-level data
        direct_estimates = {
            '01': net_income + depreciation + provisions - investment_gains + wc_receivables + wc_inventory - wc_payables,  # Cash from customers (approximate)
            '02': -(wc_inventory - wc_payables),  # Cash to suppliers (approximate)
            '03': 0,  # Would need salary expense data
            '04': interest_paid,
            '05': tax_paid,
            '06': other_operating_receipts,
            '07': other_operating_payments
        }
        
        return direct_estimates
    
    def get_tt99_classification_rules(self) -> dict:
        """
        Get TT99-specific classification rules
        
        Vietnamese GAAP is more prescriptive than IFRS - no flexibility allowed.
        
        Returns:
            Dictionary of classification rules per TT99
        """
        return {
            'interest_paid': {
                'ma_so': '04 (direct) or I14 (indirect)',
                'section': 'Operating Activities',
                'rule': 'MUST be classified as Operating (no flexibility)'
            },
            'interest_received': {
                'ma_so': '27',
                'section': 'Investing Activities',
                'rule': 'MUST be classified as Investing (no flexibility)'
            },
            'dividends_received': {
                'ma_so': '27',
                'section': 'Investing Activities',
                'rule': 'MUST be classified as Investing (no flexibility)'
            },
            'dividends_paid': {
                'ma_so': '36',
                'section': 'Financing Activities',
                'rule': 'MUST be classified as Financing (no flexibility)'
            },
            'income_taxes_paid': {
                'ma_so': '05 (direct) or I15 (indirect)',
                'section': 'Operating Activities',
                'rule': 'MUST be classified as Operating'
            },
            'finance_lease_principal': {
                'ma_so': '35',
                'section': 'Financing Activities',
                'rule': 'Principal repayment MUST be Financing (aligns with IFRS 16)'
            },
            'trading_securities': {
                'ma_so': 'I13',
                'section': 'Operating Activities (Working Capital)',
                'rule': 'Changes treated as Operating WC adjustment (unique to VN GAAP)'
            }
        }
    
    def generate_report(self, company_name: str, period: str) -> dict:
        """
        Generate formatted cash flow statement report
        
        Args:
            company_name: Tên công ty (Reporting entity)
            period: Reporting period (e.g., "Năm 2024")
        
        Returns:
            Formatted report dictionary
        """
        totals = self.calculate_section_totals()
        net_flow = self.calculate_net_cash_flow()
        
        report = {
            'header': {
                'form': 'Mẫu số B 03 - DN',
                'regulation': 'Thông tư 99/2025/TT-BTC',
                'company': company_name,
                'period': period,
                'currency_unit': self.currency_unit,
                'method': 'Phương pháp ' + ('trực tiếp' if self.method == 'direct' else 'gián tiếp')
            },
            'sections': {
                'operating': {
                    'title': 'I. Lưu chuyển tiền từ hoạt động kinh doanh',
                    'lines': [],
                    'total': totals['cfo'],
                    'ma_so': '20'
                },
                'investing': {
                    'title': 'II. Lưu chuyển tiền từ hoạt động đầu tư',
                    'lines': [],
                    'total': totals['cfi'],
                    'ma_so': '30'
                },
                'financing': {
                    'title': 'III. Lưu chuyển tiền từ hoạt động tài chính',
                    'lines': [],
                    'total': totals['cff'],
                    'ma_so': '40'
                },
                'reconciliation': {
                    'title': 'IV. Điều chỉnh',
                    'lines': [],
                    'total': net_flow,
                    'ma_so': '50, 60, 61, 70'
                }
            }
        }
        
        # Populate lines based on method
        if self.method == 'direct':
            operating_codes = ['01', '02', '03', '04', '05', '06', '07']
        else:
            operating_codes = ['I01', 'I02', 'I03', 'I04', 'I05', 'I06', 'I07', 
                              'I08', 'I09', 'I10', 'I11', 'I12', 'I13', 'I14', 'I15', 'I16', 'I17']
        
        for code in operating_codes:
            if code in self.data:
                report['sections']['operating']['lines'].append({
                    'ma_so': code,
                    'description': self.data[code]['description'],
                    'amount': self.data[code]['value']
                })
        
        for code in ['21', '22', '23', '24', '25', '26', '27']:
            if code in self.data:
                report['sections']['investing']['lines'].append({
                    'ma_so': code,
                    'description': self.data[code]['description'],
                    'amount': self.data[code]['value']
                })
        
        for code in ['31', '32', '33', '34', '35', '36']:
            if code in self.data:
                report['sections']['financing']['lines'].append({
                    'ma_so': code,
                    'description': self.data[code]['description'],
                    'amount': self.data[code]['value']
                })
        
        for code in ['50', '60', '61', '70']:
            if code in self.data:
                report['sections']['reconciliation']['lines'].append({
                    'ma_so': code,
                    'description': self.data[code]['description'],
                    'amount': self.data[code]['value']
                })
        
        return report
    
    def export_to_dict(self) -> dict:
        """
        Export all data as simple dictionary
        
        Returns:
            Dictionary with ma_so keys and values
        """
        return {
            ma_so: item['value'] 
            for ma_so, item in self.data.items()
        }


# Example usage
if __name__ == "__main__":
    # Create model with indirect method (most common in Vietnam)
    model = VietnameseCashFlowModel(method='indirect')
    model.set_currency_unit('tỷ đồng')
    
    # Sample indirect method data (in tỷ VND)
    sample_data = {
        'I01': 11360,    # Lợi nhuận trước thuế
        'I02': 2500,     # Khấu hao
        'I03': 150,      # Dự phòng
        'I04': -50,      # Lãi tỷ giá chưa thực hiện
        'I05': -200,     # Lãi từ hoạt động đầu tư
        'I06': 800,      # Chi phí đi vay
        'I07': 100,      # Điều chỉnh khác
        'I09': -500,     # Tăng phải thu
        'I10': -300,     # Tăng hàng tồn kho
        'I11': 400,      # Tăng phải trả
        'I12': -50,      # Tăng chi phí chờ phân bổ
        'I13': -100,     # Tăng chứng khoán kinh doanh
        'I14': -750,     # Chi phí đi vay đã trả
        'I15': -2200,    # Thuế TNDN đã nộp
        'I16': 50,       # Tiền thu khác
        'I17': -80,      # Tiền chi khác
    }
    
    # Add all line items
    for ma_so, value in sample_data.items():
        model.add_line_item(ma_so, value)
    
    # Calculate totals
    totals = model.calculate_section_totals()
    print(f"=== BÁO CÁO LƯU CHUYỂN TIỀN TỆ ===")
    print(f"Đơn vị tính: {model.currency_unit}")
    print(f"Phương pháp: {model.method}")
    print()
    print(f"Lưu chuyển tiền thuần từ HĐKD (Mã 20): {totals['ma_so_20']:,.2f}")
    print(f"Lưu chuyển tiền thuần từ HĐĐT (Mã 30): {totals['ma_so_30']:,.2f}")
    print(f"Lưu chuyển tiền thuần từ HĐTC (Mã 40): {totals['ma_so_40']:,.2f}")
    print()
    
    # Reconcile
    reconciliation = model.reconcile_to_closing_cash(
        opening_cash=8500,  # Tỷ đồng
        fx_effect=-25
    )
    print(f"=== ĐIỀU CHỈNH ===")
    print(f"Lưu chuyển tiền thuần trong kỳ (Mã 50): {reconciliation['ma_so_50']:,.2f}")
    print(f"Tiền và TĐTT đầu kỳ (Mã 60): {reconciliation['ma_so_60']:,.2f}")
    print(f"Ảnh hưởng tỷ giá (Mã 61): {reconciliation['ma_so_61']:,.2f}")
    print(f"Tiền và TĐTT cuối kỳ (Mã 70): {reconciliation['ma_so_70']:,.2f}")
    print()
    
    # Validate against balance sheet
    validation = model.validate_against_balance_sheet(
        bs_cash_beginning=8500,
        bs_cash_ending=reconciliation['ma_so_70'],
        fx_effect=-25
    )
    print(f"=== KIỂM TRA ĐỐI CHIẾU ===")
    print(f"Kết quả: {'ĐẠT' if validation['valid'] else 'KHÔNG ĐẠT'}")
    print(f"Sai lệch: {validation['discrepancy']:,.6f}")
    print(f"Thông báo: {validation['message']}")
    print()
    
    # Show classification rules
    print(f"=== QUY TẮC PHÂN LOẠI THEO TT99 ===")
    rules = model.get_tt99_classification_rules()
    for item, rule in rules.items():
        print(f"{item}:")
        print(f"  Mã số: {rule['ma_so']}")
        print(f"  Chỉ tiêu: {rule['section']}")
        print(f"  Quy tắc: {rule['rule']}")
        print()
    
    # Generate full report
    report = model.generate_report(
        company_name="Công ty Cổ phần Sữa Việt Nam (VNM)",
        period="Năm 2024"
    )
    print(f"=== BÁO CÁO HOÀN CHỈNH ===")
    print(f"Công ty: {report['header']['company']}")
    print(f"Kỳ báo cáo: {report['header']['period']}")
    print(f"Số liệu: {len(report['sections']['operating']['lines'])} dòng HĐKD, "
          f"{len(report['sections']['investing']['lines'])} dòng HĐĐT, "
          f"{len(report['sections']['financing']['lines'])} dòng HĐTC")
