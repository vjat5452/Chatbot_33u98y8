"""SQLite database layer for leads, conversations, analytics, and feedback persistence."""

import csv
import io
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from backend.config import settings

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    """Create tables if they don't exist. Called at startup."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            company TEXT DEFAULT '',
            source_page TEXT DEFAULT '',
            lead_score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            page_url TEXT DEFAULT '',
            intent TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT DEFAULT '{}',
            page_url TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_index INTEGER NOT NULL,
            feedback TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score);
        CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
        CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_session_role ON conversations(session_id, role, id);
        CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics(event_type);
        CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);

        CREATE TABLE IF NOT EXISTS reported_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message TEXT NOT NULL,
            page_url TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            admin_notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_issues_status ON reported_issues(status);
        CREATE INDEX IF NOT EXISTS idx_issues_created ON reported_issues(created_at);

        -- Email Sales System tables --

        CREATE TABLE IF NOT EXISTS email_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            company TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            source TEXT DEFAULT 'manual',
            tags TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            lead_id INTEGER,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );
        CREATE INDEX IF NOT EXISTS idx_email_contacts_status ON email_contacts(status);
        CREATE INDEX IF NOT EXISTS idx_email_contacts_tags ON email_contacts(tags);

        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT DEFAULT '',
            html_body TEXT DEFAULT '',
            text_body TEXT DEFAULT '',
            category TEXT DEFAULT 'promotion',
            variables TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS email_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            campaign_type TEXT DEFAULT 'warm',
            template_id INTEGER,
            subject_line TEXT DEFAULT '',
            from_name TEXT DEFAULT '',
            from_email TEXT DEFAULT '',
            reply_to TEXT DEFAULT '',
            target_filter TEXT DEFAULT '{}',
            ab_enabled INTEGER DEFAULT 0,
            ab_variant_b_subject TEXT DEFAULT '',
            ab_variant_b_template_id INTEGER,
            ab_split_percentage INTEGER DEFAULT 50,
            status TEXT DEFAULT 'draft',
            scheduled_at TEXT,
            total_recipients INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            opened_count INTEGER DEFAULT 0,
            clicked_count INTEGER DEFAULT 0,
            bounced_count INTEGER DEFAULT 0,
            unsubscribed_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (template_id) REFERENCES email_templates(id)
        );
        CREATE INDEX IF NOT EXISTS idx_email_campaigns_status ON email_campaigns(status);
        CREATE INDEX IF NOT EXISTS idx_email_campaigns_type ON email_campaigns(campaign_type);

        CREATE TABLE IF NOT EXISTS email_sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            contact_id INTEGER,
            lead_id INTEGER,
            recipient_email TEXT NOT NULL,
            recipient_name TEXT DEFAULT '',
            tracking_id TEXT UNIQUE NOT NULL,
            ab_variant TEXT DEFAULT 'A',
            status TEXT DEFAULT 'queued',
            sent_at TEXT,
            opened_at TEXT,
            clicked_at TEXT,
            bounced_at TEXT,
            bounce_type TEXT DEFAULT '',
            bounce_reason TEXT DEFAULT '',
            open_count INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
            FOREIGN KEY (contact_id) REFERENCES email_contacts(id),
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );
        CREATE INDEX IF NOT EXISTS idx_email_sends_campaign ON email_sends(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_email_sends_tracking ON email_sends(tracking_id);
        CREATE INDEX IF NOT EXISTS idx_email_sends_status ON email_sends(status);
        CREATE INDEX IF NOT EXISTS idx_email_sends_recipient ON email_sends(recipient_email);

        CREATE TABLE IF NOT EXISTS email_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            send_id INTEGER NOT NULL,
            tracking_id TEXT NOT NULL,
            original_url TEXT NOT NULL,
            clicked_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (send_id) REFERENCES email_sends(id)
        );
        CREATE INDEX IF NOT EXISTS idx_email_clicks_send ON email_clicks(send_id);
        CREATE INDEX IF NOT EXISTS idx_email_clicks_tracking ON email_clicks(tracking_id);

        CREATE TABLE IF NOT EXISTS email_sequences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            campaign_type TEXT DEFAULT 'warm',
            trigger_event TEXT DEFAULT 'manual',
            trigger_config TEXT DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS email_sequence_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sequence_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            subject_override TEXT DEFAULT '',
            delay_days INTEGER DEFAULT 0,
            delay_hours INTEGER DEFAULT 0,
            condition_type TEXT DEFAULT 'always',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (sequence_id) REFERENCES email_sequences(id),
            FOREIGN KEY (template_id) REFERENCES email_templates(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sequence_steps_seq ON email_sequence_steps(sequence_id);

        CREATE TABLE IF NOT EXISTS email_sequence_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sequence_id INTEGER NOT NULL,
            contact_id INTEGER,
            lead_id INTEGER,
            current_step INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            next_step_at TEXT,
            enrolled_at TEXT DEFAULT (datetime('now', 'localtime')),
            completed_at TEXT,
            FOREIGN KEY (sequence_id) REFERENCES email_sequences(id),
            FOREIGN KEY (contact_id) REFERENCES email_contacts(id),
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );
        CREATE INDEX IF NOT EXISTS idx_enrollments_sequence ON email_sequence_enrollments(sequence_id);
        CREATE INDEX IF NOT EXISTS idx_enrollments_status ON email_sequence_enrollments(status);
        CREATE INDEX IF NOT EXISTS idx_enrollments_next ON email_sequence_enrollments(next_step_at);

        CREATE TABLE IF NOT EXISTS email_unsubscribes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            reason TEXT DEFAULT '',
            campaign_id INTEGER,
            unsubscribed_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_unsubscribes_email ON email_unsubscribes(email);

        -- Golden Q&A pairs (curated ideal answers for the chatbot) --

        CREATE TABLE IF NOT EXISTS golden_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_golden_qa_active ON golden_qa(is_active);

        -- WhatsApp Messages --

        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_wa_session ON whatsapp_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_wa_timestamp ON whatsapp_messages(timestamp);

        -- Ingested files tracking (uploaded PDFs/SQLs) --

        CREATE TABLE IF NOT EXISTS ingested_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            total_chunks INTEGER DEFAULT 0,
            total_pages INTEGER DEFAULT 0,
            total_rows INTEGER DEFAULT 0,
            tables_json TEXT DEFAULT '[]',
            chunk_ids_json TEXT DEFAULT '[]',
            storage_path TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            uploaded_at TEXT DEFAULT (datetime('now', 'localtime')),
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ingested_status ON ingested_files(status);
    """)
    conn.commit()

    # Migration: add intent column to conversations table (for existing databases)
    try:
        conn.execute("SELECT intent FROM conversations LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE conversations ADD COLUMN intent TEXT DEFAULT ''")
        conn.commit()
        print("[DB] Migrated: added 'intent' column to conversations")

    print("[DB] SQLite database initialized")


