#!/usr/bin/env python3
"""
LNMT Database Migration Example
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from lnmt_db import initialize_lnmt_database, DatabaseMigrator

def main():
    """Database migration example"""
    print("LNMT Database Migration Example")
ECHO is off.
    # Initialize database
    db = initialize_lnmt_database()
    migrator = DatabaseMigrator(db)
ECHO is off.
    # Migrate from SQLite to SQL
    print("Migrating operational data to SQL database...")
    if migrator.migrate_sqlite_to_sql():
        print("Migration to SQL completed successfully")
    else:
        print("Migration to SQL failed")
ECHO is off.
    # Sync databases
    print("Synchronizing databases...")
    if migrator.sync_databases():
        print("Database sync completed successfully")
    else:
        print("Database sync failed")
ECHO is off.
    db.close()

if __name__ == '__main__':
    main()
