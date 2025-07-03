# web/app.py
from fastapi import FastAPI, HTTPException, Depends, Request, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import jwt
import hashlib
import json
import asyncio
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="LNMT Web Dashboard",
    description="Linux Network Management Tool - Web Interface",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Database setup
DATABASE_URL = "sqlite:///./lnmt.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")  # admin, user, guest
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, index=True)
    ip_address = Column(String, index=True)
    mac_address = Column(String)
    device_type = Column(String)
    status = Column(String, default="unknown")
    last_seen = Column(DateTime, default=datetime.utcnow)
    vlan_id = Column(Integer)

class NetworkAlert(Base):
    __tablename__ = "network_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String)
    severity = Column(String)
    message = Column(Text)
    source_ip = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

class BandwidthUsage(Base):
    __tablename__ = "bandwidth_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    interface = Column(String)
    rx_bytes = Column(Float)
    tx_bytes = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class VLANConfig(Base):
    __tablename__ = "vlan_config"
    
    id = Column(Integer, primary_key=True, index=True)
    vlan_id = Column(Integer, unique=True)
    name = Column(String)
    description = Column(String)
    subnet = Column(String)
    gateway = Column(String)
    is_active = Column(Boolean, default=True)

class DNSRecord(Base):
    __tablename__ = "dns_records"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True)
    record_type = Column(String)
    value = Column(String)
    ttl = Column(Integer, default=3600)
    is_active = Column(Boolean, default=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class DeviceCreate(BaseModel):
    hostname: str
    ip_address: str
    mac_address: str
    device_type: str
    vlan_id: Optional[int] = None

class VLANCreate(BaseModel):
    vlan_id: int
    name: str
    description: str
    subnet: str
    gateway: str

class DNSRecordCreate(BaseModel):
    domain: str
    record_type: str
    value: str
    ttl: int = 3600

# Authentication utilities
security = HTTPBearer()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        role_hierarchy = {"guest": 0, "user": 1, "admin": 2}
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 2)
        
        if user_level < required_level:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# Mock data generators for development
def generate_mock_data(db: Session):
    """Generate mock data for testing"""
    # Create admin user if not exists
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@lnmt.local",
            hashed_password=hash_password("admin123"),
            role="admin"
        )
        db.add(admin_user)
    
    # Create test user
    test_user = db.query(User).filter(User.username == "user").first()
    if not test_user:
        test_user = User(
            username="user",
            email="user@lnmt.local",
            hashed_password=hash_password("user123"),
            role="user"
        )
        db.add(test_user)
    
    # Sample devices
    devices = [
        {"hostname": "router-01", "ip": "192.168.1.1", "mac": "00:11:22:33:44:55", "type": "router", "vlan": 1},
        {"hostname": "switch-01", "ip": "192.168.1.10", "mac": "00:11:22:33:44:56", "type": "switch", "vlan": 1},
        {"hostname": "server-01", "ip": "192.168.10.50", "mac": "00:11:22:33:44:57", "type": "server", "vlan": 10},
        {"hostname": "workstation-01", "ip": "192.168.20.100", "mac": "00:11:22:33:44:58", "type": "workstation", "vlan": 20},
    ]
    
    for device_data in devices:
        existing = db.query(Device).filter(Device.hostname == device_data["hostname"]).first()
        if not existing:
            device = Device(
                hostname=device_data["hostname"],
                ip_address=device_data["ip"],
                mac_address=device_data["mac"],
                device_type=device_data["type"],
                status="online",
                vlan_id=device_data["vlan"]
            )
            db.add(device)
    
    # Sample VLANs
    vlans = [
        {"id": 1, "name": "Management", "desc": "Network management", "subnet": "192.168.1.0/24", "gw": "192.168.1.1"},
        {"id": 10, "name": "Servers", "desc": "Server network", "subnet": "192.168.10.0/24", "gw": "192.168.10.1"},
        {"id": 20, "name": "Workstations", "desc": "User workstations", "subnet": "192.168.20.0/24", "gw": "192.168.20.1"},
    ]
    
    for vlan_data in vlans:
        existing = db.query(VLANConfig).filter(VLANConfig.vlan_id == vlan_data["id"]).first()
        if not existing:
            vlan = VLANConfig(
                vlan_id=vlan_data["id"],
                name=vlan_data["name"],
                description=vlan_data["desc"],
                subnet=vlan_data["subnet"],
                gateway=vlan_data["gw"]
            )
            db.add(vlan)
    
    db.commit()

# Initialize mock data on startup
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        generate_mock_data(db)
    finally:
        db.close()

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Dashboard home page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request):
    """Devices management page"""
    return templates.TemplateResponse("devices.html", {"request": request})

@app.get("/vlans", response_class=HTMLResponse)
async def vlans_page(request: Request):
    """VLAN management page"""
    return templates.TemplateResponse("vlans.html", {"request": request})

@app.get("/dns", response_class=HTMLResponse)
async def dns_page(request: Request):
    """DNS management page"""
    return templates.TemplateResponse("dns.html", {"request": request})

