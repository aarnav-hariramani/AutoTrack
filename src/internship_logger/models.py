from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Application:
    email_id: str
    thread_id: str
    company: str
    role: str
    status: str                 # Applied | Interview | OA | Rejected | Offer | Other
    date_applied: datetime
    source: str                 # Workday | Lever | Greenhouse | Email | Other
    followup_due: Optional[datetime] = None
