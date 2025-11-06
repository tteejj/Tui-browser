/**
 * RPi Local Chat - Frontend Application
 */

class ChatApp {
    constructor() {
        this.sessionToken = localStorage.getItem('chat_session_token');
        this.currentUser = null;
        this.currentChannel = null;
        this.channels = [];
        this.eventSource = null;

        this.init();
    }

    init() {
        // Check if user has existing session
        if (this.sessionToken) {
            this.verifySession();
        } else {
            this.showLoginScreen();
        }

        this.attachEventListeners();
    }

    attachEventListeners() {
        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        // Message form
        const messageForm = document.getElementById('messageForm');
        if (messageForm) {
            messageForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        // File upload
        const uploadBtn = document.getElementById('uploadBtn');
        const fileInput = document.getElementById('fileInput');
        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        // Upload preview actions
        const cancelUpload = document.getElementById('cancelUpload');
        const confirmUpload = document.getElementById('confirmUpload');
        if (cancelUpload) {
            cancelUpload.addEventListener('click', () => this.cancelUpload());
        }
        if (confirmUpload) {
            confirmUpload.addEventListener('click', () => this.uploadImage());
        }

        // Logout
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
    }

    showLoginScreen() {
        document.getElementById('loginScreen').classList.add('active');
        document.getElementById('chatScreen').classList.remove('active');
    }

    showChatScreen() {
        document.getElementById('loginScreen').classList.remove('active');
        document.getElementById('chatScreen').classList.add('active');
    }

    async handleLogin() {
        const username = document.getElementById('usernameInput').value.trim();
        const pin = document.getElementById('pinInput').value.trim();
        const errorDiv = document.getElementById('loginError');

        errorDiv.textContent = '';
        errorDiv.classList.remove('show');

        try {
            const response = await fetch('/api/auth/verify-pin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, pin })
            });

            const data = await response.json();

            if (response.ok) {
                this.sessionToken = data.session_token;
                this.currentUser = {
                    id: data.user_id,
                    username: data.username
                };

                localStorage.setItem('chat_session_token', this.sessionToken);
                this.showChatScreen();
                this.loadApp();
            } else {
                errorDiv.textContent = data.error || 'Login failed';
                errorDiv.classList.add('show');
            }
        } catch (error) {
            console.error('Login error:', error);
            errorDiv.textContent = 'Connection error. Please try again.';
            errorDiv.classList.add('show');
        }
    }

