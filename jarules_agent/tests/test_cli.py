# jarules_agent/tests/test_cli.py

import unittest
from unittest.mock import patch, MagicMock, call
import io
import sys

# Adjust import path for standalone execution if necessary
# This ensures that 'from jarules_agent...' works correctly
import os
if '.' not in sys.path:
    # Assuming this test file is in jarules_agent/tests/
    # Add the parent directory of 'jarules_agent' to sys.path
    # This would be os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # However, the tool environment usually sets up PYTHONPATH to /app (project root)
    # So, direct imports like 'from jarules_agent...' should ideally work.
    # Let's try a common approach if the above isn't sufficient in all contexts:
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    # project_root = os.path.abspath(os.path.join(current_dir, '..', '..')) # Adjust '..' based on actual depth
    # if project_root not in sys.path:
    #    sys.path.insert(0, project_root)
    pass # Relying on tool's PYTHONPATH setup for now.


try:
    from jarules_agent.ui.cli import run_cli
    from jarules_agent.connectors import local_files # Module itself for patching its functions
    from jarules_agent.connectors.github_connector import GitHubClient
    from jarules_agent.connectors.gemini_api import GeminiClient, GeminiApiKeyError, GeminiCodeGenerationError, GeminiApiError, GeminiExplanationError, GeminiModificationError
    # LLMConnectorError might be useful if we want to test for it broadly
    from jarules_agent.connectors.base_llm_connector import LLMConnectorError 
except ModuleNotFoundError as e:
    print(f"Test setup: Could not import modules: {e}")
    # Fallback for simpler pathing if the above fails in specific environments
    # This assumes the script might be run from jarules_agent/tests or similar
    # and 'jarules_agent' is the top-level package we need to make visible.
    # Adjusting sys.path here can be fragile; proper PYTHONPATH is preferred.
    # If this is a consistent issue, the path adjustment at the top of the file needs to be more robust.
    # For now, we'll assume the primary try block works in the tool environment.
    raise