# ── Lead operations ──

def save_lead(session_id: str, name: str = "", email: str = "", phone: str = "",
              company: str = "", source_page: str = "") -> int:
    """Insert or update a lead. Returns the lead ID."""
    # Validate name before saving — reject common English words / sentences
    if name:
        from backend.lead_capture import _is_valid_name
        if not _is_valid_name(name):
            name = ""
    conn = _get_conn()
    now = datetime.now().isoformat()

    # Try to update existing lead for this session
    existing = conn.execute(
        "SELECT id, name, email, phone, company FROM leads WHERE session_id = ?",
        (session_id,)
    ).fetchone()

    if existing:
        # Merge: only overwrite non-empty fields
        updates = {}
        if name and not existing["name"]:
            updates["name"] = name
        if email and not existing["email"]:
            updates["email"] = email
        if phone and not existing["phone"]:
            updates["phone"] = phone
        if company and not existing["company"]:
            updates["company"] = company
        if source_page:
            updates["source_page"] = source_page

        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values())
            conn.execute(
                f"UPDATE leads SET {sets}, updated_at = ? WHERE session_id = ?",
                vals + [now, session_id]
            )
            conn.commit()
        return existing["id"]

    # Insert new lead
    cursor = conn.execute(
        """INSERT INTO leads (session_id, name, email, phone, company, source_page, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, name, email, phone, company, source_page, now, now)
    )
    conn.commit()
    return cursor.lastrowid


def update_lead_score(session_id: str, score: int):
    """Update lead score and auto-classify status."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    if score >= settings.lead_hot_threshold:
        status = "hot"
    elif score >= settings.lead_qualified_threshold:
        status = "qualified"
    elif score > 20:
        status = "engaged"
    else:
        status = "new"

    # Don't downgrade from 'converted'
    existing = conn.execute(
        "SELECT status FROM leads WHERE session_id = ?", (session_id,)
    ).fetchone()

    if existing and existing["status"] == "converted":
        # Only update score, keep converted status
        conn.execute(
            "UPDATE leads SET lead_score = ?, updated_at = ? WHERE session_id = ?",
            (score, now, session_id)
        )
    else:
        conn.execute(
            """INSERT INTO leads (session_id, lead_score, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
               lead_score = excluded.lead_score,
               status = excluded.status,
               updated_at = excluded.updated_at""",
            (session_id, score, status, now, now)
        )
    conn.commit()


def update_lead_status(lead_id: int, status: str, notes: str = None):
    """Manually update lead status and/or notes."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    if notes is not None:
        conn.execute(
            "UPDATE leads SET status = ?, notes = ?, updated_at = ? WHERE id = ?",
            (status, notes, now, lead_id)
        )
    else:
        conn.execute(
            "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, lead_id)
        )
    conn.commit()


def get_leads(status: str = None, search: str = None, min_score: int = None,
              max_score: int = None, created_after: str = None,
              sort: str = "created_at", order: str = "desc",
              limit: int = 50, offset: int = 0) -> dict:
    """Get paginated leads list with filters."""
    conn = _get_conn()
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if search:
        conditions.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR company LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])
    if min_score is not None:
        conditions.append("lead_score >= ?")
        params.append(min_score)
    if max_score is not None:
        conditions.append("lead_score <= ?")
        params.append(max_score)
    if created_after:
        conditions.append("created_at >= ?")
        params.append(created_after)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Validate sort column
    allowed_sorts = {"created_at", "updated_at", "lead_score", "name", "status"}
    if sort not in allowed_sorts:
        sort = "created_at"
    order_dir = "ASC" if order.lower() == "asc" else "DESC"

    # Count total
    total = conn.execute(f"SELECT COUNT(*) FROM leads {where}", params).fetchone()[0]

    # Fetch page
    rows = conn.execute(
        f"SELECT * FROM leads {where} ORDER BY {sort} {order_dir} LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    return {
        "total": total,
        "leads": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
    }


def get_lead(lead_id: int) -> dict | None:
    """Get a single lead with conversation history."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not row:
        return None

    lead = dict(row)
    # Attach conversation
    messages = conn.execute(
        "SELECT role, content, page_url, timestamp FROM conversations WHERE session_id = ? ORDER BY id",
        (lead["session_id"],)
    ).fetchall()
    lead["conversation"] = [dict(m) for m in messages]
    return lead


# ── Conversation operations ──

def save_message(session_id: str, role: str, content: str, page_url: str = ""):
    """Save a single chat message to persistent storage."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, page_url, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, page_url, now)
    )
    conn.commit()


def save_messages_batch(session_id: str, messages: list[dict]):
    """Save multiple messages in a single transaction (fewer fsync calls)."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.executemany(
        "INSERT INTO conversations (session_id, role, content, page_url, intent, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        [(session_id, m["role"], m["content"], m.get("page_url", ""), m.get("intent", ""), now) for m in messages]
    )
    conn.commit()