@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request):
    """Alerts page"""
    return templates.TemplateResponse("alerts.html", {"request": request})

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    return templates.TemplateResponse("config.html", {"request": request})

# Authentication API Routes
@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    """Register new user (admin only)"""
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }

# Dashboard API Routes
@app.get("/api/dashboard/summary")
async def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get dashboard summary data"""
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    total_alerts = db.query(NetworkAlert).filter(NetworkAlert.resolved == False).count()
    total_vlans = db.query(VLANConfig).filter(VLANConfig.is_active == True).count()
    
    # Recent alerts
    recent_alerts = db.query(NetworkAlert).filter(NetworkAlert.resolved == False).order_by(NetworkAlert.timestamp.desc()).limit(5).all()
    
    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": total_devices - online_devices,
        "total_alerts": total_alerts,
        "total_vlans": total_vlans,
        "recent_alerts": [
            {
                "id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat()
            } for alert in recent_alerts
        ]
    }

# Device API Routes
@app.get("/api/devices")
async def get_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all devices"""
    devices = db.query(Device).all()
    return [
        {
            "id": device.id,
            "hostname": device.hostname,
            "ip_address": device.ip_address,
            "mac_address": device.mac_address,
            "device_type": device.device_type,
            "status": device.status,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "vlan_id": device.vlan_id
        } for device in devices
    ]

@app.post("/api/devices")
async def create_device(device_data: DeviceCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("user"))):
    """Create new device"""
    device = Device(**device_data.dict())
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"message": "Device created successfully", "device_id": device.id}

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("user"))):
    """Delete device"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}

# VLAN API Routes
@app.get("/api/vlans")
async def get_vlans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all VLANs"""
    vlans = db.query(VLANConfig).all()
    return [
        {
            "id": vlan.id,
            "vlan_id": vlan.vlan_id,
            "name": vlan.name,
            "description": vlan.description,
            "subnet": vlan.subnet,
            "gateway": vlan.gateway,
            "is_active": vlan.is_active
        } for vlan in vlans
    ]

@app.post("/api/vlans")
async def create_vlan(vlan_data: VLANCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("user"))):
    """Create new VLAN"""
    existing = db.query(VLANConfig).filter(VLANConfig.vlan_id == vlan_data.vlan_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="VLAN ID already exists")
    
    vlan = VLANConfig(**vlan_data.dict())
    db.add(vlan)
    db.commit()
    return {"message": "VLAN created successfully"}

# DNS API Routes
@app.get("/api/dns")
async def get_dns_records(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all DNS records"""
    records = db.query(DNSRecord).all()
    return [
        {
            "id": record.id,
            "domain": record.domain,
            "record_type": record.record_type,
            "value": record.value,
            "ttl": record.ttl,
            "is_active": record.is_active
        } for record in records
    ]

@app.post("/api/dns")
async def create_dns_record(record_data: DNSRecordCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("user"))):
    """Create new DNS record"""
    record = DNSRecord(**record_data.dict())
    db.add(record)
    db.commit()
    return {"message": "DNS record created successfully"}

# Alerts API Routes
@app.get("/api/alerts")
async def get_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all alerts"""
    alerts = db.query(NetworkAlert).order_by(NetworkAlert.timestamp.desc()).all()
    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "source_ip": alert.source_ip,
            "timestamp": alert.timestamp.isoformat(),
            "resolved": alert.resolved
        } for alert in alerts
    ]

@app.put("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("user"))):
    """Resolve an alert"""
    alert = db.query(NetworkAlert).filter(NetworkAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.resolved = True
    db.commit()
    return {"message": "Alert resolved successfully"}

# Bandwidth/Statistics API Routes
@app.get("/api/stats/bandwidth")
async def get_bandwidth_stats(hours: int = 24, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get bandwidth statistics"""
    since = datetime.utcnow() - timedelta(hours=hours)
    stats = db.query(BandwidthUsage).filter(BandwidthUsage.timestamp >= since).all()
    
    return [
        {
            "interface": stat.interface,
            "rx_bytes": stat.rx_bytes,
            "tx_bytes": stat.tx_bytes,
            "timestamp": stat.timestamp.isoformat()
        } for stat in stats
    ]

# Configuration API Routes
@app.get("/api/config/lnmt")
async def get_lnmt_config(current_user: User = Depends(require_role("admin"))):
    """Get LNMT configuration"""
    # Mock configuration - in real implementation, read from lnmt.conf
    return {
        "network_interface": "eth0",
        "monitoring_interval": 60,
        "alert_email": "admin@lnmt.local",
        "log_level": "INFO",
        "backup_enabled": True,
        "backup_location": "/var/backups/lnmt"
    }

@app.put("/api/config/lnmt")
async def update_lnmt_config(config_data: dict, current_user: User = Depends(require_role("admin"))):
    """Update LNMT configuration"""
    # Mock update - in real implementation, write to lnmt.conf
    return {"message": "Configuration updated successfully"}

# WebSocket for real-time updates (basic implementation)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await websocket.accept()
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(30)
            await websocket.send_json({
                "type": "health_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"status": "healthy"}
            })
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)