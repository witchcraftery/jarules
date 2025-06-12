<template>
  <div id="app-container">
    <div v-if="globalError.active" class="global-error-banner">
      <div class="error-content">
        <p><strong>Error:</strong> {{ globalError.message }}</p>
        <pre v-if="globalError.details" class="error-details">{{ globalError.details }}</pre>
      </div>
      <div class="error-actions">
        <button v-if="globalError.details" @click="copyErrorDetails" class="action-button">Copy Details</button>
        <button @click="dismissGlobalError" class="action-button dismiss-button">Dismiss</button>
      </div>
    </div>

    <h1>{{ message }}</h1>

    <div class="versions">
      <p>Electron: <span id="electron-version">{{ versions.electron }}</span></p>
      <p>Node: <span id="node-version">{{ versions.node }}</span></p>
      <p>Chrome: <span id="chrome-version">{{ versions.chrome }}</span></p>
    </div>

    <div class="top-panel">
      <div class="model-info">
        <h2>LLM Management</h2>
        <div v-if="activeModelDetails">
          <p><strong>Active Model:</strong> {{ activeModelDetails.name }}</p>
          <p>(ID: {{ activeModelDetails.id }}, Provider: {{ activeModelDetails.provider }})</p>
          <p><em>{{ activeModelDetails.description }}</em></p>
        </div>
        <p v-else-if="activeModelId"><strong>Active Model ID:</strong> {{ activeModelId }} (Details loading or not found)</p>
        <p v-else><strong>Active Model:</strong> {{ 'None selected or loading...' }}</p>

        <div class="model-selection">
          <h3>Available Models:</h3>
          <p v-if="isLoadingModels" class="loading-text">Loading available models...</p>
          <ul v-if="!isLoadingModels && availableModels.length > 0 && availableModels[0].id !== 'error' && availableModels[0].id !== 'empty' && availableModels[0].id !== 'ipc_error'">
            <li v-for="model in availableModels" :key="model.id">
              <strong>{{ model.name }}</strong> (ID: {{ model.id }})
              <button @click="selectModel(model.id)" :disabled="model.id === activeModelId || isStreaming">
                Set Active
              </button>
              <p><em>Provider: {{ model.provider }}</em></p>
              <p><em>{{ model.description }}</em></p>
            </li>
          </ul>
          <p v-else-if="!isLoadingModels && availableModels.length > 0 && (availableModels[0].id === 'error' || availableModels[0].id === 'empty' || availableModels[0].id === 'ipc_error')">{{ availableModels[0].name }}: {{ availableModels[0].description }}</p>
          <p v-else-if="!isLoadingModels">No models available or could not load.</p>
        </div>
        <p v-if="setModelMessage" class="feedback-message">{{ setModelMessage }}</p>
      </div>

      <div class="history-controls">
        <h3>Chat History</h3>
        <button @click="handleClearHistory" :disabled="isStreaming || isLoadingClearHistory || chatMessages.length === 0">
          {{ isLoadingClearHistory ? 'Clearing...' : 'Clear Chat History' }}
        </button>
        <p v-if="historyStatusMessage" class="feedback-message">{{ historyStatusMessage }}</p>
      </div>
    </div> <!-- End of top-panel -->

    <!-- Chat Messages Display Area -->
    <p v-if="isLoadingHistory && chatMessages.length === 0" class="loading-history-text">Loading chat history...</p>
    <MessageDisplay :messages="chatMessages" />

    <!-- Prompt Input Area -->
    <ChatInput @send-prompt="handleSendPrompt" :is-streaming="isStreaming" />

    <!-- Configuration Display Area -->
    <div class="config-area">
      <ConfigurationDisplay />
    </div>

    <div class="parallel-task-section">
      <h2>Parallel Task Management</h2>

      <div v-if="!showParallelProcessingUI">
        <TaskDefinitionInput @submit-task="handleTaskSubmitted" />

        <div v-if="currentTaskDescription">
          <h3>Task to be Processed:</h3>
          <p>{{ currentTaskDescription }}</p>
          <SubAgentSelector @confirm-agent-selection="handleAgentsSelected" />
        </div>

        <button
          v-if="currentTaskDescription && selectedAgentsForTask.length > 0"
          @click="startParallelTask"
          class="start-parallel-task-button">
          Start Parallel Task with Selected Agents
        </button>
      </div>

      <div v-if="showParallelProcessingUI && activeParallelRun">
        <ParallelTaskDisplay
          :active-parallel-run="activeParallelRun"
          @view-full-result="handleViewFullResult"
          @finalize-version-selection="handleFinalizeSelection"
          @retry-agent-task="handleRetryTask"
        />
        <button @click="resetParallelTaskUI" class="reset-parallel-ui-button">
          Define New Parallel Task
        </button>
        <button @click="cancelCurrentParallelRun" class="cancel-parallel-run-button">Cancel Entire Run</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from 'vue';
