// preload.js
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object.
contextBridge.exposeInMainWorld('api', {
  // LLM Interaction APIs (invoking main process handlers)
  listAvailableModels: () => ipcRenderer.invoke('listAvailableModels'),
  getActiveModel: () => ipcRenderer.invoke('getActiveModel'),
  setActiveModel: (modelId) => ipcRenderer.invoke('setActiveModel', modelId),
  getConfig: () => ipcRenderer.invoke('get-llm-config'), // Added for LLM config
  // sendPrompt: (prompt) => ipcRenderer.invoke('sendPrompt', prompt), // OLD request-response
  stopGeneration: () => ipcRenderer.invoke('stop-llm-generation'),

  // NEW for streaming:
  // The Vue component will pass callback functions to handle different stream events.
  sendPromptStreaming: (prompt, onStart, onChunk, onError, onDone) => {
    // Send the prompt to the main process.
    ipcRenderer.send('llm:send-prompt-streaming', prompt);

    // Clean up previous listeners to avoid duplicates if this function is called again.
    // This is important for re-entrant calls.
    ipcRenderer.removeAllListeners('llm:stream-started');
    ipcRenderer.removeAllListeners('llm:stream-chunk');
    ipcRenderer.removeAllListeners('llm:stream-error');
    ipcRenderer.removeAllListeners('llm:stream-done');

    // Set up new listeners for the current prompt request.
    ipcRenderer.on('llm:stream-started', (event, message) => {
      if (onStart && typeof onStart === 'function') onStart(message);
    });
    ipcRenderer.on('llm:stream-chunk', (event, message) => {
      if (onChunk && typeof onChunk === 'function') onChunk(message);
    });
    ipcRenderer.on('llm:stream-error', (event, errorDetails) => {
      if (onError && typeof onError === 'function') onError(errorDetails);
    });
    ipcRenderer.on('llm:stream-done', (event, doneDetails) => {
      if (onDone && typeof onDone === 'function') onDone(doneDetails);
      // Once done, it's good practice to clean up these specific listeners here as well,
      // especially if onDone signifies the absolute end of this interaction.
      // However, cleanupPromptListeners can also be called from Vue's onUnmounted or before a new prompt.
      // For simplicity here, we'll let cleanupPromptListeners handle it if called.
    });
  },

  // Utility to explicitly clean up listeners.
  // This should be called from the Vue component, e.g., in onUnmounted or before sending a new prompt.
  cleanupPromptListeners: () => {
    ipcRenderer.removeAllListeners('llm:stream-started');
    ipcRenderer.removeAllListeners('llm:stream-chunk');
    ipcRenderer.removeAllListeners('llm:stream-error');
    ipcRenderer.removeAllListeners('llm:stream-done');
    console.log('[Preload] Cleaned up all LLM stream listeners.');
  },

  // Chat History APIs
  loadChatHistory: () => ipcRenderer.invoke('history:load'),
  addChatMessage: (message) => ipcRenderer.send('history:add-message', message), // Fire-and-forget style
  clearChatHistory: () => ipcRenderer.invoke('history:clear'),

  // You can also expose other utility functions if needed, for example,
  // to get Electron versions if you remove the DOMContentLoaded listener below.
  getVersions: () => ({
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  }),

  // Parallel Git Task APIs
  startParallelGitTask: (taskDetails) => ipcRenderer.invoke('start-parallel-git-task', taskDetails),
  finalizeSelectedGitVersion: (finalizationDetails) => ipcRenderer.invoke('finalize-selected-git-version', finalizationDetails),
  retryAgentGitTask: (retryDetails) => ipcRenderer.invoke('retry-agent-git-task', retryDetails),
  cancelParallelRun: (runId) => ipcRenderer.invoke('cancel-parallel-git-run', runId),

  // Listener setup functions
  onParallelGitTaskUpdate: (callback) => ipcRenderer.on('parallel-git-task-update', (_event, value) => callback(value)),
  onParallelGitRunCompleted: (callback) => ipcRenderer.on('parallel-git-run-completed', (_event, value) => callback(value)),

  // Function to clean up listeners (important for components being unmounted or re-created)
  cleanupParallelTaskListeners: () => {
    ipcRenderer.removeAllListeners('parallel-git-task-update');
    ipcRenderer.removeAllListeners('parallel-git-run-completed');
    console.log('[Preload] Cleaned up all Parallel Git Task stream listeners.');

  },

  // Diagnostics APIs
  runAllDiagnostics: () => ipcRenderer.invoke('run-all-diagnostics'),

  // Sets up a global listener. App.vue should manage calling cleanup.
  onDiagnosticCheckUpdate: (callback) => ipcRenderer.on('diagnostic-check-update', (_event, value) => callback(value)),

  cleanupDiagnosticListeners: () => { // Use this name
    ipcRenderer.removeAllListeners('diagnostic-check-update');
    console.log('[Preload] Cleaned up all Diagnostic listeners.');

  }
});


// The DOMContentLoaded listener below is fine for displaying versions initially,
// but for more complex apps, Vue/React components would handle this display.
// If App.vue will handle displaying versions via window.api.getVersions(), this can be removed.
// For now, let's keep it as it doesn't harm, but know it's separate from contextBridge.
window.addEventListener('DOMContentLoaded', () => {
  const replaceText = (selector, text) => {
    const element = document.getElementById(selector);
    if (element) element.innerText = text;
  };

  for (const dependency of ['chrome', 'node', 'electron']) {
    if (process.versions[dependency]) { // Check if version exists
        replaceText(`${dependency}-version`, process.versions[dependency]);
    } else {
        replaceText(`${dependency}-version`, 'N/A');
    }
  }
});
