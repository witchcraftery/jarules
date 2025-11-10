import asyncio
import json
import logging
import os
import sys
import uuid
from collections import defaultdict
import argparse

try:
    from . import git_utils
except ImportError:
    import git_utils

logger = logging.getLogger(__name__)

# Configuration
RUN_LLM_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "run_llm_on_branch.py")
DEFAULT_TEMP_DIR = os.path.join(os.path.expanduser("~"), ".jarules", "temp_archives")

# --- Helper Functions ---

def report_run_status(run_id, status, **kwargs):
    """Reports the overall status of the parallel run."""
    payload = {"runId": run_id, "overallStatus": status}
    payload.update(kwargs)
    print(json.dumps(payload), flush=True)

async def _read_stream(stream, run_id, agent_id, callback):
    """Reads and processes lines from a subprocess stream."""
    while True:
        line_bytes = await stream.readline()
        if not line_bytes:
            break
        line = line_bytes.decode('utf-8').strip()
        if line:
            try:
                update_data = json.loads(line)
                callback(update_data)
            except json.JSONDecodeError:
                logger.warning(f"RID={run_id} AID={agent_id} - Non-JSON output from subprocess: {line}")

def _get_python_executable():
    """Returns the path to the current Python executable."""
    return sys.executable

class ParallelTaskManager:
    def __init__(self, repo_path="."):
        self.repo_path = os.path.abspath(repo_path)
        self.active_runs = {}

    async def start_run(self, task_prompt, selected_agents, base_branch):
        run_id = str(uuid.uuid4())
        self.active_runs[run_id] = {
            "status": "starting",
            "agents": {agent['id']: {"status": "queued"} for agent in selected_agents},
            "tasks": []
        }
        report_run_status(run_id, "starting", message="Parallel run initiated.")

        try:
            original_branch = git_utils.get_current_branch(repo_path=self.repo_path)
        except git_utils.GitError as e:
            logger.error(f"Failed to get current branch: {e}")
            report_run_status(run_id, "error", errorMessage="Failed to get current git branch.", errorDetails=str(e))
            return

        def process_update_callback(update):
            """Callback to process status updates from subprocesses."""
            agent_id = update.get("agentId")
            if agent_id in self.active_runs[run_id]["agents"]:
                self.active_runs[run_id]["agents"][agent_id] = update
            print(json.dumps({"type": "agent_update", "data": update}), flush=True)

        agent_tasks = []
        for agent in selected_agents:
            agent_id = agent['id']
            branch_name = f"agent-{agent_id}-{run_id[:8]}"

            command = [
                _get_python_executable(),
                RUN_LLM_SCRIPT_PATH,
                "--task_prompt", task_prompt,
                "--branch_name", branch_name,
                "--base_branch", base_branch,
                "--run_id", run_id,
                "--agent_id", agent_id,
                "--llm_config_id", agent.get('id', 'default'),
                "--repo_path", self.repo_path,
            ]

            agent_tasks.append(self._run_agent_task(run_id, agent_id, command, process_update_callback))

        self.active_runs[run_id]["tasks"] = agent_tasks
        await asyncio.gather(*agent_tasks)

        # Final cleanup and status report
        self.cleanup_run(run_id, original_branch)
        report_run_status(run_id, "completed", message="All agents have finished processing.")

    async def _run_agent_task(self, run_id, agent_id, command, callback):
        """Creates and manages a single agent subprocess."""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.repo_path
        )

        # Concurrently read stdout and stderr
        await asyncio.gather(
            _read_stream(process.stdout, run_id, agent_id, callback),
            _read_stream(process.stderr, run_id, agent_id, callback) # Also process stderr for JSON error reports
        )

        await process.wait()
        logger.info(f"Subprocess for agent {agent_id} (run {run_id}) finished with exit code {process.returncode}.")

    def cleanup_run(self, run_id, original_branch):
        """Cleans up branches created during a run."""
        logger.info(f"Cleaning up run {run_id}. Switching back to '{original_branch}'.")
        try:
            git_utils.switch_branch(original_branch, repo_path=self.repo_path)
            run_data = self.active_runs.get(run_id, {})
            for agent_id in run_data.get("agents", {}):
                branch_name = f"agent-{agent_id}-{run_id[:8]}"
                if git_utils.branch_exists(branch_name, repo_path=self.repo_path):
                    logger.info(f"Deleting branch: {branch_name}")
                    git_utils.delete_branch(branch_name, force=True, repo_path=self.repo_path)
        except git_utils.GitError as e:
            logger.error(f"Error during cleanup for run {run_id}: {e}")
        finally:
            if run_id in self.active_runs:
                del self.active_runs[run_id]

    def get_run_status(self, run_id):
        return self.active_runs.get(run_id, {"status": "not_found"})

    def get_agent_outputs(self, run_id, agent_id):
        """Retrieves the final outputs of a specific agent task."""
        run = self.active_runs.get(run_id)
        if not run:
            return {"success": False, "error": "Run not found."}

        agent_data = run["agents"].get(agent_id)
        if not agent_data or agent_data.get("status") != "completed":
            return {"success": False, "error": "Agent task not completed or not found."}

        return {
            "success": True,
            "solutionSummary": agent_data.get("solutionSummary"),
            "keyFilePaths": agent_data.get("keyFilePaths", [])
        }

    def get_file_content(self, run_id, agent_id, file_path):
        branch_name = f"agent-{agent_id}-{run_id[:8]}"
        try:
            content = git_utils._run_git_command(['git', 'show', f'{branch_name}:{file_path}'], cwd=self.repo_path)
            return {"success": True, "content": content}
        except git_utils.GitError as e:
            return {"success": False, "error": f"Could not read file from branch: {e}"}

    def create_zip_archive(self, run_id, agent_id):
        branch_name = f"agent-{agent_id}-{run_id[:8]}"
        os.makedirs(DEFAULT_TEMP_DIR, exist_ok=True)
        zip_filename = f"run_{run_id}_agent_{agent_id}_{branch_name}.zip"
        output_zip_path = os.path.join(DEFAULT_TEMP_DIR, zip_filename)

        try:
            git_utils.archive_branch_to_zip(branch_name, output_zip_path, repo_path=self.repo_path)
            return {"success": True, "downloadPath": output_zip_path, "filename": zip_filename}
        except git_utils.GitError as e:
            return {"success": False, "error": f"Failed to create zip archive: {e}"}


