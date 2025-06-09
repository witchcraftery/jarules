import logging
import os
import httpx

from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

logger = logging.getLogger(__name__)

# Define a custom exception for OpenRouter API errors
class OpenRouterApiError(Exception):
    """Custom exception for OpenRouter API errors."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class OpenRouterConnector(BaseLLMConnector):
    """
    Connector for interacting with various LLMs through the OpenRouter API.
    """

    DEFAULT_API_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL_NAME = "gryphe/mythomax-l2-13b" # A free model for default

    def __init__(self, config: dict):
        """
        Initializes the OpenRouterConnector.

        Args:
            config: A dictionary containing configuration parameters.
                    Expected keys:
                    - 'api_key_env_var' (str): Name of the environment variable holding the API key.
                    - 'model_name' (str, optional): Default model to use (e.g., "openai/gpt-4o").
                    - 'api_base_url' (str, optional): Base URL for the OpenRouter API.
                    - 'default_system_prompt' (str, optional): Default system prompt.
                    - 'generation_params' (dict, optional): Default generation parameters.
                    - 'request_timeout' (int, optional): Timeout for HTTP requests.
                    - 'http_referer' (str, optional): HTTP Referer header, often your site URL.
        """
        super().__init__(config)

        api_key_env_var = config.get("api_key_env_var", "OPENROUTER_API_KEY")
        self.api_key = os.environ.get(api_key_env_var)
        if not self.api_key:
            raise ValueError(f"API key not found. Set the {api_key_env_var} environment variable.")

        self.api_base_url = config.get("api_base_url", self.DEFAULT_API_BASE_URL)
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]

        self.model_name = config.get("model_name", self.DEFAULT_MODEL_NAME)
        self.default_system_prompt = config.get("default_system_prompt")
        self.generation_params = config.get("generation_params", {})
        self.http_referer = config.get("http_referer", "http://localhost:3000") # Example referer
        request_timeout = config.get("request_timeout", 60) # OpenRouter can sometimes be slow

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
            logger.info(f"Default system prompt: {self.default_system_prompt[:100]}...")
        if self.generation_params:
            logger.info(f"Default generation parameters: {self.generation_params}")

import json # For potential JSON parsing errors

    async def _make_chat_completion_request(self, messages: list, generation_params_override: dict = None) -> str:
        """
        Helper method to make a request to the /chat/completions endpoint.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
        }

        # Merge default generation_params with overrides, then with payload
        current_generation_params = {**self.generation_params, **(generation_params_override or {})}
        payload.update(current_generation_params)

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

            response_data = response.json()

            if not response_data.get("choices") or not response_data["choices"][0].get("message") \
               or "content" not in response_data["choices"][0]["message"]:
                logger.error(f"Invalid response structure from OpenRouter: {response_data}")
                raise OpenRouterApiError("Invalid response structure from OpenRouter.", status_code=response.status_code)

            content = response_data["choices"][0]["message"]["content"]
            logger.info(f"Successfully received response from OpenRouter. Choice 0 content length: {len(content)}")
            return content.strip()

        except httpx.RequestError as e:
            logger.error(f"Error connecting to OpenRouter API: {e}")
            raise OpenRouterApiError(f"Connection to OpenRouter failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API request failed: {e.response.status_code} - {e.response.text[:200]}")
            # Attempt to parse error details from OpenRouter response if available
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                if error_json and "error" in error_json:
                    error_detail = error_json["error"].get("message", error_detail)
            except json.JSONDecodeError:
                pass # Use text if JSON parsing fails
            raise OpenRouterApiError(f"OpenRouter API error: {e.response.status_code} - {error_detail}", status_code=e.response.status_code) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from OpenRouter: {e}")
            raise OpenRouterApiError(f"Invalid JSON response from OpenRouter: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during OpenRouter request: {e}")
            raise OpenRouterApiError(f"An unexpected error occurred: {e}") from e


    async def check_availability(self) -> bool:
        """
        Checks if the OpenRouter API is available by trying to fetch the list of models.
        This also implicitly checks if the API key is valid.
        """
        logger.info(f"Checking OpenRouter API availability and API key validity at {self.api_base_url}...")
        try:
            # OpenRouter's /models endpoint is suitable for checking key validity and reachability.
            # It doesn't list all models for all users but confirms the API is responsive.
            # Alternatively, a very cheap model could be queried with a max_tokens: 1 prompt.
            response = await self.client.get("/models") # This endpoint might be restricted for some keys
                                                     # A more universal check might be a simple, cheap chat completion.
                                                     # For now, we'll assume /models gives some indication or use a test call.

            # If /models is restricted, let's try a more direct check using a very simple chat completion.
            if response.status_code == 401 or response.status_code == 403: # Unauthorized or Forbidden
                 logger.warning(f"/models endpoint check returned {response.status_code}. Attempting fallback check with test chat completion.")
                 # Fallback: try a very cheap request to a known free model
                 test_payload = {
                     "model": self.model_name or self.DEFAULT_MODEL_NAME, # Use configured or default
                     "messages": [{"role": "user", "content": "test"}],
                     "max_tokens": 1
                 }
                 response = await self.client.post("/chat/completions", json=test_payload)

            response.raise_for_status() # Check for 4xx/5xx after potential fallback

            # Check if response is as expected (e.g., contains 'data' for /models or 'choices' for chat)
            response_data = response.json()
            if "data" in response_data or "choices" in response_data :
                logger.info("OpenRouter API is available and API key appears valid.")
                return True
            else:
                logger.warning(f"OpenRouter API availability check returned unexpected data structure: {response_data}")
                return False # Or True, depending on how strict we want to be with /models response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error(f"OpenRouter API key is invalid or not authorized. Status: {e.response.status_code}")
            else:
                logger.error(f"OpenRouter API availability check failed with status {e.response.status_code}: {e.response.text[:200]}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Error connecting to OpenRouter for availability check: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during OpenRouter availability check: {e}")
            return False

    async def generate_code(self, user_prompt: str, system_instruction: str = None, context: str = "") -> str:
        """
        Generates code based on the given prompt and context using OpenRouter.
        """
        logger.info(f"generate_code called with user_prompt: {user_prompt[:50]}...")

        messages = []
        current_system_prompt = system_instruction if system_instruction is not None else self.default_system_prompt
        if current_system_prompt:
            messages.append({"role": "system", "content": current_system_prompt})

        full_user_prompt = f"{context}\n\n{user_prompt}" if context else user_prompt
        messages.append({"role": "user", "content": full_user_prompt})

        return await self._make_chat_completion_request(messages)

    async def explain_code(self, code_snippet: str, system_instruction: str = None, context: str = "") -> str:
        """
        Explains the given code snippet using OpenRouter.
        """
        logger.info(f"explain_code called for code snippet: {code_snippet[:50]}...")

        messages = []
        current_system_prompt = system_instruction
        if current_system_prompt is None:
            current_system_prompt = self.default_system_prompt if self.default_system_prompt \
                                 else "You are an expert code explainer. Provide clear and concise explanations for the given code."
        messages.append({"role": "system", "content": current_system_prompt})

        user_content = f"{context}\n\nPlease explain the following code snippet:\n```\n{code_snippet}\n```" if context \
                       else f"Please explain the following code snippet:\n```\n{code_snippet}\n```"
        messages.append({"role": "user", "content": user_content})

        return await self._make_chat_completion_request(messages)

    async def suggest_code_modification(self, code_snippet: str, instruction: str, system_instruction: str = None, context: str = "") -> str:
        """
        Suggests modifications to the code snippet based on the instruction using OpenRouter.
        """
        logger.info(f"suggest_code_modification called for code: {code_snippet[:50]} with instruction: {instruction}")

        messages = []
        current_system_prompt = system_instruction
        if current_system_prompt is None:
            current_system_prompt = self.default_system_prompt if self.default_system_prompt \
                                 else "You are an expert code modification assistant. Given a code snippet and an instruction, provide the modified code or a clear description of changes."
        messages.append({"role": "system", "content": current_system_prompt})

        user_content = f"{context}\n\nCode snippet:\n```\n{code_snippet}\n```\n\nInstruction for modification: {instruction}\n\nPlease provide the modified code snippet or explain the necessary changes." if context \
                       else f"Code snippet:\n```\n{code_snippet}\n```\n\nInstruction for modification: {instruction}\n\nPlease provide the modified code snippet or explain the necessary changes."
        messages.append({"role": "user", "content": user_content})

        return await self._make_chat_completion_request(messages)

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
    sample_config = {
        "api_key_env_var": "OPENROUTER_API_KEY",
        "model_name": "mistralai/mistral-7b-instruct", # A common free model
        "http_referer": "YOUR_SITE_URL_HERE", # Replace with your actual site URL or test name
        "default_system_prompt": "You are a helpful coding assistant.",
        "generation_params": {"temperature": 0.7, "max_tokens": 100}
    }

    async def main():
        try:
            connector = OpenRouterConnector(config=sample_config)
            logger.info("Connector created.")

            # Test check_availability (placeholder)
            available = await connector.check_availability()
            logger.info(f"Availability: {available}")

            # Test generate_code (placeholder)
            # code = await connector.generate_code("Write a python function to add two numbers.")
            # logger.info(f"Generated code (placeholder): {code}")

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            if 'connector' in locals() and connector:
                await connector.close()

    if os.getenv("OPENROUTER_API_KEY") and sample_config["http_referer"] != "YOUR_SITE_URL_HERE":
        asyncio.run(main())
    else:
        logger.warning("Skipping example usage: OPENROUTER_API_KEY not set or http_referer not configured.")
        logger.warning("To run this example, set OPENROUTER_API_KEY environment variable and update http_referer in sample_config.")
        logger.warning("Example: export OPENROUTER_API_KEY='your_api_key_here'")
