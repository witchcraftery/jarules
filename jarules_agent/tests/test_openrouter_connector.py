import unittest
import os
from unittest.mock import patch, AsyncMock, MagicMock

import httpx # For RequestError and HTTPStatusError

# Attempt to import the OpenRouterConnector
try:
    from jarules_agent.connectors.openrouter_connector import OpenRouterConnector, OpenRouterApiError
    from jarules_agent.connectors.base_llm_connector import BaseLLMConnector
except ImportError:
    # This is to handle path issues if tests are run from a different working directory
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from jarules_agent.connectors.openrouter_connector import OpenRouterConnector, OpenRouterApiError
    from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

# Helper for creating mock httpx.Response objects (can be shared or duplicated)
def create_mock_response(status_code: int, json_data: dict = None, text_data: str = None):
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

class TestOpenRouterConnector(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the OpenRouterConnector.
    """

    def setUp(self):
        """
        Set up for test cases.
        This method is called before each test method.
        """
        self.api_key_env_var_name = "TEST_OPENROUTER_API_KEY"
        self.mock_api_key = "test_openrouter_key_12345"

        self.base_config = {
            "api_key_env_var": self.api_key_env_var_name,
            "model_name": "test/default-model",
            "api_base_url": "https://test.openrouter.ai/api/v1",
            "default_system_prompt": "You are a test OpenRouter bot.",
            "generation_params": {"temperature": 0.6, "max_tokens": 500},
            "request_timeout": 20,
            "http_referer": "https://mytestsite.com"
        }

        # Patch os.environ to control the API key for tests
        self.env_patch = patch.dict(os.environ, {self.api_key_env_var_name: self.mock_api_key})
        self.env_patch.start()

        # Patch the httpx.AsyncClient
        self.mock_async_client_patch = patch('httpx.AsyncClient', new_callable=AsyncMock)
        self.MockAsyncClient = self.mock_async_client_patch.start()
        self.mock_client_instance = self.MockAsyncClient.return_value

        self.connector = OpenRouterConnector(config=self.base_config)

    async def asyncTearDown(self):
        """
        Clean up after test cases.
        This method is called after each test method.
        """
        await self.connector.close() # Ensure client is closed
        self.mock_async_client_patch.stop()
        self.env_patch.stop()

    def test_openrouter_connector_initialization(self):
        """
        Test that the OpenRouterConnector initializes correctly.
        """
        self.assertIsNotNone(self.connector, "Connector should not be None")
        self.assertIsInstance(self.connector, BaseLLMConnector, "Connector should be an instance of BaseLLMConnector")
        self.assertEqual(self.connector.api_key, self.mock_api_key)
        self.assertEqual(self.connector.model_name, self.base_config["model_name"])
        self.assertEqual(self.connector.api_base_url, self.base_config["api_base_url"])

        expected_headers = {
            "Authorization": f"Bearer {self.mock_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.base_config["http_referer"],
        }
        self.MockAsyncClient.assert_called_once_with(
            base_url=self.base_config["api_base_url"],
            headers=expected_headers,
            timeout=self.base_config["request_timeout"]
        )
        self.assertTrue(hasattr(self.connector, "logger"), "Connector should have a logger attribute")

    def test_initialization_missing_api_key(self):
        """ Test connector initialization fails if API key environment variable is not set. """
        # Stop the main env_patch for this test
        self.env_patch.stop()

        # Ensure the key is not in os.environ for this specific test context
        current_env = os.environ.copy()
        if self.api_key_env_var_name in current_env:
            del current_env[self.api_key_env_var_name]

        with patch.dict(os.environ, current_env, clear=True):
            with self.assertRaisesRegex(ValueError, f"API key not found. Set the {self.api_key_env_var_name} environment variable."):
                OpenRouterConnector(config=self.base_config)

        # Restart the main patch for other tests if it's not the last test for this instance
        # Note: setUp and tearDown handle this per test method in IsolatedAsyncioTestCase
        # self.env_patch.start() # No need to restart here due to per-test setup/teardown

    @patch('jarules_agent.connectors.openrouter_connector.logger')
    async def test_check_availability_success_with_models_endpoint(self, mock_logger):
        """ Test check_availability success using /models endpoint. """
        mock_response = create_mock_response(200, json_data={"data": [{"id": "some_model"}]})
        self.mock_client_instance.get.return_value = mock_response

        result = await self.connector.check_availability()
        self.assertTrue(result)
        self.mock_client_instance.get.assert_called_once_with("/models")
        mock_logger.info.assert_called_with("OpenRouter API is available and API key appears valid.")

    @patch('jarules_agent.connectors.openrouter_connector.logger')
    async def test_check_availability_fallback_success(self, mock_logger):
        """ Test check_availability success using fallback chat completion. """
        # First call to /models fails (e.g. 403), second call to /chat/completions succeeds
        mock_models_fail_response = create_mock_response(403, text_data="Forbidden")
        mock_chat_success_response = create_mock_response(200, json_data={
            "choices": [{"message": {"content": "test response"}}]
        })
        self.mock_client_instance.get.return_value = mock_models_fail_response
        self.mock_client_instance.post.return_value = mock_chat_success_response

        result = await self.connector.check_availability()
        self.assertTrue(result)
        self.mock_client_instance.get.assert_called_once_with("/models")
        self.mock_client_instance.post.assert_called_once()
        args_post, kwargs_post = self.mock_client_instance.post.call_args
        self.assertEqual(args_post[0], "/chat/completions")
        self.assertEqual(kwargs_post['json']['model'], self.base_config['model_name']) # Uses configured model
        mock_logger.info.assert_called_with("OpenRouter API is available and API key appears valid.")

    @patch('jarules_agent.connectors.openrouter_connector.logger')
    async def test_check_availability_fails_unauthorized(self, mock_logger):
        """ Test check_availability failure on 401 Unauthorized for both attempts. """
        mock_models_unauth_response = create_mock_response(401, text_data="Unauthorized")
        # Assume fallback chat completion also results in 401
        mock_chat_unauth_response = create_mock_response(401, text_data="Unauthorized")

        self.mock_client_instance.get.return_value = mock_models_unauth_response
        self.mock_client_instance.post.return_value = mock_chat_unauth_response

        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_any_call("OpenRouter API key is invalid or not authorized. Status: 401")


    @patch('jarules_agent.connectors.openrouter_connector.logger')
    async def test_check_availability_connection_error(self, mock_logger):
        """ Test check_availability failure on connection error. """
        self.mock_client_instance.get.side_effect = httpx.RequestError("Connection failed", request=MagicMock())
        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_called_with("Error connecting to OpenRouter for availability check: Connection failed")

    async def test_generate_code_success(self):
        """ Test successful code generation. """
        expected_response_content = "def hello():\n  print('Hello from OpenRouter!')"
        mock_api_response_json = {
            "choices": [{"message": {"role": "assistant", "content": expected_response_content}}]
        }
        self.mock_client_instance.post.return_value = create_mock_response(200, json_data=mock_api_response_json)

        user_prompt = "Write a Python hello function."
        context = "This is for a tutorial."
        system_instruction = "Be very creative."

        actual_code = await self.connector.generate_code(user_prompt, system_instruction=system_instruction, context=context)
        self.assertEqual(actual_code, expected_response_content)

        self.mock_client_instance.post.assert_called_once()
        args, kwargs = self.mock_client_instance.post.call_args
        self.assertEqual(args[0], "/chat/completions")
        payload = kwargs['json']
        self.assertEqual(payload['model'], self.base_config['model_name'])
        self.assertEqual(len(payload['messages']), 2)
        self.assertEqual(payload['messages'][0]['role'], "system")
        self.assertEqual(payload['messages'][0]['content'], system_instruction)
        self.assertEqual(payload['messages'][1]['role'], "user")
        self.assertIn(user_prompt, payload['messages'][1]['content'])
        self.assertIn(context, payload['messages'][1]['content'])
        # Check if generation_params from config are included
        for k, v in self.base_config['generation_params'].items():
            self.assertEqual(payload[k], v)


    async def test_generate_code_uses_default_system_prompt(self):
        """ Test generate_code uses default system prompt if no specific one is given. """
        self.mock_client_instance.post.return_value = create_mock_response(200, json_data={
            "choices": [{"message": {"content": "some code"}}]
        })
        await self.connector.generate_code("prompt")
        _, kwargs = self.mock_client_instance.post.call_args
        self.assertEqual(kwargs['json']['messages'][0]['content'], self.base_config['default_system_prompt'])

    async def test_generate_code_no_system_prompt_if_default_is_none(self):
        """ Test generate_code sends no system message if default and specific are None. """
        self.connector.default_system_prompt = None # Override for this test
        self.mock_client_instance.post.return_value = create_mock_response(200, json_data={
            "choices": [{"message": {"content": "some code"}}]
        })
        await self.connector.generate_code("prompt")
        _, kwargs = self.mock_client_instance.post.call_args
        self.assertTrue(all(msg['role'] != 'system' for msg in kwargs['json']['messages']))


    @patch('jarules_agent.connectors.openrouter_connector.logger')
    async def test_generate_code_api_error_handling(self, mock_logger):
        """ Test API error handling in generate_code. """
        error_message = "Insufficient credits"
        mock_error_response = create_mock_response(402, json_data={"error": {"message": error_message, "type": "credits"}})
        self.mock_client_instance.post.return_value = mock_error_response

        with self.assertRaises(OpenRouterApiError) as cm:
            await self.connector.generate_code("prompt")

        self.assertEqual(cm.exception.status_code, 402)
        self.assertIn(error_message, str(cm.exception))
        mock_logger.error.assert_called_with(f"OpenRouter API request failed: 402 - {error_message}")


    async def test_explain_code_success(self):
        """ Test successful code explanation. """
        expected_explanation = "This Python code defines a simple function."
        self.mock_client_instance.post.return_value = create_mock_response(200, json_data={
            "choices": [{"message": {"content": expected_explanation}}]
        })

        actual_explanation = await self.connector.explain_code("def foo(): pass")
        self.assertEqual(actual_explanation, expected_explanation)

        _, kwargs = self.mock_client_instance.post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['messages'][0]['role'], "system")
        self.assertEqual(payload['messages'][0]['content'], "You are an expert code explainer. Provide clear and concise explanations for the given code.") # Default for explain
        self.assertIn("Please explain the following code snippet", payload['messages'][1]['content'])


    async def test_suggest_code_modification_success(self):
        """ Test successful code modification suggestion. """
        expected_suggestion = "def bar(): # renamed\n  pass"
        self.mock_client_instance.post.return_value = create_mock_response(200, json_data={
            "choices": [{"message": {"content": expected_suggestion}}]
        })

        actual_suggestion = await self.connector.suggest_code_modification("def foo(): pass", "rename to bar")
        self.assertEqual(actual_suggestion, expected_suggestion)

        _, kwargs = self.mock_client_instance.post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['messages'][0]['role'], "system")
        self.assertEqual(payload['messages'][0]['content'], "You are an expert code modification assistant. Given a code snippet and an instruction, provide the modified code or a clear description of changes.") # Default for suggest
        self.assertIn("Instruction for modification: rename to bar", payload['messages'][1]['content'])


    @patch('jarules_agent.connectors.openrouter_connector.logger')
    async def test_invalid_response_structure(self, mock_logger):
        """ Test handling of unexpected JSON structure from OpenRouter. """
        self.mock_client_instance.post.return_value = create_mock_response(200, json_data={"unexpected_field": "no_choices_here"})
        with self.assertRaisesRegex(OpenRouterApiError, "Invalid response structure from OpenRouter."):
            await self.connector.generate_code("prompt")
        mock_logger.error.assert_called_with("Invalid response structure from OpenRouter: {'unexpected_field': 'no_choices_here'}")


if __name__ == '__main__':
    unittest.main()
