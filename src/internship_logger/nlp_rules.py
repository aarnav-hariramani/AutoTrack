import re
from datetime import datetime
import dateparser

STATUS_RULES = [
    ("Rejected", r"(?:we regret|unfortunately|not moving forward|declined)"),
    ("Interview", r"(?:interview|schedule time|book a time|phone screen|screening)"),
    ("OA", r"(?:online assessment|coding challenge|hackerrank|codility|assessment)"),
    ("Applied", r"(?:application confirmation|application received|thank you for applying|thank you for your application|we(?:\s+have)?\s+received your application|we'?ve received your application|confirm that your application|has been received|thank you for your interest)"),
]

ROLE_HINT = r"(software|swe|data|machine\s*learning|ml|ai|computer|backend|frontend)[^.\n]{0,40}\b(intern|internship)\b"

def classify_status(subject: str, body: str) -> str:
    text = f"{subject}\n{body}".lower()
    for label, pattern in STATUS_RULES:
        if re.search(pattern, text):
            return label
    return "Other"

def extract_company(subject: str, from_header: str, body: str) -> str:
    m = re.search(r"\bat\s+([A-Za-z0-9&.\- ]{2,})", subject)
    if m:
        return m.group(1).strip(" -—|:")
    m = re.search(r"application (?:to|for)\s+([A-Za-z0-9&.\- ]{2,})", subject, flags=re.I)
    if m:
        return m.group(1).strip(" -—|:")
    m = re.search(r"^(.*?)(?:<|$)", from_header)
    if m:
        return m.group(1).strip().strip('"')
    return "Unknown"

def extract_role(subject: str, body: str) -> str:
    m = re.search(ROLE_HINT, subject, flags=re.I)
    if m:
        return m.group(0).strip(" -—|:")
    m = re.search(ROLE_HINT, body, flags=re.I)
    if m:
        return m.group(0).strip(" -—|:")
    m = re.search(r"for the (.*?) position", subject, flags=re.I)
    if m:
        return m.group(1).strip(" -—|:")
    return "Intern"

def extract_date_applied(subject: str, body: str, fallback: datetime) -> datetime:
    m = re.search(r"(on|at|dated)\s+([A-Za-z0-9, /\-]+)", body, flags=re.I)
    if m:
        parsed = dateparser.parse(m.group(2))
        if parsed:
            return parsed
    return fallback