class TestCLI(unittest.TestCase):

    def setUp(self):
        """Set up for each test method."""
        # Redirect stdout and stderr to capture print statements from the CLI
        self.mock_stdout = io.StringIO()
        self.mock_stderr = io.StringIO()
        self.patch_stdout = patch('sys.stdout', self.mock_stdout)
        self.patch_stderr = patch('sys.stderr', self.mock_stderr)
        
        self.patch_stdout.start()
        self.patch_stderr.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.patch_stdout.stop()
        self.patch_stderr.stop()

    @patch('jarules_agent.ui.cli.GitHubClient') # Also mock GitHubClient to avoid its init
    @patch('jarules_agent.ui.cli.GeminiClient') 
    def test_startup_gemini_api_key_error(self, MockGeminiClient, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock() # Ensure GitHubClient doesn't cause issues
        # Configure the constructor of the mocked GeminiClient to raise GeminiApiKeyError
        MockGeminiClient.side_effect = GeminiApiKeyError("Test API Key Error")
        
        run_cli() 
        
        output = self.mock_stdout.getvalue() 
        self.assertIn("Error: Test API Key Error AI features will be unavailable.", output)
        # Check that the "Gemini Client initialized successfully" message is NOT there
        self.assertNotIn("Gemini Client initialized successfully.", output)
        # Check that help is not displayed after this error
        self.assertNotIn("Available commands:", output)

    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient') 
    @patch('builtins.input')
    def test_help_command(self, mock_input, MockGeminiClient, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        MockGeminiClient.return_value = MagicMock() # Successful Gemini client mock
        mock_input.side_effect = ["help", "exit"]
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        # Check for welcome message and Gemini init success
        self.assertIn("Welcome to JaRules CLI!", output)
        self.assertIn("Gemini Client initialized successfully.", output)
        
        # Check for help sections
        self.assertIn("Available commands:", output)
        self.assertIn("Local File System:", output)
        self.assertIn("GitHub:", output)
        self.assertIn("AI:", output)
        self.assertIn("General:", output)
        
        # Check for specific commands in help output
        self.assertIn("ls <directory_path>", output)
        self.assertIn("gh_ls <owner>/<repo>", output)
        self.assertIn("ai gencode \"<prompt_text>\"", output)
        self.assertIn("help", output)
        self.assertIn("exit / quit", output)

        # Check that the exit message is also present
        self.assertIn("Exiting JaRules CLI. Goodbye!", output)

    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    @patch('builtins.input')
    def test_exit_command(self, mock_input, MockGeminiClient, MockGitHubClient):
        MockGitHubClient.return_value = MagicMock()
        MockGeminiClient.return_value = MagicMock() # Successful Gemini client mock
        mock_input.side_effect = ["exit"]
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        self.assertIn("Welcome to JaRules CLI!", output) # Should still see welcome
        self.assertIn("Gemini Client initialized successfully.", output) # And successful init
        self.assertIn("Exiting JaRules CLI. Goodbye!", output)
        self.assertEqual(mock_input.call_count, 1)

    # --- Tests for 'ls' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ls_success(self, MockGeminiClient, MockGitHubClient, mock_list_files, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["ls .", "exit"]
        mock_list_files.return_value = ['file1.txt', 'subdir']
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_list_files.assert_called_once_with('.')
        self.assertIn("Files in '.':", output)
        self.assertIn("file1.txt", output)
        self.assertIn("subdir", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ls_empty_dir(self, MockGeminiClient, MockGitHubClient, mock_list_files, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["ls empty_dir", "exit"]
        mock_list_files.return_value = []
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_list_files.assert_called_once_with('empty_dir')
        self.assertIn("No files or directories found in 'empty_dir'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ls_file_not_found(self, MockGeminiClient, MockGitHubClient, mock_list_files, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["ls nonexistent_path", "exit"]
        mock_list_files.side_effect = FileNotFoundError("No such file or directory")
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_list_files.assert_called_once_with('nonexistent_path')
        self.assertIn("Error: No such file or directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ls_not_a_directory(self, MockGeminiClient, MockGitHubClient, mock_list_files, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["ls path_to_a_file", "exit"]
        mock_list_files.side_effect = NotADirectoryError("Not a directory")
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_list_files.assert_called_once_with('path_to_a_file')
        self.assertIn("Error: Not a directory", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.list_files')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ls_no_args(self, MockGeminiClient, MockGitHubClient, mock_list_files, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["ls", "exit"]
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ls <directory_path>", output)
        mock_list_files.assert_not_called()

    # --- Tests for 'read' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_read_success(self, MockGeminiClient, MockGitHubClient, mock_read_file, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["read test.txt", "exit"]
        mock_read_file.return_value = "file content"
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_read_file.assert_called_once_with('test.txt')
        self.assertIn("Content of 'test.txt':", output)
        self.assertIn("---", output) # Check for separator
        self.assertIn("file content", output)
        # Ensure both separators are there
        self.assertEqual(output.count("---"), 2)


    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_read_file_not_found(self, MockGeminiClient, MockGitHubClient, mock_read_file, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["read nofile.txt", "exit"]
        mock_read_file.side_effect = FileNotFoundError("File not found")
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_read_file.assert_called_once_with('nofile.txt')
        self.assertIn("Error: File not found", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_read_no_args(self, MockGeminiClient, MockGitHubClient, mock_read_file, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["read", "exit"]
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: read <file_path>", output)
        mock_read_file.assert_not_called()

    # --- Tests for 'write' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_write_success(self, MockGeminiClient, MockGitHubClient, mock_write_file, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["write output.txt Hello world", "exit"]
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_write_file.assert_called_once_with('output.txt', "Hello world")
        self.assertIn("Content written to 'output.txt'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_write_io_error(self, MockGeminiClient, MockGitHubClient, mock_write_file, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        mock_input.side_effect = ["write file.txt content", "exit"]
        mock_write_file.side_effect = IOError("Disk full")
        
        run_cli()
        
        output = self.mock_stdout.getvalue()
        mock_write_file.assert_called_once_with('file.txt', "content")
        self.assertIn("Error writing file: Disk full", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.write_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_write_no_args_or_missing_content(self, MockGeminiClient, MockGitHubClient, mock_write_file, mock_input):
        MockGeminiClient.return_value = MagicMock()
        MockGitHubClient.return_value = MagicMock()
        
        # Test with 'write' (no arguments)
        mock_input.side_effect = ["write", "exit"]
        run_cli()
        output_no_args = self.mock_stdout.getvalue()
        self.assertIn("Usage: write <file_path> <content>", output_no_args)
        
        # Reset stdout for the next call if needed or check distinct parts
        self.mock_stdout.truncate(0)
        self.mock_stdout.seek(0)

        # Test with 'write file.txt' (missing content)
        mock_input.side_effect = ["write file.txt", "exit"]
        run_cli()
        output_missing_content = self.mock_stdout.getvalue()
        self.assertIn("Usage: write <file_path> <content>", output_missing_content)
        
        mock_write_file.assert_not_called()

    # Example of a placeholder test
    # def test_example_placeholder(self):
    #    self.assertTrue(True)

    # --- Tests for AI commands ---

    # --- Tests for 'ai gencode' command ---
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_gencode_success(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.generate_code.return_value = "def hello():\n  print('Hello World')"
        mock_input.side_effect = ["ai gencode \"create a hello world function in python\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.generate_code.assert_called_once_with("create a hello world function in python")
        self.assertIn("--- Generated Code ---", output)
        self.assertIn("def hello():\n  print('Hello World')", output)
        self.assertIn("--- End of Generated Code ---", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_gencode_empty_result(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.generate_code.return_value = None
        mock_input.side_effect = ["ai gencode \"some prompt\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.generate_code.assert_called_once_with("some prompt")
        self.assertIn("No code generated, or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_gencode_api_error(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.generate_code.side_effect = GeminiApiError("Test API Error")
        mock_input.side_effect = ["ai gencode \"some prompt\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.generate_code.assert_called_once_with("some prompt")
        self.assertIn("API Error: Test API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_gencode_generation_error(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.generate_code.side_effect = GeminiCodeGenerationError("Test Gen Error")
        mock_input.side_effect = ["ai gencode \"some prompt\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.generate_code.assert_called_once_with("some prompt")
        self.assertIn("Error generating code: Test Gen Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_gencode_no_prompt(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_input.side_effect = ["ai gencode", "exit"] # No prompt provided

        run_cli()

        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai gencode \"<prompt_text>\"", output)
        mock_gemini_instance.generate_code.assert_not_called()

    # --- Tests for 'ai explain' command ---
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_success(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.explain_code.return_value = "This code does amazing things."
        mock_input.side_effect = ["ai explain \"def foo(): pass\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.explain_code.assert_called_once_with("def foo(): pass")
        self.assertIn("--- Code Explanation ---", output)
        self.assertIn("This code does amazing things.", output)
        self.assertIn("--- End of Explanation ---", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_empty_result(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.explain_code.return_value = None
        mock_input.side_effect = ["ai explain \"code\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.explain_code.assert_called_once_with("code")
        self.assertIn("No explanation generated or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_api_error(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.explain_code.side_effect = GeminiApiError("Explain API Error")
        mock_input.side_effect = ["ai explain \"code\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.explain_code.assert_called_once_with("code")
        self.assertIn("API Error: Explain API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_explanation_error(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.explain_code.side_effect = GeminiExplanationError("Explain Gen Error")
        mock_input.side_effect = ["ai explain \"code\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gemini_instance.explain_code.assert_called_once_with("code")
        self.assertIn("Error explaining code: Explain Gen Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_no_snippet(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_input.side_effect = ["ai explain", "exit"] # No snippet

        run_cli()

        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai explain \"<code_snippet>\"", output)
        mock_gemini_instance.explain_code.assert_not_called()

    # --- Tests for 'ai explain_file' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_file_success(self, MockGeminiClient, MockGitHubClient, mock_local_read_file, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_local_read_file.return_value = "content from file"
        mock_gemini_instance.explain_code.return_value = "file explanation"
        mock_input.side_effect = ["ai explain_file test.py", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_gemini_instance.explain_code.assert_called_once_with("content from file")
        self.assertIn("--- Code Explanation ---", output)
        self.assertIn("file explanation", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_file_read_not_found(self, MockGeminiClient, MockGitHubClient, mock_local_read_file, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_local_read_file.side_effect = FileNotFoundError("No such file")
        mock_input.side_effect = ["ai explain_file non_existent.py", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("non_existent.py")
        self.assertIn("Error: File not found: non_existent.py", output)
        mock_gemini_instance.explain_code.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_file_api_error(self, MockGeminiClient, MockGitHubClient, mock_local_read_file, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_local_read_file.return_value = "file content"
        mock_gemini_instance.explain_code.side_effect = GeminiApiError("Explain File API Error")
        mock_input.side_effect = ["ai explain_file test.py", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_gemini_instance.explain_code.assert_called_once_with("file content")
        self.assertIn("API Error: Explain File API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_explain_file_no_path(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_input.side_effect = ["ai explain_file", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai explain_file <filepath>", output)
        mock_gemini_instance.explain_code.assert_not_called()

    # --- Tests for 'ai suggest_fix' command ---
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_success(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.suggest_code_modification.return_value = "fixed code here"
        # Note: The CLI joins args after the command and sub-command, so "code snippet" and "the issue" are treated as two arguments
        # For the actual CLI, users would need to quote: ai suggest_fix "code snippet" "the issue"
        # For testing, we can pass them as if they were quoted by splitting the string here.
        mock_input.side_effect = ["ai suggest_fix \"original code\" \"has a bug\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        # The CLI's split() will result in ["ai", "suggest_fix", "\"original", "code\"", "\"has", "a", "bug\""]
        # The current CLI logic for `ai suggest_fix` expects exactly 2 arguments after "ai suggest_fix".
        # This means `args[0]` is "original code" and `args[1]` is "has a bug" due to how `parts = raw_input.split()` and `args = parts[1:]` work
        # then `command = parts[0]` and `args = parts[1:]` means command is "ai" and `args` is `["suggest_fix", "original code", "has a bug"]`
        # Then `sub_command = args[0]` is `suggest_fix`. `code_snippet = args[1]` is `original code`. `issue_description = args[2]` is `has a bug`.
        # This seems to be how it's parsed in cli.py based on the patch for 'ai suggest_fix' in previous steps.
        # Let's adjust the test to match the argument parsing in cli.py:
        # `ai suggest_fix code_snippet issue_description`
        # The issue is that the cli.py code `code_snippet = args[0]` and `issue_description = args[1]` for `ai suggest_fix`.
        # This is incorrect for `ai suggest_fix "code snippet" "issue"`.
        # The CLI code is: `elif command == "ai" and args and args[0].lower() == "suggest_fix":`
        #   `if len(args) == 3:  # Expecting "suggest_fix", "<code>", "<issue>"`
        #   `  code_snippet = args[1]`
        #   `  issue_description = args[2]`
        # This was an error in my test plan. The actual CLI code for `ai suggest_fix` is `if len(args) == 2: code_snippet = args[0]; issue_description = args[1]`
        # This is wrong. The code for `ai suggest_fix` in cli.py is:
        # elif command == "ai" and args and args[0].lower() == "suggest_fix":
        #    if len(args) == 3: # Expecting "suggest_fix", "<code>", "<issue>"
        #        code_snippet = args[1]
        #        issue_description = args[2]
        # The test input `ai suggest_fix "original code" "has a bug"` will be split by space.
        # parts = ["ai", "suggest_fix", "\"original", "code\"", "\"has", "a", "bug\""]
        # command = "ai"
        # args = ["suggest_fix", "\"original", "code\"", "\"has", "a", "bug\""]
        # args[0].lower() == "suggest_fix" is true.
        # len(args) > 1 is true.
        # code_snippet = " ".join(args[1:]) -> "original code" "has a bug"
        # This test needs to be re-thought based on how cli.py actually parses.
        # The `ai suggest_fix` command in cli.py is:
        # elif command == "ai" and args and args[0].lower() == "suggest_fix":
        #    if len(args) == 3:  <-- This is the problem, it expects suggest_fix, then code, then issue
        #        code_snippet_arg = args[1]
        #        issue_description_arg = args[2]
        # The test input needs to be "ai suggest_fix code_snippet_one_word issue_desc_one_word"
        # Or the CLI needs to parse quoted strings. Given the current CLI parsing, I'll adapt the test.
        # The current CLI `ai suggest_fix` takes `args[0]` as `suggest_fix`, `args[1]` as code, `args[2]` as issue.
        # My previous diff for cli.py for suggest_fix was:
        # elif command == "ai" and args and args[0].lower() == "suggest_fix":
        #    if len(args) == 2: # Expecting code snippet and issue description as two separate arguments
        #        code_snippet = args[0] <--- This indicates it's after the "suggest_fix" part
        #        issue_description = args[1]
        # This means the `parts` would be `["ai", "suggest_fix", "code_snippet", "issue_description"]`
        # So `args` for the `ai` command becomes `["suggest_fix", "code_snippet", "issue_description"]`
        # Then `args[0].lower() == "suggest_fix"` is true.
        # `code_snippet = args[1]` and `issue_description = args[2]`
        # The input must be `ai suggest_fix "code snippet" "issue description"`
        # The parts split by space is: `ai`, `suggest_fix`, `"code`, `snippet"`, `"issue`, `description"`
        # So `args` to the `ai` branch is `["suggest_fix", "\"code", "snippet\"", "\"issue", "description\""]`
        # Then `code_snippet = args[1]` (which is `"\"code"`) and `issue_description = args[2]` (which is `"snippet\""`)
        # This is not right.
        # The code in cli.py `elif command == "ai" and args and args[0].lower() == "suggest_fix":`
        #   `if len(args) >= 3: # Expecting subcommand, code, and issue`
        #   `  code_snippet = args[1]`
        #   `  issue_description = " ".join(args[2:])`
        # This seems more plausible. Let's assume this.
        mock_input.side_effect = ["ai suggest_fix \"def main(): bug()\" \"fix this bug\"", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gemini_instance.suggest_code_modification.assert_called_once_with("def main(): bug()", "fix this bug")
        self.assertIn("--- Suggested Fix ---", output)
        self.assertIn("fixed code here", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_empty_result(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.suggest_code_modification.return_value = None
        mock_input.side_effect = ["ai suggest_fix code issue", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gemini_instance.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn("No code modification suggested or the response was empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_api_error(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.suggest_code_modification.side_effect = GeminiApiError("Fix API Error")
        mock_input.side_effect = ["ai suggest_fix code issue", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gemini_instance.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn("API Error: Fix API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_modification_error(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_gemini_instance.suggest_code_modification.side_effect = GeminiModificationError("Fix Mod Error")
        mock_input.side_effect = ["ai suggest_fix code issue", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        mock_gemini_instance.suggest_code_modification.assert_called_once_with("code", "issue")
        self.assertIn("Error suggesting fix: Fix Mod Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_not_enough_args(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        
        mock_input.side_effect = ["ai suggest_fix codeonly", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix \"<code_snippet>\" \"<issue_description>\"", output)
        
        self.mock_stdout.truncate(0) # Clear previous output
        self.mock_stdout.seek(0)
        mock_input.side_effect = ["ai suggest_fix", "exit"]
        run_cli()
        output2 = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix \"<code_snippet>\" \"<issue_description>\"", output2)
        
        mock_gemini_instance.suggest_code_modification.assert_not_called()

    # --- Tests for 'ai suggest_fix_file' command ---
    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_file_success(self, MockGeminiClient, MockGitHubClient, mock_local_read_file, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_local_read_file.return_value = "file content for fix"
        mock_gemini_instance.suggest_code_modification.return_value = "fixed file content"
        mock_input.side_effect = ["ai suggest_fix_file test.py \"fix this file\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_gemini_instance.suggest_code_modification.assert_called_once_with("file content for fix", "fix this file")
        self.assertIn("--- Suggested Fix ---", output)
        self.assertIn("fixed file content", output)

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_file_read_not_found(self, MockGeminiClient, MockGitHubClient, mock_local_read_file, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_local_read_file.side_effect = FileNotFoundError("No file for fix")
        mock_input.side_effect = ["ai suggest_fix_file non_existent.py \"fix it\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("non_existent.py")
        self.assertIn("Error: File not found: non_existent.py", output)
        mock_gemini_instance.suggest_code_modification.assert_not_called()

    @patch('builtins.input')
    @patch('jarules_agent.connectors.local_files.read_file')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_file_api_error(self, MockGeminiClient, MockGitHubClient, mock_local_read_file, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value
        mock_local_read_file.return_value = "file content"
        mock_gemini_instance.suggest_code_modification.side_effect = GeminiApiError("Fix File API Error")
        mock_input.side_effect = ["ai suggest_fix_file test.py \"fix issue\"", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_local_read_file.assert_called_once_with("test.py")
        mock_gemini_instance.suggest_code_modification.assert_called_once_with("file content", "fix issue")
        self.assertIn("API Error: Fix File API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_ai_suggest_fix_file_no_path_or_issue(self, MockGeminiClient, MockGitHubClient, mock_input):
        MockGitHubClient.return_value = MagicMock()
        mock_gemini_instance = MockGeminiClient.return_value

        mock_input.side_effect = ["ai suggest_fix_file", "exit"]
        run_cli()
        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix_file <filepath> \"<issue_description>\"", output)

        self.mock_stdout.truncate(0)
        self.mock_stdout.seek(0)
        mock_input.side_effect = ["ai suggest_fix_file path_only", "exit"]
        run_cli()
        output2 = self.mock_stdout.getvalue()
        self.assertIn("Usage: ai suggest_fix_file <filepath> \"<issue_description>\"", output2)
        
        mock_gemini_instance.suggest_code_modification.assert_not_called()

    # --- Tests for 'gh_ls' command ---
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_ls_success(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.list_repo_files.return_value = ['file1.py', 'README.md']
        mock_input.side_effect = ["gh_ls testowner/testrepo/docs", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.list_repo_files.assert_called_once_with(owner='testowner', repo='testrepo', path='docs')
        self.assertIn("Files in 'testowner/testrepo/docs':", output)
        self.assertIn("file1.py", output)
        self.assertIn("README.md", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_ls_success_no_path(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.list_repo_files.return_value = ['file2.py', 'LICENSE']
        mock_input.side_effect = ["gh_ls testowner/testrepo", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.list_repo_files.assert_called_once_with(owner='testowner', repo='testrepo', path='')
        self.assertIn("Files in 'testowner/testrepo/':", output) # Path becomes empty string, slash added in output
        self.assertIn("file2.py", output)
        self.assertIn("LICENSE", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_ls_empty_result(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.list_repo_files.return_value = []
        mock_input.side_effect = ["gh_ls owner/repo", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.list_repo_files.assert_called_once_with(owner='owner', repo='repo', path='')
        self.assertIn("No files or directories found in 'owner/repo/', or path is invalid/empty.", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_ls_api_error(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.list_repo_files.side_effect = Exception("GitHub API Error")
        mock_input.side_effect = ["gh_ls owner/repo", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.list_repo_files.assert_called_once_with(owner='owner', repo='repo', path='')
        self.assertIn("Error listing GitHub repository files: GitHub API Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_ls_invalid_arg_format(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_input.side_effect = ["gh_ls owneronly", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: gh_ls <owner>/<repo>[/<path>]", output)
        mock_gh_instance.list_repo_files.assert_not_called()

    # --- Tests for 'gh_read' command ---
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_read_success(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.read_repo_file.return_value = "File content from GitHub"
        mock_input.side_effect = ["gh_read owner/repo/path/to/file.txt", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.read_repo_file.assert_called_once_with(owner='owner', repo='repo', file_path='path/to/file.txt')
        self.assertIn("Content of 'owner/repo/path/to/file.txt':", output)
        self.assertIn("---", output)
        self.assertIn("File content from GitHub", output)
        self.assertEqual(output.count("---"), 2)


    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_read_file_not_found_or_error(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.read_repo_file.return_value = None # Simulate file not found or unreadable
        mock_input.side_effect = ["gh_read owner/repo/nofile.txt", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.read_repo_file.assert_called_once_with(owner='owner', repo='repo', file_path='nofile.txt')
        self.assertIn("Could not read file 'owner/repo/nofile.txt'.", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_read_api_error(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_gh_instance.read_repo_file.side_effect = Exception("GitHub API Read Error")
        mock_input.side_effect = ["gh_read owner/repo/file.txt", "exit"]

        run_cli()

        output = self.mock_stdout.getvalue()
        mock_gh_instance.read_repo_file.assert_called_once_with(owner='owner', repo='repo', file_path='file.txt')
        self.assertIn("Error reading GitHub repository file: GitHub API Read Error", output)

    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.GitHubClient')
    @patch('jarules_agent.ui.cli.GeminiClient')
    def test_gh_read_invalid_arg_format(self, MockGeminiClient, MockGitHubClientClass, mock_input):
        MockGeminiClient.return_value = MagicMock()
        mock_gh_instance = MockGitHubClientClass.return_value
        mock_input.side_effect = ["gh_read owner/repo", "exit"] # Missing file_path part

        run_cli()

        output = self.mock_stdout.getvalue()
        self.assertIn("Usage: gh_read <owner>/<repo>/<file_path>", output)
        mock_gh_instance.read_repo_file.assert_not_called()

if __name__ == '__main__':
    unittest.main()
