# Mailtrap Email Setup Guide

PotholeIQ uses Mailtrap for email alerts during development and demo. This guide covers both **sandbox testing** (fake inbox) and **production sending** (real email delivery).

---

## Quick Start — Mailtrap Sandbox (for demo)

Mailtrap Sandbox catches emails in a fake inbox — no real delivery, perfect for demos.

### Step 1: Create a Mailtrap account

1. Go to [https://mailtrap.io](https://mailtrap.io) and sign up (free, no credit card needed)
2. After signing in, go to **Email Testing** → **Sandboxes**
3. Click on **My Sandbox** (created automatically)

### Step 2: Get your SMTP credentials

1. In your sandbox, click the **Integrations** tab
2. Select **SMTP** from the list
3. You'll see credentials like:

```
Host:     sandbox.smtp.mailtrap.io
Port:     2525
Username: abc123def456    (a long hash)
Password: 987xyz654wvu    (a long hash)
```

### Step 3: Configure PotholeIQ

Edit `MainProject/Backend/.env` and fill in the values:

```
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=abc123def456         # <-- paste your Mailtrap username
SMTP_PASS=987xyz654wvu         # <-- paste your Mailtrap password
ALERT_EMAIL_TO=anything@inbox.mailtrap.io   # Mailtrap catches all mail to the sandbox
```

### Step 4: Verify it works

1. Start the backend: `PYTHONPATH=. uvicorn Backend.app.main:app --reload --port 8000`
2. Start the frontend: `cd MainProject/Frontend && npm run dev`
3. Click a pothole on the map → click **"Send DOT alert"**
4. Go back to Mailtrap → **My Sandbox** → **Inbox**
5. You should see the alert email with subject like `[PotholeIQ] HIGH Risk — HARLEM RIVER DRIVE, MANHATTAN`

### How it works

- When SMTP is configured, alerts are sent via email and logged to the database
- When SMTP is **not** configured (missing user/pass), alerts are logged to the database only and the email content prints to the console with `[ALERT — no SMTP]`
- Mailtrap sandbox uses port **2525** without STARTTLS — the code auto-detects this and skips STARTTLS
- Production SMTP (port 587) uses STARTTLS automatically

---

## Production — Real Email Delivery

For sending real emails, you have several options:

### Option A: Mailtrap Sending (recommended)

1. In Mailtrap, go to **Sending** → **Domains** → add your domain
2. Follow DNS verification steps (SPF, DKIM, DMARC)
3. Under **Integrations** → **SMTP**, get production credentials:

```
SMTP_HOST=live.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=api
SMTP_PASS=your_mailtrap_api_token
```

### Option B: Brevo (formerly Sendinblue)

Free tier: 300 emails/day, no credit card.

```
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASS=your_brevo_smtp_key
```

### Option C: Gmail (requires App Password)

1. Enable 2FA on your Google account
2. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate an App Password for "Mail"

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_16_char_app_password
```

### Option D: Resend

Modern API-first email service, free tier available.

```
SMTP_HOST=smtp.resend.com
SMTP_PORT=465
SMTP_USER=resend
SMTP_PASS=your_resend_api_key
```

> **Note:** Resend uses port 465 with implicit TLS. You would need to change `smtplib.SMTP` to `smtplib.SMTP_SSL` in `alerts.py` and `alert_service.py` for port 465 to work.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `[ALERT — no SMTP]` printed to console | `SMTP_USER` or `SMTP_PASS` is empty. Fill them in `.env`. |
| `[ALERT email failed] Authentication failed` | Wrong username/password. Copy credentials exactly from Mailtrap. |
| `[ALERT email failed] Connection refused` | Wrong host or port. Sandbox = `sandbox.smtp.mailtrap.io:2525`, production = `live.smtp.mailtrap.io:587`. |
| Email sent but not received (sandbox) | Check Mailtrap sandbox inbox, not your real email. Sandbox doesn't deliver to real addresses. |
| STARTTLS error on port 2525 | The code auto-detects port 2525 and skips STARTTLS. If you see this, make sure `SMTP_PORT=2525` is set correctly. |
| `SMTP_PASSWORD` vs `SMTP_PASS` mismatch | The code reads `SMTP_PASS`. Make sure `.env` uses `SMTP_PASS=` (not `SMTP_PASSWORD=`). |

---

## Code Changes Summary

Three files were modified to support Mailtrap:

1. **`Backend/app/alerts.py`** — `_send_email()` now skips STARTTLS when `SMTP_PORT=2525`
2. **`Backend/app/services/alert_service.py`** — `send_alert_email()` same STARTTLS fix
3. **`Backend/.env`** — Defaults changed to Mailtrap sandbox (`sandbox.smtp.mailtrap.io:2525`)
4. **`Backend/.env.example`** — Updated with Mailtrap instructions and production alternatives
5. **`SMTP_PASSWORD` → `SMTP_PASS`** — Fixed env var name mismatch in `.env`

---

## Architecture

```
Frontend "Send DOT alert" button
    ↓
POST /api/alerts/send (with x-api-key header)
    ↓
Backend alert_service.py → _send_email()
    ↓
SMTP connection (Mailtrap sandbox :2525 or production :587)
    ↓
Mailtrap inbox (sandbox) or real inbox (production)
```

The alert is **always** saved to the SQLite `alerts` table regardless of email delivery. The `delivered` column tracks whether the email was actually sent.