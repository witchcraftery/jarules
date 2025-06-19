# jarules_agent/connectors/gemini_api.py

import os
from typing import Optional, List, Any, Dict
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions # For specific API errors
from .base_llm_connector import BaseLLMConnector, LLMConnectorError

# --- Custom Exceptions ---
class GeminiClientError(LLMConnectorError):
    """Base exception for GeminiClient errors."""
    pass

class GeminiApiKeyError(GeminiClientError):
    """Raised when the Gemini API key is not configured."""
    pass

class GeminiApiError(GeminiClientError):
    """Raised for errors during Gemini API calls."""
    def __init__(self, message: str, underlying_exception: Optional[Exception] = None):
        super().__init__(message)
        self.underlying_exception = underlying_exception

class GeminiCodeGenerationError(GeminiClientError):
    """Raised for specific errors during code generation, e.g., safety blocks."""
    pass

class GeminiExplanationError(GeminiClientError):
    """Raised for specific errors during code explanation, e.g., safety blocks."""
    pass

class GeminiModificationError(GeminiClientError):
    """Raised for specific errors during code modification suggestions, e.g., safety blocks."""
    pass

class GeminiClient(BaseLLMConnector):
    """
    A client for interacting with the Google Gemini API.
    """
    DEFAULT_MODEL_NAME = 'gemini-1.5-flash-latest' # A good default, you can change if needed

    @staticmethod
    def _get_enum_name(enum_value):
        """Helper to safely get name from enum or return string representation."""
        if hasattr(enum_value, 'name'):
            return enum_value.name
        return str(enum_value)

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any):
        """
        Initializes the GeminiClient.

        Args:
            model_name: Optional. The name of the Gemini model to use. 
                        Defaults to 'gemini-1.5-flash-latest'.
            **kwargs: Additional keyword arguments for connector-specific configuration,
                      including 'api_key', 'default_system_prompt', 'generation_params'.

        Raises:
            GeminiApiKeyError: If the API key is not found.
            GeminiClientError: For other configuration or initialization issues.
        """
        super().__init__(model_name=model_name, **kwargs) 
        
        # 1. API Key Handling
        # Prioritize API key from self._config (populated by kwargs in BaseLLMConnector), then environment variable
        self.api_key = self._config.get('api_key') or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiApiKeyError(
                "Gemini API key not found. Pass 'api_key' in LLMManager config or "
                "set GEMINI_API_KEY environment variable."
            )
        
        try:
            genai.configure(api_key=self.api_key)
        except Exception as e:
            raise GeminiClientError(f"Failed to configure Gemini API: {e}", underlying_exception=e)

        # 2. Default System Prompt Handling
        self.default_system_prompt: Optional[str] = self._config.get('default_system_prompt')

        # 3. Generation Parameters Handling
        self.default_generation_config: Optional[genai.types.GenerationConfig] = None
        generation_params_dict = self._config.get('generation_params')
        if isinstance(generation_params_dict, dict):
            try:
                # Ensure only valid keys for GenerationConfig are passed
                # Valid keys are: temperature, top_p, top_k, candidate_count, max_output_tokens, stop_sequences
                valid_gen_config_keys = {
                    "temperature", "top_p", "top_k", "candidate_count", 
                    "max_output_tokens", "stop_sequences"
                }
                filtered_params = {k: v for k, v in generation_params_dict.items() if k in valid_gen_config_keys}
                if filtered_params:
                    self.default_generation_config = genai.types.GenerationConfig(**filtered_params)
            except Exception as e: # Catch potential errors during GenerationConfig creation
                raise GeminiClientError(f"Invalid 'generation_params' in config: {e}", underlying_exception=e)

        # Model Initialization (using self.model_name from BaseLLMConnector)
        effective_model_name = self.model_name or self.DEFAULT_MODEL_NAME
        try:
            self.model = genai.GenerativeModel(effective_model_name)
            # Update self.model_name if the default was used and no specific model was requested.
            if self.model_name is None:
                 self.model_name = effective_model_name 
            print(f"GeminiClient initialized successfully with model: {self.model_name}")
        except Exception as e:
            raise GeminiClientError(f"Failed to initialize Gemini model '{self.model_name}': {e}", underlying_exception=e)

    def check_availability(self) -> Dict[str, Any]:
        """
        Checks the availability and status of the Google Gemini API.

        Makes a lightweight call to list models to verify connectivity and authentication.

        Returns:
            A dictionary with keys 'available' (bool) and 'details' (str).
            Example: {'available': True, 'details': 'Gemini API is available and authentication is successful.'}
                     {'available': False, 'details': 'Error message...'}
        """
        if not self.api_key: # Should have been caught by __init__, but as a safeguard
            return {'available': False, 'details': 'Gemini API key is not configured in the client.'}

        try:
            # Ensure genai is configured for this instance check, though it's done in __init__
            # This is more of a double check if the instance is long-lived and something changed.
            # However, genai.configure is global, so __init__ should suffice.
            # The most direct check is to try a lightweight API call.

            models = genai.list_models()
            # Check if we actually got a list of models and specific model types we might expect
            # For example, check if any model has 'generateContent' in its supported_generation_methods
            can_generate = any('generateContent' in model.supported_generation_methods for model in models)

            if models and can_generate:
                return {'available': True, 'details': 'Gemini API is available and authentication is successful. Found usable models.'}
            elif models:
                return {'available': False, 'details': 'Gemini API is responding but no models suitable for content generation were found.'}
            else: # Should not happen if list_models() succeeded without error and returned empty
                return {'available': False, 'details': 'Gemini API is responding but returned an empty list of models.'}

        except google_exceptions.Unauthenticated as e:
            return {'available': False, 'details': f"Gemini API authentication failed: {e}. Please check your API key."}
        except google_exceptions.PermissionDenied as e:
            return {'available': False, 'details': f"Gemini API permission denied: {e}. The API key may not have the necessary permissions or the API may not be enabled in your Google Cloud project."}
        except google_exceptions.ResourceExhausted as e:
            # This could indicate quota issues, which means the API is available but not usable for this request.
            return {'available': False, 'details': f"Gemini API quota likely exceeded: {e}"}
        except google_exceptions.GoogleAPIError as e: # Catch other Google API errors
            return {'available': False, 'details': f"Gemini API error: {e}"}
        except GeminiApiKeyError as e: # Should be caught in __init__
             return {'available': False, 'details': f"Gemini API Key Error: {e}"}
        except Exception as e: # Catch any other unexpected errors (e.g., network issues not caught by GoogleAPIError)
            return {'available': False, 'details': f"An unexpected error occurred while checking Gemini API availability: {e}"}

    def _generate_content_raw(self, prompt_parts: List[Any], method_generation_config: Optional[genai.types.GenerationConfig] = None, safety_settings: Optional[List[Dict]] = None, **kwargs: Any) -> genai.types.GenerateContentResponse:
        """
        Private helper to make a raw call to the Gemini API's generate_content.

        Args:
            prompt_parts: A list of parts for the prompt (e.g., strings, images).
            method_generation_config: Optional. Configuration for the generation, passed from calling method.
            safety_settings: Optional. Safety settings for the request.

        Returns:
            The raw response object from `model.generate_content()`.

        Raises:
            GeminiApiError: If an API error occurs during generation.
        """
        if not self.model: # Should not happen if __init__ succeeded
            raise GeminiClientError("Gemini model not initialized.")
        
        # Prioritize generation config: method > instance default > API default (None)
        final_generation_config = method_generation_config if method_generation_config is not None else self.default_generation_config

        print(f"Sending prompt to Gemini: {prompt_parts}. Config: {final_generation_config}")
        try:
            response = self.model.generate_content(
                contents=prompt_parts,
                generation_config=final_generation_config,
                safety_settings=safety_settings
            )
            return response
        except google_exceptions.GoogleAPIError as e:
            error_message = f"Gemini API error during content generation: {e}"
            print(error_message)
            raise GeminiApiError(error_message, underlying_exception=e) from e
        except Exception as e: # Catch any other unexpected errors during generation
            error_message = f"An unexpected error occurred during content generation: {e}"
            print(error_message)
            raise GeminiApiError(error_message, underlying_exception=e) from e

    # Placeholder for a more user-friendly public method
    def generate_text(self, prompt: str) -> str:
        """
        Generates text using the Gemini API with the configured model.

        Args:
            prompt: The input prompt (string) for the Gemini API.

        Returns:
            The generated text as a string.

        Raises:
            GeminiApiError: If the API call fails or the response is malformed.
        """
        try:
            response = self._generate_content_raw([prompt])
            
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 raise GeminiApiError(f"Prompt blocked by Gemini API. Reason: {self._get_enum_name(response.prompt_feedback.block_reason)}. Details: {response.prompt_feedback}")

            if response.candidates and response.candidates[0].content.parts:
                return "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
            else: # No candidates or no parts in the first candidate
                # This case might also catch some implicit blocks if candidates list is empty
                # and no explicit prompt_feedback.block_reason was given.
                finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                raise GeminiApiError(f"No content generated or unexpected response structure from Gemini API. Finish reason: {finish_reason}", 
                                     underlying_exception=ValueError(f"Full response: {response}"))

        except GeminiApiError: # Re-raise if it's already our custom type
            raise
        except Exception as e: # Wrap other exceptions
            raise GeminiApiError(f"Failed to generate text: {e}", underlying_exception=e) from e

    DEFAULT_CODE_SYSTEM_INSTRUCTION = (
        "You are an expert AI coding assistant. "
        "Please provide only the code requested by the user, without any additional explanatory text, "
        "markdown formatting, or language indicators (like ```python) surrounding the code block. "
        "If you need to include comments, ensure they are within the code block itself (e.g., using # for Python)."
    )

    def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        """
        Generates code using the Gemini API.

        Args:
            user_prompt: The user's direct request for code generation.
            system_instruction: Optional. A guiding instruction for the model.
                                If None, a default instruction promoting direct code output is used.
            history: Optional. A list of dictionaries representing the conversation history.

        Returns:
            The generated code as a string, or None if generation fails or is blocked.

        Raises:
            GeminiCodeGenerationError: If the prompt is blocked for safety reasons or generation stops unexpectedly.
            GeminiApiError: For other API-related errors during the call.
        """
        if system_instruction is not None:
            active_system_instruction = system_instruction
        elif self.default_system_prompt is not None:
            active_system_instruction = self.default_system_prompt
        else:
            active_system_instruction = self.DEFAULT_CODE_SYSTEM_INSTRUCTION

        # Construct content for Gemini API
        # History is expected to be [{"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}]
        # Gemini expects [{"role": "user", "parts": ["..."]}, {"role": "model", "parts": ["..."]}]
        gemini_contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                # Gemini uses 'parts' which is a list of strings (or other Part types)
                # Assuming 'text' key from input history, if not, adapt as needed.
                content_text = item.get("text") or item.get("content") # Accommodate "content" if used
                if content_text:
                     gemini_contents.append({"role": role, "parts": [content_text]})
                # If history item is malformed (e.g. no text/content), it's skipped.

        # System instruction handling (as per Gemini's recommendation, often part of the first user message or separate system message if API supports)
        # For generate_content, system instructions are typically prepended or handled by model tuning.
        # Here, we'll prepend it to the user prompt if it's not already part of the history construction logic.
        # If a system instruction exists, it should ideally be the first message or part of the model's configuration.
        # Let's assume the current approach is to prepend system instruction to the user prompt if no history,
        # or ensure it's the first "system" message if history is present and the API supports system roles distinctly.
        # For Gemini, system instructions can be part of the `contents` list.
        # If there's a system instruction and no history, we can make it the first "user" turn with system context.
        # Or, if the model supports a dedicated system instruction field (some Gemini models via specific tuning/API structures do).
        # For `genai.GenerativeModel.generate_content(contents=...)`, system instructions are often part of the `contents` list.
        # Let's try to put the system instruction as the first element if it exists.
        
        final_prompt_parts = []
        if active_system_instruction: # Ensure it's not an empty string
            # Gemini doesn't have a dedicated "system" role in the same way as OpenAI for its `contents` argument.
            # It's common to put system instructions as the first "user" message or as part of the model's configuration.
            # If history is empty, we prepend system instruction to the user_prompt.
            # If history is present, the system instruction might need to be the first message in `gemini_contents`
            # or integrated into the first user message.
            # For simplicity, if history is NOT provided, we treat system_instruction + user_prompt as the first turn.
            # If history IS provided, we assume system_instruction was part of its construction or is handled by the first history message.
            # This logic might need refinement based on how system instructions are best handled with history in Gemini.
            # A common pattern is: System Prompt, User Prompt, Model Response, User Prompt, Model Response ...
            # So, if history is empty, system prompt + user prompt becomes the first message.
            # If history exists, system prompt should have been the *very first* message.
            # The current history format {"role": "user/assistant", "text": ...} doesn't explicitly include a system message *before* the first user message.
            # So, we will add the system instruction before the current user_prompt if no history,
            # and prepend it to gemini_contents if history is present.

            # If history is provided, we should ensure the system message is the first message.
            # This is a bit tricky if history already has a "system" message or if the system message should always precede history.
            # For now, let's assume system_instruction applies to the current turn.
            # If gemini_contents is empty (no history), then the first user message will include system instructions.
            if not gemini_contents and active_system_instruction:
                 final_prompt_parts.append({"role": "user", "parts": [active_system_instruction, user_prompt]})
            else:
                # If history exists, we prepend the system instruction as a new user message if it's not already there.
                # This might lead to "user: system_instr", "user: history_user_msg1", "model: history_model_msg1" etc.
                # which is not ideal.
                # A better approach for history: the system instruction should be part of the initial context.
                # Let's refine: system_instruction is for the *current* user_prompt.
                # The `gemini_contents` will be history. The current turn is `user_prompt` potentially guided by `system_instruction`.
                # Gemini's `generate_content` takes a list of `Content` objects (dicts).
                # The prompt to the model is the entire list.
                # System instructions are often provided in the `system_instruction` parameter of `GenerativeModel`
                # or as the first element in the `contents` list.
                # `genai.GenerativeModel(model_name, system_instruction=...)` is one way.
                # Or `self.model.generate_content(contents=[{'role':'system', 'parts': ["..."]}, user_message_1, model_message_1 ...])`
                # However, `genai.Content` doesn't officially list 'system' as a role. It's 'user' or 'model'.
                # So, system instructions are typically prepended to the first user message or set at model init.
                # Let's assume default_system_prompt or passed system_instruction modifies the *current* user_prompt.

                # Add history to final_prompt_parts
                final_prompt_parts.extend(gemini_contents)
                # Add current user prompt, potentially prefixed by system instruction if it wasn't for the whole history
                current_turn_parts = []
                if active_system_instruction and not history: # Apply system instruction only if no history, assuming history already accounted for it
                    current_turn_parts.append(active_system_instruction)
                current_turn_parts.append(user_prompt)
                final_prompt_parts.append({"role": "user", "parts": current_turn_parts})

        else: # No system instruction
            final_prompt_parts.extend(gemini_contents)
            final_prompt_parts.append({"role": "user", "parts": [user_prompt]})


        # For now, using instance default generation config.
        # Could extend to allow method-specific overrides via kwargs if needed.
        current_generation_config = self.default_generation_config

        try:
            # Ensure final_prompt_parts is not empty if user_prompt was empty and no history
            if not final_prompt_parts:
                if user_prompt: # Should always have user_prompt unless it's an error
                    final_prompt_parts.append({"role": "user", "parts": [user_prompt]})
                else:
                    # This case should ideally be validated before calling _generate_content_raw
                    raise GeminiCodeGenerationError("User prompt is empty and no history provided.")

            response = self._generate_content_raw(final_prompt_parts, method_generation_config=current_generation_config)

            # Check for safety blocks or problematic finish reasons first
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_msg = f"Code generation prompt blocked by Gemini API. Reason: {self._get_enum_name(response.prompt_feedback.block_reason)}. Details: {response.prompt_feedback}"
                print(error_msg)
                raise GeminiCodeGenerationError(error_msg)

            if not response.candidates:
                error_msg = "Code generation failed: No candidates returned from API."
                print(error_msg)
                # This could be due to a block not caught by prompt_feedback, or other issues.
                # For instance, if all candidates were filtered out by safety settings on the request (not just prompt_feedback).
                raise GeminiCodeGenerationError(error_msg)

            candidate = response.candidates[0]
            if candidate.finish_reason not in [genai.protos.Candidate.FinishReason.STOP, genai.protos.Candidate.FinishReason.MAX_TOKENS]:
                # Other reasons include SAFETY, RECITATION, OTHER, UNKNOWN, UNSET
                error_msg = f"Code generation stopped unexpectedly. Finish Reason: {self._get_enum_name(candidate.finish_reason)}. Details: {candidate.safety_ratings if candidate.safety_ratings else 'N/A'}"
                print(error_msg)
                raise GeminiCodeGenerationError(error_msg)

            if not candidate.content or not candidate.content.parts:
                print("Code generation resulted in no content parts.")
                return None # Or raise error if this is unexpected

            generated_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))

            # Strip common markdown code block delimiters
            # Common patterns: ```python\n...\n``` or ```\n...\n```
            if generated_text.startswith("```") and generated_text.endswith("```"):
                lines = generated_text.splitlines()
                if len(lines) > 1 and lines[0].startswith("```"): # Check if first line is ```python or just ```
                    start_line_offset = 1
                else: # Should not happen if it starts and ends with ``` but check anyway
                    start_line_offset = 0 
                
                if lines[-1] == "```":
                    end_line_offset = -1
                else: # Should not happen with the endswith check, but for robustness
                    end_line_offset = len(lines)

                # If after stripping ``` and potential language, we are left with empty or just newlines,
                # it means the model might have only returned the markdown.
                core_content_lines = lines[start_line_offset:end_line_offset]
                if not any(line.strip() for line in core_content_lines): # All lines are empty or whitespace
                    generated_text = "" # Treat as empty if only markdown was returned
                else:
                    generated_text = "\n".join(core_content_lines)


            return generated_text.strip() # Strip leading/trailing whitespace from the final code.

        except GeminiApiError as e: # Re-raise if it's already our specific API error
            print(f"Gemini API error during code generation: {e}")
            raise
        except GeminiCodeGenerationError: # Re-raise if it's already our specific code gen error
            raise
        except Exception as e: # Wrap other unexpected exceptions
            error_msg = f"An unexpected error occurred during code generation: {e}"
            print(error_msg)
            raise GeminiCodeGenerationError(error_msg, underlying_exception=e) from e

    DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION = (
        "You are a helpful coding assistant. Explain the following code snippet clearly and concisely. "
        "Describe its purpose, how it works, and any key components or logic."
    )

    def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        """
        Explains a given code snippet using the Gemini API.

        Args:
            code_snippet: The string containing the code to be explained.
            system_instruction: Optional. A guiding instruction for the model.
                                If None, a default instruction for explanation is used.
            history: Optional. A list of dictionaries representing the conversation history.

        Returns:
            The generated explanation as a string, or None if generation fails or is blocked.

        Raises:
            GeminiExplanationError: If the prompt is blocked for safety reasons or generation stops unexpectedly.
            GeminiApiError: For other API-related errors during the call.
        """
        if system_instruction is not None:
            active_system_instruction = system_instruction
        elif self.default_system_prompt is not None:
            active_system_instruction = self.default_system_prompt
        else:
            active_system_instruction = self.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION

        gemini_contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                content_text = item.get("text") or item.get("content")
                if content_text:
                    gemini_contents.append({"role": role, "parts": [content_text]})

        user_prompt_for_explanation = f"Please explain the following code:\n\n```\n{code_snippet}\n```"

        final_prompt_parts = []
        if not gemini_contents and active_system_instruction:
            final_prompt_parts.append({"role": "user", "parts": [active_system_instruction, user_prompt_for_explanation]})
        else:
            final_prompt_parts.extend(gemini_contents)
            current_turn_parts = []
            if active_system_instruction and not history:
                 current_turn_parts.append(active_system_instruction)
            current_turn_parts.append(user_prompt_for_explanation)
            final_prompt_parts.append({"role": "user", "parts": current_turn_parts})


        current_generation_config = self.default_generation_config

        try:
            if not final_prompt_parts:
                 raise GeminiExplanationError("User prompt for explanation is empty and no history provided.")
            response = self._generate_content_raw(final_prompt_parts, method_generation_config=current_generation_config)

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_msg = f"Code explanation prompt blocked by Gemini API. Reason: {self._get_enum_name(response.prompt_feedback.block_reason)}. Details: {response.prompt_feedback}"
                print(error_msg)
                raise GeminiExplanationError(error_msg)

            if not response.candidates:
                error_msg = "Code explanation failed: No candidates returned from API."
                print(error_msg)
                raise GeminiExplanationError(error_msg)
            
            candidate = response.candidates[0]
            if candidate.finish_reason not in [genai.protos.Candidate.FinishReason.STOP, genai.protos.Candidate.FinishReason.MAX_TOKENS]:
                error_msg = f"Code explanation stopped unexpectedly. Finish Reason: {self._get_enum_name(candidate.finish_reason)}. Details: {candidate.safety_ratings if candidate.safety_ratings else 'N/A'}"
                print(error_msg)
                raise GeminiExplanationError(error_msg)

            if not candidate.content or not candidate.content.parts:
                print("Code explanation resulted in no content parts.")
                return None 
            
            explanation_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
            return explanation_text.strip()

        except GeminiApiError as e:
            print(f"Gemini API error during code explanation: {e}")
            raise
        except GeminiExplanationError:
            raise
        except Exception as e:
            error_msg = f"An unexpected error occurred during code explanation: {e}"
            print(error_msg)
            raise GeminiExplanationError(error_msg, underlying_exception=e) from e

    DEFAULT_MODIFY_SYSTEM_INSTRUCTION = (
        "You are an expert AI coding assistant. You are tasked with modifying the provided code snippet based on a user's issue description or request. "
        "Provide the complete modified code snippet. Enclose the final, complete code snippet in a standard markdown code block (e.g., ```python ... ``` or ``` ... ```). "
        "Do not include any other explanatory text outside the code block unless it's part of the code comments."
    )

    def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        """
        Suggests modifications to a given code snippet based on an issue description.

        Args:
            code_snippet: The string containing the code to be modified.
            issue_description: A natural language description of the desired modification or fix.
            system_instruction: Optional. A guiding instruction for the model.
                                If None, a default instruction for modification is used.
            history: Optional. A list of dictionaries representing the conversation history.

        Returns:
            The suggested modified code as a string, or None if generation fails/is blocked.

        Raises:
            GeminiModificationError: If the prompt is blocked or generation stops unexpectedly.
            GeminiApiError: For other API-related errors.
        """
        if system_instruction is not None:
            active_system_instruction = system_instruction
        elif self.default_system_prompt is not None:
            active_system_instruction = self.default_system_prompt
        else:
            active_system_instruction = self.DEFAULT_MODIFY_SYSTEM_INSTRUCTION

        gemini_contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                content_text = item.get("text") or item.get("content")
                if content_text:
                    gemini_contents.append({"role": role, "parts": [content_text]})
        
        user_prompt_for_modification = (
            f"Issue/Request: {issue_description}\n\n"
            f"Original Code:\n```\n{code_snippet}\n```\n\n"
            "Please provide the modified code snippet."
        )

        final_prompt_parts = []
        if not gemini_contents and active_system_instruction:
            final_prompt_parts.append({"role": "user", "parts": [active_system_instruction, user_prompt_for_modification]})
        else:
            final_prompt_parts.extend(gemini_contents)
            current_turn_parts = []
            if active_system_instruction and not history: # Apply system instruction if no history
                current_turn_parts.append(active_system_instruction)
            current_turn_parts.append(user_prompt_for_modification)
            final_prompt_parts.append({"role": "user", "parts": current_turn_parts})
        
        current_generation_config = self.default_generation_config

        try:
            if not final_prompt_parts:
                raise GeminiModificationError("User prompt for modification is empty and no history provided.")
            response = self._generate_content_raw(final_prompt_parts, method_generation_config=current_generation_config)

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_msg = f"Code modification prompt blocked. Reason: {self._get_enum_name(response.prompt_feedback.block_reason)}"
                print(error_msg)
                raise GeminiModificationError(error_msg)

            if not response.candidates:
                error_msg = "Code modification failed: No candidates from API."
                print(error_msg)
                raise GeminiModificationError(error_msg)

            candidate = response.candidates[0]
            if candidate.finish_reason not in [genai.protos.Candidate.FinishReason.STOP, genai.protos.Candidate.FinishReason.MAX_TOKENS]:
                error_msg = f"Code modification stopped unexpectedly. Finish Reason: {self._get_enum_name(candidate.finish_reason)}"
                print(error_msg)
                raise GeminiModificationError(error_msg)

            if not candidate.content or not candidate.content.parts:
                print("Code modification resulted in no content parts.")
                return None
            
            modified_code_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))

            # Strip markdown, similar to generate_code
            if modified_code_text.startswith("```") and modified_code_text.endswith("```"):
                lines = modified_code_text.splitlines()
                if len(lines) > 1 and lines[0].startswith("```"):
                    start_line_offset = 1
                else:
                    start_line_offset = 0
                
                if lines[-1] == "```":
                    end_line_offset = -1
                else:
                    end_line_offset = len(lines)
                
                core_content_lines = lines[start_line_offset:end_line_offset]
                if not any(line.strip() for line in core_content_lines):
                    modified_code_text = ""
                else:
                    modified_code_text = "\n".join(core_content_lines)
            
            return modified_code_text.strip()

        except GeminiApiError as e:
            print(f"Gemini API error during code modification: {e}")
            raise
        except GeminiModificationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during code modification: {e}"
            print(error_msg)
            raise GeminiModificationError(error_msg, underlying_exception=e) from e


