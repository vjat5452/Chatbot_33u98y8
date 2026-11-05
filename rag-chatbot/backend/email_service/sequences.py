"""Drip campaign sequences: create, manage steps, enroll contacts, process conditional steps."""

import json
import uuid
from datetime import datetime, timedelta

from backend.database import _get_conn
from backend.email_service import templates as email_templates, sender as email_sender


# ── Sequence CRUD ──

def create_sequence(name: str, description: str = "", campaign_type: str = "warm",
                    trigger_event: str = "manual", trigger_config: dict = None) -> int:
    conn = _get_conn()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO email_sequences (name, description, campaign_type, trigger_event, trigger_config, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, description, campaign_type, trigger_event, json.dumps(trigger_config or {}), now, now)
    )
    conn.commit()
    return cursor.lastrowid


def get_sequence(sequence_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM email_sequences WHERE id = ?", (sequence_id,)).fetchone()
    if not row:
        return None
    seq = dict(row)
    seq["trigger_config"] = json.loads(seq.get("trigger_config") or "{}")

    # Attach steps
    steps = conn.execute(
        "SELECT * FROM email_sequence_steps WHERE sequence_id = ? ORDER BY step_order",
        (sequence_id,)
    ).fetchall()
    seq["steps"] = [dict(s) for s in steps]

    # Enrollment count
    count = conn.execute(
        "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ? AND status = 'active'",
        (sequence_id,)
    ).fetchone()[0]
    seq["enrollment_count"] = count

    return seq


def get_sequences(campaign_type: str = None, active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    conditions = []
    params = []
    if campaign_type:
        conditions.append("campaign_type = ?")
        params.append(campaign_type)
    if active_only:
        conditions.append("is_active = 1")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM email_sequences {where} ORDER BY created_at DESC", params
    ).fetchall()

    sequences = []
    for row in rows:
        seq = dict(row)
        seq["trigger_config"] = json.loads(seq.get("trigger_config") or "{}")
        seq["steps"] = []
        # Get enrollment count
        count = conn.execute(
            "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ? AND status = 'active'",
            (seq["id"],)
        ).fetchone()[0]
        seq["enrollment_count"] = count
        sequences.append(seq)

    return sequences


def update_sequence(sequence_id: int, **kwargs) -> bool:
    conn = _get_conn()
    allowed = {"name", "description", "campaign_type", "trigger_event", "trigger_config", "is_active"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            if k == "trigger_config":
                updates[k] = json.dumps(v)
            else:
                updates[k] = v
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [sequence_id]
    conn.execute(f"UPDATE email_sequences SET {sets} WHERE id = ?", vals)
    conn.commit()
    return True


# ── Steps ──

def add_step(sequence_id: int, template_id: int, subject_override: str = "",
             delay_days: int = 0, delay_hours: int = 0,
             condition_type: str = "always") -> int:
    conn = _get_conn()
    # Get next step order
    max_order = conn.execute(
        "SELECT COALESCE(MAX(step_order), 0) FROM email_sequence_steps WHERE sequence_id = ?",
        (sequence_id,)
    ).fetchone()[0]

    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO email_sequence_steps
           (sequence_id, step_order, template_id, subject_override, delay_days, delay_hours, condition_type, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (sequence_id, max_order + 1, template_id, subject_override, delay_days, delay_hours, condition_type, now)
    )
    conn.commit()
    return cursor.lastrowid


def delete_step(step_id: int):
    conn = _get_conn()
    conn.execute("DELETE FROM email_sequence_steps WHERE id = ?", (step_id,))
    conn.commit()


# ── Enrollment ──

def enroll(sequence_id: int, contact_ids: list[int] = None, lead_ids: list[int] = None) -> int:
    """Enroll contacts/leads in a sequence. Returns count enrolled."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    seq = get_sequence(sequence_id)
    if not seq or not seq.get("steps"):
        return 0

    first_step = seq["steps"][0]
    next_at = (datetime.now() + timedelta(
        days=first_step.get("delay_days", 0),
        hours=first_step.get("delay_hours", 0)
    )).isoformat()

    enrolled = 0

    for cid in (contact_ids or []):
        # Check not already enrolled
        existing = conn.execute(
            "SELECT 1 FROM email_sequence_enrollments WHERE sequence_id = ? AND contact_id = ? AND status = 'active'",
            (sequence_id, cid)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """INSERT INTO email_sequence_enrollments
               (sequence_id, contact_id, current_step, status, next_step_at, enrolled_at)
               VALUES (?, ?, 1, 'active', ?, ?)""",
            (sequence_id, cid, next_at, now)
        )
        enrolled += 1

    for lid in (lead_ids or []):
        existing = conn.execute(
            "SELECT 1 FROM email_sequence_enrollments WHERE sequence_id = ? AND lead_id = ? AND status = 'active'",
            (sequence_id, lid)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """INSERT INTO email_sequence_enrollments
               (sequence_id, lead_id, current_step, status, next_step_at, enrolled_at)
               VALUES (?, ?, 1, 'active', ?, ?)""",
            (sequence_id, lid, next_at, now)
        )
        enrolled += 1

    conn.commit()
    return enrolled


# ── Process Pending Steps ──

def process_pending_steps():
    """Process all enrollments where next_step_at has passed."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    pending = conn.execute(
        """SELECT e.*, s.name as seq_name FROM email_sequence_enrollments e
           JOIN email_sequences s ON s.id = e.sequence_id
           WHERE e.status = 'active' AND e.next_step_at <= ? AND s.is_active = 1""",
        (now,)
    ).fetchall()

    for enrollment in pending:
        enrollment = dict(enrollment)
        _process_single_enrollment(enrollment)


def _process_single_enrollment(enrollment: dict):
    """Process a single enrollment step."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    seq = get_sequence(enrollment["sequence_id"])
    if not seq:
        return

    steps = seq["steps"]
    current_step_num = enrollment["current_step"]

    # Find the current step
    current_step = None
    for s in steps:
        if s["step_order"] == current_step_num:
            current_step = s
            break

    if not current_step:
        # No more steps → complete
        conn.execute(
            "UPDATE email_sequence_enrollments SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, enrollment["id"])
        )
        conn.commit()
        return

    # Check condition
    if not _check_step_condition(enrollment, current_step):
        # Condition not met → skip to next step
        _advance_enrollment(enrollment, steps, current_step_num)
        return

    # Resolve recipient email
    email = None
    name = ""
    if enrollment.get("contact_id"):
        contact = conn.execute(
            "SELECT email, name FROM email_contacts WHERE id = ?", (enrollment["contact_id"],)
        ).fetchone()
        if contact:
            email = contact["email"]
            name = contact["name"]
    elif enrollment.get("lead_id"):
        lead = conn.execute(
            "SELECT email, name FROM leads WHERE id = ?", (enrollment["lead_id"],)
        ).fetchone()
        if lead:
            email = lead["email"]
            name = lead["name"]

    if not email:
        conn.execute(
            "UPDATE email_sequence_enrollments SET status = 'cancelled' WHERE id = ?",
            (enrollment["id"],)
        )
        conn.commit()
        return

    # Check unsubscribe
    from backend.email_service.tracking import is_unsubscribed
    if is_unsubscribed(email):
        conn.execute(
            "UPDATE email_sequence_enrollments SET status = 'cancelled' WHERE id = ?",
            (enrollment["id"],)
        )
        conn.commit()
        return

    # Render and send
    template = email_templates.get_template(current_step["template_id"])
    if not template:
        _advance_enrollment(enrollment, steps, current_step_num)
        return

    first_name = name.split()[0] if name else ""
    data = {"name": name, "first_name": first_name, "email": email}
    html_body = email_templates.render_template(template["html_body"], data)
    text_body = email_templates.render_text(template["text_body"], data) if template.get("text_body") else ""
    subject = email_templates.render_text(
        current_step.get("subject_override") or template["subject"], data
    )

    tracking_id = str(uuid.uuid4())

    # Create a send record for tracking
    conn.execute(
        """INSERT INTO email_sends
           (campaign_id, contact_id, lead_id, recipient_email, recipient_name,
            tracking_id, status, created_at)
           VALUES (0, ?, ?, ?, ?, ?, 'queued', ?)""",
        (enrollment.get("contact_id"), enrollment.get("lead_id"),
         email, name, tracking_id, now)
    )

    result = email_sender.send_email(
        to_email=email, to_name=name, subject=subject,
        html_body=html_body, text_body=text_body, tracking_id=tracking_id,
    )

    if result["success"]:
        conn.execute(
            "UPDATE email_sends SET status = 'sent', sent_at = ? WHERE tracking_id = ?",
            (now, tracking_id)
        )

    conn.commit()

    # Advance to next step
    _advance_enrollment(enrollment, steps, current_step_num)


def _advance_enrollment(enrollment: dict, steps: list, current_step_num: int):
    """Move enrollment to the next step or complete it."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    # Find next step
    next_step = None
    for s in steps:
        if s["step_order"] > current_step_num:
            next_step = s
            break

    if not next_step:
        # Sequence complete
        conn.execute(
            "UPDATE email_sequence_enrollments SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, enrollment["id"])
        )
    else:
        next_at = (datetime.now() + timedelta(
            days=next_step.get("delay_days", 0),
            hours=next_step.get("delay_hours", 0)
        )).isoformat()
        conn.execute(
            "UPDATE email_sequence_enrollments SET current_step = ?, next_step_at = ? WHERE id = ?",
            (next_step["step_order"], next_at, enrollment["id"])
        )

    conn.commit()


def _check_step_condition(enrollment: dict, step: dict) -> bool:
    """Check if the step's condition is met based on previous email engagement."""
    condition = step.get("condition_type", "always")
    if condition == "always":
        return True

    conn = _get_conn()

    # Find the most recent send for this enrollment
    contact_id = enrollment.get("contact_id")
    lead_id = enrollment.get("lead_id")

    conditions = ["campaign_id = 0"]
    params = []
    if contact_id:
        conditions.append("contact_id = ?")
        params.append(contact_id)
    elif lead_id:
        conditions.append("lead_id = ?")
        params.append(lead_id)
    else:
        return True

    where = " AND ".join(conditions)
    last_send = conn.execute(
        f"SELECT opened_at, clicked_at FROM email_sends WHERE {where} ORDER BY created_at DESC LIMIT 1",
        params
    ).fetchone()

    if not last_send:
        return condition in ("always", "if_not_opened", "if_not_clicked")

    if condition == "if_opened":
        return last_send["opened_at"] is not None
    elif condition == "if_not_opened":
        return last_send["opened_at"] is None
    elif condition == "if_clicked":
        return last_send["clicked_at"] is not None
    elif condition == "if_not_clicked":
        return last_send["clicked_at"] is None

    return True


# ── Funnel Analytics ──

def get_sequence_funnel(sequence_id: int) -> dict:
    """Get funnel analytics for a sequence."""
    conn = _get_conn()

    seq = get_sequence(sequence_id)
    if not seq:
        return {}

    total_enrolled = conn.execute(
        "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ?",
        (sequence_id,)
    ).fetchone()[0]

    active = conn.execute(
        "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ? AND status = 'active'",
        (sequence_id,)
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ? AND status = 'completed'",
        (sequence_id,)
    ).fetchone()[0]

    cancelled = conn.execute(
        "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ? AND status = 'cancelled'",
        (sequence_id,)
    ).fetchone()[0]

    # Per-step stats
    step_stats = []
    for step in seq.get("steps", []):
        at_step = conn.execute(
            "SELECT COUNT(*) FROM email_sequence_enrollments WHERE sequence_id = ? AND current_step = ? AND status = 'active'",
            (sequence_id, step["step_order"])
        ).fetchone()[0]
        step_stats.append({
            "step_order": step["step_order"],
            "template_id": step["template_id"],
            "condition": step["condition_type"],
            "active_at_step": at_step,
        })

    return {
        "total_enrolled": total_enrolled,
        "active": active,
        "completed": completed,
        "cancelled": cancelled,
        "steps": step_stats,
    }


# ── Trigger Hooks (called from lead_capture) ──

def check_triggers(lead_id: int, event: str, data: dict = None):
    """Check if any sequence should auto-enroll this lead based on triggers."""
    conn = _get_conn()
    sequences = conn.execute(
        "SELECT id, trigger_event, trigger_config FROM email_sequences WHERE is_active = 1 AND trigger_event != 'manual'"
    ).fetchall()

    for seq in sequences:
        trigger_event = seq["trigger_event"]
        trigger_config = json.loads(seq["trigger_config"] or "{}")

        if trigger_event == "lead_status_change" and event == "status_change":
            target_statuses = trigger_config.get("statuses", [])
            if data and data.get("new_status") in target_statuses:
                enroll(seq["id"], lead_ids=[lead_id])

        elif trigger_event == "score_threshold" and event == "score_update":
            threshold = trigger_config.get("min_score", 0)
            if data and data.get("score", 0) >= threshold:
                enroll(seq["id"], lead_ids=[lead_id])
