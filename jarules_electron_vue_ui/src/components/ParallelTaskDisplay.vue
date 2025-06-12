<template>
  <div class="parallel-task-display">
    <h3>Parallel Task Progress & Results</h3>

    <div v-if="!activeParallelRun || activeParallelRun.agents.length === 0" class="no-active-tasks">
      <p>No parallel tasks currently active or assigned.</p>
      <p v-if="activeParallelRun && activeParallelRun.taskDescription">
        <strong>Original Task:</strong> {{ activeParallelRun.taskDescription }}
      </p>
    </div>

    <div v-else class="active-run-details">
      <h4>Task: {{ activeParallelRun.taskDescription }}</h4>
      <div class="agents-container">
        <div v-for="agentTask in activeParallelRun.agents" :key="agentTask.id" class="agent-task-card">
          <div class="agent-header">
            <strong>Agent:</strong> {{ agentTask.name }} ({{ agentTask.id }})
          </div>
          <div class="agent-status">
            <strong>Status:</strong>
            <span :class="['status-' + agentTask.status.toLowerCase().replace(/\s+/g, '-'), agentTask.error ? 'status-error-state' : '']">
              {{ agentTask.status }}
            </span>
            <span v-if="agentTask.isProcessing" class="spinner"></span>
          </div>

          <div v-if="agentTask.error" class="agent-error-message">
            <strong>Error:</strong> {{ agentTask.errorMessage || 'An unknown error occurred.' }}
          </div>

          <div class="agent-results-preview" v-if="agentTask.status === 'Completed' && !agentTask.error">
            <h4>Results Preview:</h4>
            <div v-if="agentTask.resultSummary">
                <pre class="result-summary">{{ agentTask.resultSummary }}</pre>
                <!-- In a real scenario, this could be a diff viewer, rendered markdown, etc. -->
                <button @click="viewFullResult(agentTask)" class="action-button">View Full Result</button>
            </div>
            <p v-else>No summary available. Click 'View Full Result' for details.</p>
          </div>

          <div class="agent-actions" v-if="agentTask.status === 'Completed' && !agentTask.error">
            <button
              @click="selectVersion(agentTask.id)"
              class="select-version-button"
              :disabled="someVersionAlreadySelected || isFinalizing">
              Select this Version
            </button>
          </div>
          <div class="agent-actions" v-if="agentTask.status === 'Error'">
             <button @click="retryAgentTask(agentTask.id)" class="action-button retry-button" :disabled="isFinalizing">Retry</button>
          </div>
        </div>
      </div>

      <div v-if="selectedVersionId && !isFinalizing" class="final-selection-prompt">
        <p>You have selected version from agent: <strong>{{ getAgentNameById(selectedVersionId) }}</strong>.</p>
        <button @click="confirmFinalSelection" class="confirm-final-button">Confirm & Finalize</button>
        <button @click="clearSelection" class="clear-selection-button">Change Selection</button>
      </div>
      <div v-if="isFinalizing" class="finalizing-message">
        <p>Finalizing selection... please wait.</p>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'ParallelTaskDisplay',
  props: {
    activeParallelRun: Object,
    // Example structure for activeParallelRun:
    // {
    //   runId: 'run-123',
    //   taskDescription: 'Refactor the user login module.',
    //   agents: [
    //     { id: 'gemini_default', name: 'Gemini Pro', status: 'Processing', progress: 50, resultSummary: null, error: null, isProcessing: true, errorMessage: null },
    //     { id: 'claude_haiku', name: 'Claude Haiku', status: 'Completed', resultSummary: 'Refactored User.js, LoginService.js. Added 2 unit tests.', error: null, isProcessing: false, errorMessage: null },
    //     { id: 'gpt4_turbo', name: 'GPT-4 Turbo', status: 'Error', resultSummary: null, error: true, isProcessing: false, errorMessage: 'API connection timeout.' }
    //   ]
    // }
    // For now, we'll use a local mock until integration
  },
  data() {
    return {
      // Use prop if available, otherwise fall back to mock for standalone dev if needed
      internalActiveRun: this.activeParallelRun || {
        runId: 'mock-run-001-internal',
        taskDescription: 'Develop a Vue component for displaying parallel task progress and results (Internal Mock).',
        agents: [
          { id: 'agent_alpha_fast_internal', name: 'Alpha (Fast Model - Internal Mock)', model: 'alpha-fast', provider: 'provider1', status: 'Processing', progress: 60, resultSummary: null, error: null, isProcessing: true, errorMessage: null },
          { id: 'agent_beta_detailed_internal', name: 'Beta (Detailed Model - Internal Mock)', model: 'beta-detailed', provider: 'provider2', status: 'Completed', resultSummary: 'Internal mock summary.', error: null, isProcessing: false, errorMessage: null },
        ]
      },
      selectedVersionId: null, // ID of the agent whose version is chosen by the user
      isFinalizing: false, // To show a loading/waiting state when finalizing
    };
  },
  computed: {
    someVersionAlreadySelected() {
      return !!this.selectedVersionId;
    }
  },
  methods: {
    getAgentNameById(agentId) {
        const agent = this.internalActiveRun.agents.find(a => a.id === agentId);
        return agent ? agent.name : 'Unknown Agent';
    },
    viewFullResult(agentTask) {
      // This would typically emit an event to the parent to show a modal or navigate
      console.log('View Full Result for:', agentTask);
      this.$emit('view-full-result', agentTask);
      // For now, an alert or log.
      alert(`Viewing full result for ${agentTask.name}. Output:
${agentTask.resultSummary || 'No detailed summary available in mock.'}`);
    },
    selectVersion(agentId) {
      if (!this.isFinalizing) {
        this.selectedVersionId = agentId;
        // Parent component might want to know immediately
        this.$emit('version-tentatively-selected', agentId);
      }
    },
    confirmFinalSelection() {
      if (this.selectedVersionId) {
        this.isFinalizing = true;
        console.log('Confirming final selection:', this.selectedVersionId);
        // Emit event to parent to handle the actual finalization (e.g., backend call)
        this.$emit('finalize-version-selection', this.selectedVersionId);
        // Mock finalization:
        // setTimeout(() => {
        //   alert(`Version from ${this.getAgentNameById(this.selectedVersionId)} finalized!`);
        //   this.isFinalizing = false;
        //   // Potentially clear the run or move to a different state via parent
        // }, 1500);
      }
    },
    clearSelection() {
        this.selectedVersionId = null;
        this.$emit('selection-cleared');
    },
    retryAgentTask(agentId) {
      if (!this.isFinalizing) {
        console.log('Retrying task for agent:', agentId);
        this.$emit('retry-agent-task', agentId);
        // Mock: update status locally or expect parent to update prop
      const agent = this.internalActiveRun.agents.find(a => a.id === agentId);
        if (agent) {
          agent.status = 'Retrying...';
          agent.error = null;
          agent.errorMessage = null;
          agent.isProcessing = true;
          // Simulate processing
          // setTimeout(() => {
          //   agent.status = 'Processing';
          // }, 1000);
        }
      }
    },
    // Method to update agent status (would be called by parent based on IPC events)
    // updateAgentStatus(agentId, newStatus, details = {}) {
    //   const agent = this.activeParallelRun.agents.find(a => a.id === agentId);
    //   if (agent) {
    //     agent.status = newStatus;
    //     agent.isProcessing = details.isProcessing !== undefined ? details.isProcessing : false;
    //     agent.error = details.error !== undefined ? details.error : null;
    //     agent.errorMessage = details.errorMessage !== undefined ? details.errorMessage : null;
    //     if (details.resultSummary) {
    //       agent.resultSummary = details.resultSummary;
    //     }
    //     if (details.progress) {
    //       agent.progress = details.progress;
    //     }
    //   }
    // }
  },
  watch: {
    activeParallelRun: {
      handler(newVal) {
        if (newVal) {
          this.internalActiveRun = newVal;
          // Reset selection if the whole run changes
          this.selectedVersionId = null;
          this.isFinalizing = false;
        } else {
          // If prop becomes null, revert to a default empty/mock state or clear
          this.internalActiveRun = { runId: null, taskDescription: '', agents: [] };
        }
      },
      deep: true,
      immediate: true // Apply prop data immediately on component mount
    }
  }
};
</script>

