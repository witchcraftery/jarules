import logging
import os
import httpx

from typing import Optional, List, Dict, Any # Added Optional, List, Dict, Any
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector, LLMConnectorError

logger = logging.getLogger(__name__)

# Define a custom exception for OpenRouter API errors
class OpenRouterApiError(LLMConnectorError): # Inherit from LLMConnectorError
    """Custom exception for OpenRouter API errors."""
    def __init__(self, message, status_code=None, underlying_exception: Optional[Exception] = None):
        super().__init__(message, underlying_exception=underlying_exception)
        self.status_code = status_code

class OpenRouterConnector(BaseLLMConnector):
    """
    Connector for interacting with various LLMs through the OpenRouter API.
    """

    DEFAULT_API_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL_NAME = "gryphe/mythomax-l2-13b" # A free model for default

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any): # Updated signature
        """
        Initializes the OpenRouterConnector.

        Args:
            model_name: Optional. The default model to use (e.g., "openai/gpt-4o").
            **kwargs: Configuration parameters.
                      Expected keys in kwargs:
                      - 'api_key_env_var' (str): Name of the environment variable holding the API key.
                                                 Defaults to "OPENROUTER_API_KEY".
                      - 'api_base_url' (str, optional): Base URL for the OpenRouter API.
                                                        Defaults to "https://openrouter.ai/api/v1".
                      - 'default_system_prompt' (str, optional): Default system prompt.
                      - 'generation_params' (dict, optional): Default generation parameters.
                      - 'request_timeout' (int, optional): Timeout for HTTP requests. Defaults to 60.
                      - 'http_referer' (str, optional): HTTP Referer header. Defaults to "http://localhost:3000".
        """
        effective_model_name = model_name or kwargs.get("model_name") or self.DEFAULT_MODEL_NAME
        super().__init__(model_name=effective_model_name, **kwargs)

        api_key_env_var = self._config.get("api_key_env_var", "OPENROUTER_API_KEY")
        self.api_key = os.environ.get(api_key_env_var)
        if not self.api_key:
            raise OpenRouterApiError(f"API key not found. Set the {api_key_env_var} environment variable.")

        self.api_base_url = self._config.get("api_base_url", self.DEFAULT_API_BASE_URL)
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]

        self.default_system_prompt = self._config.get("default_system_prompt")
        self.generation_params = self._config.get("generation_params", {})
        self.http_referer = self._config.get("http_referer", "http://localhost:3000") # Example referer
        request_timeout = self._config.get("request_timeout", 60) # OpenRouter can sometimes be slow

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        # Potentially add "X-Title" header with app name if desired

        self.client = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers=headers,
            timeout=request_timeout
        )
        logger.info(
            f"OpenRouterConnector initialized with model: {self.model_name}, "
            f"base_url: {self.api_base_url}, timeout: {request_timeout}"
        )
        if self.default_system_prompt:
            logger.info(f"Default system prompt: {(self.default_system_prompt or '')[:100]}...")
        if self.generation_params:
            logger.info(f"Default generation parameters: {self.generation_params}")

    async def _make_chat_completion_request(self, messages: List[Dict[str, str]], generation_params_override: Optional[Dict[str, Any]] = None) -> str:
        """
        Helper method to make a request to the /chat/completions endpoint.
        """
        payload = {
            "model": self.model_name, # self.model_name is from BaseLLMConnector
            "messages": messages,
        }

        # Merge default generation_params with overrides, then with payload
        current_generation_params = self.generation_params.copy()
        if generation_params_override:
            current_generation_params.update(generation_params_override)

        # Only add parameters to payload if they have values, to avoid sending e.g. "temperature": null
        for key, value in current_generation_params.items():
            if value is not None:
                payload[key] = value
        # payload.update(current_generation_params) # Old way, could send None values

        logger.debug(f"OpenRouter request payload: {json.dumps(payload, indent=2)}")
        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

            response_data = response.json()

            if not response_data.get("choices") or not response_data["choices"][0].get("message") \
               or "content" not in response_data["choices"][0]["message"]:
                logger.error(f"Invalid response structure from OpenRouter: {response_data}")
                raise OpenRouterApiError("Invalid response structure from OpenRouter.", status_code=response.status_code, underlying_exception=ValueError(str(response_data)))

            content = response_data["choices"][0]["message"]["content"]
            logger.info(f"Successfully received response from OpenRouter. Choice 0 content length: {len(content or '')}")
            return (content or "").strip() # Ensure content is not None before strip

        except httpx.RequestError as e:
            logger.error(f"Error connecting to OpenRouter API: {e}")
            raise OpenRouterApiError(f"Connection to OpenRouter failed: {e}", underlying_exception=e) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API request failed: {e.response.status_code} - {e.response.text[:200]}")
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                if error_json and "error" in error_json: # OpenAI compatible error
                    error_detail = error_json["error"].get("message", error_detail)
                elif error_json and "detail" in error_json: # Some other proxy errors
                    error_detail = error_json["detail"]
            except json.JSONDecodeError:
                pass
            raise OpenRouterApiError(f"OpenRouter API error: {e.response.status_code} - {error_detail}", status_code=e.response.status_code, underlying_exception=e) from e
        except json.JSONDecodeError as e: # Should be rare if HTTPStatusError parsing works
            logger.error(f"Failed to parse JSON response from OpenRouter: {e}. Response text: {response.text[:200] if 'response' in locals() else 'N/A'}")
            raise OpenRouterApiError(f"Invalid JSON response from OpenRouter: {e}", underlying_exception=e) from e
        except Exception as e: # Catch-all for unexpected errors
            logger.error(f"An unexpected error occurred during OpenRouter request: {e}")
            raise OpenRouterApiError(f"An unexpected error occurred: {e}", underlying_exception=e) from e

    def check_availability(self) -> Dict[str, Any]:
        """
        Checks if the OpenRouter API is available by trying to make a cheap request.
        This also implicitly checks if the API key is valid.
        This method is synchronous and runs the async check internally.
        """
        logger.info(f"Checking OpenRouter API availability and API key validity at {self.api_base_url} using model {self.model_name}...")

        async def _async_check():
            test_messages = [{"role": "user", "content": "test"}]
            test_gen_params = {"max_tokens": 1, "temperature": 0.0}
            await self._make_chat_completion_request(messages=test_messages, generation_params_override=test_gen_params)

        try:
            # Similar to ClaudeConnector, manage running async code from sync context
            try:
                loop = asyncio.get_running_loop()
                # This check might be too simplistic for all async environments.
                # Consider if a more robust async-to-sync execution utility is needed for the project.
            except RuntimeError: # No running event loop
                loop = None

            if loop and loop.is_running():
                # This is a tricky situation. Calling asyncio.run() from a running loop is an error.
                # A proper solution would involve `asyncio.create_task` and awaiting it if possible,
                # or using a thread pool to run the async code if truly blocking sync is required.
                # For now, returning an error indicating this specific state.
                logger.warning("check_availability (sync) called from within an active asyncio event loop. This can cause issues.")
                # As a temporary measure, we'll try to run it, but this is not ideal.
                # The user might need to call an async version if they are in an async context.
                # Or the connector needs a truly synchronous HTTP client for this method.
                # For this exercise, we stick to asyncio.run and document the limitation.
                pass # Fall through to asyncio.run

            asyncio.run(_async_check())
            logger.info("OpenRouter API is available and API key appears valid.")
            return {'available': True, 'details': 'OpenRouter API is available and authentication is successful.'}
        except OpenRouterApiError as e:
            details = f"OpenRouter API error: {e.message}"
            if e.status_code:
                details += f" (Status: {e.status_code})"
            if e.status_code == 401:
                logger.error(f"OpenRouter API key is invalid or not authorized. Status: {e.status_code}. Message: {e.message}")
                details = f"OpenRouter API authentication failed (Status: {e.status_code}): {e.message}. Check API key."
            else:
                logger.error(f"OpenRouter API availability check failed. Status: {e.status_code}. Message: {e.message}")
            return {'available': False, 'details': details}
        except Exception as e: # Catch any other unexpected errors, including asyncio.run issues
            logger.error(f"An unexpected error occurred during OpenRouter availability check: {e}")
            if "asyncio.run() cannot be called from a running event loop" in str(e):
                 return {'available': False, 'details': "OpenRouter availability check failed: Cannot run async check from current event loop context. This connector is async but check is sync."}
            return {'available': False, 'details': f"An unexpected error occurred: {e}"}

    def _prepare_messages(self, user_prompt: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """
        Prepares the list of messages for the API request, incorporating history and system instructions.
        History format: [{"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}]
        OpenAI/OpenRouter format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        messages: List[Dict[str, str]] = []

        # 1. Add system instruction if provided
        active_system_instruction = system_instruction if system_instruction is not None else self.default_system_prompt
        if active_system_instruction: # Ensure it's not None or empty string
            messages.append({"role": "system", "content": active_system_instruction})

        # 2. Add history
        if history:
            for item in history:
                # Transform role and content key
                role = item.get("role")
                # Prioritize "text", then "content". Could be made more robust.
                content = item.get("text") or item.get("content")

                if role and content:
                    # Ensure role is one of "user", "assistant", "system" (though system usually first)
                    # OpenAI/OpenRouter typically expect "user" or "assistant" for history turns.
                    # If a "system" role is in history, it might be from a previous turn's system_instruction.
                    # For simplicity, we'll pass it as is, but it's usually best for "system" to be at the start.
                    valid_roles = ["user", "assistant", "system"]
                    if role not in valid_roles:
                        logger.warning(f"History item has invalid role '{role}'. Skipping.")
                        continue
                    messages.append({"role": role, "content": content})
                else:
                    logger.warning(f"History item missing role or content: {item}. Skipping.")

        # 3. Add current user prompt
        if user_prompt: # Ensure user_prompt is not empty
             messages.append({"role": "user", "content": user_prompt})
        else:
            # This case should ideally be prevented by callers or raise an error.
            # If the last message is not from 'user', many models will error.
            # If messages is empty and no user_prompt, _make_chat_completion_request will likely fail.
            logger.warning("User prompt is empty. The API call might fail if messages list is empty or ends with non-user role.")
            if not messages or messages[-1]["role"] != "user":
                 # Add a minimal user message if list is empty or last message is not user to prevent errors
                 # This is a fallback, ideally user_prompt should always be present.
                 # messages.append({"role": "user", "content": "..."}) # Or raise error
                 pass # Let it proceed, _make_chat_completion_request might handle empty messages scenario if needed (e.g. raise error)


        return messages

    async def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        logger.info(f"generate_code called with user_prompt: {user_prompt[:50]}...")
        # The 'context' parameter from the old signature is not used here.
        # If context is needed, it should be part of the user_prompt or history.

        messages = self._prepare_messages(user_prompt, system_instruction, history)
        if not messages: # Should not happen if user_prompt is guaranteed
            raise OpenRouterApiError("Cannot generate code with an empty message list (no user_prompt and no history).")

        # Allow overriding generation_params via kwargs if needed, e.g., kwargs.get("generation_params_override")
        generation_params_override = kwargs.get("generation_params")
        return await self._make_chat_completion_request(messages, generation_params_override=generation_params_override)

    async def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        logger.info(f"explain_code called for code snippet: {code_snippet[:50]}...")

        user_content = f"Please explain the following code snippet:\n```\n{code_snippet}\n```"

        # Use a default system prompt if none provided and default_system_prompt is not set
        effective_system_instruction = system_instruction
        if effective_system_instruction is None and self.default_system_prompt is None:
            effective_system_instruction = "You are an expert code explainer. Provide clear and concise explanations for the given code."
        # If system_instruction is provided, it's used. If None, self.default_system_prompt is used by _prepare_messages.
        # The above line sets a specific default only if no other system prompt would be chosen.

        messages = self._prepare_messages(user_content, effective_system_instruction, history)
        if not messages:
            raise OpenRouterApiError("Cannot explain code with an empty message list.")

        generation_params_override = kwargs.get("generation_params")
        return await self._make_chat_completion_request(messages, generation_params_override=generation_params_override)

    async def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        logger.info(f"suggest_code_modification called for code: {code_snippet[:50]} with issue: {issue_description[:50]}")

        user_content = (
            f"Code snippet:\n```\n{code_snippet}\n```\n\n"
            f"Issue/Request for modification: {issue_description}\n\n"
            "Please provide the modified code snippet."
        )

        effective_system_instruction = system_instruction
        if effective_system_instruction is None and self.default_system_prompt is None:
            effective_system_instruction = "You are an expert code modification assistant. Given a code snippet and an instruction, provide the modified code snippet."

        messages = self._prepare_messages(user_content, effective_system_instruction, history)
        if not messages:
            raise OpenRouterApiError("Cannot suggest code modification with an empty message list.")

        generation_params_override = kwargs.get("generation_params")
        return await self._make_chat_completion_request(messages, generation_params_override=generation_params_override)

    async def close(self):
        """
        Closes the httpx client.
        """
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()
            logger.info("OpenRouterConnector's HTTP client closed.")

# Example usage (for testing purposes, if run directly)
if __name__ == '__main__':
    import asyncio

    # This requires OPENROUTER_API_KEY to be set in the environment
    # And a valid referer if your OpenRouter account requires it.

    async def main_async_tests():
        connector = None
        try:
            connector = OpenRouterConnector(
                model_name="mistralai/mistral-7b-instruct",
                api_key_env_var="OPENROUTER_API_KEY",
                http_referer=os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3001/test"), # Use env var or a default
                default_system_prompt="You are a helpful coding assistant.",
                generation_params={"temperature": 0.7, "max_tokens": 100}
            )
            logger.info("OpenRouterConnector (for async tests) created.")

            # Example: Test generate_code
            # code = await connector.generate_code("Write a python function to add two numbers.")
            # logger.info(f"Generated code: {code}")

        except OpenRouterApiError as e:
            logger.error(f"OpenRouter API error during async example: {e}")
        except Exception as e:
            logger.error(f"An error occurred during async example: {e}", exc_info=True)
        finally:
            if connector:
                await connector.close()

    def test_sync_check_availability():
        connector = None
        try:
            # Ensure you have OPENROUTER_HTTP_REFERER in env or change the default
            http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3002/test_sync")
            if http_referer == "YOUR_SITE_URL_HERE" or not http_referer: # Default from old example
                 logger.warning("OPENROUTER_HTTP_REFERER not set to a valid URL, using placeholder for sync test.")
                 http_referer = "http://localhost:3000/sync_check_test"


            connector = OpenRouterConnector(
                model_name="mistralai/mistral-7b-instruct",
                api_key_env_var="OPENROUTER_API_KEY",
                http_referer=http_referer,
                default_system_prompt="You are a helpful coding assistant for sync check.",
                generation_params={"temperature": 0.7, "max_tokens": 50}
            )
            logger.info("OpenRouterConnector (for sync check_availability) created.")

            availability_status = connector.check_availability()
            logger.info(f"OpenRouter API Availability: {availability_status['available']}, Details: {availability_status['details']}")

        except OpenRouterApiError as e: # Catch init errors
            logger.error(f"OpenRouter API error during sync example init: {e}")
            logger.info(f"OpenRouter API Availability: False, Details: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during sync example: {e}", exc_info=True)
            logger.info(f"OpenRouter API Availability: False, Details: An unexpected error occurred: {e}")
        # No explicit close here for sync test, similar to Claude connector.

    if os.getenv("OPENROUTER_API_KEY"):
        # It's good practice to ensure http_referer is actually set if required by your key
        configured_referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000/main_test")
        if configured_referer == "YOUR_SITE_URL_HERE" or not configured_referer :
             logger.warning("OPENROUTER_HTTP_REFERER is not set to a specific value. OpenRouter may require this.")

        logger.info("--- Running Sync check_availability test for OpenRouter ---")
        test_sync_check_availability()

        # logger.info("\n--- Running Async operations test for OpenRouter (commented out) ---")
        # asyncio.run(main_async_tests())
    else:
        logger.warning("Skipping OpenRouterConnector example: OPENROUTER_API_KEY not set.")
