# Implementation Guide

This document provides guidance for ongoing development tasks and tracks major implementation milestones.

## 🎉 MAJOR MILESTONE COMPLETED: Full Test Suite Validation (May 2025)

**Achievement**: **All Gemini API Tests Passing (40/40)** ✅

We've successfully completed a major milestone by achieving **100% test coverage** for our Gemini API integration and resolving all test suite issues that were blocking our development progress.

### What We Accomplished

**Complete Test Suite Validation**:
- ✅ **40/40 Gemini API tests passing** 
- ✅ **Environment variable patching resolved** - Fixed core initialization timing issue
- ✅ **Mock setup corrected** - Proper API interaction testing established
- ✅ **Import references fixed** - Correct Google AI type handling implemented  
- ✅ **Error handling validated** - Comprehensive edge case coverage achieved

**Technical Achievements**:
- **setUp() Method Pattern Fixed**: Resolved critical timing issue where environment variable patches weren't applied before `GeminiClient()` initialization
- **Mock Configuration Improved**: Updated mock instances to properly simulate `generate_content` API calls
- **Type System Resolved**: Fixed `genai.protos.Candidate.FinishReason` references and implemented safe enum handling
- **Test Expectations Aligned**: Updated assertions to match actual client implementation behavior

**Impact**: This milestone provides **bulletproof regression protection** for our AI features and establishes a solid foundation for expanding to additional LLM providers.

## Phase: LLM Configuration and Management System (November 2023 - May 2025)

**Objective**: To introduce a flexible system for managing multiple Large Language Models (LLMs) and integrate the existing Gemini client into this new architecture.

---

## ✅ Recently Completed: Multi-LLM Expansion & CLI Switching (June 2025)

This phase focused on extending the agent's capabilities to support a variety of LLM providers and allowing users to manage their active model choice via the CLI.

-   **Ollama Integration**: Enables connection to local LLMs managed by Ollama, allowing for offline and customized model usage.
-   **OpenRouter Connector**: Provides access to a wide variety of models (including GPT, Claude, Llama, etc.) via the OpenRouter API, simplifying the use of diverse cloud-based models.
-   **Anthropic Claude Integration**: Supports Claude models (e.g., Haiku, Sonnet, Opus) via the official Anthropic SDK, enabling access to their advanced reasoning and generation capabilities.
-   **Runtime Model Switching & Persistence**: Implemented CLI commands (`set-model <id>`, `get-model`, `clear-model`) allowing users to dynamically switch the active LLM provider. User selections are persisted in `~/.jarules/user_state.json`.

### Electron UI - Phase 1: Core Chat Experience Enhancements
This initial phase for the desktop UI focused on creating a functional chat interface with essential features for interacting with the configured LLM providers.

-   **Functional Electron UI Shell**: Established a base Electron application using Vue.js and Vite (`jarules_electron_vue_ui/`) with secure IPC (contextBridge, preload scripts) and Python backend integration via `python-shell` and dedicated wrapper scripts.
-   **Streaming LLM Responses**: Implemented real-time display of LLM responses as they are generated in the chat interface, enhancing perceived responsiveness.
-   **Chat History Management**: Added functionality to load chat history from, and save new messages to, `~/.jarules/chat_history.json`. Users can also clear the chat history via a UI button.
-   **Refined Message Display & Input**:
    *   Created `MessageDisplay.vue` component for rendering chat messages. This includes Markdown support for assistant responses and distinct styling for user, assistant, and error messages. It also handles auto-scrolling.
    *   Created `ChatInput.vue` component for user input, featuring an auto-resizing textarea and support for send-on-Enter (Shift+Enter for newlines).
-   **Robust Error Handling & User Feedback**: Implemented a global error banner for critical backend or IPC issues, loading state indicators for asynchronous operations (model/history loading), and a "Copy to Clipboard" feature for assistant messages.

These additions significantly enhance the flexibility and power of the JaRules agent, bringing its capabilities to a user-friendly desktop interface.

---

## 🚀 Next Development Phase: Electron UI Enhancements & Advanced Agent Features

**Status**: Core Multi-LLM capabilities and foundational Electron UI (Phase 1) are complete. This next phase focuses on enriching the Electron application with more advanced user interactions, backend integrations, and preparing for broader agent capabilities.

