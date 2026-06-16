# Account Aggregator

Scans your Gmail inbox to find every online account tied to your email address, then gives you a spreadsheet to review and decide what to keep or delete. Everything runs on your machine — no data ever leaves your computer.

> Outlook, Yahoo, and other providers are planned for a future release.

---

## Privacy

- **No data leaves your computer.** The only network calls are from your machine to Google's Gmail API.
- **Read-only access.** The tool cannot read, modify, send, or delete your emails.
- **Headers only.** Only the From, Reply-To, Subject, and Date fields are fetched. Email bodies are never requested.
- **Your credentials stay local.** You create your own Google Cloud project — no shared credentials, no central server.
- **No telemetry.** Nothing is tracked or reported anywhere.

---

## Prerequisites

- Python 3.10 or later
- A Google account
- A Google Cloud account (free tier is sufficient)

---

## Google Cloud OAuth Setup

This is a one-time setup. You are creating a private OAuth app inside your own Google Cloud project — you are the only user of this app.

### 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New Project**
3. Give it any name (e.g. "Account Aggregator") → **Create**

### 2. Enable the Gmail API

1. In the search bar, search for **Gmail API**
2. Click it → **Enable**

### 3. Configure the OAuth consent screen

1. In the left sidebar → **APIs & Services** → **OAuth consent screen**
2. Select **External** → **Create**
3. Fill in:
   - App name: anything (e.g. "Account Aggregator")
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue**
5. On the Scopes screen → **Add or Remove Scopes** → search for and add:
   `https://www.googleapis.com/auth/gmail.readonly`
6. Click **Save and Continue**
7. On the Test Users screen → **Add Users** → add your Gmail address
   > This step is required. Without it, the OAuth flow will fail.
8. Click **Save and Continue** through to the end

### 4. Create OAuth credentials

1. Left sidebar → **APIs & Services** → **Credentials**
2. **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Click **Create** → **Download JSON**
5. Save the downloaded file as `credentials.json` in the project root

### 5. Validate your setup

```bash
python setup_check.py
```

This checks that `credentials.json` exists, is not accidentally tracked by git, and that the output directory is writable. Fix any reported issues before running the scanner.

#### The "unverified app" warning

When you sign in for the first time, Google will show a warning screen because your OAuth app has not gone through Google's verification process. This is expected for self-hosted tools.

Click **Advanced** → **Go to [your app name] (unsafe)**.

This is safe. You are both the developer and the sole user of your own private OAuth app. The warning exists to protect users from third-party apps — it does not apply here.

---

## Installation

```bash
git clone <repo-url>
cd account-aggregator
pip install -r requirements.txt
```

---

## Usage

```bash
python scanner.py
```

On first run this opens a browser window to complete the OAuth flow. After sign-in, a token is saved to `output/token.json` and the scan begins.

### CLI flags

| Command | Behaviour |
|---|---|
| `python scanner.py` | Normal run. Incremental if a prior scan completed — only fetches emails newer than the last scan. |
| `python scanner.py --fresh` | Full re-scan from scratch. Ignores prior state and overwrites output. |
| `python scanner.py --check` | Runs setup checks and exits without scanning. |

### Incremental runs

After a completed scan, re-running without `--fresh` only fetches emails newer than the last scan and merges them into the existing output. Use this to keep your results up to date without re-processing your entire inbox.

---

## Output

Results are written to `output/accounts.csv`:

| Column | Description |
|---|---|
| `service` | Name of the service (e.g. Spotify, GitHub) |
| `domain` | Root domain used as the unique key (e.g. spotify.com) |
| `first_seen` | Date of the earliest matched email from this service |
| `last_seen` | Date of the most recent matched email |
| `email_count` | Number of matched emails from this service |
| `decision` | Blank — fill this in yourself (e.g. keep, delete, already deleted) |
| `deletion_url` | Blank — fill in the account deletion URL if you find it |

Open `accounts.csv` in any spreadsheet app, review the list, and fill in the `decision` column. The tool does not delete anything — that part is up to you.

### Accuracy

- **False positives:** Promotional emails from services where you may not have an account
- **False negatives:** Services that only send email types not covered by the search queries
- **Unresolved senders:** Some rows will show a bare domain instead of a service name — this happens when the sending domain belongs to an email relay and the real sender cannot be determined

---

## Troubleshooting

**`credentials.json` not found**
Make sure you downloaded the OAuth credentials JSON and saved it as `credentials.json` in the project root (not a subfolder). Run `python setup_check.py` to confirm.

**"Access blocked" or OAuth flow fails**
You may have skipped adding yourself as a Test User in step 3 of the setup. Go back to the OAuth consent screen → Test Users → add your Gmail address.

**Token expired or revoked**
Delete `output/token.json` and re-run. The OAuth flow will prompt you to sign in again.

**Scan stops early with a warning about `max_results`**
The default cap is 5000 unique messages. Set `max_results: null` in `config.yaml` to remove the limit, or increase the number.

**Interrupted scan does not resume**
The scan resumes automatically on re-run if it was interrupted. If you want to start fresh instead, run `python scanner.py --fresh`.

---

## Contributing

The ESP domain map (`data/esp_domains.json`) identifies email relay services (SendGrid, Amazon SES, Mailchimp, etc.) so the tool can resolve the real sender behind relay infrastructure. Community PRs to expand this list are welcome.
