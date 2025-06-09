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
        super().__init__(config)
        self.api_base_url = config.get("api_base_url", "http://localhost:11434")
        # Ensure base URL doesn't end with a slash to simplify joining with /api/generate etc.
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]

        self.model_name = config.get("model_name", "llama3") # Renamed from default_model for clarity
        self.default_system_prompt = config.get("default_system_prompt", None)
        self.generation_params = config.get("generation_params", {})
        request_timeout = config.get("request_timeout", 30) # Default timeout 30 seconds

        self.client = httpx.AsyncClient(base_url=self.api_base_url, timeout=request_timeout)
        logger.info(
            f"OllamaConnector initialized with base_url: {self.api_base_url}, "
            f"model: {self.model_name}, timeout: {request_timeout}"
        )
        if self.default_system_prompt:
            logger.info(f"Default system prompt: {self.default_system_prompt[:100]}...")
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

    async def generate_code(self, user_prompt: str, system_instruction: str = None, context: str = "") -> str:
        """
        Generates code based on the given prompt and context using Ollama.
        (Placeholder implementation)
        """
        logger.info(f"generate_code called with prompt: {prompt[:50]}...")
        # Actual implementation will involve making an HTTP request to Ollama
        """
        Generates code based on the given prompt and context using Ollama.
        (Implementation for stream: false)
        """
        logger.info(f"generate_code called with user_prompt: {user_prompt[:50]}...")

        current_system_prompt = system_instruction if system_instruction is not None else self.default_system_prompt

        # Constructing the full prompt or payload
        # Context can be prepended to the user_prompt or handled in a more structured way if the model supports it.
        full_prompt = f"{context}\n\nUser: {user_prompt}" if context else user_prompt

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False, # For simplicity in this version
            # "options": self.generation_params, # Pass through other params like temperature
        }
        if current_system_prompt:
            payload["system"] = current_system_prompt

        # Merge default generation_params with any specific ones if needed later
        if self.generation_params:
            payload.setdefault("options", {}).update(self.generation_params)


        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            response_data = response.json()

            # The 'response' field contains the generated text.
            # Other fields include 'created_at', 'model', 'done', 'total_duration', etc.
            generated_text = response_data.get("response", "")
            if not generated_text and response_data.get("done", False):
                logger.warning("Ollama response was empty but request was marked as done.")

            logger.info(f"Successfully received response from Ollama for generate_code. Length: {len(generated_text)}")
            return generated_text.strip()

        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama API for generate_code: {e}")
            raise OllamaApiError(f"Connection to Ollama failed: {e}", status_code=None) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API request failed for generate_code: {e.response.status_code} - {e.response.text[:200]}")
            raise OllamaApiError(f"Ollama API error: {e.response.status_code} - {e.response.text[:200]}", status_code=e.response.status_code) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama generate_code: {e}")
            raise OllamaApiError(f"Invalid JSON response from Ollama: {e}", status_code=None) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama generate_code: {e}")
            raise OllamaApiError(f"An unexpected error occurred: {e}", status_code=None) from e


    async def explain_code(self, code_snippet: str, system_instruction: str = None, context: str = "") -> str:
        """
        Explains the given code snippet using Ollama.
        """
        logger.info(f"explain_code called for code snippet: {code_snippet[:50]}...")

        prompt = f"{context}\n\nPlease explain the following code snippet:\n```\n{code_snippet}\n```" if context \
            else f"Please explain the following code snippet:\n```\n{code_snippet}\n```"

        # Use a default system prompt if none provided, or tailor one for explanation
        current_system_prompt = system_instruction
        if current_system_prompt is None:
             current_system_prompt = self.default_system_prompt if self.default_system_prompt else "You are an expert code explainer. Provide clear and concise explanations."

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": current_system_prompt,
            "stream": False,
        }
        if self.generation_params:
            payload.setdefault("options", {}).update(self.generation_params)

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            response_data = response.json()
            explanation = response_data.get("response", "").strip()
            logger.info(f"Successfully received explanation from Ollama. Length: {len(explanation)}")
            return explanation
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama API for explain_code: {e}")
            raise OllamaApiError(f"Connection to Ollama failed: {e}", status_code=None) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API request failed for explain_code: {e.response.status_code} - {e.response.text[:200]}")
            raise OllamaApiError(f"Ollama API error: {e.response.status_code} - {e.response.text[:200]}", status_code=e.response.status_code) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama explain_code: {e}")
            raise OllamaApiError(f"Invalid JSON response from Ollama: {e}", status_code=None) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama explain_code: {e}")
            raise OllamaApiError(f"An unexpected error occurred: {e}", status_code=None) from e


    async def suggest_code_modification(self, code_snippet: str, instruction: str, system_instruction: str = None, context: str = "") -> str:
        """
        Suggests modifications to the code snippet based on the instruction using Ollama.
        """
        logger.info(f"suggest_code_modification called for code: {code_snippet[:50]} with instruction: {instruction}")

        prompt = f"{context}\n\nCode snippet:\n```\n{code_snippet}\n```\n\nInstruction for modification: {instruction}\n\nPlease provide the modified code snippet or explain the necessary changes." if context \
            else f"Code snippet:\n```\n{code_snippet}\n```\n\nInstruction for modification: {instruction}\n\nPlease provide the modified code snippet or explain the necessary changes."

        current_system_prompt = system_instruction
        if current_system_prompt is None:
            current_system_prompt = self.default_system_prompt if self.default_system_prompt else "You are an expert code modification assistant. Provide only the modified code or a clear description of changes if code modification isn't directly possible."

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": current_system_prompt,
            "stream": False,
        }
        if self.generation_params:
            payload.setdefault("options", {}).update(self.generation_params)

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            response_data = response.json()
            suggestion = response_data.get("response", "").strip()
            logger.info(f"Successfully received code modification suggestion from Ollama. Length: {len(suggestion)}")
            return suggestion
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama API for suggest_code_modification: {e}")
            raise OllamaApiError(f"Connection to Ollama failed: {e}", status_code=None) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API request failed for suggest_code_modification: {e.response.status_code} - {e.response.text[:200]}")
            raise OllamaApiError(f"Ollama API error: {e.response.status_code} - {e.response.text[:200]}", status_code=e.response.status_code) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama suggest_code_modification: {e}")
            raise OllamaApiError(f"Invalid JSON response from Ollama: {e}", status_code=None) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama suggest_code_modification: {e}")
            raise OllamaApiError(f"An unexpected error occurred: {e}", status_code=None) from e

    async def close(self):
        """
        Closes the httpx client.
        Should be called when the application is shutting down.
        """
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()
            logger.info("OllamaConnector's HTTP client closed.")
