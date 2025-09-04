from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime

import dateparser
try:
    from dateparser.search import search_dates
except Exception:
    search_dates = None

from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

def _clean(s: str) -> str:
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s or "")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def _texts(subject: str, body: str) -> str:
    return _clean(subject) + "\n\n" + _clean(body)

_ZS = None
_NER = None
_EMB = None

def _ensure_models(zs_name: str, ner_name: str, emb_name: str):
    global _ZS, _NER, _EMB
    if _ZS is None:
        _ZS = pipeline("zero-shot-classification", model=zs_name)
    if _NER is None:
        _NER = pipeline("ner", model=ner_name, aggregation_strategy="simple")
    if _EMB is None:
        _EMB = SentenceTransformer(emb_name)
    return _ZS, _NER, _EMB

def extract_company(subject: str, from_header: str, body: str, ner_pipe) -> str:
    sub_ents = ner_pipe(_clean(subject)) or []
    orgs = [e["word"] for e in sub_ents if e.get("entity_group") == "ORG"]
    if orgs:
        return orgs[0]
    body_ents = ner_pipe(_clean(body[:4000])) or []
    orgs = [e["word"] for e in body_ents if e.get("entity_group") == "ORG"]
    if orgs:
        return orgs[0]
    m = re.search(r"\bat\s+([A-Z][A-Za-z0-9&.\- ]{2,})", subject)
    if m:
        return m.group(1).strip(" -—|:")
    m = re.search(r"^(.*?)(?:<|$)", from_header)
    if m:
        cand = m.group(1).strip().strip('"')
        if cand:
            return cand
    dom = re.search(r"@([^>]+)>?$", from_header or "")
    if dom and "netflix.com" in dom.group(1).lower():
        return "Netflix"
    return "Unknown"

def _candidate_role_phrases(subject: str, body: str) -> List[str]:
    txt = _texts(subject, body)
    cands = set()
    for m in re.finditer(r"([A-Za-z/ &\-]{3,80}?\b(?:internship|intern)\b)", txt, flags=re.I):
        phrase = m.group(1).strip(" -—|:").lower()
        phrase = re.sub(r"\s+", " ", phrase)
        cands.add(phrase)
    for m in re.finditer(r"for the ([A-Za-z0-9/ &\-]{3,80}?) position", txt, flags=re.I):
        cands.add(m.group(1).strip(" -—|:").lower())
    return list(cands)[:20] or ["intern"]

def extract_role(subject: str, body: str, emb_model, probe_phrases: List[str]) -> str:
    cands = _candidate_role_phrases(subject, body)
    emb_cands = emb_model.encode(cands, convert_to_tensor=True, normalize_embeddings=True)
    emb_probe = emb_model.encode(probe_phrases, convert_to_tensor=True, normalize_embeddings=True)
    sim = util.cos_sim(emb_cands, emb_probe).max(dim=1).values
    best_idx = int(sim.argmax().item())
    best = cands[best_idx]
    best = re.sub(r"\bml\b", "ML", best, flags=re.I)
    best = re.sub(r"\bai\b", "AI", best, flags=re.I)
    return best.title()

def extract_date(subject: str, body: str, fallback: datetime) -> datetime:
    text = _texts(subject, body)
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

def parse_email_transformer(cfg_block: Dict[str, Any], subject: str, from_header: str, body: str, fallback_date: datetime) -> Dict[str, Any]:
    zs_name = cfg_block.get("zero_shot_model", "facebook/bart-large-mnli")
    ner_name = cfg_block.get("ner_model", "dslim/bert-base-NER")
    emb_name = cfg_block.get("embed_model", "sentence-transformers/all-MiniLM-L6-v2")
    labels = cfg_block.get("status_labels", ["Applied","Interview","OA","Rejected","Offer","Other"])
    probes = cfg_block.get("role_probe_phrases", ["software engineering intern","data science intern","machine learning intern","research intern","security intern"])

    ZS, NER, EMB = _ensure_models(zs_name, ner_name, emb_name)

    status = ZS(_texts(subject, body), labels, multi_label=False)["labels"][0]
    company = extract_company(subject, from_header, body, NER)
    role = extract_role(subject, body, EMB, probes)
    applied = extract_date(subject, body, fallback_date)

    return {"status": status, "company": company, "role": role, "date_applied": applied}
