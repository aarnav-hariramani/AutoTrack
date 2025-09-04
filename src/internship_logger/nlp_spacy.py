import re
from typing import List, Dict, Any
from datetime import datetime
import dateparser
try:
    from dateparser.search import search_dates
except Exception:
    search_dates = None

import spacy
from spacy.language import Language
from spacy.pipeline import EntityRuler

STATUS_RULES = [
    ("Rejected", r"(?:\bwe regret\b|\bunfortunately\b|\bnot moving forward\b|\bdeclined\b)"),
    ("Interview", r"(?:\binterview\b|\bschedule time\b|\bbook a time\b|\bphone screen\b|\bscreening\b)"),
    ("OA", r"(?:\bonline assessment\b|\bcoding challenge\b|\bhackerrank\b|\bcodility\b|\bassessment\b)"),
    ("Applied", r"(?:\bapplication confirmation\b|\bapplication received\b|\bthank you for applying\b|\bthank you for your application\b|\bwe(?:\s+have)?\s+received your application\b|\bwe'?ve received your application\b|\bconfirm that your application\b|\bhas been received\b|\bthank you for your interest\b)"),
]

def classify_status(subject: str, body: str) -> str:
    text = f"{subject}\n{body}".lower()
    for label, pattern in STATUS_RULES:
        if re.search(pattern, text):
            return label
    return "Other"

def build_spacy(model_name: str, role_synonyms: List[str]) -> Language:
    nlp = spacy.load(model_name)
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    patterns = []
    role_heads = [{"LOWER": {"IN": ["engineering", "engineer", "science", "scientist", "developer"]}, "OP": "?"}]
    intern_tails = [{"LOWER": {"IN": ["intern", "internship"]}}]
    for syn in role_synonyms:
        toks = syn.split()
        head = [{"LOWER": t} for t in toks]
        pattern = head + role_heads + intern_tails
        patterns.append({"label": "ROLE", "pattern": pattern})
    ruler.add_patterns(patterns)
    return nlp

def extract_company_spacy(nlp: Language, subject: str, from_header: str, body: str) -> str:
    doc_subj = nlp(subject)
    orgs = [ent.text.strip() for ent in doc_subj.ents if ent.label_ == "ORG"]
    if orgs:
        return orgs[0]
    m = re.search(r"\bat\s+([A-Z][A-Za-z0-9&.\- ]{2,})", subject)
    if m:
        return m.group(1).strip(" -—|:")
    doc_body = nlp(body[:4000])
    orgs = [ent.text.strip() for ent in doc_body.ents if ent.label_ == "ORG"]
    if orgs:
        return orgs[0]
    m = re.search(r"^(.*?)(?:<|$)", from_header)
    if m:
        cand = m.group(1).strip().strip('"')
        if cand:
            return cand
    dom = re.search(r"@([^>]+)>?$", from_header or "")
    if dom and "netflix.com" in dom.group(1).lower():
        return "Netflix"
    return "Unknown"

def extract_role_spacy(nlp: Language, subject: str, body: str) -> str:
    doc_subj = nlp(subject)
    roles = [ent.text.strip(" -—|:") for ent in doc_subj.ents if ent.label_ == "ROLE"]
    if roles:
        return roles[0]
    doc_body = nlp(body[:1500])
    roles = [ent.text.strip(" -—|:") for ent in doc_body.ents if ent.label_ == "ROLE"]
    if roles:
        return roles[0]
    m = re.search(r"for the (.*?) position", subject, flags=re.I)
    if m:
        return m.group(1).strip(" -—|:")
    return "Intern"

def extract_date_spacy(subject: str, body: str, fallback: datetime) -> datetime:
    text = subject + "\n" + body
    if search_dates:
        try:
            found = search_dates(text, settings={"PREFER_DATES_FROM":"past"})
            if found:
                for _, dt in found:
                    if abs((fallback - dt).days) <= 365:
                        return dt
        except Exception:
            pass
    m = re.search(r"(?:on|dated)\s+([A-Za-z0-9, /\-]+)", text, flags=re.I)
    if m:
        parsed = dateparser.parse(m.group(1))
        if parsed:
            return parsed
    return fallback

def parse_email(nlp: Language, subject: str, from_header: str, body: str, fallback_date: datetime) -> Dict[str, Any]:
    status = classify_status(subject, body)
    company = extract_company_spacy(nlp, subject, from_header, body)
    role = extract_role_spacy(nlp, subject, body)
    applied = extract_date_spacy(subject, body, fallback_date)
    return {"status": status, "company": company, "role": role, "date_applied": applied}
