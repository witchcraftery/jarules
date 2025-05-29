# jarules_agent/tests/test_gemini_api.py

import unittest
from unittest.mock import patch, MagicMock, call
import os

# Adjust import path for standalone execution
import sys
if '.' not in sys.path: # Optional: Check if current directory is already in sys.path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from jarules_agent.connectors.gemini_api import GeminiClient, GeminiApiKeyError, GeminiApiError, GeminiClientError
    import google.generativeai as genai # For GenerativeModel class
    from google.ai.generativelanguage import types as glm_types # For types
    from google.api_core import exceptions as google_exceptions
except ModuleNotFoundError:
    # This path adjustment might be necessary if the above doesn't work in all execution contexts
    # e.g. if CWD is 'jarules_agent'
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from connectors.gemini_api import GeminiClient, GeminiApiKeyError, GeminiApiError, GeminiClientError
    import google.generativeai as genai
    from google.ai.generativelanguage import types as glm_types # For types
    from google.api_core import exceptions as google_exceptions


class TestGeminiApiClientSetup(unittest.TestCase):

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_123"})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_initialization_success(self, mock_generative_model, mock_configure):
        """Test successful initialization of GeminiClient."""
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        
        client = GeminiClient(model_name="test-model")
        
        mock_configure.assert_called_once_with(api_key="test_api_key_123")
        mock_generative_model.assert_called_once_with("test-model")
        self.assertEqual(client.model, mock_model_instance)
        self.assertEqual(client.model_name, "test-model")
        self.assertEqual(client.api_key, "test_api_key_123")
        print("test_initialization_success: Passed")

    @patch.dict(os.environ, {}, clear=True) # Ensure GEMINI_API_KEY is not set
    def test_initialization_no_api_key(self):
        """Test initialization fails if GEMINI_API_KEY is not set."""
        with self.assertRaisesRegex(GeminiApiKeyError, "GEMINI_API_KEY environment variable not set"):
            GeminiClient()
        print("test_initialization_no_api_key: Passed")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_123"})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_default_model_name_used(self, mock_generative_model, mock_configure):
        """Test that the default model name is used if none is provided."""
        GeminiClient() # No model_name argument
        mock_generative_model.assert_called_once_with(GeminiClient.DEFAULT_MODEL_NAME)
        print("test_default_model_name_used: Passed")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_123"})
    @patch('google.generativeai.configure', side_effect=Exception("Config failed"))
    def test_initialization_configure_failure(self, mock_configure):
        """Test initialization fails if genai.configure raises an exception."""
        with self.assertRaisesRegex(GeminiClientError, "Failed to configure Gemini API: Config failed"):
            GeminiClient()
        print("test_initialization_configure_failure: Passed")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_123"})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel', side_effect=Exception("Model init failed"))
    def test_initialization_model_failure(self, mock_generative_model, mock_configure):
        """Test initialization fails if GenerativeModel instantiation raises an exception."""
        with self.assertRaisesRegex(GeminiClientError, "Failed to initialize Gemini model 'gemini-1.5-flash-latest': Model init failed"):
            GeminiClient()
        print("test_initialization_model_failure: Passed")


