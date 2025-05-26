# JaRules - Your Async Development Agent 🤖

![JaRules Asynchronous Development Assistant](https://raw.githubusercontent.com/witchcraftery/jarules/main/jarules_title-card.jpg)

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

*   **Project Structure:** Solid foundation laid for `core`, `connectors`, `ui`, and `tests`.
*   **Local File System (`jarules_agent/connectors/local_files.py`):**
    *   List files and directories (`ls <path>`).
    *   Read file content (`read <path>`).
    *   Write content to files (`write <path> <content>`).
*   **GitHub Connector (`jarules_agent/connectors/github_connector.py`):**
    *   List files in public repositories (`gh_ls <owner>/<repo>[/<path>]`).
    *   Read file content from public repositories (`gh_read <owner>/<repo>/<file_path>`).
*   **AI API Placeholder (`jarules_agent/connectors/gemini_api.py`):** Basic structure for future Gemini integration.
*   **Command-Line Interface (`jarules_agent/ui/cli.py`):** Your current way to interact with JaRules!
*   **Dependencies (`requirements.txt`):** `requests` for GitHub API calls.
*   **Unit Tests (`jarules_agent/tests/`):** Ensuring `local_files.py` and `github_connector.py` are reliable. We even caught a bug with tests! 🐞➡️✅

## How to Run JaRules (CLI)

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

## Next Steps (The Road Ahead 🚀)

The vision for JaRules is rapidly taking shape! Recent planning has laid a detailed groundwork for several key areas. We're excited to move towards implementation:

*   **Implementing GitHub Write Operations:**
    *   **Goal:** Enable JaRules to actively manage GitHub repositories.
    *   **Planned Features:**
        *   Create new branches (e.g., for features, fixes).
        *   Commit one or more files with appropriate messages.
        *   Create pull requests to propose changes.
    *   **Details:** Method signatures in `github_connector.py` and new test cases have been outlined.

*   **Full Integration with the Gemini API:**
    *   **Goal:** Leverage Google's Gemini models for advanced AI-powered development assistance.
    *   **Planned Features:**
        *   **Code Generation:** Generate code from natural language prompts.
        *   **Interactive Code Refinement/Bug Fixing:** Suggest improvements and fixes for existing code.
        *   **Contextual Code Explanation:** Explain code snippets in natural language.
    *   **Details:** The API contract in `gemini_api.py`, API key management (via `GEMINI_API_KEY` environment variable), interaction with core agent logic, and specific test cases are planned.

*   **Expanding AI Connector Capabilities (Multi-LLM Support):**
    *   **Goal:** Make JaRules flexible by supporting various AI models, both cloud-based and local.
    *   **Planned Architecture:**
        *   A `BaseLLMConnector` abstract base class will define a common interface for all AI connectors.
        *   Initial focus on adapting `GeminiClient` to this interface.
        *   Future plans include connectors for Ollama (to run local models like CodeLlama, Llama 3, Mistral), Anthropic Claude, and potentially other specialized coding LLM APIs.
        *   The core agent will manage these connectors through a factory pattern and configuration settings.
    *   **Details:** The base class methods (e.g., `send_prompt`, `generate_code`, `explain_text`) and configuration management have been outlined.

*   **Developing the Chat User Interface (Electron App):**
    *   **Goal:** Create an intuitive and interactive desktop application for JaRules.
    *   **Technology:** Confirmed use of Electron, with Svelte or Vue.js recommended for the frontend.
    *   **Planned Features (Initial):**
        *   Message display area, multi-line text input, send button.
        *   Clear display of user inputs and agent responses (including syntax-highlighted code blocks with a copy function).
        *   Loading indicators for agent processing.
    *   **Communication Protocol:** IPC (Inter-Process Communication) between the Electron UI (renderer process) and the Python agent core (via Electron main process), using JSON messages.

*   **Towards an Implementation Guide:**
    *   Given the detailed planning, we are considering the development of a more comprehensive "Implementation Guide" or a series of focused development tasks to help contributors dive into these areas. Stay tuned for more details!

We're building a powerful assistant, and these next steps are crucial in bringing that vision to life. Contributions and feedback are welcome!