import MessageDisplay from './components/MessageDisplay.vue';
import ChatInput from './components/ChatInput.vue';
import ConfigurationDisplay from './components/ConfigurationDisplay.vue'; // Added import
import TaskDefinitionInput from './components/TaskDefinitionInput.vue';
import SubAgentSelector from './components/SubAgentSelector.vue';
import ParallelTaskDisplay from './components/ParallelTaskDisplay.vue';

const message = ref('Hello from JaRules (Electron + Vue.js + Vite!)');
const versions = ref({ electron: '', node: '', chrome: '' });

const activeModelId = ref(null);
const availableModels = ref([]);
const setModelMessage = ref('');
const historyStatusMessage = ref('');
const globalError = ref({ message: '', details: '', active: false });

const isLoadingModels = ref(false);
const isLoadingHistory = ref(false);
const isLoadingClearHistory = ref(false);
// const isLoadingActiveModel = ref(false); // Optional, fetchActiveModel is usually very fast

// For Parallel Task Management
const currentTaskDescription = ref('');
const selectedAgentsForTask = ref([]); // Array of agent objects
const activeParallelRun = ref(null); // Will hold data for ParallelTaskDisplay
// Example: { runId: 'run-xyz', taskDescription: '...', agents: [ {id: '...', name: '...', status: 'Pending'} ] }
const showParallelProcessingUI = ref(false); // To toggle visibility of the parallel processing section


// Computed property to get the full details of the active model
const activeModelDetails = computed(() => {
  if (!activeModelId.value || !availableModels.value || availableModels.value.length === 0) {
    return null;
  }
  return availableModels.value.find(model => model.id === activeModelId.value);
});

// For chat interaction
const chatMessages = ref([]);
const isStreaming = ref(false);
let currentAssistantMessageId = null;

// Global Error Handling
function setGlobalError(message, details = '') {
  globalError.value = { message, details: String(details), active: true };
  console.error("Global Error Set:", message, details); // Log to console as well
}
function dismissGlobalError() {
  globalError.value.active = false;
}
async function copyErrorDetails() {
  if (!globalError.value.details) return;
  try {
    await navigator.clipboard.writeText(String(globalError.value.details));
    alert('Error details copied to clipboard!');
  } catch (err) {
    console.error('Failed to copy error details:', err);
    alert('Failed to copy error details. See console.');
    setGlobalError("Failed to copy to clipboard.", "Please copy details manually from the console if needed.");
  }
}


async function fetchActiveModel() {
  // if (isLoadingActiveModel) isLoadingActiveModel.value = true;
  try {
    const id = await window.api.getActiveModel();
    if (id && id.error) {
        setGlobalError("Failed to fetch active model.", id.message || String(id.details));
        activeModelId.value = null;
    } else {
        activeModelId.value = id;
        if (!id) {
            console.log('No active model ID returned from backend (or it was null).');
        }
    }
  } catch (error) {
    console.error('Error fetching active model via IPC:', error);
    activeModelId.value = null;
    setGlobalError("Failed to fetch active model.", error.message || String(error));
  }
  // finally { if (isLoadingActiveModel) isLoadingActiveModel.value = false; }
}

