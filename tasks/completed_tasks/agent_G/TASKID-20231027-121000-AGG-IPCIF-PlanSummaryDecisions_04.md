# Archived Plan Section for Agent G - Plan Summary & Decisions
## From Main Task: TASKID-20231027-121000-AGG-IPCIF - Implement IPC Interface for Parallel Tasks (Phase 2.5) - Revised for Solution Previews & Zipping

---
**V. Key Decisions & Rationale:**
- Using `ipcMain.handle` for all Renderer-to-Main calls expecting a direct response.
- `event.sender` passed to `parallelTaskManager.js` functions that need to emit events back.
- Individual cleanup functions returned by `on...` methods in `preload.js` for safer listener management.
- Resolved Agent F's Q2 by adding `'get-agent-file-content'` IPC for on-demand fetching of specific file contents by the UI.

**Open Questions for Lead:**
- For `triggerAgentVersionZip`, the `downloadPath` returned: should `main.js` directly initiate Electron's download (`session.downloadURL()`) or is the current plan (renderer gets path, then calls a generic `window.electron.requestFileDownload(path)`) preferred? *(Resolution: Current plan confirmed - renderer gets path, calls generic utility).*

**Dependencies:**
- **Agent D (Backend):** `parallelTaskManager.js` must expose all necessary functions (`startRun`, `handleFinalizeVersion`, `retryAgentTask`, `cancelRun`, `getAgentOutputs`, `handleTriggerAgentVersionZip`, and new `getSpecificFileContent`). It must also correctly structure data for events, including `solutionSummary` and `keyFilePaths`.
- **Agent E & F (UI):** UI components must call these IPC functions with correct arguments and handle responses/events with correct payloads.
- **`development-status.md`:** Relies on it for canonical definition of channel names and payload structures (will need updating for `'get-agent-file-content'`).
---
