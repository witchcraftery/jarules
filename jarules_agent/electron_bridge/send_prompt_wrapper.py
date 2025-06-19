import json
import os
import sys
import signal # Added signal
import argparse
import asyncio
from pathlib import Path # Added pathlib
from typing import List, Dict, Optional # For type hinting

# Adjust path (similar to other wrappers)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Stop Generation Signal Handling ---
STOP_GENERATION_FLAG = False

def handle_stop_signal(signum, frame):
    """Sets the stop generation flag when SIGUSR1 is received."""
    global STOP_GENERATION_FLAG
    STOP_GENERATION_FLAG = True
    # Optional: print a debug message to stderr to confirm signal reception
    print(json.dumps({"type": "debug", "message": "Stop signal received, attempting to halt generation."}), file=sys.stderr)
    sys.stderr.flush()

# Register the signal handler for SIGUSR1
signal.signal(signal.SIGUSR1, handle_stop_signal)
# --- End Stop Generation Signal Handling ---

try:
    from jarules_agent.core.llm_manager import LLMManager, LLMConfigError, LLMManagerError
    from jarules_agent.connectors.base_llm_connector import LLMConnectorError
except ModuleNotFoundError:
    print(json.dumps({"error": True, "message": "ModuleNotFoundError: Could not import LLMManager or related classes.", "details": "Python environment or script path issue."}))
    sys.stdout.flush()
    sys.exit(1)

import time

# --- Configuration File Paths ---
JARULES_DIR = Path.home() / ".jarules"
CHAT_HISTORY_FILE = JARULES_DIR / "chat_history.json"
USER_STATE_FILE = JARULES_DIR / "user_state.json"
DEFAULT_CONTEXT_MESSAGE_COUNT = 10 # Default number of past messages to include if not in user_state.json

