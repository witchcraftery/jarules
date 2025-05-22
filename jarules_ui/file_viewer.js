// file_viewer.js

/**
 * Displays the content of a file with syntax highlighting in the File Viewer panel.
 * @param {string} fileName - The name of the file (currently unused, but good for context).
 * @param {string} fileContent - The content of the file.
 * @param {string} language - The programming language of the file for syntax highlighting.
 */
function displayFileContent(fileName, fileContent, language) {
    const fileViewerPanel = document.getElementById('fileViewerPanel');
    if (!fileViewerPanel) {
        console.error("File viewer panel element not found!");
        return;
    }

    // Clear previous content
    fileViewerPanel.innerHTML = '';

    // Create <pre> and <code> elements
    const preElement = document.createElement('pre');
    const codeElement = document.createElement('code');

    // Set the language class for Prism.js
    if (language) {
        codeElement.className = 'language-' + language;
    } else {
        // Default to 'plain' or 'markup' if language is not specified,
        // or let Prism autodetect if that's the desired behavior (though explicit is better).
        codeElement.className = 'language-plain'; // Fallback
        console.warn(`Language not specified for file: ${fileName}. Defaulting to plain text.`);
    }

    // Set the file content
    codeElement.textContent = fileContent;

    // Append <code> to <pre>, then <pre> to the panel
    preElement.appendChild(codeElement);
    fileViewerPanel.appendChild(preElement);

    // Call Prism to highlight the new element
    // Ensure Prism and highlightElement are available
    if (typeof Prism !== 'undefined' && Prism.highlightElement) {
        Prism.highlightElement(codeElement);
    } else {
        console.error("Prism.js or Prism.highlightElement is not available.");
        // Fallback: display raw text if Prism is not loaded
        // This is already handled by setting textContent, but good to be aware.
    }
}

// Make the function globally accessible if file_explorer.js needs to call it directly.
// (Alternatively, use a more structured approach like event emitters or modules if this were a larger app)
window.JaRulesApp = window.JaRulesApp || {};
window.JaRulesApp.displayFileContent = displayFileContent;

console.log("file_viewer.js loaded and displayFileContent function is ready.");
