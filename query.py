#!/usr/bin/env python3
"""Search Alabama WARN notices by company name."""

import argparse
import sys

import db


def search(term: str) -> list[dict]:
    conn = db.get_connection()
    rows = conn.execute(
        """
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE company_name LIKE ?
         ORDER BY announcement_date DESC
        """,
        (f"%{term}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def print_results(results: list[dict], term: str) -> None:
    if not results:
        print(f"No notices found matching '{term}'.")
        return

    print(f"\n{len(results)} notice(s) matching '{term}':\n")
    print(f"{'Company':<45} {'City':<20} {'Type':<10} {'Employees':>9}  {'Announced':<12}  {'Effective':<12}  Case ID")
    print("-" * 130)
    for r in results:
        print(
            f"{(r['company_name'] or ''):<45} "
            f"{(r['city'] or ''):<20} "
            f"{(r['event_type'] or ''):<10} "
            f"{(r['affected_employees'] or 0):>9,}  "
            f"{(r['announcement_date'] or 'N/A'):<12}  "
            f"{(r['effective_date'] or 'N/A'):<12}  "
            f"{r['case_id']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Alabama WARN notices by company name.")
    parser.add_argument("company", help="Company name to search for (partial match)")
    args = parser.parse_args()

    if not db.DB_PATH.exists():
        print("Database not found. Run sync.py first.", file=sys.stderr)
        sys.exit(1)

    results = search(args.company)
    print_results(results, args.company)


if __name__ == "__main__":
    main()
