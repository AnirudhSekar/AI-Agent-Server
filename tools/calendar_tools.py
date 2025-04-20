from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

def create_calendar_event(event_details, credentials_file, calendar_id):
    """
    Creates a calendar event in Google Calendar and returns the event with its link.

    Args:
    - event_details: A dictionary containing event details such as summary, start, and end times.
    - credentials_file: Path to the service account credentials file.
    - calendar_id: The ID of the calendar to create the event in (usually your email address if shared).

    Returns:
    - event: The created event with its details, including the event URL.
    """
    try:
        # Authenticate using the service account credentials
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=["https://www.googleapis.com/auth/calendar"]
        )

        # Build the service
        service = build("calendar", "v3", credentials=creds)

        # Create the event
        event = service.events().insert(calendarId=calendar_id, body=event_details).execute()
        event_id = event['id']

        # Wait for it to propagate
        time.sleep(2)

        # Refetch the event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        print("Event created: ", event)
        print("Event URL: ", event.get('htmlLink', 'No link available'))

        return event

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None
def get_freebusy_slots(credentials_file, time_min, time_max, calendar_id="primary"):
    """
    Checks Google Calendar for busy slots within a time range.

    Args:
    - credentials_file: Path to service account credentials file.
    - time_min: Start of the time window (ISO format with timezone offset).
    - time_max: End of the time window (ISO format with timezone offset).
    - calendar_id: Calendar to check (usually your email address).

    Returns:
    - A list of busy time slots (each with 'start' and 'end' in ISO format).
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=creds)

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id}]
        }

        response = service.freebusy().query(body=body).execute()
        busy_times = response["calendars"][calendar_id]["busy"]
        return busy_times

    except HttpError as error:
        print(f"Error checking availability: {error}")
        return []
    
def write_invoice(invoice, csv_file):
    """
    Writes invoice details to a CSV file.

    Args:
    - invoice: A dictionary containing invoice details.
    - csv_file: Path to the CSV file where the invoice will be written.
    """
    import csv
    try:
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=invoice.keys())
            writer.writerow(invoice)
            print(f"Invoice written to {csv_file}: {invoice}")
        return invoice
    except Exception as e:
        print(f"Error writing invoice: {e}")
        return None
    