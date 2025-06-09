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
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from 'vue';
import MessageDisplay from './components/MessageDisplay.vue';
import ChatInput from './components/ChatInput.vue';

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

  await fetchActiveModel();
  await fetchAvailableModels();
  await loadHistory();
});

onBeforeUnmount(() => {
  if (window.api && typeof window.api.cleanupPromptListeners === 'function') {
    window.api.cleanupPromptListeners();
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
.chat-display-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
  background-color: #fff;
  border: 1px solid #ced4da;
  border-radius: 4px;
  margin-bottom: 10px;
}
.message {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  word-wrap: break-word;
  white-space: pre-wrap;
  max-width: 90%;
}
.message.user {
  background-color: #007bff;
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 0;
}
.message.assistant {
  background-color: #e9ecef;
  color: #343a40;
  margin-right: auto;
  border-bottom-left-radius: 0;
}
.message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
.streaming-indicator {
  font-style: italic;
  color: #6c757d;
}


.prompt-test {
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
  /* position: sticky; Removed sticky as it complicates padding on #app-container */
  /* top: 0; */
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
</style>
