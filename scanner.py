#!/usr/bin/env python3
"""Delete Me — entry point."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _iso_to_gmail_date(iso: str) -> str:
    """Convert ISO 8601 timestamp to Gmail after: filter format (YYYY/MM/DD)."""
    return datetime.fromisoformat(iso).strftime("%Y/%m/%d")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan Gmail for accounts tied to your email address.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore prior state and perform a full re-scan.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate setup (credentials, output dir) and exit.",
    )
    args = parser.parse_args()

    if args.check:
        import setup_check
        sys.exit(0 if setup_check.run_checks() else 1)

    from src import auth, gmail_client, extractor
    from src import esp_map as esp_module
    from src import deduplicator, output, state

    config = load_config()
    queries = config.get("search_queries", [])
    max_results = config.get("max_results")
    output_sqlite = config.get("output_sqlite", False)

    scan_state = state.load_state()
    if args.fresh:
        state.clear_state()
        scan_state = {}

    after_date: str | None = None
    if not args.fresh and state.is_completed(scan_state):
        after_date = _iso_to_gmail_date(scan_state["last_scan_completed_at"])
        print(f"Incremental scan: fetching emails after {after_date}")
    elif state.is_interrupted(scan_state):
        print("Prior scan was interrupted — performing full re-scan")
    else:
        print("Starting full scan")

    # Clear completed marker before fetching so an interrupt leaves state as in-progress
    in_progress = {k: v for k, v in scan_state.items() if k != "last_scan_completed_at"}
    state.save_state(in_progress)

    print("Authenticating with Google...")
    creds = auth.get_credentials()
    service = gmail_client.build_service(creds)

    print(f"Fetching messages ({len(queries)} queries, max_results={max_results if max_results is not None else 'unlimited'})...")
    raw_messages = gmail_client.fetch_messages(service, queries, max_results, after_date=after_date)
    print(f"  {len(raw_messages)} messages fetched")

    records = extractor.extract_records(raw_messages)
    esp = esp_module.load_esp_map()
    resolved = esp_module.resolve_records(records, esp)
    new_groups = deduplicator.group_records(resolved)
    print(f"  {len(new_groups)} services found")

    if args.fresh:
        final_rows = new_groups
    else:
        existing = output.read_csv()
        final_rows = output.merge_rows(existing, new_groups)

    output.write_csv(final_rows)
    print(f"CSV written: {output.CSV_PATH} ({len(final_rows)} rows)")

    if output_sqlite:
        output.write_sqlite(final_rows)
        print(f"SQLite written: {output.DB_PATH}")

    state.save_state(state.mark_complete(in_progress))
    print("Scan complete.")


if __name__ == "__main__":
    main()
