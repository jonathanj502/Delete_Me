# Gmail Account Scanner — Implementation Plan

## Context

The goal is a local, open-source Python tool that scans a user's Gmail inbox to discover online accounts tied to their email address. Users clone the repo, set up their own Google Cloud OAuth credentials, and run the scanner entirely on their own machine. No data ever leaves their computer. The tool infers accounts from signup/welcome/verification/password-reset emails, groups them by service, and outputs a CSV the user can review and annotate with keep/delete decisions.

Key constraints:
- Runs 100% locally; only external calls are to Google's Gmail API from the user's machine
- Read-only Gmail access (`gmail.readonly` scope)
- No telemetry, analytics, or shared infrastructure
- Each user uses their own Google Cloud project and OAuth credentials
- Cross-platform: Windows, macOS, Linux
- Python 3.10+

---

## Architecture

### File Layout

```
gmail-account-scanner/
├── README.md                  # Setup, usage, privacy, troubleshooting
├── PRIVACY.md                 # Explicit privacy statement
├── LICENSE                    # MIT
├── requirements.txt
├── .gitignore                 # excludes credentials.json, output/
├── config.yaml                # User-editable: search queries, output format, limits
├── scanner.py                 # CLI entry point
├── setup_check.py             # Pre-flight validator — standalone script
├── src/
│   ├── __init__.py
│   ├── auth.py                # OAuth installed-app flow, token cache + refresh
│   ├── gmail_client.py        # API calls, pagination, batch fetch, backoff, cross-query dedup
│   ├── extractor.py           # Parse From/Reply-To/Subject/Date from raw header payloads
│   ├── esp_map.py             # Resolve known relay domains to the real sending service
│   ├── deduplicator.py        # Group records by service, track first/last seen + count
│   ├── output.py              # Write accounts.csv; optional accounts.db (SQLite)
│   └── state.py               # Read/write .scan_state.json (checkpoint + scan timestamp)
├── data/
│   └── esp_domains.json       # Static relay-domain map; updated via community PRs
├── tests/
│   ├── test_extractor.py
│   ├── test_esp_map.py
│   └── test_deduplicator.py
└── output/                    # gitignored — all user data lives here
    └── .gitkeep
```

### Data Flow

```
config.yaml + CLI flags
        ↓
   auth.py  ──────────────────────────────── output/token.json
        ↓
gmail_client.py
  • runs each search query
  • paginates results, respects max_results (total cap across all queries)
  • deduplicates message IDs across queries (same message can match multiple queries)
  • on incremental run: appends after:<date> to every query
  • batch-fetches headers (From, Reply-To, Subject, Date) for unique message IDs
        ↓
extractor.py  ──→  raw record per message: {message_id, from_addr, reply_to, subject, date}
        ↓
esp_map.py    ──→  resolved record: {service_name, root_domain}
        ↓
deduplicator.py ─→  aggregated record per service: {service, domain, first_seen, last_seen, count}
        ↓
output.py     ──→  output/accounts.csv  +  output/accounts.db (if output_sqlite: true)
        ↓
state.py      ──→  output/.scan_state.json (updated throughout; last_scan_completed_at set on clean finish)
```

### CLI Flags

```
python scanner.py             # normal run (incremental if a prior scan completed)
python scanner.py --fresh     # ignore prior state, full re-scan, overwrite output
python scanner.py --check     # run setup_check.py logic inline and exit
```

### Resumability & Incremental Runs

`state.py` reads and writes `output/.scan_state.json`:

```json
{
  "last_page_token": "...",
  "processed_ids": ["msg_id_1", "msg_id_2"],
  "last_scan_completed_at": "2024-03-15T14:22:00Z"
}
```

**Three distinct run states:**

| State | How detected | Behavior |
|---|---|---|
| First run | No state file | Full scan from scratch |
| Interrupted | State file exists, `last_scan_completed_at` is null | Resume from `last_page_token`; skip `processed_ids` |
| Completed previously | `last_scan_completed_at` is set | Incremental: append `after:YYYY/MM/DD` to all queries; merge new results into existing CSV |

