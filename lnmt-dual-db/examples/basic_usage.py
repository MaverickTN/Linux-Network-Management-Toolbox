#!/usr/bin/env python3
"""
LNMT Dual-Database Basic Usage Example
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from lnmt_db import initialize_lnmt_database

def main():
    """Basic usage example"""
    print("Initializing LNMT dual-database...")
ECHO is off.
    # Initialize database
    db = initialize_lnmt_database()
ECHO is off.
    # Configuration management
    print("Setting configuration...")
    db.set_config('system.debug', True, 'boolean', 'Enable debug mode')
    debug_mode = db.get_config('system.debug', False)
    print(f"Debug mode: {debug_mode}")
ECHO is off.
    # Tool management
    print("Configuring tools...")
    db.set_tool_path('nginx', '/usr/sbin/nginx', '/etc/nginx/nginx.conf')
    nginx_config = db.get_tool_path('nginx')
    print(f"Nginx config: {nginx_config}")
ECHO is off.
    # Service management
    print("Configuring services...")
    db.set_service_config('nginx', enabled=True, port=80, auto_start=True)
    service_config = db.get_service_config('nginx')
    print(f"Service config: {service_config}")
ECHO is off.
    # Operational data
    print("Logging operational data...")
    db.log_device('00:11:22:33:44:55', '192.168.1.100', 'server-01')
    db.log_system_event('INFO', 'system', 'Example event logged')
ECHO is off.
    print("Example completed successfully!")
ECHO is off.
    # Close database
    db.close()

if __name__ == '__main__':
    main()
