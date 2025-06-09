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
    # This is a critical error before streaming can even be attempted.
    print(json.dumps({"error": True, "message": "ModuleNotFoundError: Could not import LLMManager or related classes.", "details": "Python environment or script path issue."}))
    sys.stdout.flush() # Though not strictly streaming, good practice
    sys.exit(1)

# Import time for simulated streaming delay
import time

async def send_prompt_to_llm_streaming(prompt: str, provider_id: str):
    """
    Uses LLMManager to get a client and sends the prompt.
    If provider_id is 'ollama_default_local' (or similar, for testing), it simulates streaming.
    Otherwise, it sends a single response (compatibility mode or for non-streaming providers).
    Outputs multiple JSON strings, each on a new line, for streaming.
    """
    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')

    try:
        manager = LLMManager(config_path=config_path)
        if not provider_id or provider_id.lower() == "null" or provider_id.lower() == "undefined":
            print(json.dumps({"type": "error", "message": "No active model ID provided to the script.", "details": "Provider ID was null or undefined."}))
            sys.stdout.flush()
            return

        # Start of stream signal
        print(json.dumps({"type": "stream_start"}))
        sys.stdout.flush()

        # Simulate streaming for 'ollama_default_local'
        if provider_id == "ollama_default_local":
            time.sleep(0.1) # Simulate initial delay
            simulated_text = f"Simulated streaming response for '{prompt}' from {provider_id}: "
            words = ["This", "is", "a", "streamed", "response", ".", "One", "token", "at", "a", "time", "!"]
            full_response_text = ""
            for word in words:
                chunk_text = f"{word} "
                full_response_text += chunk_text
                print(json.dumps({"type": "chunk", "token": chunk_text}))
                sys.stdout.flush()
                time.sleep(0.05)
            print(json.dumps({"type": "done", "full_response": full_response_text.strip()}))
            sys.stdout.flush()
        else:
            # Non-streaming behavior for other providers (actual call)
            llm_client = manager.get_llm_client(provider_id=provider_id)
            response_text = await llm_client.generate_code(prompt)

            print(json.dumps({"type": "chunk", "token": response_text}))
            sys.stdout.flush()
            print(json.dumps({"type": "done", "full_response": response_text}))
            sys.stdout.flush()

    except LLMManagerError as e:
        print(json.dumps({"type": "error", "message": f"LLMManager Error", "details": str(e)}))
        sys.stdout.flush()
    except LLMConnectorError as e:
        print(json.dumps({"type": "error", "message": f"LLMConnector Error ({provider_id})", "details": str(e)}))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"type": "error", "message": f"An unexpected error occurred in Python script.", "details": str(e)}))
        sys.stdout.flush()
    finally:
        # Ensure a "done" message is sent if an error occurred mid-stream before "done" was naturally reached.
        # This might be complex if stream_start wasn't even sent.
        # For now, individual error handlers send their own type:error and main.js interprets that as an end.
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Send a prompt to the specified LLM provider, possibly streaming.")
    parser.add_argument("prompt", type=str, help="The user prompt to send to the LLM.")
    parser.add_argument("provider_id", type=str, help="The ID of the LLM provider configuration to use (or 'null'/'undefined').")

    args = parser.parse_args()

    if not args.prompt:
        # Critical error before streaming attempt
        print(json.dumps({"error": True, "message": "Prompt not provided.", "details": "Argument 'prompt' is required."}))
        sys.stdout.flush()
    elif not args.provider_id or args.provider_id.lower() == "null" or args.provider_id.lower() == "undefined":
        # Also a critical error if provider_id is effectively missing for a prompt command
        print(json.dumps({"error": True, "message": "Provider ID not provided or invalid.", "details": "Argument 'provider_id' was 'null' or 'undefined'."}))
        sys.stdout.flush()
    else:
        asyncio.run(send_prompt_to_llm_streaming(args.prompt, args.provider_id))
