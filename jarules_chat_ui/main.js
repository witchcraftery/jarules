// jarules_chat_ui/main.js
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

function createWindow () {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js') // Make sure preload is linked
    }
  });
  mainWindow.loadFile('index.html');
  // mainWindow.webContents.openDevTools(); // Optional: for debugging
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// IPC Listener (NEW PART)
ipcMain.on('to-main-channel', (event, message) => {
  console.log('Message received in main process on "to-main-channel":', message);
  // Send an echo back to the renderer process
  event.reply('from-main-channel', 'Main process echo: ' + message);
});
