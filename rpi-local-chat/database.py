"""
Database models and initialization for RPi Local Chat
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'chat.db')

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database with schema"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Channels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Attachments table (for images)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        ''')

        # Insert default channels if they don't exist
        cursor.execute('SELECT COUNT(*) FROM channels')
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO channels (name, description) VALUES (?, ?)",
                ('general', 'General chat for everything')
            )
            cursor.execute(
                "INSERT INTO channels (name, description) VALUES (?, ?)",
                ('pictures', 'Share your photos and images')
            )

        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_channel
            ON messages(channel_id, created_at DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_created
            ON messages(created_at DESC)
        ''')

        print("✓ Database initialized successfully")

def create_user(username, session_token):
    """Create a new user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, session_token) VALUES (?, ?)',
            (username, session_token)
        )
        return cursor.lastrowid

def get_user_by_token(session_token):
    """Get user by session token"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE session_token = ?',
            (session_token,)
        )
        return cursor.fetchone()

def get_user_by_username(username):
    """Get user by username"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        )
        return cursor.fetchone()

def update_user_last_seen(user_id):
    """Update user's last seen timestamp"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?',
            (user_id,)
        )

def get_all_channels():
    """Get all channels"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM channels ORDER BY id')
        return cursor.fetchall()

def get_channel_by_name(name):
    """Get channel by name"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM channels WHERE name = ?', (name,))
        return cursor.fetchone()

def create_message(channel_id, user_id, content, message_type='text'):
    """Create a new message"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO messages (channel_id, user_id, content, message_type)
               VALUES (?, ?, ?, ?)''',
            (channel_id, user_id, content, message_type)
        )
        return cursor.lastrowid

def get_recent_messages(channel_id, limit=100):
    """Get recent messages for a channel with user info"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT m.*, u.username, a.file_path, a.filename, a.mime_type
               FROM messages m
               JOIN users u ON m.user_id = u.id
               LEFT JOIN attachments a ON m.id = a.message_id
               WHERE m.channel_id = ?
               ORDER BY m.created_at DESC
               LIMIT ?''',
            (channel_id, limit)
        )
        return list(reversed(cursor.fetchall()))

def get_messages_with_size_limit(channel_id, size_limit_mb=100):
    """Get recent messages for a channel up to a size limit"""
    with get_db() as conn:
        cursor = conn.cursor()

        # First get messages without attachments (text, youtube links)
        cursor.execute(
            '''SELECT m.*, u.username, NULL as file_path, NULL as filename, NULL as mime_type
               FROM messages m
               JOIN users u ON m.user_id = u.id
               WHERE m.channel_id = ? AND m.id NOT IN (
                   SELECT message_id FROM attachments
               )
               ORDER BY m.created_at DESC
               LIMIT 200''',
            (channel_id,)
        )
        text_messages = list(reversed(cursor.fetchall()))

        # Then get messages with attachments, tracking size
        cursor.execute(
            '''SELECT m.*, u.username, a.file_path, a.filename, a.mime_type, a.file_size
               FROM messages m
               JOIN users u ON m.user_id = u.id
               JOIN attachments a ON m.id = a.message_id
               WHERE m.channel_id = ?
               ORDER BY m.created_at DESC''',
            (channel_id,)
        )

        attachment_messages = []
        total_size = 0
        size_limit_bytes = size_limit_mb * 1024 * 1024

        for row in cursor.fetchall():
            if total_size + row['file_size'] <= size_limit_bytes:
                total_size += row['file_size']
                attachment_messages.append(row)
            else:
                break

        attachment_messages.reverse()

        # Combine and sort by timestamp
        all_messages = text_messages + attachment_messages
        all_messages.sort(key=lambda x: x['created_at'])

        return all_messages

def create_attachment(message_id, filename, file_path, file_size, mime_type):
    """Create an attachment record"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO attachments (message_id, filename, file_path, file_size, mime_type)
               VALUES (?, ?, ?, ?, ?)''',
            (message_id, filename, file_path, file_size, mime_type)
        )
        return cursor.lastrowid

def get_total_attachments_size():
    """Get total size of all attachments in bytes"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COALESCE(SUM(file_size), 0) FROM attachments')
        return cursor.fetchone()[0]

if __name__ == '__main__':
    init_db()
