import unittest
import asyncio # For async helper if needed
from unittest.mock import patch, MagicMock, AsyncMock

import httpx # For RequestError and HTTPStatusError

# Attempt to import the OllamaConnector
try:
    from jarules_agent.connectors.ollama_connector import OllamaConnector, OllamaApiError
    from jarules_agent.connectors.base_llm_connector import BaseLLMConnector
except ImportError:
    # This is to handle path issues if tests are run from a different working directory
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from jarules_agent.connectors.ollama_connector import OllamaConnector, OllamaApiError
    from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

# Helper for creating mock httpx.Response objects
def create_mock_response(status_code: int, json_data: dict = None, text_data: str = None, error: Exception = None):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json = MagicMock(return_value=json_data)
    if text_data is not None:
        mock_resp.text = text_data

    if status_code >= 400:
        mock_resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            message=f"Error: {status_code}", request=MagicMock(), response=mock_resp
        ))
    else:
        mock_resp.raise_for_status = MagicMock()

    return mock_resp

class TestOllamaConnector(unittest.IsolatedAsyncioTestCase): # Use IsolatedAsyncioTestCase for async tests
    """
    Test suite for the OllamaConnector.
    """

    def setUp(self):
        """
        Set up for test cases.
        This method is called before each test method.
        """
        self.base_config = {
            "api_base_url": "http://localhost:11434", # No trailing slash
            "model_name": "test_model_llama3",
            "default_system_prompt": "You are a test bot.",
            "generation_params": {"temperature": 0.5},
            "request_timeout": 10
        }
        # Patch the httpx.AsyncClient before creating an instance of the connector
        self.mock_async_client_patch = patch('httpx.AsyncClient', new_callable=AsyncMock)
        self.MockAsyncClient = self.mock_async_client_patch.start()
        self.mock_client_instance = self.MockAsyncClient.return_value # This is what self.client will be

        self.connector = OllamaConnector(config=self.base_config)

    async def asyncTearDown(self): # Renamed from tearDown for clarity with IsolatedAsyncioTestCase
        """
        Clean up after test cases.
        This method is called after each test method.
        """
        await self.connector.close() # Ensure client is closed
        self.mock_async_client_patch.stop()


    def test_ollama_connector_initialization_basic(self):
        """
        Test that the OllamaConnector initializes correctly with all params.
        """
        self.assertIsNotNone(self.connector, "Connector should not be None")
        self.assertIsInstance(self.connector, BaseLLMConnector, "Connector should be an instance of BaseLLMConnector")
        self.assertEqual(self.connector.api_base_url, self.base_config["api_base_url"])
        self.assertEqual(self.connector.model_name, self.base_config["model_name"])
        self.assertEqual(self.connector.default_system_prompt, self.base_config["default_system_prompt"])
        self.assertEqual(self.connector.generation_params, self.base_config["generation_params"])

        self.MockAsyncClient.assert_called_once_with(
            base_url=self.base_config["api_base_url"],
            timeout=self.base_config["request_timeout"]
        )
        self.assertTrue(hasattr(self.connector, "logger"), "Connector should have a logger attribute")

    def test_ollama_connector_initialization_minimal(self):
        """
        Test initialization with minimal config (relying on defaults).
        """
        minimal_config = {"api_base_url": "http://ollama.custom:12345/"} # With trailing slash

        # Need to stop the previous patch to re-instantiate with a new client mock for this specific test
        self.mock_async_client_patch.stop()
        mock_async_client_patch_minimal = patch('httpx.AsyncClient', new_callable=AsyncMock)
        MockAsyncClientMinimal = mock_async_client_patch_minimal.start()

        connector_minimal = OllamaConnector(config=minimal_config)

        self.assertEqual(connector_minimal.api_base_url, "http://ollama.custom:12345") # Slash should be removed
        self.assertEqual(connector_minimal.model_name, "llama3") # Default
        self.assertIsNone(connector_minimal.default_system_prompt) # Default
        self.assertEqual(connector_minimal.generation_params, {}) # Default

        MockAsyncClientMinimal.assert_called_once_with(
            base_url="http://ollama.custom:12345", # Base URL passed to client should have slash removed
            timeout=30 # Default timeout
        )
        mock_async_client_patch_minimal.stop()
        # Restore the main patch for other tests
        self.mock_async_client_patch.start()


    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_check_availability_success(self, mock_logger):
        """ Test check_availability success when model is found and Ollama is running. """
        # Mock response for /api/tags
        mock_tags_response = create_mock_response(200, json_data={
            "models": [
                {"name": "test_model_llama3:latest", "size": 1234},
                {"name": "another_model:7b", "size": 5678}
            ]
        })
        # Mock response for /
        mock_root_response = create_mock_response(200, text_data="Ollama is running")

        self.mock_client_instance.get.side_effect = [mock_tags_response, mock_root_response]

        result = await self.connector.check_availability()
        self.assertTrue(result)

        self.mock_client_instance.get.assert_any_call("/api/tags")
        self.mock_client_instance.get.assert_any_call("/")
        mock_logger.info.assert_any_call(f"Ollama API is available at {self.base_config['api_base_url']}. Configured model '{self.base_config['model_name']}' found: True.")


    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_check_availability_model_not_found_but_ollama_running(self, mock_logger):
        """ Test check_availability when model is not found but Ollama is running. """
        mock_tags_response = create_mock_response(200, json_data={"models": [{"name": "other_model:latest"}]})
        mock_root_response = create_mock_response(200, text_data="Ollama is running")
        self.mock_client_instance.get.side_effect = [mock_tags_response, mock_root_response]

        result = await self.connector.check_availability()
        self.assertTrue(result) # Still true because Ollama itself is running
        mock_logger.warning.assert_called_once_with(
            f"Configured model '{self.base_config['model_name']}' not found in available models: ['other_model:latest']. "
            f"Ollama is running, but the specific model might be missing."
        )
        mock_logger.info.assert_any_call(f"Ollama API is available at {self.base_config['api_base_url']}. Configured model '{self.base_config['model_name']}' found: False.")


    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_check_availability_tags_fails(self, mock_logger):
        """ Test check_availability when /api/tags call fails. """
        self.mock_client_instance.get.side_effect = httpx.RequestError("Connection failed", request=MagicMock())

        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_called_with(f"Error connecting to Ollama API at {self.base_config['api_base_url']}: Connection failed")

    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_check_availability_root_fails(self, mock_logger):
        """ Test check_availability when / call fails after /api/tags succeeds. """
        mock_tags_response = create_mock_response(200, json_data={"models": [{"name": "test_model_llama3:latest"}]})
        self.mock_client_instance.get.side_effect = [
            mock_tags_response,
            httpx.HTTPStatusError("Server error", request=MagicMock(), response=create_mock_response(500, text_data="Internal Server Error"))
        ]

        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_called_with("Ollama API request failed: 500 - Internal Server Error")

    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_check_availability_root_returns_not_ollama(self, mock_logger):
        """ Test check_availability when / returns unexpected text. """
        mock_tags_response = create_mock_response(200, json_data={"models": [{"name": "test_model_llama3:latest"}]})
        mock_root_response = create_mock_response(200, text_data="Something else is running here")
        self.mock_client_instance.get.side_effect = [mock_tags_response, mock_root_response]

        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_called_with(
            f"Ollama API root endpoint check failed. Status: 200, Response: Something else is running here"
        )

    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_check_availability_tags_invalid_json(self, mock_logger):
        """ Test check_availability when /api/tags returns invalid JSON. """
        mock_tags_response = create_mock_response(200, text_data="not json")
        # Override .json() to simulate json.JSONDecodeError
        mock_tags_response.json = MagicMock(side_effect=json.JSONDecodeError("decoding error", "doc", 0))
        self.mock_client_instance.get.return_value = mock_tags_response

        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_called_with("Failed to parse JSON response from Ollama /api/tags: decoding error: line 1 column 1 (char 0)")


    # Placeholder tests for other methods (to be implemented next)
    # @patch('jarules_agent.connectors.ollama_connector.logger') # Patching logger to check calls
    # async def test_generate_code_placeholder(self, mock_logger):
    async def test_generate_code_success(self):
        """ Test successful code generation. """
        mock_ollama_response_json = {
            "model": self.base_config["model_name"],
            "created_at": "2023-11-23T14:00:00Z",
            "response": "def hello_world():\n  print('Hello, Ollama!')",
            "done": True
        }
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        user_prompt = "Create a hello world function in Python."
        expected_code = "def hello_world():\n  print('Hello, Ollama!')"

        actual_code = await self.connector.generate_code(user_prompt, system_instruction="Be a helpful AI coder.")

        self.assertEqual(actual_code, expected_code)
        self.mock_client_instance.post.assert_called_once()
        args, kwargs = self.mock_client_instance.post.call_args
        self.assertEqual(args[0], "/api/generate")
        payload = kwargs['json']
        self.assertEqual(payload['model'], self.base_config['model_name'])
        self.assertIn(user_prompt, payload['prompt'])
        self.assertEqual(payload['system'], "Be a helpful AI coder.")
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['options'], self.base_config['generation_params'])

    async def test_generate_code_uses_default_system_prompt(self):
        """ Test generate_code uses default system prompt if none provided. """
        mock_ollama_response_json = {"response": "code"}
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        await self.connector.generate_code("prompt")
        _, kwargs = self.mock_client_instance.post.call_args
        self.assertEqual(kwargs['json']['system'], self.base_config['default_system_prompt'])

    async def test_generate_code_no_system_prompt_if_default_is_none(self):
        """ Test generate_code sends no system prompt if default is None and none provided. """
        self.connector.default_system_prompt = None # Override for this test
        mock_ollama_response_json = {"response": "code"}
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        await self.connector.generate_code("prompt")
        _, kwargs = self.mock_client_instance.post.call_args
        self.assertNotIn('system', kwargs['json'])


    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_generate_code_api_http_error(self, mock_logger):
        """ Test generate_code handling HTTPStatusError. """
        error_response = create_mock_response(500, text_data="Internal Server Error")
        self.mock_client_instance.post.return_value = error_response # side_effect is not needed if create_mock_response handles raise_for_status

        with self.assertRaises(OllamaApiError) as cm:
            await self.connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 500)
        self.assertIn("Ollama API error: 500", str(cm.exception))
        mock_logger.error.assert_called_with("Ollama API request failed for generate_code: 500 - Internal Server Error")

    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_generate_code_connection_error(self, mock_logger):
        """ Test generate_code handling RequestError (connection error). """
        self.mock_client_instance.post.side_effect = httpx.RequestError("Connection failed", request=MagicMock())

        with self.assertRaises(OllamaApiError) as cm:
            await self.connector.generate_code("prompt")
        self.assertIsNone(cm.exception.status_code)
        self.assertIn("Connection to Ollama failed", str(cm.exception))
        mock_logger.error.assert_called_with("Error connecting to Ollama API for generate_code: Connection failed")


    async def test_generate_code_empty_response(self):
        """ Test generate_code with an empty response from Ollama. """
        mock_ollama_response_json = {"response": "", "done": True}
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        response = await self.connector.generate_code("prompt")
        self.assertEqual(response, "")


    async def test_explain_code_success(self):
        """ Test successful code explanation. """
        mock_ollama_response_json = {"response": "This code does XYZ."}
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        code_snippet = "def foo(): pass"
        expected_explanation = "This code does XYZ."
        actual_explanation = await self.connector.explain_code(code_snippet)

        self.assertEqual(actual_explanation, expected_explanation)
        _, kwargs = self.mock_client_instance.post.call_args
        payload = kwargs['json']
        self.assertIn("Please explain the following code snippet", payload['prompt'])
        self.assertIn(code_snippet, payload['prompt'])
        self.assertEqual(payload['system'], "You are an expert code explainer. Provide clear and concise explanations.") # Default specific to explain

    async def test_explain_code_with_custom_system_instruction(self):
        """ Test explain_code with a custom system instruction. """
        mock_ollama_response_json = {"response": "Custom explanation."}
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        custom_instruction = "Explain like I'm five."
        await self.connector.explain_code("code", system_instruction=custom_instruction)
        _, kwargs = self.mock_client_instance.post.call_args
        self.assertEqual(kwargs['json']['system'], custom_instruction)


    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_explain_code_api_error(self, mock_logger):
        """ Test explain_code handling API errors. """
        error_response = create_mock_response(400, text_data="Bad Request")
        self.mock_client_instance.post.return_value = error_response

        with self.assertRaises(OllamaApiError) as cm:
            await self.connector.explain_code("code")
        self.assertEqual(cm.exception.status_code, 400)
        mock_logger.error.assert_called_with("Ollama API request failed for explain_code: 400 - Bad Request")


    async def test_suggest_code_modification_success(self):
        """ Test successful code modification suggestion. """
        mock_ollama_response_json = {"response": "def new_foo(): pass"}
        mock_api_response = create_mock_response(200, json_data=mock_ollama_response_json)
        self.mock_client_instance.post.return_value = mock_api_response

        code_snippet = "def old_foo(): pass"
        instruction = "Rename to new_foo"
        expected_suggestion = "def new_foo(): pass"
        actual_suggestion = await self.connector.suggest_code_modification(code_snippet, instruction)

        self.assertEqual(actual_suggestion, expected_suggestion)
        _, kwargs = self.mock_client_instance.post.call_args
        payload = kwargs['json']
        self.assertIn(code_snippet, payload['prompt'])
        self.assertIn(instruction, payload['prompt'])
        self.assertEqual(payload['system'], "You are an expert code modification assistant. Provide only the modified code or a clear description of changes if code modification isn't directly possible.")


    @patch('jarules_agent.connectors.ollama_connector.logger')
    async def test_suggest_code_modification_api_error(self, mock_logger):
        """ Test suggest_code_modification handling API errors. """
        error_response = create_mock_response(503, text_data="Service Unavailable")
        self.mock_client_instance.post.return_value = error_response

        with self.assertRaises(OllamaApiError) as cm:
            await self.connector.suggest_code_modification("code", "instruction")
        self.assertEqual(cm.exception.status_code, 503)
        mock_logger.error.assert_called_with("Ollama API request failed for suggest_code_modification: 503 - Service Unavailable")


if __name__ == '__main__':
    unittest.main()
