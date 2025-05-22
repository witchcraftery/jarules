document.addEventListener('DOMContentLoaded', () => {
    const fileSystemData = [
        { name: 'README.md', type: 'file', language: 'markdown', content: '# Project Title\nThis is the README.\n\n- Point 1\n- Point 2' },
        { name: 'src', type: 'directory', children: [
            { name: 'app.js', type: 'file', language: 'javascript', content: 'console.log("Hello from app.js");\nfunction greet(name) {\n  return `Hello, ${name}!`;\n}' },
            { name: 'styles.css', type: 'file', language: 'css', content: 'body {\n  font-family: sans-serif;\n  background-color: #f0f0f0;\n}\n.header {\n color: blue;\n}' },
            { name: 'components', type: 'directory', children: [
                { name: 'Button.js', type: 'file', language: 'javascript', content: '// Button component\nexport default function Button() {\n  return <button>Click Me</button>;\n}' }
            ]}
        ]},
        { name: 'public', type: 'directory', children: [
            { name: 'index.html', type: 'file', language: 'markup', content: '<!DOCTYPE html>\n<html>\n  <head><title>Test</title></head>\n  <body><h1>Hello</h1></body>\n</html>' }
        ]},
        { name: 'package.json', type: 'file', language: 'json', content: '{ "name": "my-project", "version": "1.0.0" }' },
        { name: 'example.py', type: 'file', language: 'python', content: 'def greet(name):\n    print(f"Hello, {name}!")\n\ngreet("World")' }
    ];

    const fileExplorerPanel = document.getElementById('fileExplorerPanel');
    // const fileViewerPanel = document.getElementById('fileViewerPanel'); // Not needed here, file_viewer.js handles it

    if (!fileExplorerPanel) {
        console.error("File explorer panel element not found!");
        return;
    }
    // Clear any existing placeholder text
    fileExplorerPanel.innerHTML = ''; 

    function renderFileSystem(parentElement, data, level = 0) {
        const ul = document.createElement('ul');
        ul.style.paddingLeft = `${level * 20}px`; // Indentation for nesting

        data.forEach(item => {
            const li = document.createElement('li');
            li.textContent = (item.type === 'directory' ? '📁 ' : '📄 ') + item.name;
            li.className = item.type === 'directory' ? 'dir-item' : 'file-item';
            li.style.cursor = 'pointer';

            if (item.type === 'file') {
                li.addEventListener('click', (event) => {
                    event.stopPropagation(); // Prevent event from bubbling to parent directory click
                    console.log("File clicked:", item.name, "Language:", item.language);
                    if (window.JaRulesApp && window.JaRulesApp.displayFileContent) {
                        window.JaRulesApp.displayFileContent(item.name, item.content, item.language);
                    } else {
                        console.error("displayFileContent function is not available.");
                        // Fallback to simple display if Prism highlighting isn't set up via file_viewer.js
                        const fileViewerPanel = document.getElementById('fileViewerPanel');
                        if (fileViewerPanel) {
                           fileViewerPanel.innerHTML = `<pre>${item.content || 'File content not available.'}</pre>`;
                        }
                    }
                });
            } else if (item.type === 'directory') {
                const childrenContainer = document.createElement('div');
                childrenContainer.className = 'hidden'; // Initially hidden
                li.appendChild(childrenContainer);

                li.addEventListener('click', () => {
                    const isHidden = childrenContainer.classList.toggle('hidden');
                    if (!isHidden && !childrenContainer.hasChildNodes() && item.children) {
                        // If opening and children haven't been rendered yet
                        renderFileSystem(childrenContainer, item.children, level + 1);
                    }
                    // Toggle icon (optional)
                    // Update text content to reflect new icon and keep name
                    const currentName = li.childNodes[0].nodeValue.substring(2); // Assuming icon is 2 chars
                    li.childNodes[0].nodeValue = (isHidden ? '📁 ' : '📂 ') + currentName; 
                });
            }
            ul.appendChild(li);
        });
        parentElement.appendChild(ul);
    }

    renderFileSystem(fileExplorerPanel, fileSystemData);
    console.log("File explorer rendered.");
});
