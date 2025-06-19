# Task Assignments for Agent G

## Active Tasks
---
### Task ID: TASKID-20231027-121000-AGG-IPCIF
**Assigned:** 2023-10-27 12:10:00 UTC
**Status:** Planning Complete
**Title:** Implement IPC Interface for Parallel Tasks (Phase 2.5) - *Revised for Solution Previews & Zipping*

**Description:**
Ensure robust and correct implementation of all client-side (renderer, via `preload.js`) and main-process side (`main.js`) aspects of the IPC channels dedicated to the parallel Git task functionality. This interface is the backbone for communication between the UI and the backend orchestration logic, supporting solution summary/code previews and on-demand zipping of agent versions. Reference `IMPLEMENTATION_GUIDE.md` and `development-status.md` for detailed payload structures.

**Key Requirements:**
1.  **Implement Renderer-to-Main IPC Calls (expose via `contextBridge` in `preload.js`, implement handlers in `main.js`):**
    *   `window.api.startParallelGitTask(taskDetails)`
    *   `window.api.finalizeSelectedGitVersion(finalizationDetails)`
    *   `window.api.retryAgentGitTask(retryDetails)`
    *   `window.api.cancelParallelRun(runId)`
    *   `window.api.getAgentTaskOutputs(args)`: Args `{ runId, agentId }`. Expected to return `{ success: boolean, solutionSummary?: string, keyFilePaths?: string[], files?: [{ path: string, content: string }], error?: string }`. (Payload refinement: `solutionSummary` and `keyFilePaths` are primary; `files` for direct content is secondary if `keyFilePaths` are used by UI to request content individually).
    *   **New:** `window.api.triggerAgentVersionZip(args)`: Args `{ runId, agentId }`. Expected to return `{ success: boolean, downloadPath?: string, error?: string }`.
2.  **Implement Main-to-Renderer Event Listeners (expose via `contextBridge` in `preload.js`, ensure `main.js` uses `webContents.send`):**
    *   `window.api.onParallelGitTaskUpdate(callback)`: "Completed" status payload from this should include `solutionSummary` (string) and `keyFilePaths` (array of strings).
    *   `window.api.onParallelGitRunCompleted(callback)`

3.  **Implement Listener Cleanup:** `window.api.cleanupParallelTaskListeners()`.
4.  **Data Validation & Error Handling:** For all IPC payloads and communication.