async function fetchAvailableModels() {
  isLoadingModels.value = true;
  try {
    const modelsResult = await window.api.listAvailableModels();
    if (modelsResult && modelsResult.error) {
      setGlobalError("Failed to load available models.", modelsResult.message || String(modelsResult.details));
      availableModels.value = [];
    } else if (modelsResult && Array.isArray(modelsResult)) {
      availableModels.value = modelsResult;
      if (modelsResult.length === 0) {
        console.log('No available models returned. This might be normal if none are configured, or an error occurred upstream and main.js returned [].');
      }
    } else {
      console.error('Invalid response when fetching available models (expected array or error obj):', modelsResult);
      availableModels.value = [];
      setGlobalError("Failed to load available models: Invalid response format.");
    }
  } catch (error) {
    console.error('Error fetching available models via IPC:', error);
    availableModels.value = [];
    setGlobalError("Failed to load available models.", error.message || String(error));
  } finally {
    isLoadingModels.value = false;
  }
}

async function selectModel(modelId) {
  setModelMessage.value = 'Setting model...';
  dismissGlobalError();
  try {
    const result = await window.api.setActiveModel(modelId);
    if (result && result.success) {
      activeModelId.value = modelId;
      setModelMessage.value = result.message || `Successfully set active model to ${modelId}.`;
    } else {
      const errorMsg = result ? (result.message || "Unknown error setting model") : "Unknown error response";
      const errorDetails = result ? (result.details || errorMsg) : "No details";
      setModelMessage.value = `Failed to set model: ${errorMsg}`;
      setGlobalError(`Failed to set active model to '${modelId}'.`, errorDetails);
    }
  } catch (error) {
    console.error('Error setting active model via IPC:', error);
    setModelMessage.value = `Error: ${error.message || 'Failed to set model due to IPC error.'}`;
    setGlobalError("IPC Error while setting active model.", error.message || String(error));
  }
  setTimeout(() => { setModelMessage.value = ''; }, 3000);
}

async function handleSendPrompt(promptText) {
  dismissGlobalError();
  const userMessage = {
    id: Date.now(),
    text: promptText,
    sender: 'user',
    error: false,
    isStreaming: false
  };
  chatMessages.value.push(userMessage);
  if (window.api && typeof window.api.addChatMessage === 'function') {
    window.api.addChatMessage({ id: userMessage.id, text: userMessage.text, sender: userMessage.sender });
  }

  currentAssistantMessageId = Date.now() + 1;
  chatMessages.value.push({
    id: currentAssistantMessageId,
    text: '',
    sender: 'assistant',
    isStreaming: true,
    error: false,
  });

  isStreaming.value = true;

  const onStart = (startMsg) => {
    console.log('Stream started:', startMsg);
    const assistantMsg = chatMessages.value.find(m => m.id === currentAssistantMessageId);
    if (assistantMsg) {
      assistantMsg.isStreaming = true;
    }
  };

  const onChunk = (chunkMsg) => {
    const assistantMsg = chatMessages.value.find(m => m.id === currentAssistantMessageId);
    if (assistantMsg) {
      if (chunkMsg.type === 'chunk' && chunkMsg.token) {
        assistantMsg.text += chunkMsg.token;
      } else if (chunkMsg.type === 'error') {
        const errorDetails = chunkMsg.details || chunkMsg.message;
        setGlobalError(`Error during stream: ${chunkMsg.message}`, errorDetails);
        onError({ message: chunkMsg.message, details: errorDetails });
        return;
      }
    }
  };

  const onError = (errorMsg) => {
    console.error('Stream error callback:', errorMsg);
    const assistantMsg = chatMessages.value.find(m => m.id === currentAssistantMessageId);
    if (assistantMsg) {
      assistantMsg.text += `\n--- ERROR: ${errorMsg.message} ---`;
      if(errorMsg.details) assistantMsg.text += `\nDetails: ${errorMsg.details}`;
      assistantMsg.error = true;
      assistantMsg.isStreaming = false;
      if (window.api && typeof window.api.addChatMessage === 'function') {
        window.api.addChatMessage({ id: assistantMsg.id, text: assistantMsg.text, sender: 'assistant', error: true });
      }
    }
    isStreaming.value = false;
    if (!globalError.value.active) {
        setGlobalError(`Streaming Error: ${errorMsg.message}`, errorMsg.details);
    }
  };

  const onDone = (doneMsg) => {
    console.log('Stream finished:', doneMsg);
    const assistantMsg = chatMessages.value.find(m => m.id === currentAssistantMessageId);
    if (assistantMsg) {
      if (doneMsg.success && doneMsg.full_response) {
        // assistantMsg.text = doneMsg.full_response;
      } else if (!doneMsg.success && doneMsg.error) {
         assistantMsg.text += `\n--- Error: ${doneMsg.error} ---`;
         if(doneMsg.details) assistantMsg.text += `\nDetails: ${doneMsg.details}`;
         assistantMsg.error = true;
         setGlobalError(`LLM Error: ${doneMsg.error}`, doneMsg.details);
      }
      assistantMsg.isStreaming = false;
      if (window.api && typeof window.api.addChatMessage === 'function') {
         window.api.addChatMessage({ id: assistantMsg.id, text: assistantMsg.text, sender: 'assistant', error: assistantMsg.error || false });
      }
    }
    isStreaming.value = false;
    currentAssistantMessageId = null;
  };

  window.api.sendPromptStreaming(promptText, onStart, onChunk, onError, onDone);
}

