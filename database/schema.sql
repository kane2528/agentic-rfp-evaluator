PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    weight REAL NOT NULL CHECK(weight >= 0),
    max_score REAL NOT NULL CHECK(max_score > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS rfp_runs (
    rfp_run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    criteria_snapshot_json TEXT NOT NULL DEFAULT '[]',
    result_json TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS supplier_results (
    rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id) ON DELETE CASCADE,
    supplier_name TEXT NOT NULL,
    submission_date TEXT NOT NULL,
    experience_rating REAL NOT NULL,
    absolute_score REAL NOT NULL,
    ppi REAL NOT NULL,
    final_rank INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (rfp_run_id, supplier_name)
);

CREATE INDEX IF NOT EXISTS idx_runs_created_at ON rfp_runs(created_at DESC);
