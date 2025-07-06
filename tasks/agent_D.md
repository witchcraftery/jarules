# Task Assignments for Agent D

## Active Tasks
---
---
### Task ID: TASKID-20231029-010000-AGD-IMPLRUNLLM
**Assigned:** 2023-10-29 01:00:00 UTC
**Status:** Implemented
**Title:** Sub-Task 1.2: Implement `run_llm_on_branch.py`

**Description:**
Based on the approved design for Sub-Task 1 (Backend & Git Orchestration) and its addenda, generate the complete, runnable Python code for `jarules_agent/git_task_runners/run_llm_on_branch.py`. This script must:
*   Accept command-line arguments (task_prompt, branch_name, base_branch, run_id, agent_id, llm_config_id).
*   Use `git_utils.py` (from Sub-Task 1.1) to manage Git branches (create/switch).
*   Interact with an LLM (structure for actual `LLMManager` integration, but use a placeholder/mock for direct LLM calls for now) to perform the given task. The LLM must be prompted to:
    1.  Save its primary outputs to files in the current working directory.
    2.  Generate a `solution_summary.md` file describing its approach and solution.
    3.  List the key files it created/modified (e.g., within `solution_summary.md` or as a separate manifest).
*   Parse the list of key files if provided separately by the LLM or from `solution_summary.md`.
*   Commit all outputs (generated files, `solution_summary.md`, any manifest) using `git_utils.py`.
*   Report status (starting, processing, completed, error) via structured JSON to stdout. The 'completed' status message must include `solutionSummary` content and the `keyFilePaths` list.
*   Include robust error handling for all operations.

**Acceptance Criteria:**
- Complete Python code for `jarules_agent/git_task_runners/run_llm_on_branch.py` is generated.
- The code is written to the specified file path by a subtask.
- The script correctly uses functions from the `git_utils.py` module.
- LLM interaction is clearly marked (e.g., placeholder function call) and designed for future integration with `LLMManager`.
- Logic for prompting/handling `solution_summary.md` and key file lists is included.
- Status reporting via JSON to stdout (including `solutionSummary` and `keyFilePaths` on completion) is implemented.
- Comprehensive error handling for script operations is present.
- The code is ready for external review and testing by the User/Project Manager.

**Notes/Plans by Agent D:**
**Last Plan Update:** 2023-10-29 02:00:00 UTC by Agent D
*(Timestamp is illustrative)*

**Verification Steps / Simulated Tests:**
1.  **Argument Parsing:** Review `argparse` setup to ensure all required arguments (`task_prompt`, `branch_name`, `base_branch`, `run_id`, `agent_id`, `llm_config_id`, `repo_path`) are correctly defined.
2.  **Git Operations:** Confirm that `git_utils` functions (`get_current_branch`, `switch_branch`, `create_branch`, `commit_changes`) are called with correct parameters (especially `repo_path`).
3.  **LLM Interaction Placeholder:** Verify the `mock_llm_interaction` function simulates the creation of `solution_summary.md` and example output files, and that the prompt augmentation instructions for the *actual* LLM (commented out) are clear about requiring the summary and key file list.
4.  **Summary & Key File Parsing:**
    *   Check logic for reading `SOLUTION_SUMMARY_FILENAME`.
    *   Review `parse_key_files_from_summary` for robustness with example summary content (e.g., handling different list formats, links, extra whitespace).
5.  **File Committing:** Ensure all expected files (LLM outputs, `solution_summary.md`, manifest if any) are included in `files_to_commit` and passed to `git_utils.commit_changes`.
6.  **Status Reporting:**
    *   Verify `report_status` is called at appropriate stages (starting, processing, completed, error).
    *   Confirm the "completed" status payload includes `solutionSummary` (content) and `keyFilePaths` (parsed list), and `committedFiles`.
    *   Check JSON serialization robustness in `report_status`.
7.  **Error Handling:** Review `try...except` blocks to ensure `git_utils.GitError` and general exceptions are caught, logged, and reported via `report_status` with an "error" status, and that the script exits with `sys.exit(1)`.
8.  **Path Handling:** Ensure `repo_path` is used consistently and that file paths (e.g., for `SOLUTION_SUMMARY_FILENAME`, LLM outputs) are correctly constructed (e.g., using `os.path.join`). Check handling of relative vs. absolute paths for `llm_generated_artifact_paths` before committing.

