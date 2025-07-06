# Archived Plan Section for Agent G - Renderer-to-Main IPCs
## From Main Task: TASKID-20231027-121000-AGG-IPCIF - Implement IPC Interface for Parallel Tasks (Phase 2.5) - Revised for Solution Previews & Zipping

---
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
---
