# JaRules - Implementation Plan

## Introduction

This document outlines the development plan for the JaRules project, an asynchronous development assistant. It tracks completed milestones and lists remaining tasks to achieve the project's goals.

## Overall Goal

To create an AI-powered development agent with a chat interface that can:
- Connect to local files and GitHub repositories.
- Integrate with AI APIs (Gemini and others).
- Assist with coding, bug fixing, feature requests, and other software engineering tasks.
- Export changes directly to GitHub.

## Completed Milestones

### Phase 0: Backend Foundation & CLI (`jarules_agent`)

*   **Project Setup:** Initial Python project structure for `jarules_agent`.
*   **Local File System Connector:**
    *   Implemented `list_files`, `read_file`, `write_file` in `connectors/local_files.py`.
    *   Added comprehensive unit tests in `tests/test_local_files.py`.
*   **GitHub Connector (Read-Only):**
    *   Implemented `list_repo_files`, `read_repo_file` in `connectors/github_connector.py` using the GitHub API.
    *   Added unit tests with API call mocking in `tests/test_github_connector.py`.
    *   Included `requests` in `requirements.txt`.
*   **AI API Placeholder:** Created `connectors/gemini_api.py` with a placeholder class.
*   **Command-Line Interface (CLI):**
    *   Developed `ui/cli.py` for interacting with local file and GitHub read operations.
    *   Updated `main.py` to launch the CLI.
*   **Initial Documentation:** Created the first version of `README.md`.

### Phase 1: GUI Development (`jarules_ui`) - Mocked Data Stage

*   **Minimal Electron App Setup:**
    *   Established the `jarules_ui` directory for the Electron application.
    *   Configured `package.json` with `electron` and basic start scripts.
    *   Created `main.js` for the Electron main process to load the UI.
*   **Static UI Shell (HTML/CSS):**
    *   Developed `index.html` with the core 4-panel layout (Chat History, Active Chat, File Viewer, File Explorer) and a top bar.
    *   Created `styles.css` to implement a dark mode theme, Flexbox/Grid panel arrangement, and purple accent colors.
*   **Vanilla JS Panels (Mocked Data Interaction):**
    *   **File Explorer (`file_explorer.js`):**
        *   Dynamically renders a mocked file system structure.
        *   Supports directory expansion/collapse and file selection.
    *   **File Viewer (`file_viewer.js`):**
        *   Displays mocked code content based on selection in the File Explorer.
        *   **Syntax Highlighting:** Integrated Prism.js (core, Okaidia theme, autoloader, and components for JS, Python, CSS, Markup). Vendor files for Prism.js included in `jarules_ui/vendor/prism/`.
    *   **Chat History (`chat_history.js`):**
        *   Displays a static list of mocked chat messages with distinct styling for user and agent.
    *   **Active Chat (`active_chat.js`):**
        *   Provides an input field and message display area.
        *   Handles sending user messages (Enter key or button click).
        *   Simulates mocked, delayed responses from JaRules to demonstrate interactivity.
*   **Frontend-Backend Linking Strategy:**
    *   Created `jarules_ui/communication_strategy.md` outlining various methods (IPC, HTTP, WebSockets) and providing an initial recommendation.

## Remaining High-Level Tasks (The Road Ahead)

### Phase 2: Backend API Development (Python - `jarules_agent`)

*   **Design Core API Endpoints:**
    *   Based on `communication_strategy.md` (likely FastAPI or Flask).
    *   Define schemas for requests and responses.
*   **Implement File System API:**
    *   Endpoints for local file operations (list, read, write) building upon existing `local_files.py`.
    *   Endpoints for GitHub file operations (list, read) building upon `github_connector.py`.
*   **Implement Chat Processing API:**
    *   Endpoint to receive user messages.
    *   Initial logic to echo messages or provide very simple canned responses.
*   **Implement GitHub Authentication:**
    *   Securely handle GitHub tokens for authenticated requests (needed for write operations and private repos).
*   **Basic Error Handling & Logging:** Implement robust error handling and logging for the backend.

### Phase 3: Frontend-Backend Integration

*   **Implement Communication Layer in Electron UI (`jarules_ui`):**
    *   Based on `communication_strategy.md` (e.g., functions to call Python API via `fetch` or Electron IPC).
*   **Connect File Explorer to Backend:**
    *   Fetch and display real file/directory listings from local and GitHub sources.
*   **Connect File Viewer to Backend:**
    *   Fetch and display real file content.
*   **Connect Chat Panels to Backend:**
    *   Send user messages from Active Chat panel to the Python backend.
    *   Receive responses from the backend and display them in Active Chat and update Chat History.
*   **Refine UI based on Real Data:** Adjust UI elements and interactions as needed when working with real data.

### Phase 4: Core AI Integration

*   **Full Gemini API Connector (`jarules_agent`):**
    *   Implement API calls to Gemini for code generation, explanation, bug fixing based on prompts.
    *   Handle API key management securely.
*   **Integrate AI into Chat Flow (`jarules_agent`):**
    *   Process user messages through the AI model via the Chat Processing API.
    *   Develop prompt engineering strategies for different SE tasks.
*   **Context Management:** Design how context (current files, chat history, user goals) is passed to the AI.
*   **Streaming Responses (Optional):** If AI supports it, stream responses to the UI for better perceived performance.

### Phase 5: GitHub Write Operations

*   **Backend Logic (`jarules_agent`):**
    *   Implement functions to create commits (using a library like `GitPython` or GitHub API).
    *   Implement functions to create branches and push changes.
    *   Handle potential conflicts or errors.
*   **Frontend UI (`jarules_ui`):**
    *   Add UI elements for initiating commits, selecting files for commit, writing commit messages.
    *   Provide feedback on the success/failure of GitHub operations.

### Phase 6: Advanced Features & Refinements

*   **Code Editing in File Viewer:** Explore integrating Monaco Editor or similar for actual code editing capabilities.
*   **User Settings:** UI and backend for managing settings (API keys, preferences).
*   **"Other AI" Connectors:** Abstract AI interaction to allow plugging in other models (e.g., local LLMs via Ollama).
*   **Testing:**
    *   Expand unit tests for backend API.
    *   Add integration tests for frontend-backend communication.
    *   Consider E2E tests for the UI.
*   **Error Handling & UI Feedback:** Comprehensive error display and user guidance.
*   **Performance Optimization:** For both frontend and backend.
*   **Deployment/Packaging:** Refine Electron packaging for distribution.

## Current Focus

*   **Backend API Development (`jarules_agent`):** Starting with core API endpoints for file system operations and basic chat.
*   **Initial Frontend-Backend Integration (`jarules_ui`):** Connecting the File Explorer and File Viewer to the new backend API.

```