**Simulated Implementation Details:**

The following Python code has been generated and written to `jarules_agent/git_task_runners/run_llm_on_branch.py`:

```python
# jarules_agent/git_task_runners/run_llm_on_branch.py
import argparse
import json
import logging
import os
import sys
import time # For mock LLM delay
import re # For parsing key files from summary

try:
    from . import git_utils
except ImportError:
    import git_utils

logger = logging.getLogger(__name__)

SOLUTION_SUMMARY_FILENAME = "solution_summary.md"
KEY_FILES_SECTION_HEADER = "Key Output Files:"
PRIMARY_OUTPUT_FILENAME_TEMPLATE = "llm_output_{agent_id}.txt"

def report_status(status, run_id, agent_id, **kwargs):
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

def parse_key_files_from_summary(summary_content):
    if not summary_content:
        return []
    key_files = []
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
                file_path_candidate = match.group(1)
                link_match = re.match(r"\[.*?\]\((.*?)\)", file_path_candidate)
                if link_match:
                    key_files.append(link_match.group(1).strip())
                else:
                    key_files.append(file_path_candidate.strip().strip('`'))
            elif line.strip():
                pass
    logger.info(f"Parsed key files from summary: {key_files}")
    return key_files

def mock_llm_interaction(task_prompt, agent_id, branch_name, run_id, repo_path="."):
    logger.info(f"MOCK LLM: Simulating LLM interaction for prompt: {task_prompt[:100]}...")
    time.sleep(1)
    primary_output_filename = os.path.join(repo_path, PRIMARY_OUTPUT_FILENAME_TEMPLATE.format(agent_id=agent_id))
    example_code_file = os.path.join(repo_path, f"src/example_component_{agent_id}.vue")
    os.makedirs(os.path.dirname(example_code_file), exist_ok=True)
    with open(primary_output_filename, "w", encoding="utf-8") as f:
        f.write(f"LLM primary response to prompt: '{task_prompt}'\n")
        f.write(f"Content generated by agent {agent_id} for run {run_id} on branch {branch_name}.\n")
        f.write("This is simulated primary output content.\n")
    with open(example_code_file, "w", encoding="utf-8") as f:
        f.write(f"<template>\n  <div>Hello from {agent_id} on {branch_name}</div>\n</template>\n")
    logger.info(f"MOCK LLM: Primary output written to '{primary_output_filename}' and '{example_code_file}'.")
    summary_filename = os.path.join(repo_path, SOLUTION_SUMMARY_FILENAME)
    summary_content = f"""# Solution Summary for Agent {agent_id}

This is a mock solution summary for the task: \"{task_prompt[:50]}...\"

## Approach
The approach involved analyzing the request and generating the following components...

## Implemented Solution
A primary output file was created along with an example Vue component.

{KEY_FILES_SECTION_HEADER}
- `{os.path.basename(primary_output_filename)}`
- `{os.path.relpath(example_code_file, repo_path).replace(os.sep, '/')}`
- `another_generated_file.txt` (simulated non-existent for parsing test)
"""
    with open(summary_filename, "w", encoding="utf-8") as f:
        f.write(summary_content)
    logger.info(f"MOCK LLM: Solution summary written to '{summary_filename}'.")
    return [primary_output_filename, example_code_file, summary_filename]

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
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    if not logger.handlers:
        logging.basicConfig(level=log_level,
                            format=f'%(asctime)s - %(levelname)s - RID={args.run_id} AID={args.agent_id} - %(name)s - %(message)s',
                            stream=sys.stdout)
    logger.info(f"Script started. Task for LLM: '{args.task_prompt[:100]}...' on branch '{args.branch_name}'")
    report_status("starting", args.run_id, args.agent_id, message="Script initialized, preparing branch.")
    committed_files_final_list = []
    try:
        current_git_branch = git_utils.get_current_branch(repo_path=args.repo_path)
        if current_git_branch != args.branch_name:
            try:
                logger.info(f"Current branch is '{current_git_branch}'. Switching to '{args.branch_name}'.")
                git_utils.switch_branch(args.branch_name, repo_path=args.repo_path)
            except git_utils.GitError:
                logger.info(f"Branch '{args.branch_name}' not found. Creating from '{args.base_branch}'.")
                report_status("processing", args.run_id, args.agent_id, message=f"Creating branch {args.branch_name} from {args.base_branch}.")
                git_utils.create_branch(args.branch_name, base_branch_name=args.base_branch, repo_path=args.repo_path)
        else:
            logger.info(f"Already on correct branch '{args.branch_name}'.")
        report_status("processing", args.run_id, args.agent_id, message="Branch ready. Interacting with LLM.")
        llm_generated_artifact_paths = mock_llm_interaction(args.task_prompt, args.agent_id, args.branch_name, args.run_id, repo_path=args.repo_path)
        files_to_commit = [os.path.relpath(p, args.repo_path) if os.path.isabs(p) else p for p in llm_generated_artifact_paths]
        files_to_commit = [f.replace(os.sep, '/') for f in files_to_commit]
        summary_file_relpath = SOLUTION_SUMMARY_FILENAME
        if os.path.exists(os.path.join(args.repo_path, summary_file_relpath)) and summary_file_relpath not in files_to_commit:
            files_to_commit.append(summary_file_relpath)
        logger.info(f"LLM interaction complete. Files to commit: {files_to_commit}")
        report_status("processing", args.run_id, args.agent_id, message="LLM processing complete. Committing outputs.")
        if not files_to_commit:
            logger.warn("LLM interaction did not result in any files to commit.")
        else:
            commit_message = f"LLM work by agent {args.agent_id} for run {args.run_id} on task: {args.task_prompt[:30]}..."
            git_utils.commit_changes(commit_message, repo_path=args.repo_path, file_patterns_to_add=files_to_commit)
            logger.info(f"Committed files: {files_to_commit} with message: '{commit_message}'")
            committed_files_final_list.extend(files_to_commit)
        solution_summary_content = None
        key_file_paths_from_summary = []
        summary_file_abs_path = os.path.join(args.repo_path, SOLUTION_SUMMARY_FILENAME)
        if os.path.exists(summary_file_abs_path):
            with open(summary_file_abs_path, "r", encoding="utf-8") as f:
                solution_summary_content = f.read()
            logger.info(f"Read solution summary from '{summary_file_abs_path}'.")
            key_file_paths_from_summary = parse_key_files_from_summary(summary_content)
            key_file_paths_from_summary = [p.replace(os.sep, '/') for p in key_file_paths_from_summary]
        else:
            logger.warn(f"Solution summary file '{SOLUTION_SUMMARY_FILENAME}' not found in repo path '{args.repo_path}'.")
        final_key_files_list = list(set(key_file_paths_from_summary))
        report_status("completed", args.run_id, args.agent_id,
                      resultSummary=f"Task processing complete. Summary: {'Available' if solution_summary_content else 'Not available'}. Key files identified: {len(final_key_files_list)}.",
                      solutionSummary=solution_summary_content,
                      keyFilePaths=final_key_files_list,
                      committedFiles=committed_files_final_list
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

**Implementation Note:** The `run_llm_on_branch.py` script component is considered "Implemented". The overall Sub-Task 1 (Backend & Git Orchestration) for Agent D will be "Implemented" once `parallelTaskManager.js` design/code is also done.

**Key Decisions & Rationale:**
*(Agent D to fill if any deviations from original plan or new decisions are made during implementation)*

**Open Questions for Lead:**
*(Agent D to fill if any questions arise)*

**Dependencies:**
- Approved design for Sub-Task 1 and its addenda.
- Completed and available `jarules_agent/git_task_runners/git_utils.py` module.
- Structure of `LLMManager` and connectors (for future integration).

**Verification Steps / Simulated Tests:**
*(Agent D: Outline how you would manually verify or mentally walk through your generated code to ensure it meets requirements.)*

**Simulated Implementation Details:**
*(Agent D: Paste the full generated Python code here after creating it.)*

**Relevant Files/Links:**
- Agent D's Sub-Task 1 Plan & Addenda (conceptually in `tasks/completed_tasks/agent_D/`)
- `jarules_agent/git_task_runners/git_utils.py`
- `resourcing/sub-agent-briefing-guide.md`
- `development-status.md` (for payload details of status messages)
---
---
### Task ID: TASKID-20231028-230000-AGD-IMPLGITUTILS
**Assigned:** 2023-10-28 23:00:00 UTC
**Status:** Implemented (Revised)
**Title:** Sub-Task 1.1: Implement `git_utils.py`

**Description:**
Based on the approved design for Sub-Task 1 (Backend & Git Orchestration) and its relevant addenda (for solution summaries, key file lists, and zipping functionality), generate the complete, runnable Python code for the module `jarules_agent/git_task_runners/git_utils.py`. This module is critical and must provide robust Git operations including, but not limited to:
*   Getting current branch.
*   Creating and switching branches.
*   Adding and committing changes.
*   Generating diffs.
*   Deleting branches.
*   A function to archive a branch's content as a zip file (e.g., `archive_branch_to_zip(branch_name, output_zip_path, repo_path)`), which should use `git archive`.
All functions should include proper error handling (raising `GitError`) and logging.

**Acceptance Criteria:**
- Complete Python code for `jarules_agent/git_task_runners/git_utils.py` is generated.
- The code is written to the specified file path by a subtask.
- The generated code directly implements all functions defined in the approved design for `git_utils.py` and the new `archive_branch_to_zip` function.
- Error handling (custom `GitError`) and logging are implemented as per the design.
- The module is self-contained or uses only standard Python libraries.
- The code is ready for external review and testing by the User/Project Manager.

**Notes/Plans by Agent D:**
REVISION REQUESTED (2023-10-29): Incorporate `branch_exists` check in `create_branch` for `base_branch_name` validation. Add `branch_exists` function.
**Last Plan Update:** 2023-10-29 03:00:00 UTC by Agent D
*(Timestamp is illustrative)*

**Revision Summary (2023-10-29):**
- Added new function `branch_exists(branch_name, repo_path=None)` to check for local branch existence using `git rev-parse --verify refs/heads/{branch_name}`.
- Modified `create_branch()` to use `branch_exists()` to validate `base_branch_name`. If the base branch does not exist, `create_branch()` now raises a `GitError`.
- Modified `switch_branch()` to use `branch_exists()` and raise a `GitError` if the target branch for switching does not exist.
- Modified `archive_branch_to_zip()` to use `branch_exists()` and raise a `GitError` if the branch to be archived does not exist.
- Updated the `if __name__ == '__main__':` test block to include tests for these new checks and scenarios.

**Verification Steps / Simulated Tests (Updated):**
1.  **Code Review:** Read through the *revised* `git_utils.py` code.
2.  **`branch_exists` Function:** Verify its logic using `git rev-parse --verify` and that it correctly returns True/False.
3.  **`create_branch` Validation:** Confirm `base_branch_name` is validated using `branch_exists` and `GitError` is raised for a non-existent base.
4.  **`switch_branch` Validation:** Confirm target branch is validated using `branch_exists`.
5.  **`archive_branch_to_zip` Validation:** Confirm branch to be archived is validated using `branch_exists`.
6.  **Command Correctness, Error Path Analysis, Logging, Parameter Usage:** Re-verify these for all functions.
7.  **Test Block Review:** Ensure the `if __name__ == '__main__':` block now adequately tests the new validation logic.

**Simulated Implementation Details:**

The following *revised* Python code has been generated and written to `jarules_agent/git_task_runners/git_utils.py`:

```python
# jarules_agent/git_task_runners/git_utils.py
import subprocess
import logging
import shlex
import os
import sys
import time

logger = logging.getLogger(__name__)

class GitError(Exception):
    """Custom exception for Git command errors."""
    pass

def _run_git_command(command_list, cwd=None, check_return_code=True):
    """
    Helper function to run a Git command and handle common errors.
    """
    if cwd is None:
        pass # Will use current CWD of the process

    try:
        logger.debug(f"Running Git command: \"{' '.join(command_list)}\" in CWD: \"{cwd or os.getcwd()}\"")

        process = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd
        )

        if check_return_code and process.returncode != 0:
            error_message = (
                f"Git command \"{' '.join(command_list)}\" failed with exit code {process.returncode}.\n"
                f"Stderr: {process.stderr.strip()}"
            )
            logger.error(error_message)
            raise GitError(error_message)

        if process.stderr and not check_return_code:
             logger.debug(f"Git command stderr: {process.stderr.strip()}")

        logger.debug(f"Git command stdout: {process.stdout.strip() if process.stdout else '<no stdout>'}")
        return process if not check_return_code else process.stdout.strip()

    except FileNotFoundError:
        logger.error("Git command not found. Ensure Git is installed and in PATH.")
        raise GitError("Git command not found. Ensure Git is installed and in PATH.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while running git command \"{' '.join(command_list)}\": {e}")
        raise GitError(f"An unexpected error occurred running \"{' '.join(command_list)}\": {e}")

def branch_exists(branch_name, repo_path=None):
    """Checks if a local branch exists."""
    logger.info(f"Checking if branch '{branch_name}' exists in repo: {repo_path or 'current CWD'}")
    try:
        process = _run_git_command(['git', 'rev-parse', '--verify', f'refs/heads/{branch_name}'], cwd=repo_path, check_return_code=False)
        return process.returncode == 0
    except GitError:
        return False


def get_current_branch(repo_path=None):
    """Gets the current active Git branch in the given repository path."""
    logger.info(f"Getting current branch for repo: {repo_path or 'current CWD'}")
    return _run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path)

def create_branch(new_branch_name, base_branch_name=None, repo_path=None):
    """
    Creates a new Git branch.
    If base_branch_name is provided, checks if it exists, then creates the new branch from it.
    Otherwise, new branch is created from the current HEAD.
    Switches to the new branch after creation.
    """
    action = f"Creating new branch '{new_branch_name}'"
    command = ['git', 'checkout', '-b', new_branch_name]

    if base_branch_name:
        logger.info(f"Base branch '{base_branch_name}' specified for new branch '{new_branch_name}'. Verifying base branch exists...")
        if not branch_exists(base_branch_name, repo_path=repo_path):
            error_msg = f"Base branch '{base_branch_name}' does not exist. Cannot create new branch '{new_branch_name}' from it."
            logger.error(error_msg)
            raise GitError(error_msg)
        logger.info(f"Base branch '{base_branch_name}' verified.")
        action += f" from '{base_branch_name}'"
        command.append(base_branch_name)

    logger.info(action + f" in repo: {repo_path or 'current CWD'}")
    _run_git_command(command, cwd=repo_path)
    logger.info(f"Successfully created and switched to branch '{new_branch_name}'.")

def switch_branch(branch_name, repo_path=None):
    """Switches to an existing Git branch."""
    logger.info(f"Switching to branch '{branch_name}' in repo: {repo_path or 'current CWD'}")
    if not branch_exists(branch_name, repo_path=repo_path):
        error_msg = f"Cannot switch to branch '{branch_name}' because it does not exist."
        logger.error(error_msg)
        raise GitError(error_msg)
    _run_git_command(['git', 'checkout', branch_name], cwd=repo_path)
    logger.info(f"Successfully switched to branch '{branch_name}'.")

def add_files(file_patterns=["."], repo_path=None):
    """Adds specified file patterns to staging."""
    logger.info(f"Staging file patterns: {file_patterns} in repo: {repo_path or 'current CWD'}")
    add_command = ['git', 'add'] + file_patterns
    _run_git_command(add_command, cwd=repo_path)
    logger.debug(f"Staged files matching: {file_patterns}")

def commit_changes(commit_message, repo_path=None, file_patterns_to_add=None):
    """
    Adds specified file patterns (if any) and commits changes.
    """
    logger.info(f"Attempting to commit with message: '{commit_message}' in repo: {repo_path or 'current CWD'}")

    if file_patterns_to_add:
        add_files(file_patterns_to_add, repo_path=repo_path)

    status_process = _run_git_command(['git', 'diff', '--staged', '--quiet'], cwd=repo_path, check_return_code=False)
    if status_process.returncode == 0:
        logger.info("No staged changes to commit.")
        return "No staged changes to commit."

    commit_command = ['git', 'commit', '-m', commit_message]
    result = _run_git_command(commit_command, cwd=repo_path)
    logger.info(f"Successfully committed changes with message: '{commit_message}'.")
    return result

def get_diff(branch1, branch2=None, repo_path=None):
    """
    Generates a diff.
    """
    if branch2:
        logger.info(f"Generating diff between '{branch1}' and '{branch2}' in repo: {repo_path or 'current CWD'}")
        command = ['git', 'diff', f'{branch1}..{branch2}']
    else:
        logger.info(f"Generating diff for '{branch1}' (against working tree/index) in repo: {repo_path or 'current CWD'}")
        command = ['git', 'diff', branch1]

    return _run_git_command(command, cwd=repo_path)

def delete_branch(branch_name, force=False, repo_path=None):
    """Deletes a Git branch."""
    logger.info(f"Deleting branch '{branch_name}' (force={force}) in repo: {repo_path or 'current CWD'}")
    command = ['git', 'branch', '-D' if force else '-d', branch_name]
    _run_git_command(command, cwd=repo_path) # Will raise GitError if branch doesn't exist and not force, or other issues.
    logger.info(f"Successfully deleted branch '{branch_name}'.")

def archive_branch_to_zip(branch_name, output_zip_path, repo_path=None):
    """
    Archives the specified branch to a zip file using 'git archive'.
    """
    logger.info(f"Archiving branch '{branch_name}' to '{output_zip_path}' in repo: {repo_path or 'current CWD'}")

    if not branch_exists(branch_name, repo_path=repo_path):
        error_msg = f"Branch '{branch_name}' does not exist. Cannot archive."
        logger.error(error_msg)
        raise GitError(error_msg)

    output_dir = os.path.dirname(output_zip_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

    command = ['git', 'archive', '--format=zip', f'--output={os.path.abspath(output_zip_path)}', branch_name]

    _run_git_command(command, cwd=repo_path)

    if os.path.exists(output_zip_path) and os.path.getsize(output_zip_path) > 0:
        logger.info(f"Successfully archived branch '{branch_name}' to '{output_zip_path}'.")
        return output_zip_path
    else:
        error_message = f"Archive operation for branch '{branch_name}' seemed to succeed but '{output_zip_path}' is missing or empty."
        logger.error(error_message)
        raise GitError(error_message)

if __name__ == '__main__':
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    logger.info("Testing git_utils.py (ensure you are in a safe test repository)...")
    test_repo_path = "."
    base_branch_for_test = "main" # Assuming 'main' exists, change if your default is different

    try:
        current_branch = get_current_branch(repo_path=test_repo_path)
        logger.info(f"Initial current branch: {current_branch}")
        if not branch_exists(base_branch_for_test, repo_path=test_repo_path):
            logger.error(f"Base branch for testing '{base_branch_for_test}' does not exist. Aborting some tests.")
            raise GitError(f"Test setup failed: base branch '{base_branch_for_test}' not found.")

        test_branch = "git-utils-revision-test-branch"

        logger.info(f"Attempting to delete test branch '{test_branch}' if it exists (forcefully)...")
        try:
            if get_current_branch(repo_path=test_repo_path) == test_branch:
                switch_branch(base_branch_for_test, repo_path=test_repo_path)
            if branch_exists(test_branch, repo_path=test_repo_path):
                delete_branch(test_branch, force=True, repo_path=test_repo_path)
                logger.info(f"Test branch '{test_branch}' pre-deleted.")
        except GitError as e:
            logger.info(f"Pre-delete of '{test_branch}' failed or not needed: {e}")

        logger.info(f"Testing branch_exists for non-existent branch: non-existent-branch")
        assert not branch_exists("non-existent-branch", repo_path=test_repo_path), "branch_exists failed for non-existent branch"
        logger.info("branch_exists for non-existent branch: Correctly returned False.")

        logger.info(f"Testing branch_exists for existent branch: {base_branch_for_test}")
        assert branch_exists(base_branch_for_test, repo_path=test_repo_path), f"branch_exists failed for existent branch {base_branch_for_test}"
        logger.info(f"branch_exists for {base_branch_for_test}: Correctly returned True.")

        logger.info(f"Creating test branch: {test_branch} from {base_branch_for_test}")
        create_branch(test_branch, base_branch_name=base_branch_for_test, repo_path=test_repo_path)

        logger.info(f"Current branch after create: {get_current_branch(repo_path=test_repo_path)}")
        assert get_current_branch(repo_path=test_repo_path) == test_branch, "Not on the new test branch after creation."

        test_file_name = "test_git_utils_revision_file.txt"
        test_file_path = os.path.join(test_repo_path, test_file_name)
        if test_repo_path == ".":
            with open(test_file_path, "w") as f:
                f.write(f"Hello from {test_branch} at {time.time()}\n")

        logger.info(f"Committing changes to {test_branch}")
        commit_changes(f"Test commit on {test_branch}", repo_path=test_repo_path, file_patterns_to_add=[test_file_name])

        logger.info(f"Switching back to {base_branch_for_test}")
        switch_branch(base_branch_for_test, repo_path=test_repo_path)

        zip_file_name = "archive_revision_test_branch.zip"
        zip_file_full_path = os.path.join(test_repo_path, zip_file_name)
        if os.path.exists(zip_file_full_path):
            os.remove(zip_file_full_path)
        logger.info(f"Archiving {test_branch} to {zip_file_full_path}")
        archive_branch_to_zip(test_branch, zip_file_full_path, repo_path=test_repo_path)
        logger.info(f"Zip file created at: {zip_file_full_path}, size: {os.path.getsize(zip_file_full_path)} bytes")

        logger.info(f"Testing create_branch with non-existent base:")
        try:
            create_branch("another-test", base_branch_name="non-existent-base", repo_path=test_repo_path)
        except GitError as e:
            logger.info(f"Correctly caught error for non-existent base: {e}")
            assert "non-existent-base" in str(e), "Error message for non-existent base branch is incorrect."


    except GitError as e:
        logger.error(f"A Git utility error occurred during testing: {e}")
    except AssertionError as e:
        logger.error(f"Assertion failed during testing: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during testing: {e}", exc_info=True)
    finally:
        logger.info(f"Cleaning up: Ensuring switch back to {current_branch if 'current_branch' in locals() else base_branch_for_test}")
        try:
            if get_current_branch(repo_path=test_repo_path) != (current_branch if 'current_branch' in locals() else base_branch_for_test):
                 switch_branch(current_branch if 'current_branch' in locals() else base_branch_for_test, repo_path=test_repo_path)
        except Exception:
            pass

        logger.info(f"Cleaning up: Deleting test branch '{test_branch}' if it exists...")
        try:
            if branch_exists(test_branch, repo_path=test_repo_path): # Check before delete
                delete_branch(test_branch, force=True, repo_path=test_repo_path)
        except GitError as e:
            logger.warning(f"Could not clean up test branch '{test_branch}': {e}")

        if 'test_file_path' in locals() and os.path.exists(test_file_path):
            logger.info(f"Cleaning up: Deleting test file '{test_file_path}'")
            os.remove(test_file_path)
        if 'zip_file_full_path' in locals() and os.path.exists(zip_file_full_path):
            logger.info(f"Cleaning up: Deleting test zip '{zip_file_full_path}'")
            os.remove(zip_file_full_path)
        logger.info("git_utils.py revision tests finished.")

```

**Implementation Note:** The `git_utils.py` component is now "Implemented (Revised)".

**Key Decisions & Rationale:**
*(Agent D to fill if any deviations from original plan or new decisions are made during implementation)*

**Open Questions for Lead:**
*(Agent D to fill if any questions arise)*

**Dependencies:**
- Approved design for `git_utils.py` from Sub-Task 1 planning and addenda.

**Verification Steps / Simulated Tests:**
*(Agent D: Outline how you would manually verify or mentally walk through your generated code to ensure it meets requirements. E.g., "1. Review each function against design specs. 2. Check subprocess calls for correctness. 3. Verify error handling paths.")*

**Simulated Implementation Details:**
*(Agent D: Paste the full generated Python code here after creating it.)*

**Relevant Files/Links:**
- Agent D's original Sub-Task 1 Plan & Addenda (conceptually in `tasks/completed_tasks/agent_D/`)
- `resourcing/sub-agent-briefing-guide.md`
---

## Completed Tasks
---

## Backlog / Future Tasks
---
