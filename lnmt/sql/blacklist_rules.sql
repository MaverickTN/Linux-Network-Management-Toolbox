CREATE TABLE IF NOT EXISTS blacklist_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT,
    target TEXT,
    schedule TEXT,
    description TEXT,
    enabled INTEGER DEFAULT 1,
    hit_count INTEGER DEFAULT 0,
    last_triggered TEXT,
    user TEXT,
    created_at TEXT
);