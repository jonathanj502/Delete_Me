# Account Aggregator

Scans your Gmail inbox to find every online account tied to your email, then outputs a spreadsheet for you to review. Runs entirely on your machine — no data leaves your computer.

---

## Setup

**Prerequisites:** Python 3.10+, a Google account, a Google Cloud account (free tier)

### 1. Install dependencies

```bash
git clone <repo-url>
cd account-aggregator
pip install -r requirements.txt
```

### 2. Create a Google Cloud OAuth app (one-time)

1. [console.cloud.google.com](https://console.cloud.google.com) → New Project
2. Search **Gmail API** → Enable
3. **APIs & Services → OAuth consent screen** → External → Create → fill in app name and your email → Save and Continue
4. Scopes screen → **Add or Remove Scopes** → add `https://www.googleapis.com/auth/gmail.readonly` → Save and Continue through to the end
5. OAuth consent screen → **Audience tab** → Add Users → add your Gmail address *(required — without this the OAuth flow fails with "Access blocked")*
6. **APIs & Services → Credentials** → Create Credentials → OAuth client ID → **Desktop app** → Create → Download JSON → save as `credentials.json` in the project root

### 3. Validate

```bash
python setup_check.py
```

---

## Usage

```bash
python scanner.py           # normal run; incremental after first completed scan
python scanner.py --fresh   # full re-scan, overwrites output
python scanner.py --check   # run setup checks and exit
```

First run opens a browser for OAuth sign-in. On the "Google hasn't verified this app" warning, click **Advanced → Go to [app name] (unsafe)** — this is expected for self-hosted tools.

---

## Output

Results are written to `output/accounts.csv`:

| Column | Description |
|---|---|
| `service` | Service name (e.g. Spotify) |
| `domain` | Root domain — the unique key |
| `first_seen` / `last_seen` | Date range of matched emails |
| `email_count` | Number of matched emails |
| `decision` | Fill in: keep, delete, already deleted, … |
| `deletion_url` | Fill in the account deletion URL |

The tool does not delete anything — that part is up to you.

---

## Troubleshooting

**"Access blocked" / Error 403: access_denied** — Add your Gmail address as a test user: **APIs & Services → OAuth consent screen → Audience tab → Test users → Add Users**

**Wrong credentials type** — `credentials.json` must be a Desktop app OAuth client, not a Web app or Service Account key. Run `python setup_check.py` to check.

**Token expired** — Delete `output/token.json` and re-run.

**Scan hits the `max_results` cap** — Set `max_results: null` in `config.yaml` for an unlimited scan.

---

## Privacy

- Read-only Gmail access (`gmail.readonly`) — cannot modify or send email
- Only message headers fetched (From, Reply-To, Subject, Date) — never the body
- You create your own Google Cloud project — no shared credentials, no central server
- No telemetry

See [PRIVACY.md](PRIVACY.md) for details.

---

## Contributing

`data/esp_domains.json` maps email relay domains (SendGrid, Amazon SES, Mailchimp, etc.) to the real sending service. PRs to expand this list are welcome.
