
-- Extend DB with traffic/session support
CREATE TABLE IF NOT EXISTS dns_whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS app_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS app_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    app_id INTEGER,
    FOREIGN KEY (app_id) REFERENCES app_categories(id)
);

CREATE TABLE IF NOT EXISTS vlan_thresholds (
    vlan_id INTEGER PRIMARY KEY,
    threshold_kbps INTEGER NOT NULL,
    time_window_secs INTEGER NOT NULL,
    session_limit_secs INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    vlan TEXT NOT NULL,
    ip TEXT NOT NULL,
    hostname TEXT,
    app TEXT,
    seconds_used INTEGER DEFAULT 0
);
