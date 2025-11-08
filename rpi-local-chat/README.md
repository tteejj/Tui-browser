# RPi Local Chat

A lightweight, local network-only chat application designed for Raspberry Pi Zero 2 W and other Linux systems. Features PIN-based authentication, image sharing, YouTube link previews, and real-time messaging.

Works on:
- **Raspberry Pi** (Zero 2 W, 3, 4, 5, etc.)
- **x86/x86_64 Linux** (Debian, Ubuntu, Void Linux, etc.)
- **ARM Linux** devices

## Features

- **PIN-based Authentication**: Simple 6-digit PIN for access control
- **Real-time Messaging**: Server-Sent Events (SSE) for instant message delivery
- **Image Sharing**: Upload and share images with automatic resizing
- **YouTube Previews**: Automatic preview generation for YouTube links
- **Multiple Channels**: Organized conversations (#general, #pictures)
- **Lightweight**: Optimized for Raspberry Pi Zero 2 W (512MB RAM)
- **Local Network Only**: No internet required for chat functionality

## Hardware Requirements

- **Raspberry Pi**: Zero 2 W, 3, 4, 5, or any model
- **x86/x86_64 PC**: Any Linux-capable computer
- Storage: 8GB minimum
- Power supply
- Local network (WiFi or Ethernet)

## Software Requirements

- Python 3.7 or higher
- pip (Python package manager)
- Linux operating system (Raspberry Pi OS, Debian, Ubuntu, Void Linux, etc.)

## Installation

Choose the installation method for your operating system:

### Quick Install (Automated)

**For Raspberry Pi OS / Debian / Ubuntu:**
```bash
cd rpi-local-chat
./setup.sh
```

**For Void Linux (x86/ARM):**
```bash
cd rpi-local-chat
./setup-void.sh
```

### Manual Installation

#### For Raspberry Pi OS / Debian / Ubuntu

##### 1. Prepare Your System

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required system packages
sudo apt install python3 python3-pip python3-venv -y

# Install image processing dependencies
sudo apt install libjpeg-dev zlib1g-dev -y
```

##### 2. Download and Set Up the Application

```bash
# Create app directory
mkdir -p ~/apps
cd ~/apps

# Copy the rpi-local-chat folder to your Pi
# (Use scp, rsync, or git clone if hosted on Git)

cd rpi-local-chat

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

##### 3. Initialize the Application

```bash
# Initialize database and generate PIN
python3 database.py
python3 auth.py
```

This will display your 6-digit PIN. **Save this PIN** - you'll need it to access the chat.

##### 4. Run the Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
python3 server.py
```

The server will start on port 5000. You'll see output like:

```
🚀 RPi Local Chat Server Starting...
Access the chat at: http://<your-rpi-ip>:5000
```

##### 5. Find Your IP Address

```bash
hostname -I
```

Use the first IP address shown (usually starts with 192.168.x.x or 10.0.x.x)

#### For Void Linux (x86/x86_64/ARM)

##### 1. Prepare Your System

```bash
# Update system
sudo xbps-install -Su

# Install Python and required system packages
sudo xbps-install -Sy python3 python3-pip python3-virtualenv

# Install image processing dependencies
sudo xbps-install -Sy libjpeg-turbo-devel zlib-devel
```

##### 2. Download and Set Up the Application

```bash
# Create app directory
mkdir -p ~/apps
cd ~/apps

# Copy the rpi-local-chat folder to your system
# (Use git clone if hosted on Git)

cd rpi-local-chat

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

##### 3. Initialize the Application

```bash
# Initialize database and generate PIN
python3 database.py
python3 auth.py
```

This will display your 6-digit PIN. **Save this PIN** - you'll need it to access the chat.

##### 4. Run the Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
python3 server.py
```

##### 5. Find Your IP Address

```bash
hostname -I
# or
ip addr show
```

Use the first non-localhost IP address shown.

## Usage

### Accessing the Chat

1. Open a web browser on any device connected to your local network
2. Navigate to `http://<raspberry-pi-ip>:5000`
3. Enter your username (any name you want)
4. Enter the 6-digit PIN shown when you initialized the app
5. Click "Join Chat"

### Sending Messages

- Type your message in the input box at the bottom
- Press Enter or click "Send"

### Sharing Images

1. Click the 📎 button next to the message input
2. Select an image (PNG, JPG, GIF, or WEBP)
3. Add an optional caption
4. Click "Send Image"

Images are automatically resized to save storage space.

### Sharing YouTube Links

Simply paste a YouTube URL in your message:
```
https://www.youtube.com/watch?v=VIDEO_ID
```

The app will automatically generate a preview with thumbnail, title, and author.

### Switching Channels

Click on a channel name in the left sidebar to switch between:
- **#general**: General chat for everything
- **#pictures**: Share your photos and images

## Running as a System Service (Optional)

To have the chat server start automatically on boot:

### For systemd-based systems (Raspberry Pi OS, Debian, Ubuntu)

#### 1. Create systemd service file

```bash
sudo nano /etc/systemd/system/rpi-chat.service
```

#### 2. Add this content (adjust paths as needed):

```ini
[Unit]
Description=RPi Local Chat Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/apps/rpi-local-chat
Environment="PATH=/home/pi/apps/rpi-local-chat/venv/bin"
ExecStart=/home/pi/apps/rpi-local-chat/venv/bin/python3 server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable rpi-chat
sudo systemctl start rpi-chat

# Check status
sudo systemctl status rpi-chat

# View logs
sudo journalctl -u rpi-chat -f
```

### For runit-based systems (Void Linux)

#### 1. Create runit service directory

```bash
sudo mkdir -p /etc/sv/rpi-chat
```

#### 2. Create run script

```bash
sudo nano /etc/sv/rpi-chat/run
```

Add this content (adjust paths and username):

```bash
#!/bin/sh
exec chpst -u yourusername /home/yourusername/apps/rpi-local-chat/venv/bin/python3 /home/yourusername/apps/rpi-local-chat/server.py 2>&1
```

#### 3. Make it executable and enable the service

```bash
sudo chmod +x /etc/sv/rpi-chat/run
sudo ln -s /etc/sv/rpi-chat /var/service/

# Check status
sudo sv status rpi-chat

# View logs (if you set up logging)
sudo svlogtail rpi-chat
```

## Configuration

### Changing the PIN

```bash
python3 auth.py
```

This generates a new PIN and displays it.

### Adding More Channels

Edit `database.py` and add channels in the `init_db()` function:

```python
cursor.execute(
    "INSERT INTO channels (name, description) VALUES (?, ?)",
    ('your-channel', 'Channel description')
)
```

Then reinitialize the database:
```bash
python3 database.py
```

### Adjusting Upload Limits

Edit `server.py`:

```python
# Change max file size (default 10MB)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Change image size limit (default 100MB of images loaded)
messages = db.get_messages_with_size_limit(channel_id, size_limit_mb=100)
```

## Performance Notes

### Memory Usage
- Typical memory footprint: ~150-250MB
- Supports up to 7 concurrent users comfortably on RPi Zero 2 W
- Images are automatically resized to conserve storage and bandwidth

### Storage
- SQLite database grows with messages
- Images stored in `static/uploads/`
- All images and links are kept permanently
- Only the latest ~100MB of images are loaded in the UI

## Troubleshooting

### Can't connect to the server
- Verify Pi and client are on the same network
- Check firewall settings: `sudo ufw allow 5000`
- Verify server is running: `systemctl status rpi-chat`

### "Invalid PIN" error
- Regenerate PIN: `python3 auth.py`
- Make sure you're using the correct 6-digit PIN

### Images not uploading
- Check disk space: `df -h`
- Verify upload folder exists and has correct permissions
- Check file size (must be under 10MB)

### Server crashes or high memory usage
- Check logs: `sudo journalctl -u rpi-chat -f`
- Reduce concurrent users
- Lower image size limit in server.py

## File Structure

```
rpi-local-chat/
├── server.py           # Main Flask application
├── database.py         # Database models and operations
├── auth.py            # Authentication (PIN management)
├── requirements.txt   # Python dependencies
├── setup.sh           # Automated setup for Debian/Ubuntu/RPi OS
├── setup-void.sh      # Automated setup for Void Linux
├── run.sh             # Quick start script
├── README.md          # This file
├── static/
│   ├── css/
│   │   └── style.css  # UI styling
│   ├── js/
│   │   └── app.js     # Frontend logic
│   └── uploads/       # User-uploaded images
├── templates/
│   └── index.html     # Main web interface
├── chat.db            # SQLite database (created on first run)
└── .chat_pin          # Encrypted PIN (created on first run)
```

## Security Notes

- **Local network only**: Server binds to 0.0.0.0 but should be behind a firewall
- **PIN-based auth**: Suitable for trusted home/local networks
- **No HTTPS**: For local use only, not internet-exposed
- **Session tokens**: Stored in browser localStorage
- **No rate limiting**: Trusts local network users

**Do not expose this application to the internet without additional security measures.**

## Limitations

- Maximum 15 total users (not concurrent)
- Maximum 7 concurrent users
- 10MB max file size per image
- Local network only (no remote access)
- No end-to-end encryption
- No message editing or deletion
- No user management (admin can't ban users)

## Future Enhancements

Possible improvements:
- Message search functionality
- User avatars
- Emoji reactions
- File attachments (PDFs, documents)
- Voice messages
- Mobile-responsive design improvements
- Dark/light theme toggle

## License

MIT License - Feel free to modify and use as you wish!

## Support

For issues or questions, check the logs:
```bash
# If running as service
sudo journalctl -u rpi-chat -f

# If running manually
# Look at terminal output
```

## Credits

Built for Raspberry Pi Zero 2 W with love and minimal dependencies.
