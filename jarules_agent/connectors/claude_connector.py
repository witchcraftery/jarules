import logging
import os
import anthropic # Official Anthropic SDK

from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

logger = logging.getLogger(__name__)

# Define a custom exception for Claude API errors
class ClaudeApiError(Exception):
    """Custom exception for Anthropic Claude API errors."""
    def __init__(self, message, status_code=None, error_type=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type # e.g., 'authentication_error', 'rate_limit_error'

class ClaudeConnector(BaseLLMConnector):
    """
    Connector for interacting with Anthropic's Claude models.
    """

    DEFAULT_MODEL_NAME = "claude-3-opus-20240229"
    DEFAULT_MAX_TOKENS = 2048 # Default max tokens for Claude, can be overridden by config

    def __init__(self, config: dict):
        """
        Initializes the ClaudeConnector.

        Args:
            config: A dictionary containing configuration parameters.
                    Expected keys:
                    - 'api_key_env_var' (str): Name of the environment variable holding the API key.
                    - 'model_name' (str, optional): Default model to use (e.g., "claude-3-opus-20240229").
                    - 'default_system_prompt' (str, optional): Default system prompt text.
                    - 'max_tokens' (int, optional): Default maximum number of tokens to generate.
                    - 'request_timeout' (int, optional): Timeout for API requests in seconds.
                    - 'anthropic_version_header' (str, optional): Value for the 'anthropic-version' header.
        """
        super().__init__(config)

        api_key_env_var = config.get("api_key_env_var", "ANTHROPIC_API_KEY")
        self.api_key = os.environ.get(api_key_env_var)
        if not self.api_key:
            raise ValueError(f"API key not found. Set the {api_key_env_var} environment variable.")

        self.model_name = config.get("model_name", self.DEFAULT_MODEL_NAME)
        self.default_system_prompt = config.get("default_system_prompt")
        self.max_tokens = config.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        request_timeout = config.get("request_timeout", 60) # Default to 60 seconds

        # The Anthropic SDK uses ANTHROPIC_API_KEY env var by default if api_key is not passed to constructor.
        # Explicitly passing it ensures we use the one specified by api_key_env_var.
        # The SDK also allows setting other headers like 'anthropic-version'.
        custom_headers = {}
        anthropic_version = config.get("anthropic_version_header")
        if anthropic_version:
            custom_headers["anthropic-version"] = anthropic_version

        try:
            self.client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                timeout=request_timeout,
                custom_headers=custom_headers if custom_headers else None
            )
        except Exception as e: # Catch potential errors during client initialization
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise ClaudeApiError(f"Anthropic client initialization failed: {e}") from e

        logger.info(
            f"ClaudeConnector initialized with model: {self.model_name}, "
            f"max_tokens: {self.max_tokens}, timeout: {request_timeout}, "
            f"anthropic_version: {anthropic_version or 'SDK Default'}"
        )
        if self.default_system_prompt:
            logger.info(f"Default system prompt: {self.default_system_prompt[:100]}...")


