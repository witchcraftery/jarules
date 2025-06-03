# jarules_agent/connectors/ollama_connector.py

import os
import json # For potential structured responses if Ollama supports it directly
from typing import Optional, List, Any, Dict

# Attempt to import ollama, but don't fail catastrophically if not installed yet,
# as the user might be setting up the environment.
# The LLMManager should handle the case where a connector cannot be initialized.
try:
    import ollama
except ImportError:
    ollama = None # Placeholder if not installed

from .base_llm_connector import BaseLLMConnector, LLMConnectorError

# --- Custom Exceptions ---
class OllamaConnectorError(LLMConnectorError):
    """Base exception for OllamaConnector errors."""
    pass

class OllamaNotInstalledError(OllamaConnectorError):
    """Raised when the ollama library is not installed."""
    pass

class OllamaApiError(OllamaConnectorError):
    """Raised for errors during Ollama API calls (e.g., connection issues, model not found)."""
    pass

class OllamaModelNotAvailableError(OllamaApiError):
    """Raised specifically when a model is not available or not pulled in Ollama."""
    pass

class OllamaGenerationError(OllamaConnectorError):
    """Raised for specific errors during text generation, e.g., empty response."""
    pass

class OllamaCodeGenerationError(OllamaGenerationError):
    """Raised for specific errors during code generation."""
    pass

class OllamaExplanationError(OllamaGenerationError):
    """Raised for specific errors during code explanation."""
    pass

class OllamaModificationError(OllamaGenerationError):
    """Raised for specific errors during code modification suggestions."""
    pass


