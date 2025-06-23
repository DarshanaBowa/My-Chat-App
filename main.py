# Imports
import os
import random
import logging
from datetime import datetime
from typing import Dict

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(24)
    DEBUG = os.environ.get(
        "FLASK_DEBUG", "False").lower() in ('true', "1", "t")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    CHAT_ROOMS = [
        "My A/L Batch",
        "Diploma friends",
        "Degree Batch",
        "My Office Friends"
    ]


# Flask app setup
app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# SocketIO setup
socketio = SocketIO(
    app,
    cors_allowed_origins=app.config["CORS_ORIGINS"],
    logger=True,
    engineio_logger=True
)

# Track active users
active_users: Dict[str, dict] = {}

# Generate guest usernames


def generate_guest_username() -> str:
    timestamp = datetime.now().strftime('%H%M')
    return f"Guest{timestamp}{random.randint(1000, 9999)}"

# Home route


@app.route("/")
def index():
    if 'username' not in session:
        session['username'] = generate_guest_username()
        logger.info(f"New user session made: {session['username']}")

    return render_template(
        'index.html',
        username=session['username'],
        rooms=app.config["CHAT_ROOMS"]
    )

# SocketIO: connect


@socketio.event
def connect():
    try:
        if 'username' not in session:
            session['username'] = generate_guest_username()

        active_users[request.sid] = {
            'username': session['username'],
            'connected_at': datetime.now().isoformat()
        }

        emit('active_users', {
            'users': [user['username'] for user in active_users.values()]
        }, broadcast=True)

        logger.info(f"User connected: {session['username']}")

    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        return False

# SocketIO: disconnect


@socketio.event
def disconnect():
    try:
        if request.sid in active_users:
            username = active_users[request.sid]['username']
            del active_users[request.sid]

            emit('active_users', {
                'users': [user['username'] for user in active_users.values()]
            }, broadcast=True)

            logger.info(f"User disconnected: {username}")

    except Exception as e:
        logger.error(f"Disconnection error: {str(e)}")

# Join room


@socketio.on('join')
def on_join(data: dict):
    try:
        username = session['username']
        room = data['room']

        if room not in app.config["CHAT_ROOMS"]:
            logger.warning("Invalid room")
            return

        join_room(room)
        active_users[request.sid]['room'] = room

        emit('status', {
            'msg': f"{username} has joined the room!",
            'type': 'join',
            'timestamp': datetime.now().isoformat()
        }, room=room)

        logger.info(f"{username} joined {room}")

    except Exception as e:
        logger.error(str(e))

# Leave room


@socketio.on('leave')
def on_leave(data: dict):
    try:
        username = session['username']
        room = data['room']

        leave_room(room)
        if request.sid in active_users:
            active_users[request.sid].pop('room', None)

        emit('status', {
            'msg': f"{username} has left the room!",
            'type': 'leave',
            'timestamp': datetime.now().isoformat()
        }, room=room)

        logger.info(f"{username} left {room}")

    except Exception as e:
        logger.error(str(e))

# Handle messages


@socketio.event
def handle_messages(data: dict):
    try:
        username = session['username']
        room = data.get('room', "General")
        msg_type = data.get('type', 'message')
        message = data.get('msg', "").strip()

        if not message:
            return

        timestamp = datetime.now().isoformat()

        if msg_type == 'private':
            target_user = data.get('target')
            if not target_user:
                return

            for sid, user_data in active_users.items():
                if user_data['username'] == target_user:
                    emit('private_message', {
                        'msg': message,
                        'from': username,
                        'to': target_user,
                        'timestamp': timestamp
                    }, room=sid)
                    return
        else:
            if room not in app.config["CHAT_ROOMS"]:
                logger.warning(f"Invalid room: {room}")
                return

            emit('message', {
                'msg': message,
                'username': username,
                'room': room,
                'timestamp': timestamp
            }, room=room)

    except Exception as e:
        logger.error(str(e))


# Run the app
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=app.config["DEBUG"],
        use_reloader=app.config["DEBUG"]
    )
