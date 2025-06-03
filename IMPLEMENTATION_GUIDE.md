# JaRules Implementation Guide

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
7.  **`jarules_agent/tests/test_cli.py` Updated (Manual Task)**:
    *   The test suite for the CLI (`test_cli.py`) was manually updated to align with the new `LLMManager` architecture. This involved refactoring test setup, mock strategies (changing from `GeminiClient` to `LLMManager`), and ensuring all AI command tests correctly simulate the CLI's interaction with the `LLMManager` for obtaining LLM connector instances. This task was completed manually due to previous issues with automated tooling for this specific file.

---
Future sections can be added to this guide as new complex tasks arise.

## Phase: UI Development (Electron + Vue.js) - Roadmap

**Overall Goal:**
To develop an interactive desktop application for JaRules, providing a rich user experience similar to modern chat-based AI assistants but tailored for software development tasks. This includes capabilities for displaying conversations with the agent, viewing and navigating project files, examining code, and potentially interacting with other development-related outputs.

**Technology Stack Summary:**
*   **Framework:** Electron for the desktop application shell.
*   **UI Library:** Vue.js (version 3) for building the user interface components.
*   **Build Tool:** Vite for fast development and optimized builds of the Vue.js frontend.
*   **Main Process:** Node.js (as part of Electron).
*   **Communication:** IPC (Inter-Process Communication) between Electron's main and renderer processes; a chosen method (e.g., child process, local HTTP, ZeroMQ) for Electron-to-Python core communication.

---

### Phase 1: Basic Electron App with Vue.js Setup (Completed)

This foundational phase focused on establishing the project structure and core plumbing for the Electron-based UI.

**Key Achievements:**
*   Created the `jarules_electron_vue_ui` project directory.
*   Initialized `package.json` and installed all core dependencies: Electron, Vue.js 3, Vite, `@vitejs/plugin-vue`, and `concurrently`.
*   Configured Vite (`vite.config.js`) for Vue.js development.
*   Implemented the Electron main process script (`main.js`) to:
    *   Create and manage the main browser window.
    *   Handle application lifecycle events.
    *   Load content from Vite's dev server in development mode.
    *   Load built static files (from `dist/index.html`) in production mode.
    *   Integrate a `preload.js` script.
*   Created a basic Electron `preload.js` for context bridging (initially displaying version info).
*   Set up `index.html` as the host page for the Vue.js application, with a root `<div>` for Vue to mount.
*   Developed the Vue.js application entry point (`src/main.js`) to initialize and mount the root Vue component.
*   Created a simple root Vue component (`src/App.vue`) to display a welcome message and confirm integration.
*   Added NPM scripts to `package.json` for development (`dev`), building (`build:vite`), and running in a production-like environment (`start:prod`).
*   Established a comprehensive `.gitignore` file for the UI project.
*   Created `jarules_electron_vue_ui/README_UI.md` with setup, build, and run instructions, pointing to this guide for the detailed roadmap.

---

### Phase 2: Implement Core Chat UI & Functionality

This phase will focus on building the primary chat interface components.

**Planned Steps:**
*   **Chat Message Display:** Develop Vue components to render a list of chat messages, distinguishing between user prompts and agent responses.
*   **User Input:** Create a multi-line text input field for users to type their messages and a "Send" button.
*   **Basic IPC for Chat:**
    *   Implement IPC communication from the Vue.js renderer process (UI) to the Electron main process when the user sends a message.
    *   The Electron main process will initially receive the message and (for now) can send back a mocked or echo response via IPC to the renderer process.
*   **Message Rendering in UI:** Ensure sent messages and (mocked) responses are correctly displayed in the chat message area.
*   **Markdown Support:** Integrate a library (e.g., `marked.js` or similar) to render agent responses as Markdown, allowing for rich text formatting, links, lists, etc.
*   **Syntax Highlighting for Code Blocks:** Use a library (e.g., `highlight.js`, `prism.js`) to automatically detect and apply syntax highlighting to code blocks within Markdown-rendered agent responses.
*   **"Copy Code" Functionality:** Add a button to easily copy the content of code blocks displayed in the chat.
*   **Styling:** Apply initial styling to make the chat interface clean and usable.

---

### Phase 3: Integrate with Python Agent Core

Bridge the gap between the Electron UI and the existing Python-based JaRules agent.

**Planned Steps:**
*   **Communication Channel:**
    *   Research and select the most suitable method for robust communication between the Electron main process (Node.js) and the Python agent core. Options include:
        *   Managing the Python agent as a child process and using `stdin`/`stdout`.
        *   A local HTTP server/client setup (Python server, Electron client).
        *   A message queue system like ZeroMQ.
    *   Implement the chosen communication channel.
*   **Message Forwarding:**
    *   Relay user messages received via IPC in the Electron main process to the Python agent core through the established channel.
*   **Response Handling:**
    *   Receive responses from the Python agent in the Electron main process.
    *   Forward these responses to the Vue.js UI via IPC for display.
*   **Asynchronous Operations & UI State:**
    *   Implement UI indicators for when the agent is processing a request (e.g., loading spinners, disabled input).
    *   Handle potential errors or timeouts in communication.

---

### Phase 4: Develop File Explorer and Code Viewer Panes/Columns

Expand the UI beyond chat to include development-specific views, moving towards the multi-column vision.

**Planned Steps:**
*   **Multi-Column Layout Design:** Define and implement a basic multi-column or multi-pane layout structure for the application window (e.g., using CSS Flexbox/Grid or a UI component library).
*   **File Explorer Component:**
    *   Develop a Vue component to display a tree-like view of a project's file system.
    *   Initially, this might interact with a mocked file system or use Electron's capabilities to access a user-specified local directory.
    *   Allow navigation through directories and selection of files.
*   **Code Viewer Component:**
    *   Develop a Vue component to display the content of a file selected in the File Explorer.
    *   Integrate basic syntax highlighting for various programming languages in this viewer.
    *   (Future Consideration): Explore embedding a more powerful editor component like Monaco Editor (which powers VS Code) for richer features like inline diffs, better search, etc.
*   **Inter-Pane Communication:** Ensure that selecting a file in the explorer updates the content in the code viewer.

---

### Phase 5: State Management and Advanced Features

Refine the application, introduce robust state management, and explore more advanced SE tooling integrations.

**Planned Steps:**
*   **Global State Management:** Integrate a state management library like Pinia (the official Vue.js recommendation) to manage application-wide state, such as:
    *   Current chat history.
    *   Open files or tabs.
    *   User preferences and settings.
    *   Agent status.
*   **Additional UI Panes/Tools:** Based on the "four-column" vision, design and implement other useful panes:
    *   Terminal emulator.
    *   Test execution and results display.
    *   Task lists or issue tracking integration.
    *   Agent tool-specific UIs.
*   **User Settings:** Implement a way for users to configure settings (e.g., API keys if needed by UI, theme preferences).
*   **Theming:** Explore light/dark mode themes for the UI.
*   **Performance Optimization:** Profile and optimize UI rendering and communication pathways.
*   **Packaging & Distribution:** Set up Electron Forge or Electron Builder for creating distributable application packages for different operating systems.
