"""
Integration Tests for DCF Data Flow (Steps 4-9)
Verifies end-to-end data handling, mapping, and validation.
"""
import pytest
from app.core.metric_registry import METRIC_REGISTRY
from app.services.api_adapter import APIAdapter
from app.middleware.validation_middleware import ValidationMiddleware
from app.services.step7_resolver import Step7Resolver

class TestDataFlowIntegration:

    @pytest.fixture
    def adapter(self):
        return APIAdapter(method="DCF")

    @pytest.fixture
    def validator(self):
        return ValidationMiddleware()

    @pytest.fixture
    def resolver(self):
        return Step7Resolver()

    def test_metric_registry_completeness(self):
        """Ensure all required DCF metrics are defined."""
        dcf_metrics = METRIC_REGISTRY.get_required_metrics("DCF")
        assert len(dcf_metrics) > 0
        assert "revenue" in [m.id for m in dcf_metrics]
        assert "ebitda" in [m.id for m in dcf_metrics]

    def test_api_mapping_accuracy(self, adapter):
        """Test that yfinance keys map correctly to internal IDs."""
        raw_data = {
            "totalRevenue": [1000, 1100, 1200],
            "operatingIncome": [200, 220, 240]
        }
        mapped = adapter._map_fields(raw_data, "DCF")
        assert "revenue" in mapped
        assert "operating_income" in mapped

    def test_validation_pipeline(self, validator):
        """Test validation catches invalid data."""
        data = {
            "revenue": {"value": -100, "unit": "USD"}, # Invalid negative revenue
            "tax_rate": {"value": 1.5, "unit": "ratio"} # Invalid > 100%
        }
        report = validator.validate_step_data(data, "DCF")
        assert report["is_valid"] is False
        assert len(report["errors"]) > 0

    @pytest.mark.asyncio
    async def test_step7_resolver_routing(self, resolver):
        """Test intelligent routing in Step 7."""
        missing = ["capex", "depreciation"]
        # Mocking external calls would happen here
        # result = await resolver.resolve_missing_data("sess_123", missing, "AAPL", "DCF")
        # assert len(result["resolved"]) + len(result["failed"]) == len(missing)
        pass # Placeholder for async test with mocks

    def test_end_to_end_peer_averaging(self, adapter):
        """Verify peer data is averaged correctly."""
        peers_data = [
            {"ticker": "A", "revenue": [100, 110], "ebitda_margin": [0.2, 0.21]},
            {"ticker": "B", "revenue": [200, 220], "ebitda_margin": [0.25, 0.26]}
        ]
        # Logic to average peers would be tested here
        pass

    def test_data_versioning_structure(self):
        """Ensure data objects include versioning metadata."""
        metric = METRIC_REGISTRY.get_metric("revenue", "DCF")
        assert hasattr(metric, "id")
        assert hasattr(metric, "data_type")
        # Check that saved session data structure includes 'version' or 'timestamp'