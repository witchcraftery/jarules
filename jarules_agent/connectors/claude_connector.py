import logging
import os
import anthropic # Official Anthropic SDK
from typing import Optional, List, Dict, Any # Added Optional, List, Dict, Any

from jarules_agent.connectors.base_llm_connector import BaseLLMConnector, LLMConnectorError

logger = logging.getLogger(__name__)

# Define a custom exception for Claude API errors
class ClaudeApiError(LLMConnectorError): # Inherit from LLMConnectorError
    """Custom exception for Anthropic Claude API errors."""
    def __init__(self, message, status_code=None, error_type=None, underlying_exception: Optional[Exception] = None):
        super().__init__(message, underlying_exception=underlying_exception)
        self.status_code = status_code
        self.error_type = error_type # e.g., 'authentication_error', 'rate_limit_error'

class ClaudeConnector(BaseLLMConnector):
    """
    Connector for interacting with Anthropic's Claude models.
    """

    DEFAULT_MODEL_NAME = "claude-3-opus-20240229"
    DEFAULT_MAX_TOKENS = 2048 # Default max tokens for Claude, can be overridden by config

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any): # Updated signature
        """
        Initializes the ClaudeConnector.

        Args:
            model_name: Optional. The default model to use (e.g., "claude-3-opus-20240229").
            **kwargs: Configuration parameters.
                      Expected keys in kwargs:
                      - 'api_key_env_var' (str): Name of the environment variable holding the API key.
                                                 Defaults to "ANTHROPIC_API_KEY".
                      - 'default_system_prompt' (str, optional): Default system prompt text.
                      - 'max_tokens' (int, optional): Default maximum number of tokens to generate.
                                                      Defaults to 2048.
                      - 'request_timeout' (int, optional): Timeout for API requests in seconds.
                                                           Defaults to 60.
                      - 'anthropic_version_header' (str, optional): Value for the 'anthropic-version' header.
                      - 'generation_params' (dict, optional): Additional generation parameters like temperature.
        """
        effective_model_name = model_name or kwargs.get("model_name") or self.DEFAULT_MODEL_NAME
        super().__init__(model_name=effective_model_name, **kwargs) # Pass to BaseLLMConnector

        api_key_env_var = self._config.get("api_key_env_var", "ANTHROPIC_API_KEY")
        self.api_key = os.environ.get(api_key_env_var)
        if not self.api_key:
            raise ClaudeApiError(f"API key not found. Set the {api_key_env_var} environment variable.")

        self.default_system_prompt = self._config.get("default_system_prompt")
        self.max_tokens = self._config.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.generation_params = self._config.get("generation_params", {}) # Store other generation params
        request_timeout = self._config.get("request_timeout", 60)

        custom_headers = {}
        anthropic_version = self._config.get("anthropic_version_header")
        if anthropic_version:
            custom_headers["anthropic-version"] = anthropic_version

        try:
            self.client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                timeout=request_timeout,
                custom_headers=custom_headers if custom_headers else None
            )
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise ClaudeApiError(f"Anthropic client initialization failed: {e}", underlying_exception=e) from e

        logger.info(
            f"ClaudeConnector initialized with model: {self.model_name}, "
            f"max_tokens: {self.max_tokens}, timeout: {request_timeout}, "
            f"anthropic_version: {anthropic_version or 'SDK Default'}"
        )
        if self.default_system_prompt:
            logger.info(f"Default system prompt: {(self.default_system_prompt or '')[:100]}...")
        if self.generation_params:
            logger.info(f"Default generation parameters: {self.generation_params}")


