const socket = io();
let currentChatId = sessionStorage.getItem('currentChatId') || null; 
const currentUser = "{{ session['user']['email'] if session.get('user') else '' }}";

function appendMessage(user, message, chatRoom) {
    if (chatRoom !== currentChatId) return;

    const chatWindow = document.getElementById("chatWindow");
    const messageDiv = document.createElement('div');

    console.log("Current user email:", currentUser);
    console.log("Message sender email:", user.email);
    const cssClass = user.email === currentUser ? 'user-message' : 'other-message';
    messageDiv.className = `message ${cssClass}`;
    messageDiv.innerHTML = `<strong>${user.name}</strong>: ${message}`;

    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

socket.on("receive_message", data => { 
    if (data.room === currentChatId) {
        appendMessage(data.user, data.message, data.room);
    }
});

function loadChatSessions() {
    fetch('/chat_sessions')
        .then(response => response.json())
        .then(data => {
            const list = document.getElementById('chatList');
            list.innerHTML = '';

            if (data.length === 0) {
                list.innerHTML = '<li>No chats yet. Start a new one!</li>';
                return;
            }

            data.forEach((chat, index) => {
                let li = document.createElement('li');
                li.textContent = new Date(chat.created_at).toLocaleString();
                li.dataset.chatId = chat.chat_id;

                li.onclick = () => openChat(chat.chat_id);

                if (chat.chat_id === currentChatId) {
                    li.classList.add('active');
                }
                list.appendChild(li);

                if (index === 0 && !currentChatId) {
                    openChat(chat.chat_id);
                }
            });
        })
        .catch(error => console.error('Error loading chat sessions:', error));
}

function openChat(chatId) {
    currentChatId = chatId;
    sessionStorage.setItem('currentChatId', currentChatId); 
    socket.emit("join", { room: chatId });

    fetch(`/chat/${chatId}`)
        .then(response => response.json())
        .then(messages => {
            const chatWindow = document.getElementById('chatWindow');
            chatWindow.innerHTML = '';
            const title = document.getElementById('chatTitle');
            const selected = document.querySelector(`[data-chat-id="${chatId}"]`);
            title.textContent = selected ? selected.textContent : "Chat";

            messages.forEach(msg => {
                const div = document.createElement('div');
                const cssClass = msg.user === currentUser ? 'user-message' : 'other-message';
                div.className = `message ${cssClass}`;
                div.innerHTML = `<strong>${msg.user}</strong>: ${msg.message}`;
                chatWindow.appendChild(div);
            });
            chatWindow.scrollTop = chatWindow.scrollHeight;
        });

    highlightSelectedChat(chatId);
}

function highlightSelectedChat(chatId) {
    const items = document.querySelectorAll('#chatList li');
    items.forEach(item => {
        item.classList.toggle('active', item.dataset.chatId === chatId.toString());
    });
}

let isCreatingChat = false;

function startNewChat() {
    if (isCreatingChat) return;
    isCreatingChat = true;

    fetch('/new_chat', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            isCreatingChat = false;

            if (data.session_id) {
                currentChatId = data.session_id;
                sessionStorage.setItem('currentChatId', currentChatId); 
                socket.emit("join", { room: currentChatId });
                loadChatSessions();
                document.getElementById('chatWindow').innerHTML = '';
            } else {
                alert('Failed to start a new chat');
            }
        })
        .catch(error => {
            isCreatingChat = false;
            console.error('Error creating new chat:', error);
        });
}

function sendMessage(event) {
    event.preventDefault();
    const text = document.getElementById('messageInput').value.trim();

    if (!currentChatId) {
        alert("Please select a chat session before sending a message.");
        return;
    }
    if (!text) return;
    console.log("Sending message to room:", currentChatId);

    socket.emit("send_message", {
        message: text,
        room: currentChatId,
        target: "GPT"
    });

    document.getElementById('messageInput').value = '';
}

window.onload = loadChatSessions;
