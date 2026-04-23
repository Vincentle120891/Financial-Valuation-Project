#!/usr/bin/env python3
"""
DuPont Analysis Engine - Python Version
Migrated from Node.js dupont-engine.js
"""


def validate_input_length(data_array, field_name):
    """Validate input data length (6-10 years)"""
    if not isinstance(data_array, list):
        raise ValueError(f"{field_name} must be a list")
    if len(data_array) < 6 or len(data_array) > 10:
        raise ValueError(f"{field_name} must have 6-10 values, got {len(data_array)}")
    return True


def calculate_supporting_ratios(financial_data):
    """Module 1: Calculate Supporting Financial Ratios"""
    required_fields = [
        'revenue', 'gross_profit', 'ebitda', 'operating_income', 'net_income',
        'total_assets', 'accounts_receivable', 'inventory', 'accounts_payable',
        'cogs', 'total_debt', 'total_equity', 'current_assets', 'current_liabilities',
        'interest_expense'
    ]
    
    for field in required_fields:
        if field not in financial_data:
            raise ValueError(f"Missing required field: {field}")
        validate_input_length(financial_data[field], field)
    
    years = len(financial_data['revenue'])
    ratios = {
        'gross_margin': [],
        'ebitda_margin': [],
        'operating_margin': [],
        'net_profit_margin': [],
        'asset_turnover': [],
        'ar_days': [],
        'inv_days': [],
        'ap_days': [],
        'cash_conversion_cycle': [],
        'debt_to_equity': [],
        'current_ratio': [],
        'interest_coverage': [],
        'roe': [],
        'roa': [],
        'roic': []
    }
    
    for i in range(years):
        # Profitability Margins
        ratios['gross_margin'].append(financial_data['gross_profit'][i] / financial_data['revenue'][i])
        ratios['ebitda_margin'].append(financial_data['ebitda'][i] / financial_data['revenue'][i])
        ratios['operating_margin'].append(financial_data['operating_income'][i] / financial_data['revenue'][i])
        ratios['net_profit_margin'].append(financial_data['net_income'][i] / financial_data['revenue'][i])
        
        # Efficiency Ratios
        ratios['asset_turnover'].append(financial_data['revenue'][i] / financial_data['total_assets'][i])
        
        # Working Capital Days (assuming 365 days)
        ar_days = (financial_data['accounts_receivable'][i] / financial_data['revenue'][i]) * 365
        inv_days = (financial_data['inventory'][i] / financial_data['cogs'][i]) * 365 if financial_data['cogs'][i] > 0 else 0
        ap_days = (financial_data['accounts_payable'][i] / financial_data['cogs'][i]) * 365 if financial_data['cogs'][i] > 0 else 0
        
        ratios['ar_days'].append(ar_days)
        ratios['inv_days'].append(inv_days)
        ratios['ap_days'].append(ap_days)
        ratios['cash_conversion_cycle'].append(ar_days + inv_days - ap_days)
        
        # Leverage Ratios
        ratios['debt_to_equity'].append(financial_data['total_debt'][i] / financial_data['total_equity'][i] if financial_data['total_equity'][i] > 0 else 0)
        ratios['current_ratio'].append(financial_data['current_assets'][i] / financial_data['current_liabilities'][i] if financial_data['current_liabilities'][i] > 0 else 0)
        ratios['interest_coverage'].append(financial_data['operating_income'][i] / financial_data['interest_expense'][i] if financial_data['interest_expense'][i] > 0 else 0)
        
        # Return Ratios
        ratios['roe'].append(financial_data['net_income'][i] / financial_data['total_equity'][i] if financial_data['total_equity'][i] > 0 else 0)
        ratios['roa'].append(financial_data['net_income'][i] / financial_data['total_assets'][i] if financial_data['total_assets'][i] > 0 else 0)
        
        # ROIC (simplified: NOPAT / Invested Capital)
        tax_rate = financial_data['net_income'][i-1] / financial_data['operating_income'][i-1] if i > 0 and financial_data['operating_income'][i-1] > 0 else 0.25
        nopat = financial_data['operating_income'][i] * (1 - tax_rate)
        invested_capital = financial_data['total_debt'][i] + financial_data['total_equity'][i]
        ratios['roic'].append(nopat / invested_capital if invested_capital > 0 else 0)
    
    return ratios


