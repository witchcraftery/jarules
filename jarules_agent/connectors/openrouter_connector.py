# jarules_agent/connectors/openrouter_connector.py

import os
import json
from typing import Optional, List, Any, Dict, Union

try:
    import requests
except ImportError:
    requests = None # Placeholder if not installed

from .base_llm_connector import BaseLLMConnector, LLMConnectorError

# --- Custom Exceptions ---
class OpenRouterConnectorError(LLMConnectorError):
    """Base exception for OpenRouterConnector errors."""
    pass

class OpenRouterNotInstalledError(OpenRouterConnectorError):
    """Raised when the requests library is not installed."""
    pass

class OpenRouterApiKeyError(OpenRouterConnectorError):
    """Raised when the OpenRouter API key is not configured."""
    pass

class OpenRouterApiError(OpenRouterConnectorError):
    """
    Raised for errors during OpenRouter API calls.
    Includes HTTP status code if available.
    """
    def __init__(self, message: str, status_code: Optional[int] = None, underlying_exception: Optional[Exception] = None):
        super().__init__(message, underlying_exception)
        self.status_code = status_code

class OpenRouterModelNotAvailableError(OpenRouterApiError):
    """Raised specifically when a model is not available or recognized by OpenRouter."""
    pass

class OpenRouterGenerationError(OpenRouterConnectorError):
    """Raised for specific errors during text generation, e.g., empty response or malformed content."""
    pass

class OpenRouterCodeGenerationError(OpenRouterGenerationError):
    """Raised for specific errors during code generation."""
    pass

class OpenRouterExplanationError(OpenRouterGenerationError):
    """Raised for specific errors during code explanation."""
    pass

class OpenRouterModificationError(OpenRouterGenerationError):
    """Raised for specific errors during code modification suggestions."""
    pass