# For more specific error handling, anthropic.APIStatusError is useful.
# We'll also need `anthropic.APIConnectionError`, `anthropic.RateLimitError`, etc.

    async def _create_message(
        self,
        messages: List[Dict[str, Any]], # Content can be List[Dict] for complex content
        system_prompt_override: Optional[str] = None,
        generation_params_override: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Private helper method to interact with self.client.messages.create().
        Constructs the request and handles API responses and errors.
        """
        current_system_prompt = system_prompt_override if system_prompt_override is not None else self.default_system_prompt

        # Merge generation parameters: default_class_params < method_override_params
        final_generation_params = self.generation_params.copy()
        if generation_params_override:
            final_generation_params.update(generation_params_override)


        # Ensure max_tokens is part of the final_generation_params if not already, using self.max_tokens as default for it
        if 'max_tokens' not in final_generation_params:
            final_generation_params['max_tokens'] = self.max_tokens

        try:
            logger.debug(
                f"Sending request to Claude. Model: {self.model_name}, System: {(current_system_prompt or '')[:100]}, "
                f"Messages: {str(messages)[:200]}, Params: {final_generation_params}"
            )

            request_params = {
                "model": self.model_name,
                "messages": messages,
                **final_generation_params # Spread other params like temperature, top_p, max_tokens etc.
            }
            if current_system_prompt: # Only add system if it's not None or empty
                request_params["system"] = current_system_prompt

            response = await self.client.messages.create(**request_params)

            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                # Assuming the first content block is the primary text response
                # Claude can return multiple content blocks, e.g., text and tool_use
                # We are interested in the text block.
                text_content = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_content += block.text # Concatenate text from all text blocks if multiple (though rare for typical chat)

                if text_content:
                    logger.info(f"Successfully received response from Claude. Content length: {len(text_content)}")
                    return text_content.strip()
                else: # No text blocks found, but other content might exist (e.g. tool use)
                    logger.warning(f"Claude response did not contain any text content blocks. Stop reason: {response.stop_reason}. Full response: {response}")
                    # If stop_reason indicates completion but no text, return empty.
                    # If it's due to max_tokens or stop_sequence, empty might be valid.
                    return "" # Or raise error if text is strictly expected
            else: # No content blocks at all
                logger.warning(f"Claude response was empty or invalid: {response}. Stop Reason: {response.stop_reason}")
                if response.stop_reason: # e.g. 'max_tokens', 'stop_sequence'
                     logger.info(f"Claude response had stop_reason: {response.stop_reason} with empty content.")
                     return "" # Valid empty response
                raise ClaudeApiError("Empty or invalid response content from Claude.", status_code=None, underlying_exception=ValueError(str(response)))


        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API connection error: {e}")
            raise ClaudeApiError(f"Connection to Claude API failed: {e}", status_code=getattr(e, 'status_code', None), error_type="connection_error", underlying_exception=e) from e
        except anthropic.RateLimitError as e:
            logger.error(f"Claude API rate limit exceeded: {e}")
            raise ClaudeApiError(f"Claude API rate limit exceeded: {e}", status_code=getattr(e, 'status_code', None), error_type="rate_limit_error", underlying_exception=e) from e
        except anthropic.AuthenticationError as e:
            logger.error(f"Claude API authentication error: {e}")
            raise ClaudeApiError(f"Claude API authentication failed (check API key): {e}", status_code=getattr(e, 'status_code', None), error_type="authentication_error", underlying_exception=e) from e
        except anthropic.PermissionDeniedError as e:
            logger.error(f"Claude API permission denied: {e}")
            raise ClaudeApiError(f"Claude API permission denied: {e}", status_code=getattr(e, 'status_code', None), error_type="permission_denied_error", underlying_exception=e) from e
        except anthropic.NotFoundError as e:
            logger.error(f"Claude API resource not found (e.g. model name issue): {e}")
            raise ClaudeApiError(f"Claude API resource not found: {e}", status_code=getattr(e, 'status_code', None), error_type="not_found_error", underlying_exception=e) from e
        except anthropic.APIStatusError as e: # General status error from Anthropic SDK
            logger.error(f"Claude API status error: {e.status_code} - {e.message}")
            raise ClaudeApiError(f"Claude API error: {e.status_code} - {e.message}", status_code=e.status_code, error_type=getattr(e, 'type', "api_error"), underlying_exception=e) from e
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"An unexpected error occurred with Claude API: {e}", exc_info=True)
            raise ClaudeApiError(f"An unexpected error occurred: {e}", error_type="unexpected_error", underlying_exception=e) from e


    def check_availability(self) -> Dict[str, Any]:
        """
        Checks if the Claude API is available and the API key is valid.
        Makes a simple, low-cost API call.
        This method is synchronous to align with the base class, and runs the async check internally.
        """
        logger.info("Checking Claude API availability...")

        async def _async_check():
            # This is the original async logic
            test_messages = [{"role": "user", "content": "ping"}]
            await self._create_message(messages=test_messages, generation_params_override={"max_tokens": 5})

        try:
            # Run the internal async check function
            # If an event loop is already running (e.g., in a Jupyter notebook or other async app),
            # asyncio.run() cannot be used directly. We need to handle this.
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # If loop is running, create a task and run it. This is complex.
                    # For simplicity in this context, let's assume if we are in an async context already,
                    # this method should have been async. The requirement is to make it sync.
                    # So, we'll use asyncio.run, which creates its own event loop.
                    # This might fail if called from an already running asyncio event loop.
                    # A more robust solution might involve a helper that manages how to run async code.
                    # For now, we'll proceed with asyncio.run() and acknowledge this limitation.
                    pass # Fall through to asyncio.run() for now, or consider a more complex solution if issues arise.
            except RuntimeError: # No running event loop
                pass # asyncio.run() will create a new one.

            asyncio.run(_async_check())
            logger.info("Claude API is available and key is valid.")
            return {'available': True, 'details': 'Claude API is available and authentication is successful.'}

        except ClaudeApiError as e:
            logger.error(f"Claude API availability check failed: {e.message} (Type: {e.error_type}, Status: {e.status_code})")
            return {'available': False, 'details': f"Claude API error: {e.message} (Type: {e.error_type}, Status: {e.status_code})"}
        except Exception as e: # Catch any other unexpected errors, including issues with asyncio.run()
            logger.error(f"Unexpected error during Claude availability check: {e}")
            # This might include "asyncio.run() cannot be called from a running event loop"
            if "asyncio.run() cannot be called from a running event loop" in str(e):
                return {'available': False, 'details': "Claude availability check failed: Cannot run async check from current event loop context. This connector is async but check is sync."}
            return {'available': False, 'details': f"An unexpected error occurred: {e}"}

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
    # The old config style `connector = ClaudeConnector(config=sample_config)` is no longer valid
    # with BaseLLMConnector expecting model_name and then **kwargs.
    # Let's adjust the example.

    async def main_async_tests():
        connector = None
        try:
            # Initialize with model_name and other params as kwargs
            connector = ClaudeConnector(
                model_name="claude-3-haiku-20240307",
                api_key_env_var="ANTHROPIC_API_KEY", # This is used by __init__ to find the key
                max_tokens=150,
                default_system_prompt="You are a concise coding assistant.",
                anthropic_version_header="2023-06-01"
            )
            logger.info("ClaudeConnector (async context for other methods) created.")

            # The other methods like generate_code are async.
            # Example: Test generate_code
            # code_response = await connector.generate_code("Write a simple Python 'hello world' function.")
            # logger.info(f"Generated code: {code_response}")

        except ValueError as e: # Should be LLMConnectorError or ClaudeApiError now
            logger.error(f"Configuration error: {e}")
        except ClaudeApiError as e:
            logger.error(f"Claude API error during example: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during async example: {e}", exc_info=True)
        finally:
            if connector:
                await connector.close()

    def test_sync_check_availability():
        connector = None
        try:
            connector = ClaudeConnector(
                model_name="claude-3-haiku-20240307",
                api_key_env_var="ANTHROPIC_API_KEY",
                max_tokens=150,
                default_system_prompt="You are a concise coding assistant.",
                anthropic_version_header="2023-06-01"
            )
            logger.info("ClaudeConnector (for sync check_availability) created.")

            # Test the synchronous check_availability
            availability_status = connector.check_availability()
            logger.info(f"Claude API Availability: {availability_status['available']}, Details: {availability_status['details']}")

        except ClaudeApiError as e: # Catch init errors
            logger.error(f"Claude API error during sync example init: {e}")
            # Print availability for init failures too
            logger.info(f"Claude API Availability: False, Details: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during sync example: {e}", exc_info=True)
            logger.info(f"Claude API Availability: False, Details: An unexpected error occurred: {e}")
        # No async close needed here if only sync method was called and client wasn't used extensively in async way.
        # However, if __init__ fully initializes an async client, it should be closed.
        # This example structure is tricky due to mixed async/sync.
        # For a robust solution, the client itself would need separate sync/async versions or a sync wrapper.
        # For now, we assume the test_sync_check_availability does not require explicit close if it errors out early,
        # or that main_async_tests would handle closure if it were run.

    if os.getenv("ANTHROPIC_API_KEY"):
        logger.info("--- Running Sync check_availability test ---")
        test_sync_check_availability()

        # logger.info("\n--- Running Async operations test (commented out by default) ---")
        # asyncio.run(main_async_tests()) # Uncomment to run async parts
    else:
        logger.warning("Skipping ClaudeConnector example: ANTHROPIC_API_KEY not set.")
