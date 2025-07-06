# LNMT Dual-Database Architecture

Robust dual-database system for Linux Network Management Toolbox with SQLite (always present) + optional SQL database (PostgreSQL/MySQL) for operational data.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│                 LNMT                    │
├─────────────────────────────────────────┤
│         Application Layer               │
├─────────────────────────────────────────┤
│         Database Manager                │
├─────────────┬───────────────────────────┤
│   SQLite    │      SQL Database         │
│ (Required)  │      (Optional)          │
│             │                          │
│ • Config    │ • Device Tracking        │
│ • Settings  │ • Session Data           │
│ • Tools     │ • Traffic Logs           │
│ • Users     │ • System Logs            │
│ • Secrets   │ • Performance Metrics    │
│ • Network   │ • Analytics              │
│ • QoS       │                          │
│ • Backups   │                          │
└─────────────┴───────────────────────────┘
```

## Quick Start

```bash
# Install and setup
sudo ./scripts/install.sh

# Initialize database
python core/lnmt_db.py init

# Basic usage
python -c "from core.lnmt_db import initialize_lnmt_database; db = initialize_lnmt_database(^); print('DB initialized'^)"
```

## Features

- ✅ **Dual Database Architecture**: SQLite (config) + SQL (operational)
- ✅ **Automatic Fallback**: SQL → SQLite when SQL unavailable
- ✅ **Migration Tools**: Bidirectional data migration
- ✅ **Backup System**: Automated backup and restore
- ✅ **CLI Management**: Complete command-line interface
- ✅ **Service Integration**: Systemd services with monitoring
- ✅ **Security Features**: Encrypted secrets, audit logging

## Project Structure

- `core/` - Core database management modules
- `config/` - Configuration templates and examples
- `scripts/` - Installation and management scripts
- `systemd/` - Systemd service files
- `docs/` - Complete documentation
- `examples/` - Usage examples and samples
- `tests/` - Test suite

See `docs/README_FULL.md` for comprehensive documentation.
