"""SQLite storage for normalized activities and recovery metrics.

Activities are deduplicated on (date, start_time, sport) so re-running the
Sunday pipeline over an overlapping export only inserts new rows. Rows read from
raw activity files (source_id "file:<name>") are replaced by the activities.csv
row once a CSV lists that file.
"""
import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    source_id TEXT,
    date TEXT NOT NULL,            -- YYYY-MM-DD (local)
    start_time TEXT NOT NULL,      -- HH:MM:SS (local)
    sport TEXT NOT NULL,           -- swim | bike | run | strength | other
    raw_type TEXT,
    name TEXT,
    duration_s REAL,               -- moving time in seconds
    elapsed_s REAL,
    distance_m REAL,
    elevation_m REAL,
    avg_hr REAL,
    max_hr REAL,
    avg_power REAL,
    weighted_power REAL,
    avg_speed_mps REAL,
    perceived_exertion REAL,
    strava_relative_effort REAL,
    tss REAL,                      -- computed training stress estimate
    best20_hr REAL,                -- highest 20-min mean HR, from the raw file's HR stream
    hr_checked INTEGER DEFAULT 0,  -- 1 once the raw file was looked at for best20_hr
    UNIQUE(date, start_time, sport)
);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);

CREATE TABLE IF NOT EXISTS recovery (
    date TEXT NOT NULL,
    metric TEXT NOT NULL,          -- resting_hr | hrv | sleep_hours | vo2max
    value REAL NOT NULL,
    PRIMARY KEY (date, metric)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS plans (
    week_start TEXT PRIMARY KEY,   -- Monday, YYYY-MM-DD
    plan_json TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
"""

# Columns added after the first release; CREATE TABLE IF NOT EXISTS does not add them
# to an existing database.
ADDED_COLUMNS = {"activities": [("best20_hr", "REAL"), ("hr_checked", "INTEGER DEFAULT 0")]}


def _migrate(conn):
    for table, cols in ADDED_COLUMNS.items():
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in cols:
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


ACTIVITY_COLUMNS = [
    "source_id", "date", "start_time", "sport", "raw_type", "name", "duration_s",
    "elapsed_s", "distance_m", "elevation_m", "avg_hr", "max_hr", "avg_power",
    "weighted_power", "avg_speed_mps", "perceived_exertion", "strava_relative_effort",
]


def upsert_activities(conn, rows):
    """Insert new activities, skipping duplicates. Returns count inserted."""
    cols = ", ".join(ACTIVITY_COLUMNS)
    placeholders = ", ".join("?" for _ in ACTIVITY_COLUMNS)
    inserted = 0
    for r in rows:
        if r.get("filename"):
            replaced = conn.execute("DELETE FROM activities WHERE source_id = ?", (f"file:{r['filename']}",)).rowcount
            inserted -= replaced  # an upgrade from file row to CSV row is not a new activity
        cur = conn.execute(
            f"INSERT OR IGNORE INTO activities ({cols}) VALUES ({placeholders})",
            [r.get(c) for c in ACTIVITY_COLUMNS],
        )
        inserted += cur.rowcount
    return inserted


def import_state(conn):
    """(source ids of rows read from raw files, newest (date, start_time) imported
    from an activities.csv) - lets load_strava skip files it has already covered."""
    file_ids = {r[0] for r in conn.execute("SELECT source_id FROM activities WHERE source_id LIKE 'file:%'")}
    newest = conn.execute("SELECT date, start_time FROM activities WHERE source_id NOT LIKE 'file:%' "
                          "ORDER BY date DESC, start_time DESC LIMIT 1").fetchone()
    return file_ids, (tuple(newest) if newest else None)


def pending_hr_streams(conn):
    """Run and bike activities long enough for a 20-min HR window whose raw file
    has not been read yet."""
    return [dict(r) for r in conn.execute(
        "SELECT id, source_id, date, start_time, sport FROM activities "
        "WHERE sport IN ('run', 'bike') AND duration_s >= 1200 AND NOT hr_checked")]


def save_best_hr(conn, best_by_id):
    """best_by_id: {activity id: best 20-min HR or None}. Marks each row as checked."""
    conn.executemany("UPDATE activities SET best20_hr = ?, hr_checked = 1 WHERE id = ?",
                     [(v, k) for k, v in best_by_id.items()])


def upsert_recovery(conn, rows):
    """rows: iterable of (date, metric, value). Later values overwrite."""
    conn.executemany(
        "INSERT OR REPLACE INTO recovery (date, metric, value) VALUES (?, ?, ?)", rows
    )


def fetch_activities(conn, since=None):
    q = "SELECT * FROM activities"
    params = []
    if since:
        q += " WHERE date >= ?"
        params.append(since.isoformat())
    q += " ORDER BY date, start_time"
    return [dict(r) for r in conn.execute(q, params)]


def fetch_recovery(conn, since=None):
    q = "SELECT * FROM recovery"
    params = []
    if since:
        q += " WHERE date >= ?"
        params.append(since.isoformat())
    q += " ORDER BY date"
    out = {}
    for r in conn.execute(q, params):
        out.setdefault(r["date"], {})[r["metric"]] = r["value"]
    return out


def save_plan(conn, week_start, plan_json, generated_at):
    conn.execute(
        "INSERT OR REPLACE INTO plans (week_start, plan_json, generated_at) VALUES (?, ?, ?)",
        (week_start, plan_json, generated_at),
    )


def get_plan(conn, week_start):
    row = conn.execute("SELECT plan_json FROM plans WHERE week_start = ?", (week_start,)).fetchone()
    return row["plan_json"] if row else None


def set_meta(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))


def get_meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default
