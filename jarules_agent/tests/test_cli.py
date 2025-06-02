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
    def test_startup_llm_manager_config_error(self, MockLLMManagerClass, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        MockLLMManagerClass.side_effect = LLMConfigError("Test LLM Config Error")
        run_cli() 
        output = self.mock_stdout.getvalue() 
        self.assertIn("Error initializing LLMManager: Test LLM Config Error. AI features will be unavailable.", output)
        self.assertNotIn("LLMManager initialized successfully.", output)
        self.assertNotIn("Available commands:", output)

    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_startup_llm_connector_error_handling(self, MockLLMManagerClass, MockGitHubClient): 
        # Use the helper to set up GitHub mock, LLMManager mock will be used directly
        MockGitHubClient.return_value = MagicMock() # Basic setup for GH Client
            
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        # Simulate error during get_llm_connector call
        # Using GeminiApiKeyError as an example, as per the original test's intent
        mock_llm_manager_instance.get_llm_connector.side_effect = GeminiApiKeyError("Test API Key Error from LLMManager path")
            
        run_cli() 
            
        output = self.mock_stdout.getvalue() 
        # Ensure LLMManager itself is reported as initialized before connector loading fails
        self.assertIn("LLMManager initialized successfully.", output) 
        self.assertIn("API Key Error for LLM 'gemini_flash_default': Test API Key Error from LLMManager path. AI features will be unavailable.", output) 
        self.assertNotIn("Successfully loaded LLM", output)
        # Depending on CLI logic, "Available commands" might still be shown if basic CLI can run.
        # For now, keeping original assertion if AI failure prevents further command processing display.
        self.assertNotIn("Available commands:", output)

    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    @patch('builtins.input')
    def test_help_command(self, mock_input, MockLLMManagerClass, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_active_llm_client = MagicMock(spec=BaseLLMConnector) 
        mock_active_llm_client.model_name = "mocked-model"
        mock_llm_manager_instance.get_llm_connector.return_value = mock_active_llm_client
        mock_input.side_effect = ["help", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Welcome to JaRules CLI!", output)
        self.assertIn("LLMManager initialized successfully.", output)
        self.assertIn("Successfully loaded LLM: 'gemini_flash_default' (Model: mocked-model)", output)
        self.assertIn("Available commands:", output)

    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    @patch('builtins.input')
    def test_exit_command(self, mock_input, MockLLMManagerClass, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_active_llm_client = MagicMock(spec=BaseLLMConnector)
        mock_active_llm_client.model_name = "mocked-model"
        mock_llm_manager_instance.get_llm_connector.return_value = mock_active_llm_client
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
        mock_active_llm_client = MagicMock(spec=llm_client_spec)
        if llm_model_name is not None: # model_name could be None if get_llm_connector fails
             mock_active_llm_client.model_name = llm_model_name
        mock_llm_manager_instance.get_llm_connector.return_value = mock_active_llm_client
        # Return the same mock_gh_instance that will actually be used by the CLI
        return mock_llm_manager_instance, mock_active_llm_client, mock_gh_instance

    # --- Tests for 'ls' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_ls_success(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient) # Use helper
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
    def test_ls_empty_dir(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls empty_dir", "exit"]
        mock_list_files.return_value = []
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("No files or directories found in 'empty_dir'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_file_not_found(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls nonexistent_path", "exit"]
        mock_list_files.side_effect = FileNotFoundError("No such file or directory")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: No such file or directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_not_a_directory(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls path_to_a_file", "exit"]
        mock_list_files.side_effect = NotADirectoryError("Not a directory")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: Not a directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_no_args(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
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
    def test_read_success(self, MockLLMManagerClass, MockGitHubClient, mock_read_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
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
    def test_read_file_not_found(self, MockLLMManagerClass, MockGitHubClient, mock_read_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["read nofile.txt", "exit"]
        mock_read_file.side_effect = FileNotFoundError("File not found")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: File not found", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_no_args(self, MockLLMManagerClass, MockGitHubClient, mock_read_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
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
    def test_write_success(self, MockLLMManagerClass, MockGitHubClient, mock_write_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["write output.txt Hello world", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_write_file.assert_called_once_with('output.txt', "Hello world")
        self.assertIn("Content written to 'output.txt'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_io_error(self, MockLLMManagerClass, MockGitHubClient, mock_write_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["write file.txt content", "exit"]
        mock_write_file.side_effect = IOError("Disk full")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error writing file: Disk full", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_no_args_or_missing_content(self, MockLLMManagerClass, MockGitHubClient, mock_write_file, mock_input):
        self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClient)
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
    def test_ai_gencode_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input): # Renamed MockGitHubClient to MockGitHubClientClass
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient, llm_model_name="mocked-gemini-model"
        )
            
        mock_llm_client.generate_code.return_value = "def hello():\n  print('Hello Manager')" # Matched guide
        mock_input.side_effect = ["ai gencode \"python hello\"", "exit"] # User input from guide
            
        run_cli() # Run the CLI main loop
            
        output = self.mock_stdout.getvalue()
        # Check that LLMManager was asked for the default connector
        mock_llm_manager_instance.get_llm_connector.assert_called_once_with("gemini_flash_default")
        # Check that the connector's method was called
        mock_llm_client.generate_code.assert_called_once_with("python hello") # Fixed: quotes stripped by CLI
        self.assertIn("--- Generated Code ---", output)
        self.assertIn("def hello():\n  print('Hello Manager')", output) # Matched guide

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_no_active_client(self, MockLLMManagerClass, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_llm_manager_instance.get_llm_connector.return_value = None # Simulate no client loaded
        mock_input.side_effect = ["ai gencode \"prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("No LLM connector available.", output)

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
        mock_llm_client.generate_code.assert_called_once_with("a prompt")
        self.assertIn("No code generated or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.generate_code.side_effect = GeminiApiError("Test API Error")
        mock_input.side_effect = ["ai gencode \"a prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.generate_code.assert_called_once_with("a prompt")
        self.assertIn("API Error: Test API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_generation_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.generate_code.side_effect = GeminiCodeGenerationError("Test Generation Error")
        mock_input.side_effect = ["ai gencode \"a prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.generate_code.assert_called_once_with("a prompt")
        self.assertIn("Code Generation Error: Test Generation Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_no_prompt(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_input.side_effect = ["ai gencode", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai gencode \"<prompt_text>\"", output)
        mock_llm_client.generate_code.assert_not_called()
        
    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input): # Renamed MockGitHubClient to MockGitHubClientClass
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient, llm_model_name="mocked-gemini-model"
        )
        mock_llm_client.explain_code.return_value = "This code does amazing things."
        mock_input.side_effect = ["ai explain \"def foo(): pass\"", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_connector.assert_called_once_with("gemini_flash_default")
        mock_llm_client.explain_code.assert_called_once_with("def foo(): pass") # Fixed: quotes stripped by CLI
        self.assertIn("--- Code Explanation ---", self.mock_stdout.getvalue())
        self.assertIn("This code does amazing things.", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_empty_result(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.explain_code.return_value = None
        mock_input.side_effect = ["ai explain \"code snippet\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.explain_code.assert_called_once_with("code snippet") # Fixed: quotes stripped by CLI  
        self.assertIn("No explanation generated or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_api_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.explain_code.side_effect = GeminiApiError("Test API Error")
        mock_input.side_effect = ["ai explain \"code snippet\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.explain_code.assert_called_once_with("code snippet") # Fixed: quotes stripped by CLI
        self.assertIn("API Error: Test API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_explanation_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.explain_code.side_effect = GeminiExplanationError("Test Explanation Error")
        mock_input.side_effect = ["ai explain \"code snippet\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.explain_code.assert_called_once_with("code snippet") # Fixed: quotes stripped by CLI
        self.assertIn("Explanation Error: Test Explanation Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_no_snippet(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
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
    def test_ai_explain_file_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input): # Renamed MockGitHubClient to MockGitHubClientClass
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient, llm_model_name="mocked-gemini-model"
        )
        mock_local_read_file.return_value = "content from file"
        mock_llm_client.explain_code.return_value = "file explanation"
        mock_input.side_effect = ["ai explain_file test.py", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_connector.assert_called_once_with("gemini_flash_default")
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.explain_code.assert_called_once_with("content from file") # Fixed: no extra quotes for file content
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
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_local_read_file.return_value = "file content"
        mock_llm_client.explain_code.side_effect = GeminiApiError("Test API Error")
        mock_input.side_effect = ["ai explain_file test.py", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.explain_code.assert_called_once_with("file content") # Fixed: no extra quotes for file content
        self.assertIn("API Error: Test API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_file_no_path(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_input.side_effect = ["ai explain_file", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai explain_file <filepath>", output)
        mock_llm_client.explain_code.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input): # Renamed MockGitHubClient to MockGitHubClientClass
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient, llm_model_name="mocked-gemini-model"
        )
        mock_llm_client.suggest_code_modification.return_value = "fixed code here"
        mock_input.side_effect = ["ai suggest_fix \"def main(): bug()\" \"fix this bug\"", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_connector.assert_called_once_with("gemini_flash_default")
        mock_llm_client.suggest_code_modification.assert_called_once_with("def main(): bug()", "fix this bug")
        self.assertIn("--- Suggested Fix ---", self.mock_stdout.getvalue())
        self.assertIn("fixed code here", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_empty_result(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.suggest_code_modification.return_value = ""
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
        mock_llm_client.suggest_code_modification.side_effect = GeminiApiError("Test API Error")
        mock_input.side_effect = ["ai suggest_fix \"code\" \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn("API Error: Test API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_modification_error(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_llm_client.suggest_code_modification.side_effect = GeminiModificationError("Test Mod Error")
        mock_input.side_effect = ["ai suggest_fix \"code\" \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_llm_client.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn("Modification Error: Test Mod Error", output)

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
    def test_ai_suggest_fix_file_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_local_read_file, mock_input): # Renamed MockGitHubClient to MockGitHubClientClass
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient, llm_model_name="mocked-gemini-model"
        )
        mock_local_read_file.return_value = "file content for fix"
        mock_llm_client.suggest_code_modification.return_value = "fixed file content"
        mock_input.side_effect = ["ai suggest_fix_file test.py \"fix this file\"", "exit"]
        run_cli()
        mock_llm_manager_instance.get_llm_connector.assert_called_once_with("gemini_flash_default")
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.suggest_code_modification.assert_called_once_with("file content for fix", "fix this file")
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
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
        )
        mock_local_read_file.return_value = "file content"
        mock_llm_client.suggest_code_modification.side_effect = GeminiApiError("Test API Error")
        mock_input.side_effect = ["ai suggest_fix_file test.py \"issue\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_llm_client.suggest_code_modification.assert_called_once_with("file content", "issue")
        self.assertIn("API Error: Test API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_file_no_path_or_issue(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        mock_llm_manager_instance, mock_llm_client, _ = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClientClass, llm_client_spec=GeminiClient
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

    # --- Tests for 'gh_ls' and 'gh_read' commands ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.github_connector.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_gh_ls_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        _, _, mock_gh_instance = self._setup_cli_mocks(MockLLMManagerClass, MockGitHubClientClass) 
        # mock_gh_instance = MockGitHubClientClass.return_value # This is now handled by _setup_cli_mocks
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
        # mock_gh_instance = MockGitHubClientClass.return_value # This is now handled by _setup_cli_mocks
        mock_gh_instance.read_repo_file.return_value = "File content from GitHub"
        mock_input.side_effect = ["gh_read owner/repo/path/to/file.txt", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gh_instance.read_repo_file.assert_called_once_with(owner='owner', repo='repo', file_path='path/to/file.txt')
        self.assertIn("Content of 'owner/repo/path/to/file.txt':", output)

if __name__ == '__main__':
    unittest.main()
