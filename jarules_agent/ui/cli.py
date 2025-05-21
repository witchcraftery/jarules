# jarules_agent/ui/cli.py

import sys
# Correcting the import path assuming jarules_agent is in PYTHONPATH
# or the script is run from the directory containing jarules_agent.
try:
    from jarules_agent.connectors import local_files
except ModuleNotFoundError:
    # Fallback for direct execution if jarules_agent is not in PYTHONPATH
    # This assumes the script might be run from jarules_agent/ui or similar
    import os
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
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from connectors import local_files
    from connectors import github_connector # Added for GitHubClient


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
    print("\n  General:")
    print("    help                         - Prints this list of available commands.")
    print("    exit / quit                  - Exits the CLI.\n")

def run_cli():
    """Runs the main command-line interface loop."""
    print("Welcome to JaRules CLI!")
    # Instantiate GitHubClient (can be configured with a token later if needed)
    github_client = github_connector.GitHubClient()
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
                            print(f"Listing files in GitHub repo: {owner}/{repo}, path: '{repo_sub_path or Toplevel}'...")
                            files = github_client.list_repo_files(owner, repo, repo_sub_path)
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
                            content = github_client.read_repo_file(owner, repo, file_path_in_repo)
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
