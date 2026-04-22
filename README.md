# DDR Report Generator

AI-powered **Detailed Diagnostic Report (DDR)** generator that converts raw inspection and thermal PDFs into structured, client-ready reports.

## What It Does

```
Upload 2 PDFs → AI processes everything → Download DDR in DOCX + PDF + HTML
```

## Tech Stack

| Layer | Tool |
|---|---|
| Web Framework | FastAPI |
| PDF Ingestion | OpenDataLoader v2.0 + PyMuPDF |
| LLM | Groq API (Llama 3.3 70B) |
| DOCX Export | python-docx |
| PDF Export | WeasyPrint |
| HTML Export | Jinja2 |
| Validation | Pydantic v2 |

## Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/ddr-report-generator
cd ddr-report-generator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Add your GROQ_API_KEY from https://console.groq.com
```

### 3. Run
```bash
uvicorn app.main:app --reload
```

### 4. Open
```
http://localhost:8000        → Upload UI
http://localhost:8000/docs   → API docs
```

## Docker

```bash
docker-compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/upload` | Upload 2 PDFs, get job_id |
| GET | `/api/v1/status/{job_id}` | Poll processing status |
| GET | `/api/v1/report/{job_id}` | Get download links |
| GET | `/api/v1/report/{job_id}/preview` | Preview in browser |
| GET | `/api/v1/report/{job_id}/download/html` | Download HTML |
| GET | `/api/v1/report/{job_id}/download/docx` | Download DOCX |
| GET | `/api/v1/report/{job_id}/download/pdf` | Download PDF |
| GET | `/api/v1/health` | Health check |

## DDR Output Structure

1. **Property Issue Summary** — Executive overview
2. **Area-wise Observations** — Per-area findings with images
3. **Probable Root Cause** — Connected diagnosis
4. **Severity Assessment** — Low / Medium / High / Critical with reasoning
5. **Recommended Actions** — Immediate / Short-term / Long-term
6. **Additional Notes** — Extra observations
7. **Missing or Unclear Information** — Explicit gaps flagged

## Requirements

- Python 3.10+
- Java 11+ (for OpenDataLoader)
- Groq API key (free at console.groq.com)