async def main():
    parser = argparse.ArgumentParser(description="Orchestrate parallel LLM tasks on Git branches.")
    parser.add_argument("command", choices=['start', 'status', 'get_outputs', 'get_file', 'create_zip'])
    parser.add_argument("--run_id", help="The ID of the run for status/output commands.")
    parser.add_argument("--agent_id", help="The ID of the agent for output commands.")
    parser.add_argument("--file_path", help="The path of the file to retrieve content for.")
    parser.add_argument("--task_prompt", help="The task prompt for the 'start' command.")
    parser.add_argument("--agents", help="A JSON string of selected agents for the 'start' command.")
    parser.add_argument("--base_branch", default="main", help="The base branch for the 'start' command.")
    parser.add_argument("--repo_path", default=".", help="Path to the git repository.")

    args = parser.parse_args()

    # Basic logging setup
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    manager = ParallelTaskManager(repo_path=args.repo_path)

    if args.command == 'start':
        if not args.task_prompt or not args.agents:
            print(json.dumps({"success": False, "error": "Missing --task_prompt or --agents for start command."}))
            sys.exit(1)
        try:
            selected_agents = json.loads(args.agents)
        except json.JSONDecodeError:
            print(json.dumps({"success": False, "error": "Invalid JSON in --agents argument."}))
            sys.exit(1)

        await manager.start_run(args.task_prompt, selected_agents, args.base_branch)

    # Note: The other commands are designed to be called from another process, not via CLI like this.
    # This is a simplified CLI for testing the 'start' command.

if __name__ == "__main__":
    # Example Usage from CLI for testing the 'start' command:
    # python parallel_task_orchestrator.py start --task_prompt "Implement a new feature" --agents '[{"id": "gemini-pro"}, {"id": "claude-opus"}]'
    asyncio.run(main())