def calculate_dupont_3step(financial_data):
    """Module 2: Calculate 3-Step DuPont Analysis
    ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
    """
    validate_input_length(financial_data['net_income'], 'net_income')
    validate_input_length(financial_data['revenue'], 'revenue')
    validate_input_length(financial_data['total_assets'], 'total_assets')
    validate_input_length(financial_data['total_equity'], 'total_equity')
    
    years = len(financial_data['net_income'])
    result = {
        'net_profit_margin': [],
        'asset_turnover': [],
        'equity_multiplier': [],
        'roe_reconciled': []
    }
    
    for i in range(years):
        net_profit_margin = financial_data['net_income'][i] / financial_data['revenue'][i]
        asset_turnover = financial_data['revenue'][i] / financial_data['total_assets'][i]
        equity_multiplier = financial_data['total_assets'][i] / financial_data['total_equity'][i] if financial_data['total_equity'][i] > 0 else 0
        
        # ROE via DuPont formula
        roe_via_dupont = net_profit_margin * asset_turnover * equity_multiplier
        
        result['net_profit_margin'].append(net_profit_margin)
        result['asset_turnover'].append(asset_turnover)
        result['equity_multiplier'].append(equity_multiplier)
        result['roe_reconciled'].append(roe_via_dupont)
    
    return result


def calculate_dupont_5step(financial_data):
    """Module 3: Calculate 5-Step DuPont Analysis
    ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
    """
    required_fields = ['net_income', 'ebt', 'ebit', 'revenue', 'total_assets', 'total_equity', 'interest_expense']
    for field in required_fields:
        validate_input_length(financial_data[field], field)
    
    years = len(financial_data['net_income'])
    result = {
        'tax_burden': [],
        'interest_burden': [],
        'ebit_margin': [],
        'asset_turnover': [],
        'equity_multiplier': [],
        'roe_reconciled': []
    }
    
    for i in range(years):
        # Tax Burden = Net Income / EBT
        tax_burden = financial_data['net_income'][i] / financial_data['ebt'][i] if financial_data['ebt'][i] > 0 else 0
        
        # Interest Burden = EBT / EBIT
        interest_burden = financial_data['ebt'][i] / financial_data['ebit'][i] if financial_data['ebit'][i] > 0 else 0
        
        # EBIT Margin = EBIT / Revenue
        ebit_margin = financial_data['ebit'][i] / financial_data['revenue'][i]
        
        # Asset Turnover = Revenue / Total Assets
        asset_turnover = financial_data['revenue'][i] / financial_data['total_assets'][i]
        
        # Equity Multiplier = Total Assets / Total Equity
        equity_multiplier = financial_data['total_assets'][i] / financial_data['total_equity'][i] if financial_data['total_equity'][i] > 0 else 0
        
        # ROE via 5-step DuPont
        roe_via_dupont = tax_burden * interest_burden * ebit_margin * asset_turnover * equity_multiplier
        
        result['tax_burden'].append(tax_burden)
        result['interest_burden'].append(interest_burden)
        result['ebit_margin'].append(ebit_margin)
        result['asset_turnover'].append(asset_turnover)
        result['equity_multiplier'].append(equity_multiplier)
        result['roe_reconciled'].append(roe_via_dupont)
    
    return result


def calculate_growth_trends(financial_data):
    """Module 4: Calculate Growth Trends"""
    years = len(financial_data['revenue'])
    trends = {
        'revenue_growth': [],
        'net_income_growth': [],
        'roe_change': [],
        'roa_change': [],
        'margin_trends': {}
    }
    
    for i in range(1, years):
        # Revenue Growth
        rev_growth = (financial_data['revenue'][i] - financial_data['revenue'][i-1]) / financial_data['revenue'][i-1] if financial_data['revenue'][i-1] > 0 else 0
        trends['revenue_growth'].append(rev_growth)
        
        # Net Income Growth
        ni_growth = (financial_data['net_income'][i] - financial_data['net_income'][i-1]) / financial_data['net_income'][i-1] if financial_data['net_income'][i-1] > 0 else 0
        trends['net_income_growth'].append(ni_growth)
    
    # Fill first year with 0
    if trends['revenue_growth']:
        trends['revenue_growth'].insert(0, 0)
        trends['net_income_growth'].insert(0, 0)
    
    # Calculate average trends
    avg_rev_growth = sum(trends['revenue_growth'][1:]) / len(trends['revenue_growth'][1:]) if len(trends['revenue_growth']) > 1 else 0
    avg_ni_growth = sum(trends['net_income_growth'][1:]) / len(trends['net_income_growth'][1:]) if len(trends['net_income_growth']) > 1 else 0
    
    trends['average_revenue_growth'] = avg_rev_growth
    trends['average_net_income_growth'] = avg_ni_growth
    
    return trends


