"""Email tracking endpoints: open pixel, click redirect, unsubscribe."""

import base64
from datetime import datetime

from backend.database import _get_conn

# 1x1 transparent GIF (43 bytes)
TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def record_open(tracking_id: str) -> bool:
    """Record an email open event. Returns True if found."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    send = conn.execute(
        "SELECT id, campaign_id, opened_at, open_count FROM email_sends WHERE tracking_id = ?",
        (tracking_id,)
    ).fetchone()

    if not send:
        return False

    # Update open count and first-open timestamp
    if send["opened_at"] is None:
        conn.execute(
            "UPDATE email_sends SET opened_at = ?, open_count = open_count + 1 WHERE id = ?",
            (now, send["id"])
        )
        # Update campaign opened counter
        conn.execute(
            "UPDATE email_campaigns SET opened_count = opened_count + 1, updated_at = ? WHERE id = ?",
            (now, send["campaign_id"])
        )
    else:
        conn.execute(
            "UPDATE email_sends SET open_count = open_count + 1 WHERE id = ?",
            (send["id"],)
        )

    conn.commit()
    return True


def record_click(tracking_id: str, url: str) -> bool:
    """Record a link click. Returns True if found."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    send = conn.execute(
        "SELECT id, campaign_id, clicked_at, click_count FROM email_sends WHERE tracking_id = ?",
        (tracking_id,)
    ).fetchone()

    if not send:
        return False

    # Insert click record
    conn.execute(
        "INSERT INTO email_clicks (send_id, tracking_id, original_url, clicked_at) VALUES (?, ?, ?, ?)",
        (send["id"], tracking_id, url, now)
    )

    # Update send record
    if send["clicked_at"] is None:
        conn.execute(
            "UPDATE email_sends SET clicked_at = ?, click_count = click_count + 1 WHERE id = ?",
            (now, send["id"])
        )
        # Update campaign clicked counter
        conn.execute(
            "UPDATE email_campaigns SET clicked_count = clicked_count + 1, updated_at = ? WHERE id = ?",
            (now, send["campaign_id"])
        )
    else:
        conn.execute(
            "UPDATE email_sends SET click_count = click_count + 1 WHERE id = ?",
            (send["id"],)
        )

    conn.commit()
    return True


def process_unsubscribe(tracking_id: str, reason: str = "") -> dict | None:
    """Process an unsubscribe request. Returns info dict or None."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    send = conn.execute(
        "SELECT id, campaign_id, recipient_email, recipient_name, contact_id FROM email_sends WHERE tracking_id = ?",
        (tracking_id,)
    ).fetchone()

    if not send:
        return None

    email = send["recipient_email"].lower()

    # Add to unsubscribe list (ignore duplicates)
    try:
        conn.execute(
            "INSERT INTO email_unsubscribes (email, reason, campaign_id, unsubscribed_at) VALUES (?, ?, ?, ?)",
            (email, reason, send["campaign_id"], now)
        )
    except Exception:
        pass  # Already unsubscribed

    # Update contact status if exists
    if send["contact_id"]:
        conn.execute(
            "UPDATE email_contacts SET status = 'unsubscribed', updated_at = ? WHERE id = ?",
            (now, send["contact_id"])
        )

    # Update campaign unsubscribe counter
    conn.execute(
        "UPDATE email_campaigns SET unsubscribed_count = unsubscribed_count + 1, updated_at = ? WHERE id = ?",
        (now, send["campaign_id"])
    )

    conn.commit()

    return {
        "email": email,
        "name": send["recipient_name"],
    }


def get_unsubscribe_info(tracking_id: str) -> dict | None:
    """Get recipient info for the unsubscribe confirmation page."""
    conn = _get_conn()
    send = conn.execute(
        "SELECT recipient_email, recipient_name FROM email_sends WHERE tracking_id = ?",
        (tracking_id,)
    ).fetchone()

    if not send:
        return None

    # Check if already unsubscribed
    already = conn.execute(
        "SELECT 1 FROM email_unsubscribes WHERE email = ?",
        (send["recipient_email"].lower(),)
    ).fetchone()

    return {
        "email": send["recipient_email"],
        "name": send["recipient_name"],
        "already_unsubscribed": bool(already),
    }


def is_unsubscribed(email: str) -> bool:
    """Check if an email is on the unsubscribe list."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM email_unsubscribes WHERE email = ?", (email.lower(),)
    ).fetchone()
    return bool(row)
