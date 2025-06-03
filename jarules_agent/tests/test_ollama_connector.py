# jarules_agent/tests/test_ollama_connector.py

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys

# Temporarily add the project root to sys.path to allow importing jarules_agent
# This is often necessary when running tests directly if the package isn't installed
# For a real CI/CD pipeline, you'd typically have the package installed or PYTHONPATH set
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import, assuming ollama might not be installed
try:
    import ollama
    OLLAMA_INSTALLED = True
except ImportError:
    ollama = MagicMock() # Mock the entire library if not installed
    # Define ResponseError on the mock if it's used in type hints or error handling
    class MockResponseError(Exception):
        def __init__(self, error, status_code=500):
            self.error = error
            self.status_code = status_code
            super().__init__(error)
    ollama.ResponseError = MockResponseError
    OLLAMA_INSTALLED = False

from jarules_agent.connectors.ollama_connector import (
    OllamaConnector,
    OllamaNotInstalledError,
    OllamaConnectorError,
    OllamaApiError,
    OllamaModelNotAvailableError,
    OllamaGenerationError,
    OllamaCodeGenerationError,
    OllamaExplanationError,
    OllamaModificationError
)
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector


class TestOllamaConnector(unittest.TestCase):

    def setUp(self):
        # Patch 'ollama' module an 'ollama.Client' for most tests
        # We will selectively unpatch or change side_effects for specific scenarios

        self.ollama_patch = patch.dict(sys.modules, {'ollama': ollama if OLLAMA_INSTALLED else MagicMock(ResponseError=ollama.ResponseError)})
        self.mock_ollama_module = self.ollama_patch.start()

        # If ollama was originally installed, self.mock_ollama_module is the real one.
        # If not, it's a MagicMock. We need to ensure ollama.Client is consistently a mock.
        self.client_patch = patch('ollama.Client')
        self.MockOllamaClient = self.client_patch.start()
        self.mock_ollama_client_instance = self.MockOllamaClient.return_value

        # Default successful response for generate
        self.mock_ollama_client_instance.generate.return_value = {
            'response': 'Generated text from Ollama.',
            'done': True,
            # other fields that might be present but usually not critical for basic tests
            'model': 'test_model:latest',
            'created_at': '2023-01-01T00:00:00Z',
            'context': [1, 2, 3],
            'total_duration': 1000000,
            'load_duration': 1000,
            'prompt_eval_count': 10,
            'prompt_eval_duration': 2000,
            'eval_count': 20,
            'eval_duration': 3000
        }
        # Default successful response for list
        self.mock_ollama_client_instance.list.return_value = {
            'models': [
                {'name': 'llama3:latest', 'parameter_size': '7B'},
                {'name': 'codellama:7b-instruct', 'parameter_size': '7B'},
                {'name': 'custom_model:latest', 'parameter_size': '13B'}
            ]
        }

        # Ensure the 'ollama' global in the connector module is this patched version
        # This is crucial if the connector module itself captured 'ollama' at import time
        self.connector_ollama_patch = patch('jarules_agent.connectors.ollama_connector.ollama', self.mock_ollama_module if not OLLAMA_INSTALLED else ollama)
        self.mock_connector_ollama_module = self.connector_ollama_patch.start()


    def tearDown(self):
        self.client_patch.stop()
        self.ollama_patch.stop()
        self.connector_ollama_patch.stop()
        # Restore sys.modules if 'ollama' was force-removed for a test
        if 'ollama' not in sys.modules and OLLAMA_INSTALLED:
             # This is tricky; ideally, don't delete from sys.modules directly
             # For now, assume the patch.dict handles restoration correctly
             pass


    # --- Initialization Tests ---

    def test_init_successful_defaults(self):
        """Test successful initialization with default parameters."""
        connector = OllamaConnector()
        self.assertIsInstance(connector.client, MagicMock) # Since ollama.Client is mocked
        self.MockOllamaClient.assert_called_once_with(host=OllamaConnector.DEFAULT_BASE_URL)
        self.assertEqual(connector.model_name, OllamaConnector.DEFAULT_MODEL_NAME)
        self.assertEqual(connector.base_url, OllamaConnector.DEFAULT_BASE_URL)
        self.assertIsNone(connector.default_system_prompt)
        self.assertIsNone(connector.default_generation_options)

    def test_init_successful_custom_params(self):
        """Test successful initialization with custom parameters."""
        custom_model = "custom_model:latest"
        custom_url = "http://customhost:12345"
        custom_prompt = "You are a test bot."
        custom_gen_params = {"temperature": 0.5, "top_k": 30}

        connector = OllamaConnector(
            model_name=custom_model,
            base_url=custom_url,
            default_system_prompt=custom_prompt,
            generation_params=custom_gen_params
        )
        self.MockOllamaClient.assert_called_once_with(host=custom_url)
        self.assertEqual(connector.model_name, custom_model)
        self.assertEqual(connector.base_url, custom_url)
        self.assertEqual(connector.default_system_prompt, custom_prompt)
        self.assertEqual(connector.default_generation_options, custom_gen_params)

    def test_init_model_name_priority(self):
        """Test model_name priority: constructor > config > default."""
        # Constructor override
        connector = OllamaConnector(model_name="constructor_model")
        self.assertEqual(connector.model_name, "constructor_model")

        # Config override (simulated by passing it in kwargs, as super().__init__ handles it)
        connector = OllamaConnector(config={'model_name': 'config_model'})
        self.assertEqual(connector.model_name, "config_model")

        # Default
        connector = OllamaConnector()
        self.assertEqual(connector.model_name, OllamaConnector.DEFAULT_MODEL_NAME)

    @patch.dict(sys.modules, {'ollama': None}) # Simulate ollama not being importable
    @patch('jarules_agent.connectors.ollama_connector.ollama', None) # Ensure connector sees None
    def test_init_ollama_not_installed(self):
        """Test OllamaNotInstalledError if ollama library is not available."""
        with self.assertRaisesRegex(OllamaNotInstalledError, "The 'ollama' Python library is not installed"):
            OllamaConnector()

    def test_init_ollama_client_instantiation_fails(self):
        """Test OllamaConnectorError if ollama.Client() instantiation fails."""
        self.MockOllamaClient.side_effect = Exception("Failed to create client")
        with self.assertRaisesRegex(OllamaConnectorError, "Failed to initialize Ollama client"):
            OllamaConnector()

    def test_init_attributes_set_correctly(self):
        """Test that all relevant instance attributes are set."""
        connector = OllamaConnector(model_name="test_model", base_url="test_url",
                                    default_system_prompt="test_prompt",
                                    generation_params={"temp": 0.1})
        self.assertEqual(connector.model_name, "test_model")
        self.assertEqual(connector.base_url, "test_url")
        self.assertEqual(connector.default_system_prompt, "test_prompt")
        self.assertEqual(connector.default_generation_options, {"temp": 0.1})
        self.assertIsNotNone(connector.client)


    # --- Core Generation Logic Tests (via generate_code) ---

    def test_generate_successful(self):
        """Test successful text generation via _generate_with_ollama."""
        connector = OllamaConnector()
        prompt = "Test prompt"
        response = connector._generate_with_ollama(prompt)
        self.assertEqual(response, "Generated text from Ollama.")
        self.mock_ollama_client_instance.generate.assert_called_once_with(
            model=OllamaConnector.DEFAULT_MODEL_NAME,
            prompt=prompt,
            system=None, # Default system prompt is None initially
            options={} # Default gen options is None initially
        )

    def test_generate_with_custom_system_prompt_and_options(self):
        """Test generation with custom system prompt and options."""
        connector = OllamaConnector(default_system_prompt="Global prompt",
                                    generation_params={"temperature": 0.8})
        prompt = "Another prompt"
        system_override = "Local system prompt"
        options_override = {"top_k": 50}

        response = connector._generate_with_ollama(
            prompt,
            system_instruction=system_override,
            generation_options_override=options_override
        )
        self.assertEqual(response, "Generated text from Ollama.")
        self.mock_ollama_client_instance.generate.assert_called_once_with(
            model=OllamaConnector.DEFAULT_MODEL_NAME,
            prompt=prompt,
            system=system_override,
            options={"temperature": 0.8, "top_k": 50} # Merged options
        )

    def test_generate_uses_default_system_prompt(self):
        connector = OllamaConnector(default_system_prompt="Default system here")
        connector._generate_with_ollama("A prompt")
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY,
            system="Default system here", options=unittest.mock.ANY
        )

    def test_generate_handles_ollama_response_error_model_not_found(self):
        """Test OllamaModelNotAvailableError for model not found ResponseError."""
        self.mock_ollama_client_instance.generate.side_effect = ollama.ResponseError(
            "model 'unknown_model' not found", status_code=404
        )
        connector = OllamaConnector(model_name="unknown_model")
        with self.assertRaisesRegex(OllamaModelNotAvailableError, "model 'unknown_model' not found"):
            connector._generate_with_ollama("Test prompt")

    def test_generate_handles_ollama_response_error_other(self):
        """Test OllamaApiError for other ResponseError."""
        self.mock_ollama_client_instance.generate.side_effect = ollama.ResponseError(
            "Some other API error", status_code=500
        )
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaApiError, "Some other API error"):
            connector._generate_with_ollama("Test prompt")

    def test_generate_handles_connection_refused_error(self):
        """Test OllamaApiError for ConnectionRefusedError."""
        self.mock_ollama_client_instance.generate.side_effect = ConnectionRefusedError("Connection refused")
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaApiError, "Connection refused by Ollama server"):
            connector._generate_with_ollama("Test prompt")

    def test_generate_handles_generic_exception_during_api_call(self):
        """Test OllamaApiError for generic Exception during API call."""
        self.mock_ollama_client_instance.generate.side_effect = Exception("Unexpected error")
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaApiError, "An unexpected error occurred during Ollama generation"):
            connector._generate_with_ollama("Test prompt")

    def test_generate_handles_empty_response_string(self):
        """Test OllamaGenerationError for empty response string."""
        self.mock_ollama_client_instance.generate.return_value = {'response': ''}
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaGenerationError, "returned an empty response"):
            connector._generate_with_ollama("Test prompt")

    def test_generate_handles_whitespace_only_response(self):
        """Test OllamaGenerationError for whitespace-only response."""
        self.mock_ollama_client_instance.generate.return_value = {'response': '   \n   '}
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaGenerationError, "returned an empty response"):
            connector._generate_with_ollama("Test prompt")

    def test_generate_no_client_initialized_raises_error(self):
        connector = OllamaConnector()
        connector.client = None # Simulate failed init or manual reset
        with self.assertRaisesRegex(OllamaConnectorError, "Ollama client not initialized"):
            connector._generate_with_ollama("A prompt")

    def test_generate_options_merging_priority(self):
        """Generation options override default, method params override those."""
        connector = OllamaConnector(generation_params={"temperature": 0.7, "seed": 123})
        prompt = "Test prompt"

        # Test with method-specific override
        connector._generate_with_ollama(prompt, generation_options_override={"temperature": 0.5, "top_p": 0.9})
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY, system=unittest.mock.ANY,
            options={"temperature": 0.5, "seed": 123, "top_p": 0.9} # Merged: method overrides default
        )
        self.mock_ollama_client_instance.generate.reset_mock()

        # Test with only default options
        connector._generate_with_ollama(prompt)
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY, system=unittest.mock.ANY,
            options={"temperature": 0.7, "seed": 123}
        )

    def test_generate_filters_none_from_options(self):
        connector = OllamaConnector(generation_params={"temperature": 0.7, "stop": None})
        connector._generate_with_ollama("Test prompt")
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY, system=unittest.mock.ANY,
            options={"temperature": 0.7} # 'stop: None' should be filtered out
        )

    # --- generate_code() specific tests ---

    def test_generate_code_successful(self):
        """Test successful code generation."""
        connector = OllamaConnector()
        user_prompt = "Write a python hello world function."
        self.mock_ollama_client_instance.generate.return_value = {'response': 'def hello():\n  print("Hello, world!")'}
        code = connector.generate_code(user_prompt)
        self.assertEqual(code, 'def hello():\n  print("Hello, world!")')
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=OllamaConnector.DEFAULT_MODEL_NAME,
            prompt=user_prompt,
            system=OllamaConnector.DEFAULT_CODE_SYSTEM_INSTRUCTION,
            options={}
        )

    def test_generate_code_strips_markdown_basic(self):
        """Test markdown stripping (``` ... ```)."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': '```python\ndef hello():\n  print("Hi")\n```'}
        code = connector.generate_code("prompt")
        self.assertEqual(code, 'def hello():\n  print("Hi")')

    def test_generate_code_strips_markdown_no_language(self):
        """Test markdown stripping (``` ... ```) without language specified."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': '```\ndef hello():\n  print("Hi")\n```'}
        code = connector.generate_code("prompt")
        self.assertEqual(code, 'def hello():\n  print("Hi")')

    def test_generate_code_strips_markdown_only_start_marker(self):
        """Test markdown stripping when only start marker ```python is present."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': '```python\ndef hello():\n  print("Hi")'}
        # This is a bit ambiguous, current logic might return it as is or try to strip.
        # Let's assume the current logic for stripping is what we test.
        # The current logic might strip the first line if it's just ```python
        code = connector.generate_code("prompt")
        self.assertEqual(code, 'def hello():\n  print("Hi")')


    def test_generate_code_strips_markdown_only_end_marker(self):
        """Test markdown stripping when only end marker ``` is present."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': 'def hello():\n  print("Hi")\n```'}
        code = connector.generate_code("prompt")
        # Current logic might strip the last line if it's just ```
        self.assertEqual(code, 'def hello():\n  print("Hi")')

    def test_generate_code_empty_after_stripping(self):
        """Test returns empty string if content after stripping is empty."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': '```python\n```'}
        code = connector.generate_code("prompt")
        self.assertEqual(code, "") # Or None, depending on desired behavior for "empty" code. Current is "" then strip -> ""

    def test_generate_code_returns_none_if_ollama_returns_empty(self):
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': ''}
        with self.assertRaises(OllamaCodeGenerationError): # It should raise due to empty response from _generate
            connector.generate_code("prompt")


    def test_generate_code_custom_system_instruction(self):
        connector = OllamaConnector()
        custom_instr = "Generate only Java."
        connector.generate_code("prompt", system_instruction=custom_instr)
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY,
            system=custom_instr, options=unittest.mock.ANY
        )

    def test_generate_code_raises_ollamacodegenerationerror_on_api_error(self):
        """Test specific error for API failure in generate_code."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = OllamaApiError("API broke")
        with self.assertRaisesRegex(OllamaCodeGenerationError, "API error in generate_code"):
            connector.generate_code("prompt")

    def test_generate_code_raises_ollamacodegenerationerror_on_generation_error(self):
        """Test specific error for generation failure in generate_code."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = OllamaGenerationError("Empty stuff")
        with self.assertRaisesRegex(OllamaCodeGenerationError, "Generation error in generate_code"):
            connector.generate_code("prompt")

    def test_generate_code_unexpected_error_propagates_as_codegenerationerror(self):
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = Exception("Totally unexpected")
        with self.assertRaisesRegex(OllamaCodeGenerationError, "An unexpected error occurred during Ollama code generation"):
            connector.generate_code("prompt")


    # --- explain_code() specific tests ---

    def test_explain_code_successful(self):
        """Test successful code explanation."""
        connector = OllamaConnector()
        code_snippet = "def x(): pass"
        self.mock_ollama_client_instance.generate.return_value = {'response': 'This is an explanation.'}
        explanation = connector.explain_code(code_snippet)
        self.assertEqual(explanation, 'This is an explanation.')
        expected_prompt = f"Please explain the following code:\n\n```\n{code_snippet}\n```"
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=OllamaConnector.DEFAULT_MODEL_NAME,
            prompt=expected_prompt,
            system=OllamaConnector.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION,
            options={}
        )

    def test_explain_code_custom_system_instruction(self):
        connector = OllamaConnector()
        custom_instr = "Explain in simple terms."
        connector.explain_code("code", system_instruction=custom_instr)
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY,
            system=custom_instr, options=unittest.mock.ANY
        )

    def test_explain_code_raises_ollamaexplanationerror_on_api_error(self):
        """Test specific error for API failure in explain_code."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = OllamaApiError("API broke")
        with self.assertRaisesRegex(OllamaExplanationError, "API error in explain_code"):
            connector.explain_code("code")

    def test_explain_code_raises_ollamaexplanationerror_on_generation_error(self):
        """Test specific error for generation failure in explain_code."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = OllamaGenerationError("Empty explanation")
        with self.assertRaisesRegex(OllamaExplanationError, "Generation error in explain_code"):
            connector.explain_code("code")

    def test_explain_code_unexpected_error_propagates_as_explanationerror(self):
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = Exception("Totally unexpected explanation error")
        with self.assertRaisesRegex(OllamaExplanationError, "An unexpected error occurred during Ollama code explanation"):
            connector.explain_code("code")

    # --- suggest_code_modification() specific tests ---

    def test_suggest_code_modification_successful(self):
        """Test successful code modification suggestion."""
        connector = OllamaConnector()
        code_snippet = "def old(): pass"
        issue = "Make it new"
        self.mock_ollama_client_instance.generate.return_value = {'response': 'def new(): pass'}
        modification = connector.suggest_code_modification(code_snippet, issue)
        self.assertEqual(modification, 'def new(): pass')

        expected_prompt = (
            f"Issue/Request: {issue}\n\n"
            f"Original Code:\n```\n{code_snippet}\n```\n\n"
            "Please provide the modified code snippet."
        )
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=OllamaConnector.DEFAULT_MODEL_NAME,
            prompt=expected_prompt,
            system=OllamaConnector.DEFAULT_MODIFY_SYSTEM_INSTRUCTION,
            options={}
        )

    def test_suggest_code_modification_strips_markdown(self):
        """Test markdown stripping for modification suggestions."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.return_value = {'response': '```python\ndef new(): pass\n```'}
        modification = connector.suggest_code_modification("old code", "issue")
        self.assertEqual(modification, 'def new(): pass')

    def test_suggest_code_modification_custom_system_instruction(self):
        connector = OllamaConnector()
        custom_instr = "Suggest only one line changes."
        connector.suggest_code_modification("code", "issue", system_instruction=custom_instr)
        self.mock_ollama_client_instance.generate.assert_called_with(
            model=unittest.mock.ANY, prompt=unittest.mock.ANY,
            system=custom_instr, options=unittest.mock.ANY
        )

    def test_suggest_code_modification_raises_ollamamodificationerror_on_api_error(self):
        """Test specific error for API failure in suggest_code_modification."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = OllamaApiError("API broke")
        with self.assertRaisesRegex(OllamaModificationError, "API error in suggest_code_modification"):
            connector.suggest_code_modification("code", "issue")

    def test_suggest_code_modification_raises_ollamamodificationerror_on_generation_error(self):
        """Test specific error for generation failure in suggest_code_modification."""
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = OllamaGenerationError("Empty suggestion")
        with self.assertRaisesRegex(OllamaModificationError, "Generation error in suggest_code_modification"):
            connector.suggest_code_modification("code", "issue")

    def test_suggest_code_modification_unexpected_error_propagates_as_modificationerror(self):
        connector = OllamaConnector()
        self.mock_ollama_client_instance.generate.side_effect = Exception("Totally unexpected modification error")
        with self.assertRaisesRegex(OllamaModificationError, "An unexpected error occurred during Ollama code modification"):
            connector.suggest_code_modification("code", "issue")

    # --- _check_model_availability() tests ---

    def test_check_model_availability_model_present(self):
        """Test _check_model_availability when model is present."""
        connector = OllamaConnector(model_name="llama3:latest")
        # Default mock_ollama_client_instance.list has 'llama3:latest'
        try:
            connector._check_model_availability() # Should not raise
        except OllamaModelNotAvailableError:
            self.fail("_check_model_availability raised OllamaModelNotAvailableError unexpectedly")

    def test_check_model_availability_model_not_present_strict(self):
        """Test _check_model_availability when exact model tag is not present."""
        connector = OllamaConnector(model_name="nonexistent_model:latest")
        with self.assertRaisesRegex(OllamaModelNotAvailableError, "Model 'nonexistent_model:latest' not found"):
            connector._check_model_availability()

    def test_check_model_availability_base_model_present_tag_not(self):
        """Test _check_model_availability when base model is present but specific tag is not."""
        # mock list has 'codellama:7b-instruct'
        connector = OllamaConnector(model_name="codellama:13b-instruct") # 13b is not in mock
        # This should print a warning but not raise an error, as 'codellama' base exists
        with patch('builtins.print') as mock_print:
            connector._check_model_availability()
            mock_print.assert_any_call(unittest.mock.ANY) # Check if any print was called (for the warning)
            # More specific: check for the warning message
            self.assertTrue(any("Warning: Exact model tag 'codellama:13b-instruct' not found" in call.args[0] for call in mock_print.call_args_list))


    def test_check_model_availability_connection_error(self):
        """Test _check_model_availability with a connection error during list models."""
        self.mock_ollama_client_instance.list.side_effect = ConnectionError("Cannot connect to list")
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaApiError, "Failed to connect to Ollama at http://localhost:11434 to list models"):
            connector._check_model_availability()

    def test_check_model_availability_other_exception_on_list(self):
        """Test _check_model_availability with an unexpected error during list models."""
        self.mock_ollama_client_instance.list.side_effect = Exception("List exploded")
        connector = OllamaConnector()
        with self.assertRaisesRegex(OllamaConnectorError, "Error checking model availability"):
            connector._check_model_availability()

    def test_underlying_exception_passed_correctly(self):
        original_exception = Exception("Original cause")
        self.mock_ollama_client_instance.generate.side_effect = original_exception
        connector = OllamaConnector()
        with self.assertRaises(OllamaApiError) as cm:
            connector._generate_with_ollama("prompt")
        self.assertIs(cm.exception.underlying_exception, original_exception)

        self.mock_ollama_client_instance.list.side_effect = original_exception
        with self.assertRaises(OllamaConnectorError) as cm:
            connector._check_model_availability()
        self.assertIs(cm.exception.underlying_exception, original_exception)

    # Test inheritance from BaseLLMConnector
    def test_is_subclass_of_base_llm_connector(self):
        self.assertTrue(issubclass(OllamaConnector, BaseLLMConnector))

    # Test that connector passes kwargs to super for config loading
    def test_init_passes_kwargs_to_super_for_config(self):
        """
        Ensures that kwargs passed to OllamaConnector are passed to BaseLLMConnector's
        __init__ method, which uses them to populate self._config.
        """
        # BaseLLMConnector's __init__ expects 'config' or will use kwargs directly
        # to form a _config dict.
        # We test by passing a kwarg that OllamaConnector doesn't explicitly handle,
        # but BaseLLMConnector should pick up.

        # We need to patch BaseLLMConnector.__init__ to check what it receives
        with patch.object(BaseLLMConnector, '__init__') as mock_base_init:
            # Instantiate OllamaConnector with an extra kwarg
            OllamaConnector(model_name="test_model", some_custom_config_param="custom_value")

            # Check if BaseLLMConnector.__init__ was called
            mock_base_init.assert_called_once()

            # Check the arguments passed to BaseLLMConnector.__init__
            # The first argument to a method is 'self', so we check args[1:] or kwargs
            args, kwargs = mock_base_init.call_args
            self.assertEqual(kwargs.get('model_name'), "test_model")
            self.assertEqual(kwargs.get('some_custom_config_param'), "custom_value")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Note: If OLLAMA_INSTALLED is False, some tests might behave differently,
# especially those related to specific error types from the ollama library.
# The mocks try to simulate the behavior, but it's best to test with ollama installed.
# The OllamaNotInstalledError test specifically requires 'ollama' to be None in sys.modules.
# For other tests, we mock ollama.Client so the actual library calls are bypassed.
#
# To run tests and ensure the jarules_agent package is found, you might need to run from the project root:
# python -m unittest jarules_agent.tests.test_ollama_connector
# or ensure your PYTHONPATH is set up correctly.
# The sys.path manipulation at the top is a common workaround for direct script execution.
