# 🚀 Temporary File Sharing App

A secure, self-hosted web application for sharing files with others via unique download links and email notifications. Built with Flask, SQLite, and Mailjet integration, it is designed for privacy, ease of use, and modern security best practices.

## ✨ Features

### 📤 File Sharing & Upload
- 📤 Chunked uploads and multi-file sharing (up to 10GB per file)
- 🔗 Unique download links with token-based access
- 📁 Multi-file ZIP download support
- 🔄 Duplicate filename handling with auto-renaming

### 👨‍💼 Admin Interface
- 🖥️ Web-based admin dashboard with statistics
- ✅ Per-file download tracking and visual status
- 📊 Storage usage monitoring and file management
- � Configurable settings via web interface
- 🧹 Manual and automatic cleanup controls
- 📧 Email notification testing and management

### 🔒 Security & Authentication
- 🛡️ Robust CSRF protection (with exemptions for AJAX endpoints)
- 🔐 Encrypted storage for sensitive data (API keys, passwords)
- 👤 Admin authentication with bcrypt password hashing
- 🔑 API key authentication for external integrations

### 📧 Email & Notifications
- 📧 Single email notification per share
- ✉️ HTML email templates with customizable branding
- 🧪 Built-in email testing functionality
- 🌐 Multi-timezone support (default: Pacific/Auckland)

### 🤖 Automation & Configuration
- 🤖 Automatic environment selection (development vs production)
- 🐳 Docker-ready: production config auto-selected in containers
- 💻 Local-ready: development config auto-selected outside Docker
- 📋 Detailed logging with rotation and cleanup scheduler
- ⏰ Configurable file retention periods
- 🗄️ Automatic database initialization and migrations

### 🔌 API & Integration
- 🔌 REST API for external file uploads
- 📊 Upload progress tracking (ready for implementation)
- 🔗 Webhook-ready architecture

## 🛠 Requirements

- 🐍 Python 3.12+
- 📦 pip
- ✉️ Mailjet account (for email notifications)
- 🐳 Docker (optional, for containerized deployment)
- 💾 SQLite (included with Python)
- 🌐 Modern web browser with JavaScript support

## ⚡ Quick Start

### 💻 Local Development
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Craig-G-NZ/temporary-file-sharing.git
   cd temporary-file-sharing
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set environment variables (optional, for secrets):**
   - You can set `MAILJET_API_KEY`, `MAILJET_API_SECRET`, and other secrets as environment variables or via the admin panel.

4. **Run the app:**
   ```bash
   python app/run.py
   # or for development with Flask
   cd app && flask run --host=0.0.0.0 --port=5000
   ```

