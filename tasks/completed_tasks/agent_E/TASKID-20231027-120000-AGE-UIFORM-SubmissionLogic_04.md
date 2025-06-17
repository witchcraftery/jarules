# Archived Sub-Task for Agent E - Submission Logic Design
## From Main Task: TASKID-20231027-120000-AGE-UIFORM - Implement UI for Task Definition & Agent Selection (Phase 2.5)

---
**Simulated Implementation Update (Submission Logic in `ParallelTaskLauncher.vue`):**
**Date:** 2023-10-27

**Component:** `jarules_electron_vue_ui/src/components/ParallelTaskLauncher.vue`

**Functionality:** Handling the submission of the defined task and selected agents to the main process.

**Details:**
*   **State Refs Added:**
    *   `isSubmittingTask = ref(false)`: Manages the submission loading state.
*   **Computed Property `isFormValid`:**
    *   Ensures `taskPrompt` is not empty and at least one agent is in `selectedLLMAgents`.
*   **`submitParallelTask()` Method:**
    1.  Validates form using `isFormValid`.
    2.  Sets `isSubmittingTask = true` and updates `feedbackMessage` to "Submitting...".
    3.  Constructs `taskDetails` payload:
        *   `taskDescription`: from `taskPrompt.value`.
        *   `selectedAgents`: Mapped from `selectedLLMAgents.value` to include `{ id, name, provider, model }` for each agent, as per `IMPLEMENTATION_GUIDE.md`.
    4.  Calls `await window.api.startParallelGitTask(taskDetails)`.
        *(Dependency: `window.api.startParallelGitTask` exposed via `preload.js`, and its handler `'start-parallel-git-task'` in `main.js` which should interact with `parallelTaskManager.js` from Sub-Task 1).*
    5.  **Response Handling:**
        *   On success (`result.success` is true): Displays success message with `result.runId`. Clears `taskPrompt` and `selectedLLMAgents`.
        *   On failure: Displays error message from `result.error` and `result.details`.
    6.  Handles `try/catch` for the IPC call itself.
    7.  Sets `isSubmittingTask = false` in a `finally` block.
*   **Template Updates:**
    *   "Launch Parallel Task" button is disabled based on `isFormValid`, `isSubmittingTask`, and `isLoadingAgents`.
    *   Button text and appearance change during submission (e.g., shows "Submitting..." and a spinner).
    *   Enhanced `feedbackMessage` display with dynamic classes for success, error, info, warning alerts.
*   **Status:** UI logic for task submission is designed. Depends on Agent G for IPC channel (`'start-parallel-git-task'`) implementation and Agent D's backend (`parallelTaskManager.js`) to process the request.
---