def get_conversations(session_id: str) -> list[dict]:
    """Get full conversation for a session."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, page_url, timestamp FROM conversations WHERE session_id = ? ORDER BY id",
        (session_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_recent_conversations(limit: int = 50, offset: int = 0) -> dict:
    """Get recent conversations grouped by session — single JOIN query instead of N+2."""
    conn = _get_conn()

    total = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]

    # Single query: session stats + first user message preview + lead info via LEFT JOINs
    # Uses a CTE for the first user message to avoid a correlated subquery per row
    rows = conn.execute("""
        WITH first_user_msg AS (
            SELECT session_id, MIN(id) as first_id
            FROM conversations
            WHERE role = 'user'
            GROUP BY session_id
        )
        SELECT
            c.session_id,
            c.message_count,
            c.started_at,
            c.last_message_at,
            c.page_url,
            COALESCE(SUBSTR(p.content, 1, 100), '') as preview,
            l.id as lead_id,
            l.name as lead_name,
            l.email as lead_email,
            l.lead_score,
            l.status as lead_status
        FROM (
            SELECT session_id,
                   COUNT(*) as message_count,
                   MIN(timestamp) as started_at,
                   MAX(timestamp) as last_message_at,
                   MAX(page_url) as page_url
            FROM conversations
            GROUP BY session_id
            ORDER BY last_message_at DESC
            LIMIT ? OFFSET ?
        ) c
        LEFT JOIN first_user_msg f ON f.session_id = c.session_id
        LEFT JOIN conversations p ON p.id = f.first_id
        LEFT JOIN leads l ON l.session_id = c.session_id
        ORDER BY c.last_message_at DESC
    """, (limit, offset)).fetchall()

    sessions = []
    for row in rows:
        session = {
            "session_id": row["session_id"],
            "message_count": row["message_count"],
            "started_at": row["started_at"],
            "last_message_at": row["last_message_at"],
            "page_url": row["page_url"],
            "preview": row["preview"],
            "lead": {
                "id": row["lead_id"],
                "name": row["lead_name"],
                "email": row["lead_email"],
                "lead_score": row["lead_score"],
                "status": row["lead_status"],
            } if row["lead_id"] else None,
        }
        sessions.append(session)

    return {"total": total, "conversations": sessions, "limit": limit, "offset": offset}


# ── Analytics operations ──

def track_event(session_id: str, event_type: str, event_data: dict = None, page_url: str = ""):
    """Track an analytics event."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO analytics (session_id, event_type, event_data, page_url, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, event_type, json.dumps(event_data or {}), page_url, now)
    )
    conn.commit()


