# Internship Auto Logger (Slim + spaCy)
A lean Python tool that:
1) reads Gmail for internship **application confirmations**,
2) uses **spaCy NLP** to extract **company**, **role**, **applied date**, **status**,
3) logs to **Google Sheets**, and
4) creates **follow-up reminders** in Google Calendar (optional).

## Quick Start
### 1) Google credentials
- **OAuth (default)**: Create an OAuth client (Desktop App) in Google Cloud and download `client_secret.json`. Put it at `credentials/client_secret.json`. On first run you'll consent in a browser; this creates `credentials/token.json`.
- **Service Account (Sheets only, optional)**: Create a service account JSON (e.g., `credentials/service_account.json`), share your spreadsheet with the SA email, and set `GSPREAD_SERVICE_ACCOUNT_JSON=credentials/service_account.json` in `.env`.

> All files under `credentials/` are **.gitignored**; the folder includes a `.gitkeep` just so it is created.

### 2) Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_md
cp .env.example .env
```

### 3) Configure
Edit `config.yaml`:
- `nlp.engine`: `"spacy"` (default) or `"rules"` for the old regex parser.
- `nlp.spacy_model`: e.g., `"en_core_web_md"`.
- `app.followup_days`: days after apply date to schedule a follow-up.
- `gmail.query`: tune search terms to your inbox.

### 4) Run
```bash
python -m src.internship_logger.main --dry-run
```
Remove `--dry-run` to create Calendar events.

## How NLP Works
- **spaCy NER + EntityRuler** detects:
  - `ORG` (company) from subject/body.
  - Custom `ROLE` entities like “software engineering intern,” “data science intern,” etc. (see `nlp_spacy.py` and `config.yaml` role synonyms).
- **Status** is determined via robust keyword patterns (Applied / Interview / OA / Rejected / Other).
- **Dates** are parsed with `dateparser` (falls back to Gmail internal timestamp).

## Credential Locations
- `credentials/client_secret.json` — Google OAuth client (Desktop App).
- `credentials/token.json` — Generated after first consent.
- `credentials/service_account.json` — (Optional) for Sheets service account use.
- `.env` — Non-secret toggles like `GSPREAD_SERVICE_ACCOUNT_JSON` and `GOOGLE_SHEETS_SPREADSHEET_ID`.

## Environment Variables
- `GOOGLE_SHEETS_SPREADSHEET_ID` — optional explicit Sheet ID (else find/create by name).
- `GSPREAD_SERVICE_ACCOUNT_JSON` — path to service account JSON (if using SA for Sheets).

## Notes
- Idempotent by Gmail Message ID — the same email won't be processed twice.
- State file at `data/state.json`.
- Tune Gmail search in `config.yaml` (e.g., add `"your application to"`).

## Troubleshooting
- If auth fails, delete `credentials/token.json` and re-run to re-consent.
- If role extraction is noisy, add more synonyms in `config.yaml` or extend patterns in `nlp_spacy.py`.
