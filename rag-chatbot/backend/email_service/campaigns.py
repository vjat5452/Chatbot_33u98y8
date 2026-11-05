"""Campaign lifecycle management: create, schedule, send, pause, cancel."""

import json
import uuid
import random
from datetime import datetime

from backend.database import _get_conn
from backend.config import settings
from backend.email_service import templates as email_templates, sender as email_sender


# ── Campaign CRUD ──

def create_campaign(name: str, campaign_type: str = "warm", template_id: int = None,
                    subject_line: str = "", from_name: str = "", from_email: str = "",
                    reply_to: str = "", target_filter: dict = None,
                    ab_enabled: bool = False, ab_variant_b_subject: str = "",
                    ab_variant_b_template_id: int = None,
                    ab_split_percentage: int = 50) -> int:
    conn = _get_conn()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO email_campaigns
           (name, campaign_type, template_id, subject_line, from_name, from_email, reply_to,
            target_filter, ab_enabled, ab_variant_b_subject, ab_variant_b_template_id,
            ab_split_percentage, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
        (name, campaign_type, template_id, subject_line, from_name, from_email, reply_to,
         json.dumps(target_filter or {}), int(ab_enabled), ab_variant_b_subject,
         ab_variant_b_template_id, ab_split_percentage, now, now)
    )
    conn.commit()
    return cursor.lastrowid


