"""Pydantic request/response schemas for the API."""

from typing import Literal
from pydantic import BaseModel, field_validator


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]  # only "user" or "assistant" allowed
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list[ConversationMessage] = []
    page_url: str = ""

    @field_validator("session_id")
    @classmethod
    def session_id_max_length(cls, v: str) -> str:
        if len(v) > 128:
            raise ValueError("session_id must be 128 characters or fewer")
        return v


class SourceChunk(BaseModel):
    text: str
    table: str
    chunk_type: str
    url: str = ""
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    needs_clarification: bool = False
    follow_up_question: str = ""
    follow_up_message: str = ""
    options: list[str] = []
    suggestions: list[str] = []


class FileResult(BaseModel):
    filename: str
    file_type: str  # "sql" or "pdf"
    tables: list[str]
    total_chunks: int
    total_rows: int
    total_pages: int = 0
    error: str = ""


class IngestResponse(BaseModel):
    files: list[FileResult]
    total_files: int
    total_chunks: int


class ScrapeResponse(BaseModel):
    status: str
    pages_crawled: int
    chunks_created: int
    message: str


class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int      # which bot message (0-based)
    feedback: str            # "up" or "down"


class HealthResponse(BaseModel):
    status: str
    qdrant: bool
    embedding_model: str
    claude_model: str
    ingestion_ready: bool = True


# ── Admin / Sales Bot models ──

class LeadResponse(BaseModel):
    id: int
    session_id: str
    name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    source_page: str = ""
    lead_score: int = 0
    status: str = "new"
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class LeadDetailResponse(LeadResponse):
    conversation: list[dict] = []


class LeadListResponse(BaseModel):
    total: int
    leads: list[LeadResponse]
    limit: int
    offset: int


class LeadUpdateRequest(BaseModel):
    status: str = ""
    notes: str = ""


class DashboardStats(BaseModel):
    total_leads: int = 0
    hot_leads: int = 0
    messages_today: int = 0
    satisfaction_rate: float = 0.0
    active_sessions_today: int = 0
    avg_lead_score: float = 0.0
    total_leads_trend: float = 0.0
    hot_leads_trend: float = 0.0
    messages_today_trend: float = 0.0
    satisfaction_rate_trend: float = 0.0
    active_sessions_today_trend: float = 0.0
    avg_lead_score_trend: float = 0.0


class AnalyticsData(BaseModel):
    messages_per_day: list[dict] = []
    popular_topics: list[dict] = []
    lead_funnel: dict = {}
    peak_hours: list[dict] = []
    busiest_pages: list[dict] = []
    satisfaction_trend: list[dict] = []


class ConversationListResponse(BaseModel):
    total: int
    conversations: list[dict]
    limit: int
    offset: int


class AdminSettings(BaseModel):
    # Email provider: "smtp" or "microsoft"
    email_provider: str = "smtp"
    # SMTP settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Microsoft Graph API settings
    ms_tenant_id: str = ""
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_sender_email: str = ""
    # General
    alert_emails: str = ""
    lead_hot_threshold: int = 60
    lead_qualified_threshold: int = 40


class TrackEventRequest(BaseModel):
    session_id: str
    event_type: str
    event_data: dict = {}
    page_url: str = ""


# ── Reported Issues models ──

class ReportIssueRequest(BaseModel):
    session_id: str
    message: str
    page_url: str = ""


class IssueResponse(BaseModel):
    id: int
    session_id: str
    message: str
    page_url: str = ""
    status: str = "open"
    admin_notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class IssueListResponse(BaseModel):
    total: int
    issues: list[IssueResponse]
    limit: int
    offset: int


class IssueUpdateRequest(BaseModel):
    status: str = ""
    admin_notes: str = ""


# ── Golden Q&A models ──

class GoldenQACreate(BaseModel):
    question: str
    answer: str
    category: str = ""


class GoldenQAUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    is_active: int | None = None


class GoldenQAResponse(BaseModel):
    id: int
    question: str
    answer: str
    category: str = ""
    is_active: int = 1
    created_at: str = ""
    updated_at: str = ""


class GoldenQAListResponse(BaseModel):
    total: int
    items: list[GoldenQAResponse]


# ── Email Sales System models ──

class EmailContactCreate(BaseModel):
    email: str
    name: str = ""
    company: str = ""
    phone: str = ""
    source: str = "manual"
    tags: str = ""

class EmailContactUpdate(BaseModel):
    name: str = ""
    company: str = ""
    phone: str = ""
    tags: str = ""
    status: str = ""

class EmailContactResponse(BaseModel):
    id: int
    email: str
    name: str = ""
    company: str = ""
    phone: str = ""
    source: str = ""
    tags: str = ""
    status: str = "active"
    lead_id: int | None = None
    created_at: str = ""
    updated_at: str = ""

