/**
 * Vietnamese Language Translations for Valuation Platform
 * 
 * This file contains all Vietnamese translations for the UI.
 * Uses i18next format for React internationalization.
 * 
 * Usage:
 * import { t } from 'i18next';
 * t('common.submit') // Returns "Gửi"
 */

export const vi = {
  translation: {
    // Common Terms
    common: {
      submit: "Gửi",
      cancel: "Hủy",
      save: "Lưu",
      delete: "Xóa",
      edit: "Sửa",
      view: "Xem",
      search: "Tìm kiếm",
      loading: "Đang tải...",
      error: "Lỗi",
      success: "Thành công",
      warning: "Cảnh báo",
      info: "Thông tin",
      yes: "Có",
      no: "Không",
      ok: "OK",
      close: "Đóng",
      back: "Quay lại",
      next: "Tiếp theo",
      previous: "Trước",
      finish: "Hoàn thành",
      reset: "Đặt lại",
      refresh: "Làm mới",
      export: "Xuất",
      import: "Nhập",
      download: "Tải xuống",
      upload: "Tải lên",
    },

    // Navigation
    nav: {
      home: "Trang chủ",
      dashboard: "Bảng điều khiển",
      valuation: "Định giá",
      stocks: "Cổ phiếu",
      portfolio: "Danh mục",
      reports: "Báo cáo",
      settings: "Cài đặt",
      help: "Trợ giúp",
    },

    // Stock Types
    stockTypes: {
      vietnamese: "Cổ phiếu Việt Nam",
      international: "Cổ phiếu Quốc tế",
      us: "Cổ phiếu Mỹ",
    },

    // Exchanges
    exchanges: {
      hose: "HOSE (Sàn TP.HCM)",
      hnx: "HNX (Sàn Hà Nội)",
      upcom: "UPCOM (Sàn chưa niêm yết)",
      nyse: "NYSE",
      nasdaq: "NASDAQ",
      amex: "AMEX",
    },

    // Sectors (Vietnamese Market)
    sectors: {
      banking: "Ngân hàng",
      real_estate: "Bất động sản",
      consumer_staples: "Hàng tiêu dùng thiết yếu",
      consumer_discretionary: "Hàng tiêu dùng không thiết yếu",
      materials: "Vật liệu/Xây dựng",
      industrials: "Công nghiệp",
      energy: "Năng lượng",
      utilities: "Điện/Nước",
      healthcare: "Y tế/Dược phẩm",
      technology: "Công nghệ",
      telecommunications: "Viễn thông",
      financials: "Tài chính/Chứng khoán/Bảo hiểm",
    },

    // Financial Statements
    financialStatements: {
      income_statement: "Báo cáo kết quả hoạt động kinh doanh",
      balance_sheet: "Báo cáo tình hình tài chính",
      cash_flow: "Báo cáo lưu chuyển tiền tệ",
      notes: "Thuyết minh báo cáo tài chính",
      annual: "Năm",
      quarterly: "Quý",
      consolidated: "Hợp nhất",
      standalone: "Riêng lẻ",
    },

    // Financial Metrics
    metrics: {
      revenue: "Doanh thu",
      cogs: "Giá vốn hàng bán",
      gross_profit: "Lợi nhuận gộp",
      operating_income: "Lợi nhuận thuần từ HĐKD",
      net_income: "Lợi nhuận sau thuế",
      ebitda: "EBITDA",
      ebit: "EBIT",
      total_assets: "Tổng tài sản",
      total_liabilities: "Tổng nợ phải trả",
      equity: "Vốn chủ sở hữu",
      cash: "Tiền và tương đương tiền",
      debt: "Nợ vay",
      accounts_receivable: "Phải thu khách hàng",
      inventory: "Hàng tồn kho",
      accounts_payable: "Phải trả người bán",
      operating_cf: "Lưu chuyển tiền từ HĐKD",
      investing_cf: "Lưu chuyển tiền từ HĐĐT",
      financing_cf: "Lưu chuyển tiền từ HĐTC",
      capex: "Chi phí đầu tư TSCĐ",
      dividends: "Cổ tức đã trả",
    },

    // Ratios & Multiples
    ratios: {
      pe_ratio: "P/E",
      pb_ratio: "P/B",
      ps_ratio: "P/S",
      ev_ebitda: "EV/EBITDA",
      ev_revenue: "EV/Doanh thu",
      roe: "ROE",
      roa: "ROA",
      roic: "ROIC",
      gross_margin: "Biên lợi nhuận gộp",
      operating_margin: "Biên lợi nhuận thuần từ HĐKD",
      net_margin: "Biên lợi nhuận ròng",
      ebitda_margin: "Biên EBITDA",
      debt_to_equity: "Nợ/Vốn chủ sở hữu",
      current_ratio: "Hệ số thanh toán hiện hành",
      quick_ratio: "Hệ số thanh toán nhanh",
      asset_turnover: "Vòng quay tổng tài sản",
      inventory_turnover: "Vòng quay hàng tồn kho",
    },

    // Valuation Methods
    valuationMethods: {
      dcf: "DCF (Chiết khấu dòng tiền)",
      dd_model: "Mô hình chiết khấu cổ tức",
      nav: "NAV (Giá trị tài sản ròng)",
      rnava: "RNAV (NAV định giá lại)",
      comps: "So sánh bội số",
      residual_income: "Thu nhập thặng dư",
      sector_specific: "Mô hình theo ngành",
    },

    // Banking Specific
    banking: {
      npl_ratio: "Tỷ lệ nợ xấu",
      llr_ratio: "Tỷ lệ dự phòng rủi ro",
      cost_of_risk: "Chi phí rủi ro tín dụng",
      car_ratio: "Tỷ lệ an toàn vốn (CAR)",
      tier1_capital: "Vốn cấp 1",
      nim: "Biên lãi ròng (NIM)",
      cir: "Tỷ lệ chi phí trên thu nhập (CIR)",
      loan_growth: "Tăng trưởng tín dụng",
      deposit_growth: "Tăng trưởng tiền gửi",
      dividend_payout: "Tỷ lệ chi trả cổ tức",
      book_value_per_share: "Giá trị sổ sách trên cổ phiếu (BVPS)",
    },

    // Real Estate Specific
    realEstate: {
      land_bank: "Quỹ đất",
      total_land_area: "Tổng diện tích đất (m²)",
      developable_area: "Diện tích có thể phát triển (m²)",
      average_land_cost: "Giá vốn đất bình quân (VND/m²)",
      number_of_projects: "Số lượng dự án",
      projects_under_construction: "Dự án đang thi công",
      projects_ready_for_sale: "Dự án sẵn sàng bàn giao",
      average_selling_price: "Giá bán bình quân (VND/m²)",
      pre_sales_rate: "Tỷ lệ bán trước",
      sales_velocity: "Tốc độ bán hàng",
      nav_per_share: "NAV trên cổ phiếu",
      rnava_per_share: "RNAV trên cổ phiếu",
      pipeline_value: "Giá trị quỹ dự án tương lai",
      completion_rate: "Tỷ lệ hoàn thành dự án",
    },

    // Manufacturing Specific
    manufacturing: {
      production_capacity: "Công suất sản xuất (tấn/năm)",
      utilization_rate: "Tỷ lệ sử dụng công suất",
      actual_production: "Sản lượng thực tế (tấn)",
      raw_material_cost: "Giá vốn nguyên liệu (VND/tấn)",
      energy_cost: "Chi phí năng lượng (VND/tấn)",
      labor_cost: "Chi phí nhân công (VND/tấn)",
      average_selling_price: "Giá bán bình quân (VND/tấn)",
      price_realization: "Mức giá so với thị trường",
      commodity_exposure: "Rủi ro giá nguyên liệu",
      fx_exposure: "Rủi ro tỷ giá",
      maintenance_capex: "Capex bảo trì",
      expansion_capex: "Capex mở rộng",
    },

    // Foreign Ownership
    foreignOwnership: {
      fol: "Room ngoại (FOL)",
      fol_limit: "Giới hạn sở hữu nước ngoài",
      current_fol: "Tỷ lệ sở hữu nước ngoài hiện tại",
      fol_restricted: "Hết room ngoại",
      available_fol: "Room ngoại còn lại",
    },

    // Market Data
    marketData: {
      ticker: "Mã chứng khoán",
      company_name: "Tên công ty",
      current_price: "Giá hiện tại",
      change: "Biến động",
      change_percent: "% Biến động",
      volume: "Khối lượng",
      value: "Giá trị giao dịch",
      market_cap: "Vốn hóa thị trường",
      high_52w: "Cao nhất 52 tuần",
      low_52w: "Thấp nhất 52 tuần",
      avg_volume: "KL giao dịch bình quân",
      beta: "Beta",
      dividend_yield: "Tỷ suất cổ tức",
      eps: "EPS",
      shares_outstanding: "Số cổ phiếu lưu hành",
    },

    // Valuation Steps
    steps: {
      step1: "Chọn mô hình",
      step2: "Nhập mã cổ phiếu",
      step3: "Yêu cầu dữ liệu",
      step4: "Lấy dữ liệu API",
      step5: "Giả định AI",
      step6: "Kịch bản dự báo",
      step7: "Tính toán định giá",
      step8: "Kết quả",
    },

    // AI Assumptions
    aiAssumptions: {
      equity_risk_premium: "Phần bù rủi ro thị trường (ERP)",
      country_risk_premium: "Phần bù rủi ro quốc gia (CRP)",
      terminal_growth_rate: "Tốc độ tăng trưởng dài hạn",
      terminal_ebitda_multiple: "Bội số EV/EBITDA cuối kỳ",
      use_ai_suggestion: "Sử dụng đề xuất AI",
      manual_override: "Điều chỉnh thủ công",
      rationale: "Lý giải",
    },

    // Recommendations
    recommendations: {
      strong_buy: "MUA MẠNH",
      buy: "MUA",
      hold: "NẮM GIỮ",
      reduce: "GIẢM TỶ TRỌNG",
      sell: "BÁN",
      strong_sell: "BÁN MẠNH",
    },

    // Risk Warnings
    risks: {
      market_risk: "Rủi ro thị trường",
      credit_risk: "Rủi ro tín dụng",
      liquidity_risk: "Rủi ro thanh khoản",
      operational_risk: "Rủi ro hoạt động",
      regulatory_risk: "Rủi ro pháp lý",
      currency_risk: "Rủi ro tỷ giá",
      commodity_risk: "Rủi ro giá nguyên liệu",
      interest_rate_risk: "Rủi ro lãi suất",
    },

    // Messages
    messages: {
      data_fetch_success: "Đã lấy dữ liệu thành công",
      data_fetch_error: "Không thể lấy dữ liệu",
      calculation_complete: "Tính toán hoàn tất",
      calculation_error: "Lỗi tính toán",
      please_select_stock: "Vui lòng chọn cổ phiếu",
      invalid_ticker: "Mã cổ phiếu không hợp lệ",
      loading_data: "Đang tải dữ liệu...",
      processing: "Đang xử lý...",
      ready_to_valuate: "Sẵn sàng định giá",
    },

    // Currency
    currency: {
      vnd: "VNĐ",
      usd: "USD",
      million_vnd: "Triệu VNĐ",
      billion_vnd: "Tỷ VNĐ",
      exchange_rate: "Tỷ giá",
      convert_to_usd: "Quy đổi sang USD",
    },

    // Time Periods
    timePeriods: {
      today: "Hôm nay",
      ytd: "Từ đầu năm",
      one_month: "1 tháng",
      three_months: "3 tháng",
      six_months: "6 tháng",
      one_year: "1 năm",
      three_years: "3 năm",
      five_years: "5 năm",
      ten_years: "10 năm",
      max: "Tối đa",
    },

    // Table Headers
    tableHeaders: {
      ticker: "Mã",
      company: "Công ty",
      sector: "Ngành",
      price: "Giá",
      change: "±",
      volume: "KL",
      market_cap: "Vốn hóa",
      pe: "P/E",
      pb: "P/B",
      dividend_yield: "Cổ tức",
      recommendation: "Khuyến nghị",
    },
  },
};

export default vi;
