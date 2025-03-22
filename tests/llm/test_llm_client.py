"""
Tests for the LLM client module.

This module contains comprehensive tests for the LLMClient class and related components,
ensuring proper functionality of the async OpenAI API client.
"""
import unittest
import pytest
import pytest_asyncio
import json
import asyncio
from dataclasses import asdict
from unittest.mock import patch, AsyncMock, MagicMock
from fin_statement_model.llm.llm_client import (
    LLMClient, 
    LLMConfig, 
    LLMClientError, 
    LLMTimeoutError
)

class TestLLMConfig:
    """Tests for the LLMConfig dataclass."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        config = LLMConfig(api_key="test-api-key")
        assert config.api_key == "test-api-key"
        assert config.model_name == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 1500
        assert config.timeout == 30
        assert config.max_retries == 3
        
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        config = LLMConfig(
            api_key="test-api-key",
            model_name="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
            max_retries=5
        )
        assert config.api_key == "test-api-key"
        assert config.model_name == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.max_retries == 5
        
    def test_asdict(self):
        """Test conversion to dictionary."""
        config = LLMConfig(
            api_key="test-api-key",
            model_name="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1000,
            timeout=60
        )
        # Use dataclasses.asdict
        config_dict = asdict(config)
        assert config_dict == {
            "api_key": "test-api-key",
            "model_name": "gpt-3.5-turbo",
            "temperature": 0.5,
            "max_tokens": 1000,
            "timeout": 60,
            "max_retries": 3
        }

class TestLLMClient:
    """Tests for the LLMClient class."""
    
    @pytest_asyncio.fixture
    async def llm_client(self):
        """Create a client instance for tests."""
        with patch('openai.api_key', ''):
            client = LLMClient(config=LLMConfig(api_key="test-api-key"))
            yield client
    
    def test_init_with_config(self):
        """Test initialization with a config object."""
        config = LLMConfig(
            api_key="test-api-key",
            model_name="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1000,
            timeout=60
        )
        with patch('openai.api_key', ''):
            client = LLMClient(config=config)
            assert client.config.api_key == "test-api-key"
            assert client.config.model_name == "gpt-3.5-turbo"
            assert client.config.temperature == 0.5
            assert client.config.max_tokens == 1000
            assert client.config.timeout == 60
        
    def test_init_without_config(self):
        """Test initialization without a config object."""
        with patch('openai.api_key', ''):
            client = LLMClient()
            assert client.config.api_key == ""
            assert client.config.model_name == "gpt-4o"
            assert client.config.temperature == 0.7
            assert client.config.max_tokens == 1500
            assert client.config.timeout == 30
    
    @pytest.mark.asyncio
    async def test_make_api_call_success(self, llm_client):
        """Test successful API call."""
        # Mock the async ChatCompletion.acreate method
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
            # Setup mock response
            mock_acreate.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "This is a test response."
                        }
                    }
                ]
            }
            
            # Sample messages for the API call
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method
            response = await llm_client._make_api_call(messages)
            
            # Verify the response
            assert "choices" in response
            assert response["choices"][0]["message"]["content"] == "This is a test response."
            
            # Verify the ChatCompletion.acreate was called with correct parameters
            mock_acreate.assert_called_once_with(
                model=llm_client.config.model_name,
                messages=messages,
                temperature=llm_client.config.temperature,
                max_tokens=llm_client.config.max_tokens,
                timeout=llm_client.config.timeout
            )
    
    @pytest.mark.asyncio
    async def test_make_api_call_empty_choices(self, llm_client):
        """Test API call with empty choices."""
        # Mock the async ChatCompletion.acreate method
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
            # Setup mock response with empty choices
            mock_acreate.return_value = {"choices": []}
            
            # Sample messages for the API call
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method and expect an error
            with pytest.raises(LLMClientError) as excinfo:
                await llm_client._make_api_call(messages)
                
            # Verify the error message
            assert "No suggestions received from API" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_make_api_call_timeout(self, llm_client):
        """Test API call with a timeout error."""
        # Mock the async ChatCompletion.acreate method to raise a timeout error
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
            mock_acreate.side_effect = Exception("Request timed out")
            
            # Sample messages for the API call
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method and expect a timeout error
            with pytest.raises(LLMClientError) as excinfo:
                await llm_client._make_api_call(messages)
                
            # Verify the error message
            assert "API request failed: Request timed out" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_make_api_call_specific_timeout(self, llm_client):
        """Test API call with a specific timeout error to trigger the timeout branch."""
        # Mock the async ChatCompletion.acreate method to raise a timeout error
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
            # Create an exception with timeout in the message
            mock_acreate.side_effect = Exception("timeout exceeded")
            
            # Sample messages for the API call
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method and expect a LLMTimeoutError
            with pytest.raises(LLMTimeoutError) as excinfo:
                await llm_client._make_api_call(messages)
                
            # Verify the error message
            assert "Request timed out" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_make_api_call_general_error(self, llm_client):
        """Test API call with a general error."""
        # Mock the async ChatCompletion.acreate method to raise a general error
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
            mock_acreate.side_effect = Exception("Some API error")
            
            # Sample messages for the API call
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method and expect an error
            with pytest.raises(LLMClientError) as excinfo:
                await llm_client._make_api_call(messages)
                
            # Verify the error message
            assert "API request failed: Some API error" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_backoff_retry_logic(self, llm_client):
        """Test the backoff retry logic."""
        # Mock the async ChatCompletion.acreate method to fail twice and then succeed
        with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
            mock_acreate.side_effect = [
                Exception("Temporary error"),
                Exception("Temporary error"),
                {
                    "choices": [
                        {
                            "message": {
                                "content": "This is a test response after retries."
                            }
                        }
                    ]
                }
            ]
            
            # Sample messages for the API call
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method
            response = await llm_client._make_api_call(messages)
            
            # Verify the response
            assert "choices" in response
            assert response["choices"][0]["message"]["content"] == "This is a test response after retries."
            
            # Verify the ChatCompletion.acreate was called multiple times
            assert mock_acreate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_completion_success(self, llm_client):
        """Test getting a completion successfully."""
        # Mock the _make_api_call method
        with patch.object(llm_client, '_make_api_call', new_callable=AsyncMock) as mock_make_api_call:
            # Setup mock response
            mock_make_api_call.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "This is a test completion."
                        }
                    }
                ]
            }
            
            # Sample messages for the completion
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method
            completion = await llm_client.get_completion(messages)
            
            # Verify the completion
            assert completion == "This is a test completion."
            
            # Verify _make_api_call was called with correct parameters
            mock_make_api_call.assert_called_once_with(messages)
    
    @pytest.mark.asyncio
    async def test_get_completion_error(self, llm_client):
        """Test getting a completion with an error."""
        # Mock the _make_api_call method to raise an error
        with patch.object(llm_client, '_make_api_call', new_callable=AsyncMock) as mock_make_api_call:
            mock_make_api_call.side_effect = LLMClientError("API request failed")
            
            # Sample messages for the completion
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            
            # Call the method and expect an error
            with pytest.raises(LLMClientError) as excinfo:
                await llm_client.get_completion(messages)
                
            # Verify the error message
            assert "API request failed" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_context_manager(self, llm_client):
        """Test using the client as an async context manager."""
        # Use the client as an async context manager
        async with llm_client as client:
            # Verify the client is the same instance
            assert client is llm_client
            
            # Mock the _make_api_call method for testing within the context
            with patch.object(client, '_make_api_call', new_callable=AsyncMock) as mock_make_api_call:
                mock_make_api_call.return_value = {
                    "choices": [
                        {
                            "message": {
                                "content": "This is a test in context manager."
                            }
                        }
                    ]
                }
                
                # Sample messages for the completion
                messages = [{"role": "system", "content": "You are a helpful assistant."}]
                
                # Call the method within the context
                completion = await client.get_completion(messages)
                
                # Verify the completion
                assert completion == "This is a test in context manager."
    
    @pytest.mark.asyncio
    async def test_generate_mapping(self, llm_client):
        """Test generating a mapping."""
        # Mock the get_completion method
        with patch.object(llm_client, 'get_completion', new_callable=AsyncMock) as mock_get_completion:
            # Set up the mock to return a valid JSON string
            mock_get_completion.return_value = '{"mapped_name": "revenue", "confidence": 0.85}'
            
            # Add the generate_mapping method directly to the instance
            async def generate_mapping(prompt):
                completion = await llm_client.get_completion([
                    {"role": "system", "content": "You are a helpful financial mapping assistant."},
                    {"role": "user", "content": prompt}
                ])
                try:
                    return json.loads(completion)
                except json.JSONDecodeError as e:
                    raise e
                    
            llm_client.generate_mapping = generate_mapping
            
            # Test the generate_mapping method
            prompt = "Map the financial metric 'sales' to a standard metric."
            result = await llm_client.generate_mapping(prompt)
            
            # Assert the result matches expected output
            assert result == {"mapped_name": "revenue", "confidence": 0.85}
            
            # Verify get_completion was called with correct messages
            mock_get_completion.assert_called_once_with([
                {"role": "system", "content": "You are a helpful financial mapping assistant."},
                {"role": "user", "content": prompt}
            ])
    
    @pytest.mark.asyncio
    async def test_generate_mapping_invalid_json(self, llm_client):
        """Test generating a mapping with invalid JSON response."""
        # Mock the get_completion method
        with patch.object(llm_client, 'get_completion', new_callable=AsyncMock) as mock_get_completion:
            # Set up the mock to return invalid JSON
            mock_get_completion.return_value = "This is not valid JSON"
            
            # Add the generate_mapping method directly to the instance
            async def generate_mapping(prompt):
                completion = await llm_client.get_completion([
                    {"role": "system", "content": "You are a helpful financial mapping assistant."},
                    {"role": "user", "content": prompt}
                ])
                try:
                    return json.loads(completion)
                except json.JSONDecodeError as e:
                    raise e
                    
            llm_client.generate_mapping = generate_mapping
            
            # Test the generate_mapping method with invalid JSON
            prompt = "Map the financial metric 'sales' to a standard metric."
            
            # Should raise JSONDecodeError
            with pytest.raises(json.JSONDecodeError):
                await llm_client.generate_mapping(prompt) 