    async verifySession() {
        try {
            const response = await fetch('/api/auth/verify-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_token: this.sessionToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.currentUser = {
                    id: data.user_id,
                    username: data.username
                };
                this.showChatScreen();
                this.loadApp();
            } else {
                // Session invalid, show login
                localStorage.removeItem('chat_session_token');
                this.sessionToken = null;
                this.showLoginScreen();
            }
        } catch (error) {
            console.error('Session verification error:', error);
            this.showLoginScreen();
        }
    }

    async loadApp() {
        // Update user badge
        document.getElementById('currentUser').textContent = this.currentUser.username;

        // Load channels
        await this.loadChannels();

        // Select first channel by default
        if (this.channels.length > 0) {
            this.selectChannel(this.channels[0]);
        }

        // Connect to SSE for real-time updates
        this.connectSSE();
    }

    async loadChannels() {
        try {
            const response = await fetch('/api/channels', {
                headers: { 'Authorization': `Bearer ${this.sessionToken}` }
            });

            if (response.ok) {
                this.channels = await response.json();
                this.renderChannels();
            }
        } catch (error) {
            console.error('Error loading channels:', error);
        }
    }

    renderChannels() {
        const channelList = document.getElementById('channelList');
        channelList.innerHTML = '';

        this.channels.forEach(channel => {
            const channelItem = document.createElement('div');
            channelItem.className = 'channel-item';
            channelItem.dataset.channelId = channel.id;
            channelItem.innerHTML = `
                <span class="channel-name">#${channel.name}</span>
                <span class="channel-desc">${channel.description}</span>
            `;
            channelItem.addEventListener('click', () => this.selectChannel(channel));
            channelList.appendChild(channelItem);
        });
    }

    async selectChannel(channel) {
        this.currentChannel = channel;

        // Update UI
        document.getElementById('currentChannelName').textContent = `#${channel.name}`;
        document.getElementById('currentChannelDesc').textContent = channel.description;

        // Update active state
        document.querySelectorAll('.channel-item').forEach(item => {
            item.classList.remove('active');
            if (parseInt(item.dataset.channelId) === channel.id) {
                item.classList.add('active');
            }
        });

        // Load messages
        await this.loadMessages();
    }

    async loadMessages() {
        try {
            const response = await fetch(`/api/messages/${this.currentChannel.id}`, {
                headers: { 'Authorization': `Bearer ${this.sessionToken}` }
            });

            if (response.ok) {
                const messages = await response.json();
                this.renderMessages(messages);
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    renderMessages(messages) {
        const container = document.getElementById('messageContainer');
        container.innerHTML = '';

        messages.forEach(message => {
            this.appendMessage(message);
        });

        // Scroll to bottom
        this.scrollToBottom();
    }

    appendMessage(message) {
        const container = document.getElementById('messageContainer');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.dataset.messageId = message.id;

        const timestamp = new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });

        let contentHTML = '';

        if (message.message_type === 'text') {
            contentHTML = `<div class="message-content">${this.escapeHtml(message.content)}</div>`;
        } else if (message.message_type === 'image' && message.attachment) {
            contentHTML = `
                <div class="message-content">${this.escapeHtml(message.content)}</div>
                <div class="message-image">
                    <img src="${message.attachment.file_path}" alt="${message.attachment.filename}" loading="lazy">
                </div>
            `;
        } else if (message.message_type === 'youtube' && message.youtube) {
            const yt = message.youtube;
            contentHTML = `
                <div class="youtube-preview" onclick="window.open('${yt.url}', '_blank')">
                    <div class="youtube-thumbnail">
                        <img src="${yt.thumbnail}" alt="${this.escapeHtml(yt.title)}">
                    </div>
                    <div class="youtube-info">
                        <div class="youtube-title">${this.escapeHtml(yt.title)}</div>
                        <div class="youtube-author">${this.escapeHtml(yt.author)}</div>
                    </div>
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-author">${this.escapeHtml(message.username)}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            ${contentHTML}
        `;

        container.appendChild(messageDiv);
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const content = input.value.trim();

        if (!content) return;

        try {
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.sessionToken}`
                },
                body: JSON.stringify({
                    channel_id: this.currentChannel.id,
                    content: content
                })
            });

            if (response.ok) {
                input.value = '';
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            alert('Invalid file type. Please upload PNG, JPG, GIF, or WEBP images.');
            return;
        }

        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('File is too large. Maximum size is 10MB.');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('previewImage').src = e.target.result;
            document.getElementById('previewFileName').textContent = file.name;
            document.getElementById('uploadPreview').style.display = 'flex';
        };
        reader.readAsDataURL(file);
    }

    cancelUpload() {
        document.getElementById('fileInput').value = '';
        document.getElementById('captionInput').value = '';
        document.getElementById('uploadPreview').style.display = 'none';
    }

    async uploadImage() {
        const fileInput = document.getElementById('fileInput');
        const caption = document.getElementById('captionInput').value.trim();

        if (!fileInput.files[0]) return;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('channel_id', this.currentChannel.id);
        formData.append('caption', caption || `Uploaded ${fileInput.files[0].name}`);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`
                },
                body: formData
            });

            if (response.ok) {
                this.cancelUpload();
            } else {
                const data = await response.json();
                alert(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading image:', error);
            alert('Upload failed. Please try again.');
        }
    }

    connectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource(`/api/stream?token=${this.sessionToken}`);

        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'connected') {
                console.log('SSE connected');
                return;
            }

            // Only show message if it's for current channel
            if (data.channel_id === this.currentChannel.id) {
                this.appendMessage(data);
                this.scrollToBottom();
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            // Attempt reconnection after 5 seconds
            setTimeout(() => {
                if (this.sessionToken) {
                    this.connectSSE();
                }
            }, 5000);
        };
    }

    scrollToBottom() {
        const container = document.getElementById('messageContainer');
        container.scrollTop = container.scrollHeight;
    }

    logout() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        localStorage.removeItem('chat_session_token');
        this.sessionToken = null;
        this.currentUser = null;
        this.currentChannel = null;

        // Clear forms
        document.getElementById('usernameInput').value = '';
        document.getElementById('pinInput').value = '';

        this.showLoginScreen();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
