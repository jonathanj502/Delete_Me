#!/usr/bin/env python3
"""Gmail Account Scanner — entry point."""

import argparse
import sys
from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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
        print("Running pre-flight check...")
        # setup_check logic wired in Chunk 2
        print("(setup_check not yet implemented — coming in Chunk 2)")
        sys.exit(0)

    config = load_config()
    max_results = config.get("max_results")
    max_results_display = max_results if max_results is not None else "unlimited"
    print(f"Config loaded: {len(config.get('search_queries', []))} queries, "
          f"max_results={max_results_display}")
    print("(Scanner not yet implemented — scaffold only)")


if __name__ == "__main__":
    main()
