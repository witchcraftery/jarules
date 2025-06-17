# Archived Sub-Task for Agent E - Fetching LLM Configs Logic Design
## From Main Task: TASKID-20231027-120000-AGE-UIFORM - Implement UI for Task Definition & Agent Selection (Phase 2.5)

---
**Simulated Implementation Update (Fetching LLM Configs in `ParallelTaskLauncher.vue`):**
**Date:** 2023-10-27

**Component:** `jarules_electron_vue_ui/src/components/ParallelTaskLauncher.vue`

**Functionality:** Fetching the list of available LLM configurations to populate the `SubAgentSelector.vue`.

**Details:**
*   **IPC Channel Defined:** `'get-llm-configs'`.
    *   Renderer calls `window.api.getLLMConfigs()`.
    *   `preload.js` exposes this function, invoking `'get-llm-configs'`.
    *   `main.js` needs a handler for `'get-llm-configs'` that:
        1.  Reads `config/llm_config.yaml`.
        2.  Parses the YAML.
        3.  Transforms the data into an array of objects, each like: `{ id, name, description?, provider, model }`.
        4.  Returns this array.
        *(Coordination: This IPC handler implementation is likely Agent G's or a general backend task).*
*   **`ParallelTaskLauncher.vue` - Script Setup:**
    *   `allAvailableLLMAgents = ref([])`
    *   `isLoadingAgents = ref(false)`
    *   `async function fetchAvailableAgents()`:
        *   Sets `isLoadingAgents` to true.
        *   Calls `await window.api.getLLMConfigs()`.
        *   Populates `allAvailableLLMAgents.value` with the transformed results.
        *   Handles potential errors during fetching and sets feedback messages.
        *   Sets `isLoadingAgents` to false in a `finally` block.
    *   `onMounted(fetchAvailableAgents)`: Calls the fetch function when the component is mounted.
*   **`ParallelTaskLauncher.vue` - Template:**
    *   Displays a loading message while `isLoadingAgents` is true.
    *   Displays an error/warning message if `allAvailableLLMAgents` is empty after loading attempt.
    *   Passes `allAvailableLLMAgents` to the `<SubAgentSelector>` component.
*   **Status:** This part of the UI logic (client-side fetching and state management) is designed. Backend IPC handler implementation is a dependency.
---
