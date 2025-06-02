// preload.js

// All of the Node.js APIs are available in the preload process.
// It has the same sandbox as a Chrome extension.
window.addEventListener('DOMContentLoaded', () => {
  const replaceText = (selector, text) => {
    const element = document.getElementById(selector);
    if (element) element.innerText = text;
  };

  for (const dependency of ['chrome', 'node', 'electron']) {
    replaceText(`${dependency}-version`, process.versions[dependency]);
  }
});

// Example of exposing a simple function to the renderer process:
// (We'll use this more formally later for IPC)
// const { contextBridge } = require('electron');
// contextBridge.exposeInMainWorld('myAPI', {
//  doAThing: () => {}
// });