def load_chat_history(history_file_path: Path, num_messages: int) -> List[Dict[str, str]]:
    """
    Loads and formats the last num_messages from the chat history file.
    """
    if not history_file_path.exists():
        return []

    try:
        with open(history_file_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # Log this error to stderr or a proper logging mechanism if available
        print(json.dumps({"type": "error", "message": "Error loading chat history", "details": f"Failed to read or parse {history_file_path}: {e}"}), file=sys.stderr)
        return []

    if not isinstance(history_data, list):
        print(json.dumps({"type": "error", "message": "Invalid chat history format", "details": f"Expected a list in {history_file_path}, got {type(history_data)}"}), file=sys.stderr)
        return []

    # Get the last num_messages
    relevant_messages_raw = history_data[-num_messages:]

    formatted_messages: List[Dict[str, str]] = []
    for msg in relevant_messages_raw:
        sender = msg.get("sender")
        text = msg.get("text")

        if not sender or not text:
            # Log malformed message
            print(json.dumps({"type": "warning", "message": "Skipping malformed message in chat history", "details": f"Message missing sender or text: {msg}"}), file=sys.stderr)
            continue

        role = "user" if sender == "user" else "assistant" # Default unknown senders to assistant or skip
        if sender not in ["user", "assistant"]: # Be more specific or handle other potential senders
             # For now, skip if not user or assistant to match expected roles
            print(json.dumps({"type": "warning", "message": "Skipping message with unknown sender type in chat history", "details": f"Unknown sender: {sender}"}), file=sys.stderr)
            continue

        formatted_messages.append({"role": role, "text": text})

    return formatted_messages


async def send_prompt_to_llm_streaming(prompt: str, provider_id: str):
    """
    Uses LLMManager to get a client, loads chat history, and sends the prompt.
    Simulates streaming for 'ollama_default_local', actual calls for others.
    Outputs multiple JSON strings for streaming.
    """
    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')
    loaded_history: List[Dict[str, str]] = []

    # Determine context_message_count
    context_message_count = DEFAULT_CONTEXT_MESSAGE_COUNT
    if USER_STATE_FILE.exists():
        try:
            with open(USER_STATE_FILE, 'r', encoding='utf-8') as f:
                user_state_data = json.load(f)
            if isinstance(user_state_data, dict):
                config_count = user_state_data.get("context_message_count")
                if isinstance(config_count, int) and config_count > 0:
                    context_message_count = config_count
                elif config_count is not None: # Exists but invalid
                    print(json.dumps({"type": "warning", "message": "Invalid context_message_count in user_state.json", "details": f"Expected positive integer, got {config_count}. Using default {DEFAULT_CONTEXT_MESSAGE_COUNT}."}), file=sys.stderr)
            else:
                print(json.dumps({"type": "warning", "message": "Invalid user_state.json format", "details": f"Expected a JSON object, got {type(user_state_data)}. Using default {DEFAULT_CONTEXT_MESSAGE_COUNT}."}), file=sys.stderr)
        except (IOError, json.JSONDecodeError) as e:
            print(json.dumps({"type": "warning", "message": "Error reading user_state.json", "details": str(e) + f". Using default {DEFAULT_CONTEXT_MESSAGE_COUNT}."}), file=sys.stderr)

    # print(json.dumps({"type": "debug", "message": f"Using context_message_count: {context_message_count}"}), file=sys.stderr) # Optional debug line

    try:
        # Ensure .jarules directory exists (for both history and state file)
        JARULES_DIR.mkdir(parents=True, exist_ok=True)

        loaded_history = load_chat_history(CHAT_HISTORY_FILE, context_message_count) # Use determined count


        manager = LLMManager(config_path=config_path)
        if not provider_id or provider_id.lower() == "null" or provider_id.lower() == "undefined":
            print(json.dumps({"type": "error", "message": "No active model ID provided to the script.", "details": "Provider ID was null or undefined."}))
            sys.stdout.flush()
            return

        print(json.dumps({"type": "stream_start"}))
        sys.stdout.flush()

        if provider_id == "ollama_default_local":
            time.sleep(0.1)
            # Simulate history usage in log or output
            history_notice = f"(Simulating with history of {len(loaded_history)} messages) " if loaded_history else ""
            simulated_text = f"Simulated streaming for '{prompt}' from {provider_id} {history_notice}: "
            words = ["This", "is", "a", "streamed", "response", "reflecting", "potential", "history", "use."]
            full_response_text = ""
            for word in words:
                if STOP_GENERATION_FLAG:
                    break
                chunk_text = f"{word} "
                full_response_text += chunk_text
                print(json.dumps({"type": "chunk", "token": chunk_text}))
                sys.stdout.flush()
                time.sleep(0.05)

            if STOP_GENERATION_FLAG:
                print(json.dumps({"type": "done", "cancelled": True, "message": "Generation stopped by user"}))
                sys.stdout.flush()
                return # Exit after sending cancelled message
            else:
                print(json.dumps({"type": "done", "full_response": full_response_text.strip()}))
                sys.stdout.flush()
        else:
            # Check before starting generation for other clients
            if STOP_GENERATION_FLAG:
                print(json.dumps({"type": "done", "cancelled": True, "message": "Generation stopped by user before starting"}))
                sys.stdout.flush()
                return

            llm_client = manager.get_llm_client(provider_id=provider_id)
            # Pass the loaded_history to generate_code
            response_text = await llm_client.generate_code(prompt, history=loaded_history)

            # Check if stop was signalled during llm_client.generate_code
            if STOP_GENERATION_FLAG:
                print(json.dumps({"type": "done", "cancelled": True, "message": "Generation stopped by user during LLM call"}))
                sys.stdout.flush()
                return

            if response_text is None: # Handle cases where connector might return None (e.g. safety block)
                print(json.dumps({"type": "error", "message": "LLM did not return a response.", "details": "The response from the LLM client was None."}))
                sys.stdout.flush()
                # Ensure "done" is still sent to terminate stream on client side
                print(json.dumps({"type": "done", "full_response": None}))
                sys.stdout.flush()
                return

            print(json.dumps({"type": "chunk", "token": response_text})) # Send as one chunk for non-streaming actual call
            sys.stdout.flush()
            print(json.dumps({"type": "done", "full_response": response_text}))
            sys.stdout.flush()

    except LLMManagerError as e:
        print(json.dumps({"type": "error", "message": "LLMManager Error", "details": str(e)}))
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
