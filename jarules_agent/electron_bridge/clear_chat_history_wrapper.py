import json
import sys
from pathlib import Path
import os # For os.remove

CHAT_HISTORY_PATH = Path.home() / ".jarules" / "chat_history.json"

def clear_history():
    """
    Clears the chat history by deleting the file or overwriting with an empty list.
    Outputs JSON: {"success": true/false, "error": "message_if_any"}
    """
    output = {}
    try:
        if CHAT_HISTORY_PATH.is_file():
            os.remove(CHAT_HISTORY_PATH)
            # Check if removal was successful (it might fail silently in some edge cases, though unlikely for os.remove)
            if CHAT_HISTORY_PATH.exists():
                # If remove failed, try overwriting
                with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                output = {"success": True, "message": "History file overwritten with empty list as direct delete failed."} # This is a success case
            else:
                output = {"success": True, "message": "Chat history successfully deleted."}
        else:
            output = {"success": True, "message": "Chat history file did not exist (already clear)."}

    except IOError as e:
        output = {"error": True, "message": "IOError clearing chat history.", "details": str(e)}
    except Exception as e:
        output = {"error": True, "message": "Unexpected error clearing chat history.", "details": str(e)}

    print(json.dumps(output))

if __name__ == '__main__':
    clear_history()