def save_feedback_record(session_id: str, message_index: int, feedback: str):
    """Save feedback to SQLite (persistent, alongside Redis/memory)."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO feedback (session_id, message_index, feedback, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, message_index, feedback, now)
    )
    conn.commit()


# ── Dashboard & analytics aggregations ──

def get_dashboard_stats() -> dict:
    """Get overview numbers for the dashboard."""
    conn = _get_conn()
    today = datetime.now().strftime("%Y-%m-%d")

    total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    hot_leads = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'hot'").fetchone()[0]
    messages_today = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE timestamp >= ?", (today,)
    ).fetchone()[0]

    # Satisfaction rate
    total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    positive_feedback = conn.execute("SELECT COUNT(*) FROM feedback WHERE feedback = 'up'").fetchone()[0]
    satisfaction = round((positive_feedback / total_feedback * 100) if total_feedback > 0 else 0, 1)

    # Active sessions today
    active_sessions = conn.execute(
        "SELECT COUNT(DISTINCT session_id) FROM conversations WHERE timestamp >= ?", (today,)
    ).fetchone()[0]

    # Average lead score
    avg_score_row = conn.execute("SELECT AVG(lead_score) FROM leads").fetchone()
    avg_score = round(avg_score_row[0] or 0, 1)

    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "messages_today": messages_today,
        "satisfaction_rate": satisfaction,
        "active_sessions_today": active_sessions,
        "avg_lead_score": avg_score,
    }


def _calc_trend(current: float, previous: float) -> float:
    """Calculate percentage change between two values."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