class TestGeminiApiInteraction(unittest.TestCase):
    
    def setUp(self):
        """Setup common resources for API interaction tests."""
        self.api_key_patch = patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_for_interaction"})
        self.configure_patch = patch('google.generativeai.configure')
        self.model_patch = patch('google.generativeai.GenerativeModel')

        self.mock_configure = self.configure_patch.start()
        self.mock_generative_model_class = self.model_patch.start()
        
        self.mock_model_instance = MagicMock(spec=genai.GenerativeModel)
        self.mock_generative_model_class.return_value = self.mock_model_instance
        
        self.client = GeminiClient() # Initialize client after mocks are active

    def tearDown(self):
        self.api_key_patch.stop()
        self.configure_patch.stop()
        self.model_patch.stop()

    def test_generate_content_raw_api_call_success(self):
        """Test _generate_content_raw successfully calls the API and returns response."""
        mock_api_response = MagicMock(spec=glm_types.GenerateContentResponse)
        self.mock_model_instance.generate_content.return_value = mock_api_response
        
        prompt_parts = ["test prompt"]
        # gen_config needs to be created using glm.GenerationConfig if that's the correct type
        # For now, assuming the structure passed to the actual API call is a dict or compatible object
        # If genai.types.GenerationConfig was just for type hinting or spec, this might be okay.
        # Let's assume the client itself constructs the GenerationConfig object properly if needed.
        # The test focuses on the client's method call, not necessarily constructing this object.
        gen_config_dict = {"temperature": 0.5} # Pass as dict, client should handle
        safety_settings = [{"category": "HARM_CATEGORY_SEXUALITY", "threshold": "BLOCK_NONE"}]

        response = self.client._generate_content_raw(prompt_parts, generation_config=gen_config_dict, safety_settings=safety_settings)
        
        self.mock_model_instance.generate_content.assert_called_once_with(
            contents=prompt_parts,
            generation_config=gen_config_dict, # Ensure this matches what the client sends
            safety_settings=safety_settings
        )
        self.assertEqual(response, mock_api_response)
        print("test_generate_content_raw_api_call_success: Passed")

    def test_generate_content_raw_api_call_failure_googleapiexception(self):
        """Test _generate_content_raw handles GoogleAPIError."""
        self.mock_model_instance.generate_content.side_effect = google_exceptions.InternalServerError("Gemini service unavailable")
        
        with self.assertRaisesRegex(GeminiApiError, "Gemini API error during content generation: .*Gemini service unavailable"):
            self.client._generate_content_raw(["test prompt"])
        print("test_generate_content_raw_api_call_failure_googleapiexception: Passed")

    def test_generate_content_raw_api_call_failure_other_exception(self):
        """Test _generate_content_raw handles other unexpected exceptions."""
        self.mock_model_instance.generate_content.side_effect = ValueError("Unexpected value")
        
        with self.assertRaisesRegex(GeminiApiError, "An unexpected error occurred during content generation: Unexpected value"):
            self.client._generate_content_raw(["test prompt"])
        print("test_generate_content_raw_api_call_failure_other_exception: Passed")

    def test_generate_text_success(self):
        """Test generate_text successfully generates and extracts text."""
        # Mock the internal _generate_content_raw method for this public method test
        mock_raw_response = MagicMock(spec=glm_types.GenerateContentResponse)
        # Simulate a valid candidate with text parts
        part1 = MagicMock(spec=glm_types.Part)
        part1.text = "Hello "
        part2 = MagicMock(spec=glm_types.Part)
        part2.text = "World!"
        
        candidate_content = MagicMock(spec=glm_types.Content, parts=[part1, part2])
        mock_candidate = MagicMock(spec=glm_types.Candidate, content=candidate_content)
        mock_raw_response.candidates = [mock_candidate]
        mock_raw_response.prompt_feedback = None # No blocking

        with patch.object(self.client, '_generate_content_raw', return_value=mock_raw_response) as mock_raw_call:
            result_text = self.client.generate_text("A greeting")
            self.assertEqual(result_text, "Hello World!")
            mock_raw_call.assert_called_once_with(["A greeting"])
        print("test_generate_text_success: Passed")

    def test_generate_text_prompt_blocked(self):
        """Test generate_text handles a blocked prompt response."""
        mock_raw_response = MagicMock(spec=glm_types.GenerateContentResponse)
        mock_raw_response.candidates = [] # No candidates
        # Ensure BlockedReason is correctly referenced from glm_types.BlockedReason
        mock_raw_response.prompt_feedback = MagicMock(block_reason=glm_types.BlockedReason.SAFETY, block_reason_message="Blocked due to safety concerns")
        
        with patch.object(self.client, '_generate_content_raw', return_value=mock_raw_response):
            with self.assertRaisesRegex(GeminiApiError, "Prompt blocked by Gemini API. Reason: SAFETY"):
                self.client.generate_text("A risky prompt")
        print("test_generate_text_prompt_blocked: Passed")

    def test_generate_text_no_content_parts(self):
        """Test generate_text handles response with no text parts."""
        mock_raw_response = MagicMock(spec=glm_types.GenerateContentResponse)
        candidate_content = MagicMock(spec=glm_types.Content, parts=[]) # Empty parts
        mock_candidate = MagicMock(spec=glm_types.Candidate, content=candidate_content)
        mock_raw_response.candidates = [mock_candidate]
        mock_raw_response.prompt_feedback = None

        with patch.object(self.client, '_generate_content_raw', return_value=mock_raw_response):
            # Depending on implementation, this might return "" or raise an error.
            # Current implementation of generate_text would return "" if parts are empty.
            # If it should raise an error, the test needs to be adjusted.
            result_text = self.client.generate_text("A prompt for empty parts")
            self.assertEqual(result_text, "") # Or assertRaises if that's the desired behavior
        print("test_generate_text_no_content_parts: Passed (assuming empty string for empty parts is OK)")


    def test_generate_text_no_candidates(self):
        """Test generate_text handles response with no candidates."""
        mock_raw_response = MagicMock(spec=glm_types.GenerateContentResponse)
        mock_raw_response.candidates = [] # No candidates
        mock_raw_response.prompt_feedback = None # No blocking either, just empty

        with patch.object(self.client, '_generate_content_raw', return_value=mock_raw_response):
            with self.assertRaisesRegex(GeminiApiError, "No content generated or unexpected response structure"):
                self.client.generate_text("A prompt for no candidates")
        print("test_generate_text_no_candidates: Passed")
        
    def test_generate_text_api_error_from_raw_call(self):
        """Test generate_text propagates GeminiApiError from _generate_content_raw."""
        with patch.object(self.client, '_generate_content_raw', side_effect=GeminiApiError("Raw call failed")):
            with self.assertRaisesRegex(GeminiApiError, "Raw call failed"):
                self.client.generate_text("A failing prompt")
        print("test_generate_text_api_error_from_raw_call: Passed")


