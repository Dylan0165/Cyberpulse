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


def _send(to_email: str, subject: str, body: str) -> bool:
    """Best-effort plain-text sender.

    No-ops (logs to console and returns False) when SMTP is not configured.
    Never raises.
    """
    try:
        smtp_host = os.getenv("SMTP_HOST")
        if not smtp_host:
            logger.info(
                "email disabled (no SMTP_HOST) — would send to %s: %s",
                to_email,
                subject,
            )
            return False

        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_from = os.getenv("SMTP_FROM") or smtp_user

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
            server.sendmail(
                smtp_from or smtp_user or to_email, [to_email], msg.as_string()
            )

        logger.info("email sent to %s: %s", to_email, subject)
        return True
    except Exception as exc:  # noqa: BLE001 - never raise
        logger.error("failed to send email to %s: %s", to_email, exc)
        return False


def send_welcome_email(user, plan, interval) -> bool:
    """Send the Dutch welcome email after a paid subscription is activated.

    Best-effort: returns False (after logging) when SMTP is not configured.
    Never raises.
    """
    try:
        plan_names = {
            "starter": "Starter",
            "business": "Business",
            "enterprise": "Enterprise",
        }
        plan_features = {
            "starter": [
                "1 systeem monitoren",
                "1 beveiligingsscan per maand",
                "PDF + NIS2 + Secure Solution Rapport",
            ],
            "business": [
                "5 systemen monitoren",
                "Onbeperkte scans",
                "Alle geavanceerde modules",
                "Geplande automatische scans",
                "Secure Solution Rapport na elke scan",
            ],
            "enterprise": [
                "20 systemen monitoren",
                "Onbeperkte scans",
                "Alle modules + AI upgrade",
                "White-label rapporten",
                "Kwartaalgesprek met security experts",
            ],
        }

        name = (
            getattr(user, "name", None)
            or getattr(user, "full_name", None)
            or "klant"
        )
        pname = plan_names.get(plan, plan.title())
        features = plan_features.get(plan, [])

        subject = f"Welkom bij Scanix — Uw {pname} pakket is actief"

        feature_lines = "\n".join(f"  - {f}" for f in features)

        body = (
            f"Beste {name},\n\n"
            f"Uw Scanix {pname} pakket is geactiveerd.\n\n"
            "UW INLOGGEGEVENS\n"
            f"  E-mailadres: {user.email}\n"
            "  Wachtwoord: Het wachtwoord dat u heeft ingesteld bij registratie\n"
            "  Inloggen: https://app.scanix.nl/login\n\n"
            f"UW PAKKET: {pname.upper()}\n"
            f"{feature_lines}\n\n"
            "AAN DE SLAG\n"
            "  1. Log in op https://app.scanix.nl\n"
            '  2. Voeg uw eerste systeem toe onder "Mijn systemen"\n'
            "  3. Start uw eerste beveiligingsscan\n"
            "  4. Ontvang uw rapport binnen 10 minuten\n\n"
            "BEHEER UW ABONNEMENT: https://app.scanix.nl/billing\n\n"
            "VRAGEN? info@scanix.nl\n\n"
            "Met vriendelijke groet,\n"
            "Het Scanix Team\n\n"
            "Scanix — Automated Security Testing | scanix.nl | info@scanix.nl\n"
        )

        return _send(user.email, subject, body)
    except Exception as exc:  # noqa: BLE001 - never raise
        logger.error("failed to send welcome email: %s", exc)
        return False


def send_trial_welcome_email(user) -> bool:
    """Send the Dutch trial welcome email after a free trial account is created.

    Best-effort: returns False (after logging) when SMTP is not configured.
    Never raises.
    """
    try:
        name = (
            getattr(user, "name", None)
            or getattr(user, "full_name", None)
            or "klant"
        )

        subject = "Welkom bij Scanix — uw proefaccount is actief"

        body = (
            f"Beste {name},\n\n"
            "U heeft 1 gratis scan beschikbaar.\n\n"
            "Log in op https://app.scanix.nl en voeg uw systeem toe.\n\n"
            "Ontdek onze pakketten vanaf €149/mnd op https://scanix.nl/prijzen\n\n"
            "Met vriendelijke groet,\n"
            "Het Scanix Team\n\n"
            "Scanix — Automated Security Testing | scanix.nl | info@scanix.nl\n"
        )

        return _send(user.email, subject, body)
    except Exception as exc:  # noqa: BLE001 - never raise
        logger.error("failed to send trial welcome email: %s", exc)
        return False


def send_subscription_ended_email(user) -> bool:
    """Send the Dutch 'abonnement beëindigd' email.

    Best-effort: returns False (after logging) when SMTP is not configured.
    Never raises.
    """
    try:
        name = (
            getattr(user, "name", None)
            or getattr(user, "full_name", None)
            or "klant"
        )

        subject = "Uw Scanix abonnement is beëindigd"

        body = (
            f"Beste {name},\n\n"
            "Uw Scanix abonnement is beëindigd. Uw account staat nu weer op het "
            "gratis proefpakket (free trial).\n\n"
            "Wilt u opnieuw abonneren? Bekijk onze pakketten op "
            "https://scanix.nl/prijzen\n\n"
            "Heeft u vragen? Neem contact op via info@scanix.nl\n\n"
            "Met vriendelijke groet,\n"
            "Het Scanix Team\n\n"
            "Scanix — Automated Security Testing | scanix.nl | info@scanix.nl\n"
        )

        return _send(user.email, subject, body)
    except Exception as exc:  # noqa: BLE001 - never raise
        logger.error("failed to send subscription ended email: %s", exc)
        return False
