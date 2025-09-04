import os, json, yaml
from dataclasses import dataclass
from typing import Any, Dict, Optional
from dotenv import load_dotenv

CONFIG_PATH = os.environ.get(
    "IAL_CONFIG",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "config.yaml")
)
STATE_PATH = os.environ.get(
    "IAL_STATE",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "state.json")
)

load_dotenv()

@dataclass
class Settings:
    app: Dict[str, Any]
    gmail: Dict[str, Any]
    nlp: Dict[str, Any]
    nlp_transformer: Dict[str, Any] | None
    nlp_spacy: Dict[str, Any] | None
    sheets: Dict[str, Any]
    calendar: Dict[str, Any]
    spreadsheet_id: Optional[str] = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")

def load_settings() -> Settings:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # we have to ensure optional blocks exist
    cfg.setdefault("nlp_transformer", {})
    cfg.setdefault("nlp_spacy", {})
    return Settings(**cfg)

def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {"last_message_id": None, "processed_ids": []}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
