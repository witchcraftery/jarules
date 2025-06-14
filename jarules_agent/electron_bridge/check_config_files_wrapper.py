import json
import os
from datetime import datetime, timezone

# Attempt to import ruamel.yaml, fallback to PyYAML
try:
    from ruamel.yaml import YAML
    yaml_parser = YAML(typ='safe') # typ='safe' is good practice
    def load_yaml(stream):
        return yaml_parser.load(stream)
    yaml_error_type = Exception # ruamel.yaml.YAMLError is broad; catch general Exception for its parsing
except ImportError:
    try:
        import yaml # PyYAML
        def load_yaml(stream):
            return yaml.safe_load(stream)
        yaml_error_type = yaml.YAMLError
    except ImportError:
        # If neither is available, YAML checking will fail more gracefully later
        load_yaml = None
        yaml_error_type = None
        # print("Warning: No YAML parser (ruamel.yaml or PyYAML) found. YAML file checks will be limited.", file=sys.stderr)

def get_timestamp():
    """Generates an ISO 8601 timestamp string with Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def check_single_file(file_path: str, file_id: str, friendly_name: str, parser_type: str) -> dict:
    """
    Checks a single configuration file (existence, readability, parsability).

    Args:
        file_path: Absolute or relative path to the file.
        file_id: A unique identifier for this check (e.g., "config-llm-yaml").
        friendly_name: A human-readable name for the file being checked.
        parser_type: 'json' or 'yaml'.

    Returns:
        A DiagnosticCheckResult dictionary.
    """
    result = {
        "id": file_id,
        "name": friendly_name,
        "status": "error",  # Default to error
        "message": "Check not fully performed.",
        "details": {"file_path": os.path.abspath(file_path)}, # Store absolute path for clarity
        "timestamp": get_timestamp()
    }

    if parser_type == 'yaml' and not load_yaml:
        result["status"] = "error"
        result["message"] = f"YAML parser (ruamel.yaml or PyYAML) is not installed. Cannot check {friendly_name}."
        result["details"]["error"] = "Missing YAML library."
        result["timestamp"] = get_timestamp()
        return result

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip(): # File is empty or contains only whitespace
            result["status"] = "warning"
            result["message"] = f"{friendly_name} exists but is empty or contains only whitespace."
            result["details"]["content_status"] = "Empty or whitespace-only"
            # Try to parse empty content to see if it's valid empty (for some parsers)
            try:
                if parser_type == 'json':
                    if content.strip() == "": # Truly empty string is not valid JSON
                        raise json.JSONDecodeError("Cannot parse empty string as JSON", "", 0)
                    json.loads(content) # Should fail for empty, succeed for "{}" or "[]"
                elif parser_type == 'yaml':
                    load_yaml(content) # YAML parsers usually handle empty content as None
                result["details"]["parsing_of_empty"] = "Considered valid empty by parser or check."
            except Exception as parse_empty_e:
                # If parsing empty content itself fails (e.g. json.loads(""))
                result["status"] = "error" # More severe than warning if parser outright rejects it
                result["message"] = f"{friendly_name} is empty and not considered valid by the {parser_type} parser."
                result["details"]["error"] = f"Error parsing empty content: {type(parse_empty_e).__name__}: {str(parse_empty_e)}"

        else: # File has content
            if parser_type == 'json':
                try:
                    json.loads(content)
                    result["status"] = "success"
                    result["message"] = f"{friendly_name} exists and parsed successfully."
                    result["details"]["parsing_status"] = "File parsed successfully."
                except json.JSONDecodeError as e:
                    result["status"] = "error"
                    result["message"] = f"Failed to parse {friendly_name} as JSON."
                    result["details"]["error"] = f"JSONDecodeError: {str(e)}"
                    result["details"]["line"] = e.lineno
                    result["details"]["column"] = e.colno
            elif parser_type == 'yaml':
                try:
                    load_yaml(content)
                    result["status"] = "success"
                    result["message"] = f"{friendly_name} exists and parsed successfully."
                    result["details"]["parsing_status"] = "File parsed successfully."
                except Exception as e: # Catching broad Exception for ruamel.yaml or yaml.YAMLError for PyYAML
                    result["status"] = "error"
                    result["message"] = f"Failed to parse {friendly_name} as YAML."
                    result["details"]["error"] = f"{type(e).__name__}: {str(e)}"
            else:
                result["status"] = "error"
                result["message"] = f"Unknown parser type '{parser_type}' for {friendly_name}."
                result["details"]["error"] = f"Invalid parser_type '{parser_type}' specified."

    except FileNotFoundError:
        result["status"] = "error"
        result["message"] = f"{friendly_name} not found at {os.path.abspath(file_path)}."
        result["details"]["error"] = "FileNotFoundError"
    except IOError as e: # Catch other I/O errors like permission denied
        result["status"] = "error"
        result["message"] = f"Error reading {friendly_name}: {str(e)}"
        result["details"]["error"] = f"IOError: {type(e).__name__}: {str(e)}"
    except Exception as e: # Catch-all for any other unexpected issues
        result["status"] = "error"
        result["message"] = f"An unexpected error occurred while checking {friendly_name}."
        result["details"]["error"] = f"Unexpected {type(e).__name__}: {str(e)}"

    result["timestamp"] = get_timestamp() # Update timestamp to final check time
    return result

def main():
    """
    Checks specified configuration files and prints results as JSON.
    """
    results = []

    # 1. llm_config.yaml
    # Path relative to this script: jarules_agent/electron_bridge/script.py -> jarules_agent/config/llm_config.yaml
    script_dir = os.path.dirname(__file__)
    llm_config_path = os.path.join(script_dir, '..', 'config', 'llm_config.yaml')
    # Normalize the path to resolve ".." etc.
    llm_config_path = os.path.normpath(llm_config_path)

    results.append(check_single_file(
        file_path=llm_config_path,
        file_id="config-llm-yaml",
        friendly_name="LLM Configuration (llm_config.yaml)",
        parser_type="yaml"
    ))

    # 2. user_state.json
    user_state_path = os.path.expanduser('~/.jarules/user_state.json')
    results.append(check_single_file(
        file_path=user_state_path,
        file_id="config-user-state-json",
        friendly_name="User State (user_state.json)",
        parser_type="json"
    ))

    try:
        # Use sys.stdout directly if available, otherwise print
        import sys
        sys.stdout.write(json.dumps(results, indent=2))
        sys.stdout.flush()
    except Exception: # Fallback to print if sys.stdout is problematic (e.g. in some test environments)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
