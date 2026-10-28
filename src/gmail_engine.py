import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class GmailEngine:
    def __init__(self, token_info: dict):
        """
            Configures individual API runtime wrappers using current tenant profile maps.
        """
        # print("token info", token_info)
        creds = Credentials.from_authorized_user_info(token_info)
        self.service = build('gmail', 'v1', credentials=creds)

    def fetch_unread_messages(self) -> list:
        """
            Pulls raw data structures from the 7 most recent items (read or unread) out of the mailbox.
        """
        try:
            
            results = self.service.users().messages().list(userId='me', maxResults=7).execute()
            messages = results.get('messages', [])
            
            email_list = []
            for msg_meta in messages:
                msg_id = msg_meta['id']
                message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                
                headers = message.get('payload', {}).get('headers', [])
                subject = self._get_header_value(headers, "Subject")
                sender = self._get_header_value(headers, "From")
                date = self._get_header_value(headers, "Date")
                
                body = self._extract_body(message.get('payload', {}))
                
                email_list.append({
                    "id": msg_id,
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "body": body
                })
            return email_list
        except Exception as e:
            print(f"Gmail Core processing transaction aborted: {e}")
            return []

    def _get_header_value(self, headers: list, name: str) -> str:
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return "Unknown"

    def _extract_body(self, payload: dict) -> str:
        """
            Recursively walks complex multipart payloads to extract message strings.
        """
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    data = part['body']['data']
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    body += self._extract_body(part)
        else:
            data = payload.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body