import sys
import json
import platform
from datetime import datetime, timezone

def main():
    """
    Performs a check of the Python environment and outputs the result as JSON.
    """
    check_result = {
        "id": "python-env",
        "name": "Python Environment Check",
        "status": "error", # Default to error
        "message": "Initialization error before check.",
        "details": {},
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    try:
        python_version_full = sys.version
        python_version_simple = python_version_full.split()[0] # Get the main version number like "3.9.7"
        platform_info = platform.platform()

        check_result["status"] = "success"
        check_result["message"] = f"Python environment check successful. Version: {python_version_simple}."
        check_result["details"] = {
            "python_version_full": python_version_full,
            "python_version_simple": python_version_simple,
            "platform_info": platform_info,
            "executable": sys.executable,
            "prefix": sys.prefix,
            "version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
                "releaselevel": sys.version_info.releaselevel,
                "serial": sys.version_info.serial
            }
        }

    except Exception as e:
        check_result["status"] = "error"
        check_result["message"] = "Failed to retrieve Python environment details due to an exception."
        check_result["details"] = {
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

    # Ensure timestamp is updated to reflect the actual check time, especially if an error occurred early
    check_result["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        sys.stdout.write(json.dumps(check_result, indent=2)) # Use indent for readability if stdout is manually checked
        sys.stdout.flush()
    except Exception as e:
        # Fallback if JSON serialization fails for some reason
        # This is highly unlikely with the current structure but good for extreme robustness
        fallback_error_output = {
            "id": "python-env",
            "name": "Python Environment Check",
            "status": "error",
            "message": "Failed to serialize check result to JSON.",
            "details": {"original_error": str(check_result), "serialization_error": str(e)},
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        sys.stdout.write(json.dumps(fallback_error_output, indent=2))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
