CREATE TABLE IF NOT EXISTS self_heal_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    module TEXT,
    action TEXT,
    status TEXT,
    attempts INTEGER,
    error TEXT,
    notified TEXT
);