<style scoped>
.parallel-task-display {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin: 1rem 0;
  background-color: #f9f9f9;
}

.parallel-task-display h3, .parallel-task-display h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #333;
}
.active-run-details h4 {
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #eee;
}

.no-active-tasks {
  padding: 1rem;
  text-align: center;
  color: #555;
  font-style: italic;
}
.no-active-tasks strong {
    font-style: normal;
    font-weight: bold;
    color: #444;
}

.agents-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); /* Responsive grid */
  gap: 1rem;
  margin-top: 1rem;
}

.agent-task-card {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}

.agent-header {
  font-size: 1.1em;
  margin-bottom: 0.5rem;
  color: #0056b3;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.agent-status {
  margin-bottom: 0.5rem;
  font-size: 0.95em;
  display: flex;
  align-items: center;
}
.agent-status strong {
  margin-right: 0.3rem;
}
.status-processing, .status-generating-diff, .status-retrying {
  color: #007bff; /* Blue for in-progress */
}
.status-completed {
  color: #28a745; /* Green for completed */
}
.status-error, .status-error-state { /* Ensure error class applies for text color */
  color: #dc3545 !important; /* Red for error */
  font-weight: bold;
}
.status-cancelled {
  color: #6c757d; /* Grey for cancelled */
}


.agent-error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 0.5rem;
  border-radius: 3px;
  font-size: 0.9em;
  margin-bottom: 0.5rem;
  border: 1px solid #f5c6cb;
}

