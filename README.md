# Sparrow Interactive RAG Chatbot

A retrieval-augmented chatbot for Sparrow Interactive. It answers visitor questions from the company's website content, uploaded PDFs and a curated Golden QA set. It also captures and scores leads, and ships with an admin dashboard, email campaigns and a WhatsApp bridge.

## Repository layout

| Path | What it is |
|------|------------|
| `rag-chatbot/backend/` | FastAPI app: chat, RAG pipeline, ingestion, leads, analytics, email service, admin API |
| `rag-chatbot/frontend/` | Chat widget (HTML/CSS/JS) injected into the website |
| `rag-chatbot/admin-dashboard/` | React + Vite admin UI (leads, conversations, analytics, data, email, WhatsApp) |
| `rag-chatbot/whatsapp-bridge/` | Node.js WhatsApp bridge (Baileys) that forwards messages to the chatbot |
| `Chatbot/` | Offline mirror of the Sparrow websites; served with the widget and ingested on first run |
| `rag-chatbot/run.py` | Startup script (checks Qdrant, then launches uvicorn) |

## Tools you need

**Required**

| Tool | Version | Used for |
|------|---------|----------|
| Python | 3.10+ | Backend |
| Qdrant | latest | Vector database (Docker image or `qdrant.exe`) |
| Sarvam AI API key | – | LLM (`sarvam-105b` by default) |
| Git | – | Source control |

**Needed for specific features**

| Tool | Used for |
|------|----------|
| Node.js 18+ and npm | Building the admin dashboard; running the WhatsApp bridge |
| Docker | Easiest way to run Qdrant (optional if you use the binary) |
| Tesseract OCR | OCR for image-heavy PDFs (`pytesseract`) |
| Redis | Session storage (optional; falls back to in-memory) |
| SMTP account or Microsoft Graph app | Email alerts and campaigns |

Python dependencies are pinned in `rag-chatbot/requirements.txt`. Notable ones are FastAPI, uvicorn, `sarvamai`, `sentence-transformers`, `qdrant-client`, `pdfplumber`, `PyMuPDF` and `APScheduler`. The first run downloads two models from Hugging Face, `all-MiniLM-L6-v2` (embeddings) and `cross-encoder/ms-marco-MiniLM-L-6-v2` (reranker).

## Getting started

All commands run from `rag-chatbot/` unless noted.

### 1. Install Python dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
copy .env.example .env
```

Edit `.env` and set at least:

```
SARVAM_API_KEY=your-key-here
```

Other settings (all optional, defaults in `backend/config.py`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `SARVAM_MODEL` | `sarvam-105b` | LLM model id |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost` / `6333` | Qdrant location |
| `PORT` | `8003` | Backend port |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | Admin login. **Change these before deploying.** |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAILS` | empty | Lead alert emails |
| `EMAIL_PROVIDER` | `smtp` | `smtp` or `microsoft` (then set `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_SENDER_EMAIL`) |
| `REDIS_HOST` / `REDIS_PORT` | `localhost` / `6379` | Session store |

Never commit `.env`. It is git-ignored.

### 3. Start Qdrant

```powershell
# Docker
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# or the downloaded binary
.\qdrant.exe
```

### 4. Run the backend

```powershell
python run.py
```

`run.py` checks that Qdrant is reachable and then starts the server at `http://localhost:8003`. On the first run with an empty collection, the backend ingests the website knowledge and the `Chatbot/` mirror in the background. This takes a while and the server is usable straight away. Later runs skip this step.

Useful URLs:

- `http://localhost:8003/` serves the mirror website with the chat widget
- `http://localhost:8003/health` is a health check
- `http://localhost:8003/admin/` is the admin dashboard (needs step 5)

### 5. Build the admin dashboard

```powershell
cd admin-dashboard
npm install
npm run build        # output goes to admin-dashboard/dist, served at /admin
```

For live development use `npm run dev`. It runs at `http://localhost:5173/admin/` and proxies `/api` to the backend on port 8003.

### 6. (Optional) WhatsApp bridge

```powershell
cd whatsapp-bridge
npm install
npm start
```

The backend also tries to start the bridge on startup. On the first run, scan the QR code with WhatsApp. The bridge's status page is at `http://localhost:8004/status`.

## Testing

The test scripts in `rag-chatbot/` (`test_comprehensive.py`, `test_suites.py`, `test_live_system.py`, etc.) talk to a running server, so start Qdrant and the backend first, then run for example:

```powershell
python test_comprehensive.py
```

## Troubleshooting

- **`Cannot reach Qdrant`**: Qdrant isn't running on `QDRANT_HOST:QDRANT_PORT`. Start it (step 3).
- **Empty or missing answers**: check that `SARVAM_API_KEY` is set and valid, and that ingestion finished (see the `[Startup]` log lines).
- **`/admin/` returns 404**: the dashboard hasn't been built. Run `npm run build` in `admin-dashboard/`.
- **OCR fails on PDFs**: install Tesseract and update `TESSERACT_CMD` in `backend/pdf_parser.py`. It currently points at a Windows user-specific path.
- **git "dubious ownership" error on Windows**: run `git config --global --add safe.directory <repo path>`.