async function handleClearHistory() {
  if (confirm("Are you sure you want to clear all chat history? This action cannot be undone.")) {
    isLoadingClearHistory.value = true;
    historyStatusMessage.value = "Clearing history...";
    dismissGlobalError();
    try {
      const result = await window.api.clearChatHistory();
      if (result && result.success) {
        chatMessages.value = [];
        historyStatusMessage.value = result.message || "Chat history cleared successfully.";
      } else {
        const errorDetails = result ? (result.details || (result.message || result.error)) : 'Unknown error';
        historyStatusMessage.value = `Failed to clear history: ${result ? (result.message || result.error) : 'Unknown error'}`;
        setGlobalError("Failed to clear chat history.", errorDetails);
      }
    } catch (error) {
      console.error("Error clearing chat history via IPC:", error);
      historyStatusMessage.value = `Error: ${error.message || 'Failed to clear history due to IPC error.'}`;
      setGlobalError("IPC Error while clearing chat history.", error.message || String(error));
    } finally {
        isLoadingClearHistory.value = false;
        setTimeout(() => { historyStatusMessage.value = ''; }, 3000);
    }
  }
}

async function loadHistory() {
  isLoadingHistory.value = true;
  historyStatusMessage.value = "Loading history...";
  dismissGlobalError();
  try {
    const loadedHistory = await window.api.loadChatHistory();
    if (loadedHistory && Array.isArray(loadedHistory)) {
      chatMessages.value = loadedHistory;
      historyStatusMessage.value = loadedHistory.length > 0 ? "History loaded." : "No history found.";
    } else {
      historyStatusMessage.value = "Failed to load history or history is invalid.";
      chatMessages.value = [];
      if (loadedHistory && loadedHistory.error) {
           setGlobalError("Failed to load chat history.", loadedHistory.details || loadedHistory.message);
      } else if (!Array.isArray(loadedHistory) && loadedHistory !== null) {
           setGlobalError("Failed to load chat history.", "Received unexpected data format from backend.");
      } else {
          console.log("No history found or history is empty (main.js returned empty array or null).");
      }
    }
  } catch (error) {
    console.error("Error loading chat history via IPC:", error);
    historyStatusMessage.value = `Error: ${error.message || 'Failed to load history due to IPC error.'}`;
    chatMessages.value = [];
    setGlobalError("IPC Error while loading chat history.", error.message || String(error));
  } finally {
    isLoadingHistory.value = false;
    if (!globalError.value.active || (globalError.value.active && !globalError.value.message.includes("chat history"))) {
        setTimeout(() => { historyStatusMessage.value = ''; }, 2000);
    }
  }
}


