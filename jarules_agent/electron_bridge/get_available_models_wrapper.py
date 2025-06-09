import json
import os
import sys

# Adjust path to import LLMManager from the parent directory of 'jarules_agent'
# This assumes 'jarules_agent' is the top-level package for the agent code.
# The script is in jarules_agent/electron_bridge/
# We need to go up two levels to be able to import jarules_agent.core.llm_manager
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
# This makes project_root the directory containing 'jarules_agent' and 'jarules_electron_vue_ui'

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from jarules_agent.core.llm_manager import LLMManager, LLMConfigError
except ModuleNotFoundError:
    # Fallback if the above doesn't work in some execution contexts (e.g. PythonShell scriptPath points elsewhere)
    # This is a common issue with Python imports when scripts are called from other processes.
    # For robust execution with PythonShell, often the scriptPath in PythonShell options
    # needs to be set to a directory that allows Python to resolve modules as if it were the main project root.
    # Or, ensure PYTHONPATH is set correctly for the PythonShell environment.
    # As a last resort, a very specific relative path can be tried if the structure is fixed.
    # For now, assume the above sys.path modification works or PYTHONPATH is configured.
    print(json.dumps({"error": "ModuleNotFoundError: Could not import LLMManager. Check Python path and script location."}), file=sys.stderr)
    sys.exit(1)


def get_models():
    """
    Loads LLM configurations using LLMManager and prints enabled models as JSON.
    Outputs JSON: {"models": [list_of_model_configs]} or {"error": "message"}
    """
    # Determine the config path relative to this script or a known project structure
    # config_path = project_root / 'config/llm_config.yaml' -> if project_root is Path object
    # Assuming config is in ../../config/llm_config.yaml from this script's location
    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')

    output = {}
    try:
        # It's important that LLMManager can find its connectors.
        # This might require PYTHONPATH to be set correctly when PythonShell runs this script,
        # or for the connectors to be discoverable from LLMManager's location.
        manager = LLMManager(config_path=config_path)
        available_configs = manager.get_available_configs() # This returns a dict

        # Convert dict of configs to a list of dicts, which is often easier for UIs
        models_list = [config for config_id, config in available_configs.items()]
        output = {"models": models_list}

    except LLMConfigError as e:
        output = {"error": f"LLM Configuration Error: {str(e)}"}
    except Exception as e:
        # Catch-all for other unexpected errors during LLMManager init or config loading
        output = {"error": f"An unexpected error occurred: {str(e)}"}

    print(json.dumps(output))

if __name__ == '__main__':
    get_models()
