CREATE TABLE IF NOT EXISTS digest_report_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    recipient TEXT,
    report_type TEXT,
    delivery_method TEXT,
    status TEXT,
    error TEXT
);