5. **Access the app:**
   - Open [http://localhost:5000](http://localhost:5000) in your browser.

### 🐳 Docker Usage

1. **Build the Docker image:**
   ```bash
   docker build -t temp-file-share .
   ```

2. **Run the container:**
   ```bash
   docker run -d -p 5000:5000 \
     -e MAILJET_API_KEY=your_key \
     -e MAILJET_API_SECRET=your_secret \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/app/data:/app/data \
     --name temp-file-share temp-file-share
   ```

3. **Using Docker Compose (recommended):**
   ```bash
   # Copy docker-compose.yml and create .env file with your settings
   cp .env.example .env  # Edit with your values
   docker-compose up -d
   ```

## ⚙️ Configuration

### 🎛️ Admin Interface
1. **Access the admin panel:** [http://localhost:5000/admin/login](http://localhost:5000/admin/login)
2. **Default credentials:** `admin` / `changeme` (change immediately!)
3. **Configure via web interface:**
   - Email settings (Mailjet API credentials)
   - File retention periods
   - Upload limits and restrictions
   - Auto-cleanup settings
   - Display timezone preferences

### 🔧 Environment Variables
You can set these environment variables for configuration:
```bash
# Email configuration
MAILJET_API_KEY=your_mailjet_api_key
MAILJET_API_SECRET=your_mailjet_secret
MAILJET_FROM_EMAIL=sender@yourdomain.com
MAILJET_FROM_NAME="Your File Share"

# Admin credentials (change default!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password_here

# File settings
FILE_RETENTION_HOURS=24
MAX_CONTENT_LENGTH=10737418240  # 10GB in bytes

# Application settings
SECRET_KEY=your_secret_key_here
FLASK_ENV=production  # or development
```

- All settings (email, retention, admin, etc.) can be managed via the admin panel after first login.
- Sensitive data is encrypted using a key stored in `app/data/.encryption_key` (never commit this file).

## 🔐 Security Notes

- 🔒 Passwords and API keys are encrypted at rest using Fernet encryption
- 🛡️ CSRF protection enabled with secure token handling
- 👤 Admin authentication required for all management functions
- 🔑 Unique tokens for each file share with expiration
- 🗂️ Files stored in secure upload directories outside web root
- ⚠️ The app should be run behind HTTPS in production
- 📁 The uploads and data folders are excluded from version control for privacy
- 🧹 Automatic cleanup of expired files and shares

## 🔌 API Usage

The application includes a REST API for external integrations:

### Authentication
All API requests require an API key header:
```bash
X-API-Key: your_api_key_here
```

### Upload Files
```bash
curl -X POST http://localhost:5000/api/upload \
  -H "X-API-Key: your_api_key" \
  -F "files=@file1.txt" \
  -F "files=@file2.pdf"
```

**Response:**
```json
{
  "success": true,
  "token": "abc123...",
  "download_url": "http://localhost:5000/download/abc123...",
  "expires_at": "2024-01-01T12:00:00Z"
}
```

## 📊 Admin Features

### Dashboard
- 📈 View total, active, and expired shares
- 💾 Monitor storage usage across all uploads
- ⚙️ Quick access to configuration status

### File Management
- 📂 View all shared files with download status
- 🗑️ Manually delete expired or unwanted shares  
- 🔄 Reactivate expired shares if needed
- 📧 Resend notification emails

### Settings Management
- ✉️ Configure Mailjet email integration
- ⏰ Set file retention periods
- 📏 Configure upload size limits
- 🕒 Set cleanup schedules
- 🌍 Configure timezone display

## 🐛 Troubleshooting

### Common Issues

**Email not sending:**
- Check Mailjet API credentials in admin settings
- Use the "Test Email" feature in admin panel
- Verify `MAILJET_FROM_EMAIL` is authorized in your Mailjet account

**Files not uploading:**
- Check file size limits in admin settings
- Ensure sufficient disk space in upload directory
- Check browser JavaScript console for errors

**Permission denied errors:**
- Ensure `app/uploads`, `app/data`, and `app/logs` directories are writable
- In Docker: volumes should be properly mounted and owned by container user

**Database errors:**
- Delete `app/data/app_data.db` to reset (will lose all data)
- Check `app/data` directory is writable

### Logs
- Application logs: `app/logs/app.log`
- Download logs: `app/logs/downloads.log`
- Docker logs: `docker logs temp-file-share`

## 🤝 Contributing

Pull requests and issues are welcome! Please open an issue to discuss major changes first.

### 🧪 Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Run in development mode: `FLASK_ENV=development python app/run.py`
5. Submit a pull request

### 🏗️ Architecture
- **Frontend:** Bootstrap 5 + Vanilla JavaScript
- **Backend:** Flask with SQLite database
- **Security:** bcrypt + Fernet encryption
- **Email:** Mailjet REST API integration
- **Upload:** Chunked file upload with AJAX

## 📄 License

MIT License

## 🏗️ Technology Stack

- **Backend Framework:** Flask (Python 3.12+)
- **Database:** SQLite with automatic migrations
- **Authentication:** Flask-Login with bcrypt password hashing
- **Security:** Flask-WTF CSRF protection, Fernet encryption
- **Email Service:** Mailjet REST API
- **Frontend:** Bootstrap 5, Vanilla JavaScript, AJAX
- **File Handling:** Chunked uploads, ZIP compression
- **Deployment:** Docker + Gunicorn, development server support
- **Logging:** Python logging with rotation
- **Task Scheduling:** Background cleanup scheduler

## 📋 Project Structure

```
app/
├── __init__.py              # Flask application factory
├── run.py                   # Application entry point
├── config.py                # Configuration classes
├── models/                  # Data models
│   ├── admin.py            # Admin user model
│   ├── file_share.py       # File sharing model
│   └── settings.py         # Application settings
├── utils/                   # Utility modules
│   ├── cleanup.py          # Automated cleanup scheduler
│   ├── database.py         # Database connection handling
│   ├── email.py            # Email notification service
│   ├── file_utils.py       # File handling utilities
│   ├── helpers.py          # General helper functions
│   └── security.py         # Security utilities
├── web/                     # Web controllers
│   ├── admin.py            # Admin interface routes
│   ├── api.py              # REST API endpoints
│   ├── auth.py             # Authentication routes
│   └── main.py             # Public facing routes
├── templates/               # Jinja2 templates
├── static/                  # CSS, JS, and static assets
├── uploads/                 # File storage (gitignored)
├── data/                    # Database and encryption keys
└── logs/                    # Application logs
```

---

**Author:** Craig-G-NZ
