#!/usr/bin/env python3
"""FastAPI web server for Alabama WARN Act notices."""

import sys
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Query
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


def _filter_clauses(
    event_type: Optional[Literal["Closure", "Layoff"]],
    year_from: Optional[int],
    year_to: Optional[int],
    min_employees: Optional[int],
) -> tuple[list[str], list]:
    """Build WHERE clause fragments and bind params for the shared filters."""
    clauses, params = [], []

    if event_type == "Closure":
        clauses.append("event_type LIKE 'Clos%'")
    elif event_type == "Layoff":
        clauses.append("event_type LIKE 'Lay%'")

    if year_from is not None:
        clauses.append("announcement_date >= ?")
        params.append(f"{year_from}-01-01")

    if year_to is not None:
        clauses.append("announcement_date <= ?")
        params.append(f"{year_to}-12-31")

    if min_employees is not None:
        clauses.append("affected_employees >= ?")
        params.append(min_employees)

    return clauses, params


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    event_type: Optional[Literal["Closure", "Layoff"]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_employees: Optional[int] = None,
):
    clauses, params = _filter_clauses(event_type, year_from, year_to, min_employees)
    clauses.insert(0, "company_name LIKE ?")
    params.insert(0, f"%{q}%")

    sql = f"""
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE {' AND '.join(clauses)}
         ORDER BY announcement_date DESC
    """
    with db.get_db() as conn:
        results = _rows_to_dicts(conn.execute(sql, params).fetchall())
    return {"results": results, "count": len(results)}


@app.get("/api/top-size")
def top_size(
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[Literal["Closure", "Layoff"]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_employees: Optional[int] = None,
):
    clauses, params = _filter_clauses(event_type, year_from, year_to, min_employees)
    clauses.insert(0, "affected_employees IS NOT NULL")

    sql = f"""
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE {' AND '.join(clauses)}
         ORDER BY affected_employees DESC
         LIMIT ?
    """
    with db.get_db() as conn:
        results = _rows_to_dicts(conn.execute(sql, params + [limit]).fetchall())
    return {"results": results}


@app.get("/api/top-recent")
def top_recent(
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[Literal["Closure", "Layoff"]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_employees: Optional[int] = None,
):
    clauses, params = _filter_clauses(event_type, year_from, year_to, min_employees)
    clauses.insert(0, "announcement_date IS NOT NULL")

    sql = f"""
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE {' AND '.join(clauses)}
         ORDER BY announcement_date DESC
         LIMIT ?
    """
    with db.get_db() as conn:
        results = _rows_to_dicts(conn.execute(sql, params + [limit]).fetchall())
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="127.0.0.1", port=8000, reload=True)
