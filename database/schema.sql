-- LNMT Database Schema
-- Version: 2.0.0
-- Database: PostgreSQL 12+ (MySQL 8+ compatible with minor syntax changes)

-- Create database if not exists
-- CREATE DATABASE IF NOT EXISTS lnmt_db;

-- Extensions (PostgreSQL specific)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop existing tables (careful in production!)
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS device_vlan_assignments CASCADE;
DROP TABLE IF EXISTS scheduled_jobs CASCADE;
DROP TABLE IF EXISTS backup_history CASCADE;
DROP TABLE IF EXISTS health_checks CASCADE;
DROP TABLE IF EXISTS report_schedules CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS vlans CASCADE;
DROP TABLE IF EXISTS devices CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS system_config CASCADE;
DROP TABLE IF EXISTS themes CASCADE;
DROP TABLE IF EXISTS integrations CASCADE;

-- System Configuration Table
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    type VARCHAR(50) NOT NULL DEFAULT 'string', -- string, integer, boolean, json
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- admin, operator, user, viewer
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    last_login TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API Keys Table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Sessions Table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Devices Table
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hostname VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    mac_address MACADDR,
    device_type VARCHAR(100), -- switch, router, firewall, server, workstation
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(255),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active', -- active, inactive, maintenance, decommissioned
    snmp_community VARCHAR(255), -- encrypted
    snmp_version VARCHAR(10) DEFAULT 'v2c',
    ssh_username VARCHAR(100),
    ssh_password VARCHAR(255), -- encrypted
    ssh_key_id UUID,
    last_seen TIMESTAMP WITH TIME ZONE,
    uptime_seconds BIGINT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ip_address),
    UNIQUE(hostname)
);

-- VLANs Table
CREATE TABLE vlans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vlan_id INTEGER NOT NULL CHECK (vlan_id >= 1 AND vlan_id <= 4094),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    subnet CIDR,
    gateway INET,
    dns_servers INET[],
    dhcp_enabled BOOLEAN DEFAULT FALSE,
    dhcp_start INET,
    dhcp_end INET,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vlan_id)
);

-- Device VLAN Assignments
CREATE TABLE device_vlan_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    vlan_id UUID REFERENCES vlans(id) ON DELETE CASCADE,
    port_number VARCHAR(50),
    port_mode VARCHAR(20) DEFAULT 'access', -- access, trunk
    tagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, vlan_id, port_number)
);

-- Scheduled Jobs Table
CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    job_type VARCHAR(100) NOT NULL, -- backup, report, health_check, custom
    schedule VARCHAR(100) NOT NULL, -- cron expression
    command TEXT,
    parameters JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    last_status VARCHAR(50), -- success, failed, running
    last_output TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 3600,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backup History Table
CREATE TABLE backup_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    backup_type VARCHAR(50) NOT NULL, -- full, incremental, config
    source VARCHAR(255) NOT NULL,
    destination VARCHAR(500) NOT NULL,
    size_bytes BIGINT,
    status VARCHAR(50) NOT NULL, -- running, completed, failed
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    retention_days INTEGER DEFAULT 30,
    is_encrypted BOOLEAN DEFAULT TRUE,
    checksum VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id)
);

-- Health Checks Table
CREATE TABLE health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    check_type VARCHAR(100) NOT NULL, -- ping, http, port, snmp, custom
    target VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- healthy, unhealthy, warning
    response_time_ms INTEGER,
    status_code INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Report Schedules Table
CREATE TABLE report_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    schedule VARCHAR(100) NOT NULL, -- cron expression
    recipients TEXT[], -- email addresses
    format VARCHAR(20) DEFAULT 'pdf', -- pdf, csv, html, json
    parameters JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    last_generated TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Themes Table
CREATE TABLE themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,
    author VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    config JSONB NOT NULL,
    assets_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Integrations Table
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL, -- webhook, api, database, ldap, syslog
    config JSONB NOT NULL, -- encrypted sensitive data
    is_active BOOLEAN DEFAULT TRUE,
    last_sync TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(50),
    error_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    request_body JSONB,
    response_code INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_last_seen ON devices(last_seen);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_health_checks_checked_at ON health_checks(checked_at);
CREATE INDEX idx_health_checks_status ON health_checks(status);
CREATE INDEX idx_scheduled_jobs_next_run ON scheduled_jobs(next_run) WHERE is_active = TRUE;
CREATE INDEX idx_backup_history_created_at ON backup_history(started_at);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- Updated timestamp triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vlans_updated_at BEFORE UPDATE ON vlans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_themes_updated_at BEFORE UPDATE ON themes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_integrations_updated_at BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Initial data
INSERT INTO system_config (key, value, type, description) VALUES
    ('app_name', 'LNMT', 'string', 'Application name'),
    ('app_version', '2.0.0', 'string', 'Application version'),
    ('maintenance_mode', 'false', 'boolean', 'Maintenance mode flag'),
    ('session_timeout', '3600', 'integer', 'Session timeout in seconds'),
    ('max_login_attempts', '5', 'integer', 'Maximum login attempts before lockout'),
    ('lockout_duration', '300', 'integer', 'Account lockout duration in seconds'),
    ('password_min_length', '12', 'integer', 'Minimum password length'),
    ('password_require_special', 'true', 'boolean', 'Require special characters in password'),
    ('backup_retention_days', '30', 'integer', 'Default backup retention period'),
    ('audit_retention_days', '90', 'integer', 'Audit log retention period');

-- Default admin user (password: ChangeMeNow123!)
-- IMPORTANT: Change this password immediately after installation
INSERT INTO users (username, email, password_hash, first_name, last_name, role, is_superuser) VALUES
    ('admin', 'admin@lnmt.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGH1IDbJYma', 'System', 'Administrator', 'admin', TRUE);

-- Default theme
INSERT INTO themes (name, display_name, description, version, author, is_active, is_default, config) VALUES
    ('default', 'Default Theme', 'LNMT default theme', '1.0.0', 'LNMT Team', TRUE, TRUE, 
    '{"colors": {"primary": "#007bff", "secondary": "#6c757d", "success": "#28a745", "danger": "#dc3545", "warning": "#ffc107", "info": "#17a2b8"}}');

-- Grant permissions (PostgreSQL specific)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lnmt_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lnmt_user;
-- GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO lnmt_user;