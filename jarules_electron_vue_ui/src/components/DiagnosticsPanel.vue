<template>
  <div class="diagnostics-panel">
    <h3>Pre-flight Checks & Diagnostics</h3>
    <button @click="handleRunDiagnostics" :disabled="isLoading" class="run-diagnostics-button">
      {{ isLoading ? 'Running Checks...' : 'Run Diagnostic Checks' }}
    </button>

    <div v-if="isLoading && diagnosticResults.length === 0" class="loading-initial">
      <p>Initializing and running diagnostic checks, please wait...</p>
      <!-- Optional: Add a spinner here -->
    </div>

    <div v-if="!isLoading && lastRunTimestamp" class="last-run-timestamp">
      Last run: {{ formatTimestamp(lastRunTimestamp) }}
    </div>

    <div v-if="diagnosticResults.length > 0" class="results-container">
      <h4>Diagnostic Results:</h4>
      <ul>
        <li v-for="result in diagnosticResults" :key="result.id" class="diagnostic-item" :class="['status-' + result.status]">
          <div class="item-header">
            <span class="status-icon">{{ getStatusIcon(result.status) }}</span>
            <strong class="item-name">{{ result.name }}</strong>
          </div>
          <p class="item-message">{{ result.message }}</p>
          <pre v-if="result.details" class="item-details">{{ result.details }}</pre>
        </li>
      </ul>
    </div>
    <div v-else-if="!isLoading && hasRunOnce" class="no-results">
      No diagnostic results to display. Checks might not have run or returned empty.
    </div>
  </div>
</template>

<script>
export default {
  name: 'DiagnosticsPanel',
  data() {
    return {
      isLoading: false,
      hasRunOnce: false, // To distinguish initial state from an empty result set after a run
      diagnosticResults: [], // Array of DiagnosticCheckResult objects
      lastRunTimestamp: null,
      // Real-time updates can be handled by pushing to diagnosticResults
      // or updating existing items if using onDiagnosticCheckUpdate
    };
  },
  methods: {
    async handleRunDiagnostics() {
      this.isLoading = true;
      this.hasRunOnce = true;
      this.diagnosticResults = []; // Clear previous results or show them as stale
      // this.lastRunTimestamp = null; // Clear timestamp until new results arrive

      // Optional: Set up real-time listener if desired for individual updates
      // This example focuses on the bulk response from runAllDiagnostics
      // if (window.api && window.api.onDiagnosticCheckUpdate) {
      //   window.api.onDiagnosticCheckUpdate(this.handleIndividualCheckUpdate);
      // }

      try {
        const results = await window.api.runAllDiagnostics();
        if (results && Array.isArray(results)) {
          this.diagnosticResults = results;
          if (results.length > 0 && results[0].timestamp) { // Try to get a timestamp from first result as general run time
             this.lastRunTimestamp = results[0].timestamp; // Or generate a new Date() here.
          } else {
             this.lastRunTimestamp = new Date().toISOString();
          }
        } else {
          this.diagnosticResults = [{
            id: 'panel-error',
            name: 'Diagnostics Runner Error',
            status: 'error',
            message: 'Failed to get valid results from the diagnostics runner. Response was not an array.',
            details: JSON.stringify(results, null, 2),
            timestamp: new Date().toISOString()
          }];
          this.lastRunTimestamp = new Date().toISOString();
        }
      } catch (error) {
        console.error('Error running diagnostics:', error);
        this.diagnosticResults = [{
          id: 'panel-ipc-error',
          name: 'Diagnostics IPC Error',
          status: 'error',
          message: `An error occurred while trying to run diagnostic checks: ${error.message}`,
          details: error.stack,
          timestamp: new Date().toISOString()
        }];
        this.lastRunTimestamp = new Date().toISOString();
      } finally {
        this.isLoading = false;
        // Optional: Clean up listener if it was set up for real-time updates for this run
        // if (window.api && window.api.cleanupDiagnosticListeners) { // Assuming a general cleanup
        //   window.api.cleanupDiagnosticListeners();
        // }
      }
    },
    // handleIndividualCheckUpdate(checkResult) {
    //   // Logic to add or update checkResult in this.diagnosticResults
    //   // For example, find by id and update, or push if new.
    //   const index = this.diagnosticResults.findIndex(r => r.id === checkResult.id);
    //   if (index !== -1) {
    //     this.diagnosticResults.splice(index, 1, checkResult);
    //   } else {
    //     this.diagnosticResults.push(checkResult);
    //   }
    //   this.isLoading = this.diagnosticResults.some(r => r.status === 'running'); // Example
    //   this.lastRunTimestamp = new Date().toISOString(); // Update timestamp on any update
    // },
    getStatusIcon(status) {
      switch (status) {
        case 'success': return '✅';
        case 'warning': return '⚠️';
        case 'error': return '❌';
        case 'running': return '⏳'; // Spinner or hourglass
        default: return 'ℹ️'; // Info for unknown status
      }
    },
    formatTimestamp(isoString) {
        if (!isoString) return 'N/A';
        try {
            return new Date(isoString).toLocaleString();
        } catch (e) {
            return isoString; // Fallback to raw string if parsing fails
        }
    }
  },
  // Optional: If using real-time updates via a global listener in App.vue,
  // this component might receive results via props instead of calling runAllDiagnostics itself.
  // For now, it's self-contained.

  // beforeUnmount() {
  //   // If this component specifically set up listeners via onDiagnosticCheckUpdate that returned a cleanup func
  //   // it should call that cleanup here. If using a global listener cleaned by App.vue, this is not needed.
  // }
};
</script>

