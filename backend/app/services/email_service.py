"""Async-friendly HTML email service for Scanix.

Never blocks the event loop (stdlib smtplib runs in a threadpool) and never
raises — if SMTP is not configured it logs and no-ops. Links use APP_PUBLIC_URL
(defaults to the test-env IP, NOT a hard-coded domain), so it works before a
production domain exists.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Base URL for links in emails. Test env is IP-only; override via APP_PUBLIC_URL.
APP_URL = os.getenv("APP_PUBLIC_URL", "http://192.168.121.40").rstrip("/")


def _score_color(score: int) -> str:
    return "#22c55e" if score < 30 else "#f59e0b" if score < 60 else "#ef4444"


def _score_label(score: int) -> str:
    if score < 30:
        return "Goed beveiligd"
    if score < 60:
        return "Verbetering nodig"
    if score < 80:
        return "Risico aanwezig"
    return "Dringend actie vereist"


class EmailService:
    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        # Accept both SMTP_PASSWORD (spec) and SMTP_PASS (existing config).
        self.password = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS") or ""
        self.from_addr = os.getenv("SMTP_FROM") or self.user
        self.enabled = bool(self.host and self.user and self.password)

    def _send_sync(self, to: str, subject: str, html: str, text: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr or self.user
            msg["To"] = to
            msg.attach(MIMEText(text or " ", "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.ehlo()
                try:
                    server.starttls()
                    server.ehlo()
                except Exception as exc:  # noqa: BLE001 — TLS optional
                    logger.warning("STARTTLS unavailable: %s", exc)
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_addr or self.user, [to], msg.as_string())
            logger.info("email sent to %s: %s", to, subject)
            return True
        except Exception as exc:  # noqa: BLE001 — never raise
            logger.error("failed to send email to %s: %s", to, exc)
            return False

    async def send(self, to: str, subject: str, html: str, text: str = "") -> bool:
        if not self.enabled:
            logger.info("[Email] SMTP niet geconfigureerd. Zou sturen naar: %s (%s)", to, subject)
            return False
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_sync, to, subject, html, text)
        except Exception as exc:  # noqa: BLE001
            logger.error("email dispatch failed: %s", exc)
            return False

    # ── Templated emails ──────────────────────────────────────────────────────
    async def send_scan_complete(self, user_email: str, scan: dict) -> bool:
        target = scan.get("target", "uw systeem")
        score = int(scan.get("risk_score", 0) or 0)
        critical = scan.get("findings_critical", 0)
        high = scan.get("findings_high", 0)
        label = _score_label(score)
        link = f"{APP_URL}/scans/{scan.get('id')}"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#0a0a0a;padding:24px;text-align:center">
            <h1 style="color:#06b6d4;margin:0">Scanix</h1>
          </div>
          <div style="padding:32px;background:#fff">
            <h2>Uw scan van {target} is klaar</h2>
            <div style="background:#f4f4f4;border-radius:8px;padding:20px;margin:20px 0">
              <p style="font-size:32px;font-weight:bold;margin:0;color:{_score_color(score)}">{score}/100</p>
              <p style="margin:4px 0 0;color:#666">{label}</p>
            </div>
            <p>Gevonden: <strong style="color:#ef4444">{critical} kritieke</strong>
               en <strong style="color:#f97316">{high} hoge</strong> bevindingen.</p>
            <a href="{link}" style="display:inline-block;background:#06b6d4;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:16px">
              Bekijk volledig rapport &rarr;
            </a>
          </div>
          <div style="padding:16px;text-align:center;color:#999;font-size:12px">
            Scanix &middot; Dit bericht is verstuurd naar {user_email}
          </div>
        </div>"""
        return await self.send(user_email, f"Scan klaar: {target} — {label}", html)

    async def send_critical_finding(self, user_email: str, scan: dict, finding: dict) -> bool:
        link = f"{APP_URL}/scans/{scan.get('id')}"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#ef4444;padding:16px;text-align:center">
            <h1 style="color:#fff;margin:0">&#9888; Kritieke bevinding</h1>
          </div>
          <div style="padding:32px">
            <h2>{finding.get('title', 'Kritieke kwetsbaarheid gevonden')}</h2>
            <p>Target: <strong>{scan.get('target')}</strong></p>
            <p>{finding.get('description','')}</p>
            <a href="{link}" style="display:inline-block;background:#ef4444;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
              Bekijk bevinding &rarr;
            </a>
          </div>
        </div>"""
        return await self.send(
            user_email,
            f"KRITIEK: {finding.get('title','Kwetsbaarheid')} op {scan.get('target')}",
            html,
        )

    async def send_welcome(self, user_email: str, user_name: str = "") -> bool:
        greeting = f"Hoi {user_name}!" if user_name else "Welkom!"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#0a0a0a;padding:24px;text-align:center">
            <h1 style="color:#06b6d4">Welkom bij Scanix</h1>
          </div>
          <div style="padding:32px">
            <h2>{greeting}</h2>
            <p>Uw account is aangemaakt. U heeft 1 gratis scan credit gekregen.</p>
            <p>Voeg uw eerste website of server toe en start uw eerste scan.</p>
            <a href="{APP_URL}/dashboard" style="display:inline-block;background:#06b6d4;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">
              Start uw eerste scan &rarr;
            </a>
            <hr style="margin:32px 0;border:none;border-top:1px solid #eee">
            <p style="color:#666;font-size:13px">Vragen? Mail naar info@scanix.nl<br>U kunt notificaties beheren via uw accountinstellingen.</p>
          </div>
        </div>"""
        return await self.send(user_email, "Welkom bij Scanix — uw gratis scan staat klaar", html)

    async def send_scheduled_scan_failed(self, user_email: str, target: str, reason: str) -> bool:
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="padding:32px">
            <h2>Geplande scan mislukt</h2>
            <p>De scan van <strong>{target}</strong> kon niet worden gestart.</p>
            <p>Reden: {reason}</p>
            <a href="{APP_URL}/targets" style="display:inline-block;background:#06b6d4;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
              Bekijk uw targets &rarr;
            </a>
          </div>
        </div>"""
        return await self.send(user_email, f"Geplande scan mislukt: {target}", html)


email_service = EmailService()
