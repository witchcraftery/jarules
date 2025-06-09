import json
import os
import sys
import argparse

# Adjust path (similar to get_available_models_wrapper.py)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from jarules_agent.core.llm_manager import LLMManager, LLMConfigError
except ModuleNotFoundError:
    print(json.dumps({"success": False, "error": "ModuleNotFoundError: Could not import LLMManager."}), file=sys.stderr)
    sys.exit(1)

def set_active_model(provider_id: str):
    """
    Sets the active LLM provider using LLMManager and persists the choice.
    Outputs JSON: {"success": true/false, "message": "...", "error": "..."}
    """
    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')
    output = {}

    try:
        manager = LLMManager(config_path=config_path)
        manager.set_active_provider(provider_id) # This validates and saves
        output = {"success": True, "message": f"Active model successfully set to '{provider_id}'."}
    except ValueError as e: # Raised by set_active_provider for invalid ID
        output = {"success": False, "error": str(e)}
    except LLMConfigError as e: # If LLMManager itself fails to initialize
        output = {"success": False, "error": f"LLM Configuration Error: {str(e)}"}
    except Exception as e:
        output = {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

    print(json.dumps(output))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Set the active LLM provider for JaRules.")
    parser.add_argument("provider_id", type=str, help="The ID of the LLM provider configuration to activate.")

    args = parser.parse_args()

    if not args.provider_id:
        # Should be caught by argparse 'required' if not for positional, but good practice
        print(json.dumps({"success": False, "error": "No provider_id provided."}))
    else:
        set_active_model(args.provider_id)
