# Implementation Guide

This document provides guidance for ongoing development tasks, particularly those that may require manual intervention or were complex to achieve with current tooling.

## Phase: LLM Configuration and Management System (November 2023 - Current)

**Objective**: To introduce a flexible system for managing multiple Large Language Models (LLMs) and integrate the existing Gemini client into this new architecture.

### Completed Changes:

1.  **`config/llm_config.yaml` Created**:
    *   A new YAML file defining configurations for LLMs.
    *   Includes functional settings for `GeminiClient` (e.g., `gemini_flash_default`).
    *   Contains placeholder structures for future Ollama and OpenRouter integrations.
    *   Supports unique IDs, provider types, model names, API key environment variable names, default system prompts, and generation parameters.

2.  **`jarules_agent/core/llm_manager.py` Implemented**:
    *   New `LLMManager` class that loads and parses `llm_config.yaml`.
    *   Provides `get_llm_connector(config_id)` method to instantiate and return LLM connector instances based on configuration.
    *   Currently supports instantiating `GeminiClient`.
    *   Includes caching for loaded connectors and error handling for configuration issues.

3.  **`jarules_agent/connectors/gemini_api.py` Adapted**:
    *   `GeminiClient` constructor (`__init__`) updated to accept `api_key`, `default_system_prompt`, and `generation_params` directly.
    *   Prioritizes passed-in API key over environment variables.
    *   Uses configured default system prompts and generation parameters if no overriding values are provided in method calls.

4.  **`jarules_agent/ui/cli.py` Integrated with `LLMManager`**:
    *   CLI now instantiates `LLMManager`.
    *   Retrieves the active LLM client (currently hardcoded to use the "gemini_flash_default" configuration) via `llm_manager.get_llm_connector()`.
    *   Updated error handling for LLM initialization.

5.  **`jarules_agent/tests/test_llm_manager.py` Created**:
    *   New test suite for `LLMManager`, covering configuration loading, connector instantiation (for Gemini), and error handling.

6.  **`jarules_agent/tests/test_gemini_api.py` Reviewed**:
    *   Existing tests reviewed and deemed largely compatible with changes to `GeminiClient.__init__` due to its fallback mechanisms for API key handling.

### Pending Task: Updating `jarules_agent/tests/test_cli.py`

**Context**:
The introduction of `LLMManager` in `jarules_agent/ui/cli.py` means that the CLI no longer instantiates `GeminiClient` directly. Instead, it gets an LLM client instance from the `LLMManager`. Consequently, the unit tests in `test_cli.py` that test AI commands need to be updated to reflect this change in architecture.

**Problem Encountered**:
Automated tooling (`replace_with_git_merge_diff`, `overwrite_file_with_block`) has consistently failed to apply the necessary extensive modifications to `test_cli.py`. Even minimal diagnostic changes to this file also failed, suggesting a deeper issue with tool interaction for this specific file.

**Required Changes for `jarules_agent/tests/test_cli.py` (Manual or Future Tooling):**

1.  **Update Imports**:
    *   Add:
        ```python
        from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError
        from jarules_agent.connectors.base_llm_connector import BaseLLMConnector 
        # Keep existing Gemini-specific error imports if tests catch them directly
        ```

2.  **Update Mocking Strategy for AI Command Tests (and relevant setup tests)**:
    *   Tests that previously used `@patch('jarules_agent.ui.cli.GeminiClient')` should now use `@patch('jarules_agent.ui.cli.LLMManager')`.
    *   The mocked `LLMManager` class's `return_value` (representing the `LLMManager` instance) needs its `get_llm_connector` method to be mocked.
    *   This `get_llm_connector` mock should be configured to return a `MagicMock` instance that simulates an actual LLM client (e.g., `MagicMock(spec=GeminiClient)` or `MagicMock(spec=BaseLLMConnector)`).
    *   The methods of this inner LLM client mock (e.g., `generate_code`, `explain_code`) should then be configured for specific test assertions (return values, side effects like raising errors).

3.  **Example of Refactored Test Method Structure**:

    ```python
    # Inside TestCLI class in test_cli.py

    # Helper (if not already present or adapt existing setup for mocks)
    def _setup_cli_mocks(self, MockLLMManagerClass, MockGitHubClient, llm_client_spec=BaseLLMConnector, llm_model_name="mocked-model"):
        MockGitHubClient.return_value = MagicMock()
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        mock_active_llm_client = MagicMock(spec=llm_client_spec)
        if llm_model_name is not None: # model_name could be None if get_llm_connector fails
             mock_active_llm_client.model_name = llm_model_name
        mock_llm_manager_instance.get_llm_connector.return_value = mock_active_llm_client
        return mock_llm_manager_instance, mock_active_llm_client

    # Refactored startup test for API key error
    @patch('jarules_agent.ui.cli.LLMManager') 
    @patch('jarules_agent.ui.cli.GitHubClient') 
    def test_startup_llm_connector_error_handling(self, MockGitHubClient, MockLLMManagerClass): 
        MockGitHubClient.return_value = MagicMock() 
        mock_llm_manager_instance = MockLLMManagerClass.return_value
        # Simulate error during get_llm_connector call
        mock_llm_manager_instance.get_llm_connector.side_effect = GeminiApiKeyError("Test API Key Error from LLMManager path")
        
        run_cli() 
        
        output = self.mock_stdout.getvalue() 
        self.assertIn("API Key Error for LLM 'gemini_flash_default': Test API Key Error from LLMManager path", output) 
        self.assertIn("AI features will be unavailable.", output)
        self.assertNotIn("Successfully loaded LLM", output)

    # Refactored AI command test (example for gencode)
    @patch('builtins.input')
    @patch('jarules_agent.ui.cli.LLMManager')
    @patch('jarules_agent.ui.cli.GitHubClient')
    def test_ai_gencode_success(self, MockGitHubClient, MockLLMManagerClass, mock_input):
        # Use the helper to set up common mocks
        mock_llm_manager_instance, mock_llm_client = self._setup_cli_mocks(
            MockLLMManagerClass, MockGitHubClient, llm_client_spec=GeminiClient
        )
        
        mock_llm_client.generate_code.return_value = "def hello():\n  print('Hello Manager')"
        mock_input.side_effect = ["ai gencode \"python hello\"", "exit"] # User input
        
        run_cli() # Run the CLI main loop
        
        output = self.mock_stdout.getvalue()
        # Check that LLMManager was asked for the default connector
        mock_llm_manager_instance.get_llm_connector.assert_called_once_with("gemini_flash_default")
        # Check that the connector's method was called
        mock_llm_client.generate_code.assert_called_once_with("python hello")
        self.assertIn("--- Generated Code ---", output)
        self.assertIn("def hello():\n  print('Hello Manager')", output)
    ```

