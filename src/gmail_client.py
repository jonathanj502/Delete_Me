import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

_BATCH_SIZE = 100  # max items per Gmail API batch request


def build_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds)


def fetch_messages(
    service,
    queries: list[str],
    max_results: int | None,
) -> list[dict]:
    """Return raw API message objects (metadata headers only) for all matching queries."""
    message_ids = _collect_ids(service, queries, max_results)
    return _fetch_headers(service, list(message_ids))


def _collect_ids(
    service,
    queries: list[str],
    max_results: int | None,
) -> set[str]:
    ids: set[str] = set()
    cap_hit = False

    for query in queries:
        if cap_hit:
            break
        page_token = None

        while True:
            if max_results is not None and len(ids) >= max_results:
                cap_hit = True
                break

            page_size = min(500, max_results - len(ids)) if max_results is not None else 500
            params: dict = {"userId": "me", "q": query, "maxResults": page_size}
            if page_token:
                params["pageToken"] = page_token

            resp = _with_backoff(service.users().messages().list(**params).execute)

            messages = resp.get("messages", [])
            if not messages:
                break  # no results on this page; nextPageToken (if any) would loop forever

            for msg in messages:
                ids.add(msg["id"])
                if max_results is not None and len(ids) >= max_results:
                    cap_hit = True
                    break

            page_token = resp.get("nextPageToken")
            if not page_token or cap_hit:
                break

    if cap_hit:
        print(
            f"\nWarning: max_results cap of {max_results} reached. "
            "Set max_results to null in config.yaml for a full scan."
        )

    return ids


def _fetch_headers(service, message_ids: list[str]) -> list[dict]:
    """Batch-fetch metadata headers for each message ID."""
    results: list[dict] = []

    for i in range(0, len(message_ids), _BATCH_SIZE):
        chunk_ids = message_ids[i : i + _BATCH_SIZE]
        chunk_results: list[dict] = []
        chunk_errors: list[Exception] = []

        def _callback(
            request_id: str,
            response: dict | None,
            exception: Exception | None,
            _r: list = chunk_results,
            _e: list = chunk_errors,
        ) -> None:
            if exception is not None:
                _e.append(exception)
            elif response is not None:
                _r.append(response)

        batch = service.new_batch_http_request(callback=_callback)
        for msg_id in chunk_ids:
            batch.add(
                service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "Reply-To", "Subject", "Date"],
                )
            )
        _with_backoff(batch.execute)

        if chunk_errors:
            raise chunk_errors[0]
        results.extend(chunk_results)

    return results


def _with_backoff(fn, max_retries: int = 5):
    """Call fn(), retrying with exponential backoff on 429/5xx HTTP errors."""
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
