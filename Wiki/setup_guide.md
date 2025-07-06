# LNMT Web Dashboard Setup Guide

## 📋 Overview

This is a comprehensive web dashboard for the Linux Network Management Tool (LNMT) built with FastAPI, providing real-time monitoring, device management, and role-based access control.

## 🚀 Features

- **Authentication & Authorization**: JWT-based auth with role-based access (admin, user, guest)
- **Real-time Dashboard**: Live monitoring with charts and statistics
- **Device Management**: Complete CRUD operations for network devices
- **VLAN Management**: Configure and monitor VLANs
- **DNS Management**: Manage DNS records
- **Alert System**: Real-time alerts with severity levels
- **REST API**: Complete API with automatic documentation
- **WebSocket Updates**: Real-time data updates
- **Responsive Design**: Works on desktop and mobile

## 📦 Installation

### Prerequisites

```bash
# Python 3.10+
python3 --version

# Install required system packages (Ubuntu/Debian)
sudo apt update
sudo apt install python3-pip python3-venv
```

### Setup Instructions

1. **Create Project Structure**:
```bash
mkdir lnmt-web && cd lnmt-web
mkdir -p web/{templates,static/{css,js}}
```

2. **Create Virtual Environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**:
```bash
pip install fastapi uvicorn sqlalchemy python-jose[cryptography] python-multipart jinja2 aiofiles
```

4. **Create Files**:
   - Copy the `app.py` content to `web/app.py`
   - Copy templates to `web/templates/`
   - Copy CSS to `web/static/css/dashboard.css`
   - Copy JavaScript files to `web/static/js/`

## 🏃‍♂️ Running the Application

### Development Mode

```bash
# From the project root directory
cd web
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔐 Default Login Credentials

### Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Permissions**: Full access to all features

### User Account
- **Username**: `user`
- **Password**: `user123`
- **Permissions**: Limited access, cannot delete critical resources

## 🌐 Accessing the Dashboard

Once running, access the dashboard at:

- **Main Dashboard**: http://localhost:8000
- **Login Page**: http://localhost:8000/login
- **API Documentation**: http://localhost:8000/api/docs
- **Alternative API Docs**: http://localhost:8000/api/redoc

## 📱 Page Overview

### Dashboard Home (`/`)
- System health overview
- Device statistics
- Real-time bandwidth charts
- Recent alerts
- Network topology preview

### Device Management (`/devices`)
- View all network devices
- Add/edit/delete devices
- Filter by status, type, VLAN
- Real-time status updates

### VLAN Management (`/vlans`)
- Configure VLANs
- Subnet management
- Device assignments

### DNS Management (`/dns`)
- DNS record management
- A, AAAA, CNAME, MX records
- TTL configuration

### Alerts (`/alerts`)
- View all system alerts
- Filter by severity
- Resolve alerts
- Alert history

### Configuration (`/config`)
- LNMT settings
- Firewall configuration
- System parameters

## 🔧 API Endpoints

### Authentication
```
POST /api/auth/login          # User login
POST /api/auth/register       # Register user (admin only)
GET  /api/auth/me            # Get current user info
```

### Dashboard
```
GET  /api/dashboard/summary   # Dashboard summary data
```

### Devices
```
GET    /api/devices          # List all devices
POST   /api/devices          # Create new device
PUT    /api/devices/{id}     # Update device
DELETE /api/devices/{id}     # Delete device
```

### VLANs
```
GET    /api/vlans            # List all VLANs
POST   /api/vlans            # Create new VLAN
PUT    /api/vlans/{id}       # Update VLAN
DELETE /api/vlans/{id}       # Delete VLAN
```

### DNS Records
```
GET    /api/dns              # List DNS records
POST   /api/dns              # Create DNS record
PUT    /api/dns/{id}         # Update DNS record
DELETE /api/dns/{id}         # Delete DNS record
```

### Alerts
```
GET /api/alerts              # List all alerts
PUT /api/alerts/{id}/resolve # Resolve alert
```

### Statistics
```
GET /api/stats/bandwidth     # Bandwidth statistics
```

## 🔒 Security Features

### Authentication
- JWT tokens with 30-minute expiration
- Secure password hashing (SHA-256)
- Automatic token refresh

### Authorization
- Role-based access control
- Route-level permissions
- UI element visibility based on roles

### Security Headers
- CORS configuration
- Input validation
- SQL injection protection

## 🎨 Customization

### Styling
- Bootstrap 5 for responsive design
- Custom CSS variables for theming
- FontAwesome icons
- Chart.js for data visualization

### Configuration
Edit `web/app.py` to modify:
- Database connection string
- JWT secret key
- Token expiration time
- CORS settings

## 🧪 Testing

### Manual Testing
1. Start the application
2. Navigate to login page
3. Login with demo credentials
4. Test all major features:
   - Dashboard widgets
   - Device CRUD operations
   - Alert management
   - Real-time updates

### API Testing
Use the built-in Swagger UI at `/api/docs` to test all endpoints.

### Example API Calls
```bash
# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Get devices (with token)
curl -X GET "http://localhost:8000/api/devices" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📊 Monitoring & Logging

### Application Logs
The application logs important events:
- Authentication attempts
- API requests
- Error conditions
- WebSocket connections

### Real-time Updates
- WebSocket connection for live data
- Automatic reconnection on disconnect
- Real-time device status updates
- Live alert notifications

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**:
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill the process
   kill -9 PID
   ```

2. **Database Issues**:
   ```bash
   # Delete database file to reset
   rm lnmt.db
   # Restart application to recreate tables
   ```

3. **Static Files Not Loading**:
   - Check file paths in templates
   - Ensure static directory structure is correct
   - Verify file permissions

4. **Authentication Problems**:
   - Check JWT secret key
   - Verify token expiration settings
   - Clear browser localStorage

### Debug Mode
Enable debug logging by modifying `app.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Integration with LNMT Modules

This web interface is designed to integrate with other LNMT modules:

- **Network Scanner**: Import discovered devices
- **VLAN Manager**: Configure VLAN settings
- **DNS Manager**: Manage DNS records
- **Alert Engine**: Display and manage alerts
- **Auth Engine**: User authentication

## 📈 Performance Optimization

### Production Recommendations
- Use PostgreSQL instead of SQLite
- Implement Redis for session storage
- Set up reverse proxy (Nginx)
- Enable gzip compression
- Use CDN for static assets

### Scaling
- Deploy with Docker containers
- Use load balancer for multiple instances
- Implement database connection pooling
- Cache frequently accessed data

## 🤝 Contributing

To extend the dashboard:
1. Add new API endpoints in `app.py`
2. Create corresponding templates
3. Add JavaScript functionality
4. Update navigation and permissions
5. Add appropriate tests

## 📄 License

This LNMT Web Dashboard is part of the Linux Network Management Tool suite.