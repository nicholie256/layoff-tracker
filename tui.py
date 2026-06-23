#!/usr/bin/env python3
"""Terminal UI for Alabama WARN Act notices."""

import sys
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    DataTable, Footer, Header, Input, Label, TabbedContent, TabPane,
)
from textual.containers import Vertical

import db


def _get_conn():
    if not db.DB_PATH.exists():
        print("Database not found. Run sync.py first.", file=sys.stderr)
        sys.exit(1)
    return db.get_connection()


COLUMNS = ("Company", "City", "Type", "Employees", "Announced", "Effective", "Case ID")


def _row_tuple(r: dict) -> tuple:
    return (
        r["company_name"] or "",
        r["city"] or "",
        r["event_type"] or "",
        f"{r['affected_employees']:,}" if r["affected_employees"] is not None else "",
        r["announcement_date"] or "",
        r["effective_date"] or "",
        r["case_id"],
    )


class WarnApp(App):
    CSS = """
    Screen { background: $surface; }

    #search-bar {
        height: 3;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $primary;
    }

    #search-input {
        width: 1fr;
    }

    #result-count {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh data"),
    ]

    TITLE = "Alabama WARN Act Tracker"
    SUB_TITLE = "workforce.alabama.gov"

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="search"):
            with TabPane("Search", id="search"):
                with Vertical():
                    with Vertical(id="search-bar"):
                        yield Input(placeholder="Type company name…", id="search-input")
                    yield Label("", id="result-count")
                    yield DataTable(id="search-table", cursor_type="row", zebra_stripes=True)
            with TabPane("Top by Size", id="top-size"):
                yield DataTable(id="size-table", cursor_type="row", zebra_stripes=True)
            with TabPane("Most Recent", id="top-recent"):
                yield DataTable(id="recent-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        for table_id in ("search-table", "size-table", "recent-table"):
            table = self.query_one(f"#{table_id}", DataTable)
            table.add_columns(*COLUMNS)

        self._load_top_size()
        self._load_top_recent()

    def _load_top_size(self) -> None:
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT company_name, city, event_type, affected_employees,
                   announcement_date, effective_date, case_id
              FROM warn_notices
             WHERE affected_employees IS NOT NULL
             ORDER BY affected_employees DESC
             LIMIT 100
            """
        ).fetchall()
        conn.close()
        table = self.query_one("#size-table", DataTable)
        table.clear()
        for r in rows:
            table.add_row(*_row_tuple(dict(r)))

    def _load_top_recent(self) -> None:
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT company_name, city, event_type, affected_employees,
                   announcement_date, effective_date, case_id
              FROM warn_notices
             WHERE announcement_date IS NOT NULL
             ORDER BY announcement_date DESC
             LIMIT 100
            """
        ).fetchall()
        conn.close()
        table = self.query_one("#recent-table", DataTable)
        table.clear()
        for r in rows:
            table.add_row(*_row_tuple(dict(r)))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        term = event.value.strip()
        table = self.query_one("#search-table", DataTable)
        label = self.query_one("#result-count", Label)
        table.clear()

        if not term:
            label.update("")
            return

        conn = _get_conn()
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

        for r in rows:
            table.add_row(*_row_tuple(dict(r)))

        count = len(rows)
        label.update(f"{count} result{'s' if count != 1 else ''}" if count else "No results.")

    def action_refresh(self) -> None:
        self._load_top_size()
        self._load_top_recent()
        self.notify("Data refreshed.")


if __name__ == "__main__":
    WarnApp().run()