import anthropic.APIStatusError # For more specific error handling

    async def _create_message(
        self,
        messages: list,
        system_prompt_override: str = None,
        generation_params_override: dict = None
    ) -> str:
        """
        Private helper method to interact with self.client.messages.create().
        Constructs the request and handles API responses and errors.

        Args:
            messages: A list of message dictionaries (e.g., [{"role": "user", "content": ...}]).
            system_prompt_override: An optional system prompt to use instead of the default.
            generation_params_override: Optional dictionary to override default generation parameters.

        Returns:
            The text content from Claude's response.

        Raises:
            ClaudeApiError: If any API error occurs.
        """
        current_system_prompt = system_prompt_override if system_prompt_override is not None else self.default_system_prompt

        # Merge generation parameters
        final_generation_params = {**self.generation_params, **(generation_params_override or {})}

        try:
            logger.debug(
                f"Sending request to Claude. Model: {self.model_name}, System: {current_system_prompt[:100] if current_system_prompt else 'None'}, "
                f"Messages: {str(messages)[:200]}, Max Tokens: {self.max_tokens}, Params: {final_generation_params}"
            )
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=current_system_prompt, # Can be None, SDK handles it
                messages=messages,
                **final_generation_params # Spread other params like temperature, top_p, etc.
            )

            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                # Assuming the first content block is the primary text response
                if hasattr(response.content[0], 'text'):
                    text_content = response.content[0].text
                    logger.info(f"Successfully received response from Claude. Content length: {len(text_content)}")
                    return text_content.strip()
                else:
                    logger.error(f"Claude response content block does not have text attribute: {response.content[0]}")
                    raise ClaudeApiError("Invalid response structure: content block missing text.", status_code=None) # Or use a specific status
            else:
                logger.warning(f"Claude response was empty or invalid: {response}")
                # It's possible Claude returns an empty but valid response (e.g. if input is unsafe)
                # Depending on stop_reason, this might be normal. For now, return empty string.
                # Example: response.stop_reason == 'stop_sequence' with empty content.
                if response.stop_reason:
                     logger.info(f"Claude response had stop_reason: {response.stop_reason} with empty content.")
                     return ""
                raise ClaudeApiError("Empty or invalid response content from Claude.", status_code=None)


        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API connection error: {e}")
            raise ClaudeApiError(f"Connection to Claude API failed: {e}", status_code=e.status_code, error_type="connection_error") from e
        except anthropic.RateLimitError as e:
            logger.error(f"Claude API rate limit exceeded: {e}")
            raise ClaudeApiError(f"Claude API rate limit exceeded: {e}", status_code=e.status_code, error_type="rate_limit_error") from e
        except anthropic.AuthenticationError as e:
            logger.error(f"Claude API authentication error: {e}")
            raise ClaudeApiError(f"Claude API authentication failed (check API key): {e}", status_code=e.status_code, error_type="authentication_error") from e
        except anthropic.PermissionDeniedError as e:
            logger.error(f"Claude API permission denied: {e}")
            raise ClaudeApiError(f"Claude API permission denied: {e}", status_code=e.status_code, error_type="permission_denied_error") from e
        except anthropic.NotFoundError as e:
            logger.error(f"Claude API resource not found (e.g. model name issue): {e}")
            raise ClaudeApiError(f"Claude API resource not found: {e}", status_code=e.status_code, error_type="not_found_error") from e
        except anthropic.APIStatusError as e: # General status error from Anthropic SDK
            logger.error(f"Claude API status error: {e.status_code} - {e.message}")
            raise ClaudeApiError(f"Claude API error: {e.status_code} - {e.message}", status_code=e.status_code, error_type=e.type if hasattr(e, 'type') else "api_error") from e
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"An unexpected error occurred with Claude API: {e}", exc_info=True)
            raise ClaudeApiError(f"An unexpected error occurred: {e}", status_code=None, error_type="unexpected_error") from e


    async def check_availability(self) -> bool:
        """
        Checks if the Claude API is available and the API key is valid.
        Makes a simple, low-cost API call.
        """
        logger.info("Checking Claude API availability...")
        try:
            test_messages = [{"role": "user", "content": "ping"}]
            # Use minimal max_tokens for this check
            await self._create_message(messages=test_messages, generation_params_override={"max_tokens": 5})
            logger.info("Claude API is available and key is valid.")
            return True
        except ClaudeApiError as e:
            logger.error(f"Claude API availability check failed: {e.message} (Type: {e.error_type}, Status: {e.status_code})")
            return False
        except Exception as e: # Should be caught by ClaudeApiError but as a safeguard
            logger.error(f"Unexpected error during Claude availability check: {e}")
            return False


    async def generate_code(self, user_prompt: str, system_instruction: str = None, context: str = "") -> str:
        """
        Generates code based on the given prompt and context using Claude.
        """
        logger.info(f"generate_code called with user_prompt: {user_prompt[:50]}...")

        full_user_prompt = f"{context}\n\n{user_prompt}" if context else user_prompt
        messages = [{"role": "user", "content": full_user_prompt}]

        # System instruction is passed as system_prompt_override to _create_message
        return await self._create_message(messages=messages, system_prompt_override=system_instruction)

    async def explain_code(self, code_snippet: str, system_instruction: str = None, context: str = "") -> str:
        """
        Explains the given code snippet using Claude.
        """
        logger.info(f"explain_code called for code snippet: {code_snippet[:50]}...")

        user_content = f"{context}\n\nPlease explain the following code snippet:\n```\n{code_snippet}\n```" if context \
                       else f"Please explain the following code snippet:\n```\n{code_snippet}\n```"
        messages = [{"role": "user", "content": user_content}]

        # Use a method-specific default system prompt if no override is given
        final_system_prompt = system_instruction
        if final_system_prompt is None and not self.default_system_prompt: # Only if no connector default either
            final_system_prompt = "You are an expert code explainer. Provide clear and concise explanations for the given code."

        return await self._create_message(messages=messages, system_prompt_override=final_system_prompt)

    async def suggest_code_modification(self, code_snippet: str, instruction: str, system_instruction: str = None, context: str = "") -> str:
        """
        Suggests modifications to the code snippet based on the instruction using Claude.
        """
        logger.info(f"suggest_code_modification called for code: {code_snippet[:50]} with instruction: {instruction}")

        user_content = (
            f"{context}\n\n" if context else "" +
            f"Code snippet:\n```\n{code_snippet}\n```\n\n"
            f"Instruction for modification: {instruction}\n\n"
            "Please provide the modified code snippet or explain the necessary changes."
        )
        messages = [{"role": "user", "content": user_content}]

        final_system_prompt = system_instruction
        if final_system_prompt is None and not self.default_system_prompt:
            final_system_prompt = "You are an expert code modification assistant. Given a code snippet and an instruction, provide the modified code or a clear description of changes. If providing code, try to provide only the complete, runnable code block."

        return await self._create_message(messages=messages, system_prompt_override=final_system_prompt)

    async def close(self):
        """
        Closes the Anthropic client.
        The Anthropic SDK's AsyncAnthropic client has an `aclose()` method.
        """
        if hasattr(self, 'client') and self.client:
            try:
                await self.client.aclose()
                logger.info("ClaudeConnector's Anthropic client closed.")
            except Exception as e:
                logger.error(f"Error closing Anthropic client: {e}")

