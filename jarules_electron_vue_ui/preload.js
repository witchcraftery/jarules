// preload.js
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object.
contextBridge.exposeInMainWorld('api', {
  // LLM Interaction APIs (invoking main process handlers)
  listAvailableModels: () => ipcRenderer.invoke('listAvailableModels'),
  getActiveModel: () => ipcRenderer.invoke('getActiveModel'),
  setActiveModel: (modelId) => ipcRenderer.invoke('setActiveModel', modelId),
  sendPrompt: (prompt) => ipcRenderer.invoke('sendPrompt', prompt),

  // You can also expose other utility functions if needed, for example,
  // to get Electron versions if you remove the DOMContentLoaded listener below.
  getVersions: () => ({
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  })
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