class OllamaConnector(BaseLLMConnector):
    """
    A client for interacting with a local Ollama instance.
    """
    DEFAULT_MODEL_NAME = 'llama3' # A common default, can be overridden by config
    DEFAULT_BASE_URL = 'http://localhost:11434'

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any):
        """
        Initializes the OllamaConnector.

        Args:
            model_name: Optional. The name of the Ollama model to use (e.g., 'codellama:7b', 'llama3').
                        Defaults to 'llama3' if not provided in config.
            **kwargs: Additional keyword arguments for connector-specific configuration,
                      including 'base_url', 'default_system_prompt', 'generation_params'.

        Raises:
            OllamaNotInstalledError: If the 'ollama' library is not installed.
            OllamaConnectorError: For other configuration or initialization issues.
        """
        super().__init__(model_name=model_name, **kwargs)

        if ollama is None:
            raise OllamaNotInstalledError(
                "The 'ollama' Python library is not installed. "
                "Please install it by running 'pip install ollama'."
            )

        self.base_url: str = self._config.get('base_url', self.DEFAULT_BASE_URL)
        # The model_name from super() is prioritized if passed, else from config, else default.
        self.model_name: str = self.model_name or self._config.get('model_name') or self.DEFAULT_MODEL_NAME

        self.default_system_prompt: Optional[str] = self._config.get('default_system_prompt')
        self.default_generation_options: Optional[Dict[str, Any]] = self._config.get('generation_params')

        try:
            self.client = ollama.Client(host=self.base_url)
            # You could add a check here to see if Ollama server is reachable
            # or if the model is available, but this might slow down initialization.
            # For now, errors will be caught during generation.
            # self._check_model_availability() # Example of a check
            print(f"OllamaConnector initialized. Model: {self.model_name}, Base URL: {self.base_url}")
        except Exception as e:
            raise OllamaConnectorError(f"Failed to initialize Ollama client or connect to {self.base_url}: {e}", underlying_exception=e)

    def _check_model_availability(self):
        """Helper to check if the configured model is available in Ollama."""
        try:
            models = self.client.list().get('models', [])
            model_names = [m['name'] for m in models]
            if self.model_name not in model_names:
                # Check if just the base name is present (e.g. "codellama" for "codellama:7b")
                base_model_name = self.model_name.split(':')[0]
                if not any(m.startswith(base_model_name) for m in model_names):
                    raise OllamaModelNotAvailableError(
                        f"Model '{self.model_name}' not found in Ollama. "
                        f"Available models: {model_names}. Pull the model using 'ollama pull {self.model_name}'."
                    )
                else:
                    print(f"Warning: Exact model tag '{self.model_name}' not found, but a base model '{base_model_name}' exists. Ollama will use its default if tag is omitted.")

        except ConnectionError as e: # Specific error for connection issues if client.list() fails
            raise OllamaApiError(f"Failed to connect to Ollama at {self.base_url} to list models: {e}", underlying_exception=e)
        except Exception as e: # Catch other errors from client.list()
            raise OllamaConnectorError(f"Error checking model availability for '{self.model_name}': {e}", underlying_exception=e)


    def _generate_with_ollama(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        generation_options_override: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Private helper to make a call to the Ollama API's generate method.

        Args:
            prompt: The main prompt for the model.
            system_instruction: System-level instructions for the model.
            generation_options_override: Specific Ollama options for this generation call.

        Returns:
            The generated text as a string.

        Raises:
            OllamaApiError: If an API error occurs.
            OllamaGenerationError: If generation fails or returns no meaningful content.
        """
        if not self.client:
            raise OllamaConnectorError("Ollama client not initialized.")

        current_options = self.default_generation_options or {}
        if generation_options_override:
            current_options.update(generation_options_override)

        # Filter out None values from options, as Ollama client might not like them
        final_options = {k: v for k, v in current_options.items() if v is not None}

        final_system_instruction = system_instruction or self.default_system_prompt

        print(f"Sending prompt to Ollama model {self.model_name}. System: '{final_system_instruction}'. Prompt: '{prompt[:100]}...'. Options: {final_options}")

        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                system=final_system_instruction, # Use system parameter for system instructions
                options=final_options,
                # stream=False is default and what we want for a single response string
            )

            generated_text = response.get('response')
            if not generated_text or not generated_text.strip():
                # Log full response if it's not too large, for debugging
                debug_response = {k:v for k,v in response.items() if k != 'response'} # Exclude the (empty) response itself
                print(f"Ollama generation returned empty response. Full details: {debug_response}")
                raise OllamaGenerationError(f"Ollama model '{self.model_name}' returned an empty response. Details: {debug_response}")

            return generated_text.strip()

        except ollama.ResponseError as e: # More specific error from the ollama library
            # e.status_code and e.error (message) can be useful
            error_message = f"Ollama API error (status {e.status_code}): {e.error}"
            if "model not found" in e.error.lower() or (hasattr(e, 'response') and e.response.status_code == 404):
                 raise OllamaModelNotAvailableError(f"{error_message}. Ensure model '{self.model_name}' is pulled.", underlying_exception=e) from e
            print(error_message)
            raise OllamaApiError(error_message, underlying_exception=e) from e
        except ConnectionRefusedError as e: # More specific error for connection issues
            error_message = f"Connection refused by Ollama server at {self.base_url}. Is Ollama running?"
            print(error_message)
            raise OllamaApiError(error_message, underlying_exception=e) from e
        except Exception as e: # Catch any other unexpected errors
            error_message = f"An unexpected error occurred during Ollama generation: {e}"
            print(error_message)
            raise OllamaApiError(error_message, underlying_exception=e) from e

    DEFAULT_CODE_SYSTEM_INSTRUCTION = (
        "You are an expert AI coding assistant. "
        "Please provide only the code requested by the user, without any additional explanatory text, "
        "markdown formatting, or language indicators (like ```python) surrounding the code block. "
        "If you need to include comments, ensure they are within the code block itself (e.g., using # for Python)."
    )

    def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """
        Generates code using the Ollama API.
        """
        active_system_instruction = system_instruction or self.DEFAULT_CODE_SYSTEM_INSTRUCTION

        # kwargs could be used for Ollama-specific generation options for this call
        generation_options_override = kwargs.get('generation_options')

        try:
            generated_text = self._generate_with_ollama(
                prompt=user_prompt,
                system_instruction=active_system_instruction,
                generation_options_override=generation_options_override
            )

            # Strip common markdown code block delimiters
            if generated_text.startswith("```") and generated_text.endswith("```"):
                lines = generated_text.splitlines()
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
                    generated_text = ""
                else:
                    generated_text = "\n".join(core_content_lines)

            return generated_text.strip() if generated_text else None

        except OllamaApiError as e:
            print(f"Ollama API error during code generation: {e}")
            # Depending on severity, you might return None or re-raise
            # For now, let's re-raise specific code gen error
            raise OllamaCodeGenerationError(f"API error in generate_code: {e}", underlying_exception=e) from e
        except OllamaGenerationError as e: # Catch empty responses or other generation issues
            print(f"Ollama generation error during code generation: {e}")
            raise OllamaCodeGenerationError(f"Generation error in generate_code: {e}", underlying_exception=e) from e
        except Exception as e: # Wrap other unexpected exceptions
            error_msg = f"An unexpected error occurred during Ollama code generation: {e}"
            print(error_msg)
            raise OllamaCodeGenerationError(error_msg, underlying_exception=e) from e


    DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION = (
        "You are a helpful coding assistant. Explain the following code snippet clearly and concisely. "
        "Describe its purpose, how it works, and any key components or logic."
    )

    def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """
        Explains a given code snippet using the Ollama API.
        """
        active_system_instruction = system_instruction or self.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION

        user_prompt_for_explanation = f"Please explain the following code:\n\n```\n{code_snippet}\n```"
        generation_options_override = kwargs.get('generation_options')

        try:
            explanation_text = self._generate_with_ollama(
                prompt=user_prompt_for_explanation,
                system_instruction=active_system_instruction,
                generation_options_override=generation_options_override
            )
            return explanation_text # Typically, explanations don't need markdown stripping unless the model adds it.

        except OllamaApiError as e:
            print(f"Ollama API error during code explanation: {e}")
            raise OllamaExplanationError(f"API error in explain_code: {e}", underlying_exception=e) from e
        except OllamaGenerationError as e:
            print(f"Ollama generation error during code explanation: {e}")
            raise OllamaExplanationError(f"Generation error in explain_code: {e}", underlying_exception=e) from e
        except Exception as e:
            error_msg = f"An unexpected error occurred during Ollama code explanation: {e}"
            print(error_msg)
            raise OllamaExplanationError(error_msg, underlying_exception=e) from e

    DEFAULT_MODIFY_SYSTEM_INSTRUCTION = (
        "You are an expert AI coding assistant. You are tasked with modifying the provided code snippet based on a user's issue description or request. "
        "Provide the complete modified code snippet. Enclose the final, complete code snippet in a standard markdown code block (e.g., ```python ... ``` or ``` ... ```). "
        "Do not include any other explanatory text outside the code block unless it's part of the code comments."
    )

    def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """
        Suggests modifications to a given code snippet using the Ollama API.
        """
        active_system_instruction = system_instruction or self.DEFAULT_MODIFY_SYSTEM_INSTRUCTION

        user_prompt_for_modification = (
            f"Issue/Request: {issue_description}\n\n"
            f"Original Code:\n```\n{code_snippet}\n```\n\n"
            "Please provide the modified code snippet."
        )
        generation_options_override = kwargs.get('generation_options')

        try:
            modified_code_text = self._generate_with_ollama(
                prompt=user_prompt_for_modification,
                system_instruction=active_system_instruction,
                generation_options_override=generation_options_override
            )

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

            return modified_code_text.strip() if modified_code_text else None

        except OllamaApiError as e:
            print(f"Ollama API error during code modification: {e}")
            raise OllamaModificationError(f"API error in suggest_code_modification: {e}", underlying_exception=e) from e
        except OllamaGenerationError as e:
            print(f"Ollama generation error during code modification: {e}")
            raise OllamaModificationError(f"Generation error in suggest_code_modification: {e}", underlying_exception=e) from e
        except Exception as e:
            error_msg = f"An unexpected error occurred during Ollama code modification: {e}"
            print(error_msg)
            raise OllamaModificationError(error_msg, underlying_exception=e) from e

# Example usage (optional, for quick testing if Ollama is running)
# To test this, ensure Ollama is running and the model (e.g., 'llama3' or 'codellama') is pulled.
# Example:
# 1. Run Ollama server: `ollama serve` (usually runs automatically if installed as a service)
# 2. Pull a model: `ollama pull llama3`
# Then you can run this script.
if __name__ == '__main__':
    if ollama is None:
        print("Ollama library not installed. Skipping example usage.")
    else:
        try:
            print("\n--- Initializing OllamaConnector ---")
            # Default init (model 'llama3', url 'http://localhost:11434')
            # You can override by passing parameters to constructor or via a mock config
            # For this test, we assume default model 'llama3' is available.
            # If you want to test with a specific model from your config, you'd typically
            # have an LLMManager load it. Here, we simulate it:

            # Simulate config that might be passed from LLMManager
            mock_config_codellama = {
                'base_url': 'http://localhost:11434',
                # 'model_name': 'codellama:7b-instruct', # More specific
                'model_name': 'codellama', # Simpler, if you have a base codellama
                'default_system_prompt': "You are testing Ollama integration.",
                'generation_params': {"temperature": 0.6, "num_ctx": 4096} # Example Ollama params
            }

            # client = OllamaConnector() # Uses llama3 default
            # print(f"--- Using model: {client.model_name} ---")

            # Test with a potentially different model if you have codellama pulled
            try:
                print(f"\n--- Attempting to use model: {mock_config_codellama['model_name']} ---")
                client = OllamaConnector(
                    model_name=mock_config_codellama['model_name'],
                    **mock_config_codellama
                )
                # client._check_model_availability() # Manually call check for this test
            except OllamaModelNotAvailableError as e:
                print(f"Model {mock_config_codellama['model_name']} not available, falling back to default 'llama3'. Error: {e}")
                client = OllamaConnector() # Fallback to default 'llama3'
                # client._check_model_availability()

            print(f"--- Testing with model: {client.model_name} ---")


            # 1. Test generate_code
            print("\n--- Testing generate_code ---")
            python_prompt = "Create a Python function that returns the factorial of a number using recursion."
            generated_python_code = client.generate_code(python_prompt)
            if generated_python_code:
                print("Generated Python Code:\n", generated_python_code)
            else:
                print("No Python code generated or an issue occurred.")

            # 2. Test explain_code
            print("\n--- Testing explain_code ---")
            code_to_explain = "def fib(n):
  return n if n < 2 else fib(n-1) + fib(n-2)"
            explanation = client.explain_code(code_to_explain)
            if explanation:
                print(f"Explanation for:\n{code_to_explain}\n---\n{explanation}")
            else:
                print("No explanation generated or an issue occurred.")

            # 3. Test suggest_code_modification
            print("\n--- Testing suggest_code_modification ---")
            original_code = "def greet(name):\n  return f'Goodbye {name}!'"
            issue = "This function should greet the person, not say goodbye."
            modified_code = client.suggest_code_modification(original_code, issue)
            if modified_code:
                print(f"Original Code:\n{original_code}\nIssue: {issue}\n---\nSuggested Modification:\n{modified_code}")
            else:
                print("No modification suggested or an issue occurred.")

        except OllamaNotInstalledError as e:
            print(f"Ollama Library Error: {e}")
        except OllamaApiError as e:
            print(f"Ollama API/Connection Error: {e}. Is Ollama server running and model '{client.model_name if 'client' in locals() else 'TARGET_MODEL'}' pulled?")
            if e.underlying_exception:
                print(f"  Underlying error: {e.underlying_exception}")
        except OllamaGenerationError as e:
            print(f"Ollama Generation Error: {e}")
        except OllamaConnectorError as e:
            print(f"Ollama Connector Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during Ollama testing: {e}")
