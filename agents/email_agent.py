import ollama
import re
import base64
import quopri
import html
from datetime import datetime
from typing import Dict
from dateutil import parser
from email.header import decode_header
from tools.email_tools import send_email

last_run_key = "last_run_time"

def decode_text(text: str) -> str:
    """
    Aggressively decode raw bodies and headers:
    1) Try Base64 (pure bodies)
    2) Try quoted-printable
    3) Try MIME-encoded headers
    """
    if not text:
        return ""

    # 1) Pure Base64 body?
    try:
        # validate=True will reject invalid base64
        raw = base64.b64decode(text, validate=True)
        # decode to UTF-8, ignoring errors
        decoded = raw.decode("utf-8", errors="ignore")
        # if it looks like plaintext, return it
        if re.search(r"[A-Za-z0-9\s,.!?']", decoded):
            return decoded
    except Exception:
        pass

    # 2) Quoted-printable
    try:
        qp = quopri.decodestring(text)
        decoded = qp.decode("utf-8", errors="ignore")
        if re.search(r"[A-Za-z0-9\s,.!?']", decoded):
            return decoded
    except Exception:
        pass

    # 3) MIME-encoded header (=?UTF-8?B?...?=)
    try:
        parts = decode_header(text)
        decoded = "".join(
            part.decode(enc or "utf-8", errors="ignore") if isinstance(part, bytes) else part
            for part, enc in parts
        )
        return html.unescape(decoded.strip())
    except Exception:
        pass

    # 4) As a last resort, return original
    return text

def clean_body(text: str, max_len: int = 700) -> str:
    """
    Collapse whitespace, strip non-ASCII, truncate.
    Assumes `text` is already decoded.
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()[:max_len]

def fix_date_format(date_str: str) -> str:
    """
    Normalize something like '5-18-2025' or 'May 18, 2025'.
    """
    try:
        dt = parser.parse(date_str, fuzzy=True)
        return dt.strftime("%B %d, %Y")
    except Exception:
        return date_str

def email_summarization_agent(state: Dict = {}) -> Dict:
    now = datetime.now()
    last = state.get(last_run_key)
    if last and (now - last).total_seconds() < 300:
        state.update({
            "summary": "Summarization was already done within the last 5 minutes.",
            "action": "summary_skipped"
        })
        return state

    inbox = state.get("inbox", [])
    if not inbox:
        state.update({"summary": "No emails found.", "action": "summary_created"})
        return state

    summaries = []
    for idx, email in enumerate(inbox, start=1):
        frm  = decode_text(email.get("from",""))
        subj = decode_text(email.get("subject",""))
        raw  = email.get("body","")
        body = clean_body(decode_text(raw))

        # Special‑case meetings
        if "meeting" in subj.lower():
            m = re.search(
                r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b[A-Za-z]+ \d{1,2},? \d{4})\s*(?:at)?\s*(?P<time>\d{1,2}\s?(?:AM|PM))",
                body, re.IGNORECASE
            )
            if m:
                d_raw = m.group("date")
                t_raw = m.group("time")
                date_n = fix_date_format(d_raw)
                time_n = t_raw.upper().replace(" ", "")
                summaries.append(
                    f"{idx}. From: {frm}\n   Body: Proposes meeting on {date_n} at {time_n} to discuss business inquiries."
                )
                continue
            # fallback
            summaries.append(f"{idx}. From: {frm}\n   Body: Proposes a meeting—details in body.")
            continue

        # General case: LLM
        prompt = (
            "Summarize this email in 1–2 sentences, mentioning only the key point "
            "(invitation, request, notification, etc.).\n\n"
            f"From: {frm}\nSubject: {subj}\nBody: {body}\n\nSummary:"
        )
        try:
            res = ollama.chat(model="phi3", messages=[{"role":"user","content":prompt}])
            summ = res.get("message",{}).get("content","Summary not available.").strip()
        except Exception as e:
            summ = f"Error generating summary: {e}"
        summaries.append(f"{idx}. From: {frm}\n   Body: {summ}")

    state["summary"] = "\n\n".join(summaries)
    state[last_run_key] = now
    state["action"]     = "summary_created"
    return state
def extract_datetime_from_summary(summary: str) -> str:
    """
    Extracts a date and time from the summary text using a simple regex.
    This assumes the date and time are in a format like 'May 18, 2025 at 5PM'.
    """
    # Regex to find dates like May 18, 2025 at 5PM
    match = re.search(r"(may \d{1,2}, 20\d{2} at \d{1,2}(?::\d{2})?\s?[APMapm]{2})", summary, re.IGNORECASE)
    return match.group(1) if match else "the proposed time"

def email_reply_agent(state: Dict) -> Dict:
    summary = state.get("summary", "")
    calendar_info = state.get("calendar_event", "")
    
    # Default reply text
    if "Meeting scheduled" in calendar_info:
        reply_text = f"""\
To: {state['inbox'][0]['from']}
Subject: Re: Meeting Confirmation - Business Inquiry Discussion

Dear {state['inbox'][0]['from'].split('<')[0].strip()},

Thank you for your message. I have successfully scheduled our meeting for the proposed time:

- **Date/Time**: {extract_datetime_from_summary(summary)}
- **Event Link**: {calendar_info.split('Meeting scheduled: ')[-1]}

I look forward to our conversation.

Best regards,  
[Your Name]
"""
    elif "How about" in calendar_info:
        suggested_time = calendar_info.split("How about")[-1].strip("? ")
        reply_text = f"""\
To: {state['inbox'][0]['from']}
Subject: Re: Meeting Rescheduling Suggestion

Dear {state['inbox'][0]['from'].split('<')[0].strip()},

Thanks for suggesting a time to meet. Unfortunately, the proposed time appears to conflict with my current availability. 

Could we consider this alternative instead?

- **Suggested Alternative**: {suggested_time}

Let me know if this works for you!

Best,  
[Your Name]
"""
    else:
        reply_text = "Could you please clarify your availability?"

    state["reply"] = reply_text
    return state
