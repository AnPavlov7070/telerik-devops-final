# FastAPI Email Fetch Service

Small internal service that fetches emails from an IMAP inbox for a given time window, parses them (without downloading/including attachments), deduplicates against previous batches, and returns structured JSON.

## Features

- **POST `/fetch`** with a `[since, until]` UTC window (ISO-8601).
- Robust IMAP search (date-based) + precise filtering by `INTERNALDATE`.
- Parses subject, from/to/cc, dates, snippet, plain-text body (HTML converted if needed), and **attachments metadata only** (filename, type, size).
- Detects Deal ID via regex: `\[Сделка:([A-Za-z0-9]{4,6})\]`.
- Dedup using Message-ID or SHA256 of raw RFC822 if Message-ID absent.
- Atomic state writes and a simple file lock (`state.lock`).
- Structured logging and clear error handling.

## Config (Environment Variables)

| Variable      | Description                           | Default             |
|---------------|---------------------------------------|---------------------|
| `IMAP_HOST`   | IMAP server host                      | **required**        |
| `IMAP_PORT`   | IMAP server port                      | `993`               |
| `IMAP_SSL`    | `true` or `false`                     | `true`              |
| `IMAP_USERNAME` | IMAP username                       | **required**        |
| `IMAP_PASSWORD` | IMAP password                       | **required**        |
| `IMAP_FOLDER` | Mailbox folder                        | `INBOX`             |
| `STATE_PATH`  | Path to state JSON                    | `./state/state.json`|

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export IMAP_HOST=imap.example.com
export IMAP_PORT=993
export IMAP_SSL=true
export IMAP_USERNAME="user@example.com"
export IMAP_PASSWORD="yourpassword"
export IMAP_FOLDER=INBOX
export STATE_PATH=./state/state.json

uvicorn app.main:app --host 0.0.0.0 --port 8080