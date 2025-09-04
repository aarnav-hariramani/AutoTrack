from datetime import datetime, timedelta
from typing import Optional
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "credentials")
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.json")

SCOPES_CAL = ["https://www.googleapis.com/auth/calendar.events"]

def _ensure_cal_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES_CAL)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES_CAL)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return creds

def create_followup_event(calendar_id: str, company: str, role: str, followup_dt: datetime, email_id: str, dry_run: bool = False) -> Optional[str]:
    if dry_run:
        print(f"[DRY-RUN] Would create calendar event on {followup_dt} for {company} — {role}")
        return None
    creds = _ensure_cal_creds()
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": f"Follow up: {company} — {role}",
        "description": f"Auto-created by Internship Logger\nEmailId: {email_id}",
        "start": {"date": followup_dt.date().isoformat()},
        "end": {"date": (followup_dt.date() + timedelta(days=1)).isoformat()},
    }
    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created.get("id")
