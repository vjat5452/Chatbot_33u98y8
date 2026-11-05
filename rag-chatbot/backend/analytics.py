"""Analytics event tracking and aggregation for the sales bot layer."""

from backend import database as db


def track_chat_opened(session_id: str, page_url: str = ""):
    """Track when a user opens the chat widget."""
    db.track_event(session_id, "chat_opened", {"page_url": page_url}, page_url)


def track_message_sent(session_id: str, topic: str = "general", page_url: str = ""):
    """Track a user message with topic classification."""
    db.track_event(session_id, "message_sent", {"topic": topic}, page_url)


def track_suggestion_clicked(session_id: str, suggestion: str = "", page_url: str = ""):
    """Track when a user clicks a follow-up suggestion."""
    db.track_event(session_id, "suggestion_clicked", {"suggestion": suggestion}, page_url)


def track_lead_captured(session_id: str, contact_type: str = "", page_url: str = ""):
    """Track when contact info is detected from a message."""
    db.track_event(session_id, "lead_captured", {"contact_type": contact_type}, page_url)


def track_feedback_given(session_id: str, feedback: str = "", page_url: str = ""):
    """Track thumbs up/down feedback."""
    db.track_event(session_id, "feedback_given", {"feedback": feedback}, page_url)


def track_file_uploaded(session_id: str, filename: str = "", page_url: str = ""):
    """Track file upload event."""
    db.track_event(session_id, "file_uploaded", {"filename": filename}, page_url)


def track_page_visited(session_id: str, page_url: str = ""):
    """Track which page the user is on."""
    db.track_event(session_id, "page_visited", {"page_url": page_url}, page_url)


# ── Aggregation functions (delegates to database) ──

def messages_per_day(days: int = 30) -> list[dict]:
    """Messages per day for the last N days."""
    summary = db.get_analytics_summary(days)
    return summary["messages_per_day"]


def popular_topics(days: int = 30) -> list[dict]:
    """Most discussed topics in the last N days."""
    summary = db.get_analytics_summary(days)
    return summary["popular_topics"]


def lead_funnel() -> dict:
    """Lead status distribution."""
    summary = db.get_analytics_summary(days=9999)
    return summary["lead_funnel"]


def peak_hours(days: int = 30) -> list[dict]:
    """Busiest hours of the day."""
    summary = db.get_analytics_summary(days)
    return summary["peak_hours"]


def busiest_pages(days: int = 30) -> list[dict]:
    """Pages generating most conversations."""
    summary = db.get_analytics_summary(days)
    return summary["busiest_pages"]
