# LNMT Backup and Restore Procedures

## Overview

This document provides comprehensive procedures for backing up and restoring your LNMT installation. Regular backups are essential for disaster recovery and data protection.

## What to Backup

### Critical Components
1. **Database** - All configuration and operational data
2. **Configuration Files** - System and application settings
3. **Encryption Keys** - SSL certificates and encryption keys
4. **Custom Themes** - User-created themes and assets
5. **File Uploads** - Reports, backups, and user uploads
6. **Logs** - Audit trails and historical data (optional)

### Backup Locations

| Component | Default Location | Priority |
|-----------|-----------------|----------|
| PostgreSQL Database | `/var/lib/postgresql/` | Critical |
| Configuration | `/etc/lnmt/` | Critical |
| Data Files | `/var/lib/lnmt/` | Critical |
| Backup Archives | `/var/backups/lnmt/` | High |
| Logs | `/var/log/lnmt/` | Medium |
| Themes | `/etc/lnmt/themes/` | Medium |

## Backup Strategies

### 1. Full System Backup (Recommended)

Comprehensive backup of all LNMT components.

```bash
#!/bin/bash
# Full LNMT Backup Script

BACKUP_DIR="/var/backups/lnmt"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="lnmt_full_backup_${TIMESTAMP}"

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 1. Backup PostgreSQL database
echo "Backing up database..."
sudo -u postgres pg_dump lnmt_db | gzip > "${BACKUP_DIR}/${BACKUP_NAME}/database.sql.gz"

# 2. Backup configuration
echo "Backing up configuration..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/config.tar.gz" -C / etc/lnmt

# 3. Backup data files
echo "Backing up data files..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/data.tar.gz" -C / var/lib/lnmt

# 4. Backup logs (optional)
echo "Backing up logs..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/logs.tar.gz" -C / var/log/lnmt

# 5. Create backup manifest
cat > "${BACKUP_DIR}/${BACKUP_NAME}/manifest.txt" << EOF
Backup Date: $(date)
LNMT Version: $(cat /opt/lnmt/VERSION)
Database Size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}/database.sql.gz" | cut -f1)
Config Size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}/config.tar.gz" | cut -f1)
Data Size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}/data.tar.gz" | cut -f1)
EOF

# 6. Create final archive
echo "Creating final archive..."
tar -czf "${BACKUP_DIR}/lnmt_full_backup_${TIMESTAMP}.tar.gz" \
    -C "${BACKUP_DIR}" "${BACKUP_NAME}"

# 7. Cleanup temporary files
rm -rf "${BACKUP_DIR}/${BACKUP_NAME}"

echo "Backup completed: ${BACKUP_DIR}/lnmt_full_backup_${TIMESTAMP}.tar.gz"
```

### 2. Incremental Database Backup

For frequent database-only backups.

```bash
#!/bin/bash
# Incremental Database Backup

BACKUP_DIR="/var/backups/lnmt/incremental"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "${BACKUP_DIR}"

# Backup with custom format for faster restore
sudo -u postgres pg_dump -Fc lnmt_db > "${BACKUP_DIR}/db_${TIMESTAMP}.dump"

# Keep only last 7 days of incremental backups
find "${BACKUP_DIR}" -name "db_*.dump" -mtime +7 -delete
```

### 3. Automated Backup via LNMT

Configure automated backups in `/etc/lnmt/config.yml`:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention_days: 30
  destinations:
    local:
      enabled: true
      path: "/var/backups/lnmt"
    s3:
      enabled: true
      bucket: "my-lnmt-backups"
      region: "us-east-1"
      prefix: "production/"
```

## Restore Procedures

### 1. Full System Restore

Complete restoration from full backup.

```bash
#!/bin/bash
# Full LNMT Restore Script

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/lnmt_restore"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

# 1. Stop LNMT services
echo "Stopping LNMT services..."
systemctl stop lnmt lnmt-scheduler lnmt-health

# 2. Extract backup
echo "Extracting backup..."
mkdir -p "${RESTORE_DIR}"
tar -xzf "${BACKUP_FILE}" -C "${RESTORE_DIR}"

BACKUP_NAME=$(ls "${RESTORE_DIR}")

# 3. Restore database
echo "Restoring database..."
gunzip -c "${RESTORE_DIR}/${BACKUP_NAME}/database.sql.gz" | sudo -u postgres psql lnmt_db

# 4. Restore configuration
echo "Restoring configuration..."
tar -xzf "${RESTORE_DIR}/${BACKUP_NAME}/config.tar.gz" -C /

# 5. Restore data files
echo "Restoring data files..."
tar -xzf "${RESTORE_DIR}/${BACKUP_NAME}/data.tar.gz" -C /

# 6. Restore logs (optional)
if [ -f "${RESTORE_DIR}/${BACKUP_NAME}/logs.tar.gz" ]; then
    echo "Restoring logs..."
    tar -xzf "${RESTORE_DIR}/${BACKUP_NAME}/logs.tar.gz" -C /
fi

# 7. Fix permissions
echo "Fixing permissions..."
chown -R lnmt:lnmt /etc/lnmt /var/lib/lnmt /var/log/lnmt

# 8. Start services
echo "Starting LNMT services..."
systemctl start lnmt lnmt-scheduler lnmt-health

