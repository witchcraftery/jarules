import json
import sys
import os

# Add the parent directory to the Python path to allow sibling imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from git_task_runners.parallel_task_orchestrator import ParallelTaskManager

def main():
    if len(sys.argv) != 5:
        print(json.dumps({"success": False, "error": "Invalid arguments. Expected runId, agentId, filePath, repoPath."}))
        sys.exit(1)

    run_id = sys.argv[1]
    agent_id = sys.argv[2]
    file_path = sys.argv[3]
    repo_path = sys.argv[4]

    manager = ParallelTaskManager(repo_path=repo_path)
    result = manager.get_file_content(run_id, agent_id, file_path)

    print(json.dumps(result))

if __name__ == "__main__":
    main()
