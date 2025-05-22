document.addEventListener('DOMContentLoaded', () => {
    const chatHistoryData = [
        { speaker: "User", text: "Can you help me find a bug in this Python code?" },
        { speaker: "JaRules", text: "Sure, I can try. Please show me the code." },
        { speaker: "User", text: "Okay, here it is..." },
        { speaker: "JaRules", text: "Thanks! Looking at it now." },
        { speaker: "User", text: "Any ideas?" },
        { speaker: "JaRules", text: "I see a potential issue on line 42 regarding variable scope. Let's examine that." }
    ];

    const chatHistoryPanel = document.getElementById('chatHistoryPanel');

    if (!chatHistoryPanel) {
        console.error("Chat history panel element not found!");
        return;
    }

    // Clear any existing placeholder text
    chatHistoryPanel.innerHTML = ''; 

    function renderChatHistory(panelElement, historyData) {
        historyData.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('chat-message');
            
            if (message.speaker === "User") {
                messageDiv.classList.add('user-message');
            } else {
                messageDiv.classList.add('jarules-message');
            }

            const speakerSpan = document.createElement('span');
            speakerSpan.classList.add('speaker');
            speakerSpan.textContent = message.speaker + ":";
            
            const textSpan = document.createElement('span');
            textSpan.classList.add('message-text');
            textSpan.textContent = message.text;

            messageDiv.appendChild(speakerSpan);
            messageDiv.appendChild(textSpan);
            panelElement.appendChild(messageDiv);
        });
    }

    renderChatHistory(chatHistoryPanel, chatHistoryData);
    console.log("Chat history rendered.");
});
