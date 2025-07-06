```python
# jarules_agent/git_task_runners/run_llm_on_branch.py
import argparse
import json
import logging
import os
import sys
import time
import re

try:
    from . import git_utils
except ImportError:
    import git_utils

logger = logging.getLogger(__name__)

# --- Configuration ---
SOLUTION_SUMMARY_FILENAME = "solution_summary.md"
KEY_FILES_SECTION_HEADER = "Key Output Files:" # Expected header in solution_summary.md
PRIMARY_OUTPUT_FILENAME_TEMPLATE = "llm_output_{agent_id}.txt"

def report_status(status, run_id, agent_id, **kwargs):
    """Helper function to print status updates as JSON to stdout."""
    payload = {
        "status": status,
        "runId": run_id,
        "agentId": agent_id,
    }
    payload.update(kwargs)
    try:
        print(json.dumps(payload), flush=True)
    except TypeError as e:
        logger.error(f"TypeError serializing status payload: {e}. Payload: {payload}")
        print(json.dumps({"status": "error", "runId": run_id, "agentId": agent_id,
                          "errorMessage": "Internal error: Could not serialize status payload."}), flush=True)

def validate_repo_path(path_str):
    """Validates the provided repository path."""
    abs_path = os.path.abspath(path_str)
    if not os.path.exists(abs_path):
        raise ValueError(f"Repository path does not exist: {abs_path}")
    if not os.path.isdir(abs_path):
        raise ValueError(f"Repository path is not a directory: {abs_path}")
    if not os.path.isdir(os.path.join(abs_path, ".git")):
        logger.warning(f"Path {abs_path} does not appear to be a Git repository (missing .git directory).")
    return abs_path

def parse_key_files_from_summary(summary_content, repo_path):
    """
    Parses a list of key file paths from the solution summary content.
    Filters for files that actually exist within the repo_path.
    """
    if not summary_content:
        return []

    parsed_files = []
    in_key_files_section = False
    list_item_regex = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")

    for line in summary_content.splitlines():
        if line.strip() == KEY_FILES_SECTION_HEADER:
            in_key_files_section = True
            continue

        if in_key_files_section:
            if not line.strip() or line.startswith("#"):
                break
            match = list_item_regex.match(line)
            if match:
                file_path_candidate = match.group(1).strip()
                link_match = re.match(r"\[.*?\]\((.*?)\)", file_path_candidate)
                path_to_check_relative = link_match.group(1).strip() if link_match else file_path_candidate.strip('`')

                if os.path.isabs(path_to_check_relative):
                    logger.warning(f"Found absolute path in summary's key file list: {path_to_check_relative}. Considering it as relative to repo root.")
                    path_to_check_relative = os.path.relpath(path_to_check_relative, repo_path)

                full_path_to_check = os.path.join(repo_path, path_to_check_relative)

                if os.path.exists(full_path_to_check) and os.path.isfile(full_path_to_check):
                    parsed_files.append(path_to_check_relative.replace(os.sep, '/'))
                else:
                    logger.warning(f"Key file listed in summary not found or not a file: '{path_to_check_relative}' (resolved to '{full_path_to_check}')")
            elif line.strip():
                pass

    logger.info(f"Parsed and validated key files from summary: {parsed_files}")
    return parsed_files


