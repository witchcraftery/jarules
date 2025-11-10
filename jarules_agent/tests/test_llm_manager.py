# jarules_agent/tests/test_llm_manager.py

import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import yaml
import json
from pathlib import Path

import logging # For suppressing logger output during tests if needed

# Adjust imports based on actual project structure
from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError, LLMManagerError
from jarules_agent.connectors.gemini_api import GeminiClient, GeminiApiKeyError
from jarules_agent.connectors.ollama_connector import OllamaConnector # Import other connectors
from jarules_agent.connectors.openrouter_connector import OpenRouterConnector
from jarules_agent.connectors.claude_connector import ClaudeConnector
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

# Suppress logging output for tests unless specifically testing log messages
# logging.disable(logging.CRITICAL)


class TestLLMManager(unittest.TestCase):

    def _create_mock_config_content(self, configs_list, default_provider=None):
        content = {"llm_configs": configs_list}
        if default_provider:
            content["default_provider"] = default_provider
        return yaml.dump(content)

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_init_success_and_get_available_configs(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        sample_configs = [
            {"id": "gemini_test", "provider": "gemini", "enabled": True, "model_name": "test-model", "api_key_env": "TEST_GEMINI_KEY"},
            {"id": "ollama_disabled", "provider": "ollama", "enabled": False, "model_name": "test-ollama"}
        ]
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(sample_configs)).return_value

        manager = LLMManager(config_path="dummy_path.yaml")
        available = manager.get_available_configs()
        
        self.assertIn("gemini_test", available)
        self.assertNotIn("ollama_disabled", available) # Should be skipped as enabled=false
        self.assertEqual(available["gemini_test"]["model_name"], "test-model")
        self.assertIsNotNone(manager.connector_map) # Test connector_map initialization

    @patch('os.path.exists', return_value=False)
    def test_init_config_file_not_found(self, mock_path_exists):
        with self.assertRaisesRegex(LLMConfigError, "LLM configuration file not found"):
            LLMManager(config_path="nonexistent.yaml")

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', side_effect=yaml.YAMLError("YAML parse error"))
    def test_init_yaml_parse_error(self, mock_file_open, mock_path_exists):
        with self.assertRaisesRegex(LLMConfigError, "Error parsing LLM configuration file"):
            LLMManager(config_path="bad_yaml.yaml")

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_init_invalid_config_format_no_llm_configs_key(self, mock_file_open, mock_path_exists):
        mock_file_open.return_value = mock_open(read_data=yaml.dump({"some_other_key": []})).return_value
        with self.assertRaisesRegex(LLMConfigError, "Invalid LLM configuration: 'llm_configs' key missing"):
            LLMManager(config_path="dummy.yaml")

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_init_invalid_config_entry_missing_id(self, mock_file_open, mock_path_exists):
        sample_configs = [{"provider": "gemini", "enabled": True}] # Missing 'id'
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(sample_configs)).return_value
        with self.assertRaisesRegex(LLMConfigError, "Invalid LLM entry.*missing 'id' or 'provider'"):
            LLMManager(config_path="dummy.yaml")
            
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open')
    @patch('jarules_agent.core.llm_manager.logger') # Patch logger
    def test_init_no_enabled_configs_warning(self, mock_logger, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        sample_configs = [{"id": "gemini_disabled", "provider": "gemini", "enabled": False}]
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(sample_configs)).return_value
        manager = LLMManager(config_path="dummy.yaml")
        self.assertEqual(len(manager.get_available_configs()), 0)
        mock_logger.warning.assert_any_call("LLMManager: No enabled LLM configurations found in dummy.yaml.")

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_default_provider_set(self, mock_logger, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        configs = [{"id": "default_gem", "provider": "gemini", "enabled": True, "model_name": "gem-def"}]
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(configs, default_provider="default_gem")).return_value
        manager = LLMManager("dummy.yaml")
        self.assertEqual(manager.active_provider_id, "default_gem")
        mock_logger.info.assert_any_call("LLMManager: Default provider 'default_gem' set as active provider.")

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_default_provider_invalid_or_disabled(self, mock_logger, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        configs = [{"id": "gem1", "provider": "gemini", "enabled": True, "model_name": "gem-1"}]
        # Case 1: default_provider ID does not exist in enabled configs
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(configs, default_provider="non_existent_default")).return_value
        manager = LLMManager("dummy.yaml")
        self.assertIsNone(manager.active_provider_id)
        mock_logger.warning.assert_any_call(
            "LLMManager: Default provider ID 'non_existent_default' from config is not found "
            "among enabled configurations or is invalid. No active provider set by default."
        )
        # Case 2: default_provider exists but is disabled
        configs_with_disabled_default = [
            {"id": "default_disabled", "provider": "gemini", "enabled": False, "model_name": "gem-dis"},
            {"id": "gem_enabled", "provider": "gemini", "enabled": True, "model_name": "gem-ena"}
        ]
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(configs_with_disabled_default, default_provider="default_disabled")).return_value
        manager2 = LLMManager("dummy2.yaml")
        self.assertIsNone(manager2.active_provider_id)
        mock_logger.warning.assert_any_call(
            "LLMManager: Default provider ID 'default_disabled' from config is not found "
            "among enabled configurations or is invalid. No active provider set by default."
        )

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_no_default_provider(self, mock_logger, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        configs = [{"id": "gem1", "provider": "gemini", "enabled": True, "model_name": "gem-1"}]
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(configs, default_provider=None)).return_value
        manager = LLMManager("dummy.yaml")
        self.assertIsNone(manager.active_provider_id)
        mock_logger.info.assert_any_call("LLMManager: No default_provider specified in config. Active provider not set initially.")


    @patch.dict(os.environ, {"TEST_GEMINI_KEY_VALID": "actual_key"})
    @patch('jarules_agent.core.llm_manager.GeminiClient')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_client_gemini_success(self, mock_file_open, mock_path_exists, MockGeminiClientClass):
        mock_path_exists.return_value = True
        gemini_config = {
            "id": "gemini_test_conn", "provider": "gemini", "enabled": True, 
            "model_name": "gemini-flash", "api_key_env": "TEST_GEMINI_KEY_VALID",
            "default_system_prompt": "Test prompt",
            "generation_params": {"temperature": 0.8}
        }
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([gemini_config])).return_value
        
        mock_gemini_instance = MagicMock(spec=GeminiClient)
        MockGeminiClientClass.return_value = mock_gemini_instance
        
        manager = LLMManager(config_path="dummy.yaml")
        client = manager.get_llm_client("gemini_test_conn")

        self.assertIs(client, mock_gemini_instance)
        # Now, connector class is called with the raw config dictionary
        MockGeminiClientClass.assert_called_once_with(config=gemini_config)
        
        # Test caching
        client2 = manager.get_llm_client("gemini_test_conn")
        self.assertIs(client2, mock_gemini_instance)
        MockGeminiClientClass.assert_called_once() # Should not be called again

    @patch.dict(os.environ, {"TEST_OLLAMA_NO_KEY": "any_value_doesnt_matter"}) # Ollama doesn't need API key typically
    @patch('jarules_agent.core.llm_manager.OllamaConnector')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_client_ollama_success(self, mock_file_open, mock_path_exists, MockOllamaConnectorClass):
        mock_path_exists.return_value = True
        ollama_config = {
            "id": "ollama_test_conn", "provider": "ollama", "enabled": True,
            "model_name": "llama3", "base_url": "http://localhost:11434"
        }
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([ollama_config])).return_value

        mock_ollama_instance = MagicMock(spec=OllamaConnector)
        MockOllamaConnectorClass.return_value = mock_ollama_instance

        manager = LLMManager(config_path="dummy.yaml")
        client = manager.get_llm_client("ollama_test_conn")

        self.assertIs(client, mock_ollama_instance)
        MockOllamaConnectorClass.assert_called_once_with(config=ollama_config)


    @patch.dict(os.environ, clear=True)
    @patch('jarules_agent.core.llm_manager.GeminiClient') # Still need to patch to avoid its direct os.environ access
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_client_gemini_api_key_missing_value_error(self, mock_file_open, mock_path_exists, MockGeminiClientClass):
        mock_path_exists.return_value = True
        gemini_config = {
            "id": "gemini_key_missing", "provider": "gemini", "enabled": True,
            "model_name": "gemini-flash", "api_key_env_var": "TEST_GEMINI_KEY_MISSING_IN_ENV" # Changed to api_key_env_var
        }
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([gemini_config])).return_value

        # Mock GeminiClient's __init__ to raise ValueError if api_key is effectively missing
        MockGeminiClientClass.side_effect = ValueError("API key not found in environment for Gemini.")
        
        manager = LLMManager(config_path="dummy.yaml")
        with self.assertRaisesRegex(LLMConfigError, "Failed to initialize connector for 'gemini_key_missing' due to configuration value error: API key not found in environment for Gemini."):
            manager.get_llm_client("gemini_key_missing")

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_client_not_implemented_provider(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        unknown_provider_config = {"id": "unknown_prov", "provider": "future-ai", "enabled": True, "model_name": "super-model"}
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([unknown_provider_config])).return_value

        manager = LLMManager(config_path="dummy.yaml")
        with self.assertRaisesRegex(LLMProviderNotImplementedError, "Connector for LLM provider 'future-ai'.*is not implemented or not mapped"):
            manager.get_llm_client("unknown_prov")

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_client_config_id_not_found(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([])).return_value # Empty config list
        manager = LLMManager(config_path="dummy.yaml")
        with self.assertRaisesRegex(LLMConfigError, "LLM configuration with id 'non_existent_id' not found or not enabled."):
            manager.get_llm_client("non_existent_id")

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('jarules_agent.core.llm_manager.logger')
    @patch.object(Path, 'is_file') # Mock Path.is_file
    @patch.object(Path, 'mkdir') # Mock Path.mkdir
    def test_set_active_provider_success_and_get_active_saves_state(
        self, mock_mkdir, mock_is_file, mock_logger, mock_file_open_global, mock_os_exists
    ):
        mock_os_exists.return_value = True # For llm_config.yaml
        mock_is_file.return_value = False # No initial user_state.json

        configs = [
            {"id": "gem1", "provider": "gemini", "enabled": True, "model_name": "g1"},
            {"id": "ollama1", "provider": "ollama", "enabled": True, "model_name": "o1"}
        ]
        mock_config_data = self._create_mock_config_content(configs)

        # Mock open for llm_config.yaml and then for user_state.json write
        mock_open_llm_config = mock_open(read_data=mock_config_data)
        mock_open_user_state_write = mock_open()

        # Use a list of side_effects for multiple open calls
        mock_file_open_global.side_effect = [
            mock_open_llm_config.return_value, # First call for llm_config.yaml
            mock_open_user_state_write.return_value # Second call for writing user_state.json
        ]

        manager = LLMManager("dummy.yaml")
        self.assertIsNone(manager.active_provider_id)

        manager.set_active_provider("ollama1")
        self.assertEqual(manager.active_provider_id, "ollama1")
        mock_logger.info.assert_any_call("LLMManager: Active provider set to 'ollama1'.")

        # Check that _save_user_state was effectively called (mkdir and write)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_open_user_state_write.assert_called_once_with(manager.user_state_file_path, 'w')
        handle = mock_open_user_state_write()
        # Verify json.dump was called with the correct data
        # json.dump(obj, fp, indent=2) -> first arg is obj
        args, _ = handle.write.call_args_list[0] # json.dump calls write
        written_data = json.loads(args[0]) # This is fragile, depends on how json.dump formats
                                           # A better way might be to mock json.dump directly
        self.assertEqual(written_data, {"active_provider_id": "ollama1"})


        # Mock the OllamaConnector for the get_llm_client call
        with patch.object(manager, 'connector_map', {"ollama": OllamaConnector}): # Ensure map is correct for this test
             with patch('jarules_agent.core.llm_manager.OllamaConnector') as MockOllama:
                mock_ollama_instance = MagicMock(spec=OllamaConnector)
                MockOllama.return_value = mock_ollama_instance

                active_client = manager.get_llm_client()
                self.assertIs(active_client, mock_ollama_instance)
                MockOllama.assert_called_once_with(config=configs[1])

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_set_active_provider_invalid_id(self, mock_file_open_global, mock_os_exists):
        mock_os_exists.return_value = True
        mock_file_open_global.return_value = mock_open(read_data=self._create_mock_config_content([])).return_value
        manager = LLMManager("dummy.yaml")
        with self.assertRaisesRegex(ValueError, "Provider ID 'invalid_id' not found in loaded configurations or is not enabled."):
            manager.set_active_provider("invalid_id")

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch.object(Path, 'is_file', return_value=False) # No user state file
    def test_get_llm_client_no_active_provider_error(self, mock_is_file, mock_file_open_global, mock_os_exists):
        mock_os_exists.return_value = True
        # Config has no default_provider, and active_provider_id is not set (no user state)
        mock_file_open_global.return_value = mock_open(read_data=self._create_mock_config_content([])).return_value
        manager = LLMManager("dummy.yaml")
        self.assertIsNone(manager.active_provider_id)
        with self.assertRaisesRegex(LLMManagerError, "No provider ID specified and no active provider is set."):
            manager.get_llm_client() # No args, no active provider

    # --- Tests for persistence ---
    @patch('os.path.exists') # For llm_config.yaml
    @patch('builtins.open') # For llm_config.yaml and user_state.json
    @patch.object(Path, 'is_file')
    @patch.object(Path, 'mkdir')
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_loads_from_user_state_valid(self, mock_logger, mock_mkdir, mock_is_file, mock_file_open_global, mock_os_exists):
        mock_os_exists.return_value = True # llm_config.yaml exists
        mock_is_file.return_value = True # user_state.json exists

        configs = [{"id": "persisted_gem", "provider": "gemini", "enabled": True, "model_name": "gem-persisted"}]
        mock_config_data = self._create_mock_config_content(configs, default_provider="another_default") # A different default

        user_state_data = json.dumps({"active_provider_id": "persisted_gem"})

        # Mock open for llm_config.yaml then for user_state.json read
        mock_open_llm_config = mock_open(read_data=mock_config_data)
        mock_open_user_state_read = mock_open(read_data=user_state_data)
        mock_file_open_global.side_effect = [mock_open_llm_config.return_value, mock_open_user_state_read.return_value]

        manager = LLMManager("dummy.yaml")
        self.assertEqual(manager.active_provider_id, "persisted_gem")
        mock_logger.info.assert_any_call("LLMManager: Activated provider 'persisted_gem' from user state.")
        mock_open_user_state_read.assert_called_once_with(manager.user_state_file_path, 'r')

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch.object(Path, 'is_file')
    @patch.object(Path, 'mkdir') # For _save_user_state if fallback occurs
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_user_state_invalid_id_falls_back_to_config_default(self, mock_logger, mock_mkdir, mock_is_file, mock_file_open_global, mock_os_exists):
        mock_os_exists.return_value = True
        mock_is_file.return_value = True # user_state.json exists

        configs = [{"id": "config_default_gem", "provider": "gemini", "enabled": True, "model_name": "gem-cfg-def"}]
        mock_config_data = self._create_mock_config_content(configs, default_provider="config_default_gem")

        user_state_data = json.dumps({"active_provider_id": "invalid_persisted_id"}) # This ID is not in configs

        mock_open_llm_config = mock_open(read_data=mock_config_data)
        mock_open_user_state_read = mock_open(read_data=user_state_data)
        mock_open_user_state_write = mock_open() # For saving the fallback

        mock_file_open_global.side_effect = [
            mock_open_llm_config.return_value, # llm_config read
            mock_open_user_state_read.return_value, # user_state read
            mock_open_user_state_write.return_value # user_state write (for fallback)
        ]

        manager = LLMManager("dummy.yaml")
        self.assertEqual(manager.active_provider_id, "config_default_gem")
        mock_logger.warning.assert_any_call("LLMManager: Persisted active provider ID 'invalid_persisted_id' is no longer valid (not in enabled configurations). Falling back.")
        mock_logger.info.assert_any_call("LLMManager: Using default provider 'config_default_gem' from config as fallback.")
        # Check that the fallback was saved
        mock_open_user_state_write.assert_called_once_with(manager.user_state_file_path, 'w')


    @patch('os.path.exists')
    @patch('builtins.open')
    @patch.object(Path, 'is_file', return_value=True) # user_state.json exists
    @patch.object(Path, 'mkdir')
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_user_state_corrupted_json(self, mock_logger, mock_mkdir, mock_is_file, mock_file_open_global, mock_os_exists):
        mock_os_exists.return_value = True
        configs = [{"id": "cfg_default", "provider": "gemini", "enabled": True, "model_name": "cfg"}]
        mock_config_data = self._create_mock_config_content(configs, default_provider="cfg_default")

        corrupted_user_state_data = "this is not json"

        mock_open_llm_config = mock_open(read_data=mock_config_data)
        mock_open_user_state_read = mock_open(read_data=corrupted_user_state_data)
        # No write expected if only fallback to config default without saving immediately unless persisted was invalid

        mock_file_open_global.side_effect = [mock_open_llm_config.return_value, mock_open_user_state_read.return_value]

        manager = LLMManager("dummy.yaml")
        self.assertEqual(manager.active_provider_id, "cfg_default") # Falls back to config default
        mock_logger.warning.assert_any_call(f"Error decoding user state file: {manager.user_state_file_path}. Ignoring.")
        mock_logger.info.assert_any_call("LLMManager: No user state found. Activated default provider 'cfg_default' from config.")


    @patch.object(Path, 'is_file', return_value=False) # No user_state.json
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('jarules_agent.core.llm_manager.logger')
    def test_init_no_user_state_uses_config_default(self, mock_logger, mock_file_open_global, mock_os_exists, mock_is_file):
        mock_os_exists.return_value = True
        configs = [{"id": "cfg_def", "provider": "gemini", "enabled": True, "model_name": "cfg-def"}]
        mock_config_data = self._create_mock_config_content(configs, default_provider="cfg_def")
        mock_file_open_global.return_value = mock_open(read_data=mock_config_data).return_value

        manager = LLMManager("dummy.yaml")
        self.assertEqual(manager.active_provider_id, "cfg_def")
        mock_logger.info.assert_any_call("LLMManager: No user state found. Activated default provider 'cfg_def' from config.")
        mock_is_file.assert_called_once() # Check that it tried to load user state

    @patch.object(Path, 'is_file', return_value=False) # Start with no user state file
    @patch.object(Path, 'mkdir')
    @patch('builtins.open') # Mock open for both llm_config and user_state write
    @patch('os.path.exists', return_value=True)
    @patch('jarules_agent.core.llm_manager.logger')
    def test_clear_active_provider_state(self, mock_logger, mock_os_exists, mock_file_open_global, mock_mkdir, mock_is_file):
        configs = [{"id": "default_model", "provider": "gemini", "enabled": True, "model_name": "gem-def"}]
        mock_config_data = self._create_mock_config_content(configs, default_provider="default_model")

        # First open is for llm_config.yaml
        mock_open_llm_config = mock_open(read_data=mock_config_data)
        # Second open is for _save_user_state(None)
        mock_open_user_state_write = mock_open()
        mock_file_open_global.side_effect = [mock_open_llm_config.return_value, mock_open_user_state_write.return_value]

        manager = LLMManager("dummy.yaml")
        # Initially, active_provider_id should be the default from config
        self.assertEqual(manager.active_provider_id, "default_model")

        # Now, let's assume a different model was set and saved previously
        # For this test, we directly set it and then clear
        manager.active_provider_id = "some_other_model" # Simulate it was set

        manager.clear_active_provider_state()

        self.assertEqual(manager.active_provider_id, "default_model") # Reverted to config default
        mock_logger.info.assert_any_call("Clearing active provider state.")
        mock_logger.info.assert_any_call("Active provider reset to config default: 'default_model'.")

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True) # From _save_user_state
        handle = mock_open_user_state_write()
        args, _ = handle.write.call_args_list[0]
        written_data = json.loads(args[0])
        self.assertIsNone(written_data["active_provider_id"]) # Ensure None was saved


if __name__ == '__main__':
    unittest.main()
