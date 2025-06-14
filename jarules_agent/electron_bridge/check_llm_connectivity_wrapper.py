import json
import os
from datetime import datetime, timezone
import sys # For writing to stdout

# Attempt to import LLMManager and related error types
try:
    from jarules_agent.core.llm_manager import LLMManager
    from jarules_agent.connectors.base_llm_connector import LLMConnectorError
    # Specific exceptions from LLMManager or its components if known (e.g., config errors)
    # from jarules_agent.core.llm_manager import LLMConfigError # Assuming this might exist
except ImportError as e:
    # This script cannot function without these core components.
    # Output a JSON error message and exit if imports fail.
    def output_import_error_and_exit(import_error):
        error_result = {
            "id": "llm-connectivity-critical",
            "name": "LLM Connectivity Check - Setup Error",
            "status": "error",
            "message": "Critical error: Failed to import necessary JaRuLeS Agent modules.",
            "details": {
                "error_type": "ImportError",
                "error_message": str(import_error),
                "instructions": "Ensure JaRuLeS Agent is correctly installed and its modules are accessible in PYTHONPATH."
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        sys.stdout.write(json.dumps(error_result, indent=2))
        sys.stdout.flush()
        sys.exit(1) # Exit with error code
    output_import_error_and_exit(e)


def get_timestamp():
    """Generates an ISO 8601 timestamp string with Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def main():
    """
    Checks LLM connectivity using LLMManager and outputs the result as JSON.
    """
    check_result = {
        "id": "llm-connectivity",
        "name": "LLM Connectivity Check", # Default name
        "status": "error",  # Default to error
        "message": "Initialization error before check.",
        "details": {},
        "timestamp": get_timestamp()
    }

    try:
        # Construct path to llm_config.yaml relative to this script
        script_dir = os.path.dirname(__file__)
        config_path = os.path.join(script_dir, '..', '..', 'config', 'llm_config.yaml')
        config_path = os.path.normpath(config_path)

        if not os.path.exists(config_path):
            check_result["status"] = "error"
            check_result["message"] = "LLM configuration file (llm_config.yaml) not found."
            check_result["details"] = {
                "error_type": "FileNotFoundError",
                "expected_path": os.path.abspath(config_path),
                "instructions": "Ensure 'llm_config.yaml' is correctly placed in the 'config' directory."
            }
            check_result["timestamp"] = get_timestamp()
            sys.stdout.write(json.dumps(check_result, indent=2))
            sys.stdout.flush()
            return

        llm_manager = LLMManager(config_file_path=config_path)
        active_provider_connector = llm_manager.get_active_provider()
        active_provider_id = llm_manager.get_active_provider_id()

        if active_provider_connector is None or not active_provider_id:
            check_result["status"] = "warning" # Or "error" depending on severity perception
            check_result["name"] = "LLM Connectivity (No Active Provider)"
            check_result["message"] = "No active LLM provider is configured or enabled in llm_config.yaml."
            check_result["details"] = {
                "info": "Please select or configure an LLM provider in the configuration file.",
                "config_file_checked": os.path.abspath(config_path)
            }
        else:
            check_result["name"] = f"LLM Connectivity ({active_provider_id})"

            # The check_availability method is expected to be synchronous and return a dict
            # {'available': bool, 'details': str}
            availability_info = active_provider_connector.check_availability()

            if availability_info.get("available"):
                check_result["status"] = "success"
                check_result["message"] = f"Successfully connected to {active_provider_id}."
                check_result["details"] = {"provider_status": availability_info.get("details", "No additional details.")}
            else:
                check_result["status"] = "error"
                check_result["message"] = f"Failed to connect to {active_provider_id} or service is unavailable."
                check_result["details"] = {"provider_status": availability_info.get("details", "No specific error details provided by connector.")}

    # Example of how specific config errors from LLMManager could be caught if it raises them
    # except LLMConfigError as e:
    #     check_result["status"] = "error"
    #     check_result["name"] = "LLM Configuration Error"
    #     check_result["message"] = "Error processing LLM configuration."
    #     check_result["details"] = {
    #         "error_type": type(e).__name__,
    #         "error_message": str(e),
    #         "config_file_path": os.path.abspath(config_path if 'config_path' in locals() else "Unknown")
    #     }
    except LLMConnectorError as e: # Errors from the connector itself during check_availability or init
        check_result["status"] = "error"
        provider_id_info = llm_manager.get_active_provider_id() if 'llm_manager' in locals() else "Unknown Provider"
        check_result["name"] = f"LLM Connectivity ({provider_id_info})"
        check_result["message"] = f"Error with LLM provider '{provider_id_info}': {str(e)}"
        check_result["details"] = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "underlying_exception": str(e.underlying_exception) if hasattr(e, 'underlying_exception') and e.underlying_exception else "N/A"
        }
    except FileNotFoundError as e: # Should be caught by os.path.exists, but as a fallback for LLMManager init
        check_result["status"] = "error"
        check_result["message"] = "LLM configuration file not found during LLMManager initialization."
        check_result["details"] = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "tried_path": os.path.abspath(config_path if 'config_path' in locals() else "Unknown")
        }
    except Exception as e: # Catch-all for other unexpected errors
        check_result["status"] = "error"
        provider_id_info = llm_manager.get_active_provider_id() if 'llm_manager' in locals() else "Unknown"
        check_result["name"] = f"LLM Connectivity Check ({provider_id_info})"
        check_result["message"] = "An unexpected error occurred during LLM connectivity check."
        check_result["details"] = {
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

    check_result["timestamp"] = get_timestamp() # Final timestamp
    sys.stdout.write(json.dumps(check_result, indent=2))
    sys.stdout.flush()

if __name__ == "__main__":
    main()
