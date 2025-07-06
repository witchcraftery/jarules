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
    _run_git_command(command, cwd=repo_path)
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
    base_branch_for_test = "main"

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
            if branch_exists(test_branch, repo_path=test_repo_path):
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
