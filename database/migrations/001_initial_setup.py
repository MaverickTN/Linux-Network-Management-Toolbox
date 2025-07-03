#!/usr/bin/env python3
"""
LNMT Database Migration: 001_initial_setup
Initial database setup and schema creation
"""

import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import mysql.connector
from pathlib import Path

# Migration metadata
MIGRATION_ID = "001_initial_setup"
MIGRATION_NAME = "Initial Database Setup"
MIGRATION_TIMESTAMP = "20240101000000"

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """Handle database migrations for LNMT"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.db_type = db_config.get('type', 'postgresql')
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            if self.db_type == 'postgresql':
                self.connection = psycopg2.connect(
                    host=self.db_config['host'],
                    port=self.db_config.get('port', 5432),
                    database=self.db_config['database'],
                    user=self.db_config['user'],
                    password=self.db_config['password']
                )
                self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            elif self.db_type == 'mysql':
                self.connection = mysql.connector.connect(
                    host=self.db_config['host'],
                    port=self.db_config.get('port', 3306),
                    database=self.db_config['database'],
                    user=self.db_config['user'],
                    password=self.db_config['password']
                )
            self.cursor = self.connection.cursor()
            logger.info(f"Connected to {self.db_type} database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            
    def check_migration_exists(self):
        """Check if migration table exists and if this migration has run"""
        try:
            # Create migrations table if it doesn't exist
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_id VARCHAR(255) UNIQUE NOT NULL,
                migration_name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rollback_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'completed'
            );
            """
            self.cursor.execute(create_table_sql)
            
            # Check if this migration has already been applied
            check_sql = "SELECT COUNT(*) FROM schema_migrations WHERE migration_id = %s"
            self.cursor.execute(check_sql, (MIGRATION_ID,))
            result = self.cursor.fetchone()
            return result[0] > 0
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False
            
    def record_migration(self, status='completed'):
        """Record migration execution"""
        try:
            insert_sql = """
            INSERT INTO schema_migrations (migration_id, migration_name, status)
            VALUES (%s, %s, %s)
            """
            self.cursor.execute(insert_sql, (MIGRATION_ID, MIGRATION_NAME, status))
            logger.info(f"Migration {MIGRATION_ID} recorded as {status}")
        except Exception as e:
            logger.error(f"Error recording migration: {e}")
            
    def up(self):
        """Run forward migration"""
        logger.info(f"Running migration: {MIGRATION_NAME}")
        
        try:
            # Read and execute the schema SQL file
            schema_path = Path(__file__).parent / 'schema.sql'
            if not schema_path.exists():
                # If schema.sql is in parent directory
                schema_path = Path(__file__).parent.parent / 'schema.sql'
                
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                    
                # Execute the schema
                if self.db_type == 'postgresql':
                    self.cursor.execute(schema_sql)
                else:
                    # For MySQL, we need to execute statements one by one
                    statements = schema_sql.split(';')
                    for statement in statements:
                        if statement.strip():
                            self.cursor.execute(statement)
                            
                logger.info("Database schema created successfully")
            else:
                logger.error("schema.sql file not found")
                raise FileNotFoundError("schema.sql not found")
                
            # Additional setup specific to migration
            self._create_default_data()
            
            # Record successful migration
            self.record_migration('completed')
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.record_migration('failed')
            raise
            
    def down(self):
        """Rollback migration"""
        logger.info(f"Rolling back migration: {MIGRATION_NAME}")
        
        try:
            # Drop all tables in reverse order
            tables = [
                'audit_logs', 'integrations', 'themes', 'report_schedules',
                'health_checks', 'backup_history', 'scheduled_jobs',
                'device_vlan_assignments', 'api_keys', 'user_sessions',
                'vlans', 'devices', 'users', 'system_config'
            ]
            
            for table in tables:
                drop_sql = f"DROP TABLE IF EXISTS {table} CASCADE"
                self.cursor.execute(drop_sql)
                logger.info(f"Dropped table: {table}")
                
            # Update migration record
            update_sql = """
            UPDATE schema_migrations 
            SET rollback_at = CURRENT_TIMESTAMP, status = 'rolled_back'
            WHERE migration_id = %s
            """
            self.cursor.execute(update_sql, (MIGRATION_ID,))
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
            
    def _create_default_data(self):
        """Create additional default data not in schema.sql"""
        try:
            # Add default network device types
            device_types = [
                ('switch', 'Network Switch'),
                ('router', 'Network Router'),
                ('firewall', 'Firewall/Security Device'),
                ('wireless_ap', 'Wireless Access Point'),
                ('server', 'Server'),
                ('workstation', 'Workstation'),
                ('printer', 'Network Printer'),
                ('iot', 'IoT Device'),
                ('unknown', 'Unknown Device Type')
            ]
            
            # Create device types lookup table
            create_lookup_sql = """
            CREATE TABLE IF NOT EXISTS device_types (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                icon VARCHAR(50),
                color VARCHAR(7)
            );
            """
            self.cursor.execute(create_lookup_sql)
            
            # Insert device types
            for code, name in device_types:
                insert_sql = """
                INSERT INTO device_types (code, name) 
                VALUES (%s, %s)
                ON CONFLICT (code) DO NOTHING
                """
                self.cursor.execute(insert_sql, (code, name))
                
            logger.info("Default data created successfully")
            
        except Exception as e:
            logger.error(f"Error creating default data: {e}")
            
def main():
    """Main migration execution"""
    # Get database config from environment or config file
    db_config = {
        'type': os.getenv('DB_TYPE', 'postgresql'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'lnmt_db'),
        'user': os.getenv('DB_USER', 'lnmt_user'),
        'password': os.getenv('DB_PASSWORD', 'lnmt_password')
    }
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    migration = DatabaseMigration(db_config)
    
    try:
        migration.connect()
        
        # Check if migration already exists
        if migration.check_migration_exists():
            logger.info(f"Migration {MIGRATION_ID} already applied. Skipping...")
            return
            
        # Run the migration
        if len(sys.argv) > 1 and sys.argv[1] == 'down':
            migration.down()
        else:
            migration.up()
            
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        migration.disconnect()
        
if __name__ == "__main__":
    main()