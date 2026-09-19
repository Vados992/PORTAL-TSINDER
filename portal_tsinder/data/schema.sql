PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS artifacts (
    sha256 TEXT PRIMARY KEY, content BLOB NOT NULL, media_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, created_at TEXT NOT NULL,
    input_sha TEXT NOT NULL REFERENCES artifacts(sha256),
    result_sha TEXT NOT NULL REFERENCES artifacts(sha256),
    code_sha TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
    kind TEXT NOT NULL, payload TEXT NOT NULL, previous_sha TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS telemetry_segments (
    session_id TEXT NOT NULL, segment INTEGER NOT NULL, artifact_sha TEXT NOT NULL REFERENCES artifacts(sha256),
    PRIMARY KEY(session_id, segment)
);
CREATE TRIGGER IF NOT EXISTS immutable_artifacts_update BEFORE UPDATE ON artifacts
BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_artifacts_delete BEFORE DELETE ON artifacts
BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_events_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append only'); END;
CREATE TRIGGER IF NOT EXISTS immutable_events_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append only'); END;
