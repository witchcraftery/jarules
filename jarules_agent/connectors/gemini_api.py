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

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any):
        """
        Initializes the GeminiClient.

        Args:
            model_name: Optional. The name of the Gemini model to use. 
                        Defaults to 'gemini-1.5-flash-latest'.
            **kwargs: Additional keyword arguments for connector-specific configuration.
                      (Currently, api_key can be passed via kwargs for flexibility,
                       but primary method is environment variable)

        Raises:
            GeminiApiKeyError: If the GEMINI_API_KEY environment variable is not set
                               and 'api_key' is not in kwargs.
        """
        super().__init__(model_name=model_name, **kwargs) # Pass kwargs to base
        
        # Prioritize API key from kwargs, then environment variable
        self.api_key = self._config.get('api_key') or os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise GeminiApiKeyError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable "
                "or pass 'api_key' in kwargs."
            )
        
        try:
            genai.configure(api_key=self.api_key)
        except Exception as e: # Broad exception for configure issues
            raise GeminiClientError(f"Failed to configure Gemini API: {e}", underlying_exception=e) from e

        # Use self.model_name from BaseLLMConnector, which is set by super().__init__
        # If it's None (not passed to __init__), use the default.
        effective_model_name = self.model_name or self.DEFAULT_MODEL_NAME
        try:
            self.model = genai.GenerativeModel(effective_model_name)
            print(f"GeminiClient initialized successfully with model: {effective_model_name}")
            if self.model_name != effective_model_name and self.model_name is not None:
                # If a specific model was requested but default was used because it was None,
                # this branch won't be hit. This is more if base class logic changes model_name.
                print(f"Note: Requested model '{self.model_name}' was overridden to '{effective_model_name}'.")
            elif self.model_name is None:
                 self.model_name = effective_model_name # Store the default if none was passed

        except Exception as e: # Broad exception for model init issues
            raise GeminiClientError(f"Failed to initialize Gemini model '{effective_model_name}': {e}", underlying_exception=e) from e

    def _generate_content_raw(self, prompt_parts: List[Any], generation_config: Optional[genai.types.GenerationConfig] = None, safety_settings: Optional[List[Dict]] = None, **kwargs: Any) -> genai.types.GenerateContentResponse:
        """
        Private helper to make a raw call to the Gemini API's generate_content.

        Args:
            prompt_parts: A list of parts for the prompt (e.g., strings, images).
            generation_config: Optional. Configuration for the generation.
            safety_settings: Optional. Safety settings for the request.

        Returns:
            The raw response object from `model.generate_content()`.

        Raises:
            GeminiApiError: If an API error occurs during generation.
        """
        if not self.model: # Should not happen if __init__ succeeded
            raise GeminiClientError("Gemini model not initialized.")
        
        print(f"Sending prompt to Gemini: {prompt_parts}")
        try:
            response = self.model.generate_content(
                contents=prompt_parts,
                generation_config=generation_config,
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
                 raise GeminiApiError(f"Prompt blocked by Gemini API. Reason: {response.prompt_feedback.block_reason.name}. Details: {response.prompt_feedback}")

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

    def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """
        Generates code using the Gemini API.

        Args:
            user_prompt: The user's direct request for code generation.
            system_instruction: Optional. A guiding instruction for the model. 
                                If None, a default instruction promoting direct code output is used.

        Returns:
            The generated code as a string, or None if generation fails or is blocked.

        Raises:
            GeminiCodeGenerationError: If the prompt is blocked for safety reasons or generation stops unexpectedly.
            GeminiApiError: For other API-related errors during the call.
        """
        active_system_instruction = system_instruction if system_instruction is not None else self.DEFAULT_CODE_SYSTEM_INSTRUCTION
        
        prompt_parts = []
        if active_system_instruction: # Ensure it's not an empty string if user explicitly passed ""
            prompt_parts.append(active_system_instruction)
        prompt_parts.append(user_prompt)

        try:
            response = self._generate_content_raw(prompt_parts)

            # Check for safety blocks or problematic finish reasons first
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_msg = f"Code generation prompt blocked by Gemini API. Reason: {response.prompt_feedback.block_reason.name}. Details: {response.prompt_feedback}"
                print(error_msg)
                raise GeminiCodeGenerationError(error_msg)

            if not response.candidates:
                error_msg = "Code generation failed: No candidates returned from API."
                print(error_msg)
                # This could be due to a block not caught by prompt_feedback, or other issues.
                # For instance, if all candidates were filtered out by safety settings on the request (not just prompt_feedback).
                raise GeminiCodeGenerationError(error_msg)

            candidate = response.candidates[0]
            if candidate.finish_reason not in [genai.types.FinishReason.STOP, genai.types.FinishReason.MAX_TOKENS]:
                # Other reasons include SAFETY, RECITATION, OTHER, UNKNOWN, UNSET
                error_msg = f"Code generation stopped unexpectedly. Finish Reason: {candidate.finish_reason.name}. Details: {candidate.safety_ratings if candidate.safety_ratings else 'N/A'}"
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

    def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """
        Explains a given code snippet using the Gemini API.

        Args:
            code_snippet: The string containing the code to be explained.
            system_instruction: Optional. A guiding instruction for the model.
                                If None, a default instruction for explanation is used.

        Returns:
            The generated explanation as a string, or None if generation fails or is blocked.

        Raises:
            GeminiExplanationError: If the prompt is blocked for safety reasons or generation stops unexpectedly.
            GeminiApiError: For other API-related errors during the call.
        """
        active_system_instruction = system_instruction if system_instruction is not None else self.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION
        
        # Constructing prompt parts for explanation
        # It's often good to clearly delineate the code to be explained.
        user_prompt_for_explanation = f"Please explain the following code:\n\n```\n{code_snippet}\n```"

        prompt_parts = []
        if active_system_instruction:
            prompt_parts.append(active_system_instruction)
        prompt_parts.append(user_prompt_for_explanation)

        try:
            response = self._generate_content_raw(prompt_parts)

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_msg = f"Code explanation prompt blocked by Gemini API. Reason: {response.prompt_feedback.block_reason.name}. Details: {response.prompt_feedback}"
                print(error_msg)
                raise GeminiExplanationError(error_msg)

            if not response.candidates:
                error_msg = "Code explanation failed: No candidates returned from API."
                print(error_msg)
                raise GeminiExplanationError(error_msg)
            
            candidate = response.candidates[0]
            if candidate.finish_reason not in [genai.types.FinishReason.STOP, genai.types.FinishReason.MAX_TOKENS]:
                error_msg = f"Code explanation stopped unexpectedly. Finish Reason: {candidate.finish_reason.name}. Details: {candidate.safety_ratings if candidate.safety_ratings else 'N/A'}"
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

    def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """
        Suggests modifications to a given code snippet based on an issue description.

        Args:
            code_snippet: The string containing the code to be modified.
            issue_description: A natural language description of the desired modification or fix.
            system_instruction: Optional. A guiding instruction for the model.
                                If None, a default instruction for modification is used.

        Returns:
            The suggested modified code as a string, or None if generation fails/is blocked.

        Raises:
            GeminiModificationError: If the prompt is blocked or generation stops unexpectedly.
            GeminiApiError: For other API-related errors.
        """
        active_system_instruction = system_instruction if system_instruction is not None else self.DEFAULT_MODIFY_SYSTEM_INSTRUCTION
        
        user_prompt_for_modification = (
            f"Issue/Request: {issue_description}\n\n"
            f"Original Code:\n```\n{code_snippet}\n```\n\n"
            "Please provide the modified code snippet."
        )

        prompt_parts = [active_system_instruction, user_prompt_for_modification]

        try:
            response = self._generate_content_raw(prompt_parts)

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_msg = f"Code modification prompt blocked. Reason: {response.prompt_feedback.block_reason.name}"
                print(error_msg)
                raise GeminiModificationError(error_msg)

            if not response.candidates:
                error_msg = "Code modification failed: No candidates from API."
                print(error_msg)
                raise GeminiModificationError(error_msg)

            candidate = response.candidates[0]
            if candidate.finish_reason not in [genai.types.FinishReason.STOP, genai.types.FinishReason.MAX_TOKENS]:
                error_msg = f"Code modification stopped unexpectedly. Finish Reason: {candidate.finish_reason.name}"
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