class OpenRouterConnector(BaseLLMConnector):
    """
    A client for interacting with the OpenRouter.ai API.
    Allows access to a variety of LLMs through a unified interface.
    """
    DEFAULT_MODEL_NAME = 'mistralai/mistral-7b-instruct' # A common, good default
    DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'
    DEFAULT_HTTP_REFERER = 'https://github.com/JaRules/jarules' # Replace with actual project URL or app ID
    DEFAULT_APP_NAME = 'JaRules Agent' # Replace with actual project name

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any):
        """
        Initializes the OpenRouterConnector.

        Args:
            model_name: Optional. The specific OpenRouter model string
                        (e.g., 'mistralai/mistral-7b-instruct', 'openai/gpt-4-turbo').
            **kwargs: Additional keyword arguments for connector-specific configuration:
                      'api_key': OpenRouter API key.
                      'base_url': API endpoint.
                      'http_referer': HTTP Referer header value.
                      'app_name': X-Title header value or general app identifier.
                      'default_system_prompt': Default system message for prompts.
                      'generation_params': Default parameters for generation (e.g., temperature).

        Raises:
            OpenRouterNotInstalledError: If the 'requests' library is not installed.
            OpenRouterApiKeyError: If the OpenRouter API key is not found.
            OpenRouterConnectorError: For other configuration or initialization issues.
        """
        super().__init__(model_name=model_name, **kwargs)

        if requests is None:
            raise OpenRouterNotInstalledError(
                "The 'requests' Python library is not installed. "
                "Please install it by running 'pip install requests'."
            )

        self.api_key: Optional[str] = self._config.get('api_key') or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise OpenRouterApiKeyError(
                "OpenRouter API key not found. Pass 'api_key' in LLMManager config "
                "or set OPENROUTER_API_KEY environment variable."
            )

        self.base_url: str = self._config.get('base_url', self.DEFAULT_BASE_URL)
        # self.model_name is set by BaseLLMConnector's __init__
        # If it's None after that, use config, then default.
        self.model_name: str = self.model_name or self._config.get('model_name') or self.DEFAULT_MODEL_NAME

        self.http_referer: str = self._config.get('http_referer', self.DEFAULT_HTTP_REFERER)
        self.app_name: str = self._config.get('app_name', self._config.get('x_title', self.DEFAULT_APP_NAME)) # Allow 'x_title' for config too

        self.default_system_prompt: Optional[str] = self._config.get('default_system_prompt')
        self.default_generation_options: Optional[Dict[str, Any]] = self._config.get('generation_params')

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.app_name, # Some models/providers on OpenRouter might use this
        })

        print(f"OpenRouterConnector initialized. Model: {self.model_name}, Base URL: {self.base_url}, Referer: {self.http_referer}, App: {self.app_name}")


    def _make_api_call(
        self,
        messages: List[Dict[str, str]],
        generation_options_override: Optional[Dict[str, Any]] = None,
        stream: bool = False # OpenRouter supports streaming, but BaseLLMConnector methods expect full response
    ) -> Dict[str, Any]:
        """
        Private helper to make a POST request to the OpenRouter chat completions endpoint.

        Args:
            messages: A list of message objects (e.g., {'role': 'user', 'content': '...'})
            generation_options_override: Specific OpenRouter options for this generation call.
            stream: Whether to stream the response (currently unused by public methods).

        Returns:
            The JSON response from the API as a dictionary.

        Raises:
            OpenRouterApiError: If an API error occurs (HTTP error or error in JSON response).
            OpenRouterModelNotAvailableError: If the model is specifically not found.
        """
        if not self.session:
            raise OpenRouterConnectorError("Requests session not initialized.")

        api_url = f"{self.base_url.rstrip('/')}/chat/completions"

        current_options = self.default_generation_options or {}
        if generation_options_override:
            current_options.update(generation_options_override)

        # Filter out None values from options, as API might not like them
        final_generation_options = {k: v for k, v in current_options.items() if v is not None}

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            **final_generation_options # Spread other generation params like temperature, max_tokens
        }

        print(f"Sending prompt to OpenRouter. Model: {self.model_name}. API URL: {api_url}. Messages: {messages[0]['content'][:100]}... Options: {final_generation_options}")

        try:
            response = self.session.post(api_url, json=payload, timeout=60) # 60s timeout
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

            response_json = response.json()

            # Check for errors in the JSON response itself, even with a 200 OK
            if 'error' in response_json:
                error_data = response_json['error']
                error_message = error_data.get('message', 'Unknown API error in JSON response')
                error_type = error_data.get('type')
                # Check if it's a model not found error (OpenRouter might have specific codes/messages)
                if "model_not_found" in error_type or "model not found" in error_message.lower():
                    raise OpenRouterModelNotAvailableError(
                        f"OpenRouter: Model '{self.model_name}' not found or not available. Details: {error_message}",
                        status_code=response.status_code
                    )
                raise OpenRouterApiError(
                    f"OpenRouter API returned an error: {error_message} (Type: {error_type})",
                    status_code=response.status_code
                )

            return response_json

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            try: # Try to get more detailed error from response body
                error_content = e.response.json()
                error_detail = error_content.get('error', {}).get('message', e.response.text)
            except ValueError: # JSONDecodeError
                error_detail = e.response.text

            error_message = f"OpenRouter API HTTP error ({status_code}): {error_detail}"
            print(error_message)
            if status_code == 404 and ("model not found" in error_detail.lower() or "resolve model" in error_detail.lower()):
                 raise OpenRouterModelNotAvailableError(f"OpenRouter: Model '{self.model_name}' not found (HTTP {status_code}). Detail: {error_detail}", status_code=status_code, underlying_exception=e) from e
            raise OpenRouterApiError(error_message, status_code=status_code, underlying_exception=e) from e
        except requests.exceptions.RequestException as e: # Other request errors (timeout, connection)
            error_message = f"OpenRouter request failed: {e}"
            print(error_message)
            raise OpenRouterApiError(error_message, underlying_exception=e) from e
        except Exception as e: # Catch any other unexpected errors
            error_message = f"An unexpected error occurred during OpenRouter API call: {e}"
            print(error_message)
            raise OpenRouterApiError(error_message, underlying_exception=e) from e


    def _extract_content_from_response(self, response_json: Dict[str, Any]) -> Optional[str]:
        """Extracts the text content from a successful API response."""
        try:
            choices = response_json.get('choices')
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                raise OpenRouterGenerationError("OpenRouter response contained no choices.", underlying_exception=ValueError(f"Full response: {response_json}"))

            message = choices[0].get('message')
            if not message or not isinstance(message, dict):
                raise OpenRouterGenerationError("OpenRouter choice contained no message.", underlying_exception=ValueError(f"Full response: {response_json}"))

            content = message.get('content')
            if content is None: # Could be an empty string, which is valid
                # This might happen if generation is stopped early or model returns nothing.
                # Consider if this should be an error or just return "" or None.
                # For now, let's treat actual None as an issue, but "" as valid empty.
                print("OpenRouter response message content is null.")
                return None

            return str(content).strip() # Ensure it's a string and stripped

        except (KeyError, TypeError, IndexError, AttributeError) as e:
            error_msg = f"Failed to extract content from OpenRouter response: {e}. Response structure might be unexpected."
            print(f"{error_msg} Full response: {response_json}")
            raise OpenRouterGenerationError(error_msg, underlying_exception=e)

    # --- Default System Prompts (can be overridden by config or method calls) ---
    DEFAULT_CODE_SYSTEM_INSTRUCTION = (
        "You are an expert AI coding assistant. "
        "Please provide only the code requested by the user, without any additional explanatory text, "
        "markdown formatting, or language indicators (like ```python) surrounding the code block. "
        "If you need to include comments, ensure they are within the code block itself (e.g., using # for Python)."
    )

    DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION = (
        "You are a helpful coding assistant. Explain the following code snippet clearly and concisely. "
        "Describe its purpose, how it works, and any key components or logic."
    )

    DEFAULT_MODIFY_SYSTEM_INSTRUCTION = (
        "You are an expert AI coding assistant. You are tasked with modifying the provided code snippet based on a user's issue description or request. "
        "Provide the complete modified code snippet. Enclose the final, complete code snippet in a standard markdown code block (e.g., ```python ... ``` or ``` ... ```). "
        "Do not include any other explanatory text outside the code block unless it's part of the code comments."
    )

    def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        active_system_instruction = system_instruction or self.default_system_prompt or self.DEFAULT_CODE_SYSTEM_INSTRUCTION

        messages = []
        if active_system_instruction: # Ensure it's not an empty string if user explicitly passed ""
            messages.append({"role": "system", "content": active_system_instruction})
        messages.append({"role": "user", "content": user_prompt})

        generation_options_override = kwargs.get('generation_options')

        try:
            response_json = self._make_api_call(messages, generation_options_override)
            generated_text = self._extract_content_from_response(response_json)

            if generated_text is None: # If extraction returns None (e.g. content was null)
                return None

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

            return generated_text.strip()

        except OpenRouterApiError as e:
            raise OpenRouterCodeGenerationError(f"API error in generate_code: {e}", underlying_exception=e) from e
        except OpenRouterGenerationError as e:
            raise OpenRouterCodeGenerationError(f"Generation error in generate_code: {e}", underlying_exception=e) from e
        except Exception as e:
            raise OpenRouterCodeGenerationError(f"Unexpected error in generate_code: {e}", underlying_exception=e) from e

    def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        active_system_instruction = system_instruction or self.default_system_prompt or self.DEFAULT_EXPLAIN_SYSTEM_INSTRUCTION

        user_prompt_for_explanation = f"Please explain the following code:\n\n```\n{code_snippet}\n```"

        messages = []
        if active_system_instruction:
            messages.append({"role": "system", "content": active_system_instruction})
        messages.append({"role": "user", "content": user_prompt_for_explanation})

        generation_options_override = kwargs.get('generation_options')

        try:
            response_json = self._make_api_call(messages, generation_options_override)
            explanation_text = self._extract_content_from_response(response_json)
            return explanation_text

        except OpenRouterApiError as e:
            raise OpenRouterExplanationError(f"API error in explain_code: {e}", underlying_exception=e) from e
        except OpenRouterGenerationError as e:
            raise OpenRouterExplanationError(f"Generation error in explain_code: {e}", underlying_exception=e) from e
        except Exception as e:
            raise OpenRouterExplanationError(f"Unexpected error in explain_code: {e}", underlying_exception=e) from e

    def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        active_system_instruction = system_instruction or self.default_system_prompt or self.DEFAULT_MODIFY_SYSTEM_INSTRUCTION

        user_prompt_for_modification = (
            f"Issue/Request: {issue_description}\n\n"
            f"Original Code:\n```\n{code_snippet}\n```\n\n"
            "Please provide the modified code snippet."
        )

        messages = []
        if active_system_instruction:
            messages.append({"role": "system", "content": active_system_instruction})
        messages.append({"role": "user", "content": user_prompt_for_modification})

        generation_options_override = kwargs.get('generation_options')

        try:
            response_json = self._make_api_call(messages, generation_options_override)
            modified_code_text = self._extract_content_from_response(response_json)

            if modified_code_text is None:
                return None

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

        except OpenRouterApiError as e:
            raise OpenRouterModificationError(f"API error in suggest_code_modification: {e}", underlying_exception=e) from e
        except OpenRouterGenerationError as e:
            raise OpenRouterModificationError(f"Generation error in suggest_code_modification: {e}", underlying_exception=e) from e
        except Exception as e:
            raise OpenRouterModificationError(f"Unexpected error in suggest_code_modification: {e}", underlying_exception=e) from e