onMounted(async () => {
  if (window.api && typeof window.api.getVersions === 'function') {
      const v = await window.api.getVersions();
      versions.value = v;
  }
  if (window.api && typeof window.api.cleanupPromptListeners === 'function') {
    window.api.cleanupPromptListeners();
  }
  if (window.api && typeof window.api.cleanupParallelTaskListeners === 'function') {
    window.api.cleanupParallelTaskListeners(); // Clean up any old ones first
  }

  if (window.api && typeof window.api.onParallelGitTaskUpdate === 'function') {
    window.api.onParallelGitTaskUpdate((updateDetails) => {
      console.log('IPC Event: parallel-git-task-update', updateDetails);
      if (activeParallelRun.value && activeParallelRun.value.runId === updateDetails.runId) {
        const agent = activeParallelRun.value.agents.find(a => a.id === updateDetails.agentId);
        if (agent) {
          agent.status = updateDetails.status;
          agent.progress = updateDetails.progress !== undefined ? updateDetails.progress : agent.progress;
          agent.resultSummary = updateDetails.resultSummary !== undefined ? updateDetails.resultSummary : agent.resultSummary;
          agent.error = updateDetails.error !== undefined ? updateDetails.error : agent.error;
          agent.errorMessage = updateDetails.errorMessage !== undefined ? updateDetails.errorMessage : agent.errorMessage;
          agent.isProcessing = updateDetails.isProcessing !== undefined ? updateDetails.isProcessing : false;
        }
      }
    });
  }

  if (window.api && typeof window.api.onParallelGitRunCompleted === 'function') {
    window.api.onParallelGitRunCompleted((completionDetails) => {
        console.log('IPC Event: parallel-git-run-completed', completionDetails);
        if (activeParallelRun.value && activeParallelRun.value.runId === completionDetails.runId) {
            // Optionally, update a run-level status message or trigger UI changes
            setModelMessage.value = `Run ${completionDetails.runId} finished: ${completionDetails.overallStatus}. ${completionDetails.message || ''}`;
            // You might want to disable further actions on this run if it's fully completed/cancelled.
            // For example, iterate agents and mark them as 'Cancelled' if the run was cancelled.
            if (completionDetails.overallStatus === 'Cancelled') {
                activeParallelRun.value.agents.forEach(agent => {
                    if (agent.isProcessing) { // Only affect agents that were still running
                        agent.status = 'Cancelled';
                        agent.isProcessing = false;
                    }
                });
            }
            // Consider if `activeParallelRun` should be cleared or if a "View Summary" state is needed.
        }
        setTimeout(() => { setModelMessage.value = ''; }, 5000);
    });
  }

  await fetchActiveModel();
  await fetchAvailableModels();
  await loadHistory();
});

// Methods for Parallel Task Management
function handleTaskSubmitted(description) {
  currentTaskDescription.value = description;
  // Consider if submitting a task should immediately show agent selection or wait for another action
  console.log('Task submitted in App.vue:', description);
}

function handleAgentsSelected(agents) {
  selectedAgentsForTask.value = agents;
  console.log('Agents selected in App.vue:', agents);
}

// Method to initiate the parallel processing (will be expanded for IPC)
async function startParallelTask() {
  if (!currentTaskDescription.value || selectedAgentsForTask.value.length === 0) {
    setGlobalError('Task description and at least one agent must be selected to start.', 'Please define a task and select agents.');
    return;
  }
  dismissGlobalError();
  // showParallelProcessingUI.value = true; // Show UI optimistically or after success? Let's try after success.

  const taskDetails = {
    taskDescription: currentTaskDescription.value,
    selectedAgents: selectedAgentsForTask.value.map(agent => ({
      id: agent.id,
      name: agent.name,
      provider: agent.provider,
      model: agent.model
      // Include any other necessary agent details from 'agent' object
    })),
  };

  try {
    const result = await window.api.startParallelGitTask(taskDetails);
    if (result && result.success) {
      // Backend confirms start, create the initial UI state based on this
      const initialAgentStates = selectedAgentsForTask.value.map(agent => ({
        ...agent, // id, name, provider, model
        status: 'Queued', // Initial status confirmed by backend
        progress: 0,
        resultSummary: null,
        error: null,
        isProcessing: true, // Assumed to start processing soon
        errorMessage: null,
      }));
      activeParallelRun.value = {
        runId: result.runId, // Use runId from backend
        taskDescription: currentTaskDescription.value,
        agents: initialAgentStates,
      };
      showParallelProcessingUI.value = true;
      setModelMessage.value = result.message || 'Parallel task successfully initiated.'; // Use setModelMessage for general feedback for now
      setTimeout(() => { setModelMessage.value = ''; }, 3000);
    } else {
      setGlobalError(result.error || 'Failed to start parallel task.', result.details || 'Unknown error from backend.');
    }
  } catch (error) {
    console.error('IPC Error starting parallel task:', error);
    setGlobalError('IPC Error', `Could not start parallel task: ${error.message}`);
  }
}