# Example usage (optional, for quick testing if GEMINI_API_KEY is set)
if __name__ == '__main__':
    # This example is illustrative. In a real application, you might not pass
    # the API key directly in kwargs if it's expected to be in the environment.
    # However, this shows how kwargs could be used by the base or this class.
    # For this example, we'll rely on the environment variable.
    # Ensure GEMINI_API_KEY is set in your environment before running.
    
    if not os.environ.get("GEMINI_API_KEY"):
        print("Please set the GEMINI_API_KEY environment variable to test.")
    else:
        try:
            # Initialize without explicit model_name to use default
            client = GeminiClient() 
            print(f"\n--- Using model: {client.model_name} ---")

            # 1. Test generate_code
            print("\n--- Testing generate_code ---")
            python_prompt = "Create a Python function that returns the square of a number."
            generated_python_code = client.generate_code(python_prompt)
            if generated_python_code:
                print("Generated Python Code:\n", generated_python_code)
            else:
                print("No Python code generated or an issue occurred.")

            # 2. Test explain_code
            print("\n--- Testing explain_code ---")
            code_to_explain = "def hello(name):\n  print(f'Hello, {name}!')"
            explanation = client.explain_code(code_to_explain)
            if explanation:
                print(f"Explanation for:\n{code_to_explain}\n---\n{explanation}")
            else:
                print("No explanation generated or an issue occurred.")

            # 3. Test suggest_code_modification
            print("\n--- Testing suggest_code_modification ---")
            original_code = "def add(a,b):\n  return a-b # Bug here"
            issue = "This function should add two numbers, not subtract."
            modified_code = client.suggest_code_modification(original_code, issue)
            if modified_code:
                print(f"Original Code:\n{original_code}\nIssue: {issue}\n---\nSuggested Modification:\n{modified_code}")
            else:
                print("No modification suggested or an issue occurred.")
            
            # 4. Test with a non-default model (if you have access to others like 1.0 Pro)
            # try:
            #     pro_client = GeminiClient(model_name="gemini-1.0-pro") # Example
            #     print(f"\n--- Using model: {pro_client.model_name} ---")
            #     pro_response = pro_client.generate_code("Create a simple HTML page structure.")
            #     if pro_response:
            #         print("Generated HTML (from Pro model if different):\n", pro_response)
            #     else:
            #         print("No code generated from Pro model.")
            # except GeminiClientError as e:
            #     print(f"Could not initialize or use Pro model: {e}")


        except GeminiApiKeyError as e:
            print(f"API Key Error: {e}")
        except GeminiCodeGenerationError as e:
            print(f"Code Generation Error: {e}")
        except GeminiExplanationError as e:
            print(f"Explanation Error: {e}")
        except GeminiModificationError as e:
            print(f"Modification Error: {e}")
        except GeminiClientError as e: # Catch other GeminiClient specific errors
            print(f"Gemini Client Error: {e}")
        except LLMConnectorError as e: # Catch base connector errors
            print(f"LLM Connector Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during testing: {e}")
# if __name__ == '__main__':
