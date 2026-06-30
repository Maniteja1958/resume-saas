from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from app.agents import certificate_hunter, gap_analyzer, job_predictor, resume_parser, semantic_ats_checker
from app.core.config import settings
from app.graphs.analysis_graph import run_analysis_pipeline
from app.schemas import JobUrlRequest, RescoreRequest
from app.services.comparison_service import compare_analyses
from app.services.event_bus import event_bus
from app.services.file_handler import read_upload
from app.services.hashing import sha256_bytes, sha256_text
from app.services.jd_extraction_service import JobDescriptionFetchError, fetch_job_description
from app.services.report_service import build_pdf_report
from app.services.storage import get_analysis, init_storage, list_history, save_analysis, update_analysis, now_iso

app = FastAPI(
    title="AuraAnalyze Resume Intelligence API",
    description="Agentic resume analysis backend with streaming progress, history, comparison, batch analysis, and PDF reports.",
    version="2.0.0",
)

# Local demo CORS: allow any frontend origin because students often run Vite
# from localhost, 127.0.0.1, LAN IPs, or cloud preview URLs. No cookies are used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await init_storage()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "AuraAnalyze backend running", "status": "success"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/analyses")
async def create_analysis(
    background_tasks: BackgroundTasks,
    resume_file: UploadFile = File(...),
    job_description: str | None = Form(None),
    target_missing_count: int = Form(3),
) -> dict[str, Any]:
    content, filename, raw_text = await read_upload(resume_file)
    resume_hash = sha256_bytes(content)
    analysis_id = f"ana_{uuid.uuid4().hex[:12]}"

    await save_analysis(
        {
            "analysis_id": analysis_id,
            "created_at": now_iso(),
            "filename": filename,
            "resume_hash": resume_hash,
            "job_description_hash": sha256_text(job_description),
            "job_description_text": job_description,
            "status": "queued",
            "agent_trace": [],
            "metrics": {},
        }
    )
    await event_bus.publish(
        analysis_id,
        {"type": "queued", "message": "Upload received. Analysis queued...", "progress": 2, "payload": {"filename": filename}},
    )

    background_tasks.add_task(
        safe_run_analysis,
        raw_text=raw_text,
        filename=filename,
        resume_hash=resume_hash,
        job_description=job_description,
        target_missing_count=target_missing_count,
        analysis_id=analysis_id,
    )

    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "events_url": f"/analyses/{analysis_id}/events",
        "result_url": f"/analyses/{analysis_id}",
    }


async def safe_run_analysis(**kwargs: Any) -> None:
    try:
        await run_analysis_pipeline(**kwargs)
    except Exception as exc:
        analysis_id = kwargs.get("analysis_id")
        if analysis_id:
            await update_analysis(analysis_id, {"status": "failed", "errors": [{"message": str(exc)}]})
            await event_bus.publish(
                analysis_id,
                {"type": "error", "message": f"Analysis failed: {exc}", "progress": 100, "payload": {"error": str(exc)}},
            )


@app.get("/analyses/{analysis_id}/events")
async def analysis_events(analysis_id: str) -> StreamingResponse:
    async def generator():
        async for event in event_bus.subscribe(analysis_id):
            # Do not use SSE event name "error" for application errors because
            # browsers reserve EventSource.onerror for network/connection errors.
            event_name = "done" if event.get("type") == "done" else "agent_error" if event.get("type") == "error" else "agent_update"
            yield f"event: {event_name}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/analyses/{analysis_id}")
async def get_analysis_result(analysis_id: str) -> dict[str, Any]:
    analysis = await get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.post("/analyze")
async def analyze_compat(
    resume_file: UploadFile = File(...),
    job_description: str | None = Form(None),
    target_missing_count: int = Form(3),
) -> dict[str, Any]:
    content, filename, raw_text = await read_upload(resume_file)
    return await run_analysis_pipeline(
        raw_text=raw_text,
        filename=filename,
        resume_hash=sha256_bytes(content),
        job_description=job_description,
        target_missing_count=target_missing_count,
    )


@app.get("/history")
async def history(
    limit: int = 20,
    offset: int = 0,
    resume_hash: str | None = None,
    top_role: str | None = None,
) -> dict[str, Any]:
    return await list_history(limit=limit, offset=offset, resume_hash=resume_hash, top_role=top_role)


@app.post("/compare")
async def compare_resumes(
    resume_a: UploadFile | None = File(None),
    resume_b: UploadFile | None = File(None),
    analysis_id_a: str | None = Form(None),
    analysis_id_b: str | None = Form(None),
    job_description: str | None = Form(None),
) -> dict[str, Any]:
    analysis_a = await get_analysis(analysis_id_a) if analysis_id_a else None
    analysis_b = await get_analysis(analysis_id_b) if analysis_id_b else None

    tasks = []
    labels = []
    if analysis_a is None:
        if not resume_a:
            raise HTTPException(status_code=400, detail="resume_a or analysis_id_a is required")
        content_a, filename_a, raw_a = await read_upload(resume_a)
        tasks.append(run_analysis_pipeline(raw_text=raw_a, filename=filename_a, resume_hash=sha256_bytes(content_a), job_description=job_description))
        labels.append("a")
    if analysis_b is None:
        if not resume_b:
            raise HTTPException(status_code=400, detail="resume_b or analysis_id_b is required")
        content_b, filename_b, raw_b = await read_upload(resume_b)
        tasks.append(run_analysis_pipeline(raw_text=raw_b, filename=filename_b, resume_hash=sha256_bytes(content_b), job_description=job_description))
        labels.append("b")

    if tasks:
        results = await asyncio.gather(*tasks)
        for label, result in zip(labels, results):
            full = await get_analysis(result["analysis_id"])
            if label == "a":
                analysis_a = full
            else:
                analysis_b = full

    if not analysis_a or not analysis_b:
        raise HTTPException(status_code=404, detail="Could not load both analyses")

    return {
        "success": True,
        "analysis_a": _mini_analysis(analysis_a),
        "analysis_b": _mini_analysis(analysis_b),
        "diff": compare_analyses(analysis_a, analysis_b),
    }


