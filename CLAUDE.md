# CLAUDE.md

## Project: Delete Me

Local Python tool that aggregates all online accounts tied to a user's email address, so they can review and manually delete the ones they no longer want. Infers accounts from Gmail signup/welcome/verification emails and outputs a CSV the user annotates with keep/delete decisions. Users supply their own Google Cloud OAuth credentials and run everything on their own machine. See PLAN.md for full architecture and implementation chunks.

## Hard Constraints

- No external network calls except to Google's Gmail API from the user's machine
- Gmail access is read-only (`gmail.readonly` scope) — never request write or send scopes
- Only message headers are fetched (From, Reply-To, Subject, Date) — never request email bodies
- No telemetry, analytics, or shared infrastructure of any kind
- Each user uses their own Google Cloud project and OAuth credentials — never ship a shared `credentials.json`
- Cross-platform: Windows, macOS, Linux — avoid platform-specific code

## Non-Obvious Decisions

- `esp_domains.json` is a static file with no auto-update mechanism — a remote fetch would break the no-external-calls guarantee
- `max_results` caps the total deduplicated message set across all queries, not per query
- Failed ESP resolution rows are kept with the domain as the service name — never drop rows silently
- Grouping key is `root_domain`, not service name — service name is derived and may vary; domain is stable
- `processed_ids` in the state file only covers the current or most recently interrupted scan, not a permanent log

## Key File Locations

- Entry point: `scanner.py`
- Pre-flight validator: `setup_check.py`
- OAuth + token management: `src/auth.py`
- Scan state (checkpoint + incremental): `src/state.py` → `output/.scan_state.json`
- ESP relay domain map: `data/esp_domains.json`
- User credentials (gitignored): `credentials.json`, `output/token.json`
- Output (gitignored): `output/accounts.csv`, `output/accounts.db`

## Run Commands

```bash
python setup_check.py          # validate credentials and environment before first scan
python scanner.py              # normal run (incremental if prior scan completed)
python scanner.py --fresh      # ignore prior state, full re-scan, overwrite output
python scanner.py --check      # run setup checks inline and exit
python -m pytest tests/        # run tests
```

## Python Version

3.10+ required — uses match/case and modern type hints.
