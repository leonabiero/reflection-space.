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

    BUG FIX (2026-07-30): the email's wording ("A screenshot is
    attached." / "No screenshot was captured for this report.") used to
    be decided separately, in services/error_log.py:build_email_summary(),
    purely from whether a screenshot_b64 string existed. That could
    disagree with what this function actually did -- e.g. if decoding
    the image below failed, the email body would still claim a
    screenshot was attached even though none was. This function is the
    ONLY place that knows whether the attachment truly succeeded, so it
    is now also the only place that decides the wording: body_text is
    expected to contain the literal placeholder "%%SCREENSHOT_STATUS%%"
    (see build_email_summary), which gets replaced here with the real
    status right before sending. This makes it structurally impossible
    for the attachment and the wording to disagree.
    """
    if not is_configured():
        logger.info("Email alerting not configured -- skipping alert email: %s", subject)
        return False

    try:
        image_part = None
        if screenshot_b64:
            try:
                _header, _, b64data = screenshot_b64.partition(",")
                image_bytes = base64.b64decode(b64data)
                if image_bytes:
                    image_part = MIMEImage(image_bytes, name="screenshot.jpg")
            except Exception:
                logger.exception("Failed to decode screenshot for alert email -- sending without it")

        screenshot_status = (
            "A screenshot is attached." if image_part is not None
            else "No screenshot was captured for this report."
        )
        body_text = body_text.replace("%%SCREENSHOT_STATUS%%", screenshot_status)

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO
        msg.attach(MIMEText(body_text, "plain"))

        if image_part is not None:
            msg.attach(image_part)

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