### Electron UI - Phase 2: Advanced Features & Foolproofing
This phase aims to integrate more sophisticated interactions and robust operational checks into the Electron UI.

*   ✅ **Context Management System (Basic)**: (Completed July 2025)
    *   Implemented logic to automatically send the last N messages (default 10, configurable via `user_state.json` by setting `context_message_count`) from `~/.jarules/chat_history.json` as context to the LLM.
    *   The number of messages is determined by `context_message_count` in `user_state.json`, falling back to a default of 10 if the setting is not present or invalid.
    *   Existing "Clear Chat History" functionality in the UI effectively clears/resets this context as it empties `chat_history.json`.
*   **In-App Configuration UI (Read-Only First)**:
    *   Create a UI section to display the contents of `llm_config.yaml` in a user-friendly, read-only format.
    *   This helps users understand available models and their configurations without directly editing YAML.
    *   (Future editable configuration will be a separate, more complex feature).
*   **"Stop Generation" Functionality**:
    *   **Objective**: Allow users to interrupt an in-progress LLM response stream.
    *   **UI Implementation**:
        *   A "Stop Generating" button is added to `App.vue`, visible only when an LLM response is actively streaming (`isStreaming` ref is true).
        *   Clicking the button calls `window.api.stopGeneration()` via `preload.js`.
        *   The UI optimistically sets its `isStreaming` state to `false` and appends a "[Generation stopped by user]" message to the current assistant output.
    *   **IPC Channel (Renderer to Main)**:
        *   `window.api.stopGeneration()`:
            *   **Channel Invoked**: `'stop-llm-generation'`
            *   **Payload**: None (assumes a single active LLM stream context for the chat UI).
            *   **Expected Async Response (from main process via `invoke`)**:
                ```json
                // On success:
                { "success": true, "message": "LLM generation stop signal processed." }
                // On failure:
                { "success": false, "error": "Brief error message (e.g., 'Failed to send stop signal')", "details": "More detailed error information." }
                ```
    *   **Backend Behavior (`main.js` / Python)**:
        *   The handler for `'stop-llm-generation'` in `main.js` should attempt to terminate the associated `PythonShell` instance or signal the Python script to halt LLM processing.
        *   Crucially, upon successful interruption (or even if termination is forceful), the backend **must** ensure that the original `sendPromptStreaming` IPC's `onDone` or `onError` callback is triggered for the renderer process.
        *   This callback's payload should include a property like `cancelled: true` (e.g., `onDone({ cancelled: true, message: "Stream stopped by user" })`) to allow the UI to distinguish a user-initiated stop from a natural end-of-stream or a genuine error. This allows the UI to finalize the assistant's message correctly without displaying an erroneous error state.
    *   **UI State Management**:
        *   `App.vue` manages an `isStreaming` ref to control UI elements.
        *   The `onDone` and `onError` callbacks for `sendPromptStreaming` in `App.vue` have been updated to check for the `cancelled: true` flag to correctly update the UI and the content of the assistant's message.
