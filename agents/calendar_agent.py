# agents/calendar_agent.py

from tools.calendar_tools import get_freebusy_slots, create_calendar_event
from typing import Dict
from datetime import datetime, timedelta
import pytz
from dateutil import parser

# 👇 Import decode_text to handle base64
from agents.email_agent import decode_text

def is_time_conflicting(start: datetime, end: datetime, busy_times: list) -> bool:
    for slot in busy_times:
        busy_start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
        busy_end   = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
        if not (end <= busy_start or start >= busy_end):
            return True
    return False

def extract_meeting_datetime_from_email(email_body: str, tz: pytz.timezone) -> datetime | None:
    try:
        print("🔍 Trying to parse this email body:", email_body)
        dt = parser.parse(email_body, fuzzy=True)
        return tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)
    except Exception as e:
        print("❌ Failed to parse datetime:", str(e))
        return None

def calendar_scheduler_agent(state: Dict) -> Dict:
    meeting_email = next(
        (e for e in state.get("inbox", []) if "meeting" in e.get("subject", "").lower()),
        None
    )
    if not meeting_email:
        state["calendar_event"] = "No meeting email found."
        return state

    # 🕒 Config
    tz_str   = "America/Chicago"
    local_tz = pytz.timezone(tz_str)
    creds    = "/Users/anirudhsekar/Desktop/Coding/AI-CEO/backend/data/calendar_credentials.json"
    cal_id   = "anirudhsekar2008@gmail.com"
    duration = 60  # minutes

    # 📥 Decode the base64 email body
    try:
        raw_body = decode_text(meeting_email["body"])
    except Exception as e:
        raw_body = ""
        print("❌ Failed to decode email body:", str(e))

    print("✅ Decoded email body:", raw_body)

    # 🧠 Parse datetime
    start_dt = extract_meeting_datetime_from_email(raw_body, local_tz)
    if not start_dt:
        state["calendar_event"] = "Could not parse meeting time."
        state["action"]         = "calendar_failed"
        return state
    end_dt = start_dt + timedelta(minutes=duration)

    # 📅 Get busy slots
    utc = pytz.UTC
    day_min = start_dt.astimezone(utc).replace(hour=0, minute=0, second=0, microsecond=0)
    day_max = start_dt.astimezone(utc).replace(hour=23, minute=59, second=59)
    busy    = get_freebusy_slots(creds, day_min.isoformat(), day_max.isoformat(), cal_id)

    # ⚠️ Conflict check
    if is_time_conflicting(start_dt, end_dt, busy):
        suggestion = None
        for h in range(9, 17):
            cand_naive = start_dt.replace(hour=h, minute=0, second=0, microsecond=0)
            cand = local_tz.localize(cand_naive) if cand_naive.tzinfo is None else cand_naive
            if not is_time_conflicting(cand, cand + timedelta(minutes=duration), busy):
                suggestion = cand
                break

        if not suggestion:
            state["calendar_event"] = "No free slots available today."
            state["action"]         = "calendar_failed"
            return state

        state["suggested_time"] = {
            "start": suggestion.strftime("%Y-%m-%dT%H:%M:%S"),
            "end":   (suggestion + timedelta(minutes=duration)).strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": tz_str
        }
        state["action"] = "suggest_time"
        state["calendar_event"] = (
            f"Requested slot busy. How about {suggestion.strftime('%A, %b %d at %I:%M %p')} CST?"
        )
        return state

    # ✅ No conflict or confirmed suggestion
    if state.get("action") == "confirm_suggestion" or not is_time_conflicting(start_dt, end_dt, busy):
        if state.get("action") == "confirm_suggestion":
            sd = state["suggested_time"]
            start_str, end_str = sd["start"], sd["end"]
        else:
            start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
            end_str   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        event = create_calendar_event({
            "summary":     "Scheduled Meeting",
            "description": "Auto‑scheduled from email.",
            "start":       {"dateTime": start_str, "timeZone": tz_str},
            "end":         {"dateTime": end_str,   "timeZone": tz_str},
        }, creds, cal_id)

        link = event.get("htmlLink") if event else None
        state["calendar_event"] = f"Meeting scheduled: {link or 'link unavailable'}"
        state["action"] = "calendar_updated"
        return state

    # Fallback
    state["calendar_event"] = "Unexpected state."
    return state
