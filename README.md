# Internship Auto Logger — ML Edition
Reads Gmail for internship **application confirmations**, uses **ML (transformers)** to extract
**company / role / status / date**, logs to **Google Sheets**, and creates **Calendar** follow-ups.

## Engines
- `transformer` (default): zero-shot classification (status), NER (company), sentence-embeddings (role)
- `spacy`: classic spaCy + EntityRuler
- `rules`: minimal regex fallback

## Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# (spaCy model only if you choose nlp.engine=spacy)
python -m spacy download en_core_web_md
cp .env.example .env
```
Put your OAuth client JSON at `credentials/client_secret.json`.

## Run
Dry-run (no Calendar events):
```bash
python -m src.internship_logger.main --dry-run
```
Real run:
```bash
# ensure config.yaml has app.dry_run: false
python -m src.internship_logger.main
```

## Notes
- First run opens a browser for consent; this creates `credentials/token.json`.
- Service Account (Sheets only) is supported via `GSPREAD_SERVICE_ACCOUNT_JSON` in `.env`.
- State lives in `data/state.json` and prevents reprocessing; clear it to re-run on the same emails.