# 9. Cleanup
rm -rf "${RESTORE_DIR}"

echo "Restore completed successfully!"
```

### 2. Database-Only Restore

Restore only the database from backup.

```bash
#!/bin/bash
# Database Restore

BACKUP_FILE="$1"

# Stop services
systemctl stop lnmt lnmt-scheduler lnmt-health

# Drop and recreate database
sudo -u postgres dropdb lnmt_db
sudo -u postgres createdb lnmt_db

# Restore from custom format
sudo -u postgres pg_restore -d lnmt_db "${BACKUP_FILE}"

# Start services
systemctl start lnmt lnmt-scheduler lnmt-health
```

### 3. Point-in-Time Recovery

For PostgreSQL with WAL archiving enabled:

```bash
# Stop PostgreSQL
systemctl stop postgresql

# Restore base backup
rm -rf /var/lib/postgresql/12/main/*
tar -xzf /backups/base_backup.tar.gz -C /var/lib/postgresql/12/main/

# Create recovery configuration
cat > /var/lib/postgresql/12/main/recovery.conf << EOF
restore_command = 'cp /archive/%f %p'
recovery_target_time = '2024-01-15 14:30:00'
EOF

# Start PostgreSQL
systemctl start postgresql
```

## Backup Verification

### 1. Automated Verification Script

```bash
#!/bin/bash
# Backup Verification Script

BACKUP_FILE="$1"
VERIFY_DIR="/tmp/backup_verify"

echo "Verifying backup: ${BACKUP_FILE}"

# Extract and check
mkdir -p "${VERIFY_DIR}"
if tar -tzf "${BACKUP_FILE}" > /dev/null 2>&1; then
    echo "✓ Backup archive is valid"
else
    echo "✗ Backup archive is corrupted"
    exit 1
fi

# Extract and verify components
tar -xzf "${BACKUP_FILE}" -C "${VERIFY_DIR}"

# Check database dump
if gunzip -t "${VERIFY_DIR}/*/database.sql.gz" 2>/dev/null; then
    echo "✓ Database backup is valid"
else
    echo "✗ Database backup is corrupted"
fi

# Cleanup
rm -rf "${VERIFY_DIR}"
```

### 2. Test Restore Procedure

Periodically test restore procedures in a staging environment:

1. Create staging environment
2. Copy production backup
3. Perform full restore
4. Verify functionality
5. Document any issues

## Remote Backup Options

### 1. Amazon S3

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Upload backup
aws s3 cp /var/backups/lnmt/backup.tar.gz s3://my-bucket/lnmt-backups/
```

### 2. SFTP/SSH

```bash
# Backup to remote server
scp /var/backups/lnmt/backup.tar.gz user@backup-server:/backups/lnmt/
```

### 3. Rsync

```bash
# Sync backups to remote server
rsync -avz --delete /var/backups/lnmt/ user@backup-server:/backups/lnmt/
```

## Backup Best Practices

### 1. Schedule Regular Backups
- **Database**: Daily incremental, weekly full
- **Configuration**: On change, minimum weekly
- **Full System**: Weekly or monthly

### 2. Follow 3-2-1 Rule
- 3 copies of important data
- 2 different storage types
- 1 offsite backup

### 3. Test Restores Regularly
- Monthly restore tests
- Document restore times
- Update procedures as needed

### 4. Monitor Backup Status
- Check backup job completion
- Verify backup sizes
- Alert on failures

### 5. Secure Your Backups
- Encrypt sensitive backups
- Restrict access permissions
- Use secure transfer methods

## Disaster Recovery Plan

### 1. Recovery Time Objectives (RTO)
- **Critical**: Database and core config - 1 hour
- **Important**: Full system restore - 4 hours
- **Standard**: Complete with history - 8 hours

### 2. Recovery Point Objectives (RPO)
- **Database**: Maximum 24 hours data loss
- **Configuration**: Maximum 7 days
- **Logs**: Best effort

### 3. Emergency Contacts
- System Administrator: [Contact Info]
- Database Administrator: [Contact Info]
- Network Administrator: [Contact Info]

## Troubleshooting

### Common Issues

1. **Backup Fails with Permission Denied**
   ```bash
   # Fix permissions
   sudo chown -R lnmt:lnmt /var/backups/lnmt
   sudo chmod 750 /var/backups/lnmt
   ```

2. **Database Backup Too Large**
   ```bash
   # Use compression and custom format
   pg_dump -Fc -Z9 lnmt_db > backup.dump
   ```

3. **Restore Fails with Version Mismatch**
   ```bash
   # Check PostgreSQL versions
   pg_dump --version
   psql --version
   ```

4. **Insufficient Disk Space**
   ```bash
   # Check available space
   df -h /var/backups
   # Clean old backups
   find /var/backups/lnmt -mtime +30 -delete
   ```

## Backup Retention Policy

| Backup Type | Retention Period | Storage Location |
|-------------|-----------------|------------------|
| Daily Database | 7 days | Local |
| Weekly Full | 4 weeks | Local + Remote |
| Monthly Full | 12 months | Remote |
| Annual Archive | 7 years | Cold Storage |

## Compliance and Auditing

- Log all backup operations
- Maintain backup/restore audit trail
- Document data retention compliance
- Regular backup audit reviews