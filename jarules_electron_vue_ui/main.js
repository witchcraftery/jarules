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
    console.log(`[PythonShell] Result from ${scriptName}:`, results ? results[0] : 'No result');
    // PythonShell in JSON mode returns an array of parsed JSON objects (one per line).
    // Our scripts are designed to print a single JSON object as the last relevant output.
    const primaryResult = results ? results[0] : null;
    if (primaryResult === null && !results) { // No output at all
        return {error: true, message: `No output from ${scriptName}.`, details: "Script produced no JSON output or an empty response."};
    }
    return primaryResult; // This might be a success object or a Python-app-level error object like {"error": true, ...}
  } catch (err) {
    // This catches errors from PythonShell itself (e.g., script not found, python not executable)
    // or if Python script exits with non-zero and prints non-JSON to stderr.
    console.error(`[PythonShell] Failed to run script ${scriptName} or critical error during execution:`, err);
    return {error: true, message: `Failed to execute JaRules agent process: ${scriptName}.`, details: err.message || String(err)};
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
    // If fetching failed at startup, currentAvailableModels might be empty or contain an error placeholder.
    // This handler should ensure it always returns an array to the renderer, or an error object if it must.
    // The Python script itself returns {"models": []} or {"error": true, ...}
    // runPythonScript standardizes shell errors.
    const result = (currentAvailableModels.length > 0 && !currentAvailableModels[0]?.error)
                   ? currentAvailableModels
                   : await runPythonScript('get_available_models_wrapper.py');

    if (result && result.error) { // Error from Python script or runPythonScript
        console.error('[IPC Main] Error listing available models:', result.message, result.details);
        return []; // Return empty array to renderer on error, matching behavior of Python script
    }
    if (result && Array.isArray(result.models)) {
        currentAvailableModels = result.models; // Cache successful fetch
        return currentAvailableModels;
    }
    // Fallback for unexpected structure, though runPythonScript should catch most.
    return [];
  });

  ipcMain.handle('getActiveModel', async () => {
    console.log('[IPC Main] Received getActiveModel request.');
    // This should ideally re-fetch from Python script if not using a cached value
    // or if cache can be stale. For now, it uses currentActiveModelId set at startup/setActiveModel.
    // If currentActiveModelId is null, it's fine.
    // The Python script `get_active_model_wrapper.py` returns {"active_provider_id": id_or_null} or {"error": true, ...}
    const result = await runPythonScript('get_active_model_wrapper.py');
    if (result && result.error) {
        console.error('[IPC Main] Error getting active model:', result.message, result.details);
        return null; // Renderer expects ID string or null
    }
    currentActiveModelId = result ? result.active_provider_id : null;
    return currentActiveModelId;
  });

  ipcMain.handle('setActiveModel', async (event, modelId) => {
    console.log(`[IPC Main] Received setActiveModel request for ID: ${modelId}`);
    try {
      const result = await runPythonScript('set_active_model_wrapper.py', [modelId]);
      // Python script returns {"success": true, ...} or {"error": true, ...}
      if (result && result.success) {
        currentActiveModelId = modelId;
        console.log(`[IPC Main] Active model set to: ${modelId}`);
        return result;
      } else {
        console.error(`[IPC Main] Failed to set model:`, result ? (result.message + (result.details? ` (${result.details})` : '')) : "Unknown error from script execution.");
        return result || {error: true, message: "Unknown error setting active model."};
      }
    } catch (err) { // Should ideally be caught by runPythonScript, but as a safeguard.
      console.error('[IPC Main] Unexpected error in setActiveModel IPC handler:', err);
      return {error: true, message: err.message || `Failed to set model ${modelId}.`, details: String(err)};
    }
  });

  // Changed from ipcMain.handle to ipcMain.on for streaming
  ipcMain.on('llm:send-prompt-streaming', (event, userPrompt) => {
    console.log(`[IPC Main] Streaming: Received sendPrompt: "${userPrompt}" for active model: ${currentActiveModelId}`);

    // Convert null or undefined currentActiveModelId to string "null" or "undefined" for python script args.
    // The python script for send_prompt_wrapper.py is set up to handle these strings.
    const activeModelIdArg = currentActiveModelId === null || currentActiveModelId === undefined ?
                             String(currentActiveModelId) : currentActiveModelId;

    if (!currentActiveModelId) { // Still check for null/undefined before sending to Python for clarity in JS logs
      console.error('[IPC Main] Streaming: No active model selected for sendPrompt.');
      event.sender.send('llm:stream-error', { message: 'No active model selected. Please select a model first.' });
      event.sender.send('llm:stream-done', { success: false, error: 'No active model selected.'});
      return;
    }

    const options = {
      mode: 'json', // Each line from Python is expected to be a JSON object
      pythonOptions: ['-u'], // unbuffered stdout
      scriptPath: pythonBridgeDir,
      args: [userPrompt, String(currentActiveModelId)] // Ensure currentActiveModelId is passed as string
    };

    const pyshell = new PythonShell('send_prompt_wrapper.py', options);

    // Optional: Send a message to renderer that streaming has started, if not implied by first chunk.
    // event.sender.send('llm:stream-started'); // Python script now sends a stream_start message

    pyshell.on('message', function (message) {
      // message is already a parsed JSON object because of mode: 'json'
      // The Python script now sends structured messages: { type: 'chunk'/'done'/'error', ... }
      console.log("[IPC Main] PythonShell message:", message);

      if (message.type === 'chunk') {
        event.sender.send('llm:stream-chunk', message);
      } else if (message.type === 'done') {
        event.sender.send('llm:stream-done', { success: true, ...message });
      } else if (message.type === 'error') {
        event.sender.send('llm:stream-error', message);
        // Also send 'done' because the stream has effectively ended, even with an error.
        event.sender.send('llm:stream-done', { success: false, error: message.message });
      } else if (message.type === 'stream_start') {
         event.sender.send('llm:stream-started', message); // Forward start signal
      }
      // Other message types can be handled or ignored
    });

    pyshell.end(function (err, code, signal) {
      if (err) {
        console.error('[IPC Main] PythonShell execution finished with error:', err);
        event.sender.send('llm:stream-error', { message: err.message || 'Python script execution failed.' });
        event.sender.send('llm:stream-done', { success: false, error: err.message || 'Python script execution failed.' });
      } else {
        console.log('[IPC Main] PythonShell execution finished successfully (code, signal):', code, signal);
      }
    });
  });

  // --- Chat History IPC Handlers ---
  ipcMain.handle('history:load', async () => {
    console.log('[IPC Main] Received history:load request.');
    try {
      const result = await runPythonScript('get_chat_history_wrapper.py');
      // Python script `get_chat_history_wrapper.py` returns JSON list `[]` on error,
      // or `{"error": true, ...}` if it was modified to do so.
      // Assuming it returns list `[]` on its own internal errors, or the list of messages.
      // If runPythonScript itself returns an error object:
      if (result && result.error) {
          console.error('[IPC Main] Error loading history (from runPythonScript):', result.message, result.details);
          return []; // Return empty list to renderer
      }
      // Ensure it's an array from a successful Python call
      return Array.isArray(result) ? result : [];
    } catch (err) { // Should be caught by runPythonScript
      console.error('[IPC Main] Unexpected error in history:load IPC handler:', err);
      return []; // Default to empty list on severe error
    }
  });

  ipcMain.on('history:add-message', async (event, messageObject) => {
    console.log('[IPC Main] Received history:add-message request with message:', messageObject);
    if (!messageObject) {
      console.error('[IPC Main] history:add-message: No message object provided.');
      // Optionally send status back: event.sender.send('history:save-status', {success: false, error: ...});
      return;
    }
    try {
      const messageJsonString = JSON.stringify(messageObject);
      const result = await runPythonScript('save_chat_message_wrapper.py', [messageJsonString]);
      if (result && result.success) {
        console.log('[IPC Main] Message saved successfully.');
        // event.sender.send('history:save-status', {success: true});
      } else {
        console.error('[IPC Main] Failed to save message via Python script:', result ? result.error : "Unknown error");
        // event.sender.send('history:save-status', {success: false, error: result ? result.error : "Unknown error"});
      }
    } catch (err) {
      console.error('[IPC Main] Error in history:add-message IPC handler:', err);
      // event.sender.send('history:save-status', {success: false, error: err.message});
    }
  });

  ipcMain.handle('history:clear', async () => {
    console.log('[IPC Main] Received history:clear request.');
    try {
      const result = await runPythonScript('clear_chat_history_wrapper.py');
      // Python script returns {"success": true, ...} or {"error": true, ...}
      if (result && result.success) {
        return result;
      } else {
        console.error(`[IPC Main] Failed to clear history:`, result ? (result.message + (result.details? ` (${result.details})` : '')) : "Unknown error from script execution.");
        return result || {error: true, message: "Unknown error clearing history."};
      }
    } catch (err) { // Should ideally be caught by runPythonScript
      console.error('[IPC Main] Unexpected error in history:clear IPC handler:', err);
      return {error: true, message: err.message || 'Failed to clear chat history.', details: String(err)};
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