**`--fresh` flag:** Deletes the state file and overwrites `accounts.csv`. Use when you want a clean re-scan regardless of prior state.

**Incremental merge:** On an incremental run, the existing `accounts.csv` is read into memory, new records are merged by `root_domain` (updating `last_seen`, `email_count`), and the file is rewritten. Rows for services with no new email are preserved unchanged.

**Note on `processed_ids`:** This list only covers the *current or most recently interrupted* scan — it is reset at the start of each new full scan. It is not a permanent log of every message ever processed.

---

## Google Cloud OAuth Setup (documented in README)

Every user must create their own Google Cloud project — sharing a single `credentials.json` in a public repo would violate Google's Terms of Service and expose all users through a single revocable credential.

**Steps (README will describe each screen in exact detail):**

1. Go to `console.cloud.google.com` → "New Project" → name it anything
2. Search "Gmail API" → Enable it
3. Left sidebar → "OAuth consent screen" → **External** → fill in app name + your email → under Scopes, add `https://www.googleapis.com/auth/gmail.readonly` → **Add yourself as a Test User** (required — without this, the OAuth flow will fail)
4. "Credentials" → "Create Credentials" → "OAuth client ID" → **Desktop app** → Download JSON → save as `credentials.json` in the project root
5. Run `python setup_check.py` to validate before the first scan

**The "unverified app" warning:**
Google shows a warning on first login because the OAuth app hasn't been through Google's verification process. This is expected for self-hosted tools. Click "Advanced" → "Go to [app name] (unsafe)". This is safe: the user is both the developer and the sole user of their own OAuth app.

**Why not reduce this burden?**

| Option | Problem |
|---|---|
| Ship a shared `credentials.json` | Violates Google ToS; one revocation breaks all users |
| gcloud CLI setup script | gcloud is its own installation hurdle |
| Docker | Still requires OAuth setup; adds Docker dependency |

**Best mitigation:** Detailed step-by-step README with screenshots + `setup_check.py` that catches common mistakes before the first scan.

---

## Search Queries (config.yaml defaults)

The query list is fully configurable — users can add, remove, or replace any entry.

```yaml
search_queries:
  - "subject:verify your email"
  - "subject:confirm your email"
  - "subject:welcome to"
  - "subject:your account"
  - "subject:reset your password"
  - "subject:account created"
  - "subject:email confirmation"
  - "unsubscribe"
  - "subject:activate your account"
  - "subject:complete your registration"

max_results: 5000        # total unique messages across all queries; warns and stops when reached; null = unlimited
output_sqlite: false     # set to true to also write output/accounts.db
```

**Cross-query deduplication:** `gmail_client.py` collects message IDs across all queries into a set before fetching any headers. A message matching multiple queries is fetched and processed exactly once. `max_results` is a cap on this deduplicated set, not per query.

---

## ESP Resolution Strategy

Many transactional emails originate from email service providers (ESPs) acting as relay infrastructure (e.g., SendGrid, Amazon SES). In these cases the `From` domain belongs to the ESP, not the actual business. `esp_map.py` uses `data/esp_domains.json` to detect ESP domains and resolve the real sender.

`esp_domains.json` is a static file maintained via community PRs. There is no auto-update mechanism — that would require a remote fetch and break the "no external calls" guarantee.

```json
{
  "sendgrid.net":     {"type": "esp", "resolve_from": ["reply-to", "display-name"]},
  "amazonses.com":    {"type": "esp", "resolve_from": ["reply-to", "display-name"]},
  "list-manage.com":  {"type": "esp", "resolve_from": ["display-name"]},
  "mailchimp.com":    {"type": "esp", "resolve_from": ["display-name"]},
  "klaviyo.com":      {"type": "esp", "resolve_from": ["reply-to", "display-name"]},
  "exacttarget.com":  {"type": "esp", "resolve_from": ["reply-to"]},
  "postmarkapp.com":  {"type": "esp", "resolve_from": ["reply-to", "display-name"]}
}
```

**Resolution logic (applied to every message):**

