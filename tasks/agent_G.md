# Task Assignments for Agent G

## Active Tasks
---
### Task ID: TASKID-20231027-121000-AGG-IPCIF
**Assigned:** 2023-10-27 12:10:00 UTC
**Status:** New
**Title:** Implement IPC Interface for Parallel Tasks (Phase 2.5)

**Description:**
Ensure robust and correct implementation of all client-side (renderer, via `preload.js`) and main-process side (`main.js`) aspects of the IPC channels dedicated to the parallel Git task functionality, as specified in `IMPLEMENTATION_GUIDE.md`. This interface is the backbone for communication between the UI and the backend orchestration logic.

Key Requirements:
1.  **Implement Renderer-to-Main IPC Calls:** `window.api.startParallelGitTask`, `finalizeSelectedGitVersion`, `retryAgentGitTask`, `cancelParallelRun` (expose via `contextBridge`, implement handlers in `main.js`).
2.  **Implement Main-to-Renderer Event Listeners:** `window.api.onParallelGitTaskUpdate`, `window.api.onParallelGitRunCompleted` (expose via `contextBridge`, ensure `main.js` uses `webContents.send` for these).
3.  **Implement Listener Cleanup:** `window.api.cleanupParallelTaskListeners()`.
4.  **Data Validation & Error Handling:** For all IPC payloads and communication.

**Acceptance Criteria:**
- All specified `window.api` functions for parallel tasks are available in the renderer process via `preload.js`.
- `main.js` correctly handles IPC calls from these functions, invoking appropriate logic in `parallelTaskManager.js`.
- `main.js` handlers return asynchronous responses with correct payload structures (success/failure, IDs, messages) as defined in `IMPLEMENTATION_GUIDE.md`.
- Renderer can successfully register callbacks for `onParallelGitTaskUpdate` and `onParallelGitRunCompleted`.
- `main.js` (via `parallelTaskManager.js`) correctly emits `parallel-git-task-update` and `parallel-git-run-completed` events on the specified channels with correct payloads.
- `cleanupParallelTaskListeners` function correctly removes listeners to prevent memory leaks.
- Robust error handling is implemented for IPC communication failures or invalid payloads.

**Notes/Plans by Agent G:**
*(Please add your detailed implementation plan here, specifying changes to `preload.js`, `main.js` handlers, and how they will interact with `parallelTaskManager.js`.)*

**Relevant Files/Links:**
- `IMPLEMENTATION_GUIDE.md` (Section: "Electron UI - Phase 2.5", critically the subsection "IPC Interface for Parallel Tasks")
- `preload.js`
- `main.js` (specifically the section where IPC handlers are registered)
- `parallelTaskManager.js` (for interaction points)
---

## Completed Tasks
---

## Backlog / Future Tasks
---
