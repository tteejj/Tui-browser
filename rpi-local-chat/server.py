"""
RPi Local Chat Server - Lightweight chat application for Raspberry Pi Zero 2 W
"""
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
import time
import re
from datetime import datetime
from threading import Lock
import mimetypes
from PIL import Image
import requests
from io import BytesIO

import database as db
import auth

app = Flask(__name__)
app.config['SECRET_KEY'] = auth.generate_session_token()
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# SSE clients management
sse_clients = []
sse_lock = Lock()

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*?v=([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_metadata(video_id):
    """Get YouTube video metadata using oEmbed API"""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', 'YouTube Video'),
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                'author': data.get('author_name', 'Unknown')
            }
    except Exception as e:
        print(f"Error fetching YouTube metadata: {e}")
    return None

def resize_image(image_path, max_size=(1200, 1200)):
    """Resize image to reduce file size"""
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Resize if needed
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save with optimization
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        print(f"Error resizing image: {e}")

def broadcast_message(message_data):
    """Broadcast message to all SSE clients"""
    with sse_lock:
        dead_clients = []
        for client in sse_clients:
            try:
                client.put(message_data)
            except:
                dead_clients.append(client)

        # Remove dead clients
        for client in dead_clients:
            sse_clients.remove(client)

@app.route('/')
def index():
    """Serve the main chat page"""
    return render_template('index.html')

@app.route('/api/auth/verify-pin', methods=['POST'])
def verify_pin():
    """Verify PIN and create session"""
    data = request.json
    pin = data.get('pin', '')
    username = data.get('username', '').strip()

    if not username or len(username) < 2:
        return jsonify({'error': 'Username must be at least 2 characters'}), 400

    if not auth.verify_pin(pin):
        return jsonify({'error': 'Invalid PIN'}), 401

    # Check if username already exists
    existing_user = db.get_user_by_username(username)
    if existing_user:
        return jsonify({'error': 'Username already taken'}), 400

    # Create new user
    session_token = auth.generate_session_token()
    user_id = db.create_user(username, session_token)

    return jsonify({
        'success': True,
        'session_token': session_token,
        'user_id': user_id,
        'username': username
    })

@app.route('/api/auth/verify-session', methods=['POST'])
def verify_session():
    """Verify existing session token"""
    data = request.json
    session_token = data.get('session_token', '')

    user = db.get_user_by_token(session_token)
    if not user:
        return jsonify({'error': 'Invalid session'}), 401

    db.update_user_last_seen(user['id'])

    return jsonify({
        'success': True,
        'user_id': user['id'],
        'username': user['username']
    })

@app.route('/api/channels', methods=['GET'])
def get_channels():
    """Get all channels"""
    session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

    user = db.get_user_by_token(session_token)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    channels = db.get_all_channels()
    return jsonify([{
        'id': ch['id'],
        'name': ch['name'],
        'description': ch['description']
    } for ch in channels])

@app.route('/api/messages/<int:channel_id>', methods=['GET'])
def get_messages(channel_id):
    """Get messages for a channel"""
    session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

    user = db.get_user_by_token(session_token)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Get messages with size limit (100MB of images)
    messages = db.get_messages_with_size_limit(channel_id, size_limit_mb=100)

    result = []
    for msg in messages:
        message_obj = {
            'id': msg['id'],
            'channel_id': msg['channel_id'],
            'username': msg['username'],
            'content': msg['content'],
            'message_type': msg['message_type'],
            'created_at': msg['created_at']
        }

        # Add attachment info if present
        if msg['file_path']:
            message_obj['attachment'] = {
                'filename': msg['filename'],
                'file_path': msg['file_path'],
                'mime_type': msg['mime_type']
            }

        # Parse YouTube metadata if it's a youtube message
        if msg['message_type'] == 'youtube':
            try:
                youtube_data = json.loads(msg['content'])
                message_obj['youtube'] = youtube_data
            except:
                pass

        result.append(message_obj)

    return jsonify(result)

@app.route('/api/messages', methods=['POST'])
def send_message():
    """Send a new message"""
    session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

    user = db.get_user_by_token(session_token)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    channel_id = data.get('channel_id')
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Content cannot be empty'}), 400

    # Check if content contains YouTube link
    youtube_id = extract_youtube_id(content)
    message_type = 'text'
    stored_content = content

    if youtube_id:
        message_type = 'youtube'
        metadata = get_youtube_metadata(youtube_id)
        if metadata:
            stored_content = json.dumps({
                'video_id': youtube_id,
                'url': f"https://www.youtube.com/watch?v={youtube_id}",
                'title': metadata['title'],
                'thumbnail': metadata['thumbnail'],
                'author': metadata['author']
            })
        else:
            stored_content = json.dumps({
                'video_id': youtube_id,
                'url': f"https://www.youtube.com/watch?v={youtube_id}",
                'title': 'YouTube Video',
                'thumbnail': f"https://img.youtube.com/vi/{youtube_id}/mqdefault.jpg",
                'author': 'Unknown'
            })

    # Create message
    message_id = db.create_message(channel_id, user['id'], stored_content, message_type)

    # Prepare broadcast data
    message_data = {
        'id': message_id,
        'channel_id': channel_id,
        'username': user['username'],
        'content': stored_content,
        'message_type': message_type,
        'created_at': datetime.now().isoformat()
    }

    if message_type == 'youtube':
        message_data['youtube'] = json.loads(stored_content)

    # Broadcast to SSE clients
    broadcast_message(message_data)

    return jsonify(message_data), 201

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload an image file"""
    session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

    user = db.get_user_by_token(session_token)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    channel_id = request.form.get('channel_id')
    caption = request.form.get('caption', '').strip()

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, GIF, WEBP'}), 400

    # Generate secure filename
    filename = secure_filename(file.filename)
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Save file
    file.save(file_path)

    # Get file size before resizing
    file_size = os.path.getsize(file_path)

    # Resize image to save space
    resize_image(file_path)

    # Update file size after resizing
    file_size = os.path.getsize(file_path)

    # Get mime type
    mime_type = mimetypes.guess_type(file_path)[0] or 'image/jpeg'

    # Create message
    message_content = caption if caption else f"Uploaded {file.filename}"
    message_id = db.create_message(channel_id, user['id'], message_content, 'image')

    # Create attachment record
    relative_path = f"/static/uploads/{filename}"
    db.create_attachment(message_id, file.filename, relative_path, file_size, mime_type)

    # Prepare broadcast data
    message_data = {
        'id': message_id,
        'channel_id': int(channel_id),
        'username': user['username'],
        'content': message_content,
        'message_type': 'image',
        'created_at': datetime.now().isoformat(),
        'attachment': {
            'filename': file.filename,
            'file_path': relative_path,
            'mime_type': mime_type
        }
    }

    # Broadcast to SSE clients
    broadcast_message(message_data)

    return jsonify(message_data), 201

@app.route('/api/stream')
def stream():
    """SSE endpoint for real-time message updates"""
    session_token = request.args.get('token', '')

    user = db.get_user_by_token(session_token)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    def event_stream():
        """Generator for SSE events"""
        import queue
        client_queue = queue.Queue(maxsize=10)

        with sse_lock:
            sse_clients.append(client_queue)

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"

            while True:
                try:
                    # Wait for new message (with timeout for keepalive)
                    message = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        except GeneratorExit:
            # Client disconnected
            with sse_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def initialize_app():
    """Initialize the application"""
    # Create uploads directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize database
    db.init_db()

    # Initialize PIN
    auth.initialize_pin()

if __name__ == '__main__':
    initialize_app()

    print("\n" + "="*50)
    print("🚀 RPi Local Chat Server Starting...")
    print("="*50)
    print("\n  Access the chat at: http://<your-rpi-ip>:5000")
    print("  Local: http://localhost:5000\n")
    print("="*50 + "\n")

    # Run server
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