class EmailContactListResponse(BaseModel):
    total: int
    contacts: list[EmailContactResponse]
    limit: int
    offset: int

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    category: str = "promotion"
    variables: list[str] = []

class EmailTemplateUpdate(BaseModel):
    name: str = ""
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    category: str = ""
    variables: list[str] = []
    is_active: int | None = None

class EmailTemplateResponse(BaseModel):
    id: int
    name: str
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    category: str = ""
    variables: list = []
    is_active: int = 1
    created_at: str = ""
    updated_at: str = ""

class EmailTemplateListResponse(BaseModel):
    total: int
    templates: list[EmailTemplateResponse]

class TemplatePreviewRequest(BaseModel):
    sample_data: dict = {}

class EmailCampaignCreate(BaseModel):
    name: str
    campaign_type: str = "warm"
    template_id: int | None = None
    subject_line: str = ""
    from_name: str = ""
    from_email: str = ""
    reply_to: str = ""
    target_filter: dict = {}
    ab_enabled: bool = False
    ab_variant_b_subject: str = ""
    ab_variant_b_template_id: int | None = None
    ab_split_percentage: int = 50

class EmailCampaignUpdate(BaseModel):
    name: str = ""
    template_id: int | None = None
    subject_line: str = ""
    from_name: str = ""
    from_email: str = ""
    reply_to: str = ""
    target_filter: dict | None = None
    ab_enabled: bool | None = None
    ab_variant_b_subject: str = ""
    ab_variant_b_template_id: int | None = None
    ab_split_percentage: int | None = None

class EmailCampaignResponse(BaseModel):
    id: int
    name: str
    campaign_type: str = "warm"
    template_id: int | None = None
    subject_line: str = ""
    from_name: str = ""
    from_email: str = ""
    reply_to: str = ""
    target_filter: dict = {}
    ab_enabled: int = 0
    ab_variant_b_subject: str = ""
    ab_variant_b_template_id: int | None = None
    ab_split_percentage: int = 50
    status: str = "draft"
    scheduled_at: str | None = None
    total_recipients: int = 0
    sent_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    bounced_count: int = 0
    unsubscribed_count: int = 0
    created_at: str = ""
    updated_at: str = ""

class EmailCampaignListResponse(BaseModel):
    total: int
    campaigns: list[EmailCampaignResponse]

class CampaignScheduleRequest(BaseModel):
    scheduled_at: str

class CampaignTestRequest(BaseModel):
    test_email: str

class EmailSendResponse(BaseModel):
    id: int
    campaign_id: int
    recipient_email: str
    recipient_name: str = ""
    tracking_id: str
    ab_variant: str = "A"
    status: str = "queued"
    sent_at: str | None = None
    opened_at: str | None = None
    clicked_at: str | None = None
    open_count: int = 0
    click_count: int = 0

class EmailSendListResponse(BaseModel):
    total: int
    sends: list[EmailSendResponse]

class EmailSequenceCreate(BaseModel):
    name: str
    description: str = ""
    campaign_type: str = "warm"
    trigger_event: str = "manual"
    trigger_config: dict = {}

class EmailSequenceStepCreate(BaseModel):
    template_id: int
    subject_override: str = ""
    delay_days: int = 0
    delay_hours: int = 0
    condition_type: str = "always"

class EmailSequenceResponse(BaseModel):
    id: int
    name: str
    description: str = ""
    campaign_type: str = "warm"
    trigger_event: str = "manual"
    trigger_config: dict = {}
    is_active: int = 1
    steps: list[dict] = []
    enrollment_count: int = 0
    created_at: str = ""
    updated_at: str = ""

class EmailSequenceListResponse(BaseModel):
    total: int
    sequences: list[EmailSequenceResponse]

class SequenceEnrollRequest(BaseModel):
    contact_ids: list[int] = []
    lead_ids: list[int] = []

class EmailAnalyticsOverview(BaseModel):
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_bounced: int = 0
    total_unsubscribed: int = 0
    avg_open_rate: float = 0.0
    avg_click_rate: float = 0.0
    avg_bounce_rate: float = 0.0

class WarmVsColdComparison(BaseModel):
    warm: dict = {}
    cold: dict = {}

class ContactValidationResult(BaseModel):
    total: int = 0
    valid: int = 0
    invalid: int = 0
    disposable: int = 0
    role_based: int = 0
    no_mx: int = 0
    details: list[dict] = []


class DirectEmailRequest(BaseModel):
    to_email: str
    to_name: str = ""
    subject: str
    html_body: str
    text_body: str = ""
    from_name: str = ""
    from_email: str = ""
    reply_to: str = ""
