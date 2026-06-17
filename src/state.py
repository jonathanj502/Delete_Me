import json
from datetime import datetime, timezone
from pathlib import Path

_STATE_PATH = Path(__file__).parent.parent / "output" / ".scan_state.json"


def load_state(path: Path = _STATE_PATH) -> dict:
    """Load scan state. Returns {} on first run or unreadable file."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict, path: Path = _STATE_PATH) -> None:
    """Write state atomically via a temp file."""
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def clear_state(path: Path = _STATE_PATH) -> None:
    if path.exists():
        path.unlink()


def is_completed(state: dict) -> bool:
    """True when a prior scan finished cleanly."""
    return bool(state.get("last_scan_completed_at"))


def is_interrupted(state: dict) -> bool:
    """True when a prior scan started but did not finish."""
    return bool(state) and not state.get("last_scan_completed_at")


def mark_complete(state: dict) -> dict:
    return {**state, "last_scan_completed_at": datetime.now(timezone.utc).isoformat()}
