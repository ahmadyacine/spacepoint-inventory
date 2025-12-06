import os
from dotenv import load_dotenv
import smtplib

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

print("SMTP_USER:", SMTP_USER)
print("SMTP_PASSWORD is set:", bool(SMTP_PASSWORD))

with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    print("✅ Logged in successfully!")