def get_dashboard_stats_with_trends() -> dict:
    """Get dashboard stats with period-over-period trend deltas."""
    conn = _get_conn()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    sixty_days_ago = (now - timedelta(days=60)).isoformat()

    # Current stats (same as get_dashboard_stats)
    total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    hot_leads = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'hot'").fetchone()[0]
    messages_today = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE timestamp >= ?", (today,)
    ).fetchone()[0]

    total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    positive_feedback = conn.execute("SELECT COUNT(*) FROM feedback WHERE feedback = 'up'").fetchone()[0]
    satisfaction = round((positive_feedback / total_feedback * 100) if total_feedback > 0 else 0, 1)

    active_sessions = conn.execute(
        "SELECT COUNT(DISTINCT session_id) FROM conversations WHERE timestamp >= ?", (today,)
    ).fetchone()[0]

    avg_score_row = conn.execute("SELECT AVG(lead_score) FROM leads").fetchone()
    avg_score = round(avg_score_row[0] or 0, 1)

    # --- Trend calculations ---

    # Leads: last 30d vs prior 30d
    leads_current = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE created_at >= ?", (thirty_days_ago,)
    ).fetchone()[0]
    leads_previous = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE created_at >= ? AND created_at < ?",
        (sixty_days_ago, thirty_days_ago)
    ).fetchone()[0]

    # Hot leads: last 30d vs prior 30d
    hot_current = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status = 'hot' AND created_at >= ?", (thirty_days_ago,)
    ).fetchone()[0]
    hot_previous = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status = 'hot' AND created_at >= ? AND created_at < ?",
        (sixty_days_ago, thirty_days_ago)
    ).fetchone()[0]

    # Messages: today vs yesterday
    messages_yesterday = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE timestamp >= ? AND timestamp < ?",
        (yesterday, today)
    ).fetchone()[0]

    # Satisfaction: last 30d vs prior 30d
    sat_current_total = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE timestamp >= ?", (thirty_days_ago,)
    ).fetchone()[0]
    sat_current_pos = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE feedback = 'up' AND timestamp >= ?", (thirty_days_ago,)
    ).fetchone()[0]
    sat_prev_total = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE timestamp >= ? AND timestamp < ?",
        (sixty_days_ago, thirty_days_ago)
    ).fetchone()[0]
    sat_prev_pos = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE feedback = 'up' AND timestamp >= ? AND timestamp < ?",
        (sixty_days_ago, thirty_days_ago)
    ).fetchone()[0]
    sat_current_rate = (sat_current_pos / sat_current_total * 100) if sat_current_total > 0 else 0
    sat_prev_rate = (sat_prev_pos / sat_prev_total * 100) if sat_prev_total > 0 else 0

    # Active sessions: today vs yesterday
    sessions_yesterday = conn.execute(
        "SELECT COUNT(DISTINCT session_id) FROM conversations WHERE timestamp >= ? AND timestamp < ?",
        (yesterday, today)
    ).fetchone()[0]

    # Avg lead score: current vs 30d ago snapshot (leads created in last 30d vs prior 30d)
    avg_current = conn.execute(
        "SELECT AVG(lead_score) FROM leads WHERE created_at >= ?", (thirty_days_ago,)
    ).fetchone()[0] or 0
    avg_previous = conn.execute(
        "SELECT AVG(lead_score) FROM leads WHERE created_at >= ? AND created_at < ?",
        (sixty_days_ago, thirty_days_ago)
    ).fetchone()[0] or 0

    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "messages_today": messages_today,
        "satisfaction_rate": satisfaction,
        "active_sessions_today": active_sessions,
        "avg_lead_score": avg_score,
        "total_leads_trend": _calc_trend(leads_current, leads_previous),
        "hot_leads_trend": _calc_trend(hot_current, hot_previous),
        "messages_today_trend": _calc_trend(messages_today, messages_yesterday),
        "satisfaction_rate_trend": _calc_trend(sat_current_rate, sat_prev_rate),
        "active_sessions_today_trend": _calc_trend(active_sessions, sessions_yesterday),
        "avg_lead_score_trend": _calc_trend(avg_current, avg_previous),
    }


