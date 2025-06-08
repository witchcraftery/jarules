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
    print("\n  Model Management:")
    print("    set-model <provider_id>      - Sets the active LLM provider configuration.")
    print("                                   Example: set-model ollama_default_local")
    print("    get-model                    - Displays the ID and details of the currently active LLM provider.")
    print("    clear-model                  - Clears the persisted active model selection, reverting to default.")
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
        llm_manager = None # Ensure llm_manager is None if init fails
    except Exception as e:
        print(f"A critical error occurred initializing LLMManager: {e}. AI features will be unavailable.")
        llm_manager = None # Ensure llm_manager is None if init fails

    if llm_manager and llm_manager.active_provider_id:
        try:
            # Attempt to load the active client to confirm it's working.
            client = llm_manager.get_llm_client() # Get the active client
            print(f"LLMManager initialized. Active model ID: '{llm_manager.active_provider_id}' (Model: {client.model_name})")
        except LLMManagerError as e:
            print(f"LLMManager initialized, but failed to load active model '{llm_manager.active_provider_id}': {e}")
        except Exception as e:
            print(f"LLMManager initialized. Unexpected error loading active model '{llm_manager.active_provider_id}': {e}")
    elif llm_manager:
         print("LLMManager initialized, but no active model is set. Use 'set-model <provider_id>' or define 'default_provider' in config.")


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
            elif command == "set-model":
                if not llm_manager:
                    print("LLMManager not available.")
                    continue
                if len(args) == 1:
                    provider_id = args[0]
                    try:
                        llm_manager.set_active_provider(provider_id)
                        # Optionally, try to get the client to confirm it loads
                        client = llm_manager.get_llm_client()
                        print(f"Active model set to: '{provider_id}' (Model: {client.model_name}, Provider: {client.config.get('provider')})")
                    except ValueError as e:
                        print(f"Error setting model: {e}")
                    except LLMManagerError as e:
                        print(f"Error loading new active model '{provider_id}': {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred setting model '{provider_id}': {e}")
                else:
                    print("Usage: set-model <provider_id>")
            elif command == "get-model":
                if not llm_manager:
                    print("LLMManager not available.")
                    continue
                if llm_manager.active_provider_id:
                    active_id = llm_manager.active_provider_id
                    config = llm_manager.get_available_configs().get(active_id)
                    if config:
                        print(f"Currently active model configuration:")
                        print(f"  ID: {active_id}")
                        print(f"  Provider: {config.get('provider')}")
                        print(f"  Model Name: {config.get('model_name')}")
                        print(f"  Description: {config.get('description')}")
                    else: # Should not happen if active_provider_id is valid
                        print(f"Active model ID: '{active_id}' (details not found - inconsistency?).")
                else:
                    print("No active model is currently set. Use 'set-model <provider_id>'.")
            elif command == "clear-model":
                if not llm_manager:
                    print("LLMManager not available.")
                    continue
                try:
                    llm_manager.clear_active_provider_state()
                    if llm_manager.active_provider_id:
                         client = llm_manager.get_llm_client() # To display info about the new active (default)
                         print(f"Active model selection cleared. Now using default: '{llm_manager.active_provider_id}' (Model: {client.model_name})")
                    else:
                        print("Active model selection cleared. No default provider configured.")
                except Exception as e:
                    print(f"An error occurred while clearing model state: {e}")

            elif command == "ai" and args:
                if not llm_manager:
                    print("LLMManager not available. AI commands cannot be used.")
                    continue

                try:
                    # Get the currently active LLM client for all AI sub-commands
                    current_llm_client = llm_manager.get_llm_client()
                except LLMManagerError as e:
                    print(f"LLM Error: {e}. Cannot perform AI operation.")
                    continue
                except Exception as e: # Catch other unexpected errors during client retrieval
                    print(f"Unexpected error getting LLM client: {e}. AI features may be unavailable.")
                    continue

                ai_sub_command = args[0].lower()
                if ai_sub_command == "gencode":
                    if len(args) > 1:
                        prompt_string = strip_quotes(" ".join(args[1:]))
                        try:
                            print(f"Generating code using '{llm_manager.active_provider_id}' for prompt: \"{prompt_string}\"...")
                            generated_code = current_llm_client.generate_code(prompt_string)
                            if generated_code:
                                print("\n--- Generated Code ---")
                                print(generated_code)
                                print("--- End of Generated Code ---")
                            else:
                                print("No code generated or the response was empty.")
                        except LLMConnectorError as e: # Catch specific connector errors
                            print(f"Code Generation Error ({llm_manager.active_provider_id}): {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred during code generation ({llm_manager.active_provider_id}): {e}")
                    else:
                        print("Usage: ai gencode \"<prompt_text>\"")

                elif ai_sub_command == "explain":
                    if len(args) > 1:
                        code_snippet = strip_quotes(" ".join(args[1:]))
                        try:
                            print(f"Explaining code snippet using '{llm_manager.active_provider_id}': \"{code_snippet[:50]}...\"")
                            explanation = current_llm_client.explain_code(code_snippet)
                            if explanation:
                                print("\n--- Code Explanation ---")
                                print(explanation)
                                print("--- End of Explanation ---")
                            else:
                                print("No explanation generated or the response was empty.")
                        except LLMConnectorError as e:
                            print(f"Explanation Error ({llm_manager.active_provider_id}): {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred during code explanation ({llm_manager.active_provider_id}): {e}")
                    else:
                        print("Usage: ai explain \"<code_snippet>\"")

                elif ai_sub_command == "explain_file":
                    if len(args) == 2:
                        file_path = args[1]
                        try:
                            print(f"Explaining file using '{llm_manager.active_provider_id}': \"{file_path}\"...")
                            code_content = local_files.read_file(file_path)
                            explanation = current_llm_client.explain_code(code_content)
                            if explanation:
                                print("\n--- Code Explanation ---")
                                print(explanation)
                                print("--- End of Explanation ---")
                            else:
                                print("No explanation generated or the response was empty.")
                        except FileNotFoundError:
                            print(f"Error: File not found: {file_path}")
                        except LLMConnectorError as e:
                            print(f"Error explaining code from file ({llm_manager.active_provider_id}): {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred during file explanation ({llm_manager.active_provider_id}): {e}")
                    else:
                        print("Usage: ai explain_file <filepath>")

                elif ai_sub_command == "suggest_fix":
                    full_parts = parse_quoted_args(raw_input) # ai suggest_fix "<code>" "<issue>"
                    if len(full_parts) >= 4:
                        code_snippet = full_parts[2]
                        issue_description = full_parts[3]
                        try:
                            print(f"Suggesting fix using '{llm_manager.active_provider_id}' for code: \"{code_snippet[:50]}...\" issue: \"{issue_description[:50]}...\"")
                            suggestion = current_llm_client.suggest_code_modification(code_snippet, issue_description)
                            if suggestion:
                                print("\n--- Suggested Fix ---")
                                print(suggestion)
                                print("--- End of Suggestion ---")
                            else:
                                print("No fix suggested or the response was empty.")
                        except LLMConnectorError as e:
                            print(f"Modification Error ({llm_manager.active_provider_id}): {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred while suggesting fix ({llm_manager.active_provider_id}): {e}")
                    else:
                        print("Usage: ai suggest_fix \"<code_snippet>\" \"<issue_description>\"")

                elif ai_sub_command == "suggest_fix_file":
                    if len(args) >= 3:
                        file_path = args[1]
                        issue_description = strip_quotes(" ".join(args[2:]))
                        try:
                            print(f"Suggesting fix for file using '{llm_manager.active_provider_id}': \"{file_path}\" issue: \"{issue_description[:50]}...\"")
                            code_content = local_files.read_file(file_path)
                            suggestion = current_llm_client.suggest_code_modification(code_content, issue_description)
                            if suggestion:
                                print("\n--- Suggested Fix ---")
                                print(suggestion)
                                print("--- End of Suggestion ---")
                            else:
                                print("No fix suggested or the response was empty.")
                        except FileNotFoundError:
                            print(f"Error: File not found: {file_path}")
                        except LLMConnectorError as e:
                            print(f"Modification Error ({llm_manager.active_provider_id}): {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred while suggesting fix for file ({llm_manager.active_provider_id}): {e}")
                    else:
                        print("Usage: ai suggest_fix_file <filepath> \"<issue_description>\"")
                else:
                    print(f"Unknown AI command: 'ai {ai_sub_command}'. Type 'help' for available commands.")
            else: # Handles cases where 'ai' is typed alone or with unknown subcommands.
                if command == "ai":
                     print("AI command requires a subcommand (gencode, explain, etc.). Type 'help' for details.")
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
