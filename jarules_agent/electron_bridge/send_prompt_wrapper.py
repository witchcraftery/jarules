import json
import os
import sys
import argparse
import asyncio # Required if using async methods from LLM client

# Adjust path (similar to other wrappers)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMManagerError
    from jarules_agent.connectors.base_llm_connector import LLMConnectorError
except ModuleNotFoundError:
    print(json.dumps({"error": "ModuleNotFoundError: Could not import LLMManager or related classes."}), file=sys.stderr)
    sys.exit(1)

async def send_prompt_to_llm(prompt: str, provider_id: str):
    """
    Uses LLMManager to get a client for the active_provider_id and sends the prompt.
    Outputs JSON: {"response": "..."} or {"error": "..."}
    """
    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')
    output = {}

    try:
        manager = LLMManager(config_path=config_path)
        # Although LLMManager might have an active_provider_id, Electron main.js
        # sends the one it currently believes is active. This script will use the passed one.
        # This also means the manager doesn't strictly need to load user_state for this script,
        # but its __init__ does. The key is that get_llm_client will use the provider_id passed here.
        if not provider_id or provider_id == "null": # Handle "null" string from JS if currentActiveModelId is null
             output = {"error": "No active model ID provided to the script."}
        else:
            llm_client = manager.get_llm_client(provider_id=provider_id)
            # Assuming generate_code is the method to call.
            # If a more generic "chat" or "send_message" method exists, that could be used.
            # For now, all connectors implement generate_code.
            # This call needs to be async if the connector method is async.
            response_text = await llm_client.generate_code(prompt) # All our connectors have async generate_code
            output = {"response": response_text}

    except LLMManagerError as e: # Covers config errors, provider not found, no active model if provider_id was None
        output = {"error": f"LLMManager Error: {str(e)}"}
    except LLMConnectorError as e: # Covers errors from the specific connector (API errors, etc.)
        output = {"error": f"LLMConnector Error ({provider_id}): {str(e)}"}
    except Exception as e:
        output = {"error": f"An unexpected error occurred: {str(e)}"}

    print(json.dumps(output))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Send a prompt to the specified LLM provider via LLMManager.")
    parser.add_argument("prompt", type=str, help="The user prompt to send to the LLM.")
    parser.add_argument("provider_id", type=str, help="The ID of the LLM provider configuration to use.")

    args = parser.parse_args()

    if not args.prompt or not args.provider_id:
        print(json.dumps({"error": "Prompt or provider_id not provided."}))
    else:
        asyncio.run(send_prompt_to_llm(args.prompt, args.provider_id))
