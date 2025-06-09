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
        manager.set_active_provider(provider_id)
        output = {"success": True, "message": f"Active model successfully set to '{provider_id}'."}
    except ValueError as e:
        output = {"error": True, "message": "Invalid provider ID provided.", "details": str(e)}
    except LLMConfigError as e:
        output = {"error": True, "message": "LLM Configuration Error during set active model.", "details": str(e)}
    except Exception as e:
        output = {"error": True, "message": "An unexpected error occurred while setting active model.", "details": str(e)}

    print(json.dumps(output))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Set the active LLM provider for JaRules.")
    parser.add_argument("provider_id", type=str, help="The ID of the LLM provider configuration to activate.")

    args = parser.parse_args()

    if not args.provider_id:
        print(json.dumps({"error": True, "message": "No provider_id provided.", "details": "Argument 'provider_id' is required."}))
    else:
        set_active_model(args.provider_id)
