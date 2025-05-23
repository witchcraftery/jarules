# JaRules - Your Async Development Agent 🤖

## Overview

JaRules is an asynchronous development assistant designed to streamline your software engineering tasks. It connects to your local file system, GitHub repositories, and various AI APIs (starting with Gemini). Through an intuitive interface (initially CLI, evolving to a chat-based UI), JaRules aims to help you write code, tackle bugs, manage features, and more!

## Current Status

🚧 Under Active Development 🚧

## Broad Original Plan (The Vision)

*   Core Asynchronous Agent Logic
*   Seamless Local File System Interaction
*   Comprehensive GitHub Integration (Read & Write)
*   Flexible AI Model Connectors (Gemini, Localhost, etc.)
*   Interactive Chat User Interface
*   Intelligent Task Processing for SE Tasks

## Progress So Far (What's Built! ✨)

### Python Agent (`jarules_agent`)
*   **Project Structure:** Solid foundation laid for `core`, `connectors`, `ui` (CLI), and `tests`.
*   **Local File System (`jarules_agent/connectors/local_files.py`):**
    *   List files and directories (`ls <path>`).
    *   Read file content (`read <path>`).
    *   Write content to files (`write <path> <content>`).
*   **GitHub Connector (`jarules_agent/connectors/github_connector.py`):**
    *   List files in public repositories (`gh_ls <owner>/<repo>[/<path>]`).
    *   Read file content from public repositories (`gh_read <owner>/<repo>/<file_path>`).
*   **AI API Placeholder (`jarules_agent/connectors/gemini_api.py`):** Basic structure for future Gemini integration.
*   **Command-Line Interface (`jarules_agent/ui/cli.py`):** Your current way to interact with the Python agent!
*   **Dependencies (`requirements.txt`):** `requests` for GitHub API calls.
*   **Unit Tests (`jarules_agent/tests/`):** Ensuring `local_files.py` and `github_connector.py` are reliable. We even caught a bug with tests! 🐞➡️✅

### Electron GUI (`jarules_ui`)
*   **Electron Shell:** Minimal Electron application setup established in the `jarules_ui` directory.
*   **Static UI Shell:** HTML and CSS define a 4-panel layout (Chat History, Active Chat, File Viewer, File Explorer) featuring a dark mode theme with purple accents.
*   **Vanilla JS Panels (Mocked Data):**
    *   **File Explorer:** Dynamically renders a file tree from mocked data, supports directory expansion/collapse, and file selection.
    *   **File Viewer:** Displays content of files selected in the explorer, with syntax highlighting provided by Prism.js (Okaidia theme, supporting Python, JS, CSS, Markup/HTML).
    *   **Chat History:** Displays a mocked conversation history.
    *   **Active Chat:** Allows users to type and send messages, which appear in the chat display, and simulates replies from JaRules.
*   **Vendor Assets:** Prism.js library files (core, theme, autoloader, and language components) are included in `jarules_ui/vendor/`.
*   **Frontend-Backend Strategy:** A `jarules_ui/communication_strategy.md` document has been created, outlining methods and recommending an initial approach for frontend (Electron JS) to backend (Python) communication.

## How to Run JaRules

### Python Agent CLI (`jarules_agent`)

1.  **Clone the repository** (Details will be added once the repo is public).
2.  Navigate to the project root directory (where `requirements.txt` is located).
3.  **Set up a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Run the CLI:**
    ```bash
    python -m jarules_agent.main
    ```
    (Alternatively, from the project root: `python jarules_agent/main.py`)
6.  Type `help` in the JaRules CLI to see available commands!

### GUI (Electron App - `jarules_ui`)

1.  Navigate to the `jarules_ui` directory:
    ```bash
    cd jarules_ui
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Run the Electron application:**
    ```bash
    npm start
    ```
    This will typically compile TypeScript (if applicable for future React version) and launch the Electron app.
    *Note: The GUI currently uses mocked data for its interactive panels.*

## Next Steps (The Road Ahead 🚀)

*   **Backend Development for GUI:**
    *   Develop Python backend API endpoints as outlined in `communication_strategy.md`.
    *   Connect the Electron GUI to this Python backend, replacing mocked data with real data and functionality.
*   **Full AI Integration:**
    *   Complete the integration with the Gemini API (or other chosen AI models) for code generation, analysis, and other assistance features.
*   **GitHub Write Operations:** Implement functionalities like creating/committing files, managing branches, and creating Pull Requests via the GitHub connector.
*   **Enhanced UI/UX:**
    *   Refine the chat interface with more features (e.g., message streaming, "typing" indicators, better error display).
    *   Improve the file explorer and viewer capabilities.
*   **Core Agent Logic:** Build out the core asynchronous task management and execution logic within the Python agent.
*   **Testing:** Expand unit and integration tests for both the Python agent and the GUI.

```
