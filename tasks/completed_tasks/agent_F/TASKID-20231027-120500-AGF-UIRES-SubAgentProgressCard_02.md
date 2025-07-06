# Archived Sub-Task for Agent F - SubAgentProgressCard.vue Design
## From Main Task: TASKID-20231027-120500-AGF-UIRES - Implement UI for Results Preview & Finalization (Phase 2.5) - Revised for Solution Summaries

---
**Simulated Implementation Update (`SubAgentProgressCard.vue`):**
**Date:** 2023-10-28

**File:** `jarules_electron_vue_ui/src/components/SubAgentProgressCard.vue`

**Component Details:**
*   **Purpose:** Displays the summary status, progress, and action buttons for a single sub-agent task within the `ParallelTaskMonitor`.
*   **Props:**
    *   `agentData: Object` (The `AgentProgressData` object for one agent).
    *   `runId: String` (For context).
    *   `isActionInProgress: Boolean` (To disable buttons during parent operations).
*   **Emits:**
    *   `viewOutput(agentData)`: When "View Output" is clicked.
    *   `retryTask(agentId)`: When "Retry" is clicked.
    *   `selectForFinalize(agentId)`: When "Select this Version" is clicked.
*   **Template Structure:**
    *   Uses Bootstrap card layout.
    *   Card Header: Agent name/ID and a status badge (color-coded by `statusBadgeClass`).
    *   Card Body: Optional progress bar, result summary (if completed), or error message (if errored).
    *   Card Footer: Action buttons ("View Output", "Retry", "Select this Version") conditionally displayed based on computed properties.
*   **Script Setup (Vue 3):**
    *   `defineProps`, `defineEmits`.
    *   `statusBadgeClass`: Computed property for dynamic badge styling.
    *   `canViewOutput`, `canRetry`, `canSelectForFinalize`: Computed properties to control button visibility based on `agentData.status` and `agentData.solutionSummaryAvailable`.
*   **Styling:** Scoped CSS for card layout and elements.
*   **Status:** This component's design and simulated implementation are complete. It relies on `ParallelTaskMonitor.vue` for event handling and passing props.
---
