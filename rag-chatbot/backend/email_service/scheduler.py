"""APScheduler-based job queue for campaigns, sequences, and stats refresh."""

import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings
from backend.database import _get_conn

_scheduler = None
_daily_send_count = 0
_daily_count_lock = threading.Lock()
_daily_reset_date = ""


def _get_daily_limit() -> int:
    """Get the daily sending limit based on warmup settings."""
    if settings.email_warmup_enabled:
        return settings.email_warmup_daily_limit
    return 500  # Gmail limit


def _check_rate_limit(batch_size: int) -> int:
    """Check and enforce rate limits. Returns how many we can send."""
    global _daily_send_count, _daily_reset_date

    today = datetime.now().strftime("%Y-%m-%d")

    with _daily_count_lock:
        if _daily_reset_date != today:
            _daily_send_count = 0
            _daily_reset_date = today

        limit = _get_daily_limit()
        remaining = limit - _daily_send_count
        if remaining <= 0:
            return 0
        allowed = min(batch_size, remaining)
        _daily_send_count += allowed
        return allowed


def _process_campaigns():
    """Process pending campaign batches. Runs every 30 seconds."""
    try:
        conn = _get_conn()

        now = datetime.now().isoformat()
        scheduled = conn.execute(
            "SELECT id FROM email_campaigns WHERE status = 'scheduled' AND scheduled_at <= ?",
            (now,)
        ).fetchall()

        from backend.email_service import campaigns as email_campaigns

        for row in scheduled:
            email_campaigns.queue_campaign_sends(row["id"])

        sending = conn.execute(
            "SELECT id FROM email_campaigns WHERE status = 'sending'"
        ).fetchall()

        for row in sending:
            allowed = _check_rate_limit(settings.email_batch_size)
            if allowed <= 0:
                print("[Scheduler] Daily send limit reached, pausing until tomorrow")
                break
            email_campaigns.process_campaign_batch(row["id"], batch_size=allowed)

    except Exception as e:
        print(f"[Scheduler] Campaign processing error: {e}")


def _process_sequences():
    """Process sequence enrollments. Runs every 5 minutes."""
    try:
        from backend.email_service import sequences as email_sequences
        email_sequences.process_pending_steps()
    except Exception as e:
        print(f"[Scheduler] Sequence processing error: {e}")


def _refresh_stats():
    """Refresh campaign statistics. Runs every 2 minutes."""
    try:
        conn = _get_conn()
        now = datetime.now().isoformat()

        active_campaigns = conn.execute(
            "SELECT id FROM email_campaigns WHERE status IN ('sending', 'sent') AND updated_at >= datetime('now', '-7 days')"
        ).fetchall()

        for row in active_campaigns:
            cid = row["id"]
            conn.execute("""
                UPDATE email_campaigns SET
                    sent_count = (SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND status = 'sent'),
                    opened_count = (SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND opened_at IS NOT NULL),
                    clicked_count = (SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND clicked_at IS NOT NULL),
                    bounced_count = (SELECT COUNT(*) FROM email_sends WHERE campaign_id = ? AND status = 'bounced'),
                    updated_at = ?
                WHERE id = ?
            """, (cid, cid, cid, cid, now, cid))

        conn.commit()
    except Exception as e:
        print(f"[Scheduler] Stats refresh error: {e}")


def start_scheduler():
    """Start the APScheduler with all jobs."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)

    _scheduler.add_job(
        _process_campaigns,
        trigger=IntervalTrigger(seconds=30),
        id="process_campaigns",
        name="Process campaign email batches",
        replace_existing=True,
    )

    _scheduler.add_job(
        _process_sequences,
        trigger=IntervalTrigger(minutes=5),
        id="process_sequences",
        name="Process sequence enrollments",
        replace_existing=True,
    )

    _scheduler.add_job(
        _refresh_stats,
        trigger=IntervalTrigger(minutes=2),
        id="refresh_stats",
        name="Refresh campaign statistics",
        replace_existing=True,
    )

    _scheduler.start()
    print("[Scheduler] Email scheduler started")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[Scheduler] Email scheduler stopped")
