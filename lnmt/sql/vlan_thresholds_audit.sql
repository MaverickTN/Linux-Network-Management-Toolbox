CREATE TABLE IF NOT EXISTS vlan_thresholds_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vlan_id INTEGER,
    threshold_kbps INTEGER,
    description TEXT,
    action TEXT,
    user TEXT,
    timestamp TEXT
);