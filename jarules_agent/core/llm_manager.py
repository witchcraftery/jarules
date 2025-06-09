# jarules_agent/core/llm_manager.py

import yaml
import os
from typing import Optional, Dict, Any

# Assuming BaseLLMConnector and GeminiClient will be discoverable by Python's import system.
# Adjust relative paths if necessary based on final project structure.
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector
from jarules_agent.connectors.gemini_api import GeminiClient, GeminiApiKeyError
from jarules_agent.connectors.ollama_connector import OllamaConnector, OllamaApiError
from jarules_agent.connectors.openrouter_connector import OpenRouterConnector, OpenRouterApiError
from jarules_agent.connectors.claude_connector import ClaudeConnector, ClaudeApiError

import logging
import json # For user_state.json
from pathlib import Path # For user_state.json path

logger = logging.getLogger(__name__)

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
        self._loaded_connectors: Dict[str, BaseLLMConnector] = {}
        self.active_provider_id: Optional[str] = None
        self.user_state_file_path = Path.home() / ".jarules" / "user_state.json"
        self._default_provider_from_config: Optional[str] = None # Store the default from config

        # Mapping of provider names to connector classes
        self.connector_map = {
            "gemini": GeminiClient,
            "ollama": OllamaConnector,
            "openrouter": OpenRouterConnector,
            "claude": ClaudeConnector,
        }

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
                logger.warning(f"LLMManager: No enabled LLM configurations found in {self.config_path}.")

            # Set active_provider_id from default_provider in config
            default_provider_id = full_config.get('default_provider')

            # Determine default provider from config first
            default_provider_from_config = full_config.get('default_provider')
            if default_provider_from_config and default_provider_from_config in self._llm_configs:
                self._default_provider_from_config = default_provider_from_config
                logger.info(f"LLMManager: Default provider from config identified as '{self._default_provider_from_config}'.")
            elif default_provider_from_config:
                logger.warning(
                    f"LLMManager: Default provider ID '{default_provider_from_config}' from config is not found "
                    f"among enabled configurations or is invalid."
                )

            # Attempt to load active_provider_id from user_state.json
            persisted_active_id = self._load_user_state()

            if persisted_active_id and persisted_active_id in self._llm_configs:
                self.active_provider_id = persisted_active_id
                logger.info(f"LLMManager: Activated provider '{self.active_provider_id}' from user state.")
            elif persisted_active_id:
                logger.warning(
                    f"LLMManager: Persisted active provider ID '{persisted_active_id}' is no longer valid "
                    f"(not in enabled configurations). Falling back."
                )
                # If persisted is invalid, try to use config default
                if self._default_provider_from_config:
                    self.active_provider_id = self._default_provider_from_config
                    logger.info(f"LLMManager: Using default provider '{self.active_provider_id}' from config as fallback.")
                    self._save_user_state(self.active_provider_id) # Optionally, clean up invalid persisted state or save the fallback
                else:
                    logger.info("LLMManager: No valid persisted or default provider. Active provider not set.")
                    self._save_user_state(None) # Clear invalid persisted state
            elif self._default_provider_from_config:
                self.active_provider_id = self._default_provider_from_config
                logger.info(f"LLMManager: No user state found. Activated default provider '{self.active_provider_id}' from config.")
                # No need to save user state here, as it's the default behavior without user interaction
            else:
                logger.info("LLMManager: No user state and no default provider in config. Active provider not set initially.")

        except yaml.YAMLError as e:
            raise LLMConfigError(f"Error parsing LLM configuration file {self.config_path}: {e}") from e
        except LLMConfigError: # Re-raise our specific config errors
            raise
        except Exception as e: # Catch other unexpected errors during init
            raise LLMManagerError(f"An unexpected error occurred during LLMManager initialization: {e}") from e

    def get_available_configs(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dictionary of all enabled LLM configurations."""
        return self._llm_configs.copy()

    def set_active_provider(self, provider_id: str):
        """
        Sets the active LLM provider.

        Args:
            provider_id: The ID of the LLM configuration to set as active.

        Raises:
            ValueError: If the provider_id is not found in the loaded configurations.
        """
        if provider_id not in self._llm_configs:
            raise ValueError(f"Provider ID '{provider_id}' not found in loaded configurations or is not enabled.")
        self.active_provider_id = provider_id
        logger.info(f"LLMManager: Active provider set to '{provider_id}'.")
        self._save_user_state(provider_id)

    def _load_user_state(self) -> Optional[str]:
        """Loads the active_provider_id from the user state JSON file."""
        if self.user_state_file_path.is_file():
            try:
                with open(self.user_state_file_path, 'r') as f:
                    state_data = json.load(f)
                loaded_id = state_data.get("active_provider_id")
                if loaded_id:
                    logger.debug(f"Loaded active_provider_id '{loaded_id}' from user state.")
                    return loaded_id
                else:
                    logger.debug("User state file exists but no active_provider_id found or it's null.")
                    return None
            except json.JSONDecodeError:
                logger.warning(f"Error decoding user state file: {self.user_state_file_path}. Ignoring.")
                return None
            except IOError as e:
                logger.warning(f"Could not read user state file {self.user_state_file_path}: {e}. Ignoring.")
                return None
        logger.debug(f"User state file not found at: {self.user_state_file_path}")
        return None

    def _save_user_state(self, provider_id: Optional[str]):
        """Saves the active_provider_id to the user state JSON file."""
        try:
            self.user_state_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.user_state_file_path, 'w') as f:
                json.dump({"active_provider_id": provider_id}, f, indent=2)
            logger.debug(f"Saved active_provider_id '{provider_id}' to user state.")
        except IOError as e:
            logger.error(f"Could not write user state file {self.user_state_file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving user state: {e}", exc_info=True)

    def clear_active_provider_state(self):
        """
        Clears the persisted active provider state and resets the active provider
        to the default from the configuration file (if any).
        """
        logger.info("Clearing active provider state.")
        self._save_user_state(None) # Remove or nullify persisted state

        # Reset active_provider_id to config default
        if self._default_provider_from_config:
            self.active_provider_id = self._default_provider_from_config
            logger.info(f"Active provider reset to config default: '{self.active_provider_id}'.")
        else:
            self.active_provider_id = None
            logger.info("Active provider cleared. No default provider in config to fall back to.")


    def get_llm_client(self, provider_id: Optional[str] = None) -> BaseLLMConnector:
        """
        Retrieves an initialized LLM client (connector).
        If provider_id is None, uses the active_provider_id.
        Connectors are cached after first instantiation.

        Args:
            provider_id: The unique ID of the LLM configuration to use.
                         If None, uses the active provider.

        Returns:
            An instance of a BaseLLMConnector subclass.

        Raises:
            LLMConfigError: If the config_id is not found or config is invalid.
            LLMProviderNotImplementedError: If the provider's connector is not implemented.
            GeminiApiKeyError: (Or other connector-specific API key errors) if critical setup like API key is missing.
            LLMConfigError: If the config_id is not found or config is invalid.
            LLMProviderNotImplementedError: If the provider's connector is not implemented.
            LLMManagerError: For other manager-related issues, including no active provider set.
        """
        target_provider_id = provider_id if provider_id is not None else self.active_provider_id

        if target_provider_id is None:
            raise LLMManagerError(
                "No provider ID specified and no active provider is set. "
                "Use 'set-model <provider_id>' or configure a default_provider."
            )

        if target_provider_id in self._loaded_connectors:
            return self._loaded_connectors[target_provider_id]

        if target_provider_id not in self._llm_configs:
            # This could happen if active_provider_id was somehow set to an invalid/disabled ID
            # or if a specified provider_id is invalid.
            raise LLMConfigError(f"LLM configuration with id '{target_provider_id}' not found or not enabled.")

        config_details = self._llm_configs[target_provider_id]
        provider_name = config_details.get('provider', '').lower()

        if not provider_name:
            raise LLMConfigError(f"Provider name not specified in configuration for ID '{target_provider_id}'.")

        connector_class = self.connector_map.get(provider_name)
        if not connector_class:
            raise LLMProviderNotImplementedError(
                f"Connector for LLM provider '{provider_name}' (config_id: '{target_provider_id}') is not implemented or not mapped in LLMManager."
            )

        connector: BaseLLMConnector
        try:
            # Each connector's __init__ should handle extracting necessary fields from its config dict
            # and manage API key loading from environment variables internally based on config.
            connector = connector_class(config=config_details)
        except (GeminiApiKeyError, OllamaApiError, OpenRouterApiError, ClaudeApiError) as e: # Catch specific connector init errors
            # These errors (like missing API key) are critical.
            logger.error(f"API key or critical configuration error for {provider_name} ('{target_provider_id}'): {e}")
            raise LLMConfigError(f"Failed to initialize connector for '{target_provider_id}' due to critical config/key error: {e}") from e
        except ValueError as e: # Catch other ValueErrors from connector __init__ (e.g. API key not found)
            logger.error(f"Configuration value error for {provider_name} ('{target_provider_id}'): {e}")
            raise LLMConfigError(f"Failed to initialize connector for '{target_provider_id}' due to configuration value error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error initializing connector for {provider_name} ('{target_provider_id}'): {e}", exc_info=True)
            raise LLMManagerError(f"Unexpected error initializing connector for '{target_provider_id}': {e}") from e

        self._loaded_connectors[target_provider_id] = connector
        return connector
