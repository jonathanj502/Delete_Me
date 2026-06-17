from email.utils import parsedate_to_datetime


def group_records(resolved_records: list[dict]) -> list[dict]:
    """
    Group resolved records by root_domain into aggregate service rows.

    Service name is taken from the first record for each domain.
    Records with an empty root_domain are skipped (ungroupable).
    """
    groups: dict[str, dict] = {}

    for record in resolved_records:
        domain = record.get("root_domain", "")
        if not domain:
            continue

        date_str = _iso_date(record.get("date", ""))

        if domain not in groups:
            groups[domain] = {
                "service": record.get("service_name") or domain,
                "domain": domain,
                "first_seen": date_str,
                "last_seen": date_str,
                "email_count": 1,
                "decision": "",
                "deletion_url": "",
            }
        else:
            entry = groups[domain]
            entry["email_count"] += 1
            if date_str:
                if not entry["first_seen"] or date_str < entry["first_seen"]:
                    entry["first_seen"] = date_str
                if not entry["last_seen"] or date_str > entry["last_seen"]:
                    entry["last_seen"] = date_str

    return sorted(groups.values(), key=lambda r: r["service"].lower())


def _iso_date(date_str: str) -> str:
    """Parse an RFC 2822 date string and return YYYY-MM-DD, or '' on failure."""
    if not date_str:
        return ""
    try:
        return parsedate_to_datetime(date_str).date().isoformat()
    except Exception:
        return ""
