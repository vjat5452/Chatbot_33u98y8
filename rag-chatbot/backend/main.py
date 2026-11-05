"""FastAPI app: /chat, /ingest, /scrape, /health endpoints + admin API + serves mirror website with chatbot widget."""

import asyncio
import hashlib
import mimetypes
import re
import secrets
import shutil
import subprocess
import time
from functools import lru_cache
from pathlib import Path

from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, PlainTextResponse, StreamingResponse

from backend.config import settings
from backend.models import (
    ChatRequest, ChatResponse, IngestResponse, FileResult,
    HealthResponse, SourceChunk, ScrapeResponse, FeedbackRequest,
    LeadResponse, LeadDetailResponse, LeadListResponse, LeadUpdateRequest,
    DashboardStats, AnalyticsData, ConversationListResponse, AdminSettings,
    TrackEventRequest,
    ReportIssueRequest, IssueResponse, IssueListResponse, IssueUpdateRequest,
    GoldenQACreate, GoldenQAUpdate, GoldenQAResponse, GoldenQAListResponse,
    EmailContactCreate, EmailContactUpdate, EmailContactResponse, EmailContactListResponse,
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse, EmailTemplateListResponse,
    TemplatePreviewRequest,
    EmailCampaignCreate, EmailCampaignUpdate, EmailCampaignResponse, EmailCampaignListResponse,
    CampaignScheduleRequest, CampaignTestRequest, EmailSendListResponse,
    EmailSequenceCreate, EmailSequenceStepCreate, EmailSequenceResponse, EmailSequenceListResponse,
    SequenceEnrollRequest,
    EmailAnalyticsOverview, WarmVsColdComparison, ContactValidationResult,
    DirectEmailRequest,
)
from backend.sql_parser import parse_sql
from backend.pdf_parser import parse_pdf
from backend.chunker import Chunk, create_chunks, create_pdf_chunks
from backend.website_knowledge import WEBSITE_CHUNKS
from backend import embeddings, vector_store, rag_pipeline, session_store, database as db
from backend import lead_capture, analytics, notifications
from backend.email_service import templates as et_mod, contacts as ec_mod
from backend.email_service import campaigns as ecamp_mod, tracking as etrack_mod
from backend.email_service import sequences as eseq_mod, analytics_db as ea_mod
from backend.email_service import scheduler as email_scheduler

app = FastAPI(title="Sparrowi - Sparrow Interactive Assistant")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
MIRROR_DIR = Path(__file__).resolve().parent.parent.parent / "Chatbot"
ADMIN_DIR = Path(__file__).resolve().parent.parent / "admin-dashboard" / "dist"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"

# ── Admin Auth Session Management ──
_auth_sessions: dict[str, dict] = {}  # token -> {"username": str, "created_at": float, "last_active": float}
_auth_sessions_lock = asyncio.Lock()
_AUTH_SESSION_TTL = 1800  # 30 minutes inactivity timeout
_security = HTTPBearer(auto_error=False)


