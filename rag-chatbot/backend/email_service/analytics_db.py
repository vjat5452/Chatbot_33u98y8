"""Email analytics aggregation queries."""

from datetime import datetime, timedelta

from backend.database import _get_conn


def get_overview(days: int = 30) -> dict:
    """Get overall email metrics."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    row = conn.execute("""
        SELECT
            COUNT(*) as total_sent,
            SUM(CASE WHEN status IN ('sent', 'delivered') THEN 1 ELSE 0 END) as delivered,
            SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
            SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
            SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced
        FROM email_sends WHERE status != 'queued' AND created_at >= ?
    """, (since,)).fetchone()

    total_sent = row["total_sent"] or 0
    delivered = row["delivered"] or 0
    opened = row["opened"] or 0
    clicked = row["clicked"] or 0
    bounced = row["bounced"] or 0

    unsubs = conn.execute(
        "SELECT COUNT(*) FROM email_unsubscribes WHERE unsubscribed_at >= ?", (since,)
    ).fetchone()[0]

    return {
        "total_sent": total_sent,
        "total_delivered": delivered,
        "total_opened": opened,
        "total_clicked": clicked,
        "total_bounced": bounced,
        "total_unsubscribed": unsubs,
        "avg_open_rate": round(opened / delivered * 100, 1) if delivered > 0 else 0,
        "avg_click_rate": round(clicked / delivered * 100, 1) if delivered > 0 else 0,
        "avg_bounce_rate": round(bounced / total_sent * 100, 1) if total_sent > 0 else 0,
    }


def get_warm_vs_cold(days: int = 30) -> dict:
    """Compare warm vs cold campaign performance."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    result = {}
    for ctype in ("warm", "cold"):
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN s.status IN ('sent', 'delivered') THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN s.opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN s.clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
                SUM(CASE WHEN s.status = 'bounced' THEN 1 ELSE 0 END) as bounced
            FROM email_sends s
            JOIN email_campaigns c ON c.id = s.campaign_id
            WHERE c.campaign_type = ? AND s.status != 'queued' AND s.created_at >= ?
        """, (ctype, since)).fetchone()

        total = row["total"] or 0
        delivered = row["delivered"] or 0
        opened = row["opened"] or 0
        clicked = row["clicked"] or 0
        bounced = row["bounced"] or 0

        result[ctype] = {
            "total_sent": total,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "bounced": bounced,
            "open_rate": round(opened / delivered * 100, 1) if delivered > 0 else 0,
            "click_rate": round(clicked / delivered * 100, 1) if delivered > 0 else 0,
            "bounce_rate": round(bounced / total * 100, 1) if total > 0 else 0,
        }

    return result


def get_send_time_heatmap(days: int = 90) -> list[dict]:
    """Get engagement by day-of-week and hour for send-time optimization."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    rows = conn.execute("""
        SELECT
            CAST(strftime('%w', opened_at) AS INTEGER) as day_of_week,
            CAST(strftime('%H', opened_at) AS INTEGER) as hour,
            COUNT(*) as opens
        FROM email_sends
        WHERE opened_at IS NOT NULL AND opened_at >= ?
        GROUP BY day_of_week, hour
        ORDER BY day_of_week, hour
    """, (since,)).fetchall()

    return [{"day": r["day_of_week"], "hour": r["hour"], "opens": r["opens"]} for r in rows]


def get_domain_health(days: int = 30) -> list[dict]:
    """Get bounce rates by recipient domain."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    rows = conn.execute("""
        SELECT
            SUBSTR(recipient_email, INSTR(recipient_email, '@') + 1) as domain,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced,
            SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened
        FROM email_sends
        WHERE status != 'queued' AND created_at >= ?
        GROUP BY domain
        HAVING total >= 3
        ORDER BY total DESC
        LIMIT 20
    """, (since,)).fetchall()

    result = []
    for r in rows:
        total = r["total"]
        result.append({
            "domain": r["domain"],
            "total": total,
            "bounced": r["bounced"],
            "bounce_rate": round(r["bounced"] / total * 100, 1) if total > 0 else 0,
            "opened": r["opened"],
            "open_rate": round(r["opened"] / total * 100, 1) if total > 0 else 0,
        })

    return result


def get_send_volume_over_time(days: int = 30) -> list[dict]:
    """Get daily send volume."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    rows = conn.execute("""
        SELECT DATE(sent_at) as date, COUNT(*) as sent,
               SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
               SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked
        FROM email_sends
        WHERE sent_at IS NOT NULL AND sent_at >= ?
        GROUP BY DATE(sent_at)
        ORDER BY date
    """, (since,)).fetchall()

    return [dict(r) for r in rows]


def get_campaign_rankings(days: int = 30, limit: int = 10) -> list[dict]:
    """Get top performing campaigns."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    rows = conn.execute("""
        SELECT c.id, c.name, c.campaign_type, c.status,
               c.total_recipients, c.sent_count, c.opened_count, c.clicked_count,
               c.bounced_count, c.unsubscribed_count,
               CASE WHEN c.sent_count > 0 THEN ROUND(c.opened_count * 100.0 / c.sent_count, 1) ELSE 0 END as open_rate,
               CASE WHEN c.sent_count > 0 THEN ROUND(c.clicked_count * 100.0 / c.sent_count, 1) ELSE 0 END as click_rate
        FROM email_campaigns c
        WHERE c.created_at >= ? AND c.status IN ('sent', 'sending')
        ORDER BY open_rate DESC
        LIMIT ?
    """, (since, limit)).fetchall()

    return [dict(r) for r in rows]
