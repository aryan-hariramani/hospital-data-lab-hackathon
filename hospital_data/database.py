"""SQLite persistence and parameterized aggregate queries."""
import sqlite3
from .core import FIELDS
from .validation import validate

SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
 visit_id TEXT PRIMARY KEY,
 department TEXT NOT NULL,
 age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120),
 arrival_at TEXT NOT NULL,
 seen_at TEXT NOT NULL,
 discharged_at TEXT NOT NULL,
 wait_minutes INTEGER NOT NULL CHECK(wait_minutes >= 0),
 stay_minutes INTEGER NOT NULL CHECK(stay_minutes >= wait_minutes)
);
CREATE INDEX IF NOT EXISTS idx_department_arrival ON visits(department, arrival_at);
"""

def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def replace_visits(conn, rows):
    """Atomic replace: reject invalid inputs before touching existing data."""
    clean, report = validate(rows)
    if report["invalid_rows"]:
        raise ValueError("Database accepts validated records only")
    with conn:
        conn.execute("DELETE FROM visits")
        conn.executemany("INSERT INTO visits VALUES (?,?,?,?,?,?,?,?)",
                         [tuple(row[f] for f in FIELDS) for row in clean])

def analytics(conn, departments=None):
    where, params = "", []
    if departments is not None:
        if not departments: return {"summary": [], "daily": [], "rows": []}
        params = list(departments)
        where = " WHERE department IN (" + ",".join("?" for _ in params) + ")"
    def query(sql): return [dict(row) for row in conn.execute(sql, params)]
    summary = query("SELECT department, COUNT(*) AS visits, "
                    "ROUND(AVG(wait_minutes),2) AS avg_wait_minutes, "
                    "ROUND(AVG(stay_minutes),2) AS avg_stay_minutes "
                    "FROM visits" + where + " GROUP BY department ORDER BY visits DESC, department")
    daily = query("SELECT substr(arrival_at,1,10) AS day, COUNT(*) AS visits "
                  "FROM visits" + where + " GROUP BY day ORDER BY day")
    rows = query("SELECT * FROM visits" + where + " ORDER BY arrival_at, visit_id")
    return {"summary": summary, "daily": daily, "rows": rows}
