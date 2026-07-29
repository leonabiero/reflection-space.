"""
Email Alerts for Production Errors
=====================================

Sends Leon an email the moment something worth his immediate attention
happens: a genuine crash (not a routine single-companion retry), or
someone using the "Report a problem" button.

Disabled by default -- see config.py for the SMTP_* / ALERT_EMAIL_*
settings that turn it on. Every function here is fully defensive: a
failure to send email is logged to stdout and swallowed, never raised.
Email is a convenience notification layer on top of the Error Log
(services/error_log.py), which remains the source of truth regardless
of whether any email ever successfully sends.
"""

import base64
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO, ALERT_EMAIL_FROM
from services.db_time import get_logger

logger = get_logger(__name__)


def is_configured():
    return bool(SMTP_HOST and ALERT_EMAIL_TO)


def send_alert_email(subject, body_text, screenshot_b64=None):
    """
    Sends a plain-text alert email, with an optional screenshot
    attachment. Returns True on success, False otherwise -- never
    raises, so a broken mail server can never be the reason a report
    or an error-logging call fails.
    """
    if not is_configured():
        logger.info("Email alerting not configured -- skipping alert email: %s", subject)
        return False

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO
        msg.attach(MIMEText(body_text, "plain"))

        if screenshot_b64:
            try:
                _header, _, b64data = screenshot_b64.partition(",")
                image_bytes = base64.b64decode(b64data)
                image_part = MIMEImage(image_bytes, name="screenshot.jpg")
                msg.attach(image_part)
            except Exception:
                logger.exception("Failed to attach screenshot to alert email -- sending without it")

        if SMTP_PORT == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=10) as server:
                if SMTP_USER:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls(context=ssl.create_default_context())
                if SMTP_USER:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

        logger.info("Alert email sent: %s", subject)
        return True
    except Exception:
        logger.exception("Failed to send alert email: %s", subject)
        return False