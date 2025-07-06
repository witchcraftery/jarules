# Archived Sub-Task for Agent F - AgentOutputViewer.vue Design
## From Main Task: TASKID-20231027-120500-AGF-UIRES - Implement UI for Results Preview & Finalization (Phase 2.5) - Revised for Solution Summaries

---
**Simulated Implementation Update (`AgentOutputViewer.vue`):**
**Date:** 2023-10-28

**File:** `jarules_electron_vue_ui/src/components/AgentOutputViewer.vue` (Replaces/Refines `ResultDetailView.vue`)

**Component Details:**
*   **Purpose:** Displays the detailed output of a selected sub-agent: their solution summary (rendered as HTML) and content of key code files. Also provides actions to download the agent's version as a zip and to select it for finalization.
*   **Props:** `agentTaskData: Object`, `runId: String`.
*   **Emits:** `finalizeVersion(agentId)`.
*   **Data/State:** `solutionSummaryContent`, `codeFiles` (array of `{path, content}`), `isLoadingOutput`, `selectedFileToView`, `currentFileContent`, `errorMessage`, `isDownloadingZip`, `downloadFeedback`, `isFinalizing`.
*   **Key Logic (`fetchAgentOutputs()` called by `watchEffect` on `agentTaskData` change):**
    *   Calls `window.api.getAgentTaskOutputs({ runId, agentId })` to fetch summary and key file contents.
        *(Dependency: IPC `'get-agent-task-outputs'` from Agent G/D. Payload should be `{ success, solutionSummary?, files?: [{path, content}], error?: string }`)*.
    *   Populates local state with fetched data.
*   **Markdown Rendering:** Uses `marked.parse()` (or similar library) for `solutionSummaryContent` displayed via `v-html`.
*   **Code File Display:** Uses tabs for file selection, displays content of `selectedFileToView` in a `<pre>` tag.
*   **Download Zip Functionality (`triggerDownloadZip()`):**
    *   Calls `window.api.triggerAgentVersionZip({ runId, agentId })`.
        *(Dependency: IPC `'trigger-agent-version-zip'` from Agent G/D. Returns `{ success, downloadPath?, error?: string }`)*.
    *   Relies on main process (via a new `window.electron.requestFileDownload(path)` call for example) to handle the actual file download dialog using the provided path.
*   **Template Structure:**
    *   Displays agent identifier.
    *   Section for rendered HTML solution summary.
    *   Section for code file viewing with tabs and `<pre>` block.
    *   Action buttons: "Download Project Files for this Version", "Use This Agent's Solution".
    *   Loading and feedback messages.
*   **Status:** This component's design and simulated implementation are complete. Relies heavily on new/updated IPC channels and backend logic from Agents D & G for data and zip functionality.
---
