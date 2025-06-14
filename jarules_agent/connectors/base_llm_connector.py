# jarules_agent/connectors/base_llm_connector.py

from abc import ABC, abstractmethod
from typing import Optional, Any

class LLMConnectorError(Exception):
    """Base exception for all LLM connector errors."""
    def __init__(self, message: str, underlying_exception: Optional[Exception] = None):
        super().__init__(message)
        self.underlying_exception = underlying_exception

class BaseLLMConnector(ABC):
    """
    Abstract Base Class for Large Language Model connectors.
    Defines a common interface for interacting with different LLMs.
    """

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any):
        """
        Initializes the LLM connector.

        Args:
            model_name: Optional. The specific model name to use with the LLM provider.
            **kwargs: Additional keyword arguments for connector-specific configuration.
        """
        self.model_name = model_name
        # Allow subclasses to use additional configuration via kwargs
        # For example, api_key, base_url, etc.
        self._config = kwargs
        super().__init__()

    @abstractmethod
    def generate_code(self, user_prompt: str, system_instruction: Optional[str] = None, history: Optional[list[dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        """
        Generates code based on a user prompt and optional system instructions.

        Args:
            user_prompt: The user's direct request for code generation.
            system_instruction: Optional. Guiding instruction for the model's behavior or output format.
            history: Optional. A list of dictionaries representing the conversation history.
            **kwargs: Additional provider-specific parameters for generation.

        Returns:
            The generated code as a string, or None if generation fails or is blocked.
        
        Raises:
            LLMConnectorError: If an error occurs during code generation.
        """
        pass

    @abstractmethod
    def check_availability(self) -> dict:
        """
        Checks the availability and status of the LLM service.

        Returns:
            A dictionary with keys like `available: bool` (boolean indicating if the service is usable)
            and `details: str` (a message describing the status or any issues).

        Raises:
            LLMConnectorError: If an error occurs during the availability check.
        """
        pass

    @abstractmethod
    def explain_code(self, code_snippet: str, system_instruction: Optional[str] = None, history: Optional[list[dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        """
        Explains a given code snippet.

        Args:
            code_snippet: The string containing the code to be explained.
            system_instruction: Optional. Guiding instruction for the model's explanation.
            history: Optional. A list of dictionaries representing the conversation history.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated explanation as a string, or None if generation fails or is blocked.

        Raises:
            LLMConnectorError: If an error occurs during code explanation.
        """
        pass

    @abstractmethod
    def suggest_code_modification(self, code_snippet: str, issue_description: str, system_instruction: Optional[str] = None, history: Optional[list[dict[str, str]]] = None, **kwargs: Any) -> Optional[str]:
        """
        Suggests modifications to a given code snippet based on an issue description.

        Args:
            code_snippet: The string containing the code to be modified.
            issue_description: A natural language description of the desired modification or fix.
            system_instruction: Optional. Guiding instruction for the model.
            history: Optional. A list of dictionaries representing the conversation history.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The suggested modified code as a string, or None if generation fails/is blocked.

        Raises:
            LLMConnectorError: If an error occurs during code modification suggestion.
        """
        pass

    # It might be useful to have a more generic text generation method in the future,
    # but for now, the three specific methods align with current functionality.
    # @abstractmethod
    # def generate_text(self, prompt: str, **kwargs: Any) -> str:
    #     pass
