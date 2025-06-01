# jarules_agent/ui/cli.py

import sys
# Correcting the import path assuming jarules_agent is in PYTHONPATH
# or the script is run from the directory containing jarules_agent.
import os # Ensure os is imported if used in fallback
try:
    from jarules_agent.connectors import local_files
    from jarules_agent.connectors import github_connector # Added for GitHubClient
    from jarules_agent.connectors.gemini_api import GeminiApiKeyError, GeminiCodeGenerationError, GeminiApiError, GeminiExplanationError, GeminiModificationError 
    from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError
    from jarules_agent.connectors.base_llm_connector import LLMConnectorError # To catch broader LLM errors
except ModuleNotFoundError:
    # Fallback for direct execution if jarules_agent is not in PYTHONPATH
    # This assumes the script might be run from jarules_agent/ui or similar
    # Add parent directory of 'jarules_agent' to sys.path if 'jarules_agent' itself is not directly in sys.path
    # This is a bit complex because the structure is /app/jarules_agent/...
    # If we are in /app/jarules_agent/ui, then ../../ needs to be added for 'from jarules_agent...' to work
    # However, the tool runs from /app. So 'jarules_agent' should be directly importable.
    # The issue might be how the python interpreter is invoked or the CWD.
    # For now, let's assume the original import should work if PYTHONPATH is set up correctly by the environment.
    # If not, this path adjustment is a common workaround.
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    # The above line would be for running cli.py directly from its own directory.
    # Given the tool structure, a direct import should ideally work.
    # Let's try a simpler relative import path if the primary fails.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Go up to 'jarules_agent'
    from connectors import local_files # now this becomes from jarules_agent.connectors
    from connectors import github_connector 
    from connectors.gemini_api import GeminiApiKeyError, GeminiCodeGenerationError, GeminiApiError, GeminiExplanationError, GeminiModificationError 
    # LLMManager and related exceptions should be imported from their actual core path
    # This fallback should primarily handle connectors if the structure is odd.
    # However, the test error indicates LLMManager is not found by the patcher at jarules_agent.ui.cli.LLMManager
    # So LLMManager must be imported at the top level of cli.py
    from core.llm_manager import LLMManager, LLMConfigError, LLMProviderNotImplementedError
    from connectors.base_llm_connector import LLMConnectorError


def display_help():
    """Prints a list of available commands."""
    print("\nAvailable commands:")
    print("  Local File System:")
    print("    ls <directory_path>          - Lists files in the specified local directory.")
    print("    read <file_path>             - Reads and prints the content of the specified local file.")
    print("    write <file_path> <content>  - Writes the given content to the specified local file.")
    print("                                   (Content is joined from the third argument onwards)")
    print("\n  GitHub:")
    print("    gh_ls <owner>/<repo>[/<path>] - Lists files in a GitHub repository path.")
    print("                                   Example: gh_ls octocat/Hello-World/docs")
    print("    gh_read <owner>/<repo>/<file_path> - Reads a file from a GitHub repository.")
    print("                                   Example: gh_read octocat/Hello-World/README.md")
    print("\n  AI:")
    print("    ai gencode \"<prompt_text>\"   - Generates code based on the provided prompt.")
    print("    ai explain \"<code_snippet>\"  - Explains the provided code snippet.")
    print("    ai explain_file <filepath>   - Explains the content of the specified file.")
    print("    ai suggest_fix \"<code_snippet>\" \"<issue>\" - Suggests a fix for the code snippet based on the issue.")
    print("    ai suggest_fix_file <filepath> \"<issue>\" - Suggests a fix for the file content based on the issue.")
    print("\n  General:")
    print("    help                         - Prints this list of available commands.")
    print("    exit / quit                  - Exits the CLI.\n")

def strip_quotes(text):
    """Strip outer quotes from a string if present."""
    if len(text) >= 2:
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
    return text


