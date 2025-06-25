CREATE TABLE IF NOT EXISTS config_diff (
    id INTEGER PRIMARY KEY,
    filepath TEXT,
    timestamp TEXT,
    diff TEXT
);