# Example usage (for testing purposes, if run directly)
if __name__ == '__main__':
    import asyncio

    # This requires ANTHROPIC_API_KEY to be set in the environment.
    sample_config = {
        "api_key_env_var": "ANTHROPIC_API_KEY", # Ensure this env var is set
        "model_name": "claude-3-haiku-20240307", # Use a cheaper model for testing
        "max_tokens": 150,
        "default_system_prompt": "You are a concise coding assistant.",
        "anthropic_version_header": "2023-06-01" # Example header
    }

    async def main():
        connector = None # Ensure connector is defined for finally block
        try:
            connector = ClaudeConnector(config=sample_config)
            logger.info("ClaudeConnector created.")

            available = await connector.check_availability() # Placeholder
            logger.info(f"Availability (placeholder): {available}")

            # Example: Test generate_code (placeholder)
            # code_response = await connector.generate_code("Write a simple Python 'hello world' function.")
            # logger.info(f"Generated code (placeholder): {code_response}")

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
        except ClaudeApiError as e:
            logger.error(f"Claude API error during example: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during example: {e}", exc_info=True)
        finally:
            if connector:
                await connector.close()

    if os.getenv("ANTHROPIC_API_KEY"):
        asyncio.run(main())
    else:
        logger.warning("Skipping ClaudeConnector example: ANTHROPIC_API_KEY not set.")
        logger.warning("To run this example, set the ANTHROPIC_API_KEY environment variable.")
        logger.warning("Example: export ANTHROPIC_API_KEY='your_anthropic_api_key_here'")
