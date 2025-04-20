import ollama
from typing import Dict
import re
from dateutil import parser
from datetime import datetime
from backend.tools.email_tools import send_email
import ollama
from dateutil import parser
from typing import Dict

last_run_key = "last_run_time"

def fix_date_format(date_str):
    try:
        date = parser.parse(date_str)
        return date.strftime('%B %d, %Y')  # Formats date as 'Month Day, Year'
    except (ValueError, TypeError):
        return date_str  # If date parsing fails, return the original string

def email_summarization_agent(state: Dict = {}) -> Dict:
    current_time = datetime.now()
    last_run_time = state.get(last_run_key)

    if last_run_time:
        time_diff = current_time - last_run_time
        if time_diff.total_seconds() < 300:  # 5 minutes
            state["summary"] = "Summarization was already done within the last 5 minutes."
            state["action"] = "summary_skipped"
            return state

    inbox = state.get("inbox", [])
    if not inbox:
        state["summary"] = "No emails found."
    else:
        prompt = (
            "Summarize each of the following emails clearly, correcting any typos in the message body but "
            "DO NOT change the sender's email address. Output each summary in the following strict format:\n\n"
            "Person Name <exact_email_address>\n"
            "Body: summarized content.\n\n"
            "Use a numbered list. Do not alter the formatting or punctuation of the email addresses. Begin below:\n\n"
        )
        for idx, email in enumerate(inbox, start=1):
            prompt += f"{idx}.\nFrom: {email['from']}\nSubject: {email['subject']}\nBody: {email['body']}\n\n"

        try:
            result = ollama.chat(model="phi3", messages=[{"role": "user", "content": prompt}])
            if "message" in result:
                summary = result["message"]["content"]
                summary = re.sub(r'(\d{4}-\d{2}-\d{2})', lambda x: fix_date_format(x.group(0)), summary)
                state["summary"] = summary
                state[last_run_key] = current_time
            else:
                state["summary"] = "Summary not available."
        except Exception as e:
            state["summary"] = f"Ollama error: {str(e)}"

    state["action"] = "summary_created"
    return state


def email_reply_agent(state: Dict = {}) -> Dict:
    print("\n--- Email Agent Activated ---")
    print("Input State:", state)

    # Sort inbox by timestamp (newest first)
    inbox = state.get("inbox", [])
    if inbox and isinstance(inbox, list):
        try:
            inbox = sorted(
                inbox,
                key=lambda x: datetime.fromisoformat(x.get("timestamp", "").replace("Z", "+00:00")),
            )
        except Exception as e:
            print("Inbox sorting failed:", e)

    if not inbox:
        print("Inbox is empty.")
        state["reply"] = "No emails to reply to."
        return state

    replies = []
    for idx, email in enumerate(inbox, start=1):
        sender = email.get("from", "Unknown Sender")
        subject = email.get("subject", "No Subject")
        body = email.get("body", "").strip()

        prompt = (
            "You are a helpful email assistant. Based on the following email, write a clear, professional, and kind reply. "
            "Format the reply with:\n"
            "- A subject line\n"
            "- A greeting (e.g., Dear [Name])\n"
            "- A list-style structure or short bullet points for clarity\n"
            "- A polite closing (e.g., Best regards, Sincerely)\n"
            "Ensure the tone is warm, respectful, and easy to understand.\n\n"
            f"Email #{idx}:\nFrom: {sender}\nSubject: {subject}\nBody: {body}\n"
        )

        calendar_note = state.get("calendar_event", "").strip()
        if state.get("action") == "suggest_time" and calendar_note:
            prompt += f"\n\nNote: The originally requested time is unavailable. Suggest this time instead:\n{calendar_note}\n"

        prompt += "\nReply:\n"

        try:
            response = ollama.chat(model="llama3", messages=[{"role": "user", "content": prompt}])
            content = response.get("message", {}).get("content", "").strip()
            formatted_reply = f"{idx}. To: {sender}\n\n{content}\n"
            replies.append(formatted_reply)
        except Exception as e:
            error_msg = f"{idx}. To: {sender}\n\nError generating reply: {str(e)}"
            replies.append(error_msg)

    # Combine all replies in a single list-style output
    state["reply"] = "\n\n".join(replies)
    print("Generated Replies:\n", state["reply"])
    return state
