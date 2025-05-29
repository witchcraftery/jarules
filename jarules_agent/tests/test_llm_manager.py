# jarules_agent/tests/test_llm_manager.py

import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import yaml

# Adjust imports based on actual project structure
from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError
from jarules_agent.connectors.gemini_api import GeminiClient, GeminiApiKeyError
from jarules_agent.connectors.base_llm_connector import BaseLLMConnector

class TestLLMManager(unittest.TestCase):

    def _create_mock_config_content(self, configs_list):
        return yaml.dump({"llm_configs": configs_list})

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
    def test_init_no_enabled_configs_warning(self, mock_file_open, mock_path_exists):
        sample_configs = [{"id": "gemini_disabled", "provider": "gemini", "enabled": False}]
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content(sample_configs)).return_value
        with patch('builtins.print') as mock_print: # To capture warning
            manager = LLMManager(config_path="dummy.yaml")
            self.assertEqual(len(manager.get_available_configs()), 0)
            mock_print.assert_any_call("LLMManager: Warning - No enabled LLM configurations found in dummy.yaml.")


    @patch.dict(os.environ, {"TEST_GEMINI_KEY_VALID": "actual_key"})
    @patch('jarules_agent.core.llm_manager.GeminiClient') # Patch where GeminiClient is looked up by LLMManager
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_connector_gemini_success(self, mock_file_open, mock_path_exists, MockGeminiClientClass, mock_env):
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
        connector = manager.get_llm_connector("gemini_test_conn")

        self.assertIs(connector, mock_gemini_instance)
        MockGeminiClientClass.assert_called_once_with(
            model_name="gemini-flash",
            api_key="actual_key",
            default_system_prompt="Test prompt",
            generation_params={"temperature": 0.8},
            base_url=None # As it's not in config
        )
        
        # Test caching
        connector2 = manager.get_llm_connector("gemini_test_conn")
        self.assertIs(connector2, mock_gemini_instance)
        MockGeminiClientClass.assert_called_once() # Should not be called again


    @patch.dict(os.environ, clear=True) # Ensure TEST_GEMINI_KEY_MISSING is NOT set
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_connector_gemini_api_key_missing(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        gemini_config_key_missing = {
            "id": "gemini_key_missing", "provider": "gemini", "enabled": True,
            "model_name": "gemini-flash", "api_key_env": "TEST_GEMINI_KEY_MISSING"
        }
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([gemini_config_key_missing])).return_value
        
        manager = LLMManager(config_path="dummy.yaml")
        with self.assertRaisesRegex(GeminiApiKeyError, "Environment variable 'TEST_GEMINI_KEY_MISSING' for Gemini API key not set"):
            manager.get_llm_connector("gemini_key_missing")

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_connector_not_implemented_provider(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        ollama_config = {"id": "ollama_test", "provider": "ollama", "enabled": True, "model_name": "codellama"}
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([ollama_config])).return_value

        manager = LLMManager(config_path="dummy.yaml")
        with self.assertRaisesRegex(LLMProviderNotImplementedError, "LLM provider 'ollama'.*is not supported or connector not implemented"):
            manager.get_llm_connector("ollama_test")

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_llm_connector_config_id_not_found(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        mock_file_open.return_value = mock_open(read_data=self._create_mock_config_content([])).return_value # Empty config list
        manager = LLMManager(config_path="dummy.yaml")
        with self.assertRaisesRegex(LLMConfigError, "LLM configuration with id 'non_existent_id' not found"):
            manager.get_llm_connector("non_existent_id")

if __name__ == '__main__':
    unittest.main()
