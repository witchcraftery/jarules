# Archived Plan Section for Agent G - Main-to-Renderer Events & Cleanup
## From Main Task: TASKID-20231027-121000-AGG-IPCIF - Implement IPC Interface for Parallel Tasks (Phase 2.5) - Revised for Solution Previews & Zipping

---
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
---