# Example usage (optional, for quick testing if OPENROUTER_API_KEY is set)
if __name__ == '__main__':
    if requests is None:
        print("Requests library not installed. Skipping example usage.")
    elif not os.environ.get("OPENROUTER_API_KEY"):
        print("Please set the OPENROUTER_API_KEY environment variable to test.")
    else:
        try:
            print("\n--- Initializing OpenRouterConnector ---")
            # Using default model (mistralai/mistral-7b-instruct)
            # You can specify a model in constructor or via mock config for LLMManager
            client = OpenRouterConnector(
                # model_name="openai/gpt-3.5-turbo", # Example: To test a different model
                http_referer="http://localhost/jarules_test", # Test referer
                app_name="JaRules Test Client" # Test app name
            )
            print(f"--- Testing with model: {client.model_name} ---")

            # 1. Test generate_code
            print("\n--- Testing generate_code ---")
            python_prompt = "Create a simple Python function that adds two numbers."
            generated_python_code = client.generate_code(python_prompt)
            if generated_python_code is not None:
                print("Generated Python Code:\n", generated_python_code)
            else:
                print("No Python code generated or an issue occurred.")

            # 2. Test explain_code
            print("\n--- Testing explain_code ---")
            code_to_explain = "function example(a, b) { return a * b; }"
            explanation = client.explain_code(code_to_explain)
            if explanation is not None:
                print(f"Explanation for:\n{code_to_explain}\n---\n{explanation}")
            else:
                print("No explanation generated or an issue occurred.")

            # 3. Test suggest_code_modification
            print("\n--- Testing suggest_code_modification ---")
            original_code = "const result = x / y;"
            issue = "This should perform addition instead of division."
            modified_code = client.suggest_code_modification(original_code, issue)
            if modified_code is not None:
                print(f"Original Code:\n{original_code}\nIssue: {issue}\n---\nSuggested Modification:\n{modified_code}")
            else:
                print("No modification suggested or an issue occurred.")

        except OpenRouterNotInstalledError as e:
            print(f"Requests Library Error: {e}")
        except OpenRouterApiKeyError as e:
            print(f"API Key Error: {e}")
        except OpenRouterApiError as e:
            print(f"OpenRouter API Error (Status: {e.status_code}): {e}")
            if e.underlying_exception: print(f"  Underlying: {e.underlying_exception}")
        except OpenRouterGenerationError as e:
            print(f"OpenRouter Generation Error: {e}")
        except OpenRouterConnectorError as e:
            print(f"OpenRouter Connector Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during OpenRouter testing: {e}")
