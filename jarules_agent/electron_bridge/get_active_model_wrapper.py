import json
import os
from pathlib import Path

def get_active_model():
    """
    Reads the user state file and returns the active_provider_id.
    Outputs JSON: {"active_provider_id": "id_string_or_null"}
    """
    user_state_file_path = Path.home() / ".jarules" / "user_state.json"
    active_id = None
    error_message = None

    if user_state_file_path.is_file():
        try:
            with open(user_state_file_path, 'r') as f:
                state_data = json.load(f)
            active_id = state_data.get("active_provider_id")
        except json.JSONDecodeError:
            # This case should ideally be handled by LLMManager on write,
            # but good to be defensive. If it's corrupted, treat as no selection.
            error_message = f"Error decoding user state file: {user_state_file_path}"
            active_id = None # Ensure it's None if file is corrupt
        except IOError:
            error_message = f"Could not read user state file: {user_state_file_path}"
            active_id = None # Ensure it's None if unreadable

    # Output JSON to stdout
    # python-shell in JSON mode expects a single JSON object per line, or an array of them.
    # Here we print a single object.
    output = {"active_provider_id": active_id}
    if error_message:
        # While the primary goal is to return the ID, including an error if one occurred
        # during read might be useful for debugging from Electron side, but not strictly part of the ID.

    output = {}
    if error_occurred:
        output = {"error": True, "message": error_message, "details": f"File: {CHAT_HISTORY_PATH}", "active_provider_id": None}
    else:
        output = {"active_provider_id": active_id} # No "error":true field means success

    print(json.dumps(output))

if __name__ == '__main__':
    get_active_model()