async def _cleanup_expired_sessions():
    """Remove expired sessions."""
    now = time.time()
    async with _auth_sessions_lock:
        expired = [t for t, s in _auth_sessions.items() if now - s["last_active"] > _AUTH_SESSION_TTL]
        for t in expired:
            del _auth_sessions[t]


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """FastAPI dependency — validates admin session token on every admin request."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = credentials.credentials
    async with _auth_sessions_lock:
        session = _auth_sessions.get(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        if time.time() - session["last_active"] > _AUTH_SESSION_TTL:
            del _auth_sessions[token]
            raise HTTPException(status_code=401, detail="Session expired")
        session["last_active"] = time.time()
        return session


# Auth-exempt admin paths (login doesn't need auth, whatsapp webhook is server-to-server)
_AUTH_EXEMPT_PATHS = {"/api/admin/login", "/api/admin/whatsapp/messages"}


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    """Protect all /api/admin/* endpoints with session auth (except login)."""
    path = request.url.path
    if path.startswith("/api/admin") and path not in _AUTH_EXEMPT_PATHS:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        token = auth_header[7:]
        async with _auth_sessions_lock:
            session = _auth_sessions.get(token)
            if not session:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired session"})
            if time.time() - session["last_active"] > _AUTH_SESSION_TTL:
                del _auth_sessions[token]
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={"detail": "Session expired"})
            session["last_active"] = time.time()
    return await call_next(request)


# Lazy-load chatbot widget HTML snippet (injected before </body> in mirror pages)
_widget_path = FRONTEND_DIR / "chatbot-widget.html"


@lru_cache(maxsize=1)
def _get_widget_html() -> str:
    """Lazy-load and cache widget HTML on first use instead of at import time."""
    return _widget_path.read_text(encoding="utf-8") if _widget_path.exists() else ""


# Background ingestion tracking
_startup_complete = asyncio.Event()

# Lead nudge cache — avoids recomputing build_session_data() on every request
# Maps session_id -> (lead_nudge_value, timestamp)
_lead_nudge_cache: dict[str, tuple[str | None, float]] = {}
_lead_nudge_lock = asyncio.Lock()
_LEAD_NUDGE_CACHE_TTL = 30  # seconds
_LEAD_NUDGE_CACHE_MAX = 500  # max entries before cleanup

# Persistent counter for name-ask tracking per session
# Maps session_id -> count of name-asks sent
_name_ask_counter: dict[str, int] = {}
_NAME_ASK_COUNTER_MAX = 1000  # max entries before cleanup
_last_counter_cleanup = 0.0  # timestamp of last cleanup
_COUNTER_CLEANUP_INTERVAL = 3600  # cleanup once per hour


def _cleanup_caches():
    """Evict stale entries from in-memory caches to prevent unbounded growth."""
    global _last_counter_cleanup
    now = time.time()
    if now - _last_counter_cleanup < _COUNTER_CLEANUP_INTERVAL:
        return
    _last_counter_cleanup = now

    # Evict stale lead nudge cache entries
    if len(_lead_nudge_cache) > _LEAD_NUDGE_CACHE_MAX:
        stale = [k for k, (_, ts) in _lead_nudge_cache.items() if now - ts > _LEAD_NUDGE_CACHE_TTL]
        for k in stale:
            del _lead_nudge_cache[k]

    # Evict oldest name-ask counter entries if too many
    if len(_name_ask_counter) > _NAME_ASK_COUNTER_MAX:
        # Keep the most recent half — we can't know which are "active" without timestamps,
        # so just trim by count (sessions that got name-asks tend to be older).
        excess = len(_name_ask_counter) - _NAME_ASK_COUNTER_MAX // 2
        for k in list(_name_ask_counter.keys())[:excess]:
            del _name_ask_counter[k]


@app.on_event("startup")
async def startup():
    """Ensure Qdrant collection exists, init SQLite, and kick off background ingestion."""
    db.init_db()
    vector_store.ensure_collection()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    email_scheduler.start_scheduler()
    # Move expensive ingestion to background so the server is ready in <1s
    asyncio.create_task(_background_ingest())
    # Auto-start WhatsApp bridge in background
    asyncio.create_task(asyncio.to_thread(_start_bridge))


@app.on_event("shutdown")
async def shutdown():
    email_scheduler.stop_scheduler()
    _stop_bridge()


async def _background_ingest():
    """Run ingestion tasks in background threads to avoid blocking the event loop.

    Website and mirror content are only ingested on first run (when Qdrant is
    empty). On subsequent restarts, Qdrant's on-disk storage already has the
    data — re-ingesting would overwrite any manual cleanup (e.g. deleted junk
    chunks). Golden QA and uploaded files are always synced since they can be
    edited via the admin dashboard.
    """
    try:
        # Preload ML models so first query isn't slow
        await asyncio.to_thread(_warmup_models)
        # Only ingest website/mirror data if Qdrant collection is empty (first run)
        existing_points = vector_store.get_points_count()
        if existing_points == 0:
            print("[Startup] Empty collection detected — running first-time ingestion")
            await asyncio.to_thread(_ingest_website_knowledge)
            await asyncio.to_thread(_ingest_mirror_knowledge)
        else:
            print(f"[Startup] Qdrant already has {existing_points} vectors — skipping website/mirror re-ingestion")
        # Golden QA and uploaded files are always synced (editable via admin)
        await asyncio.to_thread(_sync_golden_qa_to_qdrant)
        await asyncio.to_thread(_restore_uploaded_files)
        # Warm keyword cache so first query doesn't pay the scroll cost
        await asyncio.to_thread(vector_store.warm_keyword_cache)
    finally:
        _startup_complete.set()
        print("[Startup] Background ingestion complete — server fully ready")


def _warmup_models():
    """Preload embedding and reranker models so first query is fast."""
    try:
        from backend.embeddings import embed_text
        from backend.reranker import _get_model as get_reranker
        print("[Startup] Warming up embedding model...")
        embed_text("warmup")  # triggers model load + caches result
        print("[Startup] Warming up reranker model...")
        get_reranker()  # triggers model load
        print("[Startup] Models ready")
    except Exception as e:
        print(f"[Startup] Model warmup failed: {e}")


def _ingest_website_knowledge():
    """Auto-ingest sparrowi.com website content into Qdrant on startup."""
    try:
        _embed_and_store(WEBSITE_CHUNKS)
        print(f"[Startup] Ingested {len(WEBSITE_CHUNKS)} website knowledge chunks")
    except Exception as e:
        print(f"[Startup] WARNING: Failed to ingest website knowledge: {e}")


def _ingest_mirror_knowledge():
    """Auto-ingest local mirror HTML content into Qdrant on startup."""
    from backend.web_scraper import crawl_mirror

    try:
        chunks = crawl_mirror(MIRROR_DIR)
        if chunks:
            _embed_and_store(chunks)
            print(f"[Startup] Ingested {len(chunks)} mirror chunks")
        else:
            print("[Startup] No mirror chunks found")
    except Exception as e:
        print(f"[Startup] WARNING: Failed to ingest mirror content: {e}")


def _sync_golden_qa_to_qdrant() -> int:
    """Sync active golden Q&A pairs from SQLite into Qdrant."""
    try:
        vector_store.delete_by_table("golden_qa")
        pairs = db.get_golden_qa_list()
        if not pairs:
            print("[Golden QA] No active Q&A pairs to sync")
            return 0
        chunks = []
        for pair in pairs:
            chunk_id = f"golden_qa_{pair['id']}"
            text = f"Q: {pair['question']}\nA: {pair['answer']}"
            chunks.append(Chunk(
                id=hashlib.sha256(chunk_id.encode()).hexdigest()[:16],
                text=text,
                table="golden_qa",
                chunk_type="golden_qa",
            ))
        _embed_and_store(chunks)
        print(f"[Golden QA] Synced {len(chunks)} Q&A pairs to Qdrant")
        return len(chunks)
    except Exception as e:
        print(f"[Golden QA] WARNING: Failed to sync: {e}")
        return 0


def _restore_uploaded_files():
    """Re-ingest tracked uploaded files if their chunks are missing from Qdrant."""
    try:
        files = db.get_ingested_files(status="active")
        if not files:
            print("[Startup] No tracked uploaded files to restore")
            return
        restored = 0
        for f in files:
            chunk_ids = f.get("chunk_ids", [])
            if chunk_ids and vector_store.points_exist(chunk_ids):
                continue  # chunks still in Qdrant
            # Re-ingest from saved file
            storage_path = f.get("storage_path", "")
            if not storage_path or not Path(storage_path).exists():
                print(f"[Startup] WARNING: Saved file missing for '{f['filename']}' — cannot restore")
                continue
            content = Path(storage_path).read_bytes()
            ext = f["file_type"]
            try:
                if ext == "pdf":
                    _ingest_pdf(content, f["filename"])
                elif ext == "sql":
                    _ingest_sql(content, f["filename"])
                restored += 1
                print(f"[Startup] Restored '{f['filename']}' ({f['total_chunks']} chunks)")
            except Exception as e:
                print(f"[Startup] WARNING: Failed to restore '{f['filename']}': {e}")
        if restored:
            print(f"[Startup] Restored {restored} uploaded file(s)")
        else:
            print(f"[Startup] All {len(files)} uploaded file(s) already in Qdrant")
    except Exception as e:
        print(f"[Startup] WARNING: Failed to restore uploaded files: {e}")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    qdrant_ok = vector_store.is_healthy()
    return HealthResponse(
        status="ok" if qdrant_ok else "degraded",
        qdrant=qdrant_ok,
        embedding_model=settings.embedding_model,
        claude_model=settings.sarvam_model,
        ingestion_ready=_startup_complete.is_set(),
    )


@app.get("/api/initial-suggestions")
async def initial_suggestions():
    """Return randomized initial suggestions for a new chat session."""
    import random as _rnd
    from backend.rag_pipeline import _SUGGESTION_TEMPLATES

    # Build a combined pool from all intent categories
    all_suggestions = []
    for pool in _SUGGESTION_TEMPLATES.values():
        all_suggestions.extend(pool)

    # Pick 4 random unique suggestions (matching the current UI layout)
    picked = _rnd.sample(all_suggestions, min(4, len(all_suggestions)))
    return {"suggestions": picked}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: List[UploadFile] = File(...)):
    """Upload and ingest one or more .sql / .pdf files."""
    results = []
    grand_total_chunks = 0

    for file in files:
        filename = file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in ("sql", "pdf"):
            results.append(FileResult(
                filename=filename, file_type=ext, tables=[], total_chunks=0,
                total_rows=0, error=f"Unsupported file type: .{ext}",
            ))
            continue

        content = await file.read()

        if not content or len(content.strip()) == 0:
            results.append(FileResult(
                filename=filename, file_type=ext, tables=[], total_chunks=0,
                total_rows=0, error="File is empty",
            ))
            continue

        try:
            if ext == "sql":
                result = _ingest_sql(content, filename)
            else:
                result = _ingest_pdf(content, filename)
            grand_total_chunks += result.total_chunks
            results.append(result)
        except Exception as e:
            results.append(FileResult(
                filename=filename, file_type=ext, tables=[], total_chunks=0,
                total_rows=0, error=str(e),
            ))

    if not results:
        raise HTTPException(status_code=400, detail="No files provided")

    return IngestResponse(
        files=results,
        total_files=len(results),
        total_chunks=grand_total_chunks,
    )


def _ingest_sql(content: bytes, filename: str) -> FileResult:
    """Parse and ingest a SQL dump file."""
    sql_text = content.decode("utf-8", errors="replace")

    parsed_tables = parse_sql(sql_text)
    if not parsed_tables:
        raise ValueError("No tables found in SQL file")

    chunks = create_chunks(parsed_tables)
    if not chunks:
        raise ValueError("No chunks generated from SQL file")

    _embed_and_store(chunks)

    total_rows = sum(len(t.rows) for t in parsed_tables)
    table_names = [t.schema.name for t in parsed_tables]

    return FileResult(
        filename=filename,
        file_type="sql",
        tables=table_names,
        total_chunks=len(chunks),
        total_rows=total_rows,
    )


def _ingest_pdf(content: bytes, filename: str, *, track: bool = False) -> FileResult:
    """Parse and ingest a PDF file. If track=True, save file to disk and record in DB."""
    parsed_pdf = parse_pdf(content, filename)

    if not parsed_pdf.pages:
        raise ValueError("No text content found in PDF")

    chunks = create_pdf_chunks(parsed_pdf)
    if not chunks:
        raise ValueError("No chunks generated from PDF")

    chunk_ids = _embed_and_store(chunks)

    # Persist file and track in database
    if track:
        import uuid
        storage_name = f"{uuid.uuid4().hex[:12]}_{filename}"
        storage_path = UPLOADS_DIR / storage_name
        storage_path.write_bytes(content)
        db.save_ingested_file(
            filename=filename, file_type="pdf", file_size=len(content),
            total_chunks=len(chunks), total_pages=parsed_pdf.total_pages,
            total_rows=0, tables=[filename], chunk_ids=chunk_ids,
            storage_path=str(storage_path),
        )

    return FileResult(
        filename=filename,
        file_type="pdf",
        tables=[filename],
        total_chunks=len(chunks),
        total_rows=0,
        total_pages=parsed_pdf.total_pages,
    )


def _is_junk_chunk(chunk) -> bool:
    """Quality gate — reject chunks that would pollute the vector database.

    Catches: empty/short content, navigation-only pages, WordPress theme
    templates, repetitive content, image-only stubs, and test data.
    Runs on EVERY ingestion path so junk can never enter Qdrant.
    """
    text = chunk.text.strip()
    # Strip the header line "[sparrowi.com — URL]" before measuring content
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    content_lines = [l for l in lines if not l.startswith("[sparrowi.com")]

    # 1. Too little real content
    content_text = " ".join(content_lines)
    if len(content_text) < 50:
        return True

    lower = content_text.lower()

    # 2. Repetitive content (same phrase > 3 times = filler)
    words = lower.split()
    if len(words) > 5:
        from collections import Counter
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        most_common_count = Counter(bigrams).most_common(1)[0][1]
        if most_common_count >= 4 and most_common_count / len(bigrams) > 0.25:
            return True

    # 3. WordPress theme template / demo content (not actual company content)
    _THEME_JUNK = {"elementor", "wpbakery", "struktur", "theme flavor",
                   "flavflavor flavor", "flavor flavor"}
    if any(t in lower for t in _THEME_JUNK):
        return True

    # 4. Navigation-only: mostly short lines with no real sentences
    if len(content_lines) > 5:
        short_lines = sum(1 for l in content_lines if len(l) < 20)
        if short_lines / len(content_lines) > 0.75:
            return True

    # 5. Image-only / meta-only stubs: just boilerplate lines, no real body text
    _BOILERPLATE_PREFIXES = (
        "Page title:", "Featured image:", "Description:", "Image descriptions:",
        "Back to top", "Follow us", "Filter", "Show all", "Home /",
    )
    meaningful_lines = [l for l in content_lines
                        if not any(l.startswith(bp) for bp in _BOILERPLATE_PREFIXES)]
    meaningful_text = " ".join(meaningful_lines).strip()
    if len(meaningful_text) < 50:
        return True

    # 6. Third-party theme / plugin descriptions (not company content)
    _THIRD_PARTY = ("flameonepage", "flavor flavor", "flavflavor",
                    "flavor starter", "flavor starter", "flavor starter",
                    "flavflavor flavor", "flavor starter", "flavor starter")
    if any(t in lower for t in _THIRD_PARTY):
        return True

    # 7. Test/dummy data
    if chunk.table == "test":
        return True

    # 8. Lorem Ipsum / placeholder filler text
    _LOREM_SIGNALS = ("lorem ipsum", "dolor sit amet", "consectetur adipiscing",
                      "sed do eiusmod", "proin qual de suis", "luhis shoyt thoto",
                      "bibendum auct", "sollicituin")
    lorem_hits = sum(1 for s in _LOREM_SIGNALS if s in lower)
    if lorem_hits >= 2:
        return True

    return False


def _embed_and_store(chunks) -> list[int]:
    """Embed chunks and upsert to Qdrant. Returns list of chunk IDs.

    Applies a quality gate to filter out junk chunks before embedding.
    """
    # Quality gate: filter out junk before embedding
    clean_chunks = []
    rejected = 0
    for c in chunks:
        if _is_junk_chunk(c):
            rejected += 1
            print(f"[Ingest] Rejected junk chunk: table={c.table} url={getattr(c, 'url', '')[:80]}")
        else:
            clean_chunks.append(c)
    if rejected:
        print(f"[Ingest] Filtered out {rejected} junk chunks, keeping {len(clean_chunks)}")

    if not clean_chunks:
        return []

    texts = [c.text for c in clean_chunks]
    vectors = embeddings.embed_batch(texts)

    chunk_ids = [int(c.id, 16) % (2**63) for c in clean_chunks]
    payloads = [
        {"text": c.text, "table": c.table, "chunk_type": c.chunk_type, "url": c.url}
        for c in clean_chunks
    ]

    vector_store.upsert_chunks(chunk_ids, vectors, payloads)
    return chunk_ids


@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    """Record thumbs up/down feedback for a bot message."""
    if request.feedback not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Feedback must be 'up' or 'down'")
    session_store.save_feedback(request.session_id, request.message_index, request.feedback)
    # Also persist to SQLite
    db.save_feedback_record(request.session_id, request.message_index, request.feedback)
    analytics.track_feedback_given(request.session_id, request.feedback)
    return {"status": "ok"}


@app.get("/feedback/debug")
async def feedback_debug():
    """Debug endpoint: view all stored feedback sessions."""
    from backend.session_store import _feedback_store
    return {
        "total_sessions": len(_feedback_store),
        "sessions": {
            sid: {
                "votes": {str(k): v for k, v in entry["votes"].items()},
                "summary": session_store.get_feedback_summary(sid),
            }
            for sid, entry in _feedback_store.items()
        },
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = "unknown"):
    """Transcribe audio using Sarvam AI Speech-to-Text."""
    from sarvamai import SarvamAI

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    if not settings.sarvam_api_key:
        raise HTTPException(status_code=500, detail="SARVAM_API_KEY is not set")

    client = SarvamAI(api_subscription_key=settings.sarvam_api_key)

    # Determine filename and content type from the upload
    filename = file.filename or "recording.webm"
    # Strip codec params (e.g. "audio/webm;codecs=opus" -> "audio/webm")
    content_type = (file.content_type or "audio/webm").split(";")[0].strip()

    try:
        response = client.speech_to_text.transcribe(
            file=(filename, audio_bytes, content_type),
            model="saaras:v3",
            language_code=language,
        )
        return {
            "transcript": response.transcript,
            "language_code": response.language_code,
        }
    except Exception as e:
        print(f"[STT] Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


def _track_sales_sync(session_id: str, user_message: str, answer: str, page_url: str):
    """Synchronous sales tracking — runs in a background thread to avoid blocking chat responses."""
    try:
        # 1. Classify intent up front (used for saving + tracking)
        intent = lead_capture.classify_intent(user_message)

        # 2. Save messages to SQLite (persistent) — batch write, with intent
        db.save_messages_batch(session_id, [
            {"role": "user", "content": user_message, "page_url": page_url, "intent": intent},
            {"role": "assistant", "content": answer, "page_url": page_url},
        ])

        # 3. Extract contact info -> save lead if found
        contact = lead_capture.extract_contact_info(user_message)

        # 3b. Short-reply name detection: if regex didn't find a name, check if
        # the bot just asked "what should I call you?" and user replied with a name
        if not contact or "name" not in contact:
            # Get the previous bot message from conversation history.
            # We just saved the current pair (user_msg + answer) above,
            # so we need to find the assistant message BEFORE the current one.
            prev_messages = db.get_conversations(session_id)
            prev_bot_msg = ""
            # Skip the current bot response (last assistant msg) to find
            # the one before it (which may have asked for the name).
            found_current = False
            for m in reversed(prev_messages):
                if m["role"] == "assistant":
                    if not found_current:
                        found_current = True  # skip current response
                        continue
                    prev_bot_msg = m["content"]
                    break
            short_name = lead_capture.extract_name_from_short_reply(user_message, prev_bot_msg)
            if short_name:
                if contact is None:
                    contact = {}
                contact["name"] = short_name

        # 3c. Check bot's response for "Nice to meet you, X!" — this means
        # the fast-path already detected a name from the user's message.
        if not contact or "name" not in contact:
            from backend.rag_pipeline import _MEET_RE, _meet_re_name
            meet_match = _MEET_RE.search(answer)
            if meet_match:
                _candidate = _meet_re_name(meet_match)
                if _candidate and lead_capture._is_valid_name(_candidate):
                    if contact is None:
                        contact = {}
                    contact["name"] = _candidate

        # Always ensure a lead record exists for this session
        db.save_lead(
            session_id,
            name=contact.get("name", "") if contact else "",
            email=contact.get("email", "") if contact else "",
            phone=contact.get("phone", "") if contact else "",
            source_page=page_url,
        )
        if contact:
            contact_types = ", ".join(contact.keys())
            analytics.track_lead_captured(session_id, contact_types, page_url)

        # 4. Track intent (already classified above)
        analytics.track_message_sent(session_id, intent, page_url)

        # 5. Recalculate lead score (+ pre-compute lead nudge for next request)
        session_data = lead_capture.build_session_data(session_id)
        score = lead_capture.calculate_score(session_data)
        db.update_lead_score(session_id, score)

        # Invalidate stale nudge cache — the full multi-phase logic in the
        # chat handler will recompute on next request. Pre-computing here was
        # dangerous because it didn't know about _name_ask_counter or the
        # soft-retry / gate thresholds, and could poison the cache.
        _lead_nudge_cache.pop(session_id, None)

        # 6. If hot lead -> send email notification
        if score >= settings.lead_hot_threshold:
            lead = db._get_conn().execute(
                "SELECT * FROM leads WHERE session_id = ?", (session_id,)
            ).fetchone()
            if lead:
                messages = db.get_conversations(session_id)
                summary_lines = []
                for m in messages[-10:]:
                    role = "User" if m["role"] == "user" else "Bot"
                    summary_lines.append(f"{role}: {m['content'][:200]}")
                conv_summary = "\n".join(summary_lines)
                notifications.send_lead_alert(dict(lead), conv_summary)

    except Exception as e:
        # Never let tracking break the chat response
        import traceback
        print(f"[Sales] Tracking error: {e}\n{traceback.format_exc()}")


def _detect_name_in_conversation(current_message: str, history: list[dict]) -> str | None:
    """Check if a name has been provided anywhere in the conversation.

    Scans: (1) the current message, (2) all history messages.
    Returns the detected name or None.
    """
    # Check current message with extract_contact_info (handles "My name is X", "I'm X")
    contact = lead_capture.extract_contact_info(current_message)
    if contact and contact.get("name"):
        return contact["name"]

    # Check if current message is a short-reply name (after bot asked)
    if history:
        prev_bot = ""
        for m in reversed(history):
            if m["role"] == "assistant":
                prev_bot = m["content"]
                break
        short_name = lead_capture.extract_name_from_short_reply(current_message, prev_bot)
        if short_name:
            return short_name

    # Scan bot messages for "Nice to meet you, X!" or "X ji," (fast-path name response)
    from backend.rag_pipeline import _MEET_RE, _meet_re_name
    for m in history:
        if m["role"] == "assistant":
            meet_match = _MEET_RE.search(m["content"])
            if meet_match:
                _candidate = _meet_re_name(meet_match)
                if _candidate and lead_capture._is_valid_name(_candidate):
                    return _candidate

    # Scan history: check each user message for name patterns
    for i, m in enumerate(history):
        if m["role"] != "user":
            continue
        # Check via extract_contact_info
        contact = lead_capture.extract_contact_info(m["content"])
        if contact and contact.get("name"):
            print(f"[Sales] Name found in history[{i}] via contact extraction: {contact['name']}")
            return contact["name"]
        # Check via short-reply detection (look at preceding bot message)
        if i > 0 and history[i - 1]["role"] == "assistant":
            short_name = lead_capture.extract_name_from_short_reply(
                m["content"], history[i - 1]["content"]
            )
            if short_name:
                print(f"[Sales] Name found in history[{i}] via short-reply: {short_name}")
                return short_name

    return None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and get a RAG-augmented response."""
    if not request.message.strip():
        return ChatResponse(
            answer="It looks like your message was empty! Please type a question and I'll be happy to help with anything about Sparrow Interactive.",
            sources=[],
            needs_clarification=False,
            follow_up_question="",
            follow_up_message="",
            options=[],
            suggestions=["What services does Sparrow Interactive offer?", "Tell me about your VR/AR experiences.", "How can I get in touch with your team?"],
        )

    # Periodic cleanup of in-memory caches (runs at most once/hour)
    _cleanup_caches()

    session_id = request.session_id
    page_url = request.page_url

    if session_id:
        history = session_store.get_history(session_id)
    else:
        history = [{"role": m.role, "content": m.content} for m in request.history]

    feedback_summary = None
    if session_id:
        feedback_summary = session_store.get_feedback_summary(session_id)

    # Pre-compute lead nudge signal (with caching to avoid expensive DB queries)
    lead_nudge = None
    if session_id:
        try:
            # Skip computation entirely for first message (no history = msg_count < 2)
            if not history:
                lead_nudge = None
            else:
                # Check lead nudge cache — but skip cache for name-related nudges
                # since the strategy depends on live message count and history
                cached_nudge = _lead_nudge_cache.get(session_id)
                _use_cache = (
                    cached_nudge
                    and (time.time() - cached_nudge[1]) < _LEAD_NUDGE_CACHE_TTL
                    and cached_nudge[0] not in ("ask_name", "ask_name_soft", "gate_name", "name_known", None)
                )
                if _use_cache:
                    lead_nudge = cached_nudge[0]
                    # Invalidate stale "ask_phone" if current message contains phone/email
                    if lead_nudge == "ask_phone":
                        current_contact = lead_capture.extract_contact_info(request.message)
                        if current_contact and (current_contact.get("phone") or current_contact.get("email")):
                            lead_nudge = "name_known"
                            _lead_nudge_cache[session_id] = (lead_nudge, time.time())
                else:
                    session_data = lead_capture.build_session_data(session_id)
                    score = lead_capture.calculate_score(session_data)
                    # +1 because current user message isn't saved to DB yet
                    # (DB save happens in background thread after response)
                    msg_count = session_data["message_count"] + 1

                    # Check if name is already known (DB or conversation history)
                    name_known_from_db = session_data["has_name"]
                    name_in_current_msg = False
                    if not name_known_from_db:
                        # Check current message first
                        contact_check = lead_capture.extract_contact_info(request.message)
                        if contact_check and contact_check.get("name"):
                            name_in_current_msg = True
                        if not name_in_current_msg and history:
                            prev_bot = ""
                            for m in reversed(history):
                                if m["role"] == "assistant":
                                    prev_bot = m["content"]
                                    break
                            if lead_capture.extract_name_from_short_reply(request.message, prev_bot):
                                name_in_current_msg = True
                        # Also check history for previously given names
                        if not name_in_current_msg:
                            found_name = _detect_name_in_conversation(request.message, history)
                            if found_name:
                                name_known_from_db = True  # treat as DB-known

                    name_known = name_known_from_db or name_in_current_msg

                    # ── Smart lead capture strategy ──
                    # Phase 1: Soft ask (first 2 attempts, natural CTA at end of response)
                    # Phase 2: Back off after 2 rejections, let conversation flow
                    # Phase 3: After 5+ more user messages, try once more softly
                    # Phase 4: After 20 total user messages without name → gate response
                    # After name: ask phone → optionally ask email

                    # Use persistent counter for name-ask tracking
                    # (history-based counting is unreliable due to text mutations)
                    _name_ask_count = _name_ask_counter.get(session_id, 0)

                    # Count user messages since last name-ask using history
                    # Find the last assistant message that looks like a name-ask
                    # Uses the module-level _NAME_ASK_RE from rag_pipeline for consistency
                    from backend.rag_pipeline import _NAME_ASK_RE as _name_ask_pattern
                    _last_name_ask_idx = -1
                    if history:
                        for idx, m in enumerate(history):
                            if m["role"] == "assistant" and _name_ask_pattern.search(m["content"]):
                                _last_name_ask_idx = idx

                    _user_msgs_since_ask = 0
                    if _last_name_ask_idx >= 0 and history:
                        for m in history[_last_name_ask_idx + 1:]:
                            if m["role"] == "user":
                                _user_msgs_since_ask += 1

                    if name_known:
                        lead_nudge = "name_known"
                    elif msg_count >= 20:
                        # Phase 4: Gate — 20+ user messages, still no name
                        lead_nudge = "gate_name"
                    elif _name_ask_count < 2:
                        # Phase 1: Normal soft ask
                        if lead_capture.should_capture_lead(msg_count, score):
                            lead_nudge = "ask_name"
                            _name_ask_counter[session_id] = _name_ask_count + 1
                    elif _name_ask_count == 2 and _user_msgs_since_ask >= 5:
                        # Phase 3: Retry softly ONCE
                        lead_nudge = "ask_name_soft"
                        _name_ask_counter[session_id] = _name_ask_count + 1
                    # else: Phase 2 — backed off, waiting

                    # Phone/email nudge — only after name is captured
                    phone_in_history = False
                    if history and not session_data["has_phone"]:
                        for m in history:
                            if m["role"] == "user":
                                hist_contact = lead_capture.extract_contact_info(m["content"])
                                if hist_contact and (hist_contact.get("phone") or hist_contact.get("email")):
                                    phone_in_history = True
                                    break

                    if name_known:
                        has_phone = session_data["has_phone"] or phone_in_history
                        has_email = session_data["has_email"]
                        current_contact = lead_capture.extract_contact_info(request.message)
                        has_contact_now = bool(
                            current_contact and (current_contact.get("phone") or current_contact.get("email"))
                        )

                        if not has_phone and not has_contact_now:
                            # Ask for phone after name is known
                            lead_nudge = "ask_phone"
                        elif has_phone and not has_email and not has_contact_now:
                            # Soft ask for email after phone is known
                            # Only ask once — check if we already asked
                            _email_asked = any(
                                m["role"] == "assistant" and
                                re.search(r"email|e-mail", m["content"], re.IGNORECASE) and
                                re.search(r"share|provide|send|drop", m["content"], re.IGNORECASE)
                                for m in (history or [])
                            )
                            if not _email_asked:
                                lead_nudge = "ask_email"

                    # Cache the computed nudge
                    _lead_nudge_cache[session_id] = (lead_nudge, time.time())
        except Exception as e:
            print(f"[Sales] Lead nudge computation error: {e}")

    try:
        result = rag_pipeline.query(request.message, history, feedback_summary=feedback_summary, lead_nudge=lead_nudge)
    except Exception as e:
        print(f"[Chat] ERROR processing '{request.message[:50]}': {type(e).__name__}: {e}")
        # Return a polite message instead of a raw error
        result = {
            "answer": (
                "I sincerely apologize for the inconvenience! Something went wrong on our end. "
                "Please try again in a few moments. If the issue persists, feel free to reach out "
                "to our team through our [Contact Us](https://www.sparrowi.com/contact-us/) page."
            ),
            "sources": [],
            "needs_clarification": False,
            "follow_up_question": "",
            "options": [],
            "suggestions": [],
        }

    # Combine answer + follow-up for history/tracking (so context is preserved)
    full_answer = result["answer"]
    if result.get("follow_up_message"):
        full_answer += "\n\n" + result["follow_up_message"]

    # Session history stays synchronous (needed for next message context)
    if session_id:
        session_store.append_messages(session_id, request.message, full_answer)

    # Sales bot tracking — fire and forget in background thread
    if session_id:
        asyncio.create_task(asyncio.to_thread(
            _track_sales_sync, session_id, request.message, full_answer, page_url
        ))

    sources = [
        SourceChunk(
            text=s["text"],
            table=s["table"],
            chunk_type=s["chunk_type"],
            url=s.get("url", ""),
            score=round(s["score"], 3),
        )
        for s in result["sources"][:settings.max_sources_shown]
    ]

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        needs_clarification=result.get("needs_clarification", False),
        follow_up_question=result.get("follow_up_question", ""),
        follow_up_message=result.get("follow_up_message", ""),
        options=result.get("options", []),
        suggestions=result.get("suggestions", []),
    )


# -- Analytics tracking endpoint (for frontend events) --

@app.post("/track")
async def track_event(request: TrackEventRequest):
    """Track a frontend analytics event."""
    db.track_event(request.session_id, request.event_type, request.event_data, request.page_url)
    return {"status": "ok"}


@app.post("/report-issue")
async def report_issue(request: ReportIssueRequest):
    """Submit a reported issue from the chatbot widget."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Issue description cannot be empty")
    issue_id = db.save_issue(request.session_id, request.message.strip(), request.page_url)
    return {"status": "ok", "issue_id": issue_id}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape():
    """Crawl sparrowi.com and ingest all content into Qdrant."""
    from backend import web_scraper

    try:
        vector_store.delete_by_table("sparrowi.com")
        chunks = web_scraper.crawl()

        # Also include local mirror content so it isn't lost after delete
        mirror_chunks = web_scraper.crawl_mirror(MIRROR_DIR)
        chunks.extend(mirror_chunks)

        if not chunks:
            return ScrapeResponse(
                status="ok",
                pages_crawled=0,
                chunks_created=0,
                message="No content found on sparrowi.com",
            )

        _embed_and_store(chunks)
        _embed_and_store(WEBSITE_CHUNKS)

        pages = set()
        for c in chunks:
            first_line = c.text.split("\n", 1)[0]
            pages.add(first_line)

        return ScrapeResponse(
            status="ok",
            pages_crawled=len(pages),
            chunks_created=len(chunks),
            message=f"Successfully scraped {len(pages)} pages into {len(chunks)} chunks",
        )
    except Exception as e:
        return ScrapeResponse(
            status="error",
            pages_crawled=0,
            chunks_created=0,
            message=f"Scrape failed: {str(e)}",
        )


@app.post("/scrape-mirror", response_model=ScrapeResponse)
async def scrape_mirror():
    """Re-ingest the local mirror website into Qdrant."""
    from backend.web_scraper import crawl_mirror

    try:
        chunks = crawl_mirror(MIRROR_DIR)
        if not chunks:
            return ScrapeResponse(
                status="ok",
                pages_crawled=0,
                chunks_created=0,
                message="No content found in local mirror",
            )

        _embed_and_store(chunks)

        return ScrapeResponse(
            status="ok",
            pages_crawled=len(set(c.url for c in chunks)),
            chunks_created=len(chunks),
            message=f"Ingested {len(chunks)} chunks from local mirror",
        )
    except Exception as e:
        return ScrapeResponse(
            status="error",
            pages_crawled=0,
            chunks_created=0,
            message=f"Mirror scrape failed: {str(e)}",
        )


# -- Admin Auth endpoints (no auth required) --

@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Authenticate admin and return session token."""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    captcha_answer = body.get("captcha_answer")
    captcha_expected = body.get("captcha_expected")

    if captcha_answer is not None and captcha_expected is not None:
        try:
            if int(captcha_answer) != int(captcha_expected):
                raise HTTPException(status_code=400, detail="Incorrect security verification")
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid captcha answer")

    if username != settings.admin_username or password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    await _cleanup_expired_sessions()
    token = secrets.token_urlsafe(48)
    async with _auth_sessions_lock:
        _auth_sessions[token] = {
            "username": username,
            "created_at": time.time(),
            "last_active": time.time(),
        }
    return {"token": token, "username": username}


@app.post("/api/admin/logout")
async def admin_logout(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Invalidate admin session."""
    if credentials and credentials.credentials in _auth_sessions:
        del _auth_sessions[credentials.credentials]
    return {"status": "ok"}


@app.get("/api/admin/auth/check")
async def admin_auth_check(session=Depends(require_admin)):
    """Verify current session is still valid."""
    return {"authenticated": True, "username": session["username"]}


# -- Admin API endpoints (auth required) --

@app.get("/api/admin/dashboard", response_model=DashboardStats)
async def admin_dashboard():
    """Get dashboard overview stats with period-over-period trends."""
    stats = db.get_dashboard_stats_with_trends()
    return DashboardStats(**stats)


@app.get("/api/admin/leads", response_model=LeadListResponse)
async def admin_leads(
    status: str = Query(None),
    search: str = Query(None),
    min_score: int = Query(None),
    max_score: int = Query(None),
    created_after: str = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get paginated leads list with filters."""
    result = db.get_leads(
        status=status, search=search, min_score=min_score, max_score=max_score,
        created_after=created_after, sort=sort, order=order, limit=limit, offset=offset,
    )
    return LeadListResponse(
        total=result["total"],
        leads=[LeadResponse(**l) for l in result["leads"]],
        limit=result["limit"],
        offset=result["offset"],
    )


@app.get("/api/admin/leads/{lead_id}", response_model=LeadDetailResponse)
async def admin_lead_detail(lead_id: int):
    """Get a single lead with full conversation history."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadDetailResponse(**lead)


@app.patch("/api/admin/leads/{lead_id}")
async def admin_update_lead(lead_id: int, request: LeadUpdateRequest):
    """Update lead status and/or notes."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    status = request.status or lead["status"]
    notes = request.notes if request.notes else None
    db.update_lead_status(lead_id, status, notes)
    return {"status": "ok"}


@app.get("/api/admin/analytics", response_model=AnalyticsData)
async def admin_analytics(days: int = Query(30, ge=1, le=365)):
    """Get analytics data for charts."""
    data = db.get_analytics_summary(days)
    return AnalyticsData(**data)


@app.get("/api/admin/conversations", response_model=ConversationListResponse)
async def admin_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get recent conversations list."""
    result = db.get_recent_conversations(limit=limit, offset=offset)
    return ConversationListResponse(**result)


@app.get("/api/admin/conversations/{session_id}")
async def admin_conversation_detail(session_id: str):
    """Get full conversation for a session."""
    messages = db.get_conversations(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"session_id": session_id, "messages": messages}


@app.get("/api/admin/export/leads")
async def admin_export_leads():
    """Export all leads as streaming CSV."""
    return StreamingResponse(
        db.export_leads_csv_stream(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sparrowi-leads.csv"},
    )


@app.post("/api/admin/settings")
async def admin_save_settings(request: AdminSettings):
    """Save admin settings (updates in-memory, persists to .env on next restart)."""
    settings.email_provider = request.email_provider
    settings.smtp_host = request.smtp_host
    settings.smtp_port = request.smtp_port
    settings.smtp_user = request.smtp_user
    if request.smtp_password:
        settings.smtp_password = request.smtp_password
    settings.ms_tenant_id = request.ms_tenant_id
    settings.ms_client_id = request.ms_client_id
    if request.ms_client_secret:
        settings.ms_client_secret = request.ms_client_secret
    settings.ms_sender_email = request.ms_sender_email
    settings.alert_emails = request.alert_emails
    settings.lead_hot_threshold = request.lead_hot_threshold
    settings.lead_qualified_threshold = request.lead_qualified_threshold
    return {"status": "ok"}


@app.get("/api/admin/settings")
async def admin_get_settings():
    """Get current admin settings."""
    return {
        "email_provider": settings.email_provider,
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user,
        "smtp_password": "••••••••" if settings.smtp_password else "",
        "ms_tenant_id": settings.ms_tenant_id,
        "ms_client_id": settings.ms_client_id,
        "ms_client_secret": "••••••••" if settings.ms_client_secret else "",
        "ms_sender_email": settings.ms_sender_email,
        "alert_emails": settings.alert_emails,
        "lead_hot_threshold": settings.lead_hot_threshold,
        "lead_qualified_threshold": settings.lead_qualified_threshold,
    }


# -- Admin Issue endpoints --

@app.get("/api/admin/issues", response_model=IssueListResponse)
async def admin_issues(
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get paginated reported issues list."""
    result = db.get_issues(status=status, limit=limit, offset=offset)
    return IssueListResponse(
        total=result["total"],
        issues=[IssueResponse(**i) for i in result["issues"]],
        limit=result["limit"],
        offset=result["offset"],
    )


@app.get("/api/admin/issues/{issue_id}", response_model=IssueResponse)
async def admin_issue_detail(issue_id: int):
    """Get a single reported issue."""
    issue = db.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return IssueResponse(**issue)


@app.patch("/api/admin/issues/{issue_id}")
async def admin_update_issue(issue_id: int, request: IssueUpdateRequest):
    """Update a reported issue's status and/or admin notes."""
    issue = db.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    status = request.status if request.status else None
    admin_notes = request.admin_notes if request.admin_notes else None
    db.update_issue(issue_id, status=status, admin_notes=admin_notes)
    return {"status": "ok"}


@app.delete("/api/admin/issues/{issue_id}")
async def admin_delete_issue(issue_id: int):
    """Delete a reported issue."""
    issue = db.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete_issue(issue_id)
    return {"status": "ok"}


# ════════════════════════════════════════════════════════════════
# Golden Q&A endpoints
# ════════════════════════════════════════════════════════════════

@app.get("/api/admin/golden-qa", response_model=GoldenQAListResponse)
async def admin_golden_qa_list(category: str = Query(None)):
    """List all golden Q&A pairs (including inactive for admin)."""
    if category:
        items = db.get_golden_qa_list(category=category, include_inactive=True)
    else:
        items = db.get_all_golden_qa()
    return GoldenQAListResponse(
        total=len(items),
        items=[GoldenQAResponse(**i) for i in items],
    )


@app.post("/api/admin/golden-qa", response_model=GoldenQAResponse)
async def admin_create_golden_qa(request: GoldenQACreate):
    """Create a golden Q&A pair and sync to Qdrant."""
    qa_id = db.create_golden_qa(
        question=request.question,
        answer=request.answer,
        category=request.category,
    )
    await asyncio.to_thread(_sync_golden_qa_to_qdrant)
    qa = db.get_golden_qa(qa_id)
    return GoldenQAResponse(**qa)


@app.patch("/api/admin/golden-qa/{qa_id}", response_model=GoldenQAResponse)
async def admin_update_golden_qa(qa_id: int, request: GoldenQAUpdate):
    """Update a golden Q&A pair and sync to Qdrant."""
    qa = db.get_golden_qa(qa_id)
    if not qa:
        raise HTTPException(status_code=404, detail="Golden Q&A pair not found")
    db.update_golden_qa(
        qa_id,
        question=request.question,
        answer=request.answer,
        category=request.category,
        is_active=request.is_active,
    )
    await asyncio.to_thread(_sync_golden_qa_to_qdrant)
    updated = db.get_golden_qa(qa_id)
    return GoldenQAResponse(**updated)


@app.delete("/api/admin/golden-qa/{qa_id}")
async def admin_delete_golden_qa(qa_id: int):
    """Delete a golden Q&A pair and sync to Qdrant."""
    qa = db.get_golden_qa(qa_id)
    if not qa:
        raise HTTPException(status_code=404, detail="Golden Q&A pair not found")
    db.delete_golden_qa(qa_id)
    await asyncio.to_thread(_sync_golden_qa_to_qdrant)
    return {"status": "ok"}


@app.post("/api/admin/golden-qa/sync")
async def admin_sync_golden_qa():
    """Force full re-sync of golden Q&A pairs to Qdrant."""
    count = await asyncio.to_thread(_sync_golden_qa_to_qdrant)
    return {"status": "ok", "synced": count}


# ════════════════════════════════════════════════════════════════
# Email Sales System endpoints
# ════════════════════════════════════════════════════════════════

# -- Email Templates --

@app.post("/api/admin/email/templates")
async def create_email_template(request: EmailTemplateCreate):
    tid = et_mod.create_template(
        name=request.name, subject=request.subject,
        html_body=request.html_body, text_body=request.text_body,
        category=request.category, variables=request.variables,
    )
    return {"id": tid}


@app.get("/api/admin/email/templates")
async def list_email_templates(category: str = Query(None)):
    templates = et_mod.get_templates(category=category)
    return EmailTemplateListResponse(total=len(templates), templates=templates)


@app.get("/api/admin/email/templates/{template_id}")
async def get_email_template(template_id: int):
    t = et_mod.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return EmailTemplateResponse(**t)


@app.patch("/api/admin/email/templates/{template_id}")
async def update_email_template(template_id: int, request: EmailTemplateUpdate):
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None and v != "" and v != []}
    if not et_mod.update_template(template_id, **kwargs):
        raise HTTPException(status_code=404, detail="Template not found or no changes")
    return {"status": "ok"}


@app.post("/api/admin/email/templates/{template_id}/preview")
async def preview_email_template(template_id: int, request: TemplatePreviewRequest):
    result = et_mod.preview_template(template_id, request.sample_data)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@app.post("/api/admin/email/templates/{template_id}/duplicate")
async def duplicate_email_template(template_id: int):
    new_id = et_mod.duplicate_template(template_id)
    if not new_id:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": new_id}


# -- Email Contacts --

@app.post("/api/admin/email/contacts")
async def create_email_contact(request: EmailContactCreate):
    cid = ec_mod.create_contact(
        email=request.email, name=request.name, company=request.company,
        phone=request.phone, source=request.source, tags=request.tags,
    )
    if not cid:
        raise HTTPException(status_code=409, detail="Contact with this email already exists")
    return {"id": cid}


@app.get("/api/admin/email/contacts")
async def list_email_contacts(
    status: str = Query(None), tags: str = Query(None),
    search: str = Query(None),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    result = ec_mod.get_contacts(status=status, tags=tags, search=search, limit=limit, offset=offset)
    return EmailContactListResponse(
        total=result["total"],
        contacts=[EmailContactResponse(**c) for c in result["contacts"]],
        limit=result["limit"], offset=result["offset"],
    )


@app.patch("/api/admin/email/contacts/{contact_id}")
async def update_email_contact(contact_id: int, request: EmailContactUpdate):
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None and v != ""}
    if not ec_mod.update_contact(contact_id, **kwargs):
        raise HTTPException(status_code=404, detail="Contact not found or no changes")
    return {"status": "ok"}


@app.post("/api/admin/email/contacts/import")
async def import_email_contacts(file: UploadFile = File(...), tags: str = ""):
    content = (await file.read()).decode("utf-8", errors="replace")
    result = ec_mod.import_csv(content, default_tags=tags)
    return result


@app.get("/api/admin/email/contacts/export")
async def export_email_contacts(status: str = Query(None)):
    csv_data = ec_mod.export_contacts_csv(status=status)
    return PlainTextResponse(
        csv_data, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=email-contacts.csv"},
    )


@app.post("/api/admin/email/contacts/validate")
async def validate_email_contacts():
    result = ec_mod.validate_contacts()
    return ContactValidationResult(**result)


@app.post("/api/admin/email/contacts/sync-leads")
async def sync_leads_to_contacts():
    result = ec_mod.sync_from_leads()
    return result


# -- Email Campaigns --

@app.post("/api/admin/email/campaigns")
async def create_email_campaign(request: EmailCampaignCreate):
    cid = ecamp_mod.create_campaign(
        name=request.name, campaign_type=request.campaign_type,
        template_id=request.template_id, subject_line=request.subject_line,
        from_name=request.from_name, from_email=request.from_email,
        reply_to=request.reply_to, target_filter=request.target_filter,
        ab_enabled=request.ab_enabled, ab_variant_b_subject=request.ab_variant_b_subject,
        ab_variant_b_template_id=request.ab_variant_b_template_id,
        ab_split_percentage=request.ab_split_percentage,
    )
    return {"id": cid}


@app.get("/api/admin/email/campaigns")
async def list_email_campaigns(
    campaign_type: str = Query(None), status: str = Query(None),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    result = ecamp_mod.get_campaigns(campaign_type=campaign_type, status=status, limit=limit, offset=offset)
    return EmailCampaignListResponse(
        total=result["total"],
        campaigns=[EmailCampaignResponse(**c) for c in result["campaigns"]],
    )


@app.get("/api/admin/email/campaigns/{campaign_id}")
async def get_email_campaign(campaign_id: int):
    c = ecamp_mod.get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return EmailCampaignResponse(**c)


@app.patch("/api/admin/email/campaigns/{campaign_id}")
async def update_email_campaign(campaign_id: int, request: EmailCampaignUpdate):
    kwargs = {}
    for k, v in request.model_dump().items():
        if v is not None and v != "" and v != []:
            kwargs[k] = v
    if not ecamp_mod.update_campaign(campaign_id, **kwargs):
        raise HTTPException(status_code=404, detail="Campaign not found or no changes")
    return {"status": "ok"}


@app.post("/api/admin/email/campaigns/{campaign_id}/send")
async def send_email_campaign(campaign_id: int):
    result = ecamp_mod.start_campaign(campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/admin/email/campaigns/{campaign_id}/schedule")
async def schedule_email_campaign(campaign_id: int, request: CampaignScheduleRequest):
    result = ecamp_mod.schedule_campaign(campaign_id, request.scheduled_at)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/admin/email/campaigns/{campaign_id}/pause")
async def pause_email_campaign(campaign_id: int):
    result = ecamp_mod.pause_campaign(campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/admin/email/campaigns/{campaign_id}/cancel")
async def cancel_email_campaign(campaign_id: int):
    result = ecamp_mod.cancel_campaign(campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/admin/email/campaigns/{campaign_id}/test")
async def test_email_campaign(campaign_id: int, request: CampaignTestRequest):
    result = ecamp_mod.send_test(campaign_id, request.test_email)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/admin/email/campaigns/{campaign_id}/recipients")
async def get_campaign_recipients(
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    result = ecamp_mod.get_campaign_recipients(campaign_id, limit=limit, offset=offset)
    return result


@app.get("/api/admin/email/campaigns/{campaign_id}/ab-results")
async def get_campaign_ab_results(campaign_id: int):
    return ecamp_mod.get_ab_results(campaign_id)


# -- Email Sequences --

@app.post("/api/admin/email/sequences")
async def create_email_sequence(request: EmailSequenceCreate):
    sid = eseq_mod.create_sequence(
        name=request.name, description=request.description,
        campaign_type=request.campaign_type,
        trigger_event=request.trigger_event, trigger_config=request.trigger_config,
    )
    return {"id": sid}


@app.get("/api/admin/email/sequences")
async def list_email_sequences(campaign_type: str = Query(None)):
    seqs = eseq_mod.get_sequences(campaign_type=campaign_type)
    return EmailSequenceListResponse(total=len(seqs), sequences=seqs)


@app.get("/api/admin/email/sequences/{sequence_id}")
async def get_email_sequence(sequence_id: int):
    seq = eseq_mod.get_sequence(sequence_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq


@app.post("/api/admin/email/sequences/{sequence_id}/steps")
async def add_sequence_step(sequence_id: int, request: EmailSequenceStepCreate):
    step_id = eseq_mod.add_step(
        sequence_id=sequence_id, template_id=request.template_id,
        subject_override=request.subject_override,
        delay_days=request.delay_days, delay_hours=request.delay_hours,
        condition_type=request.condition_type,
    )
    return {"id": step_id}


@app.post("/api/admin/email/sequences/{sequence_id}/enroll")
async def enroll_in_sequence(sequence_id: int, request: SequenceEnrollRequest):
    count = eseq_mod.enroll(sequence_id, contact_ids=request.contact_ids, lead_ids=request.lead_ids)
    return {"enrolled": count}


@app.get("/api/admin/email/sequences/{sequence_id}/funnel")
async def get_sequence_funnel(sequence_id: int):
    return eseq_mod.get_sequence_funnel(sequence_id)


# -- Email Analytics --

@app.get("/api/admin/email/analytics/overview")
async def email_analytics_overview(days: int = Query(30, ge=1, le=365)):
    data = ea_mod.get_overview(days=days)
    return EmailAnalyticsOverview(**data)


@app.get("/api/admin/email/analytics/warm-vs-cold")
async def email_analytics_warm_vs_cold(days: int = Query(30, ge=1, le=365)):
    return ea_mod.get_warm_vs_cold(days=days)


@app.get("/api/admin/email/analytics/send-times")
async def email_analytics_send_times(days: int = Query(90, ge=1, le=365)):
    return ea_mod.get_send_time_heatmap(days=days)


@app.get("/api/admin/email/analytics/domains")
async def email_analytics_domains(days: int = Query(30, ge=1, le=365)):
    return ea_mod.get_domain_health(days=days)


@app.get("/api/admin/email/analytics/volume")
async def email_analytics_volume(days: int = Query(30, ge=1, le=365)):
    return ea_mod.get_send_volume_over_time(days=days)


@app.get("/api/admin/email/analytics/rankings")
async def email_analytics_rankings(days: int = Query(30, ge=1, le=365)):
    return ea_mod.get_campaign_rankings(days=days)


# -- Delete Template --

@app.delete("/api/admin/email/templates/{template_id}")
async def delete_email_template(template_id: int):
    deleted = et_mod.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"status": "deleted"}


# -- Delete Contacts --

@app.post("/api/admin/email/contacts/delete")
async def delete_email_contacts(request: dict):
    ids = request.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No contact IDs provided")
    # Delete referencing rows first to avoid FK constraint
    from backend.database import _get_conn
    conn = _get_conn()
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM email_sequence_enrollments WHERE contact_id IN ({placeholders})", ids)
    conn.execute(f"DELETE FROM email_sends WHERE contact_id IN ({placeholders})", ids)
    conn.commit()
    ec_mod.delete_contacts(ids)
    return {"deleted": len(ids)}


# -- Delete Campaign --

@app.delete("/api/admin/email/campaigns/{campaign_id}")
async def delete_email_campaign(campaign_id: int):
    result = ecamp_mod.delete_campaign(campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# -- Direct Email Send --

@app.post("/api/admin/email/send")
async def send_direct_email(request: DirectEmailRequest):
    from backend.email_service import sender
    result = sender.send_email(
        to_email=request.to_email, to_name=request.to_name,
        subject=request.subject, html_body=request.html_body,
        text_body=request.text_body, from_name=request.from_name,
        from_email=request.from_email, reply_to=request.reply_to,
    )
    if not result["success"]:
        error_msg = result.get("error", "Send failed")
        details = result.get("details", "")
        raise HTTPException(status_code=400, detail=f"{error_msg}: {details}" if details else error_msg)
    return result


# -- Public Tracking Endpoints (No Auth) --

@app.get("/t/{tracking_id}/open.gif")
async def tracking_pixel(tracking_id: str):
    """Serve tracking pixel and record open event."""
    etrack_mod.record_open(tracking_id)
    from fastapi.responses import Response
    return Response(
        content=etrack_mod.TRACKING_PIXEL,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/t/{tracking_id}/click")
async def tracking_click(tracking_id: str, url: str = Query(...)):
    """Record click and redirect to original URL."""
    etrack_mod.record_click(tracking_id, url)

    # Update lead score if this send is linked to a lead
    conn = db._get_conn()
    send = conn.execute(
        "SELECT lead_id FROM email_sends WHERE tracking_id = ?", (tracking_id,)
    ).fetchone()
    if send and send["lead_id"]:
        lead_capture.update_score_from_email_event(send["lead_id"], "click")

    return RedirectResponse(url=url, status_code=302)


@app.get("/unsubscribe/{tracking_id}")
async def unsubscribe_page(tracking_id: str):
    """Show unsubscribe confirmation page."""
    info = etrack_mod.get_unsubscribe_info(tracking_id)
    if not info:
        return HTMLResponse("<h1>Invalid link</h1>", status_code=404)

    if info["already_unsubscribed"]:
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:500px;margin:60px auto;text-align:center;">
        <h2>Already Unsubscribed</h2>
        <p>{info['email']} has already been unsubscribed.</p>
        </body></html>
        """
        return HTMLResponse(html)

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:500px;margin:60px auto;text-align:center;">
    <h2>Unsubscribe</h2>
    <p>Are you sure you want to unsubscribe <strong>{info['email']}</strong>?</p>
    <form method="POST" action="/unsubscribe/{tracking_id}">
        <p><label>Reason (optional):<br><textarea name="reason" rows="3" style="width:100%;"></textarea></label></p>
        <button type="submit" style="background:#ef4444;color:white;border:none;padding:12px 32px;border-radius:6px;cursor:pointer;font-size:16px;">
            Unsubscribe
        </button>
    </form>
    </body></html>
    """
    return HTMLResponse(html)


@app.post("/unsubscribe/{tracking_id}")
async def process_unsubscribe(tracking_id: str, request: Request):
    """Process unsubscribe form submission."""
    form = await request.form()
    reason = form.get("reason", "")
    result = etrack_mod.process_unsubscribe(tracking_id, reason=reason)

    if not result:
        return HTMLResponse("<h1>Invalid link</h1>", status_code=404)

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:500px;margin:60px auto;text-align:center;">
    <h2>Unsubscribed Successfully</h2>
    <p><strong>{result['email']}</strong> has been removed from our mailing list.</p>
    <p style="color:#6b7280;font-size:14px;">We're sorry to see you go.</p>
    </body></html>
    """
    return HTMLResponse(html)


# -- WhatsApp bridge process manager --

_wa_bridge_process: subprocess.Popen | None = None
_WA_BRIDGE_DIR = Path(__file__).resolve().parent.parent / "whatsapp-bridge"
_WA_BRIDGE_PORT = 8004


def _is_bridge_alive() -> bool:
    """Check if something is listening on the bridge port (fast socket check)."""
    global _wa_bridge_process
    if _wa_bridge_process is not None:
        if _wa_bridge_process.poll() is not None:
            _wa_bridge_process = None
            return False
    import socket
    try:
        with socket.create_connection(("127.0.0.1", _WA_BRIDGE_PORT), timeout=0.5):
            return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


def _start_bridge() -> bool:
    """Start the WhatsApp bridge Node.js process if not already running."""
    global _wa_bridge_process
    if _is_bridge_alive():
        return True

    server_js = _WA_BRIDGE_DIR / "server.js"
    node_modules = _WA_BRIDGE_DIR / "node_modules"
    if not server_js.exists():
        print("[WhatsApp] server.js not found — cannot start bridge")
        return False
    if not node_modules.exists():
        print("[WhatsApp] node_modules not found — run 'npm install' in whatsapp-bridge/")
        return False

    try:
        _wa_bridge_process = subprocess.Popen(
            ["node", "server.js"],
            cwd=str(_WA_BRIDGE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # On Windows, CREATE_NEW_PROCESS_GROUP lets us kill cleanly
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        print(f"[WhatsApp] Bridge started (PID {_wa_bridge_process.pid})")
        return True
    except FileNotFoundError:
        print("[WhatsApp] 'node' not found — install Node.js to use WhatsApp bridge")
        return False
    except Exception as e:
        print(f"[WhatsApp] Failed to start bridge: {e}")
        return False


def _stop_bridge():
    """Stop the WhatsApp bridge process if running."""
    global _wa_bridge_process
    # Try graceful stop via our tracked process handle
    if _wa_bridge_process is not None and _wa_bridge_process.poll() is None:
        try:
            _wa_bridge_process.terminate()
            try:
                _wa_bridge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _wa_bridge_process.kill()
                _wa_bridge_process.wait(timeout=3)
            print("[WhatsApp] Bridge process stopped")
        except Exception as e:
            print(f"[WhatsApp] Error stopping bridge: {e}")
        finally:
            _wa_bridge_process = None

    # Also kill any orphaned node process on the bridge port
    # (can happen after uvicorn reload loses the process handle)
    import sys
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if f":{_WA_BRIDGE_PORT}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    if pid.isdigit():
                        subprocess.run(["taskkill", "/F", "/PID", pid],
                                       capture_output=True, timeout=5)
                        print(f"[WhatsApp] Killed orphaned bridge process (PID {pid})")
        except Exception:
            pass
    else:
        try:
            subprocess.run(
                ["fuser", "-k", f"{_WA_BRIDGE_PORT}/tcp"],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass


def _wipe_bridge_auth():
    """Delete the auth_info directory to clear saved WhatsApp session."""
    auth_dir = _WA_BRIDGE_DIR / "auth_info"
    if auth_dir.exists():
        shutil.rmtree(auth_dir, ignore_errors=True)
        print("[WhatsApp] Auth directory wiped")


def _proxy_bridge(path: str, method: str = "GET") -> dict | None:
    """Make a request to the WhatsApp bridge. Returns parsed JSON or None.
    Only call this AFTER _is_bridge_alive() returns True — avoids slow timeouts.
    """
    import urllib.request
    url = f"http://localhost:{_WA_BRIDGE_PORT}{path}"
    try:
        data = b"{}" if method == "POST" else None
        headers = {"Content-Type": "application/json"} if method == "POST" else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=3) as resp:
            import json as _json
            return _json.loads(resp.read())
    except Exception:
        return None


# -- WhatsApp API endpoints --

@app.get("/api/admin/whatsapp/status")
def whatsapp_status():
    """Get bridge status. If bridge is down, start it in the background."""
    if _is_bridge_alive():
        result = _proxy_bridge("/status")
        if result:
            return result
    # Bridge not responding — kick-start it
    _start_bridge()
    return {"connected": False, "phone_number": None, "uptime": 0, "has_qr": False}


@app.get("/api/admin/whatsapp/qr")
def whatsapp_qr():
    """Get QR from bridge. If bridge is down, start it and tell frontend to retry."""
    if _is_bridge_alive():
        result = _proxy_bridge("/qr")
        if result:
            return result
    # Bridge not responding — start it, frontend polling will pick up QR
    _start_bridge()
    return {"qr": None, "connected": False, "message": "Starting WhatsApp bridge... QR will appear shortly."}


@app.post("/api/admin/whatsapp/reset")
def whatsapp_reset():
    """Stop bridge, wipe session, restart. Frontend polling picks up new QR."""
    _stop_bridge()
    _wipe_bridge_auth()
    _start_bridge()
    return {"status": "ok", "message": "Session reset. QR will appear in a few seconds."}


@app.get("/api/admin/whatsapp/conversations")
async def whatsapp_conversations(
    page: int = Query(1, ge=1),
    search: str = Query(""),
):
    """List unique WhatsApp sessions."""
    limit = 20
    offset = (page - 1) * limit
    return db.get_whatsapp_conversations(limit=limit, offset=offset, search=search)


@app.get("/api/admin/whatsapp/conversations/{session_id}")
async def whatsapp_conversation(session_id: str):
    """Full chat history for a WhatsApp session."""
    messages = db.get_whatsapp_history(session_id)
    phone = db.get_whatsapp_phone(session_id)
    return {"session_id": session_id, "phone": phone, "messages": messages}


@app.get("/api/admin/whatsapp/analytics")
async def whatsapp_analytics():
    """WhatsApp stats overview."""
    return db.get_whatsapp_stats()


@app.post("/api/admin/whatsapp/messages")
async def whatsapp_log_message(request: Request):
    """Called by bridge to log user+bot message pair."""
    data = await request.json()
    session_id = data["session_id"]
    phone = data["phone"]
    db.save_whatsapp_message(session_id, phone, "user", data["user_message"])
    db.save_whatsapp_message(session_id, phone, "assistant", data["bot_response"])
    return {"status": "ok"}


# -- Chatbot static files (CSS, JS, logo) --

@app.get("/chatbot-static/{filename:path}")
async def serve_chatbot_static(filename: str):
    """Serve chatbot frontend assets."""
    file_path = FRONTEND_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(file_path))


# -- Admin Data Management API --

@app.get("/api/admin/data/sources")
async def admin_data_sources():
    """Overview of all knowledge sources feeding the chatbot."""
    total_points = vector_store.get_points_count()
    uploaded_files = db.get_ingested_files(status="active")
    uploaded_chunks = sum(f.get("total_chunks", 0) for f in uploaded_files)

    # Count golden QA pairs
    qa_pairs = db.get_golden_qa_list()
    qa_count = len(qa_pairs) if qa_pairs else 0

    # Website + mirror chunks = total - uploaded - golden_qa
    website_chunks = max(0, total_points - uploaded_chunks - qa_count)

    return {
        "total_chunks": total_points,
        "sources": [
            {
                "name": "Website (sparrowi.com)",
                "type": "website",
                "chunks": website_chunks,
                "status": "auto-synced",
                "description": "Scraped from sparrowi.com + hardcoded website knowledge",
            },
            {
                "name": "Uploaded Files",
                "type": "uploaded",
                "chunks": uploaded_chunks,
                "status": "active",
                "description": "PDF and SQL files uploaded by admin",
                "file_count": len(uploaded_files),
            },
            {
                "name": "Golden Q&A",
                "type": "golden_qa",
                "chunks": qa_count,
                "status": "auto-synced",
                "description": "Curated question-answer pairs",
            },
        ],
    }


@app.get("/api/admin/data/files")
async def admin_data_files():
    """List all uploaded files."""
    files = db.get_ingested_files(status="active")
    # Don't expose internal storage_path or chunk_ids to frontend
    for f in files:
        f.pop("storage_path", None)
        f.pop("chunk_ids", None)
    return {"files": files, "total": len(files)}


@app.post("/api/admin/data/upload")
async def admin_data_upload(files: List[UploadFile] = File(...)):
    """Upload and ingest files with persistent tracking."""
    results = []
    grand_total_chunks = 0

    for file in files:
        filename = file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in ("sql", "pdf"):
            results.append(FileResult(
                filename=filename, file_type=ext, tables=[], total_chunks=0,
                total_rows=0, error=f"Unsupported file type: .{ext}",
            ))
            continue

        content = await file.read()

        if not content or len(content.strip()) == 0:
            results.append(FileResult(
                filename=filename, file_type=ext, tables=[], total_chunks=0,
                total_rows=0, error="File is empty",
            ))
            continue

        try:
            if ext == "sql":
                result = _ingest_sql(content, filename)
                # Also track SQL files
                import uuid as _uuid
                storage_name = f"{_uuid.uuid4().hex[:12]}_{filename}"
                storage_path = UPLOADS_DIR / storage_name
                storage_path.write_bytes(content)
                chunk_ids = [int(c_id, 16) % (2**63) for c_id in
                             [hashlib.sha256(f"{filename}_{i}".encode()).hexdigest()[:16]
                              for i in range(result.total_chunks)]]
                db.save_ingested_file(
                    filename=filename, file_type="sql", file_size=len(content),
                    total_chunks=result.total_chunks, total_pages=0,
                    total_rows=result.total_rows, tables=result.tables,
                    chunk_ids=chunk_ids, storage_path=str(storage_path),
                )
            else:
                result = _ingest_pdf(content, filename, track=True)
            grand_total_chunks += result.total_chunks
            results.append(result)
        except Exception as e:
            results.append(FileResult(
                filename=filename, file_type=ext, tables=[], total_chunks=0,
                total_rows=0, error=str(e),
            ))

    if not results:
        raise HTTPException(status_code=400, detail="No files provided")

    return IngestResponse(
        files=results,
        total_files=len(results),
        total_chunks=grand_total_chunks,
    )


@app.delete("/api/admin/data/files/{file_id}")
async def admin_data_delete_file(file_id: int):
    """Delete a specific uploaded file and its chunks from Qdrant."""
    file_record = db.get_ingested_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    if file_record["status"] != "active":
        raise HTTPException(status_code=400, detail="File already deleted")

    # Delete chunks from Qdrant
    chunk_ids = file_record.get("chunk_ids", [])
    if chunk_ids:
        vector_store.delete_by_ids(chunk_ids)

    # Soft-delete in database
    db.delete_ingested_file(file_id)

    # Remove saved file from disk
    storage_path = file_record.get("storage_path", "")
    if storage_path and Path(storage_path).exists():
        Path(storage_path).unlink()

    return {
        "status": "ok",
        "message": f"Deleted '{file_record['filename']}' and {len(chunk_ids)} chunks",
    }


@app.get("/api/admin/data/files/{file_id}/chunks")
async def admin_data_file_chunks(file_id: int):
    """View chunks of a specific uploaded file."""
    file_record = db.get_ingested_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    chunk_ids = file_record.get("chunk_ids", [])
    if not chunk_ids:
        return {"file": file_record["filename"], "chunks": []}

    # Retrieve chunk payloads from Qdrant
    from qdrant_client import QdrantClient
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    try:
        points = client.retrieve(
            collection_name=settings.qdrant_collection,
            ids=chunk_ids,
            with_payload=True,
        )
        chunks = []
        for p in points:
            chunks.append({
                "id": p.id,
                "text": p.payload.get("text", "")[:300],
                "chunk_type": p.payload.get("chunk_type", ""),
                "table": p.payload.get("table", ""),
            })
        return {"file": file_record["filename"], "chunks": chunks, "total": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {e}")


@app.post("/api/admin/data/refresh-website")
async def admin_data_refresh_website():
    """Re-scrape sparrowi.com and update website chunks in Qdrant."""
    from backend import web_scraper

    try:
        vector_store.delete_by_table("sparrowi.com")
        chunks = web_scraper.crawl()
        mirror_chunks = web_scraper.crawl_mirror(MIRROR_DIR)
        chunks.extend(mirror_chunks)

        if not chunks:
            _embed_and_store(WEBSITE_CHUNKS)
            return {"status": "ok", "pages_crawled": 0, "chunks_created": len(WEBSITE_CHUNKS),
                    "message": "No live content found, restored knowledge base"}

        _embed_and_store(chunks)
        _embed_and_store(WEBSITE_CHUNKS)

        pages = set()
        for c in chunks:
            first_line = c.text.split("\n", 1)[0]
            pages.add(first_line)

        return {
            "status": "ok",
            "pages_crawled": len(pages),
            "chunks_created": len(chunks) + len(WEBSITE_CHUNKS),
            "message": f"Refreshed {len(pages)} pages into {len(chunks)} chunks",
        }
    except Exception as e:
        return {"status": "error", "pages_crawled": 0, "chunks_created": 0,
                "message": str(e)}


# -- Admin dashboard SPA --

@app.get("/admin")
async def admin_redirect():
    """Redirect /admin to /admin/."""
    return RedirectResponse(url="/admin/")


@app.get("/admin/{path:path}")
async def serve_admin(path: str):
    """Serve React SPA -- index.html for all routes, static files as-is."""
    if not ADMIN_DIR.is_dir():
        return HTMLResponse(
            "<h1>Admin dashboard not built</h1>"
            "<p>Run <code>cd admin-dashboard && npm run build</code> to build the dashboard.</p>",
            status_code=404,
        )

    # Try to serve the exact file first (JS, CSS, images)
    file_path = ADMIN_DIR / path
    if file_path.is_file():
        content_type, _ = mimetypes.guess_type(str(file_path))
        # Hashed asset files can be cached long; index.html should not be cached
        headers = {}
        if "/assets/" in path:
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return FileResponse(str(file_path), media_type=content_type, headers=headers)

    # For all other routes, serve index.html (SPA routing) — async file read
    index_path = ADMIN_DIR / "index.html"
    if index_path.is_file():
        content = await asyncio.to_thread(index_path.read_text, encoding="utf-8")
        return HTMLResponse(content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

    raise HTTPException(status_code=404, detail="Dashboard not found")


# -- Root redirect --

@app.get("/")
async def root():
    """Redirect root to the mirror website homepage."""
    return RedirectResponse(url="/www.sparrowi.com/")


# -- Mirror website catch-all (MUST be last) --

@app.get("/{path:path}")
async def serve_mirror(path: str):
    """Serve mirror website files, injecting the chatbot widget into HTML pages."""
    # Intercept admin paths that slip through to the catch-all
    if path == "admin" or path == "admin/":
        return await serve_admin("")
    if path.startswith("admin/"):
        return await serve_admin(path[6:])

    file_path = MIRROR_DIR / path

    # Handle directory requests
    if file_path.is_dir():
        file_path = file_path / "index.html"

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    # For HTML files: inject the chatbot widget before </body> — async file read
    if file_path.suffix.lower() in (".html", ".htm"):
        content = await asyncio.to_thread(file_path.read_text, encoding="utf-8", errors="replace")
        widget_html = _get_widget_html()
        if "</body>" in content and widget_html:
            content = content.replace("</body>", widget_html + "\n</body>", 1)
        return HTMLResponse(content)

    # For all other files: serve as-is with correct MIME type
    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=content_type)

