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

    @patch('jarules_agent.ui.cli.GitHubClient') 
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_startup_llm_manager_config_error(self, MockLLMManagerClass, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        MockLLMManagerClass.side_effect = LLMConfigError("Test LLM Config Error")
        run_cli() 
        output = self.mock_stdout.getvalue() 
        self.assertIn("Error initializing LLMManager: Test LLM Config Error. AI features will be unavailable.", output)
        self.assertNotIn("LLMManager initialized successfully.", output)
        self.assertNotIn("Available commands:", output)

    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_startup_llm_connector_api_key_error(self, MockLLMManagerClass, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        # Simulate that get_llm_connector for the default ID raises GeminiApiKeyError
        mock_llm_manager_instance.get_llm_connector.side_effect = lambda config_id: \
            GeminiApiKeyError("Test Gemini API Key Error via Manager") if config_id == "gemini_flash_default" else MagicMock()
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("LLMManager initialized successfully.", output)
        self.assertIn("API Key Error for LLM 'gemini_flash_default': Test Gemini API Key Error via Manager. AI features will be unavailable.", output)
        self.assertNotIn("Successfully loaded LLM", output)
        self.assertNotIn("Available commands:", output)

    @patch('jarules_agent.ui.cli.GitHubClient')
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

    @patch('jarules_agent.ui.cli.GitHubClient')
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

    def _setup_standard_mocks(self, MockLLMManagerClass, MockGitHubClientClass): # Renamed MockGitHubClient to MockGitHubClientClass
        """Helper to set up common mocks for most tests."""
        mock_gh_instance = MockGitHubClientClass.return_value # Use the class mock's return_value
        
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_active_llm_client = MagicMock(spec=GeminiClient) 
        mock_active_llm_client.model_name = "mocked-gemini-model"
        mock_llm_manager_instance.get_llm_connector.return_value = mock_active_llm_client
        return mock_llm_manager_instance, mock_active_llm_client, mock_gh_instance

    # --- Tests for 'ls' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager') 
    def test_ls_success(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient) # Use helper
        mock_input.side_effect = ["ls .", "exit"]
        mock_list_files.return_value = ['file1.txt', 'subdir']
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_list_files.assert_called_once_with('.')
        self.assertIn("Files in '.':", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_empty_dir(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls empty_dir", "exit"]
        mock_list_files.return_value = []
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("No files or directories found in 'empty_dir'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_file_not_found(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls nonexistent_path", "exit"]
        mock_list_files.side_effect = FileNotFoundError("No such file or directory")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: No such file or directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_not_a_directory(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls path_to_a_file", "exit"]
        mock_list_files.side_effect = NotADirectoryError("Not a directory")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: Not a directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ls_no_args(self, MockLLMManagerClass, MockGitHubClient, mock_list_files, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["ls", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ls <directory_path>", output)
        mock_list_files.assert_not_called()

    # --- Tests for 'read' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_success(self, MockLLMManagerClass, MockGitHubClient, mock_read_file, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["read test.txt", "exit"]
        mock_read_file.return_value = "file content"
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Content of 'test.txt':", output)
        self.assertIn("file content", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_file_not_found(self, MockLLMManagerClass, MockGitHubClient, mock_read_file, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["read nofile.txt", "exit"]
        mock_read_file.side_effect = FileNotFoundError("File not found")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error: File not found", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_read_no_args(self, MockLLMManagerClass, MockGitHubClient, mock_read_file, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["read", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: read <file_path>", output)
        mock_read_file.assert_not_called()

    # --- Tests for 'write' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_success(self, MockLLMManagerClass, MockGitHubClient, mock_write_file, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["write output.txt Hello world", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_write_file.assert_called_once_with('output.txt', "Hello world")
        self.assertIn("Content written to 'output.txt'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_io_error(self, MockLLMManagerClass, MockGitHubClient, mock_write_file, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_input.side_effect = ["write file.txt content", "exit"]
        mock_write_file.side_effect = IOError("Disk full")
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Error writing file: Disk full", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_write_no_args_or_missing_content(self, MockLLMManagerClass, MockGitHubClient, mock_write_file, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
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
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_success(self, MockLLMManagerClass, MockGitHubClient, mock_input):
        _, mock_active_llm_client, _ = self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_active_llm_client.generate_code.return_value = "def hello():\n  print('Hello World')"
        mock_input.side_effect = ["ai gencode \"create a hello world function in python\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        MockLLMManagerClass.return_value.get_llm_connector.assert_called_once_with("gemini_flash_default")
        mock_active_llm_client.generate_code.assert_called_once_with("create a hello world function in python")
        self.assertIn("--- Generated Code ---", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_gencode_no_active_client(self, MockLLMManagerClass, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_llm_manager_instance.get_llm_connector.return_value = None # Simulate no client loaded
        mock_input.side_effect = ["ai gencode \"prompt\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("AI client not available. Please check configuration.", output)
        
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_success(self, MockLLMManagerClass, MockGitHubClient, mock_input):
        _, mock_active_llm_client, _ = self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_active_llm_client.explain_code.return_value = "This code does amazing things."
        mock_input.side_effect = ["ai explain \"def foo(): pass\"", "exit"]
        run_cli()
        mock_active_llm_client.explain_code.assert_called_once_with("def foo(): pass")
        self.assertIn("--- Code Explanation ---", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_explain_file_success(self, MockLLMManagerClass, MockGitHubClient, mock_local_read_file, mock_input):
        _, mock_active_llm_client, _ = self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_local_read_file.return_value = "content from file"
        mock_active_llm_client.explain_code.return_value = "file explanation"
        mock_input.side_effect = ["ai explain_file test.py", "exit"]
        run_cli()
        mock_active_llm_client.explain_code.assert_called_once_with("content from file")
        self.assertIn("--- Code Explanation ---", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_success(self, MockLLMManagerClass, MockGitHubClient, mock_input):
        _, mock_active_llm_client, _ = self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_active_llm_client.suggest_code_modification.return_value = "fixed code here"
        mock_input.side_effect = ["ai suggest_fix \"def main(): bug()\" \"fix this bug\"", "exit"]
        run_cli()
        mock_active_llm_client.suggest_code_modification.assert_called_once_with("def main(): bug()", "fix this bug")
        self.assertIn("--- Suggested Fix ---", self.mock_stdout.getvalue())

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_ai_suggest_fix_file_success(self, MockLLMManagerClass, MockGitHubClient, mock_local_read_file, mock_input):
        _, mock_active_llm_client, _ = self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClient)
        mock_local_read_file.return_value = "file content for fix"
        mock_active_llm_client.suggest_code_modification.return_value = "fixed file content"
        mock_input.side_effect = ["ai suggest_fix_file test.py \"fix this file\"", "exit"]
        run_cli()
        mock_active_llm_client.suggest_code_modification.assert_called_once_with("file content for fix", "fix this file")
        self.assertIn("--- Suggested Fix ---", self.mock_stdout.getvalue())

    # --- Tests for 'gh_ls' and 'gh_read' commands ---
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_gh_ls_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClientClass) 
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.list_repo_files.return_value = ['file1.py', 'README.md']
        mock_input.side_effect = ["gh_ls testowner/testrepo/docs", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gh_instance.list_repo_files.assert_called_once_with(owner='testowner', repo='testrepo', path='docs')
        self.assertIn("Files in 'testowner/testrepo/docs':", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.LLMManager')
    def test_gh_read_success(self, MockLLMManagerClass, MockGitHubClientClass, mock_input):
        self._setup_standard_mocks(MockLLMManagerClass, MockGitHubClientClass)
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.read_repo_file.return_value = "File content from GitHub"
        mock_input.side_effect = ["gh_read owner/repo/path/to/file.txt", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gh_instance.read_repo_file.assert_called_once_with(owner='owner', repo='repo', file_path='path/to/file.txt')
        self.assertIn("Content of 'owner/repo/path/to/file.txt':", output)

if __name__ == '__main__':
    unittest.main()