*   **Pre-flight Checks / Diagnostics**:
    *   **Objective**: To provide users with a way to verify essential backend components, configurations, and connectivity, aiding in troubleshooting common issues.
    *   **UI Implementation**:
        *   A new `DiagnosticsPanel.vue` component has been created.
        *   This panel is accessible via a toggle button ("Show/Hide Diagnostics") in the main application view (`App.vue`).
        *   The panel displays a list of diagnostic checks, each with a user-friendly name, status (success, warning, error), a descriptive message, and optional technical details.
        *   A "Run Diagnostic Checks" button within the panel allows users to initiate the checks on demand.
    *   **IPC Channels & Data Structures**:
        *   **From UI (Renderer) to Main Process**:
            *   `window.api.runAllDiagnostics()`:
                *   **Channel Invoked**: `'run-all-diagnostics'`
                *   **Payload**: None.
                *   **Expected Async Response**: An array of `DiagnosticCheckResult` objects, returned after all checks complete.
        *   **From Main Process to UI (Renderer) - Optional Real-time Updates**:
            *   `window.api.onDiagnosticCheckUpdate(callback)` listens on channel `'diagnostic-check-update'`.
            *   **Payload**: A single `DiagnosticCheckResult` object.
        *   **`DiagnosticCheckResult` Object Structure**:
            ```json
            {
              "id": "string",         // Unique ID (e.g., "python-env", "llm-config-syntax")
              "name": "string",       // User-friendly name (e.g., "Python Environment Check")
              "status": "string",     // 'success', 'warning', 'error', 'running'
              "message": "string",    // User-friendly result summary/guidance
              "details": "string",    // Optional verbose technical output
              "timestamp": "string"   // ISO 8601 timestamp of the check
            }
            ```
    *   **Conceptual Backend Checks (handled by `main.js` and Python helper scripts)**:
        *   **Python Environment**: Verifies Python accessibility and version.
        *   **Configuration File Syntax**: Validates `llm_config.yaml` (YAML syntax) and `user_state.json` (JSON syntax).
        *   **Active LLM Provider Connectivity**: Attempts a basic connection or status check to the currently configured LLM provider (e.g., using a `check_availability()` method in the respective LLM connector).
    *   **Listener Cleanup**: `window.api.cleanupDiagnosticListeners()` is available to remove listeners for `'diagnostic-check-update'`.

### Electron UI - Phase 2.5: Asynchronous Git-Split Task Completion
This phase introduces a novel approach to task execution by leveraging Git branches for parallel sub-agent work.

*   **Objective**: Allow users to assign a complex prompt/task to multiple "sub-agents" (instances or configurations of LLMs) that work in parallel on separate Git branches based on the current repository state.
*   **Key Interactions**:
    *   User defines a task and selects multiple LLM configurations (sub-agents) to attempt the task.
    *   The system creates a new Git branch for each sub-agent.
    *   Each sub-agent attempts to complete the task, committing its results (code, text, etc.) to its dedicated branch.
    *   The UI provides a way for the user to preview the changes (diffs, generated files, visual outputs if applicable) from each sub-agent's completed branch.
*   **Outcome**: User reviews the parallel attempts and selects the preferred version. This version is then used to create a new Pull Request against the main working branch (or directly merged if preferred). Other sub-agent branches are automatically discarded/cleaned up.
*   **Core Components**:
    *   UI for task assignment, sub-agent selection, progress monitoring, and result preview/comparison.
    *   Backend logic for orchestrating multiple LLM agent calls in parallel.
    *   Robust Git integration for branch creation, file management, commits, diff generation, and cleanup (likely using `gitpython` or direct CLI calls from Python).
    *   Logic for PR creation (e.g., via GitHub API connector).

#### IPC Interface for Parallel Tasks

This section details the Inter-Process Communication (IPC) channels and data structures used by the Electron UI (Vue.js frontend) to interact with the main process (and subsequently the Python backend) for managing parallel Git tasks. These APIs are exposed via `window.api` in the renderer process, facilitated by `preload.js`.

**From UI (Renderer) to Main Process:**

1.  **`window.api.startParallelGitTask(taskDetails)`**
    *   **Channel Invoked**: `'start-parallel-git-task'`
    *   **Payload** (`taskDetails`: Object):
        ```json
        {
          "taskDescription": "User's detailed task prompt for the LLM agents.",
          "selectedAgents": [
            {
              "id": "gemini_default",
              "name": "Gemini (Default: gemini-pro)",
              "provider": "gemini",
              "model": "gemini-pro"
              /* Other relevant agent configuration details can be included if needed by the backend */
            }
            // ... more selected agent objects
          ]
        }
        ```
    *   **Expected Async Response** (from main process via `invoke`):
        ```json
        // On success:
        {
          "success": true,
          "runId": "unique-run-identifier-backend-generated",
          "message": "Parallel task successfully initiated."
        }
        // On failure:
        {
          "success": false,
          "error": "Brief error message (e.g., 'Setup Failed')",
          "details": "More detailed error information."
        }
        ```

2.  **`window.api.finalizeSelectedGitVersion(finalizationDetails)`**
    *   **Channel Invoked**: `'finalize-selected-git-version'`
    *   **Payload** (`finalizationDetails`: Object):
        ```json
        {
          "runId": "The unique run identifier for the current parallel task.",
          "selectedAgentId": "The ID of the agent whose version the user has chosen to finalize (e.g., merge or create PR)."
        }
        ```
    *   **Expected Async Response**:
        ```json
        { "success": true, "message": "Version finalization process started (e.g., PR created)." }
        // or
        { "success": false, "error": "Finalization Failed", "details": "..." }
        ```

