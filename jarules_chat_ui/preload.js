// jarules_chat_ui/preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  sendMessageToMain: (message) => ipcRenderer.send('to-main-channel', message),
  receiveMessageFromMain: (callback) => ipcRenderer.on('from-main-channel', (_event, ...args) => callback(...args))
  // Note: _event is passed by ipcRenderer.on, but often not needed by the final callback in renderer.js
});
