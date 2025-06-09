<template>
  <div id="app-container">
    <h1>{{ message }}</h1>

    <div class="versions">
      <p>Electron: <span id="electron-version">{{ versions.electron }}</span></p>
      <p>Node: <span id="node-version">{{ versions.node }}</span></p>
      <p>Chrome: <span id="chrome-version">{{ versions.chrome }}</span></p>
    </div>

    <div class="model-info">
      <h2>LLM Management</h2>
      <p><strong>Active Model ID:</strong> {{ activeModelId || 'Loading...' }}</p>

      <div class="model-selection">
        <h3>Available Models:</h3>
        <ul v-if="availableModels.length > 0">
          <li v-for="model in availableModels" :key="model.id">
            <strong>{{ model.name }}</strong> (ID: {{ model.id }}, Provider: {{ model.provider }})
            <button @click="selectModel(model.id)" :disabled="model.id === activeModelId">
              Set Active
            </button>
            <p><em>{{ model.description }}</em></p>
          </li>
        </ul>
        <p v-else>Loading models or no models available...</p>
      </div>
      <p v-if="setModelMessage">{{ setModelMessage }}</p>
    </div>

    <div class="prompt-test">
      <h3>Test Prompt:</h3>
      <input type="text" v-model="testPrompt" placeholder="Enter a test prompt" />
      <button @click="handleSendPrompt">Send Test Prompt</button>
      <div v-if="promptResponse" class="response-area">
        <h4>Response:</h4>
        <pre>{{ promptResponse }}</pre>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'; // Import computed

const message = ref('Hello from JaRules (Electron + Vue.js + Vite!)');
const versions = ref({ electron: '', node: '', chrome: '' });

const activeModelId = ref(null);
const availableModels = ref([]);
const setModelMessage = ref(''); // For feedback after trying to set a model

// Computed property to get the full details of the active model
const activeModelDetails = computed(() => {
  if (!activeModelId.value || availableModels.value.length === 0) {
    return null;
  }
  return availableModels.value.find(model => model.id === activeModelId.value);
});

const testPrompt = ref('Tell me a fun fact about Electron.');
const promptResponse = ref('');


async function fetchActiveModel() {
  try {
    // main.js's getActiveModel directly returns the ID or null from the Python script's JSON output.
    const id = await window.api.getActiveModel();
    activeModelId.value = id; // This could be null if nothing is set or file doesn't exist
    if (!id) {
      console.log('No active model ID returned from backend.');
    }
  } catch (error) {
    console.error('Error fetching active model:', error);
    activeModelId.value = 'Error loading active model';
  }
}

async function fetchAvailableModels() {
  try {
    // main.js's listAvailableModels directly returns the array of models or null/throws.
    const models = await window.api.listAvailableModels();
    if (models && Array.isArray(models)) {
      availableModels.value = models;
    } else if (models && models.error) {
      console.error('Error fetching available models from backend:', models.error);
      availableModels.value = [{ id: 'error', name: 'Could not load models', description: models.error, provider: 'Error' }];
    } else {
      console.error('Invalid or empty response when fetching available models:', models);
      availableModels.value = [{ id: 'empty', name: 'No models returned or invalid format', description: '', provider: 'System' }];
    }
  } catch (error) { // Catch errors from ipcRenderer.invoke itself
    console.error('Error fetching available models via IPC:', error);
    availableModels.value = [{ id: 'ipc_error', name: 'IPC Error loading models', description: error.message, provider: 'System' }];
  }
}

async function selectModel(modelId) {
  setModelMessage.value = 'Setting model...';
  try {
    const result = await window.api.setActiveModel(modelId);
    if (result && result.success) {
      activeModelId.value = modelId; // Update active model locally on success
      setModelMessage.value = result.message || `Successfully set active model to ${modelId}.`;
    } else {
      setModelMessage.value = `Failed: ${result ? result.message || result.error : 'Unknown error setting model.'}`;
    }
  } catch (error) {
    console.error('Error setting active model via IPC:', error);
    setModelMessage.value = `Error: ${error.message || 'Failed to set model due to IPC error.'}`;
  }
}