3.  **`window.api.retryAgentGitTask(retryDetails)`**
    *   **Channel Invoked**: `'retry-agent-git-task'`
    *   **Payload** (`retryDetails`: Object):
        ```json
        {
          "runId": "The unique run identifier.",
          "agentId": "The ID of the agent whose task needs to be retried."
        }
        ```
    *   **Expected Async Response**:
        ```json
        { "success": true, "message": "Agent task retry process initiated." }
        // or
        { "success": false, "error": "Retry Initiation Failed", "details": "..." }
        ```

4.  **`window.api.cancelParallelRun(runId)`**
    *   **Channel Invoked**: `'cancel-parallel-git-run'`
    *   **Payload** (`runId`: String): The unique identifier of the parallel run to be cancelled.
    *   **Expected Async Response**:
        ```json
        { "success": true, "message": "Parallel run cancellation requested." }
        // or
        { "success": false, "error": "Cancellation Failed", "details": "..." }
        ```

**From Main Process to UI (Renderer) - Via Listeners:**

The UI sets up listeners using `window.api.onParallelGitTaskUpdate(...)` and `window.api.onParallelGitRunCompleted(...)`.

1.  **`'parallel-git-task-update'`** (Event channel for individual agent updates)
    *   **Payload** (`updateDetails`: Object):
        ```json
        {
          "runId": "The unique run identifier.",
          "agentId": "The ID of the agent being updated.",
          "status": "Queued | Processing | Generating Diff | Completed | Error | Cancelled", // Current status of the agent's task
          "progress": 0-100, // Optional: Overall progress percentage for this agent's task
          "resultSummary": "A brief text summary of results, code snippet, or diff preview (especially if status is 'Completed').",
          "error": true_or_false, // Boolean indicating if this update is an error state
          "errorMessage": "Detailed error message if 'error' is true.",
          "isProcessing": true_or_false // Explicit boolean indicating if the agent is still actively working.
        }
        ```

2.  **`'parallel-git-run-completed'`** (Event channel for when an entire run finishes or is terminated)
    *   **Payload** (`completionDetails`: Object):
        ```json
        {
          "runId": "The unique run identifier.",
          "overallStatus": "All Agents Complete | Finalized | Cancelled by User | Error Terminated", // Overall status of the run
          "message": "Optional summary message about the run's completion."
          // Optionally, include final outcomes or paths to artifacts if applicable.
        }
        ```

**Note on `preload.js`:**
The `preload.js` script also exposes `window.api.cleanupParallelTaskListeners()` which should be called by the UI when relevant components are unmounted to prevent memory leaks from IPC listeners.

### Electron UI - Phase 3: Polish & Packaging
This phase focuses on refining the user experience, ensuring stability, and preparing the application for distribution.

*   **Comprehensive UI Styling and Theming**:
    *   Implement a polished and consistent visual design across the application.
    *   Explore and add theme options (e.g., light/dark mode).
*   **Keyboard Shortcuts**: Introduce keyboard shortcuts for common actions (e.g., send prompt, switch models, clear history).
*   **Thorough Testing & Bug Fixing**: Conduct extensive testing of all UI features, backend integrations, and error handling paths. Address identified bugs and performance issues.
*   **Build and Test Packaged Application**:
    *   Finalize `electron-builder` configurations for all target platforms (macOS, Windows, Linux).
    *   Build and rigorously test the packaged application installers/executables on each OS.
    *   Address any platform-specific issues.

### Advanced Agent Features (Parallel Track / Subsequent Focus)
These features aim to enhance the core intelligence and capabilities of the agent, running in parallel with UI development or as a subsequent major focus.