def get_analytics_summary(days: int = 30) -> dict:
    """Get aggregated analytics data for charts."""
    conn = _get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    # Messages per day
    messages_per_day = conn.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM conversations
        WHERE timestamp >= ? AND role = 'user'
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, (since,)).fetchall()

    # Popular topics (from analytics events)
    popular_topics = conn.execute("""
        SELECT json_extract(event_data, '$.topic') as topic, COUNT(*) as count
        FROM analytics
        WHERE event_type = 'message_sent' AND timestamp >= ?
          AND json_extract(event_data, '$.topic') IS NOT NULL
        GROUP BY topic
        ORDER BY count DESC
        LIMIT 10
    """, (since,)).fetchall()

    # Lead funnel
    funnel = {}
    for status in ("new", "engaged", "qualified", "hot", "converted"):
        funnel[status] = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE status = ?", (status,)
        ).fetchone()[0]

    # Peak hours
    peak_hours = conn.execute("""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
        FROM conversations
        WHERE timestamp >= ? AND role = 'user'
        GROUP BY hour
        ORDER BY hour
    """, (since,)).fetchall()

    # Busiest pages
    busiest_pages = conn.execute("""
        SELECT page_url, COUNT(*) as count
        FROM conversations
        WHERE timestamp >= ? AND page_url != '' AND role = 'user'
        GROUP BY page_url
        ORDER BY count DESC
        LIMIT 10
    """, (since,)).fetchall()

    # Satisfaction trend (by day)
    satisfaction_trend = conn.execute("""
        SELECT DATE(timestamp) as date,
               SUM(CASE WHEN feedback = 'up' THEN 1 ELSE 0 END) as positive,
               COUNT(*) as total
        FROM feedback
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, (since,)).fetchall()

    return {
        "messages_per_day": [dict(r) for r in messages_per_day],
        "popular_topics": [dict(r) for r in popular_topics],
        "lead_funnel": funnel,
        "peak_hours": [dict(r) for r in peak_hours],
        "busiest_pages": [dict(r) for r in busiest_pages],
        "satisfaction_trend": [
            {"date": r["date"], "rate": round(r["positive"] / r["total"] * 100, 1) if r["total"] > 0 else 0}
            for r in satisfaction_trend
        ],
    }


# ── Reported Issues operations ──

def save_issue(session_id: str, message: str, page_url: str = "") -> int:
    """Save a reported issue. Returns the issue ID."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO reported_issues (session_id, message, page_url, created_at) VALUES (?, ?, ?, ?)",
        (session_id, message, page_url, now)
    )
    conn.commit()
    return cursor.lastrowid


def get_issues(status: str = None, limit: int = 50, offset: int = 0) -> dict:
    """Get paginated reported issues list."""
    conn = _get_conn()
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM reported_issues {where}", params).fetchone()[0]

    rows = conn.execute(
        f"SELECT * FROM reported_issues {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    return {
        "total": total,
        "issues": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
    }


