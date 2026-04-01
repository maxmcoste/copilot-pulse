// Copilot Pulse Dashboard — Client-side JavaScript

// WebSocket Chat
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');

let ws = null;

function initChat() {
    if (!chatInput) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'response') {
            addMessage(data.message, 'bot');
        } else if (data.type === 'status') {
            showTyping(data.message);
        } else if (data.type === 'error') {
            addMessage(`Errore: ${data.message}`, 'bot');
        }
    };

    ws.onclose = function() {
        addMessage('Connessione persa. Ricarica la pagina.', 'bot');
    };

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || !ws) return;

    addMessage(text, 'user');
    ws.send(JSON.stringify({ question: text }));
    chatInput.value = '';
}

function addMessage(text, type) {
    removeTyping();
    const div = document.createElement('div');
    div.className = `message ${type}-message`;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping(text) {
    removeTyping();
    const div = document.createElement('div');
    div.className = 'message bot-message typing';
    div.textContent = text || 'Analizzo...';
    div.id = 'typingIndicator';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

// Quick Ask (Dashboard)
async function quickAsk(question) {
    const answerDiv = document.getElementById('quickAnswer');
    if (!answerDiv) return;

    answerDiv.classList.add('visible');
    answerDiv.textContent = 'Analizzo...';

    try {
        // Use WebSocket if available, otherwise fall back to HTTP
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ question }));
        } else {
            answerDiv.textContent = 'Apri la sezione Chat per fare domande.';
        }
    } catch (e) {
        answerDiv.textContent = `Errore: ${e.message}`;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initChat();
});
