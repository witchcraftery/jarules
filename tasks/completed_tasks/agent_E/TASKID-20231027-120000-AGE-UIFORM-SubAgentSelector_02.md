# Archived Sub-Task for Agent E - SubAgentSelector.vue Design
## From Main Task: TASKID-20231027-120000-AGE-UIFORM - Implement UI for Task Definition & Agent Selection (Phase 2.5)

---
**Simulated Implementation Update (SubAgentSelector.vue):**
**Date:** 2023-10-27

**File:** `jarules_electron_vue_ui/src/components/SubAgentSelector.vue`

**Component Details:**
*   **Purpose:** Displays a list of available LLM agent configurations and allows users to select multiple agents.
*   **Props:**
    *   `availableAgents: Array` (of agent objects: `{ id, name, description?, provider, model }`).
    *   `modelValue: Array` (of selected agent *objects*, for `v-model`).
*   **Emits:**
    *   `update:modelValue` (emits array of selected agent *objects*).
*   **Internal State:**
    *   `internalSelectedAgentIds: ref(new Set())` to efficiently manage IDs of selected agents.
*   **Template Structure:**
    *   Iterates `availableAgents` to create a clickable list item for each.
    *   Each item includes a checkbox, agent name, provider/model, and description.
    *   Visual indication for selected items.
    *   "Select All" / "Deselect All" buttons.
    *   Handles empty state (no available agents).
    *   Basic accessibility attributes for list items acting as checkboxes.
*   **Script Setup (Vue 3):**
    *   `defineProps`, `defineEmits`.
    *   `isSelected(agentId)` computed check.
    *   `toggleSelection(agentObject)` method to update selection and emit changes.
    *   `selectAllAgents()`, `deselectAllAgents()` methods.
    *   `watch` on `modelValue` prop to synchronize internal state if selection is changed externally.
*   **Styling:** Scoped CSS for list, items, hover, and selection states; includes scroll for long lists.
*   **Status:** This component's design and simulated implementation are complete.
---
