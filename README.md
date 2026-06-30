# AuraAnalyze — Complete Resume Analysis Website

This is a complete full-stack resume-analysis SaaS demo with **separate backend and frontend projects**.

- `backend/` — FastAPI API, agent orchestration, semantic ATS scoring, MongoDB persistence fallback, SSE progress, PDF reports.
- `frontend/` — React + Vite cyber-themed UI with upload analysis, streaming progress, history, comparison, batch analysis, skill editor, radar chart, and PDF export.

## 1. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend runs at:

```txt
http://localhost:8000
```

Open API docs:

```txt
http://localhost:8000/docs
```

MongoDB is optional for local demo. If MongoDB is running, set `MONGODB_URI` in `.env`. If not, the backend falls back to in-memory storage so the app still works.

## 2. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```txt
http://localhost:5173
```

## 3. Main features

- Resume upload: PDF, DOCX, or TXT
- Agentic analysis pipeline with autonomous decisions
- Real-time streaming progress via Server-Sent Events
- Semantic ATS scoring instead of simple keyword regex
- MongoDB-ready history persistence
- PDF report export
- Resume version comparison
- Batch analysis against multiple job descriptions
- Paste job posting URL and extract JD text server-side
- Friendly fallback message when job boards block scraping with 403/anti-bot protection
- Editable skill tags and lightweight re-score
- Radar skill chart
- Side-by-side role comparison

## 4. Important endpoints

```txt
POST /analyses                         Start streaming analysis
GET  /analyses/{analysis_id}/events    SSE progress stream
GET  /analyses/{analysis_id}           Fetch stored result
POST /analyze                          Synchronous compatibility endpoint
GET  /history                          Past analyses
POST /compare                          Compare two resumes
POST /analyze-batch                    Rank one resume against many JDs
GET  /report/{analysis_id}             Download PDF report
POST /rescore                          Re-run ATS + gaps after skill edits
POST /job-description/fetch            Extract JD from URL
```

## 5. Demo flow

1. Start backend and frontend.
2. Upload a resume and paste a JD.
3. Watch the streaming agent timeline.
4. Review ATS score, role matches, skill gaps, certifications, and radar chart.
5. Export PDF.
6. Open History and show score trends.
7. Compare resume v1 vs v2.
8. Run Batch Analysis against multiple companies.

## 6. Notes

### About job URL fetching

Some job boards such as Wellfound, LinkedIn, Indeed, and Naukri may return `403 Forbidden` or render the job content only with browser JavaScript. The backend tries direct fetching with browser-like headers and a reader fallback, but it cannot bypass private/authenticated/anti-bot pages. If this happens, paste the job description manually into the textarea and run the analysis.

### Troubleshooting

If you still see the old raw `403 Forbidden` message or the frontend says `Lost connection to analysis stream`, stop and restart both servers after pulling/copying the latest files:

```bash
# backend
cd backend
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm run dev
```

The frontend now suppresses false SSE disconnect errors and falls back to polling `/analyses/{analysis_id}` if the live stream is interrupted.

This project is intentionally demo-friendly:

- It works without Claude or SerpAPI keys using local heuristic agents.
- It supports MongoDB when available but does not require it.
- The semantic ATS checker uses a synonym-aware semantic fallback so phrases like “backend JavaScript runtime” can match `Node.js`.
- The backend includes a LangGraph-compatible orchestration layer and falls back to an internal async state machine if LangGraph is not installed.
"# resume-saas" 
