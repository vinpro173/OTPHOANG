import imaplib
import email
import re
import requests
import time
import os
from email.utils import parseaddr

EMAIL = os.getenv("EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
IMAP_SERVER = "imap.gmail.com"
last_otp = None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    })

def extract_otp(text):
    match = re.search(r'\b\d{6}\b', text)
    return match.group() if match else None

def format_otp(otp):
    return f"{otp[:3]} {otp[3:]}"

def get_icloud_recipient(msg):
    """Lấy địa chỉ iCloud từ trường To:"""
    to_header = msg.get("To", "")
    # Có thể có nhiều địa chỉ, tách ra
    addresses = to_header.split(",")
    for addr in addresses:
        _, email_addr = parseaddr(addr.strip())
        if "@icloud.com" in email_addr.lower():
            return email_addr.lower()
    # Nếu không tìm thấy icloud, trả về toàn bộ To
    _, fallback = parseaddr(to_header)
    return fallback or to_header

def check_email():
    global last_otp
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")
    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    if not email_ids:
        mail.logout()
        return

    latest_email_id = email_ids[-1]
    _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])

            # Lấy địa chỉ iCloud nhận mail
            icloud_addr = get_icloud_recipient(msg)

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            otp = extract_otp(body)
            if otp and otp != last_otp:
                send_telegram(
                    f"📧 {icloud_addr}\n"
                    f"🔐 OTP: {format_otp(otp)}"
                )
                last_otp = otp

    mail.logout()

print("Đang theo dõi email...")
while True:
    try:
        check_email()
        time.sleep(5)
    except Exception as e:
        print("Lỗi:", e)
        time.sleep(10)