def validate_dupont_calculations(dupont_3step, dupont_5step, financial_data):
    """Module 5: Validate DuPont Calculations"""
    validation = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    years = len(financial_data['revenue'])
    
    # Check 3-step reconciliation
    for i in range(years):
        direct_roe = financial_data['net_income'][i] / financial_data['total_equity'][i] if financial_data['total_equity'][i] > 0 else 0
        reconciled_roe = dupont_3step['roe_reconciled'][i]
        
        if abs(direct_roe - reconciled_roe) > 0.01:  # 1% tolerance
            validation['warnings'].append(f"Year {i}: 3-step ROE reconciliation off by {abs(direct_roe - reconciled_roe):.4f}")
    
    # Check 5-step reconciliation
    for i in range(years):
        direct_roe = financial_data['net_income'][i] / financial_data['total_equity'][i] if financial_data['total_equity'][i] > 0 else 0
        reconciled_roe = dupont_5step['roe_reconciled'][i]
        
        if abs(direct_roe - reconciled_roe) > 0.01:  # 1% tolerance
            validation['warnings'].append(f"Year {i}: 5-step ROE reconciliation off by {abs(direct_roe - reconciled_roe):.4f}")
    
    # Check for negative margins (potential issues)
    for i in range(years):
        if dupont_3step['net_profit_margin'][i] < 0:
            validation['warnings'].append(f"Year {i}: Negative net profit margin")
    
    if validation['errors']:
        validation['is_valid'] = False
    
    return validation


def perform_dupont_analysis(input_data):
    """Main DuPont Analysis Function"""
    try:
        # Calculate all components
        supporting_ratios = calculate_supporting_ratios(input_data)
        dupont_3step = calculate_dupont_3step(input_data)
        dupont_5step = calculate_dupont_5step(input_data)
        growth_trends = calculate_growth_trends(input_data)
        validation = validate_dupont_calculations(dupont_3step, dupont_5step, input_data)
        
        # Determine number of years analyzed
        years_analyzed = len(input_data['revenue'])
        
        return {
            'success': True,
            'supporting_ratios': supporting_ratios,
            'dupont_3step': dupont_3step,
            'dupont_5step': dupont_5step,
            'growth_trends': growth_trends,
            'validation': validation,
            'metadata': {
                'years_analyzed': years_analyzed,
                'currency': input_data.get('currency', 'USD'),
                'unit_scaling': input_data.get('unit_scaling', 'thousands')
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Main entry point for testing
if __name__ == "__main__":
    import json
    
    # Test data (6 years)
    test_data = {
        'revenue': [100000, 110000, 121000, 133100, 146410, 161051],
        'gross_profit': [60000, 66000, 72600, 79860, 87846, 96631],
        'ebitda': [40000, 44000, 48400, 53240, 58564, 64420],
        'operating_income': [30000, 33000, 36300, 39930, 43923, 48315],
        'net_income': [20000, 22000, 24200, 26620, 29282, 32210],
        'total_assets': [200000, 210000, 220500, 231525, 243101, 255256],
        'total_equity': [100000, 110000, 121000, 133100, 146410, 161051],
        'total_debt': [50000, 55000, 60500, 66550, 73205, 80526],
        'accounts_receivable': [10000, 11000, 12100, 13310, 14641, 16105],
        'inventory': [5000, 5500, 6050, 6655, 7321, 8053],
        'accounts_payable': [8000, 8800, 9680, 10648, 11713, 12884],
        'cogs': [40000, 44000, 48400, 53240, 58564, 64420],
        'current_assets': [30000, 33000, 36300, 39930, 43923, 48315],
        'current_liabilities': [15000, 16500, 18150, 19965, 21962, 24158],
        'interest_expense': [2500, 2750, 3025, 3328, 3660, 4026],
        'ebt': [27500, 30250, 33275, 36603, 40263, 44289],
        'ebit': [30000, 33000, 36300, 39930, 43923, 48315],
        'currency': 'USD',
        'unit_scaling': 'thousands'
    }
    
    result = perform_dupont_analysis(test_data)
    print(json.dumps(result, indent=2))