4.  **Specific Tests to Update (apply the above pattern to all these):**
    *   `test_startup_gemini_api_key_error` (should be renamed e.g. `test_startup_llm_manager_init_failure`)
    *   All tests for AI commands:
        *   `test_ai_gencode_success`
        *   `test_ai_gencode_empty_result`
        *   `test_ai_gencode_api_error`
        *   `test_ai_gencode_llm_connector_error` (newly added in the full test file attempt)
        *   `test_ai_gencode_generation_error`
        *   `test_ai_gencode_no_prompt`
        *   `test_ai_explain_success`
        *   `test_ai_explain_empty_result`
        *   `test_ai_explain_api_error`
        *   `test_ai_explain_explanation_error`
        *   `test_ai_explain_no_snippet`
        *   `test_ai_explain_file_success` (also needs `local_files.read_file` mock)
        *   `test_ai_explain_file_read_not_found`
        *   `test_ai_explain_file_api_error`
        *   `test_ai_explain_file_no_path`
        *   `test_ai_suggest_fix_success`
        *   `test_ai_suggest_fix_empty_result`
        *   `test_ai_suggest_fix_api_error`
        *   `test_ai_suggest_fix_modification_error`
        *   `test_ai_suggest_fix_not_enough_args`
        *   `test_ai_suggest_fix_file_success` (also needs `local_files.read_file` mock)
        *   `test_ai_suggest_fix_file_read_not_found`
        *   `test_ai_suggest_fix_file_api_error`
        *   `test_ai_suggest_fix_file_no_path_or_issue`
    *   Tests for non-AI commands (`ls`, `read`, `write`, `gh_ls`, `gh_read`) also need their `@patch('jarules_agent.ui.cli.GeminiClient')` changed to `@patch('jarules_agent.ui.cli.LLMManager')` and the mock setup adjusted to ensure the LLM part initializes quietly and doesn't interfere.

**Recommendation**:
Due to the tooling issues, these changes to `test_cli.py` should be applied manually or with alternative editing tools outside of this current interactive environment if the automated tools continue to fail. The file will be committed in its current (outdated) state, and this guide serves as the reference for the necessary updates.

---
Future sections can be added to this guide as new complex tasks arise.

### Detailed Plan for Updating `jarules_agent/tests/test_cli.py` (Generated 2024-03-11)

1. *Update imports in `jarules_agent/tests/test_cli.py`*:
    - Add `from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError`.
    - Add `from jarules_agent.connectors.base_llm_connector import BaseLLMConnector`.
2. *Update mocking strategy for AI command tests in `jarules_agent/tests/test_cli.py`*:
    - Change `@patch('jarules_agent.ui.cli.GeminiClient')` to `@patch('jarules_agent.ui.cli.LLMManager')`.
    - Mock the `get_llm_connector` method of the `LLMManager` instance to return a `MagicMock(spec=BaseLLMConnector)` or `MagicMock(spec=GeminiClient)`.
    - Configure the methods of this inner LLM client mock (e.g., `generate_code`, `explain_code`) for specific test assertions.
3. *Refactor test methods in `jarules_agent/tests/test_cli.py`*:
    - Implement the `_setup_cli_mocks` helper method as described in the implementation guide.
    - Update `test_startup_gemini_api_key_error` (renaming it to `test_startup_llm_manager_init_failure` or similar, e.g. `test_startup_llm_connector_error_handling` as per the guide's example).
    - Refactor all AI command tests (`test_ai_gencode_*`, `test_ai_explain_*`, `test_ai_suggest_fix_*`) using the new mocking strategy and helper method. This includes tests for success, empty results, API errors, connector errors, generation errors, and missing arguments/file issues.
    - Adjust non-AI command tests (`ls`, `read`, `write`, `gh_ls`, `gh_read`) to use `@patch('jarules_agent.ui.cli.LLMManager')` and ensure the LLM mock setup doesn't interfere.
4. *Run tests*:
    - After applying the changes, run the test suite to ensure all tests pass and the updates correctly reflect the new architecture.
5. *Submit the changes*:
    - Commit the updated `test_cli.py` and `IMPLEMENTATION_GUIDE.md` with a message describing the refactoring and the guide update.
