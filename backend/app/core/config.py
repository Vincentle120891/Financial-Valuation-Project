"""
Application Configuration

Loads configuration from environment variables with sensible defaults.
Uses pydantic-settings for type validation and automatic env loading.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    
    app_name: str = Field(default="Valuation Engine API", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # API Settings
    api_prefix: str = Field(default="/api", description="API route prefix")
    api_root_path: Optional[str] = Field(default=None, description="Root path for API (for reverse proxy setups)")
    api_version: str = Field(default="v1", description="Current API version")
    cors_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    
    # =========================================================================
    # API KEYS
    # =========================================================================
    
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key for AI engine")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    qwen_api_key: Optional[str] = Field(default=None, description="Alibaba Qwen/DashScope API key")
    alpha_vantage_key: Optional[str] = Field(default=None, description="Alpha Vantage API key")
    
    # Aliases for different env var naming conventions
    google_gemini_api_key: Optional[str] = Field(default=None)
    dashscope_api_key: Optional[str] = Field(default=None)
    alpha_vantage_api_key: Optional[str] = Field(default=None)
    
    @property
    def effective_gemini_key(self) -> Optional[str]:
        """Get effective Gemini API key from multiple possible env vars."""
        return self.gemini_api_key or self.google_gemini_api_key
    
    @property
    def effective_qwen_key(self) -> Optional[str]:
        """Get effective Qwen API key from multiple possible env vars."""
        return self.qwen_api_key or self.dashscope_api_key
    
    @property
    def effective_alpha_vantage_key(self) -> Optional[str]:
        """Get effective Alpha Vantage API key from multiple possible env vars."""
        return self.alpha_vantage_key or self.alpha_vantage_api_key
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    session_ttl_hours: int = Field(default=24, description="Session TTL in hours")
    max_sessions_per_user: int = Field(default=10, description="Maximum sessions per user")
    
    # Redis settings (for production session store)
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    
    @property
    def use_redis(self) -> bool:
        """Check if Redis is configured for session storage."""
        return self.redis_url is not None or self.redis_host != "localhost"
    
    # =========================================================================
    # VALUATION ENGINE DEFAULTS
    # =========================================================================
    
    # DCF Defaults
    default_wacc: float = Field(default=0.08, description="Default WACC (8%)")
    default_terminal_growth: float = Field(default=0.02, description="Default terminal growth rate (2%)")
    default_tax_rate: float = Field(default=0.21, description="Default statutory tax rate (21%)")
    default_risk_free_rate: float = Field(default=0.045, description="Default risk-free rate (4.5%)")
    default_equity_risk_premium: float = Field(default=0.055, description="Default equity risk premium (5.5%)")
    default_forecast_years: int = Field(default=5, description="Default forecast period (5 years)")
    
    # DuPont Defaults
    dupont_analysis_years: int = Field(default=8, description="DuPont analysis period (8 years)")
    
    # Comps Defaults
    comps_min_peers: int = Field(default=3, description="Minimum peer companies for Comps")
    comps_max_peers: int = Field(default=10, description="Maximum peer companies for Comps")
    comps_outlier_std_threshold: float = Field(default=2.0, description="Outlier threshold in standard deviations")
    
    # =========================================================================
    # AI ENGINE SETTINGS
    # =========================================================================
    
    ai_fallback_enabled: bool = Field(default=True, description="Enable deterministic fallback when AI fails")
    ai_timeout_seconds: int = Field(default=30, description="AI API timeout in seconds")
    ai_max_retries: int = Field(default=3, description="Maximum retries for AI API calls")
    
    # =========================================================================
    # LOGGING SETTINGS
    # =========================================================================
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json, text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_rotation_mb: int = Field(default=10, description="Log rotation size in MB")
    log_backup_count: int = Field(default=5, description="Number of backup log files")
    
    # =========================================================================
    # RATE LIMITING (for future implementation)
    # =========================================================================
    
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window in seconds")
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def validate_api_keys(self) -> dict:
        """Validate and return status of all API keys."""
        return {
            "groq": self.groq_api_key is not None,
            "gemini": self.effective_gemini_key is not None,
            "qwen": self.effective_qwen_key is not None,
            "alpha_vantage": self.effective_alpha_vantage_key is not None,
        }
    
    def get_missing_api_keys(self) -> List[str]:
        """Return list of missing API keys."""
        status = self.validate_api_keys()
        return [key for key, present in status.items() if not present]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for FastAPI."""
    return settings
