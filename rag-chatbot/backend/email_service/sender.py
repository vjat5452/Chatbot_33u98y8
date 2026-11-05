"""Email sending with SMTP and Microsoft Graph API support, tracking pixel injection, and link wrapping."""

import json
import re
import smtplib
import threading
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote, urlencode

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# ── SMTP Connection Pool (thread-local, reused across batches) ──

_local = threading.local()


def _get_smtp() -> smtplib.SMTP:
    """Get or create a thread-local SMTP connection."""
    if hasattr(_local, "smtp") and _local.smtp is not None:
        try:
            _local.smtp.noop()
            return _local.smtp
        except Exception:
            try:
                _local.smtp.quit()
            except Exception:
                pass
            _local.smtp = None

    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(settings.smtp_user, settings.smtp_password)
    _local.smtp = server
    return server


def close_smtp():
    """Close the thread-local SMTP connection."""
    if hasattr(_local, "smtp") and _local.smtp is not None:
        try:
            _local.smtp.quit()
        except Exception:
            pass
        _local.smtp = None


# ── Microsoft Graph API ──

_graph_token: dict | None = None  # cached {"access_token": ..., "expires_on": ...}


def _get_graph_token() -> str:
    """Acquire or refresh an OAuth2 token for Microsoft Graph using client credentials."""
    global _graph_token
    import time

    if _graph_token and _graph_token.get("expires_on", 0) > time.time() + 60:
        return _graph_token["access_token"]

    from msal import ConfidentialClientApplication

    app = ConfidentialClientApplication(
        client_id=settings.ms_client_id,
        client_credential=settings.ms_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

    if "access_token" not in result:
        raise RuntimeError(f"Graph token error: {result.get('error_description', result)}")

    _graph_token = {
        "access_token": result["access_token"],
        "expires_on": time.time() + result.get("expires_in", 3600),
    }
    return _graph_token["access_token"]


def _send_via_graph(to_email: str, to_name: str, subject: str,
                    html_body: str, text_body: str = "",
                    from_name: str = "", reply_to: str = "") -> dict:
    """Send email using Microsoft Graph API /sendMail endpoint."""
    token = _get_graph_token()
    sender = settings.ms_sender_email

    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html_body},
        "toRecipients": [{"emailAddress": {"address": to_email, "name": to_name or to_email}}],
        "from": {"emailAddress": {"address": sender, "name": from_name or settings.email_from_name}},
    }

    if reply_to:
        message["replyTo"] = [{"emailAddress": {"address": reply_to}}]

    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"message": message, "saveToSentItems": True},
        timeout=30,
    )

    if resp.status_code == 202:
        return {"success": True}
    else:
        detail = resp.text[:500]
        logger.error("Graph sendMail failed (%s): %s", resp.status_code, detail)
        return {"success": False, "error": "graph_send_failed", "details": detail}


# ── Tracking Injection ──

def _get_tracking_base() -> str:
    """Get base URL for tracking endpoints."""
    base = settings.email_tracking_base_url.rstrip("/")
    if not base:
        base = f"http://localhost:{settings.port}"
    return base


def inject_tracking_pixel(html: str, tracking_id: str) -> str:
    """Inject a 1x1 tracking pixel before </body> or at end of HTML."""
    base = _get_tracking_base()
    pixel = f'<img src="{base}/t/{tracking_id}/open.gif" width="1" height="1" style="display:none" alt="" />'

    if "</body>" in html.lower():
        # Insert before </body>
        idx = html.lower().rfind("</body>")
        return html[:idx] + pixel + html[idx:]
    else:
        return html + pixel


def wrap_links(html: str, tracking_id: str) -> str:
    """Rewrite all <a href="..."> links to go through click tracking."""
    base = _get_tracking_base()

    def _replace_link(match):
        original_url = match.group(1)
        # Skip mailto:, tel:, and anchor links
        if original_url.startswith(("mailto:", "tel:", "#", "{{")):
            return match.group(0)
        # Skip unsubscribe links (they have their own tracking)
        if "/unsubscribe/" in original_url:
            return match.group(0)
        tracked_url = f"{base}/t/{tracking_id}/click?url={quote(original_url, safe='')}"
        return match.group(0).replace(original_url, tracked_url)

    return re.sub(r'<a\s[^>]*href=["\']([^"\']+)["\']', _replace_link, html, flags=re.IGNORECASE)


