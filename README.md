# JaRules - Your Async Development Agent 🤖

![JaRules Asynchronous Development Assistant](https://raw.githubusercontent.com/witchcraftery/jarules/main/jarules_title-card.jpg)

## Overview

JaRules is an asynchronous development assistant designed to streamline your software engineering tasks. It connects to your local file system, GitHub repositories, and various AI APIs (starting with Gemini). Through an intuitive interface (initially CLI, evolving to a chat-based UI), JaRules aims to help you write code, tackle bugs, manage features, and more!

## Current Status

🔧 **LLM Architecture Complete - Test Fixes Ready for Implementation**

## Recent Development Status (May 2025)

### ✅ **COMPLETED: LLM Configuration System**

- **LLMManager Architecture**: Flexible multi-LLM support system implemented
- **Configuration Management**: YAML-based LLM configuration with `config/llm_config.yaml`
- **Gemini Integration**: Fully integrated with configurable parameters
- **CLI Integration**: Updated to use LLMManager for AI operations
- **Core Tests**: LLMManager and Gemini connector tests passing

### 🔧 **CURRENT TASK: Test Suite Fixes**

**Status**: **Solution Identified and Tested - Ready for Implementation**

**Issue**: `test_cli.py` tests failing due to LLMManager architecture changes
**Root Cause**: Mock patch paths and command parsing expectations need updates  
**Solution**: Comprehensive fixes identified and validated through testing
**Time Estimate**: 15-30 minutes of manual application

**Blocking Issues Resolved**:

- ✅ Mock path corrections: `@patch('jarules_agent.ui.cli.GitHubClient')` → `@patch('jarules_agent.connectors.github_connector.GitHubClient')`
- ✅ Command parsing fixes: Update test expectations to match CLI argument handling
- ✅ Missing error coverage: Additional tests for comprehensive error handling

**Implementation Status**: Fixes ready to apply to `jarules_agent/tests/test_cli.py`

### 📋 **NEXT STEPS: Multi-LLM Expansion**

- Ollama integration for local models
- OpenRouter connector for cloud model diversity
- Anthropic Claude support
- Runtime model switching capabilities

## Progress So Far (What's Built! ✨)

### **Core Architecture**

- **Project Structure:** Solid foundation with `core`, `connectors`, `ui`, and `tests`

- **LLM Management System**: Flexible architecture supporting multiple AI providers
- **Configuration System**: YAML-based configuration for easy LLM provider management

### **Local File System (`jarules_agent/connectors/local_files.py`)**

- List files and directories (`ls <path>`)

- Read file content (`read <path>`)
- Write content to files (`write <path> <content>`)

### **GitHub Connector (`jarules_agent/connectors/github_connector.py`)**

- **Read Operations:**
  - `list_repo_files(owner, repo, path)`: Lists files and directories in a repository path
  - `read_repo_file(owner, repo, file_path)`: Reads the content of a file from a repository

- **Write Operations:**
  - `create_branch(owner, repo, new_branch_name, source_branch_name)`: Creates a new branch from a source branch
  - `commit_files(owner, repo, branch_name, file_changes, commit_message)`: Commits one or more file changes to a branch
  - `create_pull_request(owner, repo, head_branch, base_branch, title, body)`: Creates a new pull request

### **AI Integration (`jarules_agent/connectors/gemini_api.py`)**

- **LLMManager Integration**: Configurable Gemini client via LLMManager

- **Core AI Functions:**
  - `generate_code(user_prompt, system_instruction)`: Generates code based on prompts
  - `explain_code(code_snippet, system_instruction)`: Explains code snippets
  - `suggest_code_modification(code_snippet, issue_description, system_instruction)`: Suggests code improvements
- **Configuration Support**: API key management, default system prompts, generation parameters

### **Command-Line Interface (`jarules_agent/ui/cli.py`)**

- **LLMManager Integration**: Uses LLMManager for AI operations

- **Available Commands:**
  - **File Operations**: `ls`, `read`, `write`
  - **GitHub Operations**: `gh_ls`, `gh_read`
  - **AI Operations**: `ai gencode`, `ai explain`, `ai explain_file`, `ai suggest_fix`, `ai suggest_fix_file`
  - **Utility**: `help`, `exit`

### **Testing Suite**

- **Core Component Tests**: LLMManager, Gemini API, local files, GitHub connector

- **Integration Tests**: CLI component testing (fixes in progress)
- **Error Handling**: Comprehensive error scenario coverage

## How to Run JaRules (CLI)

1. **Clone the repository**:

    ```bash
    git clone https://github.com/witchcraftery/jarules.git
    cd jarules
    ```

2. **Set up a virtual environment (recommended)**:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up Gemini API key** (for AI features):

    ```bash
    export GEMINI_API_KEY="your_gemini_api_key_here"
    ```

5. **Run the CLI**:

    ```bash
    python -m jarules_agent.main
    ```

    (Alternatively: `python jarules_agent/main.py`)

6. **Type `help`** in the JaRules CLI to see available commands!

## Testing

### **Run All Tests**

```bash
# Full test suite
python -m pytest jarules_agent/tests/ -v

# Specific test file
python -m pytest jarules_agent/tests/test_llm_manager.py -v
```

### **Current Test Status**

- ✅ **LLMManager tests**: All passing
- ✅ **Gemini API tests**: All passing  
- ✅ **Local files tests**: All passing
- ✅ **GitHub connector tests**: All passing
- 🔧 **CLI tests**: Fixes ready for implementation (see IMPLEMENTATION_GUIDE.md)

## Development Status & Next Steps

### **Immediate Priority (Current Task)**

1. **Apply test_cli.py fixes** - Solution ready, manual implementation required
2. **Validate complete test suite** - Ensure all tests pass with LLMManager architecture
3. **Update documentation** - Reflect completed LLM architecture

### **Near-term Development (Next 1-2 weeks)**

1. **Ollama Integration**: Add support for local models (CodeLlama, Llama 3, Mistral)
2. **OpenRouter Connector**: Enable access to diverse cloud models
3. **Runtime Model Switching**: Allow users to switch between LLM providers in CLI

### **Medium-term Goals (Next month)**

1. **Anthropic Claude Support**: Add Claude API integration
2. **Enhanced CLI**: Improved user experience and command structure
3. **Configuration UI**: Web-based configuration management

### **Long-term Vision**

1. **Chat User Interface**: Electron-based desktop application
2. **Advanced Agent Capabilities**: Multi-step task execution
3. **Plugin System**: Extensible connector architecture

## Contributing

We're actively developing JaRules and welcome contributions!

### **Current Contribution Opportunities**

- **Test Implementation**: Help apply the test_cli.py fixes
- **New LLM Connectors**: Implement support for additional AI providers
- **Documentation**: Improve guides and API documentation
- **Feature Development**: Work on CLI enhancements and new capabilities

### **Development Setup**

1. Fork and clone the repository
2. Set up development environment as described above
3. Run tests to ensure everything works
4. Check `IMPLEMENTATION_GUIDE.md` for detailed development tasks

## Architecture

JaRules follows a modular architecture:

```
jarules_agent/
├── core/               # Core logic and management
│   └── llm_manager.py  # LLM provider management
├── connectors/         # External service integrations
│   ├── local_files.py  # File system operations
│   ├── github_connector.py  # GitHub API integration
│   ├── gemini_api.py   # Google Gemini integration
│   └── base_llm_connector.py  # LLM connector interface
├── ui/                 # User interfaces
│   └── cli.py          # Command-line interface
├── tests/              # Test suite
└── config/             # Configuration files
    └── llm_config.yaml # LLM provider configurations
```

## Documentation

- **IMPLEMENTATION_GUIDE.md**: Detailed development tasks and implementation notes
- **API Documentation**: Coming soon
- **Configuration Guide**: See `config/llm_config.yaml` for LLM setup examples

---

**Last Updated**: May 29, 2025  
**Version**: 0.2.0-dev (LLM Architecture Complete)  
**Status**: Test fixes ready for implementation, multi-LLM expansion next