# TODO: LLM INTEGRATION - Replace mock_llm_interaction with actual LLMManager integration.
# This will involve:
# 1. Importing LLMManager: from jarules_agent.core.llm_manager import LLMManager
# 2. Initializing LLMManager: llm_manager = LLMManager(config_path=os.path.join(args.repo_path, "config/llm_config.yaml"))
# 3. Getting the connector: connector = llm_manager.get_connector(args.llm_config_id)
#    - args.llm_config_id will be used here to select the appropriate model and its parameters (temperature, max_tokens, etc.)
# 4. Crafting a detailed prompt that instructs the LLM to:
#    a. Perform the core task.
#    b. Save outputs to specific files in `args.repo_path`.
#    c. Create `SOLUTION_SUMMARY_FILENAME` with a description of its work.
#    d. Within that summary (or a separate manifest), list the key files it created/modified under `KEY_FILES_SECTION_HEADER`.
# 5. Calling a method on the connector, e.g., `connector.generate_structured_output(prompt, output_dir=args.repo_path)`
#    which would need to return information about generated files or handle file creation itself.
def mock_llm_interaction(task_prompt, agent_id, branch_name, run_id, repo_path="."):
    """
    Placeholder for LLM interaction.
    This mock version creates a primary output file and a solution_summary.md.
    """
    logger.info(f"MOCK LLM: Simulating LLM interaction for prompt: {task_prompt[:100]}...")
    time.sleep(1)

    primary_output_filename = os.path.join(repo_path, PRIMARY_OUTPUT_FILENAME_TEMPLATE.format(agent_id=agent_id))
    example_code_file_relpath = os.path.join("src", f"example_component_{agent_id}.vue") # Relative path
    example_code_file_abs = os.path.join(repo_path, example_code_file_relpath)
    os.makedirs(os.path.dirname(example_code_file_abs), exist_ok=True)

    with open(primary_output_filename, "w", encoding="utf-8") as f:
        f.write(f"LLM primary response to prompt: '{task_prompt}'\n")
        f.write(f"Content generated by agent {agent_id} for run {run_id} on branch {branch_name}.\n")

    with open(example_code_file_abs, "w", encoding="utf-8") as f:
        f.write(f"<template>\n  <div>Hello from {agent_id} on {branch_name} in {example_code_file_relpath}</div>\n</template>\n")

    logger.info(f"MOCK LLM: Primary output written to '{primary_output_filename}' and '{example_code_file_abs}'.")

    summary_filename_abs = os.path.join(repo_path, SOLUTION_SUMMARY_FILENAME)
    key_files_for_summary = [
        os.path.basename(primary_output_filename),
        example_code_file_relpath.replace(os.sep, '/'),
        "docs/non_existent_file.md" # Test filtering
    ]
    key_files_markdown_list = "\n".join([f"- `{p}`" for p in key_files_for_summary])

    summary_content = f"""# Solution Summary for Agent {agent_id}
This is a mock solution summary for the task: \"{task_prompt[:50]}...\"
## Approach
The approach involved ...
## Implemented Solution
A primary output file and an example Vue component were created.
{KEY_FILES_SECTION_HEADER}
{key_files_markdown_list}
"""
    with open(summary_filename_abs, "w", encoding="utf-8") as f:
        f.write(summary_content)
    logger.info(f"MOCK LLM: Solution summary written to '{summary_filename_abs}'.")

    return [primary_output_filename, example_code_file_abs, summary_filename_abs]


