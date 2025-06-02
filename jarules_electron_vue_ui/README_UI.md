# JaRules Electron Vue.js UI Module

This directory contains the source code for the Electron-based desktop user interface for JaRules, built using Vue.js and Vite.

## Development Setup

1.  **Navigate to this directory:**
    ```bash
    cd jarules_electron_vue_ui
    ```
2.  **Install dependencies** (if you haven't already):
    ```bash
    npm install
    ```

## Running the Application

### Development Mode
To run the application in development mode, which uses Vite's hot-reloading and opens Electron's DevTools:
```bash
npm run dev
```
This command concurrently starts the Vite development server and launches the Electron application. The Electron app will load content from `http://localhost:5173` (the default Vite port).

### Production Mode
To simulate a production environment:
1.  Build the Vue.js application:
    ```bash
    npm run build:vite
    ```
    This will create a `dist/` folder with the compiled static assets.
2.  Run the Electron application:
    ```bash
    npm run start:prod 
    ```
    Alternatively, after building, you can simply run `electron .` and it will load from the `dist/` folder as configured in `main.js`.

## Project Structure (Key Files)

- `main.js`: The main process script for Electron. Handles window creation and app lifecycle.
- `preload.js`: Electron preload script for context bridging.
- `index.html`: The main HTML file that hosts the Vue.js application.
- `vite.config.js`: Configuration for the Vite build tool.
- `src/`: Contains the Vue.js application source code.
  - `src/main.js`: The entry point for the Vue.js application.
  - `src/App.vue`: The root Vue component.

## Detailed Development Plan

The detailed multi-phase development plan, including future features and architectural discussions for this UI, is maintained in the main project's `IMPLEMENTATION_GUIDE.md` file in the root directory.