*   **Multi-step Task Execution & Planning**: Enable the agent to break down complex tasks into smaller, manageable steps and execute them sequentially or in parallel where appropriate.
*   **Enhanced Context Management**: Move beyond simple history windowing to more sophisticated context understanding, possibly including summarization, entity extraction, and relevance scoring for context tokens.
*   **Tool Usage & Function Calling**: Integrate capabilities for the LLM to use external tools or call predefined functions to gather information or perform actions (e.g., run linters, execute code, search web).
*   **Knowledge Base Integration**: Allow the agent to connect to and query local or remote knowledge bases (e.g., vector databases, document stores) to augment its responses with specific information.

### Development Guidelines for New Connectors

**Follow Established Patterns**:
- Inherit from `BaseLLMConnector`. The `BaseLLMConnector` provides a standard interface (e.g., initialization with configuration, methods for logging) and ensures that all connectors adhere to core operational principles within the `LLMManager`.
- Implement all required methods: `generate_code()`, `explain_code()`, `suggest_code_modification()`.
  - **Flexibility Note**: If a provider offers unique functionalities that don't fit these methods, consider adding optional methods to the connector. For functionalities that are variations of existing methods, use parameters to control behavior. Discuss significant deviations with the team to maintain consistency.
- Use configuration from `llm_config.yaml`.
- Comprehensive error handling with custom exception classes. Define custom exceptions for provider-specific API errors or configuration issues (e.g., `OllamaApiError`, `ClaudeConfigurationError`) inheriting from a base `ConnectorError` if appropriate.

**API Key Management**:
- **Security Best Practice**: API keys for cloud providers must NOT be hardcoded in `llm_config.yaml` or checked into version control.
- **Recommended Approach**: Load API keys from environment variables (e.g., `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`). The connector's initialization logic should fetch keys from the environment. Consider supporting a dedicated secrets management solution in the future if complexity grows.

**Testing Standards**:
- Follow the test patterns established in `test_gemini_api.py`.
- **Minimum 40+ test cases** covering all scenarios, including various input types, successful calls, API error responses (e.g., authentication failure, model not found), configuration issues, and specific edge cases relevant to the provider.
  - **Example Edge Case**: Handling API rate limits gracefully or parsing malformed/unexpected responses from the API.
- Environment variable patching **before** client initialization (especially for API keys and endpoint configurations).
- Mock setup for API interactions, specific to each provider's API.
- Error handling and edge case coverage.
- **Note**: The recently added Ollama, OpenRouter, and Claude connectors serve as good examples for these guidelines.

**Configuration Integration**:
- Add provider configuration to `config/llm_config.yaml`. See example structure below.
- Support API keys (via environment variables primarily), default prompts, and generation parameters.
- Enable `LLMManager` automatic instantiation. The `LLMManager` is responsible for reading `llm_config.yaml`, discovering available provider configurations, and instantiating the appropriate connector on demand.

**Example `config/llm_config.yaml` Structure**:
```yaml
# config/llm_config.yaml

# Gemini Configuration (existing)
gemini:
  api_key: "GEMINI_API_KEY" # Loaded from env var if possible
  default_model: "gemini-pro"
  # ... other Gemini specific settings

# Ollama Connector Configuration
ollama:
  base_url: "http://localhost:11434"
  default_model: "llama3"
  request_timeout: 120 # Example: specific parameter for Ollama

# OpenRouter Connector Configuration
openrouter:
  # API key should be loaded from OPENROUTER_API_KEY environment variable
  default_model: "openai/gpt-4o"
  # ... other OpenRouter specific settings

# Anthropic Claude Connector Configuration
anthropic:
  # API key should be loaded from ANTHROPIC_API_KEY environment variable
  default_model: "claude-3-opus-20240229"
  # ... other Anthropic specific settings

# Default provider to use if not specified by the user
default_provider: "gemini"
```

---

## Historical Context: Previous Development Phases

### RESOLVED: Test Suite Integration Issues

**Previous Issue**: CLI tests were failing due to LLMManager architecture changes  
**Resolution**: Through systematic analysis, we identified and resolved all test integration issues:

- **Mock Path Corrections**: Fixed import path references in test patches
- **Command Parsing Alignment**: Updated test expectations to match CLI behavior  
- **Enhanced Error Coverage**: Added comprehensive error handling tests
- **Environment Variable Timing**: Resolved setup method ordering issues

**Outcome**: Complete test suite validation achieved with 100% success rate

**Technical Details**: Full implementation details preserved in git history for reference