async function handleSendPrompt() {
  if (!testPrompt.value.trim()) {
    promptResponse.value = "Please enter a prompt.";
    return;
  }
  promptResponse.value = "Sending prompt, please wait...";
  try {
    const result = await window.api.sendPrompt(testPrompt.value);
    if (result && result.success) {
      promptResponse.value = result.response;
    } else {
      promptResponse.value = `Error: ${result ? result.error : 'Failed to get response from LLM.'}`;
    }
  } catch (error) {
    console.error('Error sending prompt via IPC:', error);
    promptResponse.value = `Error: ${error.message || 'Failed to send prompt due to IPC error.'}`;
  }
}

onMounted(async () => {
  // Fetch versions using the new API if the DOMContentLoaded approach is removed from preload.js
  // For now, this will also work if the spans are already populated.
  if (window.api && typeof window.api.getVersions === 'function') {
      const v = await window.api.getVersions();
      versions.value = v;
      // Clear the old spans if they were populated by preload.js directly
      // to avoid duplicate content if Vue is also setting them.
      // document.getElementById('electron-version').innerText = '';
      // etc. for node and chrome. Or, just rely on Vue to overwrite.
  }

  await fetchActiveModel();
  await fetchAvailableModels();
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
  overflow: hidden; /* Prevent body scrollbars when app-container handles scrolling */
}

#app-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Full viewport height */
  padding: 15px;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  background-color: #f4f6f8; /* Light background for the whole app */
}

h1 {
  color: #35495e; /* Slightly darker Vue green */
  text-align: center;
  margin-bottom: 15px;
}

.versions {
  margin-bottom: 15px;
  padding: 8px;
  background-color: #e9ecef; /* Lighter grey */
  border-radius: 4px;
  font-size: 0.8em;
}
.versions p {
  margin: 3px 0;
  text-align: center;
}

.model-info {
  margin-bottom: 15px;
  padding: 12px;
  border: 1px solid #ced4da; /* Softer border */
  border-radius: 4px;
  background-color: #fff;
}
.model-info h2, .model-info h3 {
  margin-bottom: 8px;
  color: #495057;
}
.model-info p {
  margin-bottom: 4px;
}

.model-selection ul {
  list-style-type: none;
  max-height: 200px; /* Limit height and make scrollable if many models */
  overflow-y: auto;
  border: 1px solid #eee;
  padding: 5px;
  border-radius: 4px;
}
.model-selection li {
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid #f1f1f1;
  border-radius: 4px;
  background-color: #fdfdfd;
  transition: background-color 0.2s ease-in-out;
}
.model-selection li:hover {
  background-color: #f5f5f5;
}
.model-selection li strong {
  color: #007bff;
}

.model-selection li button {
  margin-left: 10px;
  padding: 5px 10px;
  background-color: #28a745; /* Green */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}
.model-selection li button:hover {
  background-color: #218838;
}
.model-selection li button:disabled {
  background-color: #6c757d; /* Grey for disabled */
  cursor: not-allowed;
}
.model-selection li p { /* Description */
  font-size: 0.9em;
  color: #6c757d; /* Muted text color */
  margin-top: 3px;
}

.prompt-test {
  display: flex; /* Align input and button */
  flex-direction: column; /* Stack input/button above response area */
  padding: 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: #fff;
  margin-top: auto; /* Pushes to the bottom if #app-container is flex-column */
}
.prompt-test-input-group {
  display: flex;
  margin-bottom: 10px;
}
.prompt-test input[type="text"] {
  flex-grow: 1; /* Input takes available space */
  padding: 10px;
  margin-right: 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1em;
}
.prompt-test button {
  padding: 10px 18px;
  background-color: #007bff; /* Blue */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}
.prompt-test button:hover {
  background-color: #0056b3;
}

.response-area {
  /* margin-top: 10px; Removed margin as it's now part of the flex column */
  padding: 10px;
  background-color: #e9ecef; /* Lighter grey for response */
  border: 1px solid #ced4da;
  border-radius: 4px;
  white-space: pre-wrap;
  min-height: 60px; /* Give it some initial height */
  overflow-y: auto; /* Scroll if content is too long */
  flex-grow: 1; /* Allows this area to expand if .prompt-test is flex column */
}
</style>
