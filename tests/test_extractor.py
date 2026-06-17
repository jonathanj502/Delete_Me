import unittest

from src.extractor import extract_record, extract_records


def _raw(msg_id="abc123", headers=None):
    return {
        "id": msg_id,
        "payload": {
            "headers": [{"name": k, "value": v} for k, v in (headers or {}).items()]
        },
    }


class TestExtractRecord(unittest.TestCase):
    def test_extracts_all_fields(self):
        raw = _raw(headers={
            "From": "Spotify <noreply@spotify.com>",
            "Reply-To": "support@spotify.com",
            "Subject": "Welcome to Spotify",
            "Date": "Mon, 01 Jan 2024 12:00:00 +0000",
        })
        rec = extract_record(raw)
        self.assertEqual(rec["message_id"], "abc123")
        self.assertEqual(rec["from_addr"], "Spotify <noreply@spotify.com>")
        self.assertEqual(rec["reply_to"], "support@spotify.com")
        self.assertEqual(rec["subject"], "Welcome to Spotify")
        self.assertEqual(rec["date"], "Mon, 01 Jan 2024 12:00:00 +0000")

    def test_missing_headers_default_to_empty_string(self):
        rec = extract_record(_raw())
        self.assertEqual(rec["from_addr"], "")
        self.assertEqual(rec["reply_to"], "")
        self.assertEqual(rec["subject"], "")
        self.assertEqual(rec["date"], "")

    def test_missing_payload_key(self):
        rec = extract_record({"id": "x"})
        self.assertEqual(rec["message_id"], "x")
        self.assertEqual(rec["from_addr"], "")

    def test_header_matching_is_case_insensitive(self):
        raw = _raw(headers={"FROM": "foo@bar.com", "SUBJECT": "Hi"})
        rec = extract_record(raw)
        self.assertEqual(rec["from_addr"], "foo@bar.com")
        self.assertEqual(rec["subject"], "Hi")

    def test_first_occurrence_wins_on_duplicate_header(self):
        raw = {
            "id": "dup",
            "payload": {
                "headers": [
                    {"name": "From", "value": "first@a.com"},
                    {"name": "From", "value": "second@b.com"},
                ]
            },
        }
        rec = extract_record(raw)
        self.assertEqual(rec["from_addr"], "first@a.com")

    def test_empty_headers_list(self):
        raw = {"id": "empty", "payload": {"headers": []}}
        rec = extract_record(raw)
        self.assertEqual(rec["from_addr"], "")

    def test_message_id_preserved(self):
        rec = extract_record(_raw(msg_id="unique-id-999"))
        self.assertEqual(rec["message_id"], "unique-id-999")


class TestExtractRecords(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(extract_records([]), [])

    def test_multiple_messages(self):
        raws = [
            _raw("id1", {"From": "a@x.com"}),
            _raw("id2", {"From": "b@y.com"}),
        ]
        recs = extract_records(raws)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["message_id"], "id1")
        self.assertEqual(recs[1]["from_addr"], "b@y.com")
