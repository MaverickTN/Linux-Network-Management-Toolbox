# LNMT System Requirements

## Minimum Hardware Requirements

### For Small Networks (up to 100 devices)
- **CPU**: 2 cores (2.0 GHz or higher)
- **RAM**: 4 GB
- **Storage**: 20 GB available space
- **Network**: 100 Mbps connection

### For Medium Networks (100-500 devices)
- **CPU**: 4 cores (2.5 GHz or higher)
- **RAM**: 8 GB
- **Storage**: 50 GB available space
- **Network**: 1 Gbps connection

### For Large Networks (500+ devices)
- **CPU**: 8+ cores (3.0 GHz or higher)
- **RAM**: 16 GB or more
- **Storage**: 100 GB or more available space
- **Network**: 1 Gbps connection (10 Gbps recommended)

## Operating System Requirements

### Supported Operating Systems
- **Ubuntu**: 20.04 LTS, 22.04 LTS
- **Debian**: 10 (Buster), 11 (Bullseye), 12 (Bookworm)
- **CentOS**: 7, 8 Stream
- **RHEL**: 7, 8, 9
- **Rocky Linux**: 8, 9
- **AlmaLinux**: 8, 9

### Docker Support
- Docker Engine 20.10 or higher
- Docker Compose 2.0 or higher

## Software Dependencies

### Required Software
- **Python**: 3.8, 3.9, 3.10, or 3.11
- **Database**: 
  - PostgreSQL 12+ (recommended)
  - MySQL 8.0+
  - MariaDB 10.5+
- **Redis**: 6.0+ (for caching and sessions)
- **Web Server** (optional but recommended):
  - Nginx 1.18+
  - Apache 2.4+

### Python Package Dependencies
See `requirements.txt` for the complete list. Key packages include:
- FastAPI or Flask
- SQLAlchemy
- Redis-py
- Celery
- Gunicorn/Uvicorn
- psycopg2-binary (for PostgreSQL)
- PyMySQL (for MySQL/MariaDB)

## Network Requirements

### Required Ports
- **8080**: Default LNMT web interface (configurable)
- **5432**: PostgreSQL database (if local)
- **3306**: MySQL/MariaDB database (if local)
- **6379**: Redis cache (if local)
- **443**: HTTPS (if SSL enabled)
- **80**: HTTP (for redirect to HTTPS)

### Firewall Rules
```bash
# Allow LNMT web interface
sudo ufw allow 8080/tcp

# Allow HTTPS (if configured)
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp

# Allow database connections (if remote)
# sudo ufw allow from <trusted_ip> to any port 5432
# sudo ufw allow from <trusted_ip> to any port 3306
# sudo ufw allow from <trusted_ip> to any port 6379
```

### Network Protocols Used
- **ICMP**: For ping-based device discovery
- **SNMP**: UDP 161 for device monitoring
- **SSH**: TCP 22 for device configuration
- **DNS**: UDP/TCP 53 for DNS management
- **Syslog**: UDP 514 for log collection (optional)

## Browser Requirements

### Supported Browsers
- **Chrome/Chromium**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

### Required Browser Features
- JavaScript enabled
- Cookies enabled
- WebSocket support (for real-time updates)
- Local storage support

## Performance Considerations

### Database Sizing
- **Device Records**: ~1 KB per device
- **Health Check History**: ~500 bytes per check
- **Audit Logs**: ~2 KB per log entry
- **Backup Metadata**: ~5 KB per backup

### Estimated Storage Growth
- Small network: ~1 GB per month
- Medium network: ~5 GB per month
- Large network: ~20 GB per month

### Memory Usage
- Base application: ~500 MB
- Per worker process: ~100 MB
- Redis cache: ~500 MB (configurable)
- Database connections: ~10 MB per connection

## Security Requirements

### SSL/TLS
- Valid SSL certificate (self-signed or CA-signed)
- TLS 1.2 or higher
- Strong cipher suites

### User Permissions
- Dedicated system user for LNMT service
- Restricted file permissions
- Database user with limited privileges

### SELinux/AppArmor
- Compatible with SELinux enforcing mode
- AppArmor profiles available

## Pre-Installation Checklist

### System Preparation
- [ ] Operating system updated
- [ ] Required ports available
- [ ] Sufficient disk space
- [ ] Network connectivity verified
- [ ] Time synchronization configured (NTP)

### Software Installation
- [ ] Python installed and verified
- [ ] Database server installed
- [ ] Redis server installed
- [ ] Required system packages installed

### Security Setup
- [ ] Firewall configured
- [ ] SELinux/AppArmor configured (if applicable)
- [ ] SSL certificates prepared (if using HTTPS)
- [ ] Strong passwords generated

### Database Preparation
- [ ] Database server running
- [ ] Database created
- [ ] Database user created with appropriate permissions
- [ ] Database backup strategy planned

## Scaling Recommendations

### Horizontal Scaling
- Load balancer (HAProxy, Nginx) for multiple LNMT instances
- Database replication for read scaling
- Redis Sentinel for high availability
- Shared storage for file uploads (NFS, S3)

### Vertical Scaling
- Increase CPU cores for parallel processing
- Add RAM for larger cache and more workers
- Use SSD storage for better I/O performance
- Upgrade network bandwidth for large deployments

## Monitoring Requirements

### Recommended Monitoring Tools
- **Prometheus**: For metrics collection
- **Grafana**: For visualization
- **ELK Stack**: For log aggregation
- **Nagios/Zabbix**: For infrastructure monitoring

### Key Metrics to Monitor
- CPU usage
- Memory usage
- Disk I/O and space
- Network bandwidth
- Database performance
- API response times
- Error rates