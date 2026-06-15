"""Email notification service (stdlib smtplib).

Self-contained and importable. Never raises — returns True on success,
False otherwise. If SMTP_HOST is not configured, email is silently disabled.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_scan_complete_email(
    to_email: str,
    target: str,
    risk_score,
    critical: int,
    high: int,
    medium: int,
    low: int,
    scan_id,
) -> bool:
    """Send a 'scan voltooid' notification email in Dutch.

    Returns True if the email was sent, False otherwise (including when SMTP
    is not configured). Never raises.
    """
    try:
        smtp_host = os.getenv("SMTP_HOST")
        if not smtp_host:
            logger.info("email disabled (no SMTP_HOST)")
            return False

        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_from = os.getenv("SMTP_FROM") or smtp_user

        subject = f"Scanix scan voltooid — {target} — {risk_score}/100"
        link = f"http://192.168.121.40/scans/{scan_id}"

        body = (
            "Beste,\n\n"
            "De beveiligingsscan is voltooid.\n\n"
            f"Doelwit: {target}\n"
            f"Risicoscore: {risk_score}/100\n\n"
            "Bevindingen:\n"
            f"  Kritiek:    {critical}\n"
            f"  Hoog:       {high}\n"
            f"  Gemiddeld:  {medium}\n"
            f"  Laag:       {low}\n\n"
            f"Bekijk het volledige rapport: {link}\n\n"
            "Met vriendelijke groet,\n"
            "Scanix\n"
        )

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_from or ""
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception as exc:  # noqa: BLE001 - TLS optional
                logger.warning("STARTTLS not available: %s", exc)
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from or smtp_user or to_email, [to_email], msg.as_string())

        logger.info("scan complete email sent to %s", to_email)
        return True
    except Exception as exc:  # noqa: BLE001 - never raise
        logger.error("failed to send scan complete email: %s", exc)
        return False