class TestGeminiCodeGeneration(unittest.TestCase):
    def setUp(self):
        self.api_key_patch = patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_for_code_gen"})
        self.configure_patch = patch('google.generativeai.configure')
        self.model_patch = patch('google.generativeai.GenerativeModel')

        self.mock_configure = self.configure_patch.start()
        self.mock_generative_model_class = self.model_patch.start()
        
        self.mock_model_instance = MagicMock(spec=genai.GenerativeModel)
        self.mock_generative_model_class.return_value = self.mock_model_instance
        
        self.client = GeminiClient()

    def tearDown(self):
        self.api_key_patch.stop()
        self.configure_patch.stop()
        self.model_patch.stop()

    def _prepare_mock_response(self, text_content: Optional[str] = None, 
                               prompt_block_reason: Optional[glm_types.BlockedReason] = None, 
                               finish_reason: glm_types.FinishReason = glm_types.FinishReason.STOP,
                               safety_ratings: Optional[List[glm_types.SafetyRating]] = None):
        mock_response = MagicMock(spec=glm_types.GenerateContentResponse)
        
        if prompt_block_reason:
            mock_response.prompt_feedback = MagicMock(block_reason=prompt_block_reason) # block_reason type is glm_types.BlockedReason
            mock_response.candidates = [] # Typically no candidates if prompt is blocked
        else:
            mock_response.prompt_feedback = MagicMock(block_reason=None)
            
            candidate_content = MagicMock(spec=glm_types.Content)
            if text_content is not None:
                part = MagicMock(spec=glm_types.Part)
                part.text = text_content
                candidate_content.parts = [part]
            else:
                candidate_content.parts = []
            
            candidate = MagicMock(spec=glm_types.Candidate)
            candidate.content = candidate_content
            candidate.finish_reason = finish_reason # finish_reason type is glm_types.FinishReason
            candidate.safety_ratings = safety_ratings if safety_ratings is not None else [] # safety_ratings type is list of glm_types.SafetyRating
            mock_response.candidates = [candidate]
            
        return mock_response

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_success_simple_prompt(self, mock_raw_call):
        expected_code = "def hello():\n  print('Hello')"
        mock_raw_call.return_value = self._prepare_mock_response(text_content=expected_code)
        
        code = self.client.generate_code("create a hello world function")
        
        self.assertEqual(code, expected_code)
        mock_raw_call.assert_called_once_with([self.client.DEFAULT_CODE_SYSTEM_INSTRUCTION, "create a hello world function"])
        print("test_generate_code_success_simple_prompt: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_success_with_system_instruction(self, mock_raw_call):
        custom_instruction = "Output JavaScript code."
        expected_code = "console.log('Hello');"
        mock_raw_call.return_value = self._prepare_mock_response(text_content=expected_code)

        code = self.client.generate_code("hello world in js", system_instruction=custom_instruction)
        
        self.assertEqual(code, expected_code)
        mock_raw_call.assert_called_once_with([custom_instruction, "hello world in js"])
        print("test_generate_code_success_with_system_instruction: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_success_strips_markdown_python(self, mock_raw_call):
        raw_code = "```python\ndef hello():\n  print('Hello')\n```"
        expected_code = "def hello():\n  print('Hello')"
        mock_raw_call.return_value = self._prepare_mock_response(text_content=raw_code)
        
        code = self.client.generate_code("python hello world")
        self.assertEqual(code, expected_code)
        print("test_generate_code_success_strips_markdown_python: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_success_strips_markdown_no_language(self, mock_raw_call):
        raw_code = "```\ndef hello():\n  print('Hello')\n```"
        expected_code = "def hello():\n  print('Hello')"
        mock_raw_call.return_value = self._prepare_mock_response(text_content=raw_code)

        code = self.client.generate_code("generic hello world")
        self.assertEqual(code, expected_code)
        print("test_generate_code_success_strips_markdown_no_language: Passed")
        
    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_success_strips_markdown_only_ticks(self, mock_raw_call):
        raw_code = "```\n```" # Model only returned markdown
        expected_code = "" 
        mock_raw_call.return_value = self._prepare_mock_response(text_content=raw_code)
        code = self.client.generate_code("empty code block")
        self.assertEqual(code, expected_code)
        print("test_generate_code_success_strips_markdown_only_ticks: Passed")


    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_api_error(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiApiError # Local import for test
        mock_raw_call.side_effect = GeminiApiError("API communication failed")
        
        with self.assertRaisesRegex(GeminiApiError, "API communication failed"):
            self.client.generate_code("test prompt")
        print("test_generate_code_api_error: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_prompt_safety_blocked(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiCodeGenerationError # Local import
        mock_raw_call.return_value = self._prepare_mock_response(prompt_block_reason=glm_types.BlockedReason.SAFETY)
        
        with self.assertRaisesRegex(GeminiCodeGenerationError, "Code generation prompt blocked by Gemini API. Reason: SAFETY"):
            self.client.generate_code("a risky prompt")
        print("test_generate_code_prompt_safety_blocked: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_finish_reason_safety(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiCodeGenerationError # Local import
        # Simulate that the prompt was not blocked, but the generation stopped due to safety.
        mock_raw_call.return_value = self._prepare_mock_response(text_content="potentially unsafe part", finish_reason=glm_types.FinishReason.SAFETY)
        
        with self.assertRaisesRegex(GeminiCodeGenerationError, "Code generation stopped unexpectedly. Finish Reason: SAFETY"):
            self.client.generate_code("another risky prompt")
        print("test_generate_code_finish_reason_safety: Passed")
        
    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_no_candidates(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiCodeGenerationError # Local import
        mock_response = self._prepare_mock_response(text_content="This should not be returned")
        mock_response.candidates = [] # Explicitly set no candidates
        mock_raw_call.return_value = mock_response
        
        with self.assertRaisesRegex(GeminiCodeGenerationError, "Code generation failed: No candidates returned from API."):
            self.client.generate_code("prompt for no candidates")
        print("test_generate_code_no_candidates: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_empty_parts(self, mock_raw_call):
        # This means the candidate exists, but its content.parts list is empty.
        mock_raw_call.return_value = self._prepare_mock_response(text_content=None) # No text content -> empty parts
        
        code = self.client.generate_code("prompt for empty parts")
        self.assertIsNone(code) # Current implementation returns None if no parts
        print("test_generate_code_empty_parts: Passed")
        
    @patch.object(GeminiClient, '_generate_content_raw')
    def test_generate_code_unexpected_exception(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiCodeGenerationError # Local import
        mock_raw_call.side_effect = Exception("Something totally unexpected")
        
        with self.assertRaisesRegex(GeminiCodeGenerationError, "An unexpected error occurred during code generation: Something totally unexpected"):
            self.client.generate_code("a prompt")
        print("test_generate_code_unexpected_exception: Passed")


class TestGeminiCodeExplanation(unittest.TestCase):
    def setUp(self):
        self.api_key_patch = patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_for_explain"})
        self.configure_patch = patch('google.generativeai.configure')
        self.model_patch = patch('google.generativeai.GenerativeModel')

        self.mock_configure = self.configure_patch.start()
        self.mock_generative_model_class = self.model_patch.start()
        
        self.mock_model_instance = MagicMock(spec=genai.GenerativeModel)
        self.mock_generative_model_class.return_value = self.mock_model_instance
        
        self.client = GeminiClient()
        # Use the _prepare_mock_response helper from TestGeminiCodeGeneration or redefine if needed
        # For simplicity, assuming it's accessible or we'll use a similar local one.
        self.prepare_mock_response = TestGeminiCodeGeneration._prepare_mock_response


    def tearDown(self):
        self.api_key_patch.stop()
        self.configure_patch.stop()
        self.model_patch.stop()

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_success(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiExplanationError # Local import
        code_snippet = "def greet(name):\n  return f'Hello, {name}!'"
        expected_explanation = "This Python function `greet` takes a name as input and returns a greeting string."
        
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content=expected_explanation)
        
        explanation = self.client.explain_code(code_snippet)
        
        self.assertEqual(explanation, expected_explanation)
        
        expected_user_prompt = f"Please explain the following code:\n\n```\n{code_snippet}\n```"
        mock_raw_call.assert_called_once_with([self.client.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION, expected_user_prompt])
        print("test_explain_code_success: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_success_with_custom_system_instruction(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiExplanationError # Local import
        code_snippet = "const x = 10;"
        custom_instruction = "Explain this JavaScript snippet for a beginner."
        expected_explanation = "This JavaScript code declares a constant variable `x` and assigns it the value 10."
        
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content=expected_explanation)
        
        explanation = self.client.explain_code(code_snippet, system_instruction=custom_instruction)
        
        self.assertEqual(explanation, expected_explanation)
        expected_user_prompt = f"Please explain the following code:\n\n```\n{code_snippet}\n```"
        mock_raw_call.assert_called_once_with([custom_instruction, expected_user_prompt])
        print("test_explain_code_success_with_custom_system_instruction: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_api_error(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiApiError, GeminiExplanationError # Local imports
        code_snippet = "let a = 5;"
        mock_raw_call.side_effect = GeminiApiError("Network issue")
        
        with self.assertRaisesRegex(GeminiApiError, "Network issue"):
            self.client.explain_code(code_snippet)
        print("test_explain_code_api_error: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_safety_blocked_prompt(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiExplanationError # Local import
        code_snippet = "dangerous_code();"
        # Simulate prompt blocked
        mock_raw_call.return_value = self.prepare_mock_response(self, prompt_block_reason=glm_types.BlockedReason.SAFETY)
        
        with self.assertRaisesRegex(GeminiExplanationError, "Code explanation prompt blocked by Gemini API. Reason: SAFETY"):
            self.client.explain_code(code_snippet)
        print("test_explain_code_safety_blocked_prompt: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_finish_reason_safety(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiExplanationError # Local import
        code_snippet = "some_other_code();"
        # Simulate generation stopped due to safety (not prompt block)
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content="This is part of an explanation that got cut off", finish_reason=glm_types.FinishReason.SAFETY)
        
        with self.assertRaisesRegex(GeminiExplanationError, "Code explanation stopped unexpectedly. Finish Reason: SAFETY"):
            self.client.explain_code(code_snippet)
        print("test_explain_code_finish_reason_safety: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_empty_response_parts(self, mock_raw_call):
        code_snippet = "struct Empty {}"
        # Simulate a response that is successful (STOP) but has no content parts
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content=None) 
        
        explanation = self.client.explain_code(code_snippet)
        self.assertIsNone(explanation) # Expect None if no content parts
        print("test_explain_code_empty_response_parts: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_no_candidates(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiExplanationError # Local import
        code_snippet = "int main() { return 0; }"
        mock_response = self.prepare_mock_response(self, text_content="Should not be used")
        mock_response.candidates = [] # Explicitly no candidates
        mock_raw_call.return_value = mock_response

        with self.assertRaisesRegex(GeminiExplanationError, "Code explanation failed: No candidates returned from API."):
            self.client.explain_code(code_snippet)
        print("test_explain_code_no_candidates: Passed")
        
    @patch.object(GeminiClient, '_generate_content_raw')
    def test_explain_code_unexpected_exception(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiExplanationError # Local import
        code_snippet = "fn test() {}"
        mock_raw_call.side_effect = RuntimeError("A very unexpected runtime error")
        
        with self.assertRaisesRegex(GeminiExplanationError, "An unexpected error occurred during code explanation: A very unexpected runtime error"):
            self.client.explain_code(code_snippet)
        print("test_explain_code_unexpected_exception: Passed")


class TestGeminiCodeModification(unittest.TestCase):
    def setUp(self):
        self.api_key_patch = patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_for_modify"})
        self.configure_patch = patch('google.generativeai.configure')
        self.model_patch = patch('google.generativeai.GenerativeModel')

        self.mock_configure = self.configure_patch.start()
        self.mock_generative_model_class = self.model_patch.start()
        
        self.mock_model_instance = MagicMock(spec=genai.GenerativeModel)
        self.mock_generative_model_class.return_value = self.mock_model_instance
        
        self.client = GeminiClient()
        self.prepare_mock_response = TestGeminiCodeGeneration._prepare_mock_response # Borrow helper

    def tearDown(self):
        self.api_key_patch.stop()
        self.configure_patch.stop()
        self.model_patch.stop()

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_success(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiModificationError # Local import
        original_code = "def old_func_name():\n  return 'old'"
        issue = "Rename the function to `new_func_name` and return 'new'."
        expected_modified_code = "def new_func_name():\n  return 'new'"
        
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content=expected_modified_code)
        
        modified_code = self.client.suggest_code_modification(original_code, issue)
        
        self.assertEqual(modified_code, expected_modified_code)
        
        expected_user_prompt = (
            f"Issue/Request: {issue}\n\n"
            f"Original Code:\n```\n{original_code}\n```\n\n"
            "Please provide the modified code snippet."
        )
        mock_raw_call.assert_called_once_with([self.client.DEFAULT_MODIFY_SYSTEM_INSTRUCTION, expected_user_prompt])
        print("test_suggest_modification_success: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_success_strips_markdown(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiModificationError # Local import
        original_code = "var num = 1;"
        issue = "Change to const and value to 2."
        raw_response_code = "```javascript\nconst num = 2;\n```"
        expected_modified_code = "const num = 2;"
        
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content=raw_response_code)
        
        modified_code = self.client.suggest_code_modification(original_code, issue)
        
        self.assertEqual(modified_code, expected_modified_code)
        print("test_suggest_modification_success_strips_markdown: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_api_error(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiApiError, GeminiModificationError # Local imports
        mock_raw_call.side_effect = GeminiApiError("API connection error during modification")
        
        with self.assertRaisesRegex(GeminiApiError, "API connection error during modification"):
            self.client.suggest_code_modification("code", "issue")
        print("test_suggest_modification_api_error: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_safety_blocked_prompt(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiModificationError # Local import
        mock_raw_call.return_value = self.prepare_mock_response(self, prompt_block_reason=glm_types.BlockedReason.SAFETY)
        
        with self.assertRaisesRegex(GeminiModificationError, "Code modification prompt blocked. Reason: SAFETY"):
            self.client.suggest_code_modification("code", "issue")
        print("test_suggest_modification_safety_blocked_prompt: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_finish_reason_other(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiModificationError # Local import
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content="...", finish_reason=glm_types.FinishReason.OTHER)
        
        with self.assertRaisesRegex(GeminiModificationError, "Code modification stopped unexpectedly. Finish Reason: OTHER"):
            self.client.suggest_code_modification("code", "issue")
        print("test_suggest_modification_finish_reason_other: Passed")
        
    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_no_candidates(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiModificationError # Local import
        mock_response = self.prepare_mock_response(self, text_content="This should not be used")
        mock_response.candidates = []
        mock_raw_call.return_value = mock_response

        with self.assertRaisesRegex(GeminiModificationError, "Code modification failed: No candidates from API."):
            self.client.suggest_code_modification("code", "issue")
        print("test_suggest_modification_no_candidates: Passed")

    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_empty_response_parts(self, mock_raw_call):
        mock_raw_call.return_value = self.prepare_mock_response(self, text_content=None) # No text content
        
        modified_code = self.client.suggest_code_modification("code", "issue")
        self.assertIsNone(modified_code)
        print("test_suggest_modification_empty_response_parts: Passed")
        
    @patch.object(GeminiClient, '_generate_content_raw')
    def test_suggest_modification_unexpected_exception(self, mock_raw_call):
        from jarules_agent.connectors.gemini_api import GeminiModificationError # Local import
        mock_raw_call.side_effect = ValueError("A very specific value error")
        
        with self.assertRaisesRegex(GeminiModificationError, "Unexpected error during code modification: A very specific value error"):
            self.client.suggest_code_modification("code", "issue")
        print("test_suggest_modification_unexpected_exception: Passed")


if __name__ == '__main__':
    unittest.main()