def get_issue(issue_id: int) -> dict | None:
    """Get a single reported issue by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM reported_issues WHERE id = ?", (issue_id,)).fetchone()
    return dict(row) if row else None


def update_issue(issue_id: int, status: str = None, admin_notes: str = None):
    """Update a reported issue's status and/or admin notes."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if admin_notes is not None:
        updates.append("admin_notes = ?")
        params.append(admin_notes)

    if not updates:
        return

    updates.append("updated_at = ?")
    params.append(now)
    params.append(issue_id)

    conn.execute(
        f"UPDATE reported_issues SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()


def delete_issue(issue_id: int):
    """Delete a reported issue by ID."""
    conn = _get_conn()
    conn.execute("DELETE FROM reported_issues WHERE id = ?", (issue_id,))
    conn.commit()


def export_leads_csv() -> str:
    """Export all leads as CSV string (kept for backward compatibility)."""
    return "".join(export_leads_csv_stream())


def export_leads_csv_stream():
    """Export all leads as a streaming CSV generator, yielding 100-row batches."""
    conn = _get_conn()
    fields = ["id", "session_id", "name", "email", "phone", "company",
              "source_page", "lead_score", "status", "notes", "created_at", "updated_at"]

    # Yield header
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(fields)
    yield buf.getvalue()

    # Stream rows in batches
    cursor = conn.execute(
        f"SELECT {', '.join(fields)} FROM leads ORDER BY created_at DESC"
    )

    batch = []
    for row in cursor:
        batch.append([str(row[f] or "") for f in fields])
        if len(batch) >= 100:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerows(batch)
            yield buf.getvalue()
            batch = []

    # Flush remaining
    if batch:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerows(batch)
        yield buf.getvalue()


# ── Golden Q&A operations ──

def create_golden_qa(question: str, answer: str, category: str = "") -> int:
    """Create a golden Q&A pair. Returns the ID."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO golden_qa (question, answer, category) VALUES (?, ?, ?)",
        (question, answer, category)
    )
    conn.commit()
    return cursor.lastrowid


def update_golden_qa(qa_id: int, question: str = None, answer: str = None,
                     category: str = None, is_active: int = None):
    """Update a golden Q&A pair. Only provided fields are updated."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    updates = []
    params = []

    if question is not None:
        updates.append("question = ?")
        params.append(question)
    if answer is not None:
        updates.append("answer = ?")
        params.append(answer)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)

    if not updates:
        return

    updates.append("updated_at = ?")
    params.append(now)
    params.append(qa_id)

    conn.execute(
        f"UPDATE golden_qa SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()


def delete_golden_qa(qa_id: int):
    """Hard delete a golden Q&A pair."""
    conn = _get_conn()
    conn.execute("DELETE FROM golden_qa WHERE id = ?", (qa_id,))
    conn.commit()


def get_golden_qa(qa_id: int) -> dict | None:
    """Get a single golden Q&A pair by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM golden_qa WHERE id = ?", (qa_id,)).fetchone()
    return dict(row) if row else None


def get_golden_qa_list(category: str = None, include_inactive: bool = False) -> list[dict]:
    """Get active golden Q&A pairs, optionally filtered by category."""
    conn = _get_conn()
    conditions = []
    params = []

    if not include_inactive:
        conditions.append("is_active = 1")
    if category:
        conditions.append("category = ?")
        params.append(category)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM golden_qa {where} ORDER BY created_at DESC", params
    ).fetchall()
    return [dict(row) for row in rows]


def get_all_golden_qa() -> list[dict]:
    """Get all golden Q&A pairs including inactive (for admin listing)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM golden_qa ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


# ── WhatsApp operations ──

def save_whatsapp_message(session_id: str, phone: str, role: str, content: str):
    """Insert a WhatsApp message row."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO whatsapp_messages (session_id, phone, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, phone, role, content, now)
    )
    conn.commit()


def get_whatsapp_conversations(limit: int = 20, offset: int = 0, search: str = "") -> dict:
    """List unique WhatsApp sessions with last message, timestamp, and message count."""
    conn = _get_conn()

    search_clause = ""
    params = []
    if search:
        search_clause = "WHERE phone LIKE ?"
        params.append(f"%{search}%")

    total = conn.execute(
        f"SELECT COUNT(DISTINCT session_id) FROM whatsapp_messages {search_clause}", params
    ).fetchone()[0]

    rows = conn.execute(f"""
        SELECT
            session_id,
            phone,
            COUNT(*) as message_count,
            MAX(content) as last_message,
            MAX(timestamp) as last_active
        FROM (
            SELECT wm.*,
                   ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY id DESC) as rn
            FROM whatsapp_messages wm
            {search_clause}
        )
        GROUP BY session_id
        ORDER BY last_active DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()

    # Fix: get actual last message per session
    conversations = []
    for row in rows:
        last_msg = conn.execute(
            "SELECT content FROM whatsapp_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (row["session_id"],)
        ).fetchone()
        conversations.append({
            "session_id": row["session_id"],
            "phone": row["phone"],
            "message_count": row["message_count"],
            "last_message": last_msg["content"] if last_msg else "",
            "last_active": row["last_active"],
        })

    return {"total": total, "conversations": conversations, "limit": limit, "offset": offset}


