import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings
from src.utils import normalize_iso_datetime

class CalendarEngine:
    def __init__(self, token_info: dict):
        """Configures individual API runtime wrappers using credentials loaded at runtime."""
        creds = Credentials.from_authorized_user_info(token_info)
        self.service = build('calendar', 'v3', credentials=creds)

    def inject_event(self, summary: str, iso_start_str: str, venue: str) -> str:
        """Injects calendar event blocks complete with a 4-tier alarm matrix."""
        start_dt = normalize_iso_datetime(iso_start_str)
        end_dt = start_dt + datetime.timedelta(hours=1) # 1-hour event duration default

        event_payload = {
            'summary': summary,
            'location': venue,
            'description': 'Event Registered Automatically by AutoCalendar AI',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': settings.TIMEZONE,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': settings.TIMEZONE,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},     # 30 Minutes Before
                    {'method': 'popup', 'minutes': 1440},   # 24 Hours Before
                ],
            },
        }

        try:
            created_event = self.service.events().insert(calendarId='primary', body=event_payload).execute()
            return created_event.get('id')
        except HttpError as error:
            print(f"Google Calendar Pipeline Injection Aborted: {error}")
            return None