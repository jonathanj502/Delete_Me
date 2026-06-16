#!/usr/bin/env python3
"""Pre-flight validator — run before first scan to catch common setup mistakes."""

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
CREDENTIALS_PATH = _ROOT / "credentials.json"
OUTPUT_DIR = _ROOT / "output"

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_WARN = "[WARN]"


def _check_credentials_exist() -> bool:
    if CREDENTIALS_PATH.exists():
        print(f"{_PASS} credentials.json found")
        return True
    print(f"{_FAIL} credentials.json not found")
    print("      See README.md → 'Google Cloud OAuth Setup' for instructions.")
    return False


def _check_credentials_not_tracked() -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "credentials.json"],
            capture_output=True,
            cwd=_ROOT,
        )
        if result.returncode == 0:
            print(f"{_WARN} credentials.json is tracked by git — security risk!")
            print("      Run: git rm --cached credentials.json")
            return False
        if result.returncode not in (1, 0):
            # e.g. 128 = not inside a git repo; can't verify tracking
            print(f"{_PASS} not in a git repository — skipping tracking check")
            return True
    except FileNotFoundError:
        pass  # git not installed — skip
    print(f"{_PASS} credentials.json is not git-tracked")
    return True


def _check_output_writable() -> bool:
    OUTPUT_DIR.mkdir(exist_ok=True)
    test_file = OUTPUT_DIR / ".write_test"
    try:
        test_file.write_text("ok", encoding="utf-8")
    except OSError as exc:
        print(f"{_FAIL} output/ is not writable: {exc}")
        return False
    test_file.unlink(missing_ok=True)
    print(f"{_PASS} output/ is writable")
    return True


def run_checks() -> bool:
    """Run all pre-flight checks. Returns True if all pass."""
    results = [
        _check_credentials_exist(),
        _check_credentials_not_tracked(),
        _check_output_writable(),
    ]
    return all(results)


def main() -> None:
    print("Gmail Account Scanner — pre-flight check\n")
    ok = run_checks()
    print()
    if ok:
        print("All checks passed. Ready to scan.")
    else:
        print("Fix the issues above before running the scanner.")
        sys.exit(1)


if __name__ == "__main__":
    main()