.agent-results-preview {
  margin-top: 0.5rem;
  margin-bottom: 0.75rem;
  flex-grow: 1; /* Allow it to take up space */
}
.agent-results-preview h4 {
  font-size: 1em;
  color: #495057;
  margin-bottom: 0.3rem;
}
.agent-results-preview .result-summary {
  background-color: #e9ecef;
  padding: 0.5rem;
  border-radius: 3px;
  font-size: 0.85em;
  white-space: pre-wrap;
  max-height: 100px;
  overflow-y: auto;
  margin-bottom: 0.5rem;
}

.agent-actions {
  margin-top: auto; /* Push actions to the bottom of the card */
  padding-top: 0.5rem;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}
.agent-actions .action-button,
.agent-actions .select-version-button,
.agent-actions .retry-button {
  padding: 0.4rem 0.8rem;
  font-size: 0.9em;
  margin-left: 0.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}

.action-button {
  background-color: #6c757d; /* Grey */
  color: white;
}
.action-button:hover:not(:disabled) {
  background-color: #5a6268;
}

.retry-button {
  background-color: #ffc107; /* Yellow for retry */
  color: #212529;
}
.retry-button:hover:not(:disabled) {
  background-color: #e0a800;
}

.select-version-button {
  background-color: #007bff; /* Blue */
  color: white;
}
.select-version-button:hover:not(:disabled) {
  background-color: #0056b3;
}
.select-version-button:disabled, .action-button:disabled, .retry-button:disabled {
  background-color: #adb5bd;
  cursor: not-allowed;
}

.final-selection-prompt {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid #007bff;
  border-radius: 4px;
  background-color: #e7f3ff;
  text-align: center;
}
.final-selection-prompt p {
  margin-bottom: 0.75rem;
}
.confirm-final-button {
  padding: 0.6rem 1.2rem;
  background-color: #28a745; /* Green */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  margin-right: 0.5rem;
}
.confirm-final-button:hover {
  background-color: #218838;
}
.clear-selection-button {
  padding: 0.6rem 1.2rem;
  background-color: #dc3545; /* Red */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}
.clear-selection-button:hover {
  background-color: #c82333;
}

.finalizing-message {
  margin-top: 1rem;
  text-align: center;
  font-style: italic;
  color: #0056b3;
}

/* Basic spinner animation */
.spinner {
  display: inline-block;
  border: 3px solid rgba(0,0,0,.1);
  border-left-color: #007bff;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
  margin-left: 8px;
  vertical-align: middle;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

</style>
