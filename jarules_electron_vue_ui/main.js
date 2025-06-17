const { app, BrowserWindow, ipcMain } = require('electron'); // Ensure ipcMain is imported here
const path = require('path');
const fs = require('fs/promises');
const { PythonShell } = require('python-shell');

// Determine if running in development or production
const isDev = process.env.NODE_ENV !== 'production';

// --- Global variables to store LLM state in main process ---
let currentActiveModelId = null;
let currentAvailableModels = [];
let currentPythonShellInstance = null; // For managing the LLM streaming process
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
    currentPythonShellInstance = pyshell; // Assign to global variable

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
        currentPythonShellInstance = null; // Clear instance on done
      } else if (message.type === 'error') {
        event.sender.send('llm:stream-error', message);
        // Also send 'done' because the stream has effectively ended, even with an error.
        // Pass cancelled flag if present in the error message from python
        event.sender.send('llm:stream-done', { success: false, error: message.message, cancelled: message.cancelled });
        currentPythonShellInstance = null; // Clear instance on error
      } else if (message.type === 'stream_start') {
         event.sender.send('llm:stream-started', message); // Forward start signal
      }
      // Other message types can be handled or ignored
    });

    pyshell.end(function (err, code, signal) {
      if (err) {
        console.error('[IPC Main] PythonShell execution finished with error:', err);
        // Check if a stream-done hasn't already been sent by an error type message
        if (currentPythonShellInstance) { // If null, means 'done' or 'error' message already handled it
            event.sender.send('llm:stream-error', { message: err.message || 'Python script execution failed.' });
            event.sender.send('llm:stream-done', { success: false, error: err.message || 'Python script execution failed.' });
        }
      } else {
        console.log('[IPC Main] PythonShell execution finished successfully (code, signal):', code, signal);
        // If it ended successfully without a 'done' message (e.g. script just exited), ensure renderer is notified.
        if (currentPythonShellInstance) { // If null, 'done' message handled it.
             event.sender.send('llm:stream-done', { success: true, message: "Stream ended without explicit done message."});
        }
      }
      currentPythonShellInstance = null; // Ensure cleared on any termination
    });
  });

  // --- IPC Handler to Stop LLM Generation ---
  ipcMain.handle('stop-llm-generation', async () => {
    console.log('[IPC Main] Received stop-llm-generation request.');
    if (currentPythonShellInstance && currentPythonShellInstance.childProcess && !currentPythonShellInstance.childProcess.killed) {
      try {
        console.log('[IPC Main] Attempting to send SIGUSR1 to Python process.');
        const success = currentPythonShellInstance.childProcess.kill('SIGUSR1');
        if (success) {
          console.log('[IPC Main] Sent SIGUSR1 to Python process.');
          return { success: true, message: 'Stop signal sent to LLM generation process.' };
        } else {
          // This case might be rare, as kill usually returns true if process exists,
          // or throws if signal is invalid. But good to have a branch.
          console.warn('[IPC Main] SIGUSR1 signal was not sent successfully (kill command returned false).');
          return { success: false, error: 'Failed to send stop signal', details: 'The operation to send the signal returned false.' };
        }
      } catch (err) {
        console.error('[IPC Main] Error sending SIGUSR1:', err);
        // Check if the error is because the process is already dead
        if (err.code === 'ESRCH') { // Error No Such Process
            console.warn('[IPC Main] Attempted to signal a process that was already dead or gone.');
            currentPythonShellInstance = null; // Ensure it's cleared
            return { success: false, error: 'Process already terminated', details: 'The LLM process was not running or already finished.' };
        }
        return { success: false, error: 'Failed to send stop signal', details: err.message };
      }
    } else {
      console.warn('[IPC Main] No active LLM generation process to stop or process already terminated.');
      return { success: false, error: 'No active generation process', details: 'There is no LLM response currently streaming or the process has already ended.' };
    }
  });
  // --- End Stop LLM Generation Handler ---

  // --- LLM Configuration IPC Handler ---
  ipcMain.handle('get-llm-config', async () => {
    try {
      // __dirname is jarules_electron_vue_ui/
      // config/ is at the project root, so one level up from __dirname
      const configPath = path.join(__dirname, '../config/llm_config.yaml');
      const data = await fs.readFile(configPath, 'utf8');
      return data;
    } catch (error) {
      console.error('Failed to read llm_config.yaml:', error);
      // Return null or an error object, depending on how the renderer should handle it
      // For consistency with other handlers that might return data or error states:
      return { error: true, message: 'Failed to read LLM configuration.', details: error.message };
    }
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

  // --- Diagnostics IPC Handler ---
  ipcMain.handle('run-all-diagnostics', async (event) => {
    console.log('[IPC Main] Received run-all-diagnostics request.');
    const diagnosticScripts = [
      'check_python_environment_wrapper.py',
      'check_config_files_wrapper.py',
      'check_llm_connectivity_wrapper.py'
    ];
    const allResults = [];
    const defaultTimestamp = () => new Date().toISOString();

    for (const scriptName of diagnosticScripts) {
      try {
        const scriptOutput = await runPythonScript(scriptName);

        // Check if runPythonScript itself returned an error structure
        if (scriptOutput && scriptOutput.error === true) {
          console.error(`[IPC Main] Error from runPythonScript for ${scriptName}:`, scriptOutput.message);
          allResults.push({
            id: `script-runner-error-${scriptName.replace('.py', '')}`,
            name: scriptName,
            status: 'error',
            message: scriptOutput.message || `Failed to execute script ${scriptName} via runner.`,
            details: scriptOutput.details || 'No details from script runner.',
            timestamp: defaultTimestamp()
          });
          continue; // Move to the next script
        }

        // Validate scriptOutput structure (Python scripts should return valid JSON parsable by python-shell)
        if (scriptOutput === null || typeof scriptOutput === 'undefined') {
            console.error(`[IPC Main] No valid output from ${scriptName}. Received:`, scriptOutput);
            allResults.push({
                id: `script-output-error-${scriptName.replace('.py', '')}`,
                name: scriptName,
                status: 'error',
                message: `Script ${scriptName} returned null or undefined output.`,
                details: 'The script did not produce valid JSON output as expected.',
                timestamp: defaultTimestamp()
            });
            continue;
        }


        const processSingleResult = (singleResult) => {
          // Ensure basic structure and timestamp for each result from Python
          if (!singleResult || typeof singleResult !== 'object') {
            // This case should ideally be caught earlier if scriptOutput itself is not an object/array
            return {
              id: `malformed-result-${scriptName.replace('.py', '')}`,
              name: scriptName,
              status: 'error',
              message: 'Malformed result object received from script.',
              details: { originalOutput: singleResult },
              timestamp: defaultTimestamp()
            };
          }
          return {
            id: singleResult.id || `unknown-id-${scriptName.replace('.py', '')}`,
            name: singleResult.name || scriptName,
            status: singleResult.status || 'error',
            message: singleResult.message || 'No message provided.',
            details: singleResult.details || {},
            timestamp: singleResult.timestamp || defaultTimestamp()
          };
        };

        if (scriptName === 'check_config_files_wrapper.py') {
          if (Array.isArray(scriptOutput)) {
            scriptOutput.forEach(item => allResults.push(processSingleResult(item)));
          } else {
            console.error(`[IPC Main] Expected array from ${scriptName}, got:`, typeof scriptOutput);
            allResults.push(processSingleResult({ // Create a single error entry for the script itself
                id: `script-type-error-${scriptName.replace('.py', '')}`,
                name: scriptName,
                status: 'error',
                message: `Expected an array from ${scriptName} but received ${typeof scriptOutput}.`,
                details: { receivedOutput: scriptOutput },
                timestamp: defaultTimestamp()
            }));
          }
        } else {
          allResults.push(processSingleResult(scriptOutput));
        }

      } catch (error) { // Catch errors from runPythonScript call itself or unexpected issues
        console.error(`[IPC Main] Critical error executing ${scriptName}:`, error);
        allResults.push({
          id: `ipc-script-execution-error-${scriptName.replace('.py', '')}`,
          name: scriptName,
          status: 'error',
          message: `Failed to execute diagnostic script ${scriptName}.`,
          details: { error: error.message, stack: error.stack },
          timestamp: defaultTimestamp()
        });
      }
    }
    console.log('[IPC Main] Diagnostics complete. Results:', allResults.length);
    return allResults;
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