def get_campaign(campaign_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM email_campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not row:
        return None
    c = dict(row)
    c["target_filter"] = json.loads(c.get("target_filter") or "{}")
    return c


def get_campaigns(campaign_type: str = None, status: str = None,
                  limit: int = 50, offset: int = 0) -> dict:
    conn = _get_conn()
    conditions = []
    params = []
    if campaign_type:
        conditions.append("campaign_type = ?")
        params.append(campaign_type)
    if status:
        conditions.append("status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    total = conn.execute(f"SELECT COUNT(*) FROM email_campaigns {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM email_campaigns {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    campaigns = []
    for row in rows:
        c = dict(row)
        c["target_filter"] = json.loads(c.get("target_filter") or "{}")
        campaigns.append(c)
    return {"total": total, "campaigns": campaigns}


def update_campaign(campaign_id: int, **kwargs) -> bool:
    conn = _get_conn()
    allowed = {"name", "template_id", "subject_line", "from_name", "from_email",
               "reply_to", "target_filter", "ab_enabled", "ab_variant_b_subject",
               "ab_variant_b_template_id", "ab_split_percentage", "status", "scheduled_at"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            if k == "target_filter":
                updates[k] = json.dumps(v)
            elif k == "ab_enabled":
                updates[k] = int(v)
            else:
                updates[k] = v
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [campaign_id]
    conn.execute(f"UPDATE email_campaigns SET {sets} WHERE id = ?", vals)
    conn.commit()
    return True


# ── Recipient Resolution ──

def _get_unsubscribed_emails() -> set:
    conn = _get_conn()
    rows = conn.execute("SELECT email FROM email_unsubscribes").fetchall()
    return {r["email"].lower() for r in rows}


def _get_bounced_emails() -> set:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT recipient_email FROM email_sends WHERE status = 'bounced' AND bounce_type = 'hard'"
    ).fetchall()
    return {r["recipient_email"].lower() for r in rows}


def _get_already_sent(campaign_id: int) -> set:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT recipient_email FROM email_sends WHERE campaign_id = ?", (campaign_id,)
    ).fetchall()
    return {r["recipient_email"].lower() for r in rows}


def resolve_recipients(campaign_id: int) -> list[dict]:
    """Resolve recipients for a campaign based on type and filters."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        return []

    conn = _get_conn()
    unsubs = _get_unsubscribed_emails()
    bounced = _get_bounced_emails()
    already_sent = _get_already_sent(campaign_id)
    exclude = unsubs | bounced | already_sent

    recipients = []
    target_filter = campaign.get("target_filter", {})

    if campaign["campaign_type"] == "warm":
        recipient_source = target_filter.get("recipient_source", "leads")

        if recipient_source == "custom":
            # Custom emails provided directly by the user
            custom_emails = target_filter.get("custom_emails", [])
            for entry in custom_emails:
                email = entry.get("email", "").strip().lower()
                if email and email not in exclude:
                    recipients.append({
                        "lead_id": None, "contact_id": None,
                        "email": email,
                        "name": entry.get("name", ""),
                        "company": entry.get("company", ""),
                    })
        else:
            # Default: pull from leads table
            conditions = ["email != '' AND email IS NOT NULL"]
            params = []
            statuses = target_filter.get("status", [])
            if statuses:
                placeholders = ",".join("?" * len(statuses))
                conditions.append(f"status IN ({placeholders})")
                params.extend(statuses)
            min_score = target_filter.get("min_score")
            if min_score is not None:
                conditions.append("lead_score >= ?")
                params.append(min_score)
            max_score = target_filter.get("max_score")
            if max_score is not None:
                conditions.append("lead_score <= ?")
                params.append(max_score)
            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            rows = conn.execute(f"SELECT id, email, name, company FROM leads {where}", params).fetchall()
            for r in rows:
                email = r["email"].strip().lower()
                if email not in exclude:
                    recipients.append({"lead_id": r["id"], "contact_id": None, "email": email, "name": r["name"] or "", "company": r["company"] or ""})
    else:
        conditions = ["status = 'active'"]
        params = []
        tags = target_filter.get("tags", [])
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
            conditions.append("(" + " OR ".join(tag_conditions) + ")")
        where = "WHERE " + " AND ".join(conditions)
        rows = conn.execute(f"SELECT id, email, name, company FROM email_contacts {where}", params).fetchall()
        for r in rows:
            email = r["email"].strip().lower()
            if email not in exclude:
                recipients.append({"lead_id": None, "contact_id": r["id"], "email": email, "name": r["name"] or "", "company": r["company"] or ""})

    return recipients


# ── Queue Campaign Sends ──

def queue_campaign_sends(campaign_id: int) -> int:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return 0
    recipients = resolve_recipients(campaign_id)
    if not recipients:
        return 0

    conn = _get_conn()
    now = datetime.now().isoformat()
    ab_enabled = campaign.get("ab_enabled", 0)
    split_pct = campaign.get("ab_split_percentage", 50)
    if ab_enabled:
        random.shuffle(recipients)

    for i, r in enumerate(recipients):
        tracking_id = str(uuid.uuid4())
        variant = "A"
        if ab_enabled:
            variant = "A" if (i / len(recipients) * 100) < split_pct else "B"
        conn.execute(
            """INSERT INTO email_sends
               (campaign_id, contact_id, lead_id, recipient_email, recipient_name,
                tracking_id, ab_variant, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)""",
            (campaign_id, r.get("contact_id"), r.get("lead_id"),
             r["email"], r["name"], tracking_id, variant, now)
        )

    conn.execute(
        "UPDATE email_campaigns SET total_recipients = ?, status = 'sending', updated_at = ? WHERE id = ?",
        (len(recipients), now, campaign_id)
    )
    conn.commit()
    return len(recipients)


# ── Process Batch ──

def process_campaign_batch(campaign_id: int, batch_size: int = None) -> dict:
    batch_size = batch_size or settings.email_batch_size
    campaign = get_campaign(campaign_id)
    if not campaign or campaign["status"] not in ("sending",):
        return {"sent": 0, "failed": 0, "done": True}

    conn = _get_conn()
    queued = conn.execute(
        "SELECT * FROM email_sends WHERE campaign_id = ? AND status = 'queued' LIMIT ?",
        (campaign_id, batch_size)
    ).fetchall()

    if not queued:
        conn.execute("UPDATE email_campaigns SET status = 'sent', updated_at = ? WHERE id = ?", (datetime.now().isoformat(), campaign_id))
        conn.commit()
        return {"sent": 0, "failed": 0, "done": True}

    sent = 0
    failed = 0
    now = datetime.now().isoformat()

    for send_row in queued:
        send = dict(send_row)
        template_id = campaign["template_id"]
        subject = campaign["subject_line"]
        if send["ab_variant"] == "B" and campaign.get("ab_variant_b_template_id"):
            template_id = campaign["ab_variant_b_template_id"]
        if send["ab_variant"] == "B" and campaign.get("ab_variant_b_subject"):
            subject = campaign["ab_variant_b_subject"]

        template = email_templates.get_template(template_id) if template_id else None
        if not template:
            conn.execute("UPDATE email_sends SET status = 'failed', sent_at = ? WHERE id = ?", (now, send["id"]))
            failed += 1
            continue

        first_name = (send["recipient_name"] or "").split()[0] if send["recipient_name"] else ""
        data = {"name": send["recipient_name"], "first_name": first_name, "email": send["recipient_email"], "company": ""}
        html_body = email_templates.render_template(template["html_body"], data)
        text_body = email_templates.render_text(template["text_body"], data) if template.get("text_body") else ""
        rendered_subject = email_templates.render_text(subject or template["subject"], data)

        result = email_sender.send_email(
            to_email=send["recipient_email"], to_name=send["recipient_name"],
            subject=rendered_subject, html_body=html_body, text_body=text_body,
            tracking_id=send["tracking_id"],
            from_name=campaign.get("from_name", ""), from_email=campaign.get("from_email", ""),
            reply_to=campaign.get("reply_to", ""),
        )

        if result["success"]:
            conn.execute("UPDATE email_sends SET status = 'sent', sent_at = ? WHERE id = ?", (now, send["id"]))
            sent += 1
        else:
            bounce_type = result.get("bounce_type", "soft")
            conn.execute("UPDATE email_sends SET status = 'bounced', bounced_at = ?, bounce_type = ?, bounce_reason = ? WHERE id = ?", (now, bounce_type, result.get("details", ""), send["id"]))
            failed += 1
            if bounce_type == "hard" and send.get("contact_id"):
                conn.execute("UPDATE email_contacts SET status = 'bounced', updated_at = ? WHERE id = ?", (now, send["contact_id"]))

    conn.execute("""
        UPDATE email_campaigns SET
            sent_count = (SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND status = 'sent'),
            bounced_count = (SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND status = 'bounced'),
            updated_at = ?
        WHERE id = ?
    """, (campaign_id, campaign_id, now, campaign_id))
    conn.commit()

    remaining = conn.execute("SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND status = 'queued'", (campaign_id,)).fetchone()[0]
    if remaining == 0:
        conn.execute("UPDATE email_campaigns SET status = 'sent', updated_at = ? WHERE id = ?", (now, campaign_id))
        conn.commit()

    return {"sent": sent, "failed": failed, "done": remaining == 0}


# ── Campaign Actions ──

def start_campaign(campaign_id: int) -> dict:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    if campaign["status"] not in ("draft", "scheduled"):
        return {"error": f"Cannot start campaign in '{campaign['status']}' status"}
    count = queue_campaign_sends(campaign_id)
    if count == 0:
        return {"error": "No recipients found matching the campaign filters"}
    return {"status": "sending", "recipients": count}


def schedule_campaign(campaign_id: int, scheduled_at: str) -> dict:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    if campaign["status"] != "draft":
        return {"error": f"Cannot schedule campaign in '{campaign['status']}' status"}
    update_campaign(campaign_id, status="scheduled", scheduled_at=scheduled_at)
    return {"status": "scheduled", "scheduled_at": scheduled_at}


def pause_campaign(campaign_id: int) -> dict:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    if campaign["status"] != "sending":
        return {"error": "Can only pause a sending campaign"}
    update_campaign(campaign_id, status="paused")
    return {"status": "paused"}


def cancel_campaign(campaign_id: int) -> dict:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    if campaign["status"] in ("sent", "cancelled"):
        return {"error": f"Campaign already {campaign['status']}"}
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM email_sends WHERE campaign_id = ? AND status = 'queued'", (campaign_id,))
    conn.execute("UPDATE email_campaigns SET status = 'cancelled', updated_at = ? WHERE id = ?", (now, campaign_id))
    conn.commit()
    return {"status": "cancelled"}


def delete_campaign(campaign_id: int) -> dict:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    conn = _get_conn()
    # Delete click events that reference sends for this campaign
    conn.execute(
        "DELETE FROM email_clicks WHERE send_id IN "
        "(SELECT id FROM email_sends WHERE campaign_id = ?)", (campaign_id,)
    )
    conn.execute("DELETE FROM email_sends WHERE campaign_id = ?", (campaign_id,))
    conn.execute("DELETE FROM email_campaigns WHERE id = ?", (campaign_id,))
    conn.commit()
    return {"status": "deleted"}


def send_test(campaign_id: int, test_email: str) -> dict:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    template = email_templates.get_template(campaign["template_id"]) if campaign.get("template_id") else None
    if not template:
        return {"error": "No template assigned to campaign"}
    data = {"name": "Test User", "first_name": "Test", "company": "Test Co", "email": test_email}
    html_body = email_templates.render_template(template["html_body"], data)
    subject = email_templates.render_text(campaign["subject_line"] or template["subject"], data)
    result = email_sender.send_test_email(to_email=test_email, subject=subject, html_body=html_body, from_name=campaign.get("from_name", ""), from_email=campaign.get("from_email", ""))
    return result


# ── Campaign Recipients & A/B Results ──

def get_campaign_recipients(campaign_id: int, limit: int = 50, offset: int = 0) -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM email_sends WHERE campaign_id = ?", (campaign_id,)).fetchone()[0]
    rows = conn.execute("SELECT * FROM email_sends WHERE campaign_id = ? ORDER BY created_at LIMIT ? OFFSET ?", (campaign_id, limit, offset)).fetchall()
    return {"total": total, "sends": [dict(r) for r in rows]}


def get_ab_results(campaign_id: int) -> dict:
    conn = _get_conn()
    results = {}
    for variant in ("A", "B"):
        row = conn.execute("""
            SELECT COUNT(*) as total,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
                SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced
            FROM email_sends WHERE campaign_id = ? AND ab_variant = ?
        """, (campaign_id, variant)).fetchone()
        r = dict(row)
        r["open_rate"] = round(r["opened"] / r["sent"] * 100, 1) if r["sent"] > 0 else 0
        r["click_rate"] = round(r["clicked"] / r["sent"] * 100, 1) if r["sent"] > 0 else 0
        results[variant] = r
    return results
