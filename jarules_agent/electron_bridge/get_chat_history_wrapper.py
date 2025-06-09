import json
import sys
from pathlib import Path

CHAT_HISTORY_PATH = Path.home() / ".jarules" / "chat_history.json"

def get_history():
    """
    Reads the chat history file.
    Outputs JSON list to stdout, or an empty list if file not found/invalid.
    """
    history = []
    error_occurred = False
    error_message = None

    if CHAT_HISTORY_PATH.is_file():
        try:
            with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    history = data
                else:
                    # Corrupted or wrong format, treat as empty and log error
                    error_message = f"Chat history file is not a list: {CHAT_HISTORY_PATH}"
                    error_occurred = True
        except json.JSONDecodeError:
            error_message = f"Error decoding chat history JSON: {CHAT_HISTORY_PATH}"
            error_occurred = True
        except IOError as e:
            error_message = f"IOError reading chat history file {CHAT_HISTORY_PATH}: {e}"
            error_occurred = True
        except Exception as e: # Catch any other unexpected error
            error_message = f"Unexpected error reading chat history {CHAT_HISTORY_PATH}: {e}"
            error_occurred = True
    else:
        # File doesn't exist, which is fine, just means no history.
        pass # history is already []

    # In case of error, we still print an empty list for the renderer to handle gracefully.
    # The error can be logged to stderr for debugging if needed from Electron main process.
    if error_occurred and error_message:
        print(f"Error accessing chat history: {error_message}", file=sys.stderr)
        # Fallback to empty list is already default.
        # If we wanted to signal error to Electron explicitly via stdout JSON:
        # print(json.dumps({"error": error_message, "history": []}))
        # But for now, just returning [] on error simplifies renderer logic slightly.

    print(json.dumps(history))

if __name__ == '__main__':
    # Ensure the .jarules directory exists for other operations, though not strictly for read.
    # (Path.home() / ".jarules").mkdir(parents=True, exist_ok=True)
    get_history()
