# Archived Plan Section for Agent G - IPC General Setup
## From Main Task: TASKID-20231027-121000-AGG-IPCIF - Implement IPC Interface for Parallel Tasks (Phase 2.5) - Revised for Solution Previews & Zipping

---
**I. General Setup and Conventions**

1.  **`preload.js` Structure (`jarules_electron_vue_ui/public/preload.js`):**
    *   All new IPC functions exposed under `window.api` via `contextBridge.exposeInMainWorld('api', { ... });`.
2.  **`main.js` Structure (`jarules_chat_ui/main.js`):**
    *   IPC handlers (`ipcMain.handle`) registered.
    *   Imports and uses functions from `parallelTaskManager.js`.
    *   Consistent error handling: `try...catch`, returning `{ success: false, error: message, details: error.stack }`.
3.  **Logging:** Basic `console.log` or dedicated logger for IPC calls and responses.
4.  **Payloads:** Adhere to structures in `development-status.md` and `IMPLEMENTATION_GUIDE.md`.
---
