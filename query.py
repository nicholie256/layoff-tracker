#!/usr/bin/env python3
"""Query Alabama WARN notices from the local database."""

import argparse
import sys

import db

COL_WIDTH = 130


def _print_table(rows: list[dict]) -> None:
    print(f"\n{'Company':<45} {'City':<20} {'Type':<10} {'Employees':>9}  {'Announced':<12}  {'Effective':<12}  Case ID")
    print("-" * COL_WIDTH)
    for r in rows:
        print(
            f"{(r['company_name'] or ''):<45} "
            f"{(r['city'] or ''):<20} "
            f"{(r['event_type'] or ''):<10} "
            f"{(r['affected_employees'] or 0):>9,}  "
            f"{(r['announcement_date'] or 'N/A'):<12}  "
            f"{(r['effective_date'] or 'N/A'):<12}  "
            f"{r['case_id']}"
        )


def cmd_search(args: argparse.Namespace) -> None:
    conn = db.get_connection()
    rows = conn.execute(
        """
        SELECT company_name, city, event_type, affected_employees,
               announcement_date, effective_date, case_id
          FROM warn_notices
         WHERE company_name LIKE ?
         ORDER BY announcement_date DESC
        """,
        (f"%{args.company}%",),
    ).fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    if not results:
        print(f"No notices found matching '{args.company}'.")
        return

    print(f"\n{len(results)} notice(s) matching '{args.company}':")
    _print_table(results)


def cmd_top_size(args: argparse.Namespace) -> None:
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
        (args.limit,),
    ).fetchall()
    conn.close()

    print(f"\nTop {args.limit} notices by employees affected:")
    _print_table([dict(r) for r in rows])


def cmd_top_recent(args: argparse.Namespace) -> None:
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
        (args.limit,),
    ).fetchall()
    conn.close()

    print(f"\n{args.limit} most recent notices:")
    _print_table([dict(r) for r in rows])


def main() -> None:
    if not db.DB_PATH.exists():
        print("Database not found. Run sync.py first.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Query Alabama WARN notices.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Search by company name (partial match)")
    p_search.add_argument("company", help="Company name to search for")
    p_search.set_defaults(func=cmd_search)

    p_size = sub.add_parser("top-size", help="Top notices by employees affected")
    p_size.add_argument("--limit", type=int, default=100, metavar="N")
    p_size.set_defaults(func=cmd_top_size)

    p_recent = sub.add_parser("top-recent", help="Most recent notices by announcement date")
    p_recent.add_argument("--limit", type=int, default=100, metavar="N")
    p_recent.set_defaults(func=cmd_top_recent)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