// Methods to handle events from ParallelTaskDisplay
function handleViewFullResult(agentTask) {
  console.log('App.vue: View Full Result for', agentTask);
  // Implement logic to show detailed results, perhaps a modal
  alert(`App.vue: Viewing full result for ${agentTask.name}. Data: ${JSON.stringify(agentTask)}`);
}

async function handleFinalizeSelection(selectedAgentId) {
  if (!activeParallelRun.value || !activeParallelRun.value.runId) {
    setGlobalError('Cannot finalize: No active run ID.', 'Internal error.');
    return;
  }
  console.log('App.vue: Attempting to finalize selection for agent ID', selectedAgentId);
  // Optional: Update UI optimistically or show loading state
  const agentToFinalize = activeParallelRun.value.agents.find(a => a.id === selectedAgentId);
  if (agentToFinalize) agentToFinalize.status = 'Finalizing...';

  try {
    const result = await window.api.finalizeSelectedGitVersion({
      runId: activeParallelRun.value.runId,
      selectedAgentId: selectedAgentId,
    });
    if (result && result.success) {
      setModelMessage.value = result.message || `Version from ${selectedAgentId} finalized.`;
      // Backend might send further 'parallel-git-task-update' or 'parallel-git-run-completed'
      // For now, we can mark the agent as finalized in UI.
      if (agentToFinalize) agentToFinalize.status = 'Finalized';
    } else {
      setGlobalError(result.error || 'Finalization failed.', result.details || 'Unknown error.');
      if (agentToFinalize) agentToFinalize.status = 'Completed'; // Revert status if finalization failed
    }
  } catch (error) {
    console.error('IPC Error finalizing version:', error);
    setGlobalError('IPC Error', `Could not finalize version: ${error.message}`);
    if (agentToFinalize) agentToFinalize.status = 'Completed'; // Revert
  }
  setTimeout(() => { setModelMessage.value = ''; }, 3000);
}

async function handleRetryTask(agentId) {
  if (!activeParallelRun.value || !activeParallelRun.value.runId) {
    setGlobalError('Cannot retry: No active run ID.', 'Internal error.');
    return;
  }
  console.log('App.vue: Attempting to retry task for agent ID', agentId);
  const agentToRetry = activeParallelRun.value.agents.find(a => a.id === agentId);
  if (agentToRetry) {
    agentToRetry.status = 'Retrying...';
    agentToRetry.error = null;
    agentToRetry.errorMessage = null;
    agentToRetry.isProcessing = true;
  }

  try {
    const result = await window.api.retryAgentGitTask({
      runId: activeParallelRun.value.runId,
      agentId: agentId,
    });
    if (result && result.success) {
      setModelMessage.value = result.message || `Retry initiated for ${agentId}.`;
      // Expect backend to send 'parallel-git-task-update' for this agent.
      // UI will update based on those incoming messages.
    } else {
      setGlobalError(result.error || 'Retry initiation failed.', result.details || 'Unknown error.');
      if (agentToRetry) { // Revert status if retry failed to initiate
        agentToRetry.status = 'Error';
        agentToRetry.error = true;
        agentToRetry.errorMessage = result.details || 'Failed to initiate retry.';
        agentToRetry.isProcessing = false;
      }
    }
  } catch (error) {
    console.error('IPC Error retrying task:', error);
    setGlobalError('IPC Error', `Could not retry task: ${error.message}`);
    if (agentToRetry) { // Revert on IPC error
        agentToRetry.status = 'Error';
        agentToRetry.error = true;
        agentToRetry.errorMessage = error.message;
        agentToRetry.isProcessing = false;
    }
  }
  setTimeout(() => { setModelMessage.value = ''; }, 3000);
}