def inject_unsubscribe(html: str, tracking_id: str) -> str:
    """Add unsubscribe link to email footer."""
    base = _get_tracking_base()
    unsub_url = f"{base}/unsubscribe/{tracking_id}"
    footer = f"""
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
        <p style="color: #9ca3af; font-size: 11px;">
            You received this email from {settings.email_from_name}.
            <a href="{unsub_url}" style="color: #9ca3af; text-decoration: underline;">Unsubscribe</a>
        </p>
    </div>
    """

    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        return html[:idx] + footer + html[idx:]
    else:
        return html + footer


# ── Send Email ──

def send_email(to_email: str, to_name: str, subject: str, html_body: str,
               text_body: str = "", tracking_id: str = None,
               from_name: str = "", from_email: str = "", reply_to: str = "") -> dict:
    """Send a single email via configured provider (SMTP or Microsoft Graph). Returns status dict."""
    sender_name = from_name or settings.email_from_name
    sender_email = from_email or settings.email_from_address or settings.smtp_user
    reply = reply_to or settings.email_reply_to or sender_email

    # Process HTML for tracking
    if tracking_id:
        html_body = wrap_links(html_body, tracking_id)
        html_body = inject_tracking_pixel(html_body, tracking_id)
        html_body = inject_unsubscribe(html_body, tracking_id)

    # ── Microsoft Graph API path ──
    if settings.email_provider == "microsoft":
        if not settings.ms_client_id or not settings.ms_tenant_id or not settings.ms_sender_email:
            return {"success": False, "error": "Microsoft Graph not configured"}
        try:
            return _send_via_graph(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                from_name=sender_name,
                reply_to=reply,
            )
        except Exception as e:
            logger.error("Graph API error: %s", e)
            return {"success": False, "error": "graph_error", "details": str(e)}

    # ── SMTP path (default) ──
    if not settings.smtp_host or not settings.smtp_user:
        return {"success": False, "error": "SMTP not configured"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
    msg["Reply-To"] = reply

    # List-Unsubscribe header (required by Gmail/Outlook for deliverability)
    if tracking_id:
        base = _get_tracking_base()
        msg["List-Unsubscribe"] = f"<{base}/unsubscribe/{tracking_id}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    # Attach text and HTML parts
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Try sending, retry once with fresh connection on failure
    last_err = None
    for attempt in range(2):
        try:
            server = _get_smtp()
            server.sendmail(sender_email, [to_email], msg.as_string())
            return {"success": True}
        except smtplib.SMTPRecipientsRefused as e:
            close_smtp()
            return {"success": False, "error": "recipient_refused", "bounce_type": "hard", "details": str(e)}
        except smtplib.SMTPSenderRefused as e:
            close_smtp()
            return {"success": False, "error": "sender_refused", "details": str(e)}
        except smtplib.SMTPDataError as e:
            close_smtp()
            error_code = e.smtp_code if hasattr(e, "smtp_code") else 0
            bounce_type = "hard" if error_code >= 550 else "soft"
            return {"success": False, "error": "smtp_data_error", "bounce_type": bounce_type, "details": str(e)}
        except Exception as e:
            close_smtp()
            last_err = e
            if attempt == 0:
                continue  # retry with fresh connection
            break

    return {"success": False, "error": "send_failed", "bounce_type": "soft", "details": str(last_err)}


def send_test_email(to_email: str, subject: str, html_body: str,
                    from_name: str = "", from_email: str = "") -> dict:
    """Send a test email without tracking."""
    return send_email(
        to_email=to_email,
        to_name="",
        subject=f"[TEST] {subject}",
        html_body=html_body,
        from_name=from_name,
        from_email=from_email,
    )
