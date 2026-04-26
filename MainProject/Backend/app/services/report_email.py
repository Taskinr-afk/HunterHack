"""
Email notification for citizen-submitted pothole reports.
Uses SMTP env vars (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS).
Falls back to console logging when SMTP is not configured.
Compatible with Mailtrap for demo purposes.
"""

import os
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

SMTP_HOST       = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER       = os.getenv("SMTP_USER", "")
SMTP_PASSWORD   = os.getenv("SMTP_PASS", "")
FROM_EMAIL      = os.getenv("ALERT_EMAIL_FROM", SMTP_USER)
REPORT_RECIPIENT = os.getenv("REPORT_EMAIL_TO", os.getenv("ALERT_EMAIL_TO", "dot.notifications@nyc.gov"))


def _send_report_email(subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[REPORT EMAIL — no SMTP] {subject}\n{body}")
        return False
    msg = MIMEMultipart()
    msg["From"]    = FROM_EMAIL
    msg["To"]      = REPORT_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[REPORT EMAIL failed] {e}")
        return False


def send_report_notification(report: dict) -> bool:
    subject = (
        f"[PotholeIQ] New Citizen Report — "
        f"{report.get('street_name', 'Unknown Street')}, {report.get('borough', 'NYC')}"
    )
    body = f"""
Citizen Pothole Report — PotholeIQ
====================================
Report ID     : {report.get('report_id')}
Pothole Key   : {report.get('pothole_key')}
Location      : {report.get('street_name', 'Unknown')}, {report.get('borough', 'NYC')}
Coordinates   : {report.get('latitude'):.6f}, {report.get('longitude'):.6f}
Description   : {report.get('descriptor', 'No description provided')}
Reporter Name : {report.get('reporter_name', 'Anonymous')}
Reporter Email: {report.get('reporter_email', 'Not provided')}
Image URL     : {report.get('image_url', 'No image')}
Status        : Unverified — requires verification

Submitted at  : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

Action required: Verify this pothole report at your earliest convenience.
    """.strip()
    return _send_report_email(subject, body)