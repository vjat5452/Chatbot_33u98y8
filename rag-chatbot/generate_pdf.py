"""Generate chatbotfilessystem.pdf with full project architecture documentation."""

from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Sparrowi RAG Chatbot - File System & Architecture", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 60, 120)
        self.ln(4)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.ln(2)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def bold_text(self, text):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def code_block(self, text):
        self.set_font("Courier", "", 8)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.set_x(x + 5)
        self.multi_cell(180, 4.5, text, fill=True)
        self.ln(2)

    def table_row(self, col1, col2, widths=(55, 130), bold_first=False):
        self.set_font("Helvetica", "B" if bold_first else "", 8)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        y = self.get_y()
        self.set_xy(x, y)
        self.multi_cell(widths[0], 4.5, col1)
        h1 = self.get_y() - y
        self.set_xy(x + widths[0], y)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(widths[1], 4.5, col2)
        h2 = self.get_y() - y
        max_h = max(h1, h2)
        self.set_y(y + max_h + 1)

    def table_header(self, col1, col2, widths=(55, 130)):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(220, 230, 245)
        self.set_text_color(20, 20, 20)
        y = self.get_y()
        self.cell(widths[0], 6, col1, fill=True)
        self.cell(widths[1], 6, col2, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def check_page_break(self, h=30):
        if self.get_y() + h > 270:
            self.add_page()


pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# ── Title Page ──
pdf.ln(30)
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(20, 60, 120)
pdf.cell(0, 15, "Sparrowi RAG Chatbot", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 16)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 10, "Complete File System & Architecture Documentation", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_font("Helvetica", "", 11)
pdf.cell(0, 8, "Project: Sparrow Interactive AI Sales Assistant", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "Location: C:\\Users\\User\\Desktop\\Chatbot\\", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "Total Size: 1.5 GB | 92 Qdrant Chunks | Python + React + Node.js", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(15)
pdf.set_font("Helvetica", "I", 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 8, "Generated: March 2026", align="C", new_x="LMARGIN", new_y="NEXT")

# ── Page 2: Project Overview ──
pdf.add_page()
pdf.section_title("1. Project Overview")
pdf.body_text(
    "This project is an AI-powered RAG (Retrieval-Augmented Generation) sales chatbot built for Sparrow Interactive Pvt Ltd, "
    "a leading experiential technology and phygital solutions company specializing in real estate. The chatbot is embedded on the "
    "company's website (sparrowi.com) and also available via WhatsApp. It answers customer questions using company knowledge "
    "retrieved from a vector database (Qdrant), processed through a re-ranker, and answered by the Sarvam AI LLM."
)

pdf.sub_title("Technology Stack")
techs = [
    ("Backend Framework", "FastAPI (Python) running on Uvicorn, port 8003"),
    ("LLM / AI Model", "Sarvam AI (sarvam-m model) via sarvamai SDK"),
    ("Embedding Model", "all-MiniLM-L6-v2 (sentence-transformers) - 384 dimensions"),
    ("Re-ranker Model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
    ("Vector Database", "Qdrant (local binary qdrant.exe) on port 6333"),
    ("Relational Database", "SQLite (sparrowi.db) - leads, conversations, analytics"),
    ("Session Storage", "Redis (optional, falls back to in-memory OrderedDict)"),
    ("Frontend Widget", "Vanilla HTML/CSS/JS chatbot widget injected into website"),
    ("Admin Dashboard", "React + Vite + TailwindCSS + shadcn/ui"),
    ("WhatsApp Bridge", "Node.js + @whiskeysockets/baileys on port 8004"),
    ("PDF Parsing", "pdfplumber + PyPDF2 + Tesseract OCR (PyMuPDF)"),
    ("Web Scraping", "httpx + BeautifulSoup4"),
    ("Email System", "SMTP (Gmail) + Microsoft Graph API + Jinja2 templates"),
]
pdf.table_header("Component", "Technology")
for comp, tech in techs:
    pdf.check_page_break(12)
    pdf.table_row(comp, tech, bold_first=True)

# ── Top-Level Directory ──
pdf.add_page()
pdf.section_title("2. Top-Level Directory Structure")
pdf.code_block(
    "C:\\Users\\User\\Desktop\\Chatbot\\          (1.5 GB total)\n"
    "|-- Chatbot/                238 MB   Scraped mirror of www.sparrowi.com (HTTrack)\n"
    "|-- rag-chatbot/            1.3 GB   The main application\n"
    "|-- .claude/                          Claude Code project memory\n"
    "|-- index.html                        HTTrack mirror index page\n"
    "|-- backblue.gif, fade.gif            HTTrack UI assets\n"
    "+-- Chatbot.whtt                      HTTrack project file"
)

pdf.sub_title("rag-chatbot/ Directory (Main Application)")
pdf.code_block(
    "rag-chatbot/                          (1.3 GB)\n"
    "|-- backend/           1 MB     Python backend (FastAPI) - all server logic\n"
    "|-- frontend/          124 KB   Chatbot widget UI files\n"
    "|-- admin-dashboard/   140 MB   React admin panel (includes node_modules)\n"
    "|-- whatsapp-bridge/   54 MB    WhatsApp integration (Node.js)\n"
    "|-- data/              17 MB    SQLite database\n"
    "|-- venv/              962 MB   Python virtual environment\n"
    "|-- storage/           2 KB     Qdrant on-disk storage (EMPTY collections)\n"
    "|-- snapshots/         0        Qdrant snapshots (empty)\n"
    "|-- qdrant.exe         70 MB    Qdrant vector database binary\n"
    "|-- .env                        API keys and configuration\n"
    "|-- run.py                      Startup script\n"
    "|-- requirements.txt            Python dependencies\n"
    "|-- test_*.py (many)            Test suites\n"
    "+-- .qdrant-initialized         Setup flag file"
)

# ── Backend Files ──
pdf.add_page()
pdf.section_title("3. Backend Directory (backend/)")
pdf.body_text("The backend is the brain of the application. All Python source files live here.")

files = [
    ("main.py (60 KB)", "FastAPI application with ALL API endpoints:\n"
     "- /chat - Main chat endpoint (receives user message, returns AI response)\n"
     "- /ingest - Upload SQL/PDF files for ingestion into Qdrant\n"
     "- /scrape - Trigger live website scraping\n"
     "- /health - Health check endpoint\n"
     "- /admin/* - Admin dashboard API (leads, analytics, settings)\n"
     "- /api/leads/* - Lead management CRUD\n"
     "- /api/email/* - Email campaign management\n"
     "- Serves the scraped website mirror with chatbot widget injected into every page"),

    ("rag_pipeline.py (104 KB)", "Core RAG orchestration - the largest and most important file:\n"
     "1. Receives user query\n"
     "2. Checks for greetings/small-talk (instant response, no API call)\n"
     "3. Embeds query using MiniLM\n"
     "4. Vector search in Qdrant (cosine similarity)\n"
     "5. Keyword search in Qdrant (IDF-weighted)\n"
     "6. Merges and deduplicates results\n"
     "7. Re-ranks with cross-encoder\n"
     "8. Builds context from top chunks\n"
     "9. Calls Sarvam AI with context + conversation history\n"
     "10. Returns response with sources and follow-up suggestions\n"
     "Also handles: response caching, grounding verification, conversation memory"),

    ("config.py (2.6 KB)", "Loads .env file and exposes all settings via Pydantic BaseSettings:\n"
     "Sarvam AI key, Qdrant host/port/collection, embedding model, server host/port,\n"
     "RAG parameters (top_k=6, min_score=0.35), reranker settings, scraper config,\n"
     "Redis config, SQLite path, SMTP/Microsoft Graph email settings, lead scoring thresholds"),

    ("claude_client.py (3.9 KB)", "Wrapper around Sarvam AI SDK (not Claude despite the filename).\n"
     "- ask_with_history(): Sends messages with conversation history (last 4 turns)\n"
     "- ask(): Single message shorthand\n"
     "- Timeout handling: 15s for answers, 8s for short decision calls\n"
     "- Strips <think> tags from model output"),

    ("embeddings.py (1 KB)", "Sentence-transformers wrapper:\n"
     "- Lazy-loads all-MiniLM-L6-v2 model on first use\n"
     "- embed_text(): Single text embedding (cached with LRU, max 4096)\n"
     "- embed_batch(): Batch embedding for ingestion (batch_size=64)\n"
     "- Output: 384-dimensional normalized vectors"),

    ("vector_store.py (10.4 KB)", "Qdrant client with all database operations:\n"
     "- ensure_collection(): Creates 'sql_chunks' collection if missing\n"
     "- upsert_chunks(): Inserts vectors in batches of 100\n"
     "- search(): Cosine similarity search with score filtering and dedup\n"
     "- keyword_search(): Full-text keyword search with IDF weighting and 10-min cache\n"
     "- reset_collection(): Clears all data\n"
     "- delete_by_table(): Deletes chunks by source table name"),

    ("reranker.py (1.9 KB)", "Cross-encoder re-ranker for precision:\n"
     "- Lazy-loads cross-encoder/ms-marco-MiniLM-L-6-v2\n"
     "- Scores (query, chunk) pairs with the cross-encoder\n"
     "- Filters results below min score threshold (-5.0)\n"
     "- Returns top_k=3 most relevant chunks"),

    ("chunker.py (8.8 KB)", "Text chunking engine:\n"
     "- Converts SQL tables, PDF pages, and website text into Chunk objects\n"
     "- Max 1500 chars per chunk, min 60 chars (skip near-empty)\n"
     "- Splits by paragraph breaks, then newlines, then sentences\n"
     "- Deterministic chunk IDs via SHA256 hashing\n"
     "- Chunk types: schema, rows, summary, pdf_page, pdf_section, website, golden_qa"),

    ("web_scraper.py (10.4 KB)", "Website crawler:\n"
     "- Crawls sparrowi.com using httpx + BeautifulSoup\n"
     "- Extracts text content + image metadata (alt text, figcaptions)\n"
     "- Produces Chunk objects for vector ingestion\n"
     "- Configurable: max 50 pages, 30s timeout per page"),

    ("website_knowledge.py (15 KB)", "Pre-built hardcoded knowledge chunks:\n"
     "- Company overview, services (5 core services), team structure\n"
     "- Office locations (India, UAE, Oman, Africa)\n"
     "- Client lists by zone (North, West, South)\n"
     "- Contact information, social media links\n"
     "- Auto-ingested into Qdrant on every startup as baseline knowledge"),

    ("database.py (42 KB)", "SQLite database layer with tables for:\n"
     "- leads: Customer leads with scoring (name, email, phone, score, status)\n"
     "- conversations: Full chat history per session\n"
     "- analytics_events: Event tracking (chat_opened, message_sent, etc.)\n"
     "- feedback: User thumbs up/down votes on responses\n"
     "- golden_qa: Curated Q&A pairs for high-quality answers\n"
     "- email_contacts, email_templates, email_campaigns, email_sequences\n"
     "- issues: Bug/issue tracking"),

    ("lead_capture.py (22 KB)", "Sales lead detection engine:\n"
     "- Regex extraction of emails and phone numbers from messages\n"
     "- Lead scoring: hot (70+), qualified (40+), new\n"
     "- Intent classification for purchase signals\n"
     "- Supports international phone formats (India, UAE, UK, US, Oman)"),

    ("session_store.py (5.6 KB)", "Conversation session management:\n"
     "- Tries Redis first (host:6379), falls back to in-memory OrderedDict\n"
     "- Stores conversation history per session_id\n"
     "- Stores feedback (upvote/downvote) per message\n"
     "- TTL: 1 hour per session"),

    ("analytics.py (2.5 KB)", "Event tracking wrapper:\n"
     "- track_chat_opened(), track_message_sent(), track_suggestion_clicked()\n"
     "- Writes events to SQLite via database.py"),

    ("notifications.py (6.7 KB)", "Email alert system:\n"
     "- Sends SMTP email alerts when hot leads are captured\n"
     "- Runs in background thread to not block API requests"),

    ("sql_parser.py (5.6 KB)", "SQL dump file parser:\n"
     "- Extracts CREATE TABLE schemas (column names, types, constraints)\n"
     "- Extracts INSERT INTO row data\n"
     "- Returns structured ParsedTable objects"),

    ("pdf_parser.py (5.8 KB)", "PDF text extraction:\n"
     "- Primary: pdfplumber for high-quality text\n"
     "- Fallback: PyPDF2 for simpler PDFs\n"
     "- OCR: pytesseract + PyMuPDF for image-heavy pages\n"
     "- Text cleaning to fix extraction artifacts"),

    ("models.py (9.6 KB)", "Pydantic models for all API request/response schemas:\n"
     "ChatRequest, ChatResponse, LeadResponse, EmailCampaignCreate, etc."),

    ("email/ directory", "Full email marketing module:\n"
     "- contacts.py: Email contact CRUD\n"
     "- templates.py: Jinja2 email templates with variable substitution\n"
     "- campaigns.py: Campaign management (create, schedule, send)\n"
     "- sequences.py: Multi-step drip email sequences\n"
     "- sender.py: Email sending via SMTP or Microsoft Graph API\n"
     "- tracking.py: Open/click tracking via pixel and redirect URLs\n"
     "- analytics_db.py: Email performance analytics\n"
     "- scheduler.py: APScheduler for timed sends"),
]

for fname, desc in files:
    pdf.check_page_break(40)
    pdf.sub_title(fname)
    pdf.body_text(desc)

# ── Frontend ──
pdf.add_page()
pdf.section_title("4. Frontend Directory (frontend/)")
pdf.body_text("The chatbot widget UI that gets embedded into the website pages.")

fe_files = [
    ("chatbot-widget.html (6.7 KB)", "Embeddable HTML snippet containing the chat widget markup. Gets injected "
     "by main.py before </body> in every scraped website page served by the backend."),
    ("app.js (38 KB)", "Full chatbot UI logic: message rendering, session management, typing indicators, "
     "suggestion chips, lead capture form display, auto-scroll, and API communication with /chat endpoint."),
    ("chatbot-widget.css (27 KB)", "Complete widget styling - chat bubble, message bubbles, input area, "
     "suggestion chips, lead forms, animations, responsive design."),
    ("index.html (6.9 KB)", "Standalone chatbot page (for testing outside the website mirror)."),
    ("style.css (22 KB)", "Standalone page styling."),
    ("logo.png, sparrow-fab.png", "Sparrow Interactive branding assets used in the widget."),
]
for fname, desc in fe_files:
    pdf.check_page_break(15)
    pdf.table_row(fname, desc, widths=(60, 125), bold_first=True)

# ── Admin Dashboard ──
pdf.section_title("5. Admin Dashboard (admin-dashboard/)")
pdf.body_text(
    "React single-page application built with Vite + TailwindCSS + shadcn/ui. "
    "Built output lives in admin-dashboard/dist/ and is served by FastAPI at /admin."
)
admin_pages = [
    ("Dashboard.jsx", "Overview stats: total leads, conversations, messages, conversion rates"),
    ("Leads.jsx / LeadView.jsx", "Lead management: view list, individual lead details, scoring, status updates, CSV export"),
    ("Conversations.jsx", "Chat history viewer with full message threads per session"),
    ("Analytics.jsx", "Charts and metrics: daily messages, top topics, response times"),
    ("GoldenQA.jsx", "Manage curated Q&A pairs that get ingested as high-priority chunks into Qdrant"),
    ("Issues.jsx", "Bug/issue tracker for chatbot problems"),
    ("Settings.jsx", "Admin configuration panel"),
    ("email/ pages", "Email campaign management: contacts, templates, campaigns, sequences, analytics"),
    ("whatsapp/ pages", "WhatsApp integration status and management"),
]
pdf.table_header("Page", "Purpose")
for page, purpose in admin_pages:
    pdf.check_page_break(12)
    pdf.table_row(page, purpose, bold_first=True)

# ── WhatsApp Bridge ──
pdf.add_page()
pdf.section_title("6. WhatsApp Bridge (whatsapp-bridge/)")
pdf.body_text(
    "Node.js service using @whiskeysockets/baileys (unofficial WhatsApp Web API). "
    "Runs on port 8004. Connects to WhatsApp via QR code scan, then acts as a bridge:"
)
pdf.code_block(
    "WhatsApp User sends message\n"
    "        |\n"
    "        v\n"
    "whatsapp-bridge/server.js (port 8004)\n"
    "        |\n"
    "        | POST /chat with message + session_id\n"
    "        v\n"
    "FastAPI backend (port 8003)\n"
    "        |\n"
    "        | RAG pipeline -> Sarvam AI -> response\n"
    "        v\n"
    "whatsapp-bridge strips markdown, sends plain text back to WhatsApp"
)
wa_files = [
    ("server.js (6.2 KB)", "Main bridge: QR connection, message handler, markdown stripping, health endpoint"),
    ("auth_info/", "WhatsApp session credentials persisted across restarts"),
    ("node_modules/", "baileys, qrcode-terminal, pino dependencies"),
]
for f, d in wa_files:
    pdf.table_row(f, d, bold_first=True)

# ── Data Directory ──
pdf.section_title("7. Data Directory (data/)")
data_files = [
    ("sparrowi.db (17 MB)", "SQLite database storing ALL persistent data:\n"
     "- leads table: captured leads with name, email, phone, score, status\n"
     "- conversations table: every chat message (role, content, timestamp)\n"
     "- analytics_events: user behavior tracking\n"
     "- feedback: upvote/downvote on bot responses\n"
     "- golden_qa: curated Q&A pairs for reliable answers\n"
     "- email_contacts, email_templates, email_campaigns, email_sequences\n"
     "- issues: reported problems"),
    ("sample.sql (75 bytes)", "Example SQL dump file for testing the ingestion pipeline"),
]
for f, d in data_files:
    pdf.check_page_break(25)
    pdf.sub_title(f)
    pdf.body_text(d)

# ── Qdrant Storage ──
pdf.add_page()
pdf.section_title("8. Qdrant Vector Database")

pdf.sub_title("Binary: qdrant.exe (70 MB)")
pdf.body_text(
    "Standalone Qdrant binary that runs locally on port 6333. No Docker required. "
    "Stores vectors for semantic similarity search."
)

pdf.sub_title("Storage Directory: storage/")
pdf.code_block(
    "storage/\n"
    "|-- raft_state.json     Qdrant cluster state (single-node, term=0)\n"
    "|-- aliases/data.json   Collection aliases (empty: {})\n"
    "+-- collections/        EMPTY - no persistent collection data"
)

pdf.sub_title("Why Qdrant Shows 'Deactivated' / Empty Collections")
pdf.body_text(
    "The storage/collections/ directory is EMPTY. This is the key finding:\n\n"
    "Qdrant's on-disk persistence has NO saved collection data. When you previously ran "
    "qdrant.exe and saw 92 chunks, those were loaded IN-MEMORY during that session only. "
    "Once qdrant.exe was stopped, all vector data was lost.\n\n"
    "This is BY DESIGN in this project. The application re-ingests all data on every startup:\n"
    "1. website_knowledge.py hardcoded chunks (company info)\n"
    "2. Golden QA pairs from SQLite database\n"
    "3. Scraped website content from sparrowi.com\n\n"
    "So the chunks are rebuilt fresh each time the app starts. The storage directory being empty "
    "simply means Qdrant is not currently running. When you start qdrant.exe + run.py, all 92 "
    "chunks will be recreated automatically."
)

pdf.sub_title("Collection Details: sql_chunks")
pdf.table_header("Property", "Value")
chunk_info = [
    ("Collection Name", "sql_chunks"),
    ("Vector Dimensions", "384 (all-MiniLM-L6-v2 output)"),
    ("Distance Metric", "Cosine Similarity"),
    ("Total Points", "92 chunks"),
    ("Status (when running)", "green"),
]
for k, v in chunk_info:
    pdf.table_row(k, v, bold_first=True)

# ── Chunk Breakdown ──
pdf.sub_title("Chunk Breakdown by Source (92 Total)")

pdf.bold_text("Website Chunks (sparrowi.com) - ~68 chunks")
pdf.body_text(
    "Scraped from the live website. Includes:\n"
    "- Homepage, About Us, Contact Us, Blog pages\n"
    "- Service pages: Interactive Solutions, Immersive Experiences, Scale Models, Renders, "
    "Walkthroughs, Experiential Journeys, Architectural Visualization\n"
    "- Portfolio items: Mahindra Experience Centre, Ambuja Neotia Brand Centre, etc.\n"
    "- Blog posts: Jio World Convention Centre, Serum Institute collaboration, Sultan Haitham City\n"
    "- Zone client pages: North Zone (DLF, Ace, Gaurs), West Zone (Runwal, Paradise)"
)

pdf.bold_text("Golden QA Chunks - ~12 chunks")
pdf.body_text(
    "Pre-curated high-quality Q&A pairs stored in SQLite, ingested as chunks:\n"
    "- Company background and history\n"
    "- Services offered (5 core services)\n"
    "- Pricing and engagement process\n"
    "- Team structure and key personnel (Rashmi Kohli, Ashish Mahajan, Tarrun Kumaria, etc.)\n"
    "- Client relationship management\n"
    "- Project execution workflow\n"
    "- Contact information and office visits\n"
    "- Portfolio overview (2,500+ projects)"
)

pdf.bold_text("PDF Policy Chunks - ~12 chunks")
pdf.body_text(
    "Extracted from 'Updated Policy Document - Sparrow Interactive (2025).pdf':\n"
    "- Work hours and attendance (Mon-Sat, 0930-1830)\n"
    "- Leave policies: Privilege Leave, Casual Leave, Medical Leave\n"
    "- Compensatory offs for overtime work\n"
    "- Late coming penalties\n"
    "- Dinner/conveyance reimbursement for late work (after 2100 hrs)\n"
    "- Leave application procedures"
)

# ── Data Flow ──
pdf.add_page()
pdf.section_title("9. System Architecture & Data Flow")

pdf.sub_title("Startup Sequence")
pdf.code_block(
    "1. Start qdrant.exe            -> Qdrant listens on port 6333\n"
    "2. Run: python run.py          -> Checks Qdrant health\n"
    "3. FastAPI startup:            -> Launches uvicorn on port 8003\n"
    "   a. Init SQLite tables       -> Creates leads, conversations, etc.\n"
    "   b. Create Qdrant collection -> 'sql_chunks' (384-dim, cosine)\n"
    "   c. Ingest website_knowledge -> Hardcoded company info chunks\n"
    "   d. Ingest golden QA         -> Curated Q&A from SQLite\n"
    "   e. Ingest scraped website   -> Crawl sparrowi.com pages\n"
    "   f. Embed all chunks         -> all-MiniLM-L6-v2 (384-dim vectors)\n"
    "   g. Upsert to Qdrant         -> 92 vectors stored\n"
    "   h. Warm keyword cache       -> Pre-load all points for keyword search\n"
    "4. (Optional) Start WhatsApp   -> node server.js on port 8004"
)

pdf.sub_title("Chat Request Flow")
pdf.code_block(
    "User Message (widget or WhatsApp)\n"
    "        |\n"
    "        v\n"
    "POST /chat {query, session_id}\n"
    "        |\n"
    "        v\n"
    "[1] Check greetings/small-talk -> instant response (no API)\n"
    "        |\n"
    "        v\n"
    "[2] Check response cache -> return cached if hit\n"
    "        |\n"
    "        v\n"
    "[3] Embed query with all-MiniLM-L6-v2 (384-dim vector)\n"
    "        |\n"
    "        v\n"
    "[4] Parallel search:\n"
    "    - Vector search (Qdrant cosine, top_k=6, min_score=0.35)\n"
    "    - Keyword search (IDF-weighted, cached points)\n"
    "        |\n"
    "        v\n"
    "[5] Merge + deduplicate results\n"
    "        |\n"
    "        v\n"
    "[6] Re-rank with cross-encoder (ms-marco-MiniLM-L-6-v2)\n"
    "    Filter below -5.0 score, keep top 3\n"
    "        |\n"
    "        v\n"
    "[7] Build context (max 3000 chars from top chunks)\n"
    "        |\n"
    "        v\n"
    "[8] Call Sarvam AI (sarvam-m model)\n"
    "    System prompt + context + conversation history (last 4 turns)\n"
    "    Timeout: 15s for answers, 8s for decisions\n"
    "        |\n"
    "        v\n"
    "[9] Post-processing:\n"
    "    - Detect lead intent, extract contact info\n"
    "    - Score lead (hot/qualified/new)\n"
    "    - Generate follow-up suggestions\n"
    "    - Store in session + SQLite\n"
    "    - Send email alert if hot lead\n"
    "        |\n"
    "        v\n"
    "Return: {answer, sources, suggestions, lead_nudge}"
)

# ── Configuration ──
pdf.add_page()
pdf.section_title("10. Configuration (.env)")
pdf.body_text("All configuration is in rag-chatbot/.env, loaded via Pydantic BaseSettings:")

env_vars = [
    ("SARVAM_API_KEY", "Sarvam AI API key for LLM calls"),
    ("SARVAM_MODEL", "sarvam-m (the LLM model used)"),
    ("QDRANT_HOST", "localhost"),
    ("QDRANT_PORT", "6333"),
    ("QDRANT_COLLECTION", "sql_chunks"),
    ("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    ("HOST / PORT", "0.0.0.0:8003 (FastAPI server)"),
    ("EMAIL_PROVIDER", "microsoft (Microsoft Graph API)"),
    ("MS_TENANT_ID", "Azure AD tenant for email sending"),
    ("MS_CLIENT_ID", "Azure app registration client ID"),
    ("MS_CLIENT_SECRET", "Azure app secret (for Graph API auth)"),
    ("MS_SENDER_EMAIL", "rishi.sharma@sparrowi.com"),
    ("SMTP_HOST/PORT/USER", "Gmail SMTP (currently disabled)"),
    ("EMAIL_TRACKING_BASE_URL", "http://192.168.1.31:8003 (for open/click tracking)"),
]
pdf.table_header("Variable", "Value / Description")
for k, v in env_vars:
    pdf.check_page_break(10)
    pdf.table_row(k, v, bold_first=True)

# ── Dependencies ──
pdf.section_title("11. Python Dependencies (requirements.txt)")
deps = [
    ("fastapi==0.115.6", "Web framework for all API endpoints"),
    ("uvicorn[standard]==0.34.0", "ASGI server to run FastAPI"),
    ("sarvamai", "Sarvam AI SDK for LLM chat completions"),
    ("sentence-transformers==3.3.1", "Embedding model (MiniLM) and cross-encoder (re-ranker)"),
    ("qdrant-client==1.12.1", "Qdrant vector database client"),
    ("pydantic==2.10.4", "Data validation and settings management"),
    ("httpx==0.28.1", "HTTP client for web scraping and API calls"),
    ("beautifulsoup4==4.12.3", "HTML parsing for web scraper"),
    ("PyPDF2==3.0.1", "PDF text extraction (fallback)"),
    ("pdfplumber==0.11.9", "PDF text extraction (primary)"),
    ("PyMuPDF==1.25.3", "PDF rendering for OCR"),
    ("pytesseract==0.3.13", "OCR for image-heavy PDF pages"),
    ("Pillow==11.1.0", "Image processing for OCR"),
    ("redis==5.2.1", "Redis client for session storage"),
    ("APScheduler>=3.10.0", "Task scheduling for email campaigns"),
    ("msal>=1.28.0", "Microsoft Authentication Library for Graph API"),
    ("Jinja2>=3.1.0", "Email template rendering"),
    ("dnspython>=2.6.0", "DNS validation for email contacts"),
    ("dkimpy>=1.1.0", "DKIM email authentication"),
]
pdf.table_header("Package", "Purpose")
for pkg, purpose in deps:
    pdf.check_page_break(10)
    pdf.table_row(pkg, purpose, bold_first=True)

# ── Size Breakdown ──
pdf.add_page()
pdf.section_title("12. Disk Size Breakdown")

sizes = [
    ("venv/ (Python packages)", "962 MB", "All installed Python dependencies including PyTorch, transformers, etc."),
    ("admin-dashboard/", "140 MB", "React app including node_modules and built dist/"),
    ("qdrant.exe", "70 MB", "Qdrant vector database binary"),
    ("whatsapp-bridge/", "54 MB", "Node.js app with baileys and dependencies"),
    ("Chatbot/ (website mirror)", "238 MB", "HTTrack scraped copy of sparrowi.com (HTML, images, CSS, JS)"),
    ("data/sparrowi.db", "17 MB", "SQLite database with all persistent application data"),
    ("backend/", "~1 MB", "All Python source code (the actual application logic)"),
    ("frontend/", "124 KB", "Chatbot widget HTML, JS, CSS, and images"),
    ("storage/ (Qdrant)", "2 KB", "Qdrant on-disk storage (collections empty - data is in-memory)"),
    ("Test files", "~1 MB", "Various test scripts and result JSON files"),
]

pdf.table_header("Component", "Size")
for comp, size, _ in sizes:
    pdf.table_row(comp, size, bold_first=True)

pdf.ln(5)
pdf.bold_text("Total Project Size: 1.5 GB")
pdf.body_text(
    "Note: 96% of the disk space (1.44 GB) is consumed by dependencies (venv, node_modules, "
    "qdrant.exe, website mirror). The actual application source code is only ~2 MB."
)

# ── Test Files ──
pdf.section_title("13. Test Files")
pdf.body_text("Multiple test suites for quality assurance:")
tests = [
    ("test_chatbot.py", "Core chatbot functionality tests"),
    ("test_golden_qa.py", "Golden QA accuracy tests"),
    ("test_comprehensive_v2.py", "Comprehensive V2 test suite"),
    ("test_deep_inspection.py", "Deep inspection of responses"),
    ("test_complex.py / test_extreme.py", "Edge case and complex query tests"),
    ("stress_test_100.py / stress_test_hard.py", "Load and stress testing"),
    ("test_sales_bot.py / test_sales_layer_1000.py", "Sales bot layer testing"),
    ("run_100_queries.py", "Batch query runner for benchmarking"),
    ("test_100_conversations.py / test_200_sessions.py", "Multi-session conversation tests"),
]
for f, d in tests:
    pdf.table_row(f, d, bold_first=True)

# ── Summary ──
pdf.add_page()
pdf.section_title("14. Summary")
pdf.body_text(
    "The Sparrowi RAG Chatbot is a full-stack AI sales assistant with the following architecture:\n\n"
    "BACKEND: FastAPI Python server handling chat, ingestion, scraping, lead management, email campaigns, "
    "and serving the website mirror with embedded chatbot widget.\n\n"
    "AI PIPELINE: User queries are embedded (MiniLM), searched in Qdrant (vector + keyword), re-ranked "
    "(cross-encoder), and answered by Sarvam AI LLM with retrieved context.\n\n"
    "KNOWLEDGE BASE: 92 chunks in Qdrant from 3 sources: scraped website (~68), curated Q&A (~12), "
    "and company policy PDF (~12). All re-ingested on every startup.\n\n"
    "STORAGE: SQLite for leads/conversations/analytics/email. Redis (optional) for sessions. "
    "Qdrant for vectors (in-memory, rebuilt on startup).\n\n"
    "FRONTENDS: Embeddable chat widget (vanilla JS), React admin dashboard, WhatsApp bridge (Node.js).\n\n"
    "INTEGRATIONS: Sarvam AI (LLM), Microsoft Graph API (email), WhatsApp (baileys), "
    "Tesseract (OCR), SMTP (Gmail backup)."
)

# Save
output_path = r"C:\Users\User\Desktop\Chatbot\rag-chatbot\chatbotfilessystem.pdf"
pdf.output(output_path)
print(f"PDF saved to: {output_path}")
print(f"Pages: {pdf.page_no()}")
