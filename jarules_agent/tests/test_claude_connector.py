import unittest
import os
from unittest.mock import patch, AsyncMock, MagicMock

# Attempt to import the ClaudeConnector and related classes
try:
    from jarules_agent.connectors.claude_connector import ClaudeConnector, ClaudeApiError
    from jarules_agent.connectors.base_llm_connector import BaseLLMConnector
    # Assuming anthropic might be used for type hinting or specific exceptions in future
    import anthropic
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from jarules_agent.connectors.claude_connector import ClaudeConnector, ClaudeApiError
    from jarules_agent.connectors.base_llm_connector import BaseLLMConnector
    import anthropic


class TestClaudeConnector(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the ClaudeConnector.
    """

    def setUp(self):
        """
        Set up for test cases.
        This method is called before each test method.
        """
        self.api_key_env_var_name = "TEST_ANTHROPIC_API_KEY"
        self.mock_api_key = "test_claude_api_key_xxxxxxxx"

        self.base_config = {
            "api_key_env_var": self.api_key_env_var_name,
            "model_name": "claude-3-test-model-20240101",
            "default_system_prompt": "You are a test Claude bot.",
            "max_tokens": 1024,
            "request_timeout": 45,
            "anthropic_version_header": "2023-06-01" # Test with this header
        }

        # Patch os.environ to control the API key for tests
        self.env_patch = patch.dict(os.environ, {self.api_key_env_var_name: self.mock_api_key})
        self.env_patch.start()

        # Patch the anthropic.AsyncAnthropic client
        self.mock_anthropic_client_patch = patch('anthropic.AsyncAnthropic', new_callable=AsyncMock)
        self.MockAsyncAnthropicClient = self.mock_anthropic_client_patch.start()
        # Configure the mock client instance that will be returned by AsyncAnthropic()
        self.mock_client_instance = self.MockAsyncAnthropicClient.return_value
        # Ensure the client has an aclose method, also an AsyncMock
        self.mock_client_instance.aclose = AsyncMock()


        self.connector = ClaudeConnector(config=self.base_config)

    async def asyncTearDown(self):
        """
        Clean up after test cases.
        This method is called after each test method.
        """
        if self.connector: # Ensure connector was successfully created
            await self.connector.close()
        self.mock_anthropic_client_patch.stop()
        self.env_patch.stop()

    def test_claude_connector_initialization(self):
        """
        Test that the ClaudeConnector initializes correctly.
        """
        self.assertIsNotNone(self.connector, "Connector should not be None")
        self.assertIsInstance(self.connector, BaseLLMConnector, "Connector should be an instance of BaseLLMConnector")
        self.assertEqual(self.connector.api_key, self.mock_api_key)
        self.assertEqual(self.connector.model_name, self.base_config["model_name"])
        self.assertEqual(self.connector.max_tokens, self.base_config["max_tokens"])

        expected_custom_headers = {"anthropic-version": self.base_config["anthropic_version_header"]}
        self.MockAsyncAnthropicClient.assert_called_once_with(
            api_key=self.mock_api_key,
            timeout=self.base_config["request_timeout"],
            custom_headers=expected_custom_headers
        )
        self.assertTrue(hasattr(self.connector, "logger"), "Connector should have a logger attribute")

    def test_initialization_missing_api_key(self):
        """ Test connector initialization fails if API key environment variable is not set. """
        self.env_patch.stop() # Stop the main env_patch for this test

        current_env = os.environ.copy()
        if self.api_key_env_var_name in current_env:
            del current_env[self.api_key_env_var_name]

        with patch.dict(os.environ, current_env, clear=True):
            with self.assertRaisesRegex(ValueError, f"API key not found. Set the {self.api_key_env_var_name} environment variable."):
                # Need to ensure the client isn't called if API key is missing
                self.mock_anthropic_client_patch.stop() # Stop patch for this specific sub-test
                ClaudeConnector(config=self.base_config)
                self.mock_anthropic_client_patch.start() # Restart for other tests

    def test_initialization_anthropic_client_fails(self):
        """ Test connector initialization fails if Anthropic client instantiation fails. """
        self.mock_anthropic_client_patch.stop() # Stop the successful patch

        failing_client_patch = patch('anthropic.AsyncAnthropic', side_effect=anthropic.APIConnectionError("Connection Failed"))
        MockFailingClient = failing_client_patch.start()

        with self.assertRaisesRegex(ClaudeApiError, "Anthropic client initialization failed: Connection Failed"):
            ClaudeConnector(config=self.base_config)

        MockFailingClient.assert_called_once()
        failing_client_patch.stop()
        self.mock_anthropic_client_patch.start() # Restart successful patch

    async def test_close_method_calls_client_aclose(self):
        """ Test that the connector's close method calls the client's aclose. """
        await self.connector.close()
        self.mock_client_instance.aclose.assert_called_once()

    # Helper to create a mock Anthropic Message object
    def _create_mock_anthropic_message_response(self, text_content: str, stop_reason="end_turn"):
        mock_text_block = MagicMock(spec=anthropic.types.TextBlock)
        mock_text_block.text = text_content
        mock_text_block.type = "text"

        mock_response = MagicMock(spec=anthropic.types.Message)
        mock_response.id = "msg_test_123"
        mock_response.content = [mock_text_block]
        mock_response.model = self.base_config["model_name"]
        mock_response.role = "assistant"
        mock_response.stop_reason = stop_reason
        mock_response.type = "message"
        mock_response.usage = anthropic.types.Usage(input_tokens=10, output_tokens=20)
        return mock_response

    @patch('jarules_agent.connectors.claude_connector.logger')
    async def test_check_availability_success(self, mock_logger):
        """ Test check_availability success. """
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response("pong")

        result = await self.connector.check_availability()
        self.assertTrue(result)
        self.mock_client_instance.messages.create.assert_called_once()
        call_args = self.mock_client_instance.messages.create.call_args
        self.assertEqual(call_args.kwargs['messages'], [{"role": "user", "content": "ping"}])
        self.assertEqual(call_args.kwargs['max_tokens'], 5) # Specific override for check
        mock_logger.info.assert_called_with("Claude API is available and key is valid.")

    @patch('jarules_agent.connectors.claude_connector.logger')
    async def test_check_availability_api_error(self, mock_logger):
        """ Test check_availability failure on API error. """
        self.mock_client_instance.messages.create.side_effect = anthropic.AuthenticationError("Invalid API Key", request=MagicMock())

        result = await self.connector.check_availability()
        self.assertFalse(result)
        mock_logger.error.assert_called_with("Claude API availability check failed: Invalid API Key (Type: authentication_error, Status: None)")


    async def test_generate_code_success(self):
        """ Test successful code generation. """
        expected_code = "def hello_claude():\n  print('Hello, Claude!')"
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response(expected_code)

        user_prompt = "Python hello world function for Claude."
        context = "This is a test."
        system_instruction = "Be a helpful coding AI."

        actual_code = await self.connector.generate_code(user_prompt, system_instruction=system_instruction, context=context)
        self.assertEqual(actual_code, expected_code)

        self.mock_client_instance.messages.create.assert_called_once()
        call_args = self.mock_client_instance.messages.create.call_args
        self.assertEqual(call_args.kwargs['model'], self.base_config['model_name'])
        self.assertEqual(call_args.kwargs['max_tokens'], self.base_config['max_tokens'])
        self.assertEqual(call_args.kwargs['system'], system_instruction)
        self.assertEqual(len(call_args.kwargs['messages']), 1)
        self.assertEqual(call_args.kwargs['messages'][0]['role'], "user")
        self.assertIn(user_prompt, call_args.kwargs['messages'][0]['content'])
        self.assertIn(context, call_args.kwargs['messages'][0]['content'])

    async def test_generate_code_uses_default_system_prompt(self):
        """ Test generate_code uses the connector's default system prompt if none is provided. """
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response("code")
        await self.connector.generate_code("prompt")
        call_args = self.mock_client_instance.messages.create.call_args
        self.assertEqual(call_args.kwargs['system'], self.base_config['default_system_prompt'])

    async def test_generate_code_no_system_prompt_if_both_null(self):
        """ Test generate_code sends None for system if both specific and default are None. """
        self.connector.default_system_prompt = None # Override for this test
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response("code")
        await self.connector.generate_code("prompt")
        call_args = self.mock_client_instance.messages.create.call_args
        self.assertIsNone(call_args.kwargs['system'])


    @patch('jarules_agent.connectors.claude_connector.logger')
    async def test_generate_code_api_error_handling(self, mock_logger):
        """ Test API error handling in generate_code wraps into ClaudeApiError. """
        original_error = anthropic.RateLimitError("Rate limit exceeded", request=MagicMock())
        self.mock_client_instance.messages.create.side_effect = original_error

        with self.assertRaises(ClaudeApiError) as cm:
            await self.connector.generate_code("prompt")

        self.assertEqual(cm.exception.error_type, "rate_limit_error")
        self.assertIn("Claude API rate limit exceeded", str(cm.exception.message))
        mock_logger.error.assert_called_with(f"Claude API rate limit exceeded: {original_error}")


    async def test_explain_code_success(self):
        """ Test successful code explanation. """
        expected_explanation = "This code defines a function foo."
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response(expected_explanation)

        actual_explanation = await self.connector.explain_code("def foo(): pass")
        self.assertEqual(actual_explanation, expected_explanation)

        call_args = self.mock_client_instance.messages.create.call_args
        self.assertEqual(call_args.kwargs['system'], "You are an expert code explainer. Provide clear and concise explanations for the given code.") # Method-specific default
        self.assertIn("Please explain the following code snippet", call_args.kwargs['messages'][0]['content'])

    async def test_explain_code_with_connector_default_system_prompt(self):
        """ Test explain_code uses connector's default system prompt if set and no override. """
        self.connector.default_system_prompt = "Default system prompt for connector."
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response("explanation")

        await self.connector.explain_code("def foo(): pass")
        call_args = self.mock_client_instance.messages.create.call_args
        self.assertEqual(call_args.kwargs['system'], self.connector.default_system_prompt)


    async def test_suggest_code_modification_success(self):
        """ Test successful code modification suggestion. """
        expected_suggestion = "def bar(): # renamed\n  pass"
        self.mock_client_instance.messages.create.return_value = self._create_mock_anthropic_message_response(expected_suggestion)

        actual_suggestion = await self.connector.suggest_code_modification("def foo(): pass", "rename to bar")
        self.assertEqual(actual_suggestion, expected_suggestion)

        call_args = self.mock_client_instance.messages.create.call_args
        self.assertEqual(call_args.kwargs['system'], "You are an expert code modification assistant. Given a code snippet and an instruction, provide the modified code or a clear description of changes. If providing code, try to provide only the complete, runnable code block.") # Method-specific default
        self.assertIn("Instruction for modification: rename to bar", call_args.kwargs['messages'][0]['content'])

    @patch('jarules_agent.connectors.claude_connector.logger')
    async def test_create_message_invalid_response_structure(self, mock_logger):
        """ Test _create_message handling of unexpected response structure. """
        mock_invalid_response = MagicMock(spec=anthropic.types.Message)
        mock_invalid_response.content = [] # Empty content list
        self.mock_client_instance.messages.create.return_value = mock_invalid_response

        with self.assertRaisesRegex(ClaudeApiError, "Empty or invalid response content from Claude."):
            await self.connector.generate_code("prompt")
        mock_logger.warning.assert_called_with(f"Claude response was empty or invalid: {mock_invalid_response}")

    @patch('jarules_agent.connectors.claude_connector.logger')
    async def test_create_message_content_block_no_text(self, mock_logger):
        """ Test _create_message when content block has no 'text' attribute. """
        mock_block_no_text = MagicMock() # No spec, so won't have .text unless added
        del mock_block_no_text.text # Ensure it's not there if MagicMock auto-creates one

        mock_response_no_text_in_block = MagicMock(spec=anthropic.types.Message)
        mock_response_no_text_in_block.content = [mock_block_no_text]
        self.mock_client_instance.messages.create.return_value = mock_response_no_text_in_block

        with self.assertRaisesRegex(ClaudeApiError, "Invalid response structure: content block missing text."):
            await self.connector.generate_code("prompt")
        mock_logger.error.assert_called_with(f"Claude response content block does not have text attribute: {mock_block_no_text}")


if __name__ == '__main__':
    unittest.main()
