import unittest
from src.esp_map import resolve_record, _root_domain, _clean_display_name, _is_generic

_ESP_MAP = {
    "sendgrid.net":    {"type": "esp", "resolve_from": ["reply-to", "display-name"]},
    "amazonses.com":   {"type": "esp", "resolve_from": ["reply-to", "display-name"]},
    "list-manage.com": {"type": "esp", "resolve_from": ["display-name"]},
    "exacttarget.com": {"type": "esp", "resolve_from": ["reply-to"]},
}


def _rec(from_addr, reply_to="", subject="Test", date="2024-01-01", message_id="m1"):
    return {
        "message_id": message_id,
        "from_addr": from_addr,
        "reply_to": reply_to,
        "subject": subject,
        "date": date,
    }


class TestRootDomain(unittest.TestCase):
    def test_strips_subdomain(self):
        self.assertEqual(_root_domain("mail.spotify.com"), "spotify.com")

    def test_apex_domain_unchanged(self):
        self.assertEqual(_root_domain("spotify.com"), "spotify.com")

    def test_deep_subdomain(self):
        self.assertEqual(_root_domain("a.b.c.spotify.com"), "spotify.com")

    def test_empty(self):
        self.assertEqual(_root_domain(""), "")


class TestCleanDisplayName(unittest.TestCase):
    def test_via_suffix_stripped(self):
        self.assertEqual(_clean_display_name("Spotify via SendGrid"), "Spotify")

    def test_plain_name_unchanged(self):
        self.assertEqual(_clean_display_name("Acme Corp"), "Acme Corp")

    def test_case_insensitive_via(self):
        self.assertEqual(_clean_display_name("Acme Via Marketing"), "Acme")


class TestIsGeneric(unittest.TestCase):
    def test_noreply_is_generic(self):
        self.assertTrue(_is_generic("noreply"))

    def test_mixed_case(self):
        self.assertTrue(_is_generic("Noreply"))

    def test_spotify_not_generic(self):
        self.assertFalse(_is_generic("Spotify"))


class TestResolveRecord(unittest.TestCase):
    def test_first_party_sender(self):
        """Non-ESP from domain → root domain used directly."""
        r = resolve_record(_rec("Spotify <no-reply@email.spotify.com>"), _ESP_MAP)
        self.assertEqual(r["root_domain"], "spotify.com")
        self.assertEqual(r["service_name"], "Spotify")

    def test_esp_reply_to_wins(self):
        """ESP from domain with valid Reply-To → resolve from Reply-To domain."""
        r = resolve_record(
            _rec(
                "Spotify <notifications@sendgrid.net>",
                reply_to="bounce@email.spotify.com",
            ),
            _ESP_MAP,
        )
        self.assertEqual(r["root_domain"], "spotify.com")
        self.assertEqual(r["service_name"], "Spotify")

    def test_esp_display_name_fallback(self):
        """ESP with no Reply-To but recognizable display name → display name used."""
        r = resolve_record(_rec("Spotify via SendGrid <x@sendgrid.net>"), _ESP_MAP)
        self.assertEqual(r["service_name"], "Spotify")
        self.assertEqual(r["root_domain"], "spotify")

    def test_mailchimp_display_name(self):
        """list-manage.com only supports display-name resolution."""
        r = resolve_record(_rec("Acme Corp <news@list-manage.com>"), _ESP_MAP)
        self.assertEqual(r["service_name"], "Acme Corp")
        self.assertEqual(r["root_domain"], "acmecorp")

    def test_ses_with_reply_to(self):
        """Amazon SES with Reply-To → resolve domain."""
        r = resolve_record(
            _rec(
                "Shop <no-reply@amazonses.com>",
                reply_to="orders@shop.example.com",
            ),
            _ESP_MAP,
        )
        self.assertEqual(r["root_domain"], "example.com")

    def test_exacttarget_no_reply_to_fallback(self):
        """ExactTarget only supports reply-to; no Reply-To → fallback to from domain."""
        r = resolve_record(_rec("Noreply <alerts@exacttarget.com>"), _ESP_MAP)
        # Falls through to Step 4 — not dropped, domain used as key
        self.assertEqual(r["root_domain"], "exacttarget.com")
        self.assertIsNotNone(r["service_name"])

    def test_unresolvable_generic_not_dropped(self):
        """Generic display name on ESP with no Reply-To → Step 4, row is kept."""
        r = resolve_record(_rec("Noreply <noreply@sendgrid.net>"), _ESP_MAP)
        self.assertEqual(r["root_domain"], "sendgrid.net")
        self.assertIn("service_name", r)

    def test_empty_from_addr(self):
        """Completely missing From → empty strings, not raised."""
        r = resolve_record(_rec(""), _ESP_MAP)
        self.assertEqual(r["root_domain"], "")
        self.assertEqual(r["service_name"], "")

    def test_esp_subdomain_from_addr(self):
        """ESP email from a subdomain of a known ESP root is still detected."""
        r = resolve_record(
            _rec("Spotify <x@em123.sendgrid.net>", reply_to="y@email.spotify.com"),
            _ESP_MAP,
        )
        self.assertEqual(r["root_domain"], "spotify.com")
        self.assertEqual(r["service_name"], "Spotify")

    def test_esp_reply_to_subdomain_guard(self):
        """Reply-To through a subdomain of a known ESP is skipped; display-name wins instead."""
        r = resolve_record(
            _rec("Acme <x@sendgrid.net>", reply_to="y@mail.klaviyo.com"),
            {**_ESP_MAP, "klaviyo.com": {"type": "esp", "resolve_from": ["reply-to"]}},
        )
        # mail.klaviyo.com root = klaviyo.com which is in esp_map → Reply-To skipped
        # Display-name "Acme" is non-generic → wins
        self.assertEqual(r["service_name"], "Acme")
        self.assertEqual(r["root_domain"], "acme")

    def test_original_fields_preserved(self):
        """All original record fields pass through unchanged."""
        rec = _rec("Test <t@example.com>", subject="Hello", date="2024-06-01")
        r = resolve_record(rec, _ESP_MAP)
        self.assertEqual(r["subject"], "Hello")
        self.assertEqual(r["date"], "2024-06-01")
        self.assertEqual(r["message_id"], "m1")


if __name__ == "__main__":
    unittest.main()
