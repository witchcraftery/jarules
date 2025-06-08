# jarules_agent/tests/test_cli.py

import unittest
from unittest.mock import patch, MagicMock, call
import io
import sys

# Adjust import path for standalone execution
import os
if '.' not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from jarules_agent.ui.cli import run_cli
    from jarules_agent.connectors import local_files
    from jarules_agent.connectors.github_connector import GitHubClient
    # Specific Gemini errors are still caught by CLI, so keep them.
    from jarules_agent.connectors.gemini_api import (
        GeminiClient, GeminiApiKeyError, GeminiCodeGenerationError, 
        GeminiApiError, GeminiExplanationError, GeminiModificationError
    )
    from jarules_agent.connectors.base_llm_connector import LLMConnectorError, BaseLLMConnector
    from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError
except ModuleNotFoundError as e:
    print(f"Test setup: Could not import modules for test_cli.py: {e}")
    raise

class TestCLI(unittest.TestCase):

    def setUp(self):
        self.mock_stdout = io.StringIO()
        self.patch_stdout = patch('sys.stdout', self.mock_stdout)
        self.patch_stdout.start()
        self.mock_stderr = io.StringIO()
        self.patch_stderr = patch('sys.stderr', self.mock_stderr)
        self.patch_stderr.start()


    def tearDown(self):
        self.patch_stdout.stop()
        self.patch_stderr.stop()

    @patch('jarules_agent.connectors.github_connector.GitHubClient') 
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_startup_llm_manager_config_error(self, MockLLMManagerClass, MockGitHubClientClass):
        MockGitHubClientClass.return_value = MagicMock()
        MockLLMManagerClass.side_effect = LLMConfigError("Test LLM Config Error")
        run_cli() 
        output = self.mock_stdout.getvalue() 
        self.assertIn("Error initializing LLMManager: Test LLM Config Error. AI features will be unavailable.", output)
        self.assertNotIn("LLMManager initialized.", output) # Changed message
        # Help might still be displayed if LLMManager is not critical for basic ops,
        # but current CLI logic might exit or not show full help. Assuming it doesn't proceed.
        # self.assertNotIn("Available commands:", output) # This depends on final CLI flow

    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_startup_llm_load_active_model_error(self, MockLLMManagerClass, MockGitHubClientClass):
        MockGitHubClientClass.return_value = MagicMock()
            
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_llm_manager_instance.active_provider_id = "failing_default" # Assume this was set from config
        # Simulate error during get_llm_client call for the active model
        mock_llm_manager_instance.get_llm_client.side_effect = LLMManagerError("Test: Could not load failing_default")
            
        run_cli() 
            
        output = self.mock_stdout.getvalue() 
        self.assertIn("LLMManager initialized, but failed to load active model 'failing_default': Test: Could not load failing_default", output)
        self.assertNotIn("Active model ID: 'failing_default' (Model:", output) # Success message shouldn't appear

    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    @patch('builtins.input')
    def test_help_command(self, mock_input, MockLLMManagerClass, MockGitHubClientClass):
        mock_llm_manager_instance, mock_active_llm_client, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_llm_manager_instance.active_provider_id = "gemini_flash_default" # Assume a default is active
        mock_active_llm_client.config = {"provider": "gemini"} # Add provider for get-model in set-model

        mock_input.side_effect = ["help", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Welcome to JaRules CLI!", output)
        self.assertIn(f"LLMManager initialized. Active model ID: '{mock_llm_manager_instance.active_provider_id}' (Model: {mock_active_llm_client.model_name})", output)
        self.assertIn("Available commands:", output)
        self.assertIn("set-model <provider_id>", output) # Check for new commands in help
        self.assertIn("get-model", output)


    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    @patch('builtins.input')
    def test_exit_command(self, mock_input, MockLLMManagerClass, MockGitHubClientClass):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Exiting JaRules CLI. Goodbye!", output)
        self.assertEqual(mock_input.call_count, 1)

    # Helper (if not already present or adapt existing setup for mocks)
    def _setup_cli_mocks(self, MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=BaseLLMConnector, llm_model_name="mocked-model"):
        # Create a consistent mock for GitHubClient that can be used and configured
        mock_gh_instance = MagicMock()
        MockGitHubClientClass.return_value = mock_gh_instance
        
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_llm_manager_instance.active_provider_id = "test_default_active_id" # Simulate an active provider

        mock_active_llm_client = MagicMock(spec=llm_client_spec)
        if llm_model_name is not None:
             mock_active_llm_client.model_name = llm_model_name
        # This mock now applies to get_llm_client
        mock_llm_manager_instance.get_llm_client.return_value = mock_active_llm_client
        return mock_llm_manager_instance, mock_active_llm_client, mock_gh_instance

    # --- Model Management Command Tests ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_set_model_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, mock_llm_client, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)

        # Simulate properties of the client that would be set for the new model
        new_model_client_mock = MagicMock(spec=BaseLLMConnector)
        new_model_client_mock.model_name = "ollama-model-123"
        new_model_client_mock.config = {"provider": "ollama"} # Used by get-model for display

        def set_active_effect(provider_id):
            mock_llm_manager.active_provider_id = provider_id # Simulate manager setting it
            # When get_llm_client is called after set_active_provider, return the new mock client
            mock_llm_manager.get_llm_client.return_value = new_model_client_mock
            return None # set_active_provider itself returns None

        mock_llm_manager.set_active_provider.side_effect = set_active_effect

        mock_input.side_effect = ["set-model ollama_local_config", "exit"]
        run_cli()

        output = self.mock_stdout.getvalue()
        mock_llm_manager.set_active_provider.assert_called_once_with("ollama_local_config")
        # get_llm_client is called by set-model to confirm, and by startup message
        self.assertGreaterEqual(mock_llm_manager.get_llm_client.call_count, 1)
        self.assertIn("Active model set to: 'ollama_local_config' (Model: ollama-model-123, Provider: ollama)", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_set_model_invalid_id(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_llm_manager.set_active_provider.side_effect = ValueError("Invalid provider ID 'bad_id'")
        mock_input.side_effect = ["set-model bad_id", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error setting model: Invalid provider ID 'bad_id'", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_set_model_load_failure(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_llm_manager.set_active_provider.return_value = None # Simulate successful set in manager attribute
        mock_llm_manager.get_llm_client.side_effect = LLMManagerError("Failed to load new model") # Error on get

        mock_input.side_effect = ["set-model new_model_id", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error loading new active model 'new_model_id': Failed to load new model", output)


    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_get_model_active_set(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        active_id = "active_test_model"
        mock_llm_manager.active_provider_id = active_id
        mock_llm_manager.get_available_configs.return_value = {
            active_id: {"provider": "test_provider", "model_name": "TestModelX", "description": "A test model."}
        }
        mock_input.side_effect = ["get-model", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Currently active model configuration:", output)
        self.assertIn(f"  ID: {active_id}", output)
        self.assertIn("  Provider: test_provider", output)
        self.assertIn("  Model Name: TestModelX", output)
        self.assertIn("  Description: A test model.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_get_model_none_active(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_llm_manager.active_provider_id = None # Ensure no active model
        mock_input.side_effect = ["get-model", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("No active model is currently set. Use 'set-model <provider_id>'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_clear_model_success_with_default(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)

        # Simulate that after clearing, there's a default model it falls back to
        mock_llm_manager.active_provider_id = "some_active_model_before_clear" # Initial state

        # This client will be returned by get_llm_client *after* clear_active_provider_state has run
        # and potentially reset active_provider_id to a default.
        default_client_mock = MagicMock(spec=BaseLLMConnector)
        default_client_mock.model_name = "default-model-001"

        def clear_state_effect():
            mock_llm_manager.active_provider_id = "config_default_model" # Simulate it reverted to this
            mock_llm_manager.get_llm_client.return_value = default_client_mock # get_llm_client will now return this

        mock_llm_manager.clear_active_provider_state.side_effect = clear_state_effect

        mock_input.side_effect = ["clear-model", "exit"]
        run_cli()

        output = self.mock_stdout.getvalue()
        mock_llm_manager.clear_active_provider_state.assert_called_once()
        self.assertIn("Active model selection cleared. Now using default: 'config_default_model' (Model: default-model-001)", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_clear_model_success_no_default(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_llm_manager.active_provider_id = "some_active_model_before_clear"

        def clear_state_effect_no_default():
            mock_llm_manager.active_provider_id = None # Simulate no default to fall back to

        mock_llm_manager.clear_active_provider_state.side_effect = clear_state_effect_no_default

        mock_input.side_effect = ["clear-model", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_manager.clear_active_provider_state.assert_called_once()
        self.assertIn("Active model selection cleared. No default provider configured.", output)


    # --- Tests for 'ls' command (no changes, but ensure they still pass with new setup) ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_ls_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["ls .", "exit"]
        mock_list_files.return_value = ['file1.txt', 'subdir']
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_list_files.assert_called_once_with('.')
        self.assertIn("Files in '.':", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_empty_dir(self, MockLLMManagerClass, MockGitHubClientClass, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["ls empty_dir", "exit"]
        mock_list_files.return_value = []
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("No files or directories found in 'empty_dir'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_file_not_found(self, MockLLMManagerClass, MockGitHubClientClass, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["ls nonexistent_path", "exit"]
        mock_list_files.side_effect = FileNotFoundError("No such file or directory")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: No such file or directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_not_a_directory(self, MockLLMManagerClass, MockGitHubClientClass, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["ls path_to_a_file", "exit"]
        mock_list_files.side_effect = NotADirectoryError("Not a directory")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: Not a directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_no_args(self, MockLLMManagerClass, MockGitHubClientClass, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["ls", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ls <directory_path>", output)
        mock_list_files.assert_not_called()

    # --- Tests for 'read' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_read_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["read test.txt", "exit"]
        mock_read_file.return_value = "file content"
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Content of 'test.txt':", output)
        self.assertIn("file content", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_file_not_found(self, MockLLMManagerClass, MockGitHubClientClass, mock_read_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["read nofile.txt", "exit"]
        mock_read_file.side_effect = FileNotFoundError("File not found")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: File not found", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_no_args(self, MockLLMManagerClass, MockGitHubClientClass, mock_read_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["read", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: read <file_path>", output)
        mock_read_file.assert_not_called()

    # --- Tests for 'write' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_write_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["write output.txt Hello world", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_write_file.assert_called_once_with('output.txt', "Hello world")
        self.assertIn("Content written to 'output.txt'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_io_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_write_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["write file.txt content", "exit"]
        mock_write_file.side_effect = IOError("Disk full")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error writing file: Disk full", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_no_args_or_missing_content(self, MockLLMManagerClass, MockGitHubClientClass, mock_write_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_input.side_effect = ["write", "exit"]
        run_cli()
        self.assertIn("Usage: write <file_path> <content>", self.mock_stdout.getvalue())
        self.mock_stdout.truncate(0); self.mock_stdout.seek(0) # Clear stdout
        mock_input.side_effect = ["write file.txt", "exit"]
        run_cli()
        self.assertIn("Usage: write <file_path> <content>", self.mock_stdout.getvalue())
        mock_write_file.assert_not_called()

    # --- Tests for AI commands ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=BaseLLMConnector, llm_model_name="active-model"
        )
        mock_llm_manager_instance.active_provider_id = "test_active_model_id" # Set an active ID for logging
            
        mock_llm_client.generate_code.return_value = "def hello():\n  print('Hello Active Model')"
        mock_input.side_effect = ["ai gencode \"python hello\"", "exit"]
            
        run_cli()
            
        output = self.mock_stdout.getvalue()
        mock_llm_manager_instance.get_llm_client.assert_called_once_with() # Called with no args
        mock_llm_client.generate_code.assert_called_once_with("python hello")
        self.assertIn(f"Generating code using '{mock_llm_manager_instance.active_provider_id}'", output)
        self.assertIn("--- Generated Code ---", output)
        self.assertIn("def hello():\n  print('Hello Active Model')", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_llm_manager_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, _, _ = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_llm_manager_instance.get_llm_client.side_effect = LLMManagerError("No active model set")
        mock_input.side_effect = ["ai gencode \"prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("LLM Error: No active model set. Cannot perform AI operation.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_empty_result(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.generate_code.return_value = ""
        mock_input.side_effect = ["ai gencode \"a prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.generate_code.assert_called_once_with("a prompt") # Ensure method still called
        self.assertIn("No code generated or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_manager_instance.active_provider_id = "gem_err_provider"
        mock_llm_client.generate_code.side_effect = LLMConnectorError("Test API Error from Connector") # Generic error
        mock_input.side_effect = ["ai gencode \"a prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.generate_code.assert_called_once_with("a prompt")
        self.assertIn("Code Generation Error (gem_err_provider): Test API Error from Connector", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_generation_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        # This test might be redundant if GeminiCodeGenerationError is a subclass of LLMConnectorError
        # and handled by the previous test. Assuming it's distinct for now or a more specific case.
        mock_llm_manager_instance.active_provider_id = "gem_gen_err_provider"
        mock_llm_client.generate_code.side_effect = GeminiCodeGenerationError("Test Specific Generation Error")
        mock_input.side_effect = ["ai gencode \"a prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.generate_code.assert_called_once_with("a prompt")
        self.assertIn("Code Generation Error (gem_gen_err_provider): Test Specific Generation Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_no_prompt(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_input.side_effect = ["ai gencode", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai gencode \"<prompt_text>\"", output)
        mock_llm_client.generate_code.assert_not_called() # Should not be called if usage is printed
        
    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_llm_manager_instance.active_provider_id = "explainer_model"
        mock_llm_client.explain_code.return_value = "This code does amazing things."
        mock_input.side_effect = ["ai explain \"def foo(): pass\"", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_client.assert_called_once_with()
        mock_llm_client.explain_code.assert_called_once_with("def foo(): pass")
        self.assertIn(f"Explaining code snippet using '{mock_llm_manager_instance.active_provider_id}'", self.mock_stdout.getvalue())
        self.assertIn("--- Code Explanation ---", self.mock_stdout.getvalue())
        self.assertIn("This code does amazing things.", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_empty_result(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.explain_code.return_value = None # Or ""
        mock_input.side_effect = ["ai explain \"code snippet\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.explain_code.assert_called_once_with("code snippet")
        self.assertIn("No explanation generated or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_manager_instance.active_provider_id = "err_explain_model"
        mock_llm_client.explain_code.side_effect = LLMConnectorError("Test Explain API Error")
        mock_input.side_effect = ["ai explain \"code snippet\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.explain_code.assert_called_once_with("code snippet")
        self.assertIn(f"Explanation Error ({mock_llm_manager_instance.active_provider_id}): Test Explain API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_explanation_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        # Redundant if GeminiExplanationError is subclass of LLMConnectorError
        mock_llm_manager_instance.active_provider_id = "gem_spec_explain_err"
        mock_llm_client.explain_code.side_effect = GeminiExplanationError("Test Specific Explanation Error")
        mock_input.side_effect = ["ai explain \"code snippet\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.explain_code.assert_called_once_with("code snippet")
        self.assertIn(f"Explanation Error ({mock_llm_manager_instance.active_provider_id}): Test Specific Explanation Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_no_snippet(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_input.side_effect = ["ai explain", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai explain \"<code_snippet>\"", output)
        mock_llm_client.explain_code.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_file_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_llm_manager_instance.active_provider_id = "file_explainer"
        mock_local_read_file.return_value = "content from file"
        mock_llm_client.explain_code.return_value = "file explanation"
        mock_input.side_effect = ["ai explain_file test.py", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_client.assert_called_once_with()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.explain_code.assert_called_once_with("content from file")
        self.assertIn(f"Explaining file using '{mock_llm_manager_instance.active_provider_id}'", self.mock_stdout.getvalue())
        self.assertIn("--- Code Explanation ---", self.mock_stdout.getvalue())
        self.assertIn("file explanation", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_file_read_not_found(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_local_read_file.side_effect = FileNotFoundError("File not found")
        mock_input.side_effect = ["ai explain_file nofile.py", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("nofile.py")
        self.assertIn("Error: File not found: nofile.py", output)
        mock_llm_client.explain_code.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_file_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_llm_manager_instance.active_provider_id = "file_explain_err_model"
        mock_local_read_file.return_value = "file content"
        mock_llm_client.explain_code.side_effect = LLMConnectorError("Test File Explain API Error")
        mock_input.side_effect = ["ai explain_file test.py", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.explain_code.assert_called_once_with("file content")
        self.assertIn(f"Error explaining code from file ({mock_llm_manager_instance.active_provider_id}): Test File Explain API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_file_no_path(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_input.side_effect = ["ai explain_file", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai explain_file <filepath>", output)
        mock_llm_client.explain_code.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_llm_manager_instance.active_provider_id = "fixer_model"
        mock_llm_client.suggest_code_modification.return_value = "fixed code here"
        mock_input.side_effect = ["ai suggest_fix \"def main(): bug()\" \"fix this bug\"", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_client.assert_called_once_with()
        mock_llm_client.suggest_code_modification.assert_called_once_with("def main(): bug()", "fix this bug")
        self.assertIn(f"Suggesting fix using '{mock_llm_manager_instance.active_provider_id}'", self.mock_stdout.getvalue())
        self.assertIn("--- Suggested Fix ---", self.mock_stdout.getvalue())
        self.assertIn("fixed code here", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_empty_result(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.suggest_code_modification.return_value = "" # Or None
        mock_input.side_effect = ["ai suggest_fix \"code\" \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn("No fix suggested or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_manager_instance.active_provider_id = "fix_api_err_model"
        mock_llm_client.suggest_code_modification.side_effect = LLMConnectorError("Test Suggest API Error")
        mock_input.side_effect = ["ai suggest_fix \"code\" \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn(f"Modification Error ({mock_llm_manager_instance.active_provider_id}): Test Suggest API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_modification_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        # Redundant if GeminiModificationError is subclass of LLMConnectorError
        mock_llm_manager_instance.active_provider_id = "fix_mod_err_model"
        mock_llm_client.suggest_code_modification.side_effect = GeminiModificationError("Test Specific Mod Error")
        mock_input.side_effect = ["ai suggest_fix \"code\" \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn(f"Modification Error ({mock_llm_manager_instance.active_provider_id}): Test Specific Mod Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_not_enough_args(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_input.side_effect = ["ai suggest_fix \"codeonly\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix \"<code_snippet>\" \"<issue_description>\"", output)
        mock_llm_client.suggest_code_modification.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_file_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_llm_manager_instance.active_provider_id = "file_fixer_model"
        mock_local_read_file.return_value = "file content for fix"
        mock_llm_client.suggest_code_modification.return_value = "fixed file content"
        mock_input.side_effect = ["ai suggest_fix_file test.py \"fix this file\"", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_client.assert_called_once_with()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.suggest_code_modification.assert_called_once_with("file content for fix", "fix this file")
        self.assertIn(f"Suggesting fix for file using '{mock_llm_manager_instance.active_provider_id}'", self.mock_stdout.getvalue())
        self.assertIn("--- Suggested Fix ---", self.mock_stdout.getvalue())
        self.assertIn("fixed file content", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_file_read_not_found(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_local_read_file.side_effect = FileNotFoundError("File not found")
        mock_input.side_effect = ["ai suggest_fix_file nofile.py \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("nofile.py")
        self.assertIn("Error: File not found: nofile.py", output)
        mock_llm_client.suggest_code_modification.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_file_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_llm_manager_instance.active_provider_id = "file_fix_err_model"
        mock_local_read_file.return_value = "file content"
        mock_llm_client.suggest_code_modification.side_effect = LLMConnectorError("Test File Suggest API Error")
        mock_input.side_effect = ["ai suggest_fix_file test.py \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.suggest_code_modification.assert_called_once_with("file content", "issue")
        self.assertIn(f"Modification Error ({mock_llm_manager_instance.active_provider_id}): Test File Suggest API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_file_no_path_or_issue(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass
        )
        mock_input.side_effect = ["ai suggest_fix_file test.py", "exit"] # Missing issue
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix_file <filepath> \"<issue_description>\"", output)
        mock_llm_client.suggest_code_modification.assert_not_called()
        
        self.mock_stdout.truncate(0) # Clear stdout for next check
        self.mock_stdout.seek(0)
        mock_input.side_effect = ["ai suggest_fix_file", "exit"] # Missing path and issue
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix_file <filepath> \"<issue_description>\"", output)
        mock_llm_client.suggest_code_modification.assert_not_called()

    # --- Tests for 'gh_ls' and 'gh_read' commands (ensure they still work) ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_gh_ls_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        _, _, mock_gh_instance = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass) 
        mock_gh_instance.list_repo_files.return_value = ['file1.py', 'README.md']
        mock_input.side_effect = ["gh_ls testowner/testrepo/docs", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gh_instance.list_repo_files.assert_called_once_with(owner='testowner', repo='testrepo', path='docs')
        self.assertIn("Files in 'testowner/testrepo/docs':", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_gh_read_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        _, _, mock_gh_instance = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_gh_instance.read_repo_file.return_value = "File content from GitHub"
        mock_input.side_effect = ["gh_read owner/repo/path/to/file.txt", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gh_instance.read_repo_file.assert_called_once_with(owner='owner', repo='repo', file_path='path/to/file.txt')
        self.assertIn("Content of 'owner/repo/path/to/file.txt':", output)

if __name__ == '__main__':
    unittest.main()