```
Step 1 — Extract the From domain.

Step 2 — If the From domain is in esp_domains.json:
    a. Try Reply-To domain (if listed in resolve_from)
    b. Try the display-name portion of the From header (e.g., "Spotify via SendGrid" → "Spotify")
    → Use the first one that yields a recognizable name/domain

Step 3 — Normalize the resolved (or original) domain:
    Strip subdomains: mail.spotify.com → spotify.com
    Derive service name: spotify.com → Spotify

Step 4 — If no name can be resolved (generic display name like "Noreply", no Reply-To):
    Keep the row. Use the root domain as the service name. Do not drop it.
```

**Grouping key:** `root_domain`. If two messages resolve to the same `root_domain`, they belong to the same service entry regardless of how the service name was derived. The stored `service` name is taken from the first resolved record for that domain.

**Accuracy limits (documented in README):**
- False positives: promotional emails from services where the user has no account
- False negatives: services that only send email types not covered by the search queries
- Unresolved ESP emails: kept with domain as service name; users should scrutinize these

---

## CSV Output Schema

```
service, domain, first_seen, last_seen, email_count, decision, deletion_url
```

- `service`: resolved service name (may be a bare domain if resolution failed)
- `domain`: root domain used as the grouping key
- `first_seen` / `last_seen`: ISO 8601 dates of the earliest and most recent matched email
- `email_count`: number of matched emails from this service
- `decision`: blank — user fills in (e.g., "keep", "delete", "already deleted")
- `deletion_url`: blank for v1 — user fills in; community-maintained map is a future follow-up

Note: `login_method_guess` was considered for v1 but removed — email headers contain no reliable signal for this.

---

## Privacy & Security

**In code:**
- `.gitignore` excludes `credentials.json` and the entire `output/` directory (which contains `token.json`, `accounts.csv`, and `.scan_state.json`)
- `setup_check.py` warns if `credentials.json` is tracked by git
- `gmail.readonly` scope is requested at OAuth runtime — the tool cannot modify or send email
- Only message headers (From, Reply-To, Subject, Date) are fetched; email bodies are never requested

**Credential risk levels (explained in README):**
- `token.json`: high sensitivity — grants live read access to the user's Gmail. Treat like a password. Stored inside `output/` which is gitignored.
- `credentials.json`: lower sensitivity — contains the OAuth client ID and secret for the user's own Google Cloud app. It does not grant inbox access on its own; access still requires the user to complete the OAuth flow. Should still not be committed or shared.

**In README:**
- Explicit statement: "This tool makes no network requests except to Google's Gmail API from your machine. No data ever leaves your computer."
- Step-by-step explanation of what each credential file is and why to protect it

---

## Decisions Log

| Topic | Decision | Notes |
|---|---|---|
| Module split | `esp_map.py` and `deduplicator.py` are separate | Resolution and grouping are distinct operations |
| `setup_check.py` | Standalone script | Users run it explicitly before first use |
| "unsubscribe" query | In defaults | Broad but cross-query dedup handles redundancy |
| Query config | Fully configurable | Users can add, remove, or replace any query |
| `max_results` scope | Total unique messages across all queries | Not per query |
| ESP map maintenance | Static file, community PRs | Remote fetch would break no-external-calls guarantee |
| Grouping key | `root_domain` | Service name is derived from domain; domain is the stable key |
| Failed ESP resolution | Keep row with domain as service name | Never drop rows silently |
| SQLite | Opt-in via `output_sqlite: false` | CSV is always generated |
| Deletion URLs | Blank for v1 | Community map as future follow-up |
| Python version | 3.10+ | match/case, better type hints |
| Scan cap | 5000 total unique messages, with warning | `null` in config for unlimited |
| Re-run behavior | Incremental by default | `after:YYYY/MM/DD` filter from `last_scan_completed_at`; `--fresh` to override |
| Incremental merge | Read CSV → merge by `root_domain` → rewrite | Preserves untouched rows; updates counts and last_seen |

---

## Implementation Chunks

### Chunk 1 — Project scaffold
Files: `.gitignore`, `requirements.txt`, `config.yaml`, `LICENSE`, `src/__init__.py`, `tests/`, `output/.gitkeep`, `scanner.py` stub (loads config, prints usage)