def parse_quoted_args(text):
    """Parse a string into arguments, respecting quoted strings."""
    import shlex
    try:
        return shlex.split(text)
    except ValueError:
        # Fallback to simple split if shlex fails
        return text.split()


def run_cli():
    """Runs the main command-line interface loop."""
    print("Welcome to JaRules CLI!")
    # Instantiate GitHubClient (can be configured with a token later if needed)
    github_client = github_connector.GitHubClient()

    # Instantiate LLMManager and load default LLM
    # LLMManager class should be available here due to top-level imports
    try:
        llm_manager = LLMManager(config_path='config/llm_config.yaml')
        print("LLMManager initialized successfully.")
    except LLMConfigError as e: # LLMConfigError should also be available
        print(f"Error initializing LLMManager: {e}. AI features will be unavailable.")
        return 
    except Exception as e:
        print(f"A critical error occurred initializing LLMManager: {e}. AI features will be unavailable.")
        return

    active_llm_client = None 
    default_llm_config_id = "gemini_flash_default" 

    try:
        active_llm_client = llm_manager.get_llm_connector(default_llm_config_id)
        if active_llm_client:
            print(f"Successfully loaded LLM: '{default_llm_config_id}' (Model: {active_llm_client.model_name})")
        else: 
            print(f"Warning: Could not load default LLM '{default_llm_config_id}'. AI features may be limited.")
    except GeminiApiKeyError as e: 
        print(f"API Key Error for LLM '{default_llm_config_id}': {e}. AI features will be unavailable.")
        return 
    except LLMProviderNotImplementedError as e:
        print(f"LLM Provider Error: {e}. AI features for this provider are unavailable.")
        return
    except LLMConfigError as e: 
        print(f"LLM Configuration Error: {e}. AI features may be unavailable.")
        return
    except Exception as e: 
        print(f"An unexpected error occurred while loading LLM '{default_llm_config_id}': {e}. AI features will be unavailable.")
        return

    display_help()

    while True:
        try:
            raw_input = input("JaRules> ").strip()
            if not raw_input:
                continue

            parts = raw_input.split()
            command = parts[0].lower()
            args = parts[1:]

            if command in ["exit", "quit"]:
                print("Exiting JaRules CLI. Goodbye!")
                break
            elif command == "help":
                display_help()
            elif command == "ls":
                if len(args) == 1:
                    dir_path = args[0]
                    try:
                        files = local_files.list_files(dir_path)
                        if files:
                            print(f"\nFiles in '{dir_path}':")
                            for item in files:
                                print(f"  {item}")
                        else:
                            print(f"No files or directories found in '{dir_path}'.")
                    except FileNotFoundError as e:
                        print(f"Error: {e}")
                    except NotADirectoryError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                else:
                    print("Usage: ls <directory_path>")
            elif command == "read":
                if len(args) == 1:
                    file_path = args[0]
                    try:
                        content = local_files.read_file(file_path)
                        print(f"\nContent of '{file_path}':\n---\n{content}\n---")
                    except FileNotFoundError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                else:
                    print("Usage: read <file_path>")
            elif command == "write":
                if len(args) >= 2:
                    file_path = args[0]
                    content = " ".join(args[1:]) # Join all parts after file_path as content
                    try:
                        local_files.write_file(file_path, content)
                        print(f"Content written to '{file_path}'.")
                    except IOError as e:
                        print(f"Error writing file: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                else:
                    print("Usage: write <file_path> <content>")
            elif command == "gh_ls":
                if len(args) == 1:
                    full_repo_path = args[0]
                    path_parts = full_repo_path.split('/')
                    if len(path_parts) >= 2:
                        owner = path_parts[0]
                        repo = path_parts[1]
                        repo_sub_path = "/".join(path_parts[2:]) if len(path_parts) > 2 else ""
                        try:
                            print(f"Listing files in GitHub repo: {owner}/{repo}, path: '{repo_sub_path or 'Toplevel'}'...")
                            files = github_client.list_repo_files(owner=owner, repo=repo, path=repo_sub_path)
                            if files: # list_repo_files returns empty list on error or if dir is empty
                                print(f"\nFiles in '{owner}/{repo}/{repo_sub_path}':")
                                for item in files:
                                    print(f"  {item}")
                            else:
                                print(f"No files or directories found in '{owner}/{repo}/{repo_sub_path}', or path is invalid/empty.")
                        except Exception as e: # Catch any exception from the client
                            print(f"Error listing GitHub repository files: {e}")
                    else:
                        print("Usage: gh_ls <owner>/<repo>[/<path>]")
                else:
                    print("Usage: gh_ls <owner>/<repo>[/<path>]")
            elif command == "gh_read":
                if len(args) == 1:
                    full_file_path = args[0]
                    path_parts = full_file_path.split('/')
                    if len(path_parts) >= 3: # Need at least owner/repo/file.txt
                        owner = path_parts[0]
                        repo = path_parts[1]
                        file_path_in_repo = "/".join(path_parts[2:])
                        try:
                            print(f"Reading file from GitHub repo: {owner}/{repo}/{file_path_in_repo}...")
                            content = github_client.read_repo_file(owner=owner, repo=repo, file_path=file_path_in_repo)
                            if content is not None:
                                print(f"\nContent of '{owner}/{repo}/{file_path_in_repo}':\n---\n{content}\n---")
                            else:
                                print(f"Could not read file '{owner}/{repo}/{file_path_in_repo}'. It might not exist, be a directory, or an error occurred.")
                        except Exception as e: # Catch any exception from the client
                            print(f"Error reading GitHub repository file: {e}")
                    else:
                        print("Usage: gh_read <owner>/<repo>/<file_path>")
                else:
                    print("Usage: gh_read <owner>/<repo>/<file_path>")
            elif command == "ai" and args and args[0].lower() == "gencode":
                if not active_llm_client:
                    print("No LLM connector available.")
                    continue
                if len(args) > 1:
                    # Join all arguments and strip outer quotes
                    prompt_string = strip_quotes(" ".join(args[1:]))
                    try:
                        print(f"Generating code for prompt: \"{prompt_string}\"...")
                        generated_code = active_llm_client.generate_code(prompt_string)
                        if generated_code:
                            print("\n--- Generated Code ---")
                            print(generated_code)
                            print("--- End of Generated Code ---")
                        else:
                            print("No code generated or the response was empty.")
                    except GeminiCodeGenerationError as e: # Specific error from Gemini
                        print(f"Code Generation Error: {e}")
                    except GeminiApiError as e: # Specific error from Gemini
                        print(f"API Error: {e}")
                    except LLMConnectorError as e: # Broader error from any LLM connector
                        print(f"LLM Connector Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred during code generation: {e}")
                else:
                    print("Usage: ai gencode \"<prompt_text>\"")
            elif command == "ai" and args and args[0].lower() == "explain":
                if not active_llm_client:
                    print("No LLM connector available.")
                    continue
                if len(args) > 1:
                    # Join all arguments and strip outer quotes
                    code_snippet = strip_quotes(" ".join(args[1:]))
                    try:
                        print(f"Explaining code snippet: \"{code_snippet[:50]}...\"")
                        explanation = active_llm_client.explain_code(code_snippet)
                        if explanation:
                            print("\n--- Code Explanation ---")
                            print(explanation)
                            print("--- End of Explanation ---")
                        else:
                            print("No explanation generated or the response was empty.")
                    except GeminiExplanationError as e:
                        print(f"Explanation Error: {e}")
                    except GeminiApiError as e:
                        print(f"API Error: {e}")
                    except LLMConnectorError as e:
                        print(f"LLM Connector Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred during code explanation: {e}")
                else:
                    print("Usage: ai explain \"<code_snippet>\"")
            elif command == "ai" and args and args[0].lower() == "explain_file":
                if not active_llm_client:
                    print("AI client not available. Please check configuration.")
                    continue
                if len(args) == 2:
                    file_path = args[1]
                    try:
                        print(f"Explaining file: \"{file_path}\"...")
                        code_content = local_files.read_file(file_path)
                        explanation = active_llm_client.explain_code(code_content)
                        if explanation:
                            print("\n--- Code Explanation ---")
                            print(explanation)
                            print("--- End of Explanation ---")
                        else:
                            print("No explanation generated or the response was empty.")
                    except FileNotFoundError:
                        print(f"Error: File not found: {file_path}")
                    except GeminiExplanationError as e:
                        print(f"Error explaining code from file: {e}")
                    except GeminiApiError as e:
                        print(f"API Error: {e}")
                    except LLMConnectorError as e:
                        print(f"LLM Connector Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred during file explanation: {e}")
                else:
                    print("Usage: ai explain_file <filepath>")
            elif command == "ai" and args and args[0].lower() == "suggest_fix":
                if not active_llm_client:
                    print("No LLM connector available.")
                    continue
                # Use proper quote-aware parsing for suggest_fix
                # Re-parse the full input to handle quoted arguments properly
                full_parts = parse_quoted_args(raw_input)
                if len(full_parts) >= 4:  # ai, suggest_fix, code_snippet, issue_description
                    code_snippet = full_parts[2]  # Third element
                    issue_description = full_parts[3]  # Fourth element
                    try:
                        print(f"Suggesting fix for code snippet: \"{code_snippet[:50]}...\" based on issue: \"{issue_description[:50]}...\"")
                        suggestion = active_llm_client.suggest_code_modification(code_snippet, issue_description)
                        if suggestion:
                            print("\n--- Suggested Fix ---")
                            print(suggestion)
                            print("--- End of Suggestion ---")
                        else:
                            print("No fix suggested or the response was empty.")
                    except GeminiModificationError as e:
                        print(f"Modification Error: {e}")
                    except GeminiApiError as e:
                        print(f"API Error: {e}")
                    except LLMConnectorError as e:
                        print(f"LLM Connector Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred while suggesting fix: {e}")
                else:
                    print("Usage: ai suggest_fix \"<code_snippet>\" \"<issue_description>\"")
            elif command == "ai" and args and args[0].lower() == "suggest_fix_file":
                if not active_llm_client:
                    print("No LLM connector available.")
                    continue
                if len(args) >= 3: # Expecting sub-command, filepath, and issue_description
                    file_path = args[1]
                    issue_description = strip_quotes(" ".join(args[2:]))
                    try:
                        print(f"Suggesting fix for file: \"{file_path}\" based on issue: \"{issue_description[:50]}...\"")
                        code_content = local_files.read_file(file_path)
                        suggestion = active_llm_client.suggest_code_modification(code_content, issue_description)
                        if suggestion:
                            print("\n--- Suggested Fix ---")
                            print(suggestion)
                            print("--- End of Suggestion ---")
                        else:
                            print("No fix suggested or the response was empty.")
                    except FileNotFoundError:
                        print(f"Error: File not found: {file_path}")
                    except GeminiModificationError as e:
                        print(f"Modification Error: {e}")
                    except GeminiApiError as e:
                        print(f"API Error: {e}")
                    except LLMConnectorError as e:
                        print(f"LLM Connector Error: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred while suggesting fix for file: {e}")
                else:
                    print("Usage: ai suggest_fix_file <filepath> \"<issue_description>\"")
            else:
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")

        except EOFError: # Handle Ctrl+D
            print("\nExiting JaRules CLI. Goodbye!")
            break
        except KeyboardInterrupt: # Handle Ctrl+C
            print("\nOperation cancelled by user. Type 'exit' or 'quit' to leave.")
        except Exception as e:
            print(f"An unexpected error occurred in the CLI: {e}")

if __name__ == "__main__":
    # This is to ensure that if local_files.py also has a main block,
    # it doesn't run when cli.py imports it.
    # The import guard in local_files.py would also prevent this.
    run_cli()
