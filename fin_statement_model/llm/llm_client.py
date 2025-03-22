import logging
import openai
import backoff
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

@dataclass
class LLMConfig:
    api_key: str
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1500
    timeout: int = 30
    max_retries: int = 3
    # base_url is no longer needed as the openai library handles the endpoint configuration.

class LLMClientError(Exception):
    """Base exception for LLM client errors."""
    pass

class LLMTimeoutError(LLMClientError):
    """Exception for timeout errors."""
    pass

class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the async LLM client with configuration."""
        self.config = config or LLMConfig(api_key="")
        openai.api_key = self.config.api_key

    @backoff.on_exception(
        backoff.expo,
        (Exception, LLMTimeoutError),
        max_tries=3,
        giveup=lambda e: isinstance(e, LLMTimeoutError)
    )
    async def _make_api_call(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Make the async API call to OpenAI with retry logic.

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
                timeout=self.config.timeout
            )

            if not response.get("choices"):
                logger.error("No suggestions received from OpenAI API")
                raise LLMClientError("No suggestions received from API")

            return response
        except Exception as e:
            if "timeout" in str(e).lower():
                logger.error("Async request timed out")
                raise LLMTimeoutError("Request timed out") from e
            logger.error("OpenAI async API request failed: %s", str(e))
            raise LLMClientError(f"API request failed: {str(e)}") from e

    async def get_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Get a completion result from the LLM using async API.

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
            logger.error("Error getting completion: %s", str(e))
            raise LLMClientError(f"Failed to get completion: {str(e)}") from e

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass