import csv
import io
import tempfile
import unittest
from pathlib import Path

from src.deduplicator import group_records, _iso_date
from src.output import write_csv, read_csv, merge_rows


def _resolved(domain, service="Spotify", date="Mon, 01 Jan 2024 12:00:00 +0000"):
    return {
        "message_id": f"msg_{domain}",
        "from_addr": f"x@{domain}",
        "reply_to": "",
        "subject": "Welcome",
        "date": date,
        "service_name": service,
        "root_domain": domain,
    }


class TestIsoDate(unittest.TestCase):
    def test_valid_rfc2822(self):
        self.assertEqual(_iso_date("Mon, 01 Jan 2024 12:00:00 +0000"), "2024-01-01")

    def test_empty(self):
        self.assertEqual(_iso_date(""), "")

    def test_malformed(self):
        self.assertEqual(_iso_date("not a date"), "")


class TestGroupRecords(unittest.TestCase):
    def test_deduplicates_same_domain(self):
        recs = [_resolved("spotify.com")] * 3
        groups = group_records(recs)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["email_count"], 3)
        self.assertEqual(groups[0]["domain"], "spotify.com")

    def test_separate_domains(self):
        recs = [_resolved("spotify.com"), _resolved("netflix.com", service="Netflix")]
        groups = group_records(recs)
        self.assertEqual(len(groups), 2)

    def test_first_seen_last_seen_range(self):
        recs = [
            _resolved("spotify.com", date="Mon, 01 Jan 2024 12:00:00 +0000"),
            _resolved("spotify.com", date="Sat, 15 Jun 2024 08:00:00 +0000"),
            _resolved("spotify.com", date="Wed, 01 Mar 2023 08:00:00 +0000"),
        ]
        groups = group_records(recs)
        self.assertEqual(groups[0]["first_seen"], "2023-03-01")
        self.assertEqual(groups[0]["last_seen"], "2024-06-15")

    def test_service_name_from_first_record(self):
        recs = [
            _resolved("spotify.com", service="Spotify Premium"),
            _resolved("spotify.com", service="Spotify"),
        ]
        groups = group_records(recs)
        self.assertEqual(groups[0]["service"], "Spotify Premium")

    def test_empty_root_domain_skipped(self):
        recs = [
            {**_resolved("spotify.com"), "root_domain": ""},
            _resolved("netflix.com", service="Netflix"),
        ]
        groups = group_records(recs)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["domain"], "netflix.com")

    def test_output_has_blank_decision_and_deletion_url(self):
        groups = group_records([_resolved("spotify.com")])
        self.assertEqual(groups[0]["decision"], "")
        self.assertEqual(groups[0]["deletion_url"], "")

    def test_empty_input(self):
        self.assertEqual(group_records([]), [])

    def test_sorted_by_service_name(self):
        recs = [
            _resolved("z.com", service="Zzz"),
            _resolved("a.com", service="Aaa"),
            _resolved("m.com", service="Mmm"),
        ]
        groups = group_records(recs)
        names = [g["service"] for g in groups]
        self.assertEqual(names, sorted(names, key=str.lower))

    def test_malformed_date_does_not_crash(self):
        recs = [_resolved("spotify.com", date="not a real date")]
        groups = group_records(recs)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["first_seen"], "")


class TestMergeRows(unittest.TestCase):
    def _row(self, domain, service="S", count=1, first="2024-01-01", last="2024-01-01",
             decision="", deletion_url=""):
        return {
            "service": service, "domain": domain,
            "first_seen": first, "last_seen": last,
            "email_count": count, "decision": decision, "deletion_url": deletion_url,
        }

    def test_new_domain_appended(self):
        merged = merge_rows(
            existing=[self._row("a.com")],
            new_groups=[self._row("b.com", service="B")],
        )
        domains = {r["domain"] for r in merged}
        self.assertIn("b.com", domains)
        self.assertIn("a.com", domains)

    def test_count_incremented_on_existing_domain(self):
        merged = merge_rows(
            existing=[self._row("a.com", count=3)],
            new_groups=[self._row("a.com", count=2)],
        )
        self.assertEqual(merged[0]["email_count"], 5)

    def test_last_seen_updated_if_newer(self):
        merged = merge_rows(
            existing=[self._row("a.com", last="2024-01-01")],
            new_groups=[self._row("a.com", last="2024-06-01")],
        )
        self.assertEqual(merged[0]["last_seen"], "2024-06-01")

    def test_first_seen_updated_if_older(self):
        merged = merge_rows(
            existing=[self._row("a.com", first="2024-06-01")],
            new_groups=[self._row("a.com", first="2023-01-01")],
        )
        self.assertEqual(merged[0]["first_seen"], "2023-01-01")

    def test_decision_preserved_on_merge(self):
        merged = merge_rows(
            existing=[self._row("a.com", decision="keep")],
            new_groups=[self._row("a.com", count=2)],
        )
        self.assertEqual(merged[0]["decision"], "keep")

    def test_empty_existing(self):
        merged = merge_rows([], [self._row("a.com")])
        self.assertEqual(len(merged), 1)


class TestCsvRoundtrip(unittest.TestCase):
    def test_write_and_read(self):
        rows = [
            {"service": "Spotify", "domain": "spotify.com", "first_seen": "2024-01-01",
             "last_seen": "2024-06-01", "email_count": 5, "decision": "", "deletion_url": ""},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.csv"
            write_csv(rows, path)
            read_back = read_csv(path)
            self.assertEqual(len(read_back), 1)
            self.assertEqual(read_back[0]["domain"], "spotify.com")
            self.assertEqual(read_back[0]["email_count"], "5")  # CSV is all strings

    def test_read_nonexistent_returns_empty(self):
        self.assertEqual(read_csv(Path("/nonexistent/path/accounts.csv")), [])


if __name__ == "__main__":
    unittest.main()
