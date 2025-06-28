CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL,
    action TEXT NOT NULL,
    params TEXT DEFAULT '{}',
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    last_result TEXT
);

CREATE TABLE IF NOT EXISTS job_run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    run_time TEXT,
    result TEXT,
    output TEXT
);
