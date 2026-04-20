async function sendMessage() {
    const inputField = document.getElementById('chatInput');
    const message = inputField.value.trim();
    if (!message) return; // Don't send empty messages

    const chatMessages = document.getElementById('chatMessages');

    // 1. Append the User's Message to the chat window
    const userDiv = document.createElement('div');
    userDiv.className = 'mb-2 text-end';
    userDiv.innerHTML = `<span class="bg-primary text-white p-2 border rounded d-inline-block shadow-sm">${message}</span>`;
    chatMessages.appendChild(userDiv);
    
    // Clear the input box
    inputField.value = '';
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 2. Send the message to your Flask Backend (/api/chat)
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();

        // 3. Append the Bot's Response
        const botDiv = document.createElement('div');
        botDiv.className = 'mb-2 text-start mt-2';
        botDiv.innerHTML = `<span class="bg-white text-dark p-2 border rounded d-inline-block shadow-sm"><i class="bi bi-robot me-1"></i> ${data.reply}</span>`;
        chatMessages.appendChild(botDiv);

        // Scroll to the bottom again
        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (error) {
        console.error('Error connecting to Muni Assist:', error);
    }
}

// Allow the user to press the "Enter" key on their keyboard to send a message
document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById('chatInput');
    if(chatInput) {
        chatInput.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                sendMessage();
            }
        });
    }
});