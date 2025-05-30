"""LLM client module for OpenAI and backoff integration.

This module provides `LLMConfig` for client configuration and `LLMClient` for
asynchronous interactions with OpenAI's ChatCompletion API, including retry logic.
"""

import logging
import openai
import backoff
from dataclasses import dataclass
from typing import Optional, Any
from types import TracebackType

from fin_statement_model.core.errors import FinancialModelError

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration data for LLMClient.

    Attributes:
        api_key: API key for OpenAI authentication.
        model_name: Model to use (e.g., 'gpt-4o').
        temperature: Sampling temperature setting.
        max_tokens: Maximum tokens to generate.
        timeout: Request timeout in seconds.
        max_retries: Number of retries on failure.
    """

    api_key: str
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1500
    timeout: int = 30
    max_retries: int = 3
    # base_url is no longer needed as the openai library handles the endpoint configuration.


class LLMClientError(FinancialModelError):
    """Base exception for LLM client errors."""


class LLMTimeoutError(LLMClientError):
    """Exception for timeout errors."""


class LLMClient:
    """Asynchronous client for OpenAI ChatCompletion API with retry logic.

    Utilizes `LLMConfig` and supports retries on rate limits and timeouts.

    Methods:
        _make_api_call: Internal method for performing the API call with retry logic.
        get_completion: High-level method to obtain chat completions.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the async LLM client with configuration."""
        self.config = config or LLMConfig(api_key="")
        openai.api_key = self.config.api_key

    @backoff.on_exception(
        backoff.expo,
        (Exception, LLMTimeoutError),
        max_tries=3,
        giveup=lambda e: isinstance(e, LLMTimeoutError),
    )
    @backoff.on_exception(backoff.expo, openai.RateLimitError, max_tries=8)
    async def _make_api_call(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Make the async API call to OpenAI with retry logic.

        Args:
            messages: List of message dicts for the ChatCompletion API

        Returns:
            Dict containing the API response

        Raises:
            LLMClientError: For any client-related errors, including timeout if applicable
        """
        try:
            logger.debug(f"Sending async request to OpenAI API with model {self.config.model_name}")
            response = await openai.ChatCompletion.acreate(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
            )

            if not response.get("choices"):
                logger.error("No suggestions received from OpenAI API")
                raise LLMClientError("No suggestions received from API")

            return response
        except Exception as e:
            if "timeout" in str(e).lower():
                logger.exception("Async request timed out")
                raise LLMTimeoutError("Request timed out") from e
            logger.exception("OpenAI async API request failed")
            raise LLMClientError(f"API request failed: {e!s}") from e

    async def get_completion(self, messages: list[dict[str, str]]) -> str:
        """Get a completion result from the LLM using async API.

        Args:
            messages: List of message dictionaries for the ChatCompletion API

        Returns:
            str: The suggested completion from the LLM

        Raises:
            LLMClientError: For any client-related errors
        """
        try:
            logger.info("Requesting completion from OpenAI async API")
            response = await self._make_api_call(messages)
            completion = response["choices"][0]["message"]["content"].strip()
            logger.info("Successfully received completion")
            return completion
        except Exception as e:
            logger.exception("Error getting completion")
            raise LLMClientError(f"Failed to get completion: {e!s}") from e

    async def __aenter__(self) -> "LLMClient":
        """Enter the asynchronous context manager, returning the client."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        """Exit the asynchronous context manager, performing cleanup."""
        # Ensure method has a body
