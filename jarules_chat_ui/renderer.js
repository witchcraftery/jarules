document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages-container'); // Get reference to messages container

    if (!messagesContainer) {
        console.error('Error: Messages container not found.');
        // Optionally, disable UI or inform user if core components are missing
        return; 
    }

    if (sendButton && messageInput) {
        sendButton.addEventListener('click', () => {
            const message = messageInput.value.trim();
            if (message) {
                if (window.api && typeof window.api.sendMessageToMain === 'function') {
                    window.api.sendMessageToMain(message);
                    messageInput.value = ''; // Clear the input field
                } else {
                    console.error('Error: sendMessageToMain function is not available on window.api.');
                }
            }
        });

        messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendButton.click();
            }
        });
    } else {
        console.error('Error: Message input or send button not found.');
    }

    // Listen for messages from the main process
    if (window.api && typeof window.api.receiveMessageFromMain === 'function') {
        window.api.receiveMessageFromMain((message) => {
            const messageElement = document.createElement('div');
            messageElement.textContent = message;
            // Optional: Add a class for styling, e.g., messageElement.classList.add('received-message');
            messagesContainer.appendChild(messageElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight; // Scroll to bottom
        });
    } else {
        console.error('Error: receiveMessageFromMain function is not available on window.api.');
    }
});
