def extract_record(raw_message: dict) -> dict:
    """Parse a raw Gmail API message (format=metadata) into a flat record."""
    headers: dict[str, str] = {}
    for h in raw_message.get("payload", {}).get("headers", []):
        headers.setdefault(h["name"].lower(), h["value"])

    return {
        "message_id": raw_message["id"],
        "from_addr": headers.get("from", ""),
        "reply_to": headers.get("reply-to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
    }


def extract_records(raw_messages: list[dict]) -> list[dict]:
    return [extract_record(msg) for msg in raw_messages]
