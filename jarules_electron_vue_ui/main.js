const { app, BrowserWindow } = require('electron');
const path = require('path');

// Determine if running in development or production
const isDev = process.env.NODE_ENV !== 'production';

function createWindow() {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      // Recommended for security:
      // contextIsolation: true, 
      // nodeIntegration: false, 
    },
  });

  // Load the index.html of the app.
  if (isDev) {
    // In development, load from the Vite dev server
    // Ensure Vite dev server is running on this port
    mainWindow.loadURL('http://localhost:5173'); 
    // Open the DevTools.
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load the built index.html file
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
  }
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