def main():
    parser = argparse.ArgumentParser(description="Run an LLM task on a specific Git branch.")
    parser.add_argument("--task_prompt", required=True, help="The detailed prompt for the LLM task.")
    parser.add_argument("--branch_name", required=True, help="The unique Git branch name for this task.")
    parser.add_argument("--base_branch", required=True, help="The base Git branch to branch off from or diff against.")
    parser.add_argument("--run_id", required=True, help="The unique ID for the overall parallel run.")
    parser.add_argument("--agent_id", required=True, help="The unique ID for this specific agent/task.")
    parser.add_argument("--llm_config_id", required=True, help="The ID of the LLM configuration to use.")
    parser.add_argument("--repo_path", default=".", help="Path to the repository root. Defaults to current directory.")
    args = parser.parse_args()

    # TODO: LOGGING STRATEGY - Consider a more centralized logging setup, potentially configured
    # by the main application (e.g., Electron app) and passed to scripts, or using environment
    # variables more extensively for log levels and formats.
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    if not logger.handlers: # Ensure handlers are not added multiple times if script is re-run/imported
        handler = logging.StreamHandler(sys.stdout)
        # Include run_id and agent_id in log format for better traceability in parallel runs
        handler.setFormatter(logging.Formatter(f'%(asctime)s - %(levelname)s - RID={args.run_id} AID={args.agent_id} - %(name)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(log_level)
        # Also configure root logger if this script is the main entry point, for git_utils logs
        if __name__ == "__main__":
            logging.getLogger().addHandler(handler) # Add handler to root logger
            logging.getLogger().setLevel(log_level) # Set level for root logger

    try:
        validated_repo_path = validate_repo_path(args.repo_path)
        logger.info(f"Validated repo path: {validated_repo_path}")
    except ValueError as e:
        logger.error(f"Invalid repo_path: {e}")
        report_status("error", args.run_id, args.agent_id, errorMessage=f"Invalid repo_path: {e}", errorDetails=str(e))
        sys.exit(1)

    logger.info(f"Script started. Task for LLM: '{args.task_prompt[:100]}...' on branch '{args.branch_name}'")
    report_status("starting", args.run_id, args.agent_id, message="Script initialized, preparing branch.")

    committed_files_final_list = []

    try:
        current_git_branch = git_utils.get_current_branch(repo_path=validated_repo_path)
        if current_git_branch != args.branch_name:
            try:
                logger.info(f"Current branch is '{current_git_branch}'. Switching to '{args.branch_name}'.")
                git_utils.switch_branch(args.branch_name, repo_path=validated_repo_path)
            except git_utils.GitError as e:
                logger.info(f"Branch '{args.branch_name}' not found or switch failed ({e}). Creating from '{args.base_branch}'.")
                report_status("processing", args.run_id, args.agent_id, message=f"Creating branch {args.branch_name} from {args.base_branch}.")
                git_utils.create_branch(args.branch_name, base_branch_name=args.base_branch, repo_path=validated_repo_path)
        else:
            logger.info(f"Already on correct branch '{args.branch_name}'.")

        report_status("processing", args.run_id, args.agent_id, message="Branch ready. Interacting with LLM.")

        # TODO: LLM_CONFIG_ID USAGE - When LLMManager is integrated, args.llm_config_id will be crucial
        # for selecting the correct model, API key, and generation parameters (temperature, etc.)
        # from the llm_config.yaml file via the LLMManager.
        llm_generated_artifact_abs_paths = mock_llm_interaction(
            args.task_prompt, args.agent_id, args.branch_name, args.run_id, repo_path=validated_repo_path
        )

        files_to_commit_relative = []
        for abs_path in llm_generated_artifact_abs_paths:
            if os.path.exists(abs_path): # Ensure file reported by LLM (mock) actually exists
                rel_path = os.path.relpath(abs_path, validated_repo_path)
                files_to_commit_relative.append(rel_path.replace(os.sep, '/'))
            else:
                logger.warning(f"LLM mock reported file '{abs_path}' which does not exist. Skipping.")

        # Ensure summary file is included for commit if it exists, even if not in LLM output paths
        summary_file_relpath = SOLUTION_SUMMARY_FILENAME
        summary_file_abs_path_check = os.path.join(validated_repo_path, summary_file_relpath)
        if os.path.exists(summary_file_abs_path_check) and summary_file_relpath not in files_to_commit_relative:
            files_to_commit_relative.append(summary_file_relpath)

        files_to_commit_relative = sorted(list(set(files_to_commit_relative))) # Unique, sorted

        logger.info(f"LLM interaction complete. Files to commit: {files_to_commit_relative}")
        report_status("processing", args.run_id, args.agent_id, message="LLM processing complete. Committing outputs.")

        if not files_to_commit_relative:
            logger.warn("LLM interaction did not result in any existing files to commit.")
        else:
            commit_message = f"LLM work by agent {args.agent_id} for run {args.run_id} on task: {args.task_prompt[:30]}..."
            git_utils.commit_changes(commit_message, repo_path=validated_repo_path, file_patterns_to_add=files_to_commit_relative)
            logger.info(f"Committed files: {files_to_commit_relative} with message: '{commit_message}'")
            committed_files_final_list.extend(files_to_commit_relative)

        solution_summary_content = None
        key_file_paths_from_summary = []
        summary_file_abs_path_read = os.path.join(validated_repo_path, SOLUTION_SUMMARY_FILENAME)

        if os.path.exists(summary_file_abs_path_read) and os.path.getsize(summary_file_abs_path_read) > 0: # Validate size
            with open(summary_file_abs_path_read, "r", encoding="utf-8") as f:
                solution_summary_content = f.read()
            logger.info(f"Read solution summary from '{summary_file_abs_path_read}'.")
            # Filter key files to ensure they exist before reporting
            key_file_paths_from_summary = parse_key_files_from_summary(solution_summary_content, validated_repo_path)
        elif os.path.exists(summary_file_abs_path_read):
             logger.warn(f"Solution summary file '{SOLUTION_SUMMARY_FILENAME}' found but is empty.")
        else:
            logger.warn(f"Solution summary file '{SOLUTION_SUMMARY_FILENAME}' not found in repo path '{validated_repo_path}'.")

        final_key_files_list = key_file_paths_from_summary # Already filtered by parse_key_files_from_summary

        report_status("completed", args.run_id, args.agent_id,
                      resultSummary=f"Task processing complete. Summary: {'Available' if solution_summary_content else 'Not available'}. Key files reported by LLM: {len(final_key_files_list)}.",
                      solutionSummary=solution_summary_content,
                      keyFilePaths=final_key_files_list,
                      committedFiles=committed_files_final_list # List of files actually committed
                     )
        logger.info("Task completed successfully.")

    except git_utils.GitError as e:
        error_msg = f"A Git operation failed: {e}"
        logger.error(error_msg, exc_info=True)
        report_status("error", args.run_id, args.agent_id, errorMessage=error_msg, errorDetails=str(e))
        sys.exit(1)
    except Exception as e:
        error_msg = f"An unexpected error occurred in run_llm_on_branch.py: {e}"
        logger.error(error_msg, exc_info=True)
        report_status("error", args.run_id, args.agent_id, errorMessage=error_msg, errorDetails=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()

```
