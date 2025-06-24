"""APIConfig sub-model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["APIConfig"]


class APIConfig(BaseModel):
    """Settings for external API integrations."""

    fmp_api_key: str | None = Field(None, description="Financial Modeling Prep API key")
    fmp_base_url: str = Field("https://financialmodelingprep.com/api/v3", description="FMP API base URL")
    api_timeout: int = Field(30, description="API request timeout in seconds")
    api_retry_count: int = Field(3, description="Number of retries for failed API requests")
    cache_api_responses: bool = Field(True, description="Cache API responses to reduce API calls")
    cache_ttl_hours: int = Field(24, description="Cache time-to-live in hours")

    @field_validator("api_timeout", "api_retry_count", "cache_ttl_hours")
    @classmethod
    def _validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    model_config = ConfigDict(extra="forbid")
