import os, base64, re
from typing import List, Dict, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "credentials")
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.json")

# Request ALL scopes once so token.json works everywhere
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar.events",
]

def _ensure_creds(scopes: List[str]) -> Credentials:
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    creds: Optional[Credentials] = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return creds

def get_gmail_service():
    creds = _ensure_creds(SCOPES)
    return build("gmail", "v1", credentials=creds)

def search_messages(query: str, max_results: int = 100) -> List[Dict[str, Any]]:
    service = get_gmail_service()
    results: List[Dict[str, Any]] = []
    try:
        resp = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        if "messages" in resp:
            results.extend(resp["messages"])
    except HttpError as e:
        print(f"[Gmail] HttpError: {e}")
    return results

def get_message(msg_id: str) -> Dict[str, Any]:
    service = get_gmail_service()
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()

def _get_header(headers: List[Dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""

def _decode_payload(data: str) -> str:
    # Gmail returns base64url-encoded data
    missing_padding = len(data) % 4
    if missing_padding:
        data += "=" * (4 - missing_padding)
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

def _clean_text(s: str) -> str:
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s or "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    return s.strip()

def extract_plain_text(message: Dict[str, Any]) -> Tuple[str, str, str]:
    """Returns: (subject, from_email, text)"""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    subject = _get_header(headers, "Subject")
    from_email = _get_header(headers, "From")

    body_text = ""
    def traverse(parts):
        nonlocal body_text
        for p in parts:
            mime = p.get("mimeType", "")
            if "parts" in p:
                traverse(p["parts"])
            elif mime == "text/plain" and "data" in p.get("body", {}):
                body_text += _decode_payload(p["body"]["data"]) + "\n"
            elif mime == "text/html" and "data" in p.get("body", {}):
                html = _decode_payload(p["body"]["data"])
                text = re.sub("<[^<]+?>", " ", html)
                body_text += text + "\n"

    if "parts" in payload:
        traverse(payload["parts"])
    else:
        body = payload.get("body", {})
        if "data" in body:
            body_text = _decode_payload(body["data"])

    # Clean
    subject = _clean_text(subject)
    from_email = _clean_text(from_email)
    body_text = _clean_text(body_text)
    return subject, from_email, body_text
