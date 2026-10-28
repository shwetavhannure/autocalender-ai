import time
from config.settings import settings
from src.database_mgr import DatabaseManager
from src.gmail_engine import GmailEngine
from src.parser_engine import ParserEngine
from src.calendar_engine import CalendarEngine

def run_worker_loop():
    print("🔄 BACKGROUND WORKER PROCESS DEPLOYED - AUTOMATED MONITORING ACTIVE")
    print('---------------------------------------------------------------------')
    db = DatabaseManager()
    parser = ParserEngine()

    while True:
        try:
            active_users = db.get_all_active_users()
            print(f"\n[Polling Sync] Scanning mailboxes for {len(active_users)} active profile profiles...")

            for user in active_users:
                user_email = user['email']
                token_info = user['token_info'] # Handled cleanly as a native Python dict directly from Mongo

                # Initialize state managers for the current user session
                gmail = GmailEngine(token_info)
                calendar = CalendarEngine(token_info)

                unread_emails = gmail.fetch_unread_messages()
                if not unread_emails:
                    print(f"No new emails found for user: {user_email}")
                    continue

                # Process the latest 7 messages (Read + Unread) for this poll cycle
                unread_emails = unread_emails[:7]

                for email_data in unread_emails:
                    email_id = email_data['id']

                    # Check unique processing history to ensure structural idempotency
                    if db.is_email_processed(user_email, email_id):
                        continue

                    # Process junk filtering routines
                    spam_keywords = ["newsletter", "receipt", "invoice", "unsubscribed", "password reset"]
                    if any(kw in email_data['subject'].lower() for kw in spam_keywords):
                        print(f"Spam Filtered: Skipping promotional or security email '{email_data['subject']}'")
                        db.mark_email_as_processed(user_email, email_id)
                        continue

                    print(f"### Processing email message '{email_data['subject']}' for user context: {user_email}")
                    
                    # ⚡ UPDATED: Pass both body and subject so the parser extracts precise event context
                    parsed_info = parser.extract_event_details(
                        email_body=email_data['body'],
                        subject=email_data['subject']
                    )

                    # EXPLICIT LOGGING: Inform the developer why an email is skipped instead of failing silently
                    if (parsed_info['event'] == settings.DEFAULT_FALLBACK_STRING or 
                        parsed_info['iso_start'] == settings.DEFAULT_FALLBACK_STRING):
                        print(f"Skipped scheduling for '{email_data['subject']}'")
                        db.mark_email_as_processed(user_email, email_id)
                        continue

                    # Execute Calendar Event creation link bindings
                    event_id = calendar.inject_event(
                        summary=f"{parsed_info['event']}",
                        iso_start_str=parsed_info['iso_start'],
                        venue=parsed_info['venue']
                    )

                    if event_id:
                        print(f"### Calendar Synchronization Successful. Event Track Record ID: {event_id}")
                        db.mark_email_as_processed(user_email, email_id)
                    else:
                        print(f"Calendar Injection Failed for event: {parsed_info['event']}")

        except Exception as e:
            print(f"Background Worker Exception Intercepted: {e}")

        # Sleep before beginning the next polling check (e.g., 600 seconds for 10 minutes)
        print(f"\n ----- Polling cycle complete. Sleeping for {settings.POLLING_INTERVAL_SECONDS} seconds...")
        time.sleep(settings.POLLING_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker_loop()