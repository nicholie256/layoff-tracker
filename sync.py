#!/usr/bin/env python3
"""Fetch Alabama WARN Act notices and upsert into local SQLite database."""

import csv
import io
import logging
import sys
from datetime import date

import requests

import db

CSV_URL = "https://workforce.alabama.gov/documents/warn-list/"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_csv(url: str = CSV_URL) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_date(value: str) -> str | None:
    """Normalize MM/DD/YYYY → YYYY-MM-DD. Returns None if unparseable or sentinel."""
    value = value.strip()
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            parsed = __import__("datetime").datetime.strptime(value, fmt).date()
            if parsed.year < 1900:
                return None
            return parsed.isoformat()
        except ValueError:
            continue
    log.warning("Unrecognized date format: %r", value)
    return None


def parse_int(value: str) -> int | None:
    try:
        return int(value.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None


# The CSV has no header row; columns are positional.
FIELDNAMES = [
    "case_id", "event_type", "announcement_date", "effective_date",
    "company_name", "city", "affected_employees", "record_number",
]


def normalize(row: dict) -> dict | None:
    """Map raw CSV row to our schema. Returns None if the row should be skipped."""
    case_id = row.get("case_id", "").strip()
    if not case_id:
        return None

    return {
        "case_id": case_id,
        "event_type": row.get("event_type", "").strip() or None,
        "announcement_date": parse_date(row.get("announcement_date", "")),
        "effective_date": parse_date(row.get("effective_date", "")),
        "company_name": row.get("company_name", "").strip() or None,
        "city": row.get("city", "").strip() or None,
        "affected_employees": parse_int(row.get("affected_employees", "")),
    }


def main() -> None:
    log.info("Fetching WARN notices from %s", CSV_URL)
    try:
        raw = fetch_csv()
    except requests.RequestException as exc:
        log.error("Failed to fetch CSV: %s", exc)
        sys.exit(1)

    reader = csv.DictReader(io.StringIO(raw), fieldnames=FIELDNAMES)
    records = []
    for row in reader:
        normalized = normalize(row)
        if normalized:
            records.append(normalized)

    log.info("Parsed %d records", len(records))

    conn = db.get_connection()
    db.init_db(conn)
    inserted, updated = db.upsert_notices(conn, records)
    conn.close()

    log.info("Done — %d inserted, %d updated", inserted, updated)


if __name__ == "__main__":
    main()
