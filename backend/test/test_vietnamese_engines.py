"""
Tests for Vietnamese Market Routes and Engines
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
sys.path.insert(0, '/workspace/backend')

from app.services.vietnamese import (
    VNTradingCompsAnalyzer,
    VNTargetCompanyData,
    VNPeerCompanyData,
    VNDuPontAnalyzer,
    VNFinancialStatements,
)


class TestVNTradingCompsAnalyzer:
    """Test the Vietnamese Trading Comps Analyzer engine"""

    def test_analyzer_initialization(self):
        """Test that analyzer can be initialized with target and peer companies"""
        target = VNTargetCompanyData(
            ticker="VNM",
            company_name="Vinamilk",
            market_cap_vnd=150000,
            enterprise_value_vnd=160000,
            ebitda_ltm_vnd=18200,
            eps_ltm_vnd=7500,
            net_debt_vnd=10000,
            shares_outstanding=1000,
            share_price_vnd=150,
            sector="Consumer Goods"
        )

        peers = [
            VNPeerCompanyData(
                ticker="MSN",
                company_name="Masan Group",
                market_cap_vnd=120000,
                enterprise_value_vnd=130000,
                share_price_vnd=120,
                shares_outstanding=1000,
                ebitda_ltm_vnd=15000,
                eps_ltm_vnd=6000,
                revenue_ltm_vnd=70000,
                net_income_ltm_vnd=9000,
                book_value_vnd=80000,
                sector="Consumer Goods"
            )
        ]

        analyzer = VNTradingCompsAnalyzer(target, peers)
        assert analyzer is not None
        assert analyzer.target_company.ticker == "VNM"
        assert len(analyzer.peer_companies) == 1

    def test_run_analysis_basic(self):
        """Test that run_analysis returns results without errors"""
        target = VNTargetCompanyData(
            ticker="VNM",
            company_name="Vinamilk",
            market_cap_vnd=150000,
            enterprise_value_vnd=160000,
            ebitda_ltm_vnd=18200,
            eps_ltm_vnd=7500,
            net_debt_vnd=10000,
            shares_outstanding=1000,
            share_price_vnd=150,
            sector="Consumer Goods"
        )

        peers = [
            VNPeerCompanyData(
                ticker="MSN",
                company_name="Masan Group",
                market_cap_vnd=120000,
                enterprise_value_vnd=130000,
                share_price_vnd=120,
                shares_outstanding=1000,
                ebitda_ltm_vnd=15000,
                eps_ltm_vnd=6000,
                revenue_ltm_vnd=70000,
                net_income_ltm_vnd=9000,
                book_value_vnd=80000,
                sector="Consumer Goods"
            ),
            VNPeerCompanyData(
                ticker="SAB",
                company_name="Sabeco",
                market_cap_vnd=140000,
                enterprise_value_vnd=145000,
                share_price_vnd=140,
                shares_outstanding=1000,
                ebitda_ltm_vnd=16000,
                eps_ltm_vnd=6500,
                revenue_ltm_vnd=75000,
                net_income_ltm_vnd=9500,
                book_value_vnd=85000,
                sector="Consumer Goods"
            )
        ]

        analyzer = VNTradingCompsAnalyzer(target, peers)
        results = analyzer.run_analysis()

        assert results is not None
        assert hasattr(results, 'to_dict')
        result_dict = results.to_dict()
        assert 'valuation_summary' in result_dict or 'target_valuation' in result_dict

    def test_run_analysis_with_outlier_filtering(self):
        """Test analysis with outlier filtering enabled"""
        target = VNTargetCompanyData(
            ticker="VNM",
            company_name="Vinamilk",
            market_cap_vnd=150000,
            enterprise_value_vnd=160000,
            ebitda_ltm_vnd=18200,
            eps_ltm_vnd=7500,
            net_debt_vnd=10000,
            shares_outstanding=1000,
            share_price_vnd=150,
            sector="Consumer Goods"
        )

        peers = [
            VNPeerCompanyData(
                ticker="MSN",
                company_name="Masan Group",
                market_cap_vnd=120000,
                enterprise_value_vnd=130000,
                share_price_vnd=120,
                shares_outstanding=1000,
                ebitda_ltm_vnd=15000,
                eps_ltm_vnd=6000,
                revenue_ltm_vnd=70000,
                net_income_ltm_vnd=9000,
                book_value_vnd=80000,
                sector="Consumer Goods"
            )
        ]

        analyzer = VNTradingCompsAnalyzer(target, peers)
        results = analyzer.run_analysis(
            apply_outlier_filtering=True,
            iqr_multiplier=1.5,
            outlier_metric="ev_ebitda_ltm"
        )

        assert results is not None


class TestVNDuPontAnalyzer:
    """Test the Vietnamese DuPont Analyzer engine"""

    def test_analyzer_initialization(self):
        """Test that DuPont analyzer can be initialized"""
        analyzer = VNDuPontAnalyzer()
        assert analyzer is not None

    def test_load_data_and_calculate(self):
        """Test loading data and calculating DuPont analysis"""
        statements = VNFinancialStatements()

        # Set up minimal financial data for 3 years
        statements.revenue = [85500, 80000, 75000, 0, 0, 0, 0, 0]
        statements.cogs_gross = [-50000, -48000, -45000, 0, 0, 0, 0, 0]
        statements.sga = [-10000, -9500, -9000, 0, 0, 0, 0, 0]
        statements.common_equity = [32300, 30000, 28000, 0, 0, 0, 0, 0]
        statements.total_assets = [50500, 48000, 45000, 0, 0, 0, 0, 0]

        analyzer = VNDuPontAnalyzer()
        analyzer.load_data(statements)

        result = analyzer.calculate_all()

        assert result is not None
        assert hasattr(result, 'to_dict')
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)

    def test_dupont_with_complete_data(self):
        """Test DuPont analysis with more complete financial data"""
        statements = VNFinancialStatements()

        # Set up 5 years of data
        for idx in range(5):
            year_multiplier = 1 + (idx * 0.1)
            statements.revenue[idx] = 75000 * year_multiplier
            statements.cogs_gross[idx] = -45000 * year_multiplier
            statements.sga[idx] = -9000 * year_multiplier
            statements.depreciation[idx] = -2000 * year_multiplier
            statements.interest_expense[idx] = -500 * year_multiplier
            statements.tax_current[idx] = -3000 * year_multiplier
            statements.common_equity[idx] = 28000 * year_multiplier
            statements.cash[idx] = 5000 * year_multiplier
            statements.accounts_receivable[idx] = 8000 * year_multiplier
            statements.inventories[idx] = 10000 * year_multiplier
            statements.ppe_component1[idx] = 20000 * year_multiplier
            statements.accounts_payable[idx] = 6000 * year_multiplier
            statements.revolving_credit[idx] = 3000 * year_multiplier
            statements.long_term_debt[idx] = 10000 * year_multiplier

        analyzer = VNDuPontAnalyzer()
        analyzer.load_data(statements)

        result = analyzer.calculate_all()

        assert result is not None
        result_dict = result.to_dict()
        assert 'dupont_analysis' in result_dict or 'roe' in str(result_dict).lower()


class TestVietnameseMarketRoutes:
    """Test the Vietnamese market data routes"""

    @pytest.fixture
    def sample_comps_request(self):
        """Sample request data for comps endpoint"""
        return {
            "target_ticker": "VNM",
            "target_company_name": "Vinamilk",
            "sector": "Consumer Goods",
            "target_revenue_vnd": 85500,
            "target_ebitda_vnd": 18200,
            "target_net_income_vnd": 12700,
            "target_eps_vnd": 7500,
            "target_book_value_vnd": 32300,
            "peer_multiples": [
                {
                    "ticker": "MSN",
                    "company_name": "Masan Group",
                    "enterprise_value": 130000,
                    "share_price": 120,
                    "book_value": 80000,
                    "pb_ratio": 1.5,
                    "ev_ebitda_ltm": 8.5,
                    "pe_ltm": 15.0,
                    "revenue": 70000,
                    "net_income": 9000
                }
            ],
            "apply_outlier_filtering": False,
            "iqr_multiplier": 1.5,
            "outlier_metric": "ev_ebitda_ltm"
        }

    @pytest.fixture
    def sample_dupont_request(self):
        """Sample request data for DuPont endpoint"""
        return {
            "ticker": "VNM",
            "company_name": "Vinamilk",
            "exchange": "HOSE",
            "years": [2021, 2022, 2023],
            "financial_data_by_year": {
                "2023": {
                    "net_income": 12700,
                    "revenue": 85500,
                    "total_assets": 50500,
                    "shareholders_equity": 32300
                },
                "2022": {
                    "net_income": 11500,
                    "revenue": 80000,
                    "total_assets": 48000,
                    "shareholders_equity": 30000
                },
                "2021": {
                    "net_income": 10800,
                    "revenue": 75000,
                    "total_assets": 45000,
                    "shareholders_equity": 28000
                }
            },
            "custom_ratios": {}
        }

    def test_comps_route_structure(self, sample_comps_request):
        """Test that comps route has proper structure to call engine"""
        # This test verifies the route structure without actually calling the API
        from app.services.vietnamese import (
            VNTradingCompsAnalyzer,
            VNTargetCompanyData,
            VNPeerCompanyData
        )

        # Verify we can create the necessary data structures
        target = VNTargetCompanyData(
            ticker=sample_comps_request["target_ticker"],
            company_name=sample_comps_request["target_company_name"],
            market_cap_vnd=150000,
            enterprise_value_vnd=160000,
            ebitda_ltm_vnd=sample_comps_request["target_ebitda_vnd"],
            eps_ltm_vnd=sample_comps_request["target_eps_vnd"],
            net_debt_vnd=10000,
            shares_outstanding=1000,
            share_price_vnd=150,
            sector=sample_comps_request["sector"]
        )

        assert target.ticker == "VNM"
        assert target.sector == "Consumer Goods"

    def test_dupont_route_structure(self, sample_dupont_request):
        """Test that DuPont route has proper structure to call engine"""
        from app.services.vietnamese import VNDuPontAnalyzer, VNFinancialStatements

        # Verify we can create the necessary data structures
        statements = VNFinancialStatements()
        analyzer = VNDuPontAnalyzer()

        assert statements is not None
        assert analyzer is not None

        # Verify we can load data
        statements.revenue[0] = 85500
        analyzer.load_data(statements)

        # Verify we can calculate
        result = analyzer.calculate_all()
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])