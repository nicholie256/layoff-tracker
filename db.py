import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "warn.db"


def get_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(path: Path = DB_PATH):
    conn = get_connection(path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS warn_notices (
            case_id            TEXT PRIMARY KEY,
            event_type         TEXT,
            announcement_date  TEXT,
            effective_date     TEXT,
            company_name       TEXT,
            city               TEXT,
            affected_employees INTEGER,
            synced_at          TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_company ON warn_notices (company_name COLLATE NOCASE)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_announcement ON warn_notices (announcement_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_affected ON warn_notices (affected_employees)")
    conn.commit()


def upsert_notices(conn: sqlite3.Connection, records: list[dict]) -> tuple[int, int]:
    """Returns (inserted, updated) counts."""
    synced_at = datetime.now(timezone.utc).isoformat()

    existing_ids = {
        row[0] for row in conn.execute("SELECT case_id FROM warn_notices")
    }

    conn.executemany("""
        INSERT INTO warn_notices
            (case_id, event_type, announcement_date, effective_date,
             company_name, city, affected_employees, synced_at)
        VALUES (:case_id, :event_type, :announcement_date, :effective_date,
                :company_name, :city, :affected_employees, :synced_at)
        ON CONFLICT(case_id) DO UPDATE SET
            event_type         = excluded.event_type,
            announcement_date  = excluded.announcement_date,
            effective_date     = excluded.effective_date,
            company_name       = excluded.company_name,
            city               = excluded.city,
            affected_employees = excluded.affected_employees,
            synced_at          = excluded.synced_at
    """, [{**r, "synced_at": synced_at} for r in records])

    conn.commit()

    inserted = sum(1 for r in records if r["case_id"] not in existing_ids)
    updated = len(records) - inserted
    return inserted, updated
