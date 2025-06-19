# Development Status & Project Dashboard

This document tracks the overall development status, current priorities, feature progress, and key integration points for the JaRules project.

## Overall Project Status

*   **Current Focus:** Electron UI - Phase 2.5: Asynchronous Git-Split Task Completion.
*   **Next Up:** Electron UI - Phase 3: Polish & Packaging, Advanced Agent Features.
*   **Overall Health:** Green (Active development, new workflow process being implemented).
*   **Key Process Update:** LLM Sub-Agents performing tasks (especially code generation/modification) are now required to produce a `solution_summary.md` file describing their approach and solution. This summary will be displayed in the UI.
    *   **Decision:** LLM agents are responsible for listing the key files they create/modify (as part of their summary or structured output).
    *   **Decision:** UI (Agent F) will use a Markdown-to-HTML library to render these summaries.
    *   **New Feature:** A "Download Agent Version as Zip" functionality will be added to the results preview UI.
    *   **Decision (Zip Download Flow):** The `'trigger-agent-version-zip'` IPC will return a temporary `downloadPath` and `filename` to the renderer. The renderer will then call a separate generic main process utility (e.g., `window.electron.requestFileDownload(path, filename)`) to initiate the OS download dialog.


## Current Priorities (as of YYYY-MM-DD)
*(To be updated by Lead Planner/User)*

1.  Finalize planning for all sub-tasks of "Electron UI - Phase 2.5".
2.  Formally approve plans for Agent F (Sub-Task 3) and Agent G (Sub-Task 4).
3.  Begin (simulated) implementation of Phase 2.5 sub-tasks, prioritizing Agent D (Backend), then Agent G (IPC), then Agent F (UI).


## Feature/Phase Status

*(To be updated by Lead Planner as major features/phases progress)*

*   **Electron UI - Phase 1 (Core Chat Experience):** ✅ Completed
*   **Multi-LLM Backend & CLI Switching:** ✅ Completed
*   **Agent Task Management Workflow Refinement:** ✅ Completed (Guide updated, status file active, archival process refined).
*   **Electron UI - Phase 2 (Advanced Features - In-App Config, Stop Gen, Diagnostics):**
    *   Tasks defined, awaiting planning/assignment using new system.
*   **Electron UI - Phase 2.5 (Async Git-Split Task Completion):** 🔄 In Progress
    *   Sub-Task 1 (Agent D - Backend & Git Orchestration): Detailed design complete & approved. Addenda for solution summary, key file lists, and zip functionality created/confirmed.
    *   Sub-Task 2 (Agent E - Task Definition & Agent Selection UI): Detailed plan and simulated implementation design **archived (granularly)**. `tasks/agent_E.md` is clear.
    *   Sub-Task 3 (Agent F - Results Preview & Finalization UI): Detailed plan (revised for summaries, code view, zip) **complete** in `tasks/agent_F.md` (Status: "Planning Complete"). Awaiting final approval.
    *   Sub-Task 4 (Agent G - IPC Interface Implementation): Detailed plan **complete** in `tasks/agent_G.md` (Status: "Planning Complete"). Awaiting final approval. Includes new IPCs for file content & zipping.



## Integration Points & Dependencies

This section tracks key interfaces, modules, or data contracts that span across different sub-tasks or agents, and their current status.

| Dependency / Integration Point             | Description                                                                 | Provided By (Agent/Task) | Consumed By (Agent/Task)         | Status                                        | Notes                                                                 |
|--------------------------------------------|-----------------------------------------------------------------------------|--------------------------|----------------------------------|-----------------------------------------------|-----------------------------------------------------------------------|
| **IPC Channel: `'get-llm-configs'`**       | Fetches available LLM configurations from `llm_config.yaml`.                | Agent G (Sub-Task 4)     | Agent E (Sub-Task 2)             | Planning Complete (Agent G)  | Agent E's UI plan (archived) details payload. |
| **IPC Channel: `'start-parallel-git-task'`** | Initiates a new parallel Git task run.                                      | Agent G (Sub-Task 4)     | Agent E (Sub-Task 2)             | Planning Complete (Agent G)  | Agent E's UI plan (archived) details payload. Backend by Agent D (Sub-Task 1).   |
| **`parallelTaskManager.js` API**           | Module in `main.js` for orchestrating backend Git & LLM tasks.              | Agent D (Sub-Task 1)     | Agent G (Sub-Task 4 - IPC Handlers) | Design Complete by Prov. Addenda for summary, key files, & zip. | Agent G will write IPC handlers that call this API.                     |
| **IPC Channel: `'parallel-git-task-update'`**| Main process sends updates on individual agent task progress to UI.         | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G)  | Payload defined in `IMPLEMENTATION_GUIDE.md`. Originated by Agent D. **"Completed" status payload to include `solutionSummary` content and `keyFilePaths` list.**    |
| **IPC Channel: `'parallel-git-run-completed'`**| Main process sends event when an entire parallel run is complete.           | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G)  | Payload defined in `IMPLEMENTATION_GUIDE.md`. Originated by Agent D.    |
| **IPC Channel: `'finalize-selected-git-version'`**| UI signals main process to finalize a selected agent's Git version.     | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G)  | Backend by Agent D.                                                   |
| **IPC Channel: `'retry-agent-git-task'`**  | UI signals main process to retry a specific agent's task.                 | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G)  | Backend by Agent D.                                                   |
| **IPC Channel: `'cancel-parallel-git-run'`**| UI signals main process to cancel an entire parallel run.                 | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G)  | Backend by Agent D.                                                   |
| **IPC Channel: `'get-agent-task-outputs'`** | Fetches solution summary and list of key file paths for an agent task.      | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G) | Returns `{ success, solutionSummary?, keyFilePaths?, error? }`. Backend by Agent D. |
| **IPC Channel: `'get-agent-file-content'` (New)** | Fetches content of a specific file for an agent task.                     | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G) | Args `{ runId, agentId, filePath }`. Returns `{ success, content?, error? }`. Backend by Agent D. |
| **IPC Channel: `'trigger-agent-version-zip'`** | UI requests a zip of an agent's branch content.                           | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Planning Complete (Agent G) | Returns `{ success, downloadPath?, filename?, error? }`. Renderer then calls `requestFileDownload`. Backend zipping by Agent D. |
| **Electron Utility: `requestFileDownload` (New)** | Main process utility to trigger OS download dialog for a given temp path. | General Main Process (Could be Agent G) | Agent F (Sub-Task 3 UI) | Definition Confirmed; Pending Implementation | Exposed via `preload.js` (e.g., `window.electron.requestFileDownload(path, filename)`). Handles temp file cleanup. |


*(Add more rows as new integration points are identified)*

---
*Note: Statuses for dependencies can be: "Pending Definition", "Defined", "Planning Complete (Provider)", "Pending Implementation by Provider", "Implemented by Provider", "Needs Testing", "Available/Tested".*
