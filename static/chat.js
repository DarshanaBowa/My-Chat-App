let socket = io();
let currentRoom = "General";
let username = document.getElementById('username').textContent;
let roomMessages = {};

// Socket Listeners
socket.on('connect', () => {
    joinRoom('General');
});

socket.on('message', (data) => {
    addMessage(data.username, data.msg, data.username === username ? 'own' : 'other');
});

socket.on('private_message', (data) => {
    addMessage(data.from, `[Private] ${data.msg}`, 'private');
});

socket.on('status', (data) => {
    addMessage('System', data.msg, 'system');
});

socket.on('active_users', (data) => {
    const userList = document.getElementById('active-users');
    userList.innerHTML = data.users.map(user =>
        `<div class="user-item" onclick="insertPrivateMessage('${user}')">${user} ${user === username ? '(you)' : ''}</div>`
    ).join('');
});

// Add message to chat
function addMessage(sender, message, type) {
    if (!roomMessages[currentRoom]) {
        roomMessages[currentRoom] = [];
    }

    roomMessages[currentRoom].push({ sender, message, type });

    const chat = document.getElementById('chat');
    const messageDiv = document.createElement('div');

    messageDiv.className = `message ${type}`;
    messageDiv.textContent = `${sender}: ${message}`;

    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;
}

// Send message
function sendMessage() {
    const input = document.getElementById('message');
    const message = input.value.trim();

    if (!message) return;

    if (message.startsWith('@')) {
        const [target, ...msgParts] = message.substring(1).split(' ');
        const privateMsg = msgParts.join(' ');

        if (privateMsg) {
            socket.emit('handle_messages', {
                msg: privateMsg,
                type: 'private',
                target: target
            });
        }
    } else {
        socket.emit('handle_messages', {
            msg: message,
            room: currentRoom
        });
    }

    input.value = '';
    input.focus();
}

// Join room
function joinRoom(room) {
    socket.emit('leave', { room: currentRoom });
    currentRoom = room;
    socket.emit('join', { room });

    const chat = document.getElementById('chat');
    chat.innerHTML = '';

    if (roomMessages[room]) {
        roomMessages[room].forEach(msg => {
            addMessage(msg.sender, msg.message, msg.type);
        });
    }

    // Update active room UI
    document.querySelectorAll('.room-item').forEach(item => {
        item.classList.remove('active-room');
        if (item.textContent.trim() === room) {
            item.classList.add('active-room');
        }
    });
}

// Insert private message
function insertPrivateMessage(user) {
    const input = document.getElementById('message');
    input.value = `@${user} `;
    input.focus();
}

// Handle Enter key
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}
