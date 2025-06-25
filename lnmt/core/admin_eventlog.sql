CREATE TABLE IF NOT EXISTS admin_eventlog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor TEXT,
    action TEXT NOT NULL,
    target TEXT,
    success INTEGER NOT NULL,
    details TEXT
);
