#!/usr/bin/env python3
"""
LNMT Database CLI
Command-line interface for database operations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from lnmt_db import initialize_lnmt_database, DatabaseCLI

def main():
    """Main CLI entry point"""
    db = initialize_lnmt_database()
    cli = DatabaseCLI(db)
ECHO is off.
    if len(sys.argv) > 1:
        command = sys.argv[1]
ECHO is off.
        if command == "config":
            cli.show_config()
        elif command == "list-tools":
            cli.list_tools()
        elif command == "list-services":
            cli.list_services()
        elif command == "migrate-to-sql":
            cli.migrate_to_sql()
        elif command == "sync":
            cli.sync_databases()
        elif command == "backup":
            backup_path = sys.argv[2] if len(sys.argv) > 2 else f"backup_{int^(time.time^(^)^)}.db"
            cli.backup_sqlite(backup_path)
        else:
            print("Available commands: config, list-tools, list-services, migrate-to-sql, sync, backup")
    else:
        cli.show_config()
ECHO is off.
    db.close()

if __name__ == '__main__':
    main()
