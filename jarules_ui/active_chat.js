document.addEventListener('DOMContentLoaded', () => {
    const messageDisplayArea = document.getElementById('messageDisplayArea');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');

    if (!messageDisplayArea || !chatInput || !sendButton) {
        console.error("One or more active chat DOM elements not found!");
        return;
    }

    function addMessageToDisplay(speaker, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message'); // General class for all messages

        if (speaker === "User") {
            messageDiv.classList.add('user-message');
        } else {
            messageDiv.classList.add('jarules-message');
        }

        const speakerSpan = document.createElement('span');
        speakerSpan.classList.add('speaker');
        speakerSpan.textContent = speaker + ":";
        
        const textSpan = document.createElement('span');
        textSpan.classList.add('message-text');
        textSpan.textContent = text;

        messageDiv.appendChild(speakerSpan);
        messageDiv.appendChild(textSpan);
        messageDisplayArea.appendChild(messageDiv);

        // Scroll to the bottom
        messageDisplayArea.scrollTop = messageDisplayArea.scrollHeight;
    }

    function handleSendMessage() {
        const text = chatInput.value.trim();
        if (text !== "") {
            addMessageToDisplay("User", text);
            chatInput.value = ""; // Clear input

            // Simulate JaRules Reply
            setTimeout(() => {
                // For a better UX, you might want to show a "JaRules is typing..." indicator here
                // and then replace it, rather than just adding another message.
                // However, for simplicity, we'll just add messages.
                // Let's add a "Thinking..." first for a brief moment.
                const thinkingMessage = addMessageToDisplay("JaRules", "Thinking..."); 
                // This ^ line is a bit problematic if addMessageToDisplay doesn't return the element.
                // For now, we'll just append. A more complex UX would need to store and replace.

                setTimeout(() => {
                    // Replace "Thinking..." or add a new message.
                    // For this version, we'll just add a new one.
                    addMessageToDisplay("JaRules", "That's an interesting point! Let me look into that for you.");
                }, 1000); // Delay for the actual reply
            }, 500); // Initial delay for "Thinking..."
        }
    }

    sendButton.addEventListener('click', handleSendMessage);

    chatInput.addEventListener('keydown', (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault(); // Prevent default Enter behavior (like newline in a textarea)
            handleSendMessage();
        }
    });

    // Initial Welcome Message
    addMessageToDisplay("JaRules", "Hello! I'm JaRules. How can I assist you today?");
    
    console.log("active_chat.js initialized and event listeners added.");
});
