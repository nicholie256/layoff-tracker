#!/usr/bin/env python3
"""FastAPI web server for Alabama WARN Act notices."""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db

if not db.DB_PATH.exists():
    print("Database not found. Run sync.py first.", file=sys.stderr)
    sys.exit(1)

app = FastAPI(title="Alabama WARN Tracker")

STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/search")
def search(q: str = Query(..., min_length=1)):
    conn = db.get_connection()
    rows = conn.execute(
        """
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE company_name LIKE ?
         ORDER BY announcement_date DESC
        """,
        (f"%{q}%",),
    ).fetchall()
    conn.close()
    return {"results": _rows_to_dicts(rows), "count": len(rows)}


@app.get("/api/top-size")
def top_size(limit: int = Query(100, ge=1, le=1000)):
    conn = db.get_connection()
    rows = conn.execute(
        """
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE affected_employees IS NOT NULL
         ORDER BY affected_employees DESC
         LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return {"results": _rows_to_dicts(rows)}


@app.get("/api/top-recent")
def top_recent(limit: int = Query(100, ge=1, le=1000)):
    conn = db.get_connection()
    rows = conn.execute(
        """
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE announcement_date IS NOT NULL
         ORDER BY announcement_date DESC
         LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return {"results": _rows_to_dicts(rows)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="127.0.0.1", port=8000, reload=True)