async function cancelCurrentParallelRun() {
  if (!activeParallelRun.value || !activeParallelRun.value.runId) {
    setGlobalError('No active run to cancel.');
    return;
  }
  if (confirm('Are you sure you want to cancel this entire parallel run?')) {
    try {
      const result = await window.api.cancelParallelRun(activeParallelRun.value.runId);
      if (result && result.success) {
        setModelMessage.value = result.message || 'Parallel run cancellation requested.';
        // Expect backend to send 'parallel-git-run-completed' or individual agent updates.
        // Or, optimistically update UI:
        // activeParallelRun.value.agents.forEach(agent => {
        //   if (agent.status !== 'Completed' && agent.status !== 'Finalized') {
        //     agent.status = 'Cancelled';
        //     agent.isProcessing = false;
        //   }
        // });
      } else {
        setGlobalError(result.error || 'Failed to cancel run.', result.details);
      }
    } catch (error) {
      console.error('IPC Error cancelling run:', error);
      setGlobalError('IPC Error', `Could not cancel run: ${error.message}`);
    }
    setTimeout(() => { setModelMessage.value = ''; }, 3000);
  }
}

function resetParallelTaskUI() {
  currentTaskDescription.value = '';
  selectedAgentsForTask.value = [];
  activeParallelRun.value = null;
  showParallelProcessingUI.value = false;
  dismissGlobalError();
}

onBeforeUnmount(() => {
  if (window.api && typeof window.api.cleanupPromptListeners === 'function') {
    window.api.cleanupPromptListeners();
  }
  if (window.api && typeof window.api.cleanupParallelTaskListeners === 'function') {
    window.api.cleanupParallelTaskListeners();
  }
});

</script>

<style scoped>
/* Basic Reset & App Container */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
  overflow: hidden;
}

#app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 15px;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  background-color: #f4f6f8;
  padding-top: 0; /* Adjust if global error banner is active */
}

h1 {
  color: #35495e;
  text-align: center;
  margin-bottom: 10px;
  flex-shrink: 0;
  padding-top: 15px; /* Add padding if no error banner, or adjust based on banner height */
}

.versions {
  margin-bottom: 10px;
  padding: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  font-size: 0.8em;
  text-align: center;
  flex-shrink: 0;
}
.versions p {
  margin: 3px 0;
  display: inline;
  margin-right: 10px;
}

.top-panel {
  display: flex;
  gap: 15px;
  margin-bottom: 10px;
  flex-shrink: 0;
  align-items: flex-start;
}

.model-info {
  padding: 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: #fff;
  flex: 1;
}
.model-info h2, .model-info h3 {
  margin-top: 0;
  margin-bottom: 8px;
  color: #495057;
}
.model-info p {
  margin-bottom: 4px;
  font-size: 0.9em;
}
.model-info strong {
    color: #35495e;
}


.model-selection ul {
  list-style-type: none;
  max-height: 120px;
  overflow-y: auto;
  border: 1px solid #eee;
  padding: 5px;
  border-radius: 4px;
}
.model-selection li {
  margin-bottom: 8px;
  padding: 8px;
  border: 1px solid #f1f1f1;
  border-radius: 4px;
  background-color: #fdfdfd;
  transition: background-color 0.2s ease-in-out;
  font-size: 0.9em;
}
.model-selection li:hover {
  background-color: #f5f5f5;
}
.model-selection li strong {
  color: #007bff;
}

.model-selection li button {
  margin-left: 8px;
  padding: 4px 8px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
  font-size: 0.85em;
}
.model-selection li button:hover {
  background-color: #218838;
}
.model-selection li button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
.model-selection li p {
  font-size: 0.85em;
  color: #6c757d;
  margin-top: 2px;
}
p.feedback-message {
  margin-top: 8px;
  font-size: 0.9em;
  color: #17a2b8;
}
.history-controls {
  padding: 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: #fff;
  flex: 1;
  text-align: center;
}
.history-controls button {
  padding: 10px 18px;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}
.history-controls button:hover:not(:disabled) {
  background-color: #c82333;
}
.history-controls button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
.history-status-message {
  margin-top: 8px;
  font-size: 0.9em;
  min-height: 1.2em;
}


