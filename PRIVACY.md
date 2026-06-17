# Privacy Statement

This tool is designed so that your email data never leaves your computer.

## What this tool does

- Connects to Google's Gmail API **from your machine** using credentials you create in your own Google Cloud project
- Reads only message **headers** (From, Reply-To, Subject, Date) — email bodies are never requested
- Writes results to a local CSV file (`output/accounts.csv`) on your machine

## What this tool does not do

- Send any data to any server other than Google's Gmail API
- Store, transmit, or log your email headers anywhere outside your machine
- Request write, send, or delete permissions — access is strictly read-only (`gmail.readonly` scope)
- Use shared credentials or a central OAuth app — each user creates their own Google Cloud project

## Credential files

| File | Sensitivity | Notes |
|---|---|---|
| `credentials.json` | Medium | OAuth client ID and secret for your own Google Cloud app. Does not grant inbox access on its own. Keep it out of git. |
| `output/token.json` | High | Live access token for your Gmail account. Treat it like a password. Stored in `output/` which is gitignored. |

Both files stay on your machine. Neither is transmitted anywhere except as part of the standard Google OAuth flow.

## Verification

- `.gitignore` excludes `credentials.json` and the entire `output/` directory
- `python setup_check.py` warns if `credentials.json` is accidentally tracked by git
- You can inspect all network calls this tool makes — the only outbound connections are to `gmail.googleapis.com`
