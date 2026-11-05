"""Session-based conversation history storage.

Uses Redis if available, falls back to in-memory OrderedDict.
Redis init is lazy — happens on first session operation, not at import time.
"""

from __future__ import annotations

import copy
import json
import time
from collections import OrderedDict

from backend.config import settings

_redis_client = None
_use_redis = False
_redis_checked = False
_memory_store: OrderedDict[str, dict] = OrderedDict()  # LRU: {session_id: {"history": [...], "ts": float}}
_feedback_store: OrderedDict[str, dict] = OrderedDict()  # {session_id: {"votes": {msg_index: "up"/"down"}, "ts": float}}


def _ensure_redis():
    """Lazy Redis init — called on first session operation instead of at import time."""
    global _redis_client, _use_redis, _redis_checked
    if _redis_checked:
        return
    _redis_checked = True
    try:
        import redis
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=1,
        )
        client.ping()
        _redis_client = client
        _use_redis = True
        print("[Session] Redis connected")
    except Exception:
        _use_redis = False
        print("[Session] Redis unavailable -- using in-memory storage")


def get_history(session_id: str) -> list[dict]:
    """Get conversation history for a session."""
    _ensure_redis()
    if _use_redis and _redis_client:
        try:
            data = _redis_client.get(f"session:{session_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"[Session] Redis get_history error: {e}")
        return []

    # In-memory fallback — return a copy so callers can't mutate the store
    entry = _memory_store.get(session_id)
    if entry:
        # Move to end (most recently used)
        _memory_store.move_to_end(session_id)
        return copy.deepcopy(entry["history"])
    return []


def save_history(session_id: str, history: list[dict]):
    """Save conversation history for a session."""
    _ensure_redis()
    # Cap at 20 messages
    history = history[-20:]

    if _use_redis and _redis_client:
        try:
            _redis_client.setex(
                f"session:{session_id}",
                settings.session_ttl,
                json.dumps(history),
            )
            return
        except Exception as e:
            print(f"[Session] Redis save_history error: {e}")

    # In-memory fallback with OrderedDict LRU
    _memory_store[session_id] = {"history": history, "ts": time.time()}
    _memory_store.move_to_end(session_id)

    # Evict oldest sessions (O(1) per eviction)
    while len(_memory_store) > 100:
        _memory_store.popitem(last=False)


def append_messages(session_id: str, user_msg: str, assistant_msg: str):
    """Append a user+assistant message pair to the session history."""
    history = get_history(session_id)
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": assistant_msg})
    save_history(session_id, history)


# --- Feedback storage ---

def save_feedback(session_id: str, message_index: int, feedback: str):
    """Store 'up' or 'down' feedback for a specific bot message in a session."""
    _ensure_redis()
    if _use_redis and _redis_client:
        try:
            key = f"feedback:{session_id}"
            data = _redis_client.get(key)
            votes = json.loads(data) if data else {}
            votes[str(message_index)] = feedback
            _redis_client.setex(key, settings.session_ttl, json.dumps(votes))
            return
        except Exception as e:
            print(f"[Session] Redis save_feedback error: {e}")

    # In-memory fallback with OrderedDict LRU
    if session_id not in _feedback_store:
        _feedback_store[session_id] = {"votes": {}, "ts": time.time()}
    _feedback_store[session_id]["votes"][str(message_index)] = feedback
    _feedback_store[session_id]["ts"] = time.time()
    _feedback_store.move_to_end(session_id)

    # Evict oldest feedback sessions (O(1) per eviction)
    while len(_feedback_store) > 100:
        _feedback_store.popitem(last=False)


def get_feedback_summary(session_id: str) -> dict:
    """Return {"ups": N, "downs": N, "recent_down": bool} for a session."""
    _ensure_redis()
    votes = {}

    if _use_redis and _redis_client:
        try:
            data = _redis_client.get(f"feedback:{session_id}")
            if data:
                votes = json.loads(data)
        except Exception as e:
            print(f"[Session] Redis get_feedback_summary error: {e}")
    else:
        entry = _feedback_store.get(session_id)
        if entry:
            votes = entry["votes"]

    ups = sum(1 for v in votes.values() if v == "up")
    downs = sum(1 for v in votes.values() if v == "down")

    # "recent_down" = the highest-indexed vote is a thumbs down
    recent_down = False
    if votes:
        last_index = max(int(k) for k in votes)
        recent_down = votes[str(last_index)] == "down"

    return {"ups": ups, "downs": downs, "recent_down": recent_down}


def get_feedback(session_id: str, message_index: int) -> str | None:
    """Return feedback ('up'/'down') for a specific message, or None."""
    _ensure_redis()
    if _use_redis and _redis_client:
        try:
            data = _redis_client.get(f"feedback:{session_id}")
            if data:
                votes = json.loads(data)
                return votes.get(str(message_index))
        except Exception as e:
            print(f"[Session] Redis get_feedback error: {e}")
        return None

    entry = _feedback_store.get(session_id)
    if entry:
        return entry["votes"].get(str(message_index))
    return None
