"""Loads .env and exposes all configuration constants."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Sarvam AI
    sarvam_api_key: str = ""
    sarvam_model: str = "sarvam-105b"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "sql_chunks"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 output size

    # Server
    host: str = "0.0.0.0"
    port: int = 8003

    # RAG
    top_k: int = 6  # fetch candidates
    min_score: float = 0.25  # lowered from 0.35 to catch semantic synonyms (web dev = full stack)
    max_context_chars: int = 2200  # kept below sarvam-m's 7192-token window after system prompt (~5k tok)
    max_sources_shown: int = 5  # max sources returned to frontend

    # Re-ranker
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_k: int = 3
    reranker_enabled: bool = True
    reranker_min_score: float = -5.0  # cross-encoder logit threshold (negative = irrelevant)

    # Grounding
    grounding_enabled: bool = True
    grounding_temperature: float = 0.0

    # Web Scraper
    scraper_base_url: str = "https://www.sparrowi.com"
    scraper_max_pages: int = 50
    scraper_timeout: int = 30  # seconds per page

    # Redis (optional — falls back to in-memory if unavailable)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    session_ttl: int = 3600  # 1 hour

    # SQLite
    db_path: str = str(Path(__file__).resolve().parent.parent / "data" / "sparrowi.db")

    # Email Notifications (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_emails: str = ""  # comma-separated

    # Lead Scoring Thresholds
    lead_hot_threshold: int = 70
    lead_qualified_threshold: int = 40

    # Email Campaigns
    email_from_name: str = "Sparrowi"
    email_from_address: str = ""
    email_reply_to: str = ""
    email_rate_limit: int = 30
    email_batch_size: int = 25
    email_tracking_base_url: str = ""
    email_max_retries: int = 3
    email_warmup_enabled: bool = False
    email_warmup_daily_limit: int = 50

    # Microsoft Graph API (alternative email provider)
    email_provider: str = "smtp"  # "smtp" or "microsoft"
    ms_tenant_id: str = ""
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_sender_email: str = ""  # e.g. rishi.sharma@sparrowi.com

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin123"

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent / ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
