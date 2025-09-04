import os
from typing import Dict, Any
import gspread

HEADERS = ["Timestamp","Company","Role","Date Applied","Status","Source","EmailId","ThreadId","FollowUp Due","Notes"]

def _get_client():
    sa_path = os.getenv("GSPREAD_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_path:
        return gspread.service_account(filename=sa_path)
    return gspread.oauth(
        credentials_filename=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "credentials", "client_secret.json"),
        authorized_user_filename=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "credentials", "token.json"),
    )

def ensure_sheet(spreadsheet_name: str, worksheet_name: str):
    gc = _get_client()
    try:
        sh = gc.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(spreadsheet_name)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)
    first_row = ws.row_values(1)
    if first_row != HEADERS:
        if not first_row:
            ws.append_row(HEADERS)
        else:
            ws.delete_rows(1)
            ws.insert_row(HEADERS, index=1)
    return ws

def upsert_row(ws, row: Dict[str, Any]) -> None:
    cells = ws.findall(row.get("EmailId","")) if row.get("EmailId") else []
    if cells:
        r = cells[0].row
        ordered = [row.get(h, "") for h in HEADERS]
        ws.update(f"A{r}:J{r}", [ordered])
    else:
        ws.append_row([row.get(h, "") for h in HEADERS])
