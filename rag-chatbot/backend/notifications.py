"""Email notifications for the sales bot layer using Python's built-in smtplib."""

import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from backend.config import settings


def _get_alert_emails() -> list[str]:
    """Parse comma-separated alert emails from config."""
    if not settings.alert_emails:
        return []
    return [e.strip() for e in settings.alert_emails.split(",") if e.strip()]


def _send_email(subject: str, html_body: str):
    """Send an email via SMTP. Runs in background thread to not block requests."""
    if not settings.smtp_host or not settings.smtp_user:
        print("[Notifications] SMTP not configured, skipping email")
        return

    recipients = _get_alert_emails()
    if not recipients:
        print("[Notifications] No alert emails configured, skipping")
        return

    def _do_send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.smtp_user
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_user, recipients, msg.as_string())

            print(f"[Notifications] Email sent: {subject}")
        except Exception as e:
            print(f"[Notifications] Failed to send email: {e}")

    thread = threading.Thread(target=_do_send, daemon=True)
    thread.start()


def send_lead_alert(lead: dict, conversation_summary: str = ""):
    """Send email alert when a hot lead is detected."""
    name = lead.get("name", "Unknown")
    email = lead.get("email", "N/A")
    phone = lead.get("phone", "N/A")
    score = lead.get("lead_score", 0)
    page = lead.get("source_page", "N/A")

    subject = f"🔥 Hot Lead Detected: {name} (Score: {score})"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #f97316; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">Hot Lead Alert</h2>
        </div>
        <div style="background: #fff; border: 1px solid #e5e7eb; padding: 24px; border-radius: 0 0 8px 8px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px 0; color: #6b7280; width: 120px;">Name:</td>
                    <td style="padding: 8px 0; font-weight: bold;">{name}</td></tr>
                <tr><td style="padding: 8px 0; color: #6b7280;">Email:</td>
                    <td style="padding: 8px 0;">{email}</td></tr>
                <tr><td style="padding: 8px 0; color: #6b7280;">Phone:</td>
                    <td style="padding: 8px 0;">{phone}</td></tr>
                <tr><td style="padding: 8px 0; color: #6b7280;">Lead Score:</td>
                    <td style="padding: 8px 0;"><strong style="color: #f97316;">{score}/100</strong></td></tr>
                <tr><td style="padding: 8px 0; color: #6b7280;">Source Page:</td>
                    <td style="padding: 8px 0;">{page}</td></tr>
            </table>
            {"<hr style='margin: 16px 0;'><h3 style='margin: 8px 0;'>Conversation Summary</h3><p style='color: #374151; white-space: pre-wrap;'>" + conversation_summary + "</p>" if conversation_summary else ""}
            <hr style="margin: 16px 0;">
            <p style="color: #6b7280; font-size: 12px;">
                This is an automated alert from the Sparrowi Sales Bot.
                View the full conversation in the <a href="/admin/">Admin Dashboard</a>.
            </p>
        </div>
    </div>
    """

    _send_email(subject, html)


def send_daily_digest(stats: dict):
    """Send daily digest email with summary of leads and conversations."""
    subject = f"📊 Sparrowi Daily Digest — {stats.get('date', 'Today')}"

    total_leads = stats.get("total_leads", 0)
    new_leads = stats.get("new_leads_today", 0)
    hot_leads = stats.get("hot_leads", 0)
    messages = stats.get("messages_today", 0)
    satisfaction = stats.get("satisfaction_rate", 0)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #2563eb; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">Daily Digest</h2>
            <p style="margin: 4px 0 0; opacity: 0.9;">{stats.get('date', 'Today')}</p>
        </div>
        <div style="background: #fff; border: 1px solid #e5e7eb; padding: 24px; border-radius: 0 0 8px 8px;">
            <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px;">
                <div style="flex: 1; min-width: 120px; background: #f3f4f6; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #2563eb;">{messages}</div>
                    <div style="color: #6b7280; font-size: 12px;">Messages Today</div>
                </div>
                <div style="flex: 1; min-width: 120px; background: #f3f4f6; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{new_leads}</div>
                    <div style="color: #6b7280; font-size: 12px;">New Leads</div>
                </div>
                <div style="flex: 1; min-width: 120px; background: #f3f4f6; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #f97316;">{hot_leads}</div>
                    <div style="color: #6b7280; font-size: 12px;">Hot Leads</div>
                </div>
                <div style="flex: 1; min-width: 120px; background: #f3f4f6; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #8b5cf6;">{satisfaction}%</div>
                    <div style="color: #6b7280; font-size: 12px;">Satisfaction</div>
                </div>
            </div>
            <p style="color: #6b7280; font-size: 12px; text-align: center;">
                Total leads in database: {total_leads} |
                View details in the <a href="/admin/">Admin Dashboard</a>
            </p>
        </div>
    </div>
    """

    _send_email(subject, html)
