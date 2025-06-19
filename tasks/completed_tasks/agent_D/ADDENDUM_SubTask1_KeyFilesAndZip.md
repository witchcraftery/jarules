# Addendum 02 to Sub-Task 1 (Agent D - Backend Orchestration) - Key File Listing & Zipping
**Date of Addendum:** 2023-10-28
*(Timestamp is illustrative)*
**Original Task ID(s) Affected:** All tasks involving `run_llm_on_branch.py` and `parallelTaskManager.js` from Agent D's original Sub-Task 1 plan.
**Previous Addendum:** `ADDENDUM_SubTask1_SolutionSummary.md` (This addendum builds upon and should be considered alongside it).

This addendum outlines further modifications required for Sub-Task 1 to support enhanced UI previews, specifically the listing of key output files by LLMs and on-demand zipping of an agent's branch content.

**1. Modifications to `run_llm_on_branch.py`:**

*   **LLM Prompting for Key Files:**
    *   Building on the requirement for a `solution_summary.md`, the LLM prompt must also instruct the agent to list the primary file paths it created or significantly modified. This list should be provided in a structured way, ideally within the `solution_summary.md` (e.g., a specific section) or as a separate machine-readable file (e.g., `output_manifest.json`).
    *   Example addition to prompt: `"In your 'solution_summary.md', include a section at the end titled 'Key Output Files:' followed by a bulleted list of the relative paths to the most important files you have generated or modified for this task."`
*   **Extracting Key File List:**
    *   The Python script, after the LLM completes, will need to parse `solution_summary.md` (or `output_manifest.json`) to extract this list of key file paths.
*   **Updating "Completed" Status Message:**
    *   The JSON payload for the "completed" status message sent to `main.js` must now include:
        *   `solutionSummary` (content of `solution_summary.md`, as per Addendum 01).
        *   `keyFilePaths` (an array of strings, e.g., `["src/components/MyComponent.vue", "docs/feature.md"]`).
            ```python
            # Example snippet for run_llm_on_branch.py
            # ... (logic to get solution_summary_content and parse key_file_paths) ...

            report_status("completed", args.run_id, args.agent_id,
                          resultSummary=f"LLM work complete. Summary: {'Available' if solution_summary_content else 'N/A'}. Key files: {len(key_file_paths) if key_file_paths else 0}",
                          solutionSummary=solution_summary_content,
                          keyFilePaths=key_file_paths, # New field
                          generated_files=[output_filename, summary_filename] + (key_file_paths if key_file_paths else []) # Ensure all are committed
                         )
            ```
*   **Committing Files:** Ensure `solution_summary.md` and any manifest file (like `output_manifest.json`) are committed to the branch along with other generated files.

**2. New Zipping Functionality (Python - e.g., new script `zip_agent_branch.py` or util in `git_utils.py`)**

*   **Purpose:** To create a zip archive of the specified agent's branch content.
*   **Inputs:** `branch_name`, `output_zip_path` (temporary path for the zip file). Optional: `repo_path`.
*   **Logic:**
    1.  Temporarily check out the `branch_name` or use `git archive`. Using `git archive` is preferred:
        ```python
        # Example using git archive (preferred)
        # command = ['git', 'archive', '--format=zip', f'--output={output_zip_path}', branch_name]
        # subprocess.run(command, cwd=repo_path, check=True)
        ```
    2.  The script should exclude `.git` directory and potentially other specified ignore patterns (`git archive` handles this well).
    3.  Return success/failure and the path to the zip file (e.g., via JSON output to stdout).
*   This script will be called by `parallelTaskManager.js`.

**3. Modifications to `parallelTaskManager.js` (Electron Main Process)**

*   **`AgentTask` Data Structure:**
    *   Add `keyFilePaths: (Array<string>, nullable)` to store the list of key file paths received from the Python script.
    *   ( `solutionSummary` field already added by previous addendum).
*   **`handleIncomingMessage` Function:**
    *   When processing a "completed" status message, extract `keyFilePaths` from the payload and store it in `agentTask.keyFilePaths`.
*   **New Function: `async handleTriggerAgentVersionZip({ runId, agentId })`:**
    *   **Purpose:** Handles the `'trigger-agent-version-zip'` IPC call from the UI.
    *   **Logic:**
        1.  Retrieve `run` and `agentTask`.
        2.  Construct a temporary output path for the zip file.
        3.  Call the new Python zipping script using `PythonShell`, passing `agentTask.branchName` and the output path.
        4.  On success: Return `{ success: true, downloadPath: temp_zip_path_reported_by_script }`.
        5.  On failure: Return `{ success: false, error: "Failed to create zip archive." }`.

**Reason for Change:**
To support enhanced UI previews by:
1.  Allowing the UI (Agent F) to know which specific files are most relevant to display for an agent's solution, as identified by the LLM agent itself.
2.  Enabling a "Download Project Files for this Version" feature in the UI.
