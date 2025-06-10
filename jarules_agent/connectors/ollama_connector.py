import logging
import httpx
import json # For potential JSON parsing errors

from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

logger = logging.getLogger(__name__)

# Define a custom exception for Ollama API errors
class OllamaApiError(Exception):
    """Custom exception for Ollama API errors."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class OllamaConnector(BaseLLMConnector):
    """
    Connector for interacting with local LLMs through the Ollama API.
    """

    def __init__(self, config: dict):
        """
        Initializes the OllamaConnector.

        Args:
            config: A dictionary containing configuration parameters for Ollama.
                    Expected keys:
                    - 'api_base_url' (str): The base URL for the Ollama API.
                    - 'model_name' (str): The default model to use.
                    - 'default_system_prompt' (str, optional): Default system prompt.
                    - 'generation_params' (dict, optional): Default generation parameters
                                                             (e.g., temperature, top_p).
                    - 'request_timeout' (int, optional): Timeout for HTTP requests in seconds.
        """
        super().__init__(model_name=config.get("model_name", "llama3"), **config) # Pass model_name and other config to BaseLLMConnector
        self.api_base_url = self._config.get("api_base_url", "http://localhost:11434")
        # Ensure base URL doesn't end with a slash to simplify joining with /api/generate etc.
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]

        # self.model_name is already set by BaseLLMConnector
        self.default_system_prompt = self._config.get("default_system_prompt", None)
        self.generation_params = self._config.get("generation_params", {})
        request_timeout = self._config.get("request_timeout", 30) # Default timeout 30 seconds

        self.client = httpx.AsyncClient(base_url=self.api_base_url, timeout=request_timeout)
        logger.info(
            f"OllamaConnector initialized with base_url: {self.api_base_url}, "
            f"model: {self.model_name}, timeout: {request_timeout}" # self.model_name from BaseLLMConnector
        )
        if self.default_system_prompt: # self.default_system_prompt from self._config
            logger.info(f"Default system prompt: {(self.default_system_prompt or '')[:100]}...")
        if self.generation_params:
            logger.info(f"Default generation parameters: {self.generation_params}")


    async def check_availability(self) -> bool:
        """
        Checks if the Ollama API is available and the configured model is listed.
        Tries to hit GET /api/tags to list models, then GET / to confirm Ollama is running.
        """
        try:
            # 1. Check if the configured model is available
            response_tags = await self.client.get("/api/tags")
            response_tags.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            models_data = response_tags.json()

            available_models = [model.get("name") for model in models_data.get("models", [])]
            # Ollama model names can be like "llama3:latest" or just "llama3"
            # So we check if self.model_name is a substring of any available model
            model_found = any(self.model_name in available_model for available_model in available_models)

            if not model_found:
                logger.warning(
                    f"Configured model '{self.model_name}' not found in available models: {available_models}. "
                    f"Ollama is running, but the specific model might be missing."
                )
                # Depending on strictness, you could return False here.
                # For now, if Ollama itself is running, we'll consider it "partially available".
                # Let's proceed to check if Ollama server itself is running.

            # 2. Check if Ollama server is running (basic check)
            response_root = await self.client.get("/")
            if response_root.status_code == 200 and "Ollama is running" in response_root.text:
                logger.info(f"Ollama API is available at {self.api_base_url}. Configured model '{self.model_name}' found: {model_found}.")
                return True
            else:
                logger.error(
                    f"Ollama API root endpoint check failed. Status: {response_root.status_code}, "
                    f"Response: {response_root.text[:200]}"
                )
                return False

        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama API at {self.api_base_url}: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API request failed: {e.response.status_code} - {e.response.text[:200]}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama /api/tags: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama availability check: {e}")
            return False

from typing import Optional, List, Dict, Any # Added Optional, List, Dict, Any

# Define a custom exception for Ollama API errors
class OllamaApiError(Exception): # Should inherit from LLMConnectorError or a base Exception from base_llm_connector
    """Custom exception for Ollama API errors."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class OllamaConnector(BaseLLMConnector): # BaseLLMConnector now expects model_name as first arg
    """
    Connector for interacting with local LLMs through the Ollama API.
    """

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any): # Updated signature
        """
        Initializes the OllamaConnector.

        Args:
            model_name: Optional. The default model to use (e.g., "llama3").
            **kwargs: Configuration parameters for Ollama.
                      Expected keys in kwargs:
                      - 'api_base_url' (str): The base URL for the Ollama API.
                                              Defaults to "http://localhost:11434".
                      - 'default_system_prompt' (str, optional): Default system prompt.
                      - 'generation_params' (dict, optional): Default generation parameters
                                                               (e.g., temperature, top_p).
                      - 'request_timeout' (int, optional): Timeout for HTTP requests in seconds.
                                                           Defaults to 30.
        """
        effective_model_name = model_name or kwargs.get("model_name") or "llama3" # Prioritize explicit, then in kwargs, then default
        super().__init__(model_name=effective_model_name, **kwargs) # Pass model_name and other config to BaseLLMConnector

        self.api_base_url = self._config.get("api_base_url", "http://localhost:11434")
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]

        self.default_system_prompt = self._config.get("default_system_prompt")
        self.generation_params = self._config.get("generation_params", {})
        request_timeout = self._config.get("request_timeout", 30)

        self.client = httpx.AsyncClient(base_url=self.api_base_url, timeout=request_timeout)
        logger.info(
            f"OllamaConnector initialized with base_url: {self.api_base_url}, "
            f"model: {self.model_name}, timeout: {request_timeout}"
        )
        if self.default_system_prompt:
            logger.info(f"Default system prompt: {(self.default_system_prompt or '')[:100]}...")
        if self.generation_params:
            logger.info(f"Default generation parameters: {self.generation_params}")

    async def _make_request(self, endpoint: str, method_payload: dict, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Helper function to make a request to Ollama API.
        Handles /api/generate and /api/chat based on history.
        """
        payload = {
            "model": self.model_name,
            "stream": False, # For simplicity
            # "options" will be merged from self.generation_params and method_payload.options if any
        }

        # Merge system prompt
        if method_payload.get("system"):
            payload["system"] = method_payload["system"]

        # Merge generation options
        options = self.generation_params.copy() # Start with class defaults
        if method_payload.get("options"):
            options.update(method_payload["options"]) # Override with method-specific options
        if options:
            payload["options"] = options

        # Determine if using /api/chat or /api/generate based on history
        # Ollama's /api/chat expects "messages": [{"role": "user/assistant", "content": "..."}]
        # /api/generate expects "prompt": "...", "system": "..." (optional), "context": [] (optional for prior turns)

        actual_endpoint = endpoint # default to /api/generate or whatever was passed

        if history: # Use /api/chat if history is provided
            actual_endpoint = "/api/chat"
            messages = []
            for item in history:
                # Transform history keys: "text" or "content" to "content"
                content = item.get("text") or item.get("content")
                if not content: continue # Skip if no content

                # Ensure role is "user" or "assistant". Default to "user" if unknown.
                role = item.get("role", "user").lower()
                if role not in ["user", "assistant", "system"]: # Ollama chat supports system role in messages
                    logger.warning(f"Unknown role '{role}' in history, defaulting to 'user'.")
                    role = "user"
                messages.append({"role": role, "content": content})

            # Add the current user prompt to messages
            if method_payload.get("prompt"): # For chat, the "prompt" is the last user message
                 messages.append({"role": "user", "content": method_payload["prompt"]})

            payload["messages"] = messages
            # Remove "prompt" and "system" from payload if using /api/chat, as they are in "messages"
            payload.pop("prompt", None)
            # payload.pop("system", None) # System prompt can be a top-level element for /api/chat too
            if payload.get("system") and any(m["role"] == "system" for m in messages):
                logger.warning("System prompt provided both at top-level and in messages for /api/chat. Top-level might be preferred by Ollama.")

        else: # No history, use /api/generate (or the original endpoint)
            if "prompt" in method_payload:
                payload["prompt"] = method_payload["prompt"]
            # "context" for /api/generate is for passing back the context from previous /api/generate calls,
            # not the same as conversational history. For now, we are not managing this low-level context.

        logger.debug(f"Ollama request to {actual_endpoint}. Payload: {json.dumps(payload, indent=2)}")

        try:
            response = await self.client.post(actual_endpoint, json=payload)
            response.raise_for_status()
            response_data = response.json()

            if actual_endpoint == "/api/chat":
                # For /api/chat, the response structure is like:
                # { "model": "...", "created_at": "...", "message": { "role": "assistant", "content": "..." }, "done": true }
                generated_text = response_data.get("message", {}).get("content", "")
            else: # /api/generate
                generated_text = response_data.get("response", "")

            if not generated_text and response_data.get("done", False):
                logger.warning(f"Ollama response was empty from {actual_endpoint} but request was marked as done.")

            logger.info(f"Successfully received response from Ollama {actual_endpoint}. Length: {len(generated_text)}")
            return generated_text.strip()

        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama API for {actual_endpoint}: {e}")
            raise OllamaApiError(f"Connection to Ollama failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API request failed for {actual_endpoint}: {e.response.status_code} - {e.response.text[:200]}")
            raise OllamaApiError(f"Ollama API error: {e.response.status_code} - {e.response.text[:200]}", status_code=e.response.status_code) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama {actual_endpoint}: {e}")
            raise OllamaApiError(f"Invalid JSON response from Ollama: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama {actual_endpoint}: {e}")
            raise OllamaApiError(f"An unexpected error occurred: {e}") from e


    async def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        logger.info(f"generate_code called with user_prompt: {user_prompt[:50]}...")
        current_system_prompt = system_instruction if system_instruction is not None else self.default_system_prompt

        # The 'context' parameter from the old signature is not used here.
        # If context is needed, it should be part of the user_prompt or history.

        payload = {
            "prompt": user_prompt, # This will be the main content for /api/generate or last message for /api/chat
            "system": current_system_prompt,
            "options": kwargs.get("options", {}) # Allow overriding generation_params via kwargs
        }
        return await self._make_request("/api/generate", payload, history=history)


    async def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        logger.info(f"explain_code called for code snippet: {code_snippet[:50]}...")

        prompt = f"Please explain the following code snippet:\n```\n{code_snippet}\n```"

        current_system_prompt = system_instruction
        if current_system_prompt is None:
             current_system_prompt = self.default_system_prompt if self.default_system_prompt else "You are an expert code explainer. Provide clear and concise explanations."

        payload = {
            "prompt": prompt,
            "system": current_system_prompt,
            "options": kwargs.get("options", {})
        }
        return await self._make_request("/api/generate", payload, history=history)


    async def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        logger.info(f"suggest_code_modification called for code: {code_snippet[:50]} with issue: {issue_description[:50]}")

        prompt = (
            f"Code snippet:\n```\n{code_snippet}\n```\n\n"
            f"Issue/Request for modification: {issue_description}\n\n"
            "Please provide the modified code snippet."
        )

        current_system_prompt = system_instruction
        if current_system_prompt is None:
            current_system_prompt = self.default_system_prompt if self.default_system_prompt else "You are an expert code modification assistant. Provide only the modified code or a clear description of changes if code modification isn't directly possible."

        payload = {
            "prompt": prompt,
            "system": current_system_prompt,
            "options": kwargs.get("options", {})
        }
        return await self._make_request("/api/generate", payload, history=history)

    async def close(self):
        """
        Closes the httpx client.
        Should be called when the application is shutting down.
        """
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()
            logger.info("OllamaConnector's HTTP client closed.")