**Acceptance Criteria:**
- All specified `window.api` functions are available in the renderer process via `preload.js`.
- `main.js` correctly handles IPC calls, invoking appropriate logic in `parallelTaskManager.js` (from Agent D's Sub-Task 1, including its addenda).
- `main.js` handlers return asynchronous responses with correct payload structures as defined in `development-status.md` and this task.
    - `'get-agent-task-outputs'` returns solution summary, key file paths, and optionally file contents.
    - `'trigger-agent-version-zip'` returns success status and a temporary download path for the zip file.
- Renderer can successfully register callbacks for `onParallelGitTaskUpdate` and `onParallelGitRunCompleted`.
- `'parallel-git-task-update'` event for "completed" tasks correctly includes `solutionSummary` and `keyFilePaths` in its payload.
- `main.js` (via `parallelTaskManager.js`) correctly emits all Main-to-Renderer events with specified payloads.
- `cleanupParallelTaskListeners` function correctly removes listeners.
- Robust error handling for IPC communication failures or invalid payloads.

**Notes/Plans by Agent G:**
**Last Plan Update:** 2023-10-28 19:00:00 UTC by Agent G
*(Timestamp is illustrative)*

**Detailed Implementation Plan (2023-10-28 by Agent G - IPC Interface for Phase 2.5 Revised):**

**Overall Goal:** Implement all specified IPC channels in `preload.js` (for renderer exposure) and `main.js` (for handling and interaction with `parallelTaskManager.js`) to support the "Asynchronous Git-Split Task Completion" feature, including new requirements for solution summaries, key file lists, zip downloads, and on-demand file content fetching.

**I. General Setup and Conventions**

1.  **`preload.js` Structure (`jarules_electron_vue_ui/public/preload.js`):**
    *   All new IPC functions exposed under `window.api` via `contextBridge.exposeInMainWorld('api', { ... });`.
2.  **`main.js` Structure (`jarules_chat_ui/main.js`):**
    *   IPC handlers (`ipcMain.handle`) registered.
    *   Imports and uses functions from `parallelTaskManager.js`.
    *   Consistent error handling: `try...catch`, returning `{ success: false, error: message, details: error.stack }`.
3.  **Logging:** Basic `console.log` or dedicated logger for IPC calls and responses.
4.  **Payloads:** Adhere to structures in `development-status.md` and `IMPLEMENTATION_GUIDE.md`.

**II. Renderer-to-Main IPC Calls (Invoke/Handle Pattern)**

For each, `preload.js` exposes `channelName: (args) => ipcRenderer.invoke('ipc-channel-name', args)`, and `main.js` has `ipcMain.handle('ipc-channel-name', async (event, args) => { /* logic */ });`.

1.  **`startParallelGitTask(taskDetails)`**
    *   Channel: `'start-parallel-git-task'`
    *   `main.js`: Receives `taskDetails { taskDescription, selectedAgents }`. Generates `runId`. Calls `parallelTaskManager.startRun(runId, taskDetails.taskDescription, taskDetails.selectedAgents, event.sender)`. Returns `{ success: true, runId: runId }` or error.
2.  **`finalizeSelectedGitVersion(finalizationDetails)`**
    *   Channel: `'finalize-selected-git-version'`
    *   `main.js`: Receives `finalizationDetails { runId, selectedAgentId }`. Calls `parallelTaskManager.handleFinalizeVersion(runId, selectedAgentId, event.sender)`. Returns `{ success: true, message: "..." }` or error.
3.  **`retryAgentGitTask(retryDetails)`**
    *   Channel: `'retry-agent-git-task'`
    *   `main.js`: Receives `retryDetails { runId, agentId }`. Calls `parallelTaskManager.retryAgentTask(runId, agentId, event.sender)`. Returns `{ success: true, message: "..." }` or error.
4.  **`cancelParallelRun(args)`**
    *   Channel: `'cancel-parallel-git-run'`
    *   `main.js`: Receives `args { runId }`. Calls `parallelTaskManager.cancelRun(runId, event.sender)`. Returns `{ success: true, message: "..." }` or error.
5.  **`getAgentTaskOutputs(args)`**
    *   Channel: `'get-agent-task-outputs'`
    *   `main.js`: Receives `args { runId, agentId }`. Calls `parallelTaskManager.getAgentOutputs(runId, agentId)` (function in `parallelTaskManager.js`). Expected to retrieve stored `solutionSummary` and `keyFilePaths`. Returns `{ success: true, solutionSummary: "...", keyFilePaths: ["..."], error?: null }` or error. (Note: Does not return full file *contents* directly).
6.  **`triggerAgentVersionZip(args)` (New)**
    *   Channel: `'trigger-agent-version-zip'`
    *   `main.js`: Receives `args { runId, agentId }`. Calls `parallelTaskManager.handleTriggerAgentVersionZip(runId, agentId)`. Returns `{ success: true, downloadPath: "path/to/zip" }` or error.
7.  **`getAgentFileContent(args)` (New - Arising from Agent F's Q2 resolution)**
    *   Channel: `'get-agent-file-content'`
    *   `preload.js`: `getAgentFileContent: (args) => ipcRenderer.invoke('get-agent-file-content', args)`
    *   `main.js` Handler: Receives `args { runId, agentId, filePath }`. Calls a new function in `parallelTaskManager.js` (e.g., `getSpecificFileContent(runId, agentId, filePath)` which Agent D's plan needs to be addended for). Returns `{ success: boolean, content?: string, error?: string }`.

**III. Main-to-Renderer Event Emitters**

1.  **`onParallelGitTaskUpdate(callback)`**
    *   Channel: `'parallel-git-task-update'`
    *   `preload.js`: Exposes registration, returns individual cleanup function.
    *   `main.js` (`parallelTaskManager.js`): `event.sender.send('parallel-git-task-update', updateDetails)`. "Completed" status `updateDetails` payload must include `solutionSummary` (string) and `keyFilePaths` (array of strings).
2.  **`onParallelGitRunCompleted(callback)`**
    *   Channel: `'parallel-git-run-completed'`
    *   `preload.js`: Exposes registration, returns individual cleanup function.
    *   `main.js` (`parallelTaskManager.js`): `event.sender.send('parallel-git-run-completed', completionDetails)`.

**IV. Listener Cleanup Functionality**

1.  **`cleanupParallelTaskListeners()`**
    *   `preload.js`: This function will now be a no-op or removed. Instead, each `on...` registration in `preload.js` will return its own specific cleanup function (e.g., `const cleanup = window.api.onParallelGitTaskUpdate(...); cleanup();`). UI components are responsible for calling these.

**Key Decisions & Rationale:**
- Using `ipcMain.handle` for all Renderer-to-Main calls expecting a direct response.
- `event.sender` passed to `parallelTaskManager.js` functions that need to emit events back.
- Individual cleanup functions returned by `on...` methods in `preload.js` for safer listener management.
- Resolved Agent F's Q2 by adding `'get-agent-file-content'` IPC for on-demand fetching of specific file contents by the UI.

**Open Questions for Lead:**
- For `triggerAgentVersionZip`, the `downloadPath` returned: should `main.js` directly initiate Electron's download (`session.downloadURL()`) or is the current plan (renderer gets path, then calls a generic `window.electron.requestFileDownload(path)`) preferred? *(Current plan seems fine, keeps `parallelTaskManager` agnostic of UI dialogs).*

**Dependencies:**
- **Agent D (Backend):** `parallelTaskManager.js` must expose all necessary functions (`startRun`, `handleFinalizeVersion`, `retryAgentTask`, `cancelRun`, `getAgentOutputs`, `handleTriggerAgentVersionZip`, and new `getSpecificFileContent`). It must also correctly structure data for events, including `solutionSummary` and `keyFilePaths`.
- **Agent E & F (UI):** UI components must call these IPC functions with correct arguments and handle responses/events with correct payloads.
- **`development-status.md`:** Relies on it for canonical definition of channel names and payload structures (will need updating for `'get-agent-file-content'`).
---

**Key Decisions & Rationale:**
*(Optional: Agent G to note key design choices or assumptions made during their planning)*

**Open Questions for Lead:**
*(Optional: Agent G to list any questions or points needing clarification from the Lead Planner/User)*

**Dependencies:**
*(Optional: Agent G to list dependencies this task has on other tasks, IPC channels, specific data, etc.)*
    - `parallelTaskManager.js` (from Agent D, Sub-Task 1) API, including functions for `handleTriggerAgentVersionZip` and providing `solutionSummary`/`keyFilePaths`.
    - Clear payload definitions in `development-status.md`.

**Relevant Files/Links:**
- `IMPLEMENTATION_GUIDE.md` (Section: "Electron UI - Phase 2.5")
- `development-status.md` (for definitive IPC channel names, payloads, and status)
- `preload.js`
- `main.js` (IPC handler registration section)
- `parallelTaskManager.js` (interaction points)
- Addenda for Sub-Task 1 (Agent D) regarding solution summaries and zipping.
---

## Completed Tasks
---

## Backlog / Future Tasks
---
