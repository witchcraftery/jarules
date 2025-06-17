# Development Status & Project Dashboard

This document tracks the overall development status, current priorities, feature progress, and key integration points for the JaRules project.

## Overall Project Status

*   **Current Focus:** Electron UI - Phase 2.5: Asynchronous Git-Split Task Completion.
*   **Next Up:** Electron UI - Phase 3: Polish & Packaging, Advanced Agent Features.
*   **Overall Health:** Green (Active development, new workflow process being implemented).

## Current Priorities (as of YYYY-MM-DD)
*(To be updated by Lead Planner/User)*

1.  Complete planning for all sub-tasks of "Electron UI - Phase 2.5".
2.  Begin (simulated) implementation of Phase 2.5 sub-tasks in order, starting with backend/core logic.
3.  Refine and solidify the new task management and documentation workflow.

## Feature/Phase Status

*(To be updated by Lead Planner as major features/phases progress)*

*   **Electron UI - Phase 1 (Core Chat Experience):** ✅ Completed
*   **Multi-LLM Backend & CLI Switching:** ✅ Completed
*   **Agent Task Management Workflow Refinement:** 🔄 In Progress (Guide updated, this status file created)
*   **Electron UI - Phase 2 (Advanced Features - In-App Config, Stop Gen, Diagnostics):**
    *   Tasks defined, awaiting planning/assignment using new system.
*   **Electron UI - Phase 2.5 (Async Git-Split Task Completion):** 🔄 In Progress
    *   Sub-Task 1 (Agent D - Backend & Git Orchestration): Detailed design complete & approved. (Simulated implementation pending/next)
    *   Sub-Task 2 (Agent E - Task Definition & Agent Selection UI): Detailed plan and simulated implementation design complete. (Awaiting final review & archival)
    *   Sub-Task 3 (Agent F - Results Preview & Finalization UI): Task assigned in `tasks/agent_F.md`. Status: New.
    *   Sub-Task 4 (Agent G - IPC Interface Implementation): Task assigned in `tasks/agent_G.md`. Status: New.

## Integration Points & Dependencies

This section tracks key interfaces, modules, or data contracts that span across different sub-tasks or agents, and their current status.

| Dependency / Integration Point             | Description                                                                 | Provided By (Agent/Task) | Consumed By (Agent/Task)         | Status                                        | Notes                                                                 |
|--------------------------------------------|-----------------------------------------------------------------------------|--------------------------|----------------------------------|-----------------------------------------------|-----------------------------------------------------------------------|
| **IPC Channel: `'get-llm-configs'`**       | Fetches available LLM configurations from `llm_config.yaml`.                | Agent G (Sub-Task 4)     | Agent E (Sub-Task 2)             | Pending Definition & Implementation by Prov.  | Agent E's UI plan details the expected payload (Array of LLM Config Objects). |
| **IPC Channel: `'start-parallel-git-task'`** | Initiates a new parallel Git task run.                                      | Agent G (Sub-Task 4)     | Agent E (Sub-Task 2)             | Pending Definition & Implementation by Prov.  | Agent E's UI plan details payload. Backend by Agent D (Sub-Task 1).     |
| **`parallelTaskManager.js` API**           | Module in `main.js` for orchestrating backend Git & LLM tasks.              | Agent D (Sub-Task 1)     | Agent G (Sub-Task 4 - IPC Handlers) | Design Complete by Provider.                  | Agent G will write IPC handlers that call this API.                     |
| **IPC Channel: `'parallel-git-task-update'`**| Main process sends updates on individual agent task progress to UI.         | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Pending Definition & Implementation by Prov.  | Payload defined in `IMPLEMENTATION_GUIDE.md`. Originated by Agent D.    |
| **IPC Channel: `'parallel-git-run-completed'`**| Main process sends event when an entire parallel run is complete.           | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Pending Definition & Implementation by Prov.  | Payload defined in `IMPLEMENTATION_GUIDE.md`. Originated by Agent D.    |
| **IPC Channel: `'finalize-selected-git-version'`**| UI signals main process to finalize a selected agent's Git version.     | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Pending Definition & Implementation by Prov.  | Backend by Agent D.                                                   |
| **IPC Channel: `'retry-agent-git-task'`**  | UI signals main process to retry a specific agent's task.                 | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Pending Definition & Implementation by Prov.  | Backend by Agent D.                                                   |
| **IPC Channel: `'cancel-parallel-git-run'`**| UI signals main process to cancel an entire parallel run.                 | Agent G (Sub-Task 4)     | Agent F (Sub-Task 3)             | Pending Definition & Implementation by Prov.  | Backend by Agent D.                                                   |

*(Add more rows as new integration points are identified)*

---
*Note: Statuses for dependencies can be: "Pending Definition", "Defined", "Pending Implementation by Provider", "Implemented by Provider", "Needs Testing", "Available/Tested".*
