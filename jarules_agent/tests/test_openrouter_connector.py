# jarules_agent/tests/test_openrouter_connector.py

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os

# Temporarily add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Conditionally import and mock 'requests'
try:
    import requests
    REQUESTS_INSTALLED = True
except ImportError:
    requests = MagicMock()
    # Define necessary exception hierarchy if requests is not installed
    class MockRequestException(IOError): pass
    class MockHTTPError(MockRequestException):
        def __init__(self, *args, response=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.response = response if response is not None else MagicMock()
    requests.exceptions = MagicMock()
    requests.exceptions.RequestException = MockRequestException
    requests.exceptions.HTTPError = MockHTTPError
    REQUESTS_INSTALLED = False


from jarules_agent.connectors.openrouter_connector import (
    OpenRouterConnector,
    OpenRouterNotInstalledError,
    OpenRouterApiKeyError,
    OpenRouterApiError,
    OpenRouterModelNotAvailableError,
    OpenRouterGenerationError,
    OpenRouterCodeGenerationError,
    OpenRouterExplanationError,
    OpenRouterModificationError
)
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector


class TestOpenRouterConnector(unittest.TestCase):

    def setUp(self):
        # Patch 'requests' module itself (for not installed test)
        # and 'requests.Session' for most other tests
        self.requests_module_patch = patch.dict(sys.modules, {'requests': requests if REQUESTS_INSTALLED else MagicMock(exceptions=requests.exceptions)})
        self.mock_requests_module = self.requests_module_patch.start()

        self.session_patch = patch('requests.Session')
        self.MockSession = self.session_patch.start()
        self.mock_session_instance = self.MockSession.return_value
        self.mock_session_instance.headers = {} # Simulate the headers dict

        # Default successful response for session.post
        self.mock_response = MagicMock(spec=requests.Response if REQUESTS_INSTALLED else object)
        self.mock_response.status_code = 200
        self.mock_response.json.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1677652288,
            "model": OpenRouterConnector.DEFAULT_MODEL_NAME,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Generated text from OpenRouter."},
                "finish_reason": "stop"
            }]
        }
        # Make raise_for_status do nothing for 200
        self.mock_response.raise_for_status = MagicMock()
        self.mock_session_instance.post.return_value = self.mock_response

        # Patch os.environ for API key tests
        self.env_patch = patch.dict(os.environ, {})
        self.mock_env = self.env_patch.start()

        # Ensure connector module sees patched requests if it was mocked
        self.connector_requests_patch = patch('jarules_agent.connectors.openrouter_connector.requests', self.mock_requests_module if not REQUESTS_INSTALLED else requests)
        self.mock_connector_requests_module = self.connector_requests_patch.start()


    def tearDown(self):
        self.session_patch.stop()
        self.requests_module_patch.stop()
        self.env_patch.stop()
        self.connector_requests_patch.stop()

    # --- Initialization Tests ---
    def test_init_successful_defaults(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_api_key_env'
        connector = OpenRouterConnector()
        self.MockSession.assert_called_once()
        self.assertEqual(self.mock_session_instance.headers["Authorization"], "Bearer test_api_key_env")
        self.assertEqual(self.mock_session_instance.headers["HTTP-Referer"], OpenRouterConnector.DEFAULT_HTTP_REFERER)
        self.assertEqual(self.mock_session_instance.headers["X-Title"], OpenRouterConnector.DEFAULT_APP_NAME)
        self.assertEqual(connector.model_name, OpenRouterConnector.DEFAULT_MODEL_NAME)

    def test_init_successful_custom_params_kwargs(self):
        connector = OpenRouterConnector(
            api_key='test_key_kwarg',
            model_name='custom/model',
            base_url='https://custom.api',
            http_referer='http://my.app',
            app_name='My Custom App',
            default_system_prompt='Custom system.',
            generation_params={'temp': 0.1}
        )
        self.assertEqual(self.mock_session_instance.headers["Authorization"], "Bearer test_key_kwarg")
        self.assertEqual(connector.model_name, 'custom/model')
        self.assertEqual(connector.base_url, 'https://custom.api')
        self.assertEqual(self.mock_session_instance.headers["HTTP-Referer"], 'http://my.app')
        self.assertEqual(self.mock_session_instance.headers["X-Title"], 'My Custom App')
        self.assertEqual(connector.default_system_prompt, 'Custom system.')
        self.assertEqual(connector.default_generation_options, {'temp': 0.1})

    def test_init_api_key_from_env_優先(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'env_key'
        connector = OpenRouterConnector(api_key='kwarg_key')
        self.assertEqual(self.mock_session_instance.headers["Authorization"], "Bearer kwarg_key") # Kwarg has priority due to _config.get('api_key') or os.environ...

    def test_init_api_key_from_config_first(self):
        # Simulate api_key coming from the config dictionary (passed via kwargs to super)
        connector = OpenRouterConnector(config={'api_key': 'config_key'})
        self.assertEqual(self.mock_session_instance.headers["Authorization"], "Bearer config_key")


    @patch.dict(sys.modules, {'requests': None})
    @patch('jarules_agent.connectors.openrouter_connector.requests', None)
    def test_init_requests_not_installed(self):
        with self.assertRaisesRegex(OpenRouterNotInstalledError, "The 'requests' Python library is not installed"):
            OpenRouterConnector(api_key="fakekey") # Need to provide key to pass that check

    def test_init_api_key_missing(self):
        # Ensure OPENROUTER_API_KEY is not in mock_env
        if "OPENROUTER_API_KEY" in self.mock_env: del self.mock_env["OPENROUTER_API_KEY"]
        with self.assertRaisesRegex(OpenRouterApiKeyError, "OpenRouter API key not found"):
            OpenRouterConnector()

    # --- API Call Logic Tests (_make_api_call via public methods) ---
    def _configure_http_error_response(self, status_code, json_response_body, error_message_in_body=""):
        mock_err_response = MagicMock(spec=requests.Response if REQUESTS_INSTALLED else object)
        mock_err_response.status_code = status_code
        mock_err_response.json.return_value = json_response_body
        mock_err_response.text = str(json_response_body) if not error_message_in_body else error_message_in_body

        http_error = requests.exceptions.HTTPError(response=mock_err_response)
        # http_error.response = mock_err_response # Set explicitly as it's not always done by constructor
        mock_err_response.raise_for_status.side_effect = http_error
        self.mock_session_instance.post.return_value = mock_err_response
        return http_error # Return the exception instance for further checks if needed

    def test_api_call_http_401_unauthorized(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self._configure_http_error_response(401, {"error": {"message": "Invalid API key", "type": "authentication_error"}})
        connector = OpenRouterConnector()
        with self.assertRaisesRegex(OpenRouterApiError, "OpenRouter API HTTP error \(401\): Invalid API key") as cm:
            connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 401)

    def test_api_call_http_404_model_not_found_in_detail(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self._configure_http_error_response(404, {"error": {"message": "The model `unknown/model` does not exist or is not available.", "type": "invalid_request_error"}})
        connector = OpenRouterConnector(model_name="unknown/model")
        with self.assertRaisesRegex(OpenRouterModelNotAvailableError, "Model 'unknown/model' not found \(HTTP 404\)") as cm:
            connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 404)

    def test_api_call_http_404_model_not_found_resolve_model(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self._configure_http_error_response(404, {"error": {"message": "Could not resolve model `unknown/model`.", "type": "invalid_request_error"}})
        connector = OpenRouterConnector(model_name="unknown/model")
        with self.assertRaisesRegex(OpenRouterModelNotAvailableError, "Model 'unknown/model' not found \(HTTP 404\)") as cm:
            connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 404)


    def test_api_call_http_500_server_error(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self._configure_http_error_response(500, {"error": {"message": "Internal server error", "type": "api_error"}})
        connector = OpenRouterConnector()
        with self.assertRaisesRegex(OpenRouterApiError, "OpenRouter API HTTP error \(500\): Internal server error") as cm:
            connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 500)

    def test_api_call_requests_exception_timeout(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self.mock_session_instance.post.side_effect = requests.exceptions.RequestException("Timeout")
        connector = OpenRouterConnector()
        with self.assertRaisesRegex(OpenRouterApiError, "OpenRouter request failed: Timeout"):
            connector.generate_code("prompt")

    def test_api_call_200_ok_but_error_in_json_response(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self.mock_response.json.return_value = {"error": {"message": "Something bad happened server-side", "type": "server_error_in_json"}}
        # raise_for_status is not called for 200, so no HTTPError
        self.mock_response.status_code = 200
        self.mock_response.raise_for_status.side_effect = None

        connector = OpenRouterConnector()
        with self.assertRaisesRegex(OpenRouterApiError, "OpenRouter API returned an error: Something bad happened server-side") as cm:
            connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 200) # Status code from original response

    def test_api_call_200_ok_model_not_found_in_json_error(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        self.mock_response.json.return_value = {"error": {"message": "Model 'oops/model' not found in provider", "type": "model_not_found"}}
        self.mock_response.status_code = 200
        self.mock_response.raise_for_status.side_effect = None

        connector = OpenRouterConnector(model_name="oops/model")
        with self.assertRaisesRegex(OpenRouterModelNotAvailableError, "Model 'oops/model' not found or not available") as cm:
            connector.generate_code("prompt")
        self.assertEqual(cm.exception.status_code, 200)


    # --- Content Extraction Tests (_extract_content_from_response) ---
    def test_extract_content_successful(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        # Default mock_response is fine for this
        content = connector._extract_content_from_response(self.mock_response.json.return_value)
        self.assertEqual(content, "Generated text from OpenRouter.")

    def test_extract_content_no_choices(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        response_data = {"choices": []}
        with self.assertRaisesRegex(OpenRouterGenerationError, "OpenRouter response contained no choices"):
            connector._extract_content_from_response(response_data)

    def test_extract_content_no_message_in_choice(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        response_data = {"choices": [{"index": 0}]} # No 'message'
        with self.assertRaisesRegex(OpenRouterGenerationError, "OpenRouter choice contained no message"):
            connector._extract_content_from_response(response_data)

    def test_extract_content_no_content_in_message(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        # 'content' key exists but is None
        response_data = {"choices": [{"message": {"role": "assistant", "content": None}}]}
        # Current implementation returns None if content is None, does not raise error.
        content = connector._extract_content_from_response(response_data)
        self.assertIsNone(content)

    def test_extract_content_keyerror_if_bad_structure(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        response_data = {"foo": "bar"} # Completely different structure
        with self.assertRaisesRegex(OpenRouterGenerationError, "Failed to extract content from OpenRouter response"):
            connector._extract_content_from_response(response_data)

    def test_extract_content_empty_string_is_valid(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = ""
        content = connector._extract_content_from_response(self.mock_response.json.return_value)
        self.assertEqual(content, "")


    # --- generate_code() specific tests ---
    def test_generate_code_successful(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = 'def hello(): pass'
        code = connector.generate_code("prompt")
        self.assertEqual(code, 'def hello(): pass')

        # Check payload
        payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
        self.assertEqual(payload_sent['model'], OpenRouterConnector.DEFAULT_MODEL_NAME)
        expected_messages = [
            {"role": "system", "content": OpenRouterConnector.DEFAULT_CODE_SYSTEM_INSTRUCTION},
            {"role": "user", "content": "prompt"}
        ]
        self.assertEqual(payload_sent['messages'], expected_messages)

    def test_generate_code_uses_connector_default_system_prompt_if_set(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector(default_system_prompt="Connector default system")
        connector.generate_code("user prompt")
        payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
        self.assertEqual(payload_sent['messages'][0]['content'], "Connector default system")


    def test_generate_code_uses_method_system_instruction_override(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector(default_system_prompt="Connector default system")
        connector.generate_code("user prompt", system_instruction="Method override system")
        payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
        self.assertEqual(payload_sent['messages'][0]['content'], "Method override system")

    def test_generate_code_no_system_prompt_if_empty_string_and_no_default(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        # Ensure default_system_prompt is None for this test
        connector = OpenRouterConnector(default_system_prompt=None)
        # Explicitly set the class default to None for this test context if needed
        with patch.object(OpenRouterConnector, 'DEFAULT_CODE_SYSTEM_INSTRUCTION', new=None):
            connector.generate_code("user prompt", system_instruction="")
            payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
            self.assertEqual(len(payload_sent['messages']), 1) # Only user message
            self.assertEqual(payload_sent['messages'][0]['role'], 'user')


    def test_generate_code_with_generation_options_kwarg(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector(generation_params={'temp': 0.5})
        connector.generate_code("prompt", generation_options={'max_tokens': 100, 'temp': 0.6})
        payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
        self.assertEqual(payload_sent['temp'], 0.6) # Method override
        self.assertEqual(payload_sent['max_tokens'], 100)


    def test_generate_code_markdown_stripping(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = '```python\ncode\n```'
        code = connector.generate_code("prompt")
        self.assertEqual(code, 'code')

    def test_generate_code_returns_none_if_content_is_null(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = None
        code = connector.generate_code("prompt")
        self.assertIsNone(code)

    def test_generate_code_returns_empty_if_content_empty_after_strip(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = '```\n```'
        code = connector.generate_code("prompt")
        self.assertEqual(code, "")


    def test_generate_code_raises_specific_error_on_api_failure(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_session_instance.post.side_effect = OpenRouterApiError("API broke")
        with self.assertRaisesRegex(OpenRouterCodeGenerationError, "API error in generate_code"):
            connector.generate_code("prompt")

    def test_generate_code_raises_specific_error_on_generation_failure(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        # Simulate a generation error (e.g., malformed response structure)
        self.mock_response.json.return_value = {"choices": []} # This will cause OpenRouterGenerationError in _extract_content
        with self.assertRaisesRegex(OpenRouterCodeGenerationError, "Generation error in generate_code"):
            connector.generate_code("prompt")


    # --- explain_code() specific tests ---
    def test_explain_code_successful(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = 'Explanation'
        explanation = connector.explain_code("code snippet")
        self.assertEqual(explanation, 'Explanation')

        payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
        expected_user_prompt = "Please explain the following code:\n\n```\ncode snippet\n```"
        self.assertEqual(payload_sent['messages'][-1]['content'], expected_user_prompt)
        self.assertEqual(payload_sent['messages'][0]['content'], OpenRouterConnector.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION)

    def test_explain_code_raises_specific_error(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_session_instance.post.side_effect = OpenRouterApiError("API broke for explain")
        with self.assertRaisesRegex(OpenRouterExplanationError, "API error in explain_code"):
            connector.explain_code("code")

    # --- suggest_code_modification() specific tests ---
    def test_suggest_code_modification_successful(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = 'modified code'
        suggestion = connector.suggest_code_modification("original code", "issue desc")
        self.assertEqual(suggestion, 'modified code')

        payload_sent = self.mock_session_instance.post.call_args.kwargs['json']
        expected_user_prompt = "Issue/Request: issue desc\n\nOriginal Code:\n```\noriginal code\n```\n\nPlease provide the modified code snippet."
        self.assertEqual(payload_sent['messages'][-1]['content'], expected_user_prompt)
        self.assertEqual(payload_sent['messages'][0]['content'], OpenRouterConnector.DEFAULT_MODIFY_SYSTEM_INSTRUCTION)


    def test_suggest_code_modification_markdown_stripping(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_response.json.return_value['choices'][0]['message']['content'] = '```\nmod\n```'
        suggestion = connector.suggest_code_modification("code", "issue")
        self.assertEqual(suggestion, 'mod')

    def test_suggest_code_modification_raises_specific_error(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        connector = OpenRouterConnector()
        self.mock_session_instance.post.side_effect = OpenRouterApiError("API broke for modify")
        with self.assertRaisesRegex(OpenRouterModificationError, "API error in suggest_code_modification"):
            connector.suggest_code_modification("code", "issue")

    def test_underlying_exception_passed_correctly_api_error(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        original_exception = requests.exceptions.Timeout("Connection timed out")
        self.mock_session_instance.post.side_effect = original_exception
        connector = OpenRouterConnector()
        with self.assertRaises(OpenRouterApiError) as cm:
            connector._make_api_call(messages=[{"role": "user", "content": "prompt"}])
        self.assertIs(cm.exception.underlying_exception, original_exception)

    def test_underlying_exception_passed_correctly_generation_error(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'test_key'
        original_exception = KeyError("choices")
        # Simulate a scenario where _extract_content_from_response would raise due to bad data
        def mock_extract_side_effect(*args, **kwargs):
            raise OpenRouterGenerationError("Simulated extraction failure", underlying_exception=original_exception)

        connector = OpenRouterConnector()
        with patch.object(connector, '_extract_content_from_response', side_effect=mock_extract_side_effect):
            with self.assertRaises(OpenRouterCodeGenerationError) as cm:
                connector.generate_code("prompt")
        self.assertIs(cm.exception.underlying_exception.underlying_exception, original_exception)


    def test_is_subclass_of_base_llm_connector(self):
        self.assertTrue(issubclass(OpenRouterConnector, BaseLLMConnector))

    def test_init_passes_kwargs_to_super_for_config(self):
        self.mock_env['OPENROUTER_API_KEY'] = 'somekey' # To pass OpenRouterConnector's own checks
        with patch.object(BaseLLMConnector, '__init__') as mock_base_init:
            OpenRouterConnector(model_name="test_model", some_custom_config_param="custom_value")
            mock_base_init.assert_called_once()
            args, kwargs = mock_base_init.call_args
            self.assertEqual(kwargs.get('model_name'), "test_model")
            self.assertEqual(kwargs.get('some_custom_config_param'), "custom_value")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
# To run tests from project root:
# python -m unittest jarules_agent.tests.test_openrouter_connector
# Ensure PYTHONPATH includes the project root or the package is installed.
# The sys.path manipulation at the top is a common workaround for direct script execution.
# Conditional import of 'requests' and mocking its exceptions if not installed
# allows tests to run in environments without 'requests', though with less fidelity
# for specific requests.exceptions behaviors.
