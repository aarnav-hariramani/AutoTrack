import argparse
from datetime import datetime, timedelta, timezone
import pytz

from .settings import load_settings, load_state, save_state
from .email_client import search_messages, get_message, extract_plain_text
# Fallbacks
from .nlp_rules import classify_status as classify_status_rules, extract_company as extract_company_rules, extract_role as extract_role_rules, extract_date_applied as extract_date_rules
# spaCy + transformer
from .nlp_spacy import build_spacy, parse_email as parse_email_spacy
from .nlp_xfmr import parse_email_transformer

_SPACY_NLP = None

def _ensure_spacy(cfg):
    global _SPACY_NLP
    if _SPACY_NLP is None:
        model = (cfg.nlp_spacy or {}).get("spacy_model", "en_core_web_md")
        synonyms = (cfg.nlp_spacy or {}).get("role_synonyms", ["software","data","ml","ai"])
        _SPACY_NLP = build_spacy(model, synonyms)
    return _SPACY_NLP

def process_once(dry_run: bool = False) -> None:
    cfg = load_settings()
    state = load_state()
    tz = pytz.timezone(cfg.app.get("timezone", "UTC"))

    query = cfg.gmail["query"]
    msg_refs = search_messages(query=query, max_results=200)

    ws = __import__(".".join(["src","internship_logger","sheets_writer"]), fromlist=["ensure_sheet"]).ensure_sheet(
        cfg.sheets["spreadsheet_name"], cfg.sheets["worksheet_name"]
    )
    upsert_row = __import__(".".join(["src","internship_logger","sheets_writer"]), fromlist=["upsert_row"]).upsert_row

    processed_ids = set(state.get("processed_ids", []))
    engine = (cfg.nlp or {}).get("engine", "transformer")

    if engine == "spacy":
        nlp = _ensure_spacy(cfg)

    for ref in msg_refs:
        msg_id = ref["id"]
        if msg_id in processed_ids:
            continue
        msg = get_message(msg_id)
        internal_date_ms = int(msg.get("internalDate", "0"))
        internal_dt = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc).astimezone(tz)

        subject, from_email, body = extract_plain_text(msg)

        if engine == "transformer":
            parsed = parse_email_transformer(getattr(cfg, "nlp_transformer", {}), subject, from_email, body, internal_dt)
            status = parsed["status"]; company = parsed["company"]; role = parsed["role"]; applied_dt = parsed["date_applied"]
        elif engine == "spacy":
            parsed = parse_email_spacy(nlp, subject, from_email, body, internal_dt)
            status = parsed["status"]; company = parsed["company"]; role = parsed["role"]; applied_dt = parsed["date_applied"]
        else:
            status = classify_status_rules(subject, body)
            company = extract_company_rules(subject, from_email, body)
            role = extract_role_rules(subject, body)
            applied_dt = extract_date_rules(subject, body, internal_dt)

        followup_days = int(cfg.app.get("followup_days", 14))
        followup_dt = applied_dt + timedelta(days=followup_days)

        row = {
            "Timestamp": datetime.now(tz).isoformat(timespec="seconds"),
            "Company": company,
            "Role": role,
            "Date Applied": applied_dt.date().isoformat(),
            "Status": status,
            "Source": "Email",
            "EmailId": msg_id,
            "ThreadId": msg.get("threadId", ""),
            "FollowUp Due": followup_dt.date().isoformat(),
            "Notes": "",
        }
        print(f"[PROCESS] {company} | {role} | {status} | applied {applied_dt.date()} | follow-up {followup_dt.date()}")

        upsert_row(ws, row)

        if cfg.calendar.get("enabled", True):
            from .reminder import create_followup_event
            create_followup_event(
                calendar_id=cfg.calendar.get("calendar_id", "primary"),
                company=company,
                role=role,
                followup_dt=followup_dt,
                email_id=msg_id,
                dry_run=dry_run or bool(cfg.app.get("dry_run", False)),
            )

        processed_ids.add(msg_id)

    state["processed_ids"] = list(processed_ids)
    if msg_refs:
        state["last_message_id"] = msg_refs[0]["id"]
    save_state(state)

def main():
    parser = argparse.ArgumentParser(description="Internship Auto Logger (ML)")
    parser.add_argument("--dry-run", action="store_true", help="Do not create Calendar events; print instead")
    args = parser.parse_args()
    process_once(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
