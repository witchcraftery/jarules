import json
import sys
import argparse
from pathlib import Path

CHAT_HISTORY_PATH = Path.home() / ".jarules" / "chat_history.json"
MAX_HISTORY_LENGTH = 200 # Optional: Limit the number of messages stored

def save_message(message_json_string: str):
    """
    Appends a new message to the chat history.
    The message is provided as a JSON string argument.
    Outputs JSON: {"success": true/false, "error": "message_if_any"}
    """
    history = []
    output = {}

    # Ensure directory exists
    try:
        CHAT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        output = {"success": False, "error": f"Could not create directory {CHAT_HISTORY_PATH.parent}: {e}"}
        print(json.dumps(output))
        return

    # Load existing history
    if CHAT_HISTORY_PATH.is_file():
        try:
            with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                history = data
            # If file is not a list or corrupted, it will be overwritten.
        except (json.JSONDecodeError, IOError):
            # Errors during read are okay, as we'll try to overwrite.
            pass

    try:
        new_message = json.loads(message_json_string)
        history.append(new_message)

        if len(history) > MAX_HISTORY_LENGTH:
            history = history[-MAX_HISTORY_LENGTH:]

        with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        output = {"success": True} # No "error":false needed, success is implicit

    except json.JSONDecodeError as e:
        output = {"error": True, "message": "Invalid JSON string for message object.", "details": str(e)}
    except IOError as e:
        output = {"error": True, "message": "IOError saving chat history.", "details": str(e)}
    except Exception as e:
        output = {"error": True, "message": "Unexpected error saving chat history.", "details": str(e)}

    print(json.dumps(output))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Save a chat message to history.")
    parser.add_argument("message_json", type=str, help="A JSON string representing the chat message object.")

    args = parser.parse_args()

    if not args.message_json:
        print(json.dumps({"error": True, "message": "No message_json provided.", "details": "Argument missing."}))
    else:
        save_message(args.message_json)
