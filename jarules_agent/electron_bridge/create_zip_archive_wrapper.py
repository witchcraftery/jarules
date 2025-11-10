import json
import sys
import os

# Add the parent directory to the Python path to allow sibling imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from git_task_runners.parallel_task_orchestrator import ParallelTaskManager

def main():
    if len(sys.argv) != 4:
        print(json.dumps({"success": False, "error": "Invalid arguments. Expected runId, agentId, repoPath."}))
        sys.exit(1)

    run_id = sys.argv[1]
    agent_id = sys.argv[2]
    repo_path = sys.argv[3]

    manager = ParallelTaskManager(repo_path=repo_path)
    result = manager.create_zip_archive(run_id, agent_id)

    print(json.dumps(result))

if __name__ == "__main__":
    main()