@app.post("/analyze-batch")
async def analyze_batch(
    resume_file: UploadFile = File(...),
    job_descriptions_json: str = Form(...),
) -> dict[str, Any]:
    try:
        job_descriptions = json.loads(job_descriptions_json)
        if not isinstance(job_descriptions, list):
            raise ValueError("job_descriptions_json must be a list")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid job_descriptions_json: {exc}")

    content, filename, raw_text = await read_upload(resume_file)
    parsed = await resume_parser.aparse(raw_text)
    predictions = await job_predictor.apredict(parsed)
    top_role = predictions.get("predictions", [{}])[0].get("role_name", "Backend Developer")

    async def analyze_one(index: int, jd: dict[str, Any]) -> dict[str, Any]:
        text = jd.get("text", "") if isinstance(jd, dict) else str(jd)
        ats, gaps = await asyncio.gather(
            semantic_ats_checker.acheck(parsed, text),
            gap_analyzer.aanalyze(parsed, top_role, text, 3),
        )
        fit_score = int(ats.get("ats_score", 0) * 0.75 + max(0, 100 - len(gaps.get("missing_skills", [])) * 10) * 0.25)
        return {
            "rank": 0,
            "company": jd.get("company", f"JD {index + 1}") if isinstance(jd, dict) else f"JD {index + 1}",
            "title": jd.get("title", "Target Role") if isinstance(jd, dict) else "Target Role",
            "fit_score": fit_score,
            "ats_score": ats.get("ats_score", 0),
            "semantic_similarity": ats.get("semantic_similarity", 0),
            "top_missing_skills": gaps.get("missing_skills", [])[:5],
            "matched_skills": ats.get("matched_keywords", [])[:8],
        }

    results = await asyncio.gather(*[analyze_one(i, jd) for i, jd in enumerate(job_descriptions)])
    results.sort(key=lambda x: x["fit_score"], reverse=True)
    for i, result in enumerate(results, start=1):
        result["rank"] = i

    return {"resume_hash": sha256_bytes(content), "filename": filename, "ranked_matches": results}


@app.post("/rescore")
async def rescore(request: RescoreRequest) -> dict[str, Any]:
    analysis = await get_analysis(request.analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    resume_data = request.resume_data
    job_description = request.job_description or analysis.get("job_description_text")
    top_role = analysis.get("scores", {}).get("top_role") or "Backend Developer"

    ats, gaps = await asyncio.gather(
        semantic_ats_checker.acheck(resume_data, job_description),
        gap_analyzer.aanalyze(resume_data, top_role, job_description, 3),
    )
    certs = {"recommendations": []} if not gaps.get("missing_skills") else await certificate_hunter.afind(gaps)

    predictions = analysis.get("predicted_roles", {"predictions": []})
    scores = {
        "ats_score": ats.get("ats_score", 0),
        "semantic_similarity": ats.get("semantic_similarity", 0),
        "top_role": top_role,
        "top_role_match": (predictions.get("predictions") or [{}])[0].get("match_percentage", 0),
        "gap_count": len(gaps.get("missing_skills", [])),
    }

    await update_analysis(
        request.analysis_id,
        {
            "parsed_resume": resume_data,
            "ats_report": ats,
            "skill_gaps": gaps,
            "certifications": certs,
            "scores": scores,
            "status": "completed",
        },
    )

    return {
        "analysis_id": request.analysis_id,
        "rescore_id": f"rescore_{uuid.uuid4().hex[:8]}",
        "ats_report": ats,
        "skill_gaps": gaps,
        "certifications": certs,
        "scores": scores,
    }


@app.post("/job-description/fetch")
async def fetch_jd(request: JobUrlRequest) -> dict[str, str]:
    try:
        return await fetch_job_description(request.url)
    except JobDescriptionFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch job description: {exc}")


@app.get("/report/{analysis_id}")
async def report(analysis_id: str) -> Response:
    analysis = await get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    pdf = build_pdf_report(analysis)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="resume-analysis-{analysis_id}.pdf"'},
    )


def _mini_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "analysis_id": analysis.get("analysis_id"),
        "filename": analysis.get("filename"),
        "ats_score": analysis.get("scores", {}).get("ats_score", 0),
        "top_role": analysis.get("scores", {}).get("top_role"),
        "top_role_match": analysis.get("scores", {}).get("top_role_match"),
    }
