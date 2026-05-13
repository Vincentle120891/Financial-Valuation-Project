"""
Vietnamese Step 4: Model Selection Processor

Handles model selection for Vietnamese companies.
While the core logic is shared with International, this processor:
- Validates model availability for Vietnamese market
- Sets Vietnam-specific default configurations
- Ensures compatibility with Vietnamese engines
- Tracks input source (always "manual" for model selection)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class vn_ModelSelectionInput(BaseModel):
    """Input for Vietnamese model selection step."""
    session_id: str = Field(..., description="Session identifier")
    selected_models: list[str] = Field(
        ...,
        description="List of selected valuation models",
        examples=[["dcf"], ["comps"], ["dupont"], ["dcf", "comps"]]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "selected_models": ["dcf", "comps"]
            }
        }


class vn_ModelSelectionOutput(BaseModel):
    """Output from Vietnamese model selection step."""
    session_id: str = Field(..., description="Session identifier")
    selected_models: list[str] = Field(..., description="Confirmed selected models")
    model_configurations: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Vietnam-specific configurations for each selected model"
    )
    available_models: list[str] = Field(
        ...,
        description="All models available for Vietnamese market"
    )
    next_step: int = Field(..., description="Next step number (5)")
    input_sources: Dict[str, str] = Field(
        ...,
        description="Source tracking for model selection inputs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "selected_models": ["dcf", "comps"],
                "model_configurations": {
                    "dcf": {
                        "currency": "VND",
                        "default_forecast_years": 5,
                        "risk_free_rate_source": "vietnamese_government_bond"
                    },
                    "comps": {
                        "currency": "VND",
                        "default_peer_count": 5,
                        "market": "vietnam"
                    }
                },
                "available_models": ["dcf", "dupont", "comps"],
                "next_step": 5,
                "input_sources": {
                    "selected_models": "manual"
                }
            }
        }


class vn_Step4ModelProcessor:
    """
    Processor for Vietnamese Step 4: Model Selection

    Manages model selection specifically for Vietnamese companies,
    ensuring compatibility with Vietnamese valuation engines.
    """

    # Available models for Vietnamese market
    AVAILABLE_MODELS = ["dcf", "dupont", "comps"]

    # Vietnam-specific model configurations
    VN_MODEL_CONFIGS = {
        "dcf": {
            "currency": "VND",
            "currency_symbol": "₫",
            "default_forecast_years": 5,
            "risk_free_rate_source": "vietnamese_government_bond_10y",
            "market_premium_source": "vietnamese_emerging_market",
            "country_risk_premium": 0.035,  # 3.5% for Vietnam
            "tax_rate_default": 0.20,  # 20% corporate tax rate in Vietnam
            "engine_module": "app.services.vietnamese.vietnamese_dcf_engine"
        },
        "dupont": {
            "currency": "VND",
            "currency_symbol": "₫",
            "focus_metrics": ["roe", "profit_margin", "asset_turnover", "equity_multiplier"],
            "peer_comparison_enabled": True,
            "engine_module": "app.services.vietnamese.vietnamese_dupont_engine"
        },
        "comps": {
            "currency": "VND",
            "currency_symbol": "₫",
            "default_peer_count": 5,
            "market": "vietnam",
            "exchange_filters": ["HOSE", "HNX", "UPCOM"],
            "multiples": ["P/E", "P/B", "EV/EBITDA", "P/S", "PEG"],
            "liquidity_filter_days": 60,  # 60-day average volume for VN market
            "engine_module": "app.services.vietnamese.vietnamese_comps_engine"
        }
    }

    def __init__(self, session_service=None):
        """Initialize with session service dependency."""
        self.session_service = session_service
        logger.info("vn_Step4ModelProcessor initialized for Vietnamese market")

    async def process(self, input_data: vn_ModelSelectionInput) -> vn_ModelSelectionOutput:
        """
        Process Vietnamese model selection.

        Args:
            input_data: Model selection input with session and selected models

        Returns:
            Output with confirmed models and Vietnam-specific configurations

        Raises:
            ValueError: If invalid models selected or session not found
        """
        logger.info(f"Processing Vietnamese model selection for session {input_data.session_id}")

        # Validate selected models
        validated_models = self._validate_models(input_data.selected_models)

        # Build Vietnam-specific configurations for selected models
        model_configs = self._build_vn_configurations(validated_models)

        # Track input sources
        input_sources = {
            "selected_models": "manual"  # Model selection is always manual
        }

        # Update session state if session service available
        if self.session_service:
            await self._update_session_state(
                input_data.session_id,
                validated_models,
                model_configs,
                input_sources
            )

        return vn_ModelSelectionOutput(
            session_id=input_data.session_id,
            selected_models=validated_models,
            model_configurations=model_configs,
            available_models=self.AVAILABLE_MODELS.copy(),
            next_step=5,
            input_sources=input_sources
        )

    def _validate_models(self, selected_models: list[str]) -> list[str]:
        """
        Validate selected models against available Vietnamese models.

        Args:
            selected_models: List of model names to validate

        Returns:
            List of validated model names

        Raises:
            ValueError: If any model is not available for Vietnamese market
        """
        if not selected_models:
            raise ValueError("At least one valuation model must be selected")

        invalid_models = [m for m in selected_models if m not in self.AVAILABLE_MODELS]
        if invalid_models:
            raise ValueError(
                f"The following models are not available for Vietnamese market: {invalid_models}. "
                f"Available models: {self.AVAILABLE_MODELS}"
            )

        logger.info(f"Validated Vietnamese models: {selected_models}")
        return selected_models.copy()

    def _build_vn_configurations(self, models: list[str]) -> Dict[str, Dict[str, Any]]:
        """
        Build Vietnam-specific configurations for selected models.

        Args:
            models: List of validated model names

        Returns:
            Dictionary mapping model names to Vietnam-specific configurations
        """
        configs = {}
        for model in models:
            # Deep copy to avoid modifying class-level defaults
            configs[model] = self.VN_MODEL_CONFIGS[model].copy()
            logger.debug(f"Built VN configuration for model {model}: {configs[model]}")

        return configs

    async def _update_session_state(
        self,
        session_id: str,
        models: list[str],
        configs: Dict[str, Dict[str, Any]],
        sources: Dict[str, str]
    ) -> None:
        """
        Update session state with model selection data.

        Args:
            session_id: Session identifier
            models: Selected model names
            configs: Vietnam-specific model configurations
            sources: Input source tracking
        """
        try:
            # Store model selection in session
            await self.session_service.update_session(session_id, {
                "selected_models": models,
                "model_configurations": configs,
                "market": "vietnam",
                "current_step": 4,
                "step_4_completed": True
            })

            # Add input sources to audit trail
            await self.session_service.add_input_sources(session_id, sources)

            logger.info(f"Updated session {session_id} with Vietnamese model selection")
        except Exception as e:
            logger.error(f"Failed to update session state for model selection: {e}")
            # Don't raise - model selection itself succeeded

    def get_available_models(self) -> list[str]:
        """Get list of models available for Vietnamese market."""
        return self.AVAILABLE_MODELS.copy()

    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Vietnam-specific configuration for a model.

        Args:
            model_name: Name of the model

        Returns:
            Configuration dictionary or None if model not found
        """
        return self.VN_MODEL_CONFIGS.get(model_name)