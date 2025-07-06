# LNMT TC/QoS Module

Comprehensive Traffic Control and Quality of Service management for Linux Network Management Toolbox.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# List network interfaces
python cli/tcctl.py interfaces

# Create HTB policy interactively
python cli/tcctl.py htb-wizard

# Start web interface
python web/tc_web_api.py
```

## Project Structure

- `src/` - Core service modules
- `cli/` - Command-line interface
- `web/` - Web API and dashboard  
- `tests/` - Test suite
- `docs/` - Documentation and examples
- `examples/` - Sample policy configurations
- `scripts/` - Installation and utility scripts

## Features

- ✅ Complete TC/QoS policy management
- ✅ Web dashboard with real-time monitoring
- ✅ Command-line interface (tcctl)
- ✅ Policy import/export (JSON/YAML)
- ✅ Safety features with backup/rollback
- ✅ Integration with LNMT dual-database
- ✅ Comprehensive test suite

## Requirements

- Python 3.8+
- Linux with iproute2 (tc command)
- Root privileges for TC operations

See `docs/` for complete documentation.
