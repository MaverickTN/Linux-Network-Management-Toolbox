-- Table to store detection thresholds
CREATE TABLE IF NOT EXISTS detection_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

INSERT OR IGNORE INTO detection_settings (key, value, description) VALUES
('ping_window', '3', 'Ping detection window in seconds'),
('min_bytes_in', '1024', 'Minimum inbound bytes for host to be considered online'),
('min_bytes_out', '1024', 'Minimum outbound bytes for host to be considered online');