<style scoped>
.diagnostics-panel {
  padding: 1rem 1.5rem;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  margin: 1rem;
  background-color: #f8f9fa;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.diagnostics-panel h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #343a40;
  font-size: 1.3em;
}

.run-diagnostics-button {
  padding: 0.5rem 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  margin-bottom: 1rem;
  transition: background-color 0.2s ease-in-out;
}
.run-diagnostics-button:hover:not(:disabled) {
  background-color: #0056b3;
}
.run-diagnostics-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.loading-initial {
  padding: 1rem;
  text-align: center;
  color: #495057;
  font-style: italic;
}

.last-run-timestamp {
  font-size: 0.85em;
  color: #6c757d;
  margin-bottom: 1rem;
  text-align: right;
}

.results-container {
  margin-top: 1rem;
}
.results-container h4 {
    margin-bottom: 0.75rem;
    font-size: 1.1em;
    color: #495057;
}

.results-container ul {
  list-style-type: none;
  padding: 0;
}

.diagnostic-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 4px;
  border: 1px solid #e9ecef;
  background-color: #fff;
}

.item-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.25rem;
}

.status-icon {
  margin-right: 0.5rem;
  font-size: 1.1em;
}

.item-name {
  font-weight: bold;
  color: #212529;
}

.item-message {
  margin: 0.25rem 0;
  color: #495057;
  font-size: 0.95em;
}

.item-details {
  background-color: #e9ecef;
  padding: 0.5rem;
  border-radius: 3px;
  font-size: 0.85em;
  white-space: pre-wrap;
  word-break: break-all;
  margin-top: 0.5rem;
  max-height: 150px; /* Prevent very long details from dominating */
  overflow-y: auto;
  color: #343a40;
}

/* Status-specific styling */
.diagnostic-item.status-success {
  border-left: 5px solid #28a745; /* Green */
}
.diagnostic-item.status-success .item-name {
  color: #155724;
}

.diagnostic-item.status-warning {
  border-left: 5px solid #ffc107; /* Yellow */
}
.diagnostic-item.status-warning .item-name {
  color: #856404;
}

.diagnostic-item.status-error {
  border-left: 5px solid #dc3545; /* Red */
}
.diagnostic-item.status-error .item-name {
  color: #721c24;
}

.diagnostic-item.status-running .item-name {
  color: #007bff; /* Blue for running */
}

.no-results {
  padding: 1rem;
  text-align: center;
  color: #6c757d;
  font-style: italic;
  margin-top: 1rem;
}
</style>