**Testable:** `git status` shows nothing in `output/` or `credentials.json` tracked; `python scanner.py` loads config without error.

### Chunk 2 — Auth + pre-flight check
Files: `src/auth.py`, `setup_check.py`

- `auth.py`: OAuth installed-app flow using `google-auth-oauthlib`; writes token to `output/token.json`; refreshes on expiry
- `setup_check.py`: checks `credentials.json` exists and is not git-tracked; checks `output/` is writable; prints pass/fail for each check

**Testable:** `python setup_check.py` catches missing or git-tracked `credentials.json`; completing the OAuth flow creates `output/token.json` and does not create it in the project root.

### Chunk 3 — Gmail client + extraction
Files: `src/gmail_client.py`, `src/extractor.py`

- `gmail_client.py`: executes all configured queries, paginates with `messages.list`, collects unique message IDs into a set, respects `max_results` cap (with warning when hit), batch-fetches headers via `messages.get` with `format=metadata`, retries with exponential backoff on 429/5xx
- `extractor.py`: parses the raw `payload.headers` list from the API response into a structured dict: `{message_id, from_addr, reply_to, subject, date}`

**Testable:** Run against a real inbox with `max_results: 10` and print raw extracted records. Requires chunk 2 (auth) to be complete.

### Chunk 4 — ESP resolution
Files: `data/esp_domains.json`, `src/esp_map.py`, `tests/test_esp_map.py`

- `esp_domains.json`: seed with the 7 ESPs listed in the plan
- `esp_map.py`: implements the 4-step resolution logic; returns `{service_name, root_domain}` for every input record

**Testable:** Unit tests with synthetic records for known ESP senders (SendGrid, SES, Mailchimp), a first-party sender (`spotify.com`), and an unresolvable generic sender.

### Chunk 5 — Grouping + output
Files: `src/deduplicator.py`, `src/output.py`, `tests/test_deduplicator.py`

- `deduplicator.py`: groups resolved records by `root_domain`; tracks `first_seen`, `last_seen`, `email_count`; service name is taken from the first record for each domain
- `output.py`: writes `accounts.csv` with the defined schema; writes `output/accounts.db` if `output_sqlite: true`; handles incremental merge (read existing CSV → merge by `root_domain` → rewrite)

**Testable:** Feed synthetic resolved records; assert grouping collapses duplicates correctly; assert CSV schema and row count.

### Chunk 6 — State, incremental logic, wire-up
Files: `src/state.py`, updates to `gmail_client.py` and `scanner.py`

- `state.py`: read/write `output/.scan_state.json`; helper to check if prior scan was interrupted vs. completed
- `gmail_client.py`: on incremental run, convert `last_scan_completed_at` (ISO 8601) to `YYYY/MM/DD` and append `after:<date>` to all queries
- `scanner.py`: wire all modules end-to-end; handle `--fresh` (delete state + overwrite output); print progress (current query name, messages fetched so far, services found so far)

**Testable:**
- Full scan → interrupt (Ctrl-C) → re-run → resumes without duplicate rows
- Full scan → re-run → only emails newer than `last_scan_completed_at` fetched; existing CSV rows preserved and updated
- `--fresh` → state reset, fresh output

---

## Verification Plan

1. `python setup_check.py` with missing `credentials.json` → clear error message
2. `python setup_check.py` with `credentials.json` git-tracked → clear warning
3. Complete OAuth flow → `output/token.json` created; no `token.json` in project root
4. Run `python scanner.py` with `max_results: 10` → `output/accounts.csv` written with correct schema
5. Run with `max_results: 5000` and a large inbox → warning printed when cap is reached
6. Interrupt scan mid-run (Ctrl-C) → re-run → resumes from checkpoint, no duplicate rows in output
7. Complete a full scan → re-run without `--fresh` → only new emails fetched; existing rows preserved
8. Run `python scanner.py --fresh` after a completed scan → state file reset, output overwritten
9. `git status` shows nothing in `output/` and no `credentials.json` tracked
10. `output_sqlite: true` in config → `output/accounts.db` created alongside CSV
