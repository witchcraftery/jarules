const { app, BrowserWindow, ipcMain } = require('electron'); // Ensure ipcMain is imported here
const path = require('path');
const { PythonShell } = require('python-shell');

// Determine if running in development or production
const isDev = process.env.NODE_ENV !== 'production';

// --- Global variables to store LLM state in main process ---
let currentActiveModelId = null;
let currentAvailableModels = [];
// --- Path to Python scripts ---
// Assuming 'jarules_agent' is a sibling directory to 'jarules_electron_vue_ui'
const jarulesAgentBaseDir = path.join(__dirname, '../../jarules_agent');
const pythonBridgeDir = path.join(jarulesAgentBaseDir, 'electron_bridge'); // For new wrapper scripts

// Helper function to run Python scripts
async function runPythonScript(scriptName, args = []) {
  const options = {
    mode: 'json', // Expect JSON output from Python scripts
    pythonOptions: ['-u'], // unbuffered stdout
    scriptPath: pythonBridgeDir,
    args: args,
  };
  try {
    console.log(`[PythonShell] Running ${scriptName} with args: ${args.join(' ')}`);
    const results = await PythonShell.run(scriptName, options);
    console.log(`[PythonShell] Result from ${scriptName}:`, results ? results[0] : 'No result'); // PythonShell in JSON mode usually returns an array with one item
    return results ? results[0] : null; // Assuming script prints a single JSON object
  } catch (err) {
    console.error(`[PythonShell] Error running ${scriptName}:`, err);
    throw err; // Re-throw to be caught by IPC handler
  }
}


function createWindow() {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      // Recommended for security:
      contextIsolation: true, // Enable context isolation
      nodeIntegration: false, // Disable Node.js integration in renderer
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
app.whenReady().then(async () => {
  // --- Initialize LLM state by calling Python scripts ---
  try {
    const activeModelResult = await runPythonScript('get_active_model_wrapper.py');
    if (activeModelResult && activeModelResult.active_provider_id) {
      currentActiveModelId = activeModelResult.active_provider_id;
      console.log('[IPC Main] Initial active model loaded:', currentActiveModelId);
    } else {
      console.log('[IPC Main] No initial active model found or script returned null.');
    }
  } catch (error) {
    console.error('[IPC Main] Failed to load initial active model:', error);
  }

  try {
    const availableModelsResult = await runPythonScript('get_available_models_wrapper.py');
    if (availableModelsResult && Array.isArray(availableModelsResult.models)) {
      currentAvailableModels = availableModelsResult.models;
      console.log('[IPC Main] Initial available models loaded:', currentAvailableModels.length, "models found.");
    } else {
      console.log('[IPC Main] No initial available models found or script returned invalid format.');
    }
  } catch (error) {
    console.error('[IPC Main] Failed to load initial available models:', error);
  }

  // --- IPC Handlers ---
  ipcMain.handle('listAvailableModels', async () => {
    console.log('[IPC Main] Received listAvailableModels request.');
    // Return cached models; could re-fetch if data can change frequently
    // For now, assume models are loaded at startup.
    if (currentAvailableModels.length === 0) { // Attempt to load if empty
        try {
            const modelsResult = await runPythonScript('get_available_models_wrapper.py');
            if (modelsResult && Array.isArray(modelsResult.models)) {
                currentAvailableModels = modelsResult.models;
            }
        } catch (error) { /* error already logged by runPythonScript */ }
    }
    return currentAvailableModels;
  });

  ipcMain.handle('getActiveModel', async () => {
    console.log('[IPC Main] Received getActiveModel request.');
    // Return cached active model; could re-fetch if needed
    return currentActiveModelId;
  });

  ipcMain.handle('setActiveModel', async (event, modelId) => {
    console.log(`[IPC Main] Received setActiveModel request for ID: ${modelId}`);
    try {
      const result = await runPythonScript('set_active_model_wrapper.py', [modelId]);
      if (result && result.success) {
        currentActiveModelId = modelId; // Update global state
        console.log(`[IPC Main] Active model set to: ${modelId}`);
        // Optionally, re-fetch available models if setActiveModel could change them (unlikely)
        // Or re-fetch active model to confirm, but script should be source of truth.
        return { success: true, message: result.message || `Active model set to ${modelId}.` };
      } else {
        console.error(`[IPC Main] Failed to set model via Python script:`, result ? result.error : "Unknown error");
        return { success: false, message: result ? result.error : `Failed to set model ${modelId}.` };
      }
    } catch (err) {
      console.error(`[IPC Main] Error in setActiveModel IPC handler:`, err);
      return { success: false, message: err.message || `Failed to set model ${modelId}.` };
    }
  });

  ipcMain.handle('sendPrompt', async (event, userPrompt) => {
    console.log(`[IPC Main] Received sendPrompt: "${userPrompt}" for active model: ${currentActiveModelId}`);
    if (!currentActiveModelId) {
      console.error('[IPC Main] No active model selected for sendPrompt.');
      return { success: false, error: 'No active model selected. Please select a model first.' };
    }
    try {
      // The wrapper script will take the prompt and use the currently active model (via LLMManager)
      // Or, pass currentActiveModelId if the script needs it explicitly.
      // Let's assume the wrapper script for send_prompt will use the persisted active model.
      const result = await runPythonScript('send_prompt_wrapper.py', [userPrompt, currentActiveModelId]);
      if (result && result.response) {
         console.log('[IPC Main] Prompt response received.');
        return { success: true, response: result.response };
      } else if (result && result.error) {
        console.error('[IPC Main] Error from send_prompt_wrapper.py:', result.error);
        return { success: false, error: result.error };
      } else {
        console.error('[IPC Main] Unknown error or empty response from send_prompt_wrapper.py');
        return { success: false, error: 'Unknown error or empty response from agent.' };
      }
    } catch (err) {
      console.error(`[IPC Main] Error in sendPrompt IPC handler:`, err);
      return { success: false, error: err.message || 'Failed to process prompt with JaRules agent.' };
    }
  });

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
