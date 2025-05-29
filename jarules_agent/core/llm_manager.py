# jarules_agent/core/llm_manager.py

import yaml
import os
from typing import Optional, Dict, Any

# Assuming BaseLLMConnector and GeminiClient will be discoverable by Python's import system.
# Adjust relative paths if necessary based on final project structure.
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector
from jarules_agent.connectors.gemini_api import GeminiClient, GeminiApiKeyError # For specific error handling

# Define custom exceptions for LLMManager
class LLMManagerError(Exception):
    """Base exception for LLMManager errors."""
    pass

class LLMConfigError(LLMManagerError):
    """Raised for errors in LLM configuration."""
    pass

class LLMProviderNotImplementedError(LLMManagerError, NotImplementedError):
    """Raised when a requested LLM provider's connector is not implemented."""
    pass


class LLMManager:
    """
    Manages LLM configurations and instantiates appropriate LLM connectors.
    """
    def __init__(self, config_path: str = 'config/llm_config.yaml'):
        """
        Initializes the LLMManager by loading configurations from the specified YAML file.

        Args:
            config_path: Path to the LLM configuration YAML file.

        Raises:
            LLMConfigError: If the config file is not found, cannot be parsed, 
                            or essential global keys are missing.
        """
        self.config_path = config_path
        self._llm_configs: Dict[str, Dict[str, Any]] = {}
        self._loaded_connectors: Dict[str, BaseLLMConnector] = {} # Cache for loaded connectors

        try:
            if not os.path.exists(self.config_path):
                raise LLMConfigError(f"LLM configuration file not found at: {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                full_config = yaml.safe_load(f)
            
            if not full_config or 'llm_configs' not in full_config:
                raise LLMConfigError(f"Invalid LLM configuration: 'llm_configs' key missing in {self.config_path}")

            for conf in full_config['llm_configs']:
                if not isinstance(conf, dict) or 'id' not in conf or 'provider' not in conf:
                    raise LLMConfigError(f"Invalid LLM entry in {self.config_path}: missing 'id' or 'provider'. Entry: {conf}")
                if not conf.get('enabled', False): # Skip disabled configurations
                    print(f"LLMManager: Skipping disabled configuration with id '{conf['id']}'.")
                    continue
                self._llm_configs[conf['id']] = conf
            
            if not self._llm_configs:
                print(f"LLMManager: Warning - No enabled LLM configurations found in {self.config_path}.")

        except yaml.YAMLError as e:
            raise LLMConfigError(f"Error parsing LLM configuration file {self.config_path}: {e}") from e
        except LLMConfigError: # Re-raise our specific config errors
            raise
        except Exception as e: # Catch other unexpected errors during init
            raise LLMManagerError(f"An unexpected error occurred during LLMManager initialization: {e}") from e

    def get_available_configs(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dictionary of all enabled LLM configurations."""
        return self._llm_configs.copy()

    def get_llm_connector(self, config_id: str) -> Optional[BaseLLMConnector]:
        """
        Retrieves an initialized LLM connector based on its configuration ID.
        Connectors are cached after first instantiation for a given config_id.

        Args:
            config_id: The unique ID of the LLM configuration to use.

        Returns:
            An instance of a BaseLLMConnector subclass, or None/raises error if issues.

        Raises:
            LLMConfigError: If the config_id is not found or config is invalid.
            LLMProviderNotImplementedError: If the provider's connector is not implemented.
            GeminiApiKeyError: (Or other connector-specific API key errors) if critical setup like API key is missing.
            LLMManagerError: For other manager-related issues.
        """
        if config_id in self._loaded_connectors:
            return self._loaded_connectors[config_id]

        if config_id not in self._llm_configs:
            raise LLMConfigError(f"LLM configuration with id '{config_id}' not found or not enabled.")

        config = self._llm_configs[config_id]
        provider = config.get('provider', '').lower()
        model_name = config.get('model_name')
        api_key_env_var = config.get('api_key_env')
        api_key = None

        if api_key_env_var:
            api_key = os.environ.get(api_key_env_var)
            if not api_key:
                # This is a critical error if the config specified an API key env var but it's not set.
                # Specific connectors (like GeminiClient) might also raise their own API key errors.
                # Depending on design, we can let the connector handle it or raise here.
                # Let's make it explicit here for Gemini, as an example.
                if provider == "gemini": # Or rely on GeminiClient to raise GeminiApiKeyError
                     raise GeminiApiKeyError(f"Environment variable '{api_key_env_var}' for Gemini API key not set for config '{config_id}'.")
                print(f"LLMManager: Warning - Environment variable '{api_key_env_var}' not set for config '{config_id}'. Connector might fail.")


        # Extract other relevant parameters from config to pass to the client constructor
        # These names should align with what the client constructors expect.
        client_kwargs = {
            "model_name": model_name,
            "api_key": api_key, # Pass the fetched API key directly
            # Pass through other params that might be in config and relevant for the client
            "default_system_prompt": config.get("default_system_prompt"),
            "generation_params": config.get("generation_params"),
            "base_url": config.get("base_url") # For Ollama, etc.
        }
        # Filter out None values, so client constructors can use their own defaults if a param is not in config
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}


        connector: Optional[BaseLLMConnector] = None

        if provider == 'gemini':
            try:
                # Pass only relevant kwargs that GeminiClient's __init__ expects
                # GeminiClient might need specific handling for api_key (e.g., if it also checks env var itself)
                # The plan is to adapt GeminiClient to accept these params.
                connector = GeminiClient(**client_kwargs)
            except GeminiApiKeyError: # Re-raise specific API key error if client raises it
                raise
            except Exception as e: # Catch other potential errors from GeminiClient init
                raise LLMManagerError(f"Failed to initialize GeminiClient for config '{config_id}': {e}") from e
        
        # --- Future Provider Implementations ---
        # elif provider == 'ollama':
        #     # from ..connectors.ollama_client import OllamaClient # Example
        #     # connector = OllamaClient(**client_kwargs)
        #     raise LLMProviderNotImplementedError(f"Connector for LLM provider '{provider}' (config_id: '{config_id}') is not yet implemented.")
        # elif provider == 'openrouter':
        #     # from ..connectors.openrouter_client import OpenRouterClient # Example
        #     # connector = OpenRouterClient(**client_kwargs)
        #     raise LLMProviderNotImplementedError(f"Connector for LLM provider '{provider}' (config_id: '{config_id}') is not yet implemented.")
        
        else:
            raise LLMProviderNotImplementedError(f"LLM provider '{provider}' (config_id: '{config_id}') is not supported or connector not implemented.")

        if connector:
            self._loaded_connectors[config_id] = connector # Cache the instance
        return connector

```
