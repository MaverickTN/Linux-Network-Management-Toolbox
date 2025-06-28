CREATE TABLE IF NOT EXISTS backup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    type TEXT,
    target TEXT,
    status TEXT,
    filename TEXT,
    size INTEGER,
    retention_policy TEXT,
    run_by TEXT,
    error TEXT
);
