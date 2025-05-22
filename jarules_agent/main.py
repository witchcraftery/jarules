# jarules_agent/main.py

import sys
# Assuming the script is run from the root of the project,
# or jarules_agent is in the Python path.
try:
    from jarules_agent.ui import cli
except ModuleNotFoundError:
    # Fallback for cases where the module structure isn't immediately recognized
    # This can happen if running 'python jarules_agent/main.py' from /app
    # Add the parent directory of 'jarules_agent' to sys.path
    import os
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    # The above line would be if main.py was one level deeper.
    # If main.py is in /app/jarules_agent/main.py, and cli.py is in /app/jarules_agent/ui/cli.py
    # then 'from jarules_agent.ui import cli' should work if /app is in sys.path.
    # Let's ensure the current directory (which should be /app/jarules_agent) is in path
    # sys.path.insert(0, os.path.dirname(__file__)) # This adds /app/jarules_agent to path
    # Then from ui import cli should work.
    # However, the original 'from jarules_agent.ui import cli' implies 'jarules_agent' itself is a package
    # visible in the path.
    # The tool environment usually handles this by setting PYTHONPATH to /app or similar.
    # Let's try to make the import more robust for different execution contexts.
    # If 'jarules_agent.ui' is not found, it might be that 'jarules_agent' is the CWD.
    if 'jarules_agent.ui' not in sys.modules:
         from ui import cli


def main():
    """
    Main function to start the JaRules application.
    Currently, it launches the Command Line Interface (CLI).
    """
    print("Starting JaRules application...")
    cli.run_cli()

if __name__ == "__main__":
    main()