/* Chat messages display area */
.chat-display-area { /* This class is not used on MessageDisplay directly, but similar styling is in MessageDisplay.vue */
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
  background-color: #fff;
  border: 1px solid #ced4da;
  border-radius: 4px;
  margin-bottom: 10px;
}
/* MessageDisplay.vue has its own styles for .message, .user, .assistant etc. */


.prompt-test { /* This class is from an old version or example, ChatInput.vue has its own styling */
  display: flex;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: #fff;
  flex-shrink: 0;
}

.prompt-test input[type="text"] {
  flex-grow: 1;
  padding: 10px;
  margin-right: 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1em;
}
.prompt-test button {
  padding: 10px 18px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}
.prompt-test button:hover:not(:disabled) {
  background-color: #0056b3;
}
.prompt-test button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

/* Global Error Banner Styles */
.global-error-banner {
  background-color: #dc3545; /* Red */
  color: white;
  padding: 15px;
  margin: 0 -15px 15px -15px; /* Extend to full width of parent padding, then add margin for content below */
  border-bottom: 2px solid #c82333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  z-index: 1000;
  flex-shrink: 0; /* Prevent banner from shrinking */
}
.global-error-banner .error-content {
  flex-grow: 1;
  margin-right: 15px;
}
.global-error-banner p {
  margin: 0;
  font-size: 1.0em; /* Adjusted font size */
}
.global-error-banner strong {
    font-weight: bold;
}
.global-error-banner .error-details {
  background-color: rgba(0,0,0,0.15);
  padding: 8px;
  border-radius: 3px;
  margin-top: 8px;
  font-size: 0.8em;
  max-height: 80px; /* Adjusted max-height */
  overflow-y: auto;
  white-space: pre-wrap;
  color: #f8d7da; /* Lighter text for details on dark red bg */
}
.global-error-banner .error-actions {
  display: flex;
  gap: 8px; /* Reduced gap */
  align-items: center;
}
.global-error-banner .action-button {
  background-color: rgba(255,255,255,0.8);
  color: #dc3545; /* Red text */
  border: 1px solid rgba(255,255,255,0.5);
  padding: 5px 10px; /* Adjusted padding */
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em; /* Adjusted font size */
  font-weight: bold;
}
.global-error-banner .action-button.dismiss-button {
  background-color: white;
  color: #dc3545;
}
.global-error-banner .action-button:hover {
  background-color: rgba(255,255,255,0.9);
  border-color: white;
}
.global-error-banner .action-button.dismiss-button:hover {
  background-color: #f8f9fa;
}

.loading-history-text {
  text-align: center;
  padding: 15px;
  font-style: italic;
  color: #6c757d;
}

.config-area { /* Added style */
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #dee2e6; /* A subtle separator */
  flex-shrink: 0; /* Prevent it from shrinking if content above grows */
  max-height: 300px; /* Example max height, adjust as needed */
  overflow-y: auto; /* Allow scrolling if content is taller than max-height */
}

.parallel-task-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid #6c757d; /* Darker separator */
}

.parallel-task-section h2 {
  margin-bottom: 15px;
  color: #35495e;
}

.parallel-task-section h3 {
  margin-top: 10px;
  margin-bottom: 5px;
  color: #495057;
}

.start-parallel-task-button, .reset-parallel-ui-button {
  padding: 10px 15px;
  font-size: 1em;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 15px;
  display: block; /* Make it block to take full width or add more specific layout */
}
.start-parallel-task-button:hover, .reset-parallel-ui-button:hover {
  background-color: #0056b3;
}
.reset-parallel-ui-button {
    background-color: #ffc107;
    color: #212529;
    margin-bottom: 10px;
}
.reset-parallel-ui-button:hover {
    background-color: #e0a800;
}

.cancel-parallel-run-button {
  padding: 10px 15px;
  font-size: 1em;
  color: #fff;
  background-color: #dc3545; /* Red */
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 10px;
  margin-left: 10px; /* If placed next to reset button */
  display: inline-block;
}
.cancel-parallel-run-button:hover {
  background-color: #c82333;
}
</style>
