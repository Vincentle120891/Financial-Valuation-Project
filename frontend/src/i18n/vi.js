/**
 * Vietnamese Translations — Corporate Finance Localization
 * 
 * Translation Mask: Only UI wrappers are translated.
 * Financial data, acronyms (WACC, EBITDA, DCF, P/E, Beta, VaR),
 * ticker codes, and calculation states stay English uppercase.
 * 
 * Density Protection: Concise Vietnamese corporate terminology used.
 * Financial acronyms remain English in data grids to prevent layout breakage.
 */
export default {
  translation: {
    // Common Actions
    common: {
      loading: "Đang tải...",
      search: "Tìm kiếm",
      select: "Chọn",
      cancel: "Hủy",
      confirm: "Xác nhận",
      save: "Lưu",
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
      submit: "Gửi",
      edit: "Sửa",
      view: "Xem",
      delete: "Xóa",
      fetch_data: "Lấy dữ liệu",
      retrieve_data: "Thu thập dữ liệu",
      run_valuation: "Chạy định giá",
      generate_scenarios: "Tạo kịch bản",
      apply: "Áp dụng",
      remove: "Xóa bỏ",
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
      watchlist: "Danh mục Theo dõi",
    },

    // Stock Types
    stockTypes: {
      vietnamese: "Cổ phiếu Việt Nam",
      international: "Cổ phiếu Quốc tế",
      us: "Cổ phiếu Mỹ",
    },

    // Step Titles — Aligned with Backend Unified Schema
    steps: {
      step1: "Bước 1: Tìm kiếm & Chọn Công ty",
      step2: "Bước 2: Xác nhận Thị trường & Dữ liệu",
      step3: "Bước 3: Chọn Phương pháp Định giá",
      step4: "Bước 4: Chọn Công ty Đồng nghiệp",
      step5: "Bước 5: Chuẩn bị Đầu vào/Giả định",
      step6: "Bước 6: Lấy dữ liệu API",
      step7: "Bước 7: Xử lý Dữ liệu Lịch sử",
      step8: "Bước 8: Giả định & Đề xuất AI",
      step9: "Bước 9: Xác nhận Giả định",
      step10: "Bước 10: Thực hiện Định giá",
      step11: "Bước 11: Kết quả & Phân tích Định giá",
    },

    // Step Descriptions
    stepDescriptions: {
      step1: "Nhập tên công ty hoặc mã chứng khoán để lấy các chỉ số tài chính và bắt đầu tìm kiếm công ty đồng nghiệp.",
      step2: "Xem xét dữ liệu thị trường và xác nhận thông tin công ty mục tiêu.",
      step3: "Chọn phương pháp định giá cho phân tích này.",
      step4: "Chọn các công ty đồng nghiệp để so sánh.",
      step5: "Xem xét và chuẩn bị các đầu vào cần thiết cho mô hình định giá.",
      step6: "Dữ liệu tài chính đã được lấy từ API. Xem xét độ chính xác trước khi tiếp tục.",
      step7: "Xem xét dữ liệu tài chính lịch sử do AI trích xuất.",
      step8: "Điều chỉnh tốc độ tăng trưởng doanh thu, biên lợi nhuận và các yếu tố dự báo khác.",
      step9: "Xác nhận tất cả giả định trước khi thực hiện các mô hình định giá.",
      step10: "Thực hiện phân tích DCF, So sánh bội số và DuPont.",
      step11: "Kết quả định giá toàn diện với so sánh đa phương pháp.",
    },

    // Financial Statements
    financialStatements: {
      income_statement: "Báo cáo Kết quả Kinh doanh",
      balance_sheet: "Bảng Cân đối Kế toán",
      cash_flow: "Báo cáo Lưu chuyển Tiền tệ",
      notes: "Thuyết minh Báo cáo Tài chính",
      annual: "Năm",
      quarterly: "Quý",
      consolidated: "Hợp nhất",
      standalone: "Riêng lẻ",
      historical: "Báo cáo Tài chính Lịch sử",
      periods: "kỳ",
    },

    // Structural Financial Labels
    sections: {
      balance_sheet: "Bảng Cân đối Kế toán",
      income_statement: "Báo cáo Kết quả Kinh doanh",
      cash_flow_statement: "Báo cáo Lưu chuyển Tiền tệ",
      assumptions_inputs: "Giả định Mô hình",
      growth_rate: "Tốc độ Tăng trưởng",
      discount_factor: "Hệ số Chiết khấu",
      revenue_drivers: "Yếu tố Tăng trưởng Doanh thu",
      cost_margins: "Chi phí & Biên lợi nhuận",
      working_capital: "Vốn Lưu động",
      wacc_components: "Các thành phần WACC",
      terminal_value: "Giá trị Dài hạn",
      dcf_model_inputs: "Đầu vào Mô hình DCF",
      peer_comparison: "Dữ liệu So sánh Đồng nghiệp",
      dupont_analysis: "Kết quả Phân tích DuPont",
      comps_analysis: "Phân tích Công ty So sánh",
      calculated_metrics: "Chỉ số Trung gian Tính toán",
      valuation_results: "Kết quả & Phân tích Định giá",
      multi_method_summary: "Tổng hợp Định giá Đa phương pháp",
      historical_financials: "Tài chính Lịch sử (từ API)",
      forecast_drivers: "Yếu tố Dự báo (từ API)",
      extraction_methodology: "Phương pháp Trích xuất",
      key_financial_metrics: "Chỉ số Tài chính Trọng yếu",
    },

    // Structural Metric Labels
    metrics: {
      revenue: "Doanh thu",
      cogs: "Giá vốn hàng bán",
      gross_profit: "Lợi nhuận gộp",
      operating_income: "Lợi nhuận thuần từ HĐKD",
      net_income: "Lợi nhuận ròng",
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
      depreciation: "Khấu hao & Phân bổ",
      sga_opex: "Chi phí Bán hàng & QLDN",
      free_cash_flow: "Dòng tiền tự do",
      shares_outstanding: "Số CP lưu hành",
      risk_free_rate: "Lãi suất không rủi ro",
      equity_risk_premium: "Phần bù rủi ro thị trường (ERP)",
      beta: "Beta",
      cost_of_debt: "Chi phí nợ",
      terminal_growth_rate: "Tốc độ tăng trưởng dài hạn",
      terminal_ebitda_multiple: "Bội số EV/EBITDA cuối kỳ",
      useful_life: "Tuổi thọ (Tài sản hiện tại)",
      avg_roe: "ROE Trung bình",
      roe_trend: "Xu hướng ROE",
      latest_roe: "ROE Mới nhất",
      revenue_cagr: "CAGR Doanh thu",
      avg_ebitda_margin: "Biên EBITDA TB",
      avg_net_margin: "Biên LNST TB",
    },

    // Data Status Badges — NEVER TRANSLATED (Translation Mask Law)
    dataStatus: {
      retrieved: "RETRIEVED",
      fetched: "✓ FETCHED",
      calculated: "📊 CALCULATED",
      manual: "✏️ MANUAL",
      ai: "🤖 AI",
      missing: "⚠ MISSING",
      unknown: "? UNKNOWN",
      no_data: "Không có dữ liệu",
    },

    // Market & Exchange
    marketData: {
      ticker: "Mã CK",
      company_name: "Tên công ty",
      current_price: "Giá hiện tại",
      market_cap: "Vốn hóa",
      change: "Biến động",
      change_percent: "% Biến động",
      volume: "Khối lượng",
      value: "Giá trị GD",
      high_52w: "Cao nhất 52 tuần",
      low_52w: "Thấp nhất 52 tuần",
      avg_volume: "KL TB",
      dividend_yield: "Tỷ suất Cổ tức",
      sector: "Ngành",
      exchange: "Sàn",
      industry: "Lĩnh vực",
      market: "Thị trường",
      region: "Khu vực",
    },

    // Valuation Methods
    valuationMethods: {
      dcf: "Công cụ DCF",
      dupont: "Phân tích DuPont",
      comps: "So sánh Bội số",
      vietnamese: "Mô hình Việt Nam",
      international: "Mô hình Quốc tế",
    },

    // Buttons
    buttons: {
      search_company: "Tìm công ty",
      fetch_data: "Lấy dữ liệu",
      retrieve_data: "Thu thập dữ liệu",
      continue_next: "Tiếp tục Bước tiếp",
      run_valuation: "Chạy định giá",
      generate_scenarios: "Tạo kịch bản",
      use_ai: "Dùng AI",
      ai_suggestion: "Đề xuất AI",
      apply_suggestion: "Áp dụng Đề xuất AI",
      manual_override: "Điều chỉnh Thủ công",
      edit_inputs: "Chỉnh sửa",
      save_inputs: "Lưu",
      back_to_previous: "Quay lại Bước trước",
      upload_pdf: "Tải lên Báo cáo PDF",
      ai_web_search: "Tìm kiếm Web bằng AI",
      sec_fetch: "Lấy từ SEC EDGAR",
      toggle_edit_mode: "Bật/Tắt chế độ Sửa",
    },

    // Input Labels
    inputs: {
      search_placeholder_intl: "Nhập mã CK (VD: AAPL, MSFT) hoặc tên công ty",
      search_placeholder_vn: "Nhập mã CK (VD: VNM, VIC, HPG) hoặc tên công ty",
      select_market: "Chọn Thị trường",
      select_model: "Chọn Mô hình Định giá",
      select_peers: "Chọn Công ty Đồng nghiệp",
      custom_prompt: "Prompt AI Tùy chỉnh",
    },

    // Messages & Notifications
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
      no_data_retrieved: "Chưa lấy được dữ liệu",
      no_data_description: "Không thể hiển thị đầu vào. Vui lòng kiểm tra xem dữ liệu đã được lấy thành công từ API chưa.",
      please_go_back: "Vui lòng quay lại Bước 5 và nhấp \"Thu thập dữ liệu\" trước.",
      loading_statements: "Đang tải báo cáo tài chính...",
      no_statements: "Chưa có dữ liệu báo cáo tài chính. Hoàn thành các bước trước để hiển thị.",
      about_step6: "Màn hình này hiển thị toàn bộ dữ liệu tài chính được tự động lấy từ API bên ngoài. Xác nhận độ chính xác trước khi tiếp tục.",
    },

    // Foreign Ownership (Vietnam)
    foreignOwnership: {
      fol: "Room ngoại (FOL)",
      fol_limit: "Giới hạn sở hữu nước ngoài",
      current_fol: "Tỷ lệ sở hữu nước ngoài hiện tại",
      fol_restricted: "Hết room ngoại",
      available_fol: "Room ngoại còn lại",
      status: "Trạng thái",
    },

    // Exchange Info
    exchangeInfo: {
      trading_hours: "Giờ giao dịch",
      settlement: "Thanh toán",
      currency: "Đơn vị tiền tệ",
      market_status: "Trạng thái thị trường",
      open: "Mở cửa",
      closed: "Đóng cửa",
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

    // System Notice — Translation Mask Disclaimer
    notices: {
      translation_disclaimer: "Lưu ý: Giao diện ngôn ngữ được bản địa hóa cho mục đích hiển thị. Các chỉ số tài chính, thuật ngữ chuyên ngành và tính toán số liệu được giữ nguyên theo tiêu chuẩn báo cáo quốc tế.",
    },
  },
};
