
CREATE TABLE IF NOT EXISTS blacklist_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vlan TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT
);
