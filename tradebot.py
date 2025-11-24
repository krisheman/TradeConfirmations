import imaplib
import email
from email.header import decode_header
import re
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURATION ---
IMAP_SERVER = "imap.gmail.com" # Change if not using Gmail
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
GOOGLE_JSON = os.environ["GOOGLE_CREDENTIALS"]
SHEET_NAME = "Trade Journal" # Name of your Google Sheet file

def connect_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1 # Opens the first tab
    return sheet

def extract_trade_details(subject, body):
    # This is where logic gets tricky. Email formats vary by broker.
    # You need to inspect the raw text of your emails to refine these Regex patterns.
    
    details = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Broker": "Unknown",
        "Action": "Unknown",
        "Symbol": "Unknown",
        "Quantity": "0",
        "Price": "0.00"
    }

    # Identify Broker
    if "Robinhood" in body or "Robinhood" in subject:
        details["Broker"] = "Robinhood"
    elif "Webull" in body or "Webull" in subject:
        details["Broker"] = "Webull"

    # --- EXAMPLE PARSING LOGIC (You must adjust regex based on actual email text) ---
    
    # Example String: "Your market order to buy 10 shares of AAPL was executed at $150.00"
    
    # Detect Symbol (Looks for 1-5 Capital letters)
    symbol_match = re.search(r"\b([A-Z]{1,5})\b", subject)
    if symbol_match:
        details["Symbol"] = symbol_match.group(1)

    # Detect Action (Buy/Sell)
    if "buy" in subject.lower() or "bought" in subject.lower():
        details["Action"] = "Buy"
    elif "sell" in subject.lower() or "sold" in subject.lower():
        details["Action"] = "Sell"

    # Detect Quantity (Look for number before 'shares')
    qty_match = re.search(r"(\d+)\s+shares", body)
    if qty_match:
        details["Quantity"] = qty_match.group(1)

    # Detect Price (Look for $ followed by digits)
    price_match = re.search(r"\$\s?([\d,]+\.\d{2})", body)
    if price_match:
        details["Price"] = price_match.group(1)

    return list(details.values())

def process_emails():
    # Connect to Email
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    # Search for emails from brokers that are UNREAD
    # Add more brokers to the search string if needed
    status, messages = mail.search(None, '(UNREAD OR (FROM "robinhood.com") (FROM "webull.com"))')
    
    email_ids = messages[0].split()
    
    if not email_ids:
        print("No new trade emails found.")
        return

    sheet = connect_sheets()

    for e_id in email_ids:
        # Fetch the email
        _, msg_data = mail.fetch(e_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # Get Email Body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                # Only process if it looks like a trade confirmation
                if "order" in subject.lower() or "trade" in subject.lower():
                    print(f"Processing: {subject}")
                    trade_data = extract_trade_details(subject, body)
                    sheet.append_row(trade_data)
                    
                    # Mark as READ so we don't process it again
                    mail.store(e_id, '+FLAGS', '\\Seen')
                else:
                    print(f"Skipping non-trade email: {subject}")

    mail.close()
    mail.logout()

if __name__ == "__main__":
    process_emails()
