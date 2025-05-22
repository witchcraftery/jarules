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

*   Implementing GitHub write operations (creating commits, branches, PRs).
*   Full integration with the Gemini API for code generation and assistance.
*   Expanding AI connector capabilities.
*   Developing the chat interface.
