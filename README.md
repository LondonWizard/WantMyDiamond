# Want My Diamond - Fine Jewelry Showcase Platform

A full-stack web application for showcasing fine jewelry, custom designs, and providing appraisal services. Built with Flask backend and modern responsive frontend.

## Features

### Customer Features
- **Jewelry Gallery**: Browse fine jewelry with detailed specifications
- **Custom Ring Designer**: Customize existing pieces with interactive options
- **Messaging System**: Direct communication with the jewelry owner
- **Custom Design Requests**: Upload images and request custom pieces
- **DIA Appraisal Service**: Professional jewelry appraisals ($50/item)

### Admin Features
- **Listing Management**: Full CRUD operations for jewelry listings
- **Message Management**: Handle customer communications
- **Request Management**: Process custom design and appraisal requests
- **Dashboard**: Overview of business metrics and recent activity

### Technical Features
- **Responsive Design**: Mobile-first, Blue Nile-inspired interface
- **File Upload Support**: Images, videos, and documents
- **Real-time Notifications**: Unread message indicators
- **Database Storage**: Secure SQLite/PostgreSQL support
- **Session Management**: Persistent customer messaging sessions

## Installation & Setup

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd WantMyDiamond
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Website: http://localhost:5000
   - Admin Panel: http://localhost:5000/admin/login
   - Default admin credentials: admin / changeme123

### Production Deployment (AWS EC2 + Ubuntu)

#### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx supervisor git -y

# Create application user
sudo adduser wmd
sudo usermod -aG sudo wmd
```

#### 2. Application Setup

```bash
# Switch to application user
sudo su - wmd

# Clone repository
git clone <your-repository-url> /home/wmd/wantmydiamond
cd /home/wmd/wantmydiamond

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Edit configuration
```

#### 3. Nginx Configuration

Create `/etc/nginx/sites-available/wantmydiamond`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/wmd/wantmydiamond/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    client_max_body_size 16M;
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/wantmydiamond /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

#### 4. Supervisor Configuration

Create `/etc/supervisor/conf.d/wantmydiamond.conf`:

```ini
[program:wantmydiamond]
command=/home/wmd/wantmydiamond/venv/bin/gunicorn -c gunicorn_config.py app:app
directory=/home/wmd/wantmydiamond
user=wmd
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/wantmydiamond.log
environment=FLASK_CONFIG=production
```

Start the service:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start wantmydiamond
```

#### 5. SSL Setup (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Configuration

### Environment Variables

- `FLASK_CONFIG`: production/development
- `SECRET_KEY`: Flask secret key (generate a secure one)
- `DATABASE_URL`: Database connection string
- `ADMIN_USERNAME`: Admin panel username
- `ADMIN_PASSWORD`: Admin panel password

### Database Setup

For production with PostgreSQL:
1. Install PostgreSQL
2. Create database and user
3. Update `DATABASE_URL` in .env
4. Run application to create tables

## Usage

### Admin Panel

1. Access `/admin/login`
2. Use configured admin credentials
3. Navigate through:
   - **Dashboard**: Overview and quick actions
   - **Listings**: Manage jewelry inventory
   - **Messages**: Customer communications
   - **Custom Requests**: Design requests
   - **Appraisal Requests**: DIA appraisal services

### Customer Flow

1. **Browse Gallery**: View available jewelry
2. **Customize Item**: Select options and preferences
3. **Contact**: Enter contact information
4. **Message**: Discuss customizations directly
5. **Custom Request**: Submit design ideas with images
6. **Appraisal**: Request professional evaluation

## API Endpoints

### Public API
- `GET /api/listings`: Jewelry listings (JSON)
- `GET /api/listing/<id>`: Single listing details
- `GET /api/categories`: Available categories

### Admin API (Authenticated)
- `GET /api/admin/stats`: Dashboard statistics
- `GET /api/admin/messages/recent`: Recent messages

## File Structure

```
WantMyDiamond/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # Database models
├── requirements.txt    # Python dependencies
├── gunicorn_config.py  # Gunicorn configuration
├── routes/             # Application routes
│   ├── main.py         # Public routes
│   ├── admin.py        # Admin routes
│   └── api.py          # API routes
├── templates/          # Jinja2 templates
│   ├── base.html       # Base template
│   ├── index.html      # Landing page
│   ├── gallery.html    # Jewelry gallery
│   └── admin/          # Admin templates
└── static/             # Static files
    └── uploads/        # File uploads
```

## Security Considerations

- Change default admin credentials
- Use strong SECRET_KEY
- Enable HTTPS in production
- Regular database backups
- Monitor file uploads
- Rate limiting (recommended)

## Support

For technical support or business inquiries:
- Website: Contact form and messaging system
- Instagram: [@wantmydiamond](https://www.instagram.com/wantmydiamond/)
- Reviews: [Wedding Wire](https://www.weddingwire.com/reviews/want-my-diamond-los-angeles/d88c9398bec89378.html)

## License

This project is proprietary software for Want My Diamond, Los Angeles.

---

**Want My Diamond** - Fine Jewelry & Custom Designs in Los Angeles

