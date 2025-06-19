# Archived Sub-Task for Agent F - ParallelTaskMonitor.vue Design
## From Main Task: TASKID-20231027-120500-AGF-UIRES - Implement UI for Results Preview & Finalization (Phase 2.5) - Revised for Solution Summaries

---
**Simulated Implementation Update (`ParallelTaskMonitor.vue`):**
**Date:** 2023-10-28

**File:** `jarules_electron_vue_ui/src/components/ParallelTaskMonitor.vue`

**Component Details:**
*   **Purpose:** Main view for monitoring an active or completed parallel run. Displays overall run status, initial task description, and hosts `SubAgentProgressCard` components for each sub-agent. It also conditionally renders `AgentOutputViewer` for detailed result inspection.
*   **Props:** `runId: String`, `initialTaskDescription: String`.
*   **Data/State:**
    *   `runDetails`: Reactive object `{ overallStatus, message, agents: Map<agentId, AgentProgressData> }`.
    *   `AgentProgressData` structure defined to hold individual agent info including `solutionSummaryAvailable` and `keyFiles`.
    *   `selectedAgentOutputToView`: Holds full data of agent selected for detail view.
    *   Various boolean flags for loading and action states (`isLoadingRunDetails`, `isCancellingRun`, etc.).
    *   `feedbackMessage` object.
*   **IPC Interactions:**
    *   **Listeners (setup in `onMounted`, cleaned in `onUnmounted`):**
        *   `window.api.onParallelGitTaskUpdate`: Updates individual agent data in `runDetails.agents`.
        *   `window.api.onParallelGitRunCompleted`: Updates `runDetails.overallStatus`.
    *   **Invoke Calls (methods):**
        *   `window.api.getParallelRunStatus({ runId })`: For initial data fetch (New IPC dependency).
        *   `window.api.cancelParallelRun({ runId })`.
        *   `window.api.retryAgentGitTask({ runId, agentId })`.
        *   `window.api.finalizeSelectedGitVersion({ runId, selectedAgentId })` (called via `handleFinalizationFromViewer`).
*   **Key Methods:**
    *   `fetchInitialRunStatus()`: Fetches current state of the run.
    *   `handleViewOutput(agentData)`: Sets `selectedAgentOutputToView`.
    *   Event handlers for retry, cancel, finalize actions.
*   **Template Structure:**
    *   Displays overall run info, task description.
    *   "Cancel Entire Run" button.
    *   Iterates `runDetails.agents` to render `SubAgentProgressCard` components.
    *   Conditionally renders `AgentOutputViewer` based on `selectedAgentOutputToView`.
*   **Reactivity:** Uses Vue 3 Composition API (`ref`, `computed`, `watch`) for reactive updates. Includes a watcher on `props.runId` to re-initialize if the monitored run changes.
*   **Status:** This component's design and simulated implementation are complete. Key dependency is the new `'get-parallel-run-status'` IPC.
---
