import json
import re
from email.utils import parseaddr
from pathlib import Path

_ESP_MAP_PATH = Path(__file__).parent.parent / "data" / "esp_domains.json"

_GENERIC_NAMES = frozenset({
    "noreply", "no-reply", "no reply", "donotreply", "do not reply",
    "mailer", "notifications", "info", "support", "hello", "team",
    "newsletter", "news", "updates", "alert", "alerts", "service",
    "account", "accounts", "mail", "email", "sender",
})


def load_esp_map(path: Path = _ESP_MAP_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_record(record: dict, esp_map: dict) -> dict:
    """
    Augment an extracted record with service_name and root_domain.

    Never drops a record — Step 4 falls back to the From domain.
    Returns the original record dict merged with service_name and root_domain.
    """
    from_addr = record.get("from_addr", "")
    reply_to = record.get("reply_to", "")

    display_name, _ = parseaddr(from_addr)
    from_domain = _email_domain(from_addr)
    from_root = _root_domain(from_domain)

    # Look up by root domain so subdomains (em123.sendgrid.net) match the map key (sendgrid.net)
    esp_entry = esp_map.get(from_root)
    resolve_from = esp_entry.get("resolve_from", []) if esp_entry else []

    # Step 2: ESP domain — try to resolve real sender
    if esp_entry:
        # 2a. Try Reply-To domain
        if "reply-to" in resolve_from and reply_to:
            rt_domain = _email_domain(reply_to)
            rt_root = _root_domain(rt_domain)
            if rt_domain and rt_root not in esp_map:
                return {**record, "service_name": _name_from_domain(rt_root), "root_domain": rt_root}

        # 2b. Try display-name
        if "display-name" in resolve_from and display_name:
            clean = _clean_display_name(display_name)
            if clean and not _is_generic(clean):
                return {
                    **record,
                    "service_name": clean,
                    "root_domain": clean.lower().replace(" ", ""),
                }

    # Steps 3 + 4: use the From domain (non-ESP, or unresolvable ESP)
    if not from_domain:
        return {**record, "service_name": "", "root_domain": ""}

    return {**record, "service_name": _name_from_domain(from_root), "root_domain": from_root}


def resolve_records(records: list[dict], esp_map: dict) -> list[dict]:
    return [resolve_record(r, esp_map) for r in records]


# ── helpers ───────────────────────────────────────────────────────────────────

def _email_domain(addr_str: str) -> str:
    _, addr = parseaddr(addr_str)
    if "@" in addr:
        return addr.split("@", 1)[1].lower().strip()
    return ""


def _root_domain(domain: str) -> str:
    """Strip subdomains: mail.spotify.com → spotify.com"""
    parts = domain.rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _name_from_domain(root_domain: str) -> str:
    """Derive a human-readable name from a root domain: spotify.com → Spotify"""
    if not root_domain:
        return ""
    return root_domain.split(".")[0].capitalize()


def _clean_display_name(name: str) -> str:
    """Strip ' via <relay>' suffixes: 'Spotify via SendGrid' → 'Spotify'"""
    return re.split(r"\s+via\s+", name, maxsplit=1, flags=re.IGNORECASE)[0].strip().strip('"')


def _is_generic(name: str) -> bool:
    return name.lower().strip() in _GENERIC_NAMES
