import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete your token.json
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

CREDENTIALS_PATH = "/Users/anirudhsekar/Desktop/Coding/AI-CEO/backend/data/gmail_oauth_client.json"
TOKEN_PATH = "/Users/anirudhsekar/Desktop/Coding/AI-CEO/backend/data/token.json"


def authenticate_gmail():
    """
    Handle OAuth authentication flow for Gmail. 
    This function ensures that the credentials are loaded or refreshed.
    """
    creds = None

    # Load credentials from token.json if available
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid credentials, start OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Start the OAuth flow to authorize the user
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the new credentials for future runs
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return creds


def get_gmail_inbox(max_results=1):
    """
    Fetches the Gmail inbox and returns the email details.
    This function ensures that authentication is done before fetching the inbox.
    """
    try:
        # Ensure Gmail authentication
        creds = authenticate_gmail()

        # Build the Gmail service using the authenticated credentials
        service = build("gmail", "v1", credentials=creds)

        # Fetch inbox messages
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get("messages", [])

        email_data = []

        for msg in messages:
            msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()

            headers = msg_detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
            body = ""

            # Extract the plain text body
            parts = msg_detail.get("payload", {}).get("parts", [])
            for part in parts:
                if part["mimeType"] == "text/plain":
                    body = part["body"].get("data", "")
                    break

            email_data.append({
                "from": sender,
                "subject": subject,
                "body": body
            })

        return email_data

    except Exception as e:
        logging.error(f"❌ Error reading Gmail inbox: {e}")
        return []


def list_labels():
    """
    Helper function to list Gmail labels for testing purposes.
    """
    try:
        creds = authenticate_gmail()
        service = build("gmail", "v1", credentials=creds)
        labels = service.users().labels().list(userId="me").execute()
        return labels.get("labels", [])

    except Exception as e:
        logging.error(f"❌ Error listing Gmail labels: {e}")
        return []