def get_whatsapp_history(session_id: str) -> list[dict]:
    """Get all messages for a WhatsApp session."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM whatsapp_messages WHERE session_id = ? ORDER BY id",
        (session_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_whatsapp_phone(session_id: str) -> str:
    """Get the phone number for a session."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT phone FROM whatsapp_messages WHERE session_id = ? LIMIT 1",
        (session_id,)
    ).fetchone()
    return row["phone"] if row else session_id.replace("wa_", "")


def get_whatsapp_stats() -> dict:
    """Aggregate stats for WhatsApp analytics."""
    conn = _get_conn()
    today = datetime.now().strftime("%Y-%m-%d")

    total_conversations = conn.execute(
        "SELECT COUNT(DISTINCT session_id) FROM whatsapp_messages"
    ).fetchone()[0]

    total_messages = conn.execute(
        "SELECT COUNT(*) FROM whatsapp_messages"
    ).fetchone()[0]

    messages_today = conn.execute(
        "SELECT COUNT(*) FROM whatsapp_messages WHERE timestamp >= ?", (today,)
    ).fetchone()[0]

    avg_len_row = conn.execute(
        "SELECT AVG(LENGTH(content)) FROM whatsapp_messages WHERE role = 'assistant'"
    ).fetchone()
    avg_response_length = round(avg_len_row[0] or 0)

    # Recent conversations for the table
    recent = conn.execute("""
        SELECT session_id, phone,
               COUNT(*) as message_count,
               MAX(timestamp) as last_active
        FROM whatsapp_messages
        GROUP BY session_id
        ORDER BY last_active DESC
        LIMIT 10
    """).fetchall()

    recent_conversations = []
    for row in recent:
        last_msg = conn.execute(
            "SELECT content FROM whatsapp_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (row["session_id"],)
        ).fetchone()
        recent_conversations.append({
            "session_id": row["session_id"],
            "phone": row["phone"],
            "message_count": row["message_count"],
            "last_message": last_msg["content"] if last_msg else "",
            "last_active": row["last_active"],
        })

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "messages_today": messages_today,
        "avg_response_length": avg_response_length,
        "recent_conversations": recent_conversations,
    }


# ── Ingested files operations ──

def save_ingested_file(filename: str, file_type: str, file_size: int,
                       total_chunks: int, total_pages: int, total_rows: int,
                       tables: list, chunk_ids: list, storage_path: str) -> int:
    """Record a successfully ingested file. Returns the file ID."""
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO ingested_files
           (filename, file_type, file_size, total_chunks, total_pages,
            total_rows, tables_json, chunk_ids_json, storage_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (filename, file_type, file_size, total_chunks, total_pages,
         total_rows, json.dumps(tables), json.dumps(chunk_ids),
         storage_path),
    )
    conn.commit()
    return cur.lastrowid


def get_ingested_files(status: str = "active") -> list[dict]:
    """Return all ingested files with the given status."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM ingested_files WHERE status = ? ORDER BY uploaded_at DESC",
        (status,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["tables"] = json.loads(d.pop("tables_json", "[]"))
        d["chunk_ids"] = json.loads(d.pop("chunk_ids_json", "[]"))
        result.append(d)
    return result


def get_ingested_file(file_id: int) -> dict | None:
    """Return a single ingested file by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM ingested_files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["tables"] = json.loads(d.pop("tables_json", "[]"))
    d["chunk_ids"] = json.loads(d.pop("chunk_ids_json", "[]"))
    return d


def delete_ingested_file(file_id: int) -> bool:
    """Soft-delete an ingested file. Returns True if found."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE ingested_files SET status = 'deleted', deleted_at = ? WHERE id = ? AND status = 'active'",
        (now, file_id),
    )
    conn.commit()
    return cur.rowcount > 0
