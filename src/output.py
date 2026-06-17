import csv
import sqlite3
from pathlib import Path

_FIELDNAMES = ["service", "domain", "first_seen", "last_seen", "email_count", "decision", "deletion_url"]
_OUTPUT_DIR = Path(__file__).parent.parent / "output"
CSV_PATH = _OUTPUT_DIR / "accounts.csv"
DB_PATH = _OUTPUT_DIR / "accounts.db"


def write_csv(rows: list[dict], path: Path = CSV_PATH) -> None:
    """Write rows to CSV, creating or overwriting the file."""
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path = CSV_PATH) -> list[dict]:
    """Read rows from an existing CSV. Returns [] if file doesn't exist."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def merge_rows(existing: list[dict], new_groups: list[dict]) -> list[dict]:
    """
    Merge new_groups into existing rows, keyed by domain.

    For matching domains: update last_seen if newer, update first_seen if older,
    add to email_count. Preserve existing decision and deletion_url.
    New domains are appended.
    """
    merged: dict[str, dict] = {row["domain"]: dict(row) for row in existing}

    for row in new_groups:
        domain = row["domain"]
        if domain in merged:
            entry = merged[domain]
            new_last = row.get("last_seen", "")
            new_first = row.get("first_seen", "")
            if new_last and new_last > entry.get("last_seen", ""):
                entry["last_seen"] = new_last
            if new_first and (not entry.get("first_seen") or new_first < entry["first_seen"]):
                entry["first_seen"] = new_first
            try:
                entry["email_count"] = int(entry.get("email_count") or 0) + int(row.get("email_count") or 0)
            except (ValueError, TypeError):
                entry["email_count"] = row.get("email_count", 0)
        else:
            merged[domain] = dict(row)

    return sorted(merged.values(), key=lambda r: r.get("service", "").lower())


def write_sqlite(rows: list[dict], path: Path = DB_PATH) -> None:
    """Write all rows to SQLite, replacing the accounts table."""
    path.parent.mkdir(exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS accounts")
        conn.execute("""
            CREATE TABLE accounts (
                service      TEXT,
                domain       TEXT PRIMARY KEY,
                first_seen   TEXT,
                last_seen    TEXT,
                email_count  INTEGER,
                decision     TEXT DEFAULT '',
                deletion_url TEXT DEFAULT ''
            )
        """)
        conn.executemany(
            """INSERT INTO accounts
               (service, domain, first_seen, last_seen, email_count, decision, deletion_url)
               VALUES (:service, :domain, :first_seen, :last_seen, :email_count, :decision, :deletion_url)""",
            [{**r, "email_count": int(r.get("email_count") or 0)} for r in rows],
        )
