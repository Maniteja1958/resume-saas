from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, TypedDict

from app.agents import certificate_hunter, gap_analyzer, job_predictor, resume_parser, semantic_ats_checker
from app.services.event_bus import event_bus
from app.services.hashing import sha256_text
from app.services.storage import save_analysis, now_iso

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # LangGraph is optional at runtime for local demo convenience.
    StateGraph = None
    START = "START"
    END = "END"

MAX_CONTEXT_LOOPS = 2
MAX_GAP_ITERATIONS = 3


class AnalysisState(TypedDict, total=False):
    analysis_id: str
    resume_hash: str
    filename: str
    raw_text: str
    job_description: str | None
    target_missing_count: int

    parsed_resume: dict[str, Any]
    parse_confidence: float
    predicted_roles: dict[str, Any]
    selected_role: str
    predictor_needs_context: bool
    predictor_context_request: dict[str, Any] | None
    predictor_context_loop_count: int

    gap_iterations: int
    skill_gaps: dict[str, Any]
    certifications: dict[str, Any]
    ats_report: dict[str, Any]

    scores: dict[str, Any]
    metrics: dict[str, Any]
    agent_trace: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    status: str


async def run_analysis_pipeline(
    *,
    raw_text: str,
    filename: str,
    resume_hash: str,
    job_description: str | None = None,
    target_missing_count: int = 3,
    analysis_id: str | None = None,
) -> dict[str, Any]:
    analysis_id = analysis_id or f"ana_{uuid.uuid4().hex[:12]}"
    state: AnalysisState = {
        "analysis_id": analysis_id,
        "resume_hash": resume_hash,
        "filename": filename,
        "raw_text": raw_text,
        "job_description": job_description,
        "target_missing_count": target_missing_count,
        "predictor_context_loop_count": 0,
        "gap_iterations": 0,
        "metrics": {},
        "agent_trace": [],
        "errors": [],
        "status": "running",
    }

    started = time.perf_counter()
    await save_analysis(
        {
            "analysis_id": analysis_id,
            "created_at": now_iso(),
            "filename": filename,
            "resume_hash": resume_hash,
            "job_description_hash": sha256_text(job_description),
            "job_description_text": job_description,
            "status": "running",
            "agent_trace": [],
            "metrics": {},
        }
    )

    try:
        graph = build_graph()
        if graph is not None:
            final_state = await graph.ainvoke(state)
        else:
            final_state = await run_internal_state_machine(state)
        final_state["metrics"]["total_ms"] = int((time.perf_counter() - started) * 1000)
        final_state["status"] = "completed"
        final_state = await persist_analysis_node(final_state)
        return build_public_response(final_state)
    except Exception as exc:
        state.setdefault("errors", []).append({"message": str(exc), "type": type(exc).__name__})
        state["status"] = "failed"
        await save_analysis(build_analysis_document(state))
        await emit(state, "error", f"Analysis failed: {exc}", 100, {"error": str(exc)})
        raise


async def run_internal_state_machine(state: AnalysisState) -> AnalysisState:
    state = await parse_resume_node(state)
    while True:
        state = await predict_roles_node(state)
        if route_after_prediction(state) == "focused_reparse":
            state = await focused_reparse_node(state)
            continue
        break
    state = await parallel_post_prediction_node(state)
    return state


def build_graph():
    if StateGraph is None:
        return None
    graph = StateGraph(AnalysisState)
    graph.add_node("parse_resume", parse_resume_node)
    graph.add_node("focused_reparse", focused_reparse_node)
    graph.add_node("predict_roles", predict_roles_node)
    graph.add_node("parallel_post_prediction", parallel_post_prediction_node)

    graph.add_edge(START, "parse_resume")
    graph.add_edge("parse_resume", "predict_roles")
    graph.add_conditional_edges(
        "predict_roles",
        route_after_prediction,
        {
            "focused_reparse": "focused_reparse",
            "parallel_post_prediction": "parallel_post_prediction",
        },
    )
    graph.add_edge("focused_reparse", "predict_roles")
    graph.add_edge("parallel_post_prediction", END)
    return graph.compile()


async def emit(state: AnalysisState, event_type: str, message: str, progress: int | None = None, payload: dict[str, Any] | None = None) -> None:
    event = {
        "type": event_type,
        "message": message,
        "progress": progress,
        "payload": payload or {},
        "ts": time.time(),
    }
    state.setdefault("agent_trace", []).append(event)
    await event_bus.publish(state["analysis_id"], event)


async def parse_resume_node(state: AnalysisState) -> AnalysisState:
    await emit(state, "agent_started", "Parsing resume...", 10, {"agent": "Resume Parser"})
    started = time.perf_counter()
    parsed = await resume_parser.aparse(state.get("raw_text", ""))
    confidence = compute_parse_confidence(parsed)
    state["parsed_resume"] = parsed
    state["parse_confidence"] = confidence
    state.setdefault("metrics", {})["resume_parser_ms"] = int((time.perf_counter() - started) * 1000)
    await emit(
        state,
        "agent_completed",
        "Resume parsed",
        25,
        {"agent": "Resume Parser", "skills_found": len(parsed.get("skills", [])), "confidence": confidence},
    )
    return state


async def focused_reparse_node(state: AnalysisState) -> AnalysisState:
    request = state.get("predictor_context_request") or {}
    await emit(
        state,
        "agent_started",
        "Job Predictor requested more parser context...",
        32,
        {"agent": "Resume Parser", "reason": request.get("reason"), "fields": request.get("fields", [])},
    )
    enriched = await resume_parser.aparse(
        state.get("raw_text", ""),
        focus_fields=request.get("fields", []),
        existing=state.get("parsed_resume"),
    )
    state["parsed_resume"] = enriched
    state["predictor_context_loop_count"] = state.get("predictor_context_loop_count", 0) + 1
    await emit(state, "agent_completed", "Additional resume context merged", 35, {"agent": "Resume Parser"})
    return state


async def predict_roles_node(state: AnalysisState) -> AnalysisState:
    await emit(state, "agent_started", "Predicting best-fit roles...", 38, {"agent": "Job Predictor"})
    started = time.perf_counter()
    prediction = await job_predictor.apredict(state.get("parsed_resume", {}))
    needs_context, request = job_predictor.should_request_more_context(state.get("parsed_resume", {}), prediction)
    if state.get("predictor_context_loop_count", 0) >= MAX_CONTEXT_LOOPS:
        needs_context = False

    state["predicted_roles"] = prediction
    state["selected_role"] = pick_top_role(prediction)
    state["predictor_needs_context"] = needs_context
    state["predictor_context_request"] = request
    state.setdefault("metrics", {})["job_predictor_ms"] = int((time.perf_counter() - started) * 1000)

    await emit(
        state,
        "agent_completed",
        "Roles predicted",
        45,
        {"agent": "Job Predictor", "top_role": state["selected_role"], "needs_more_context": needs_context},
    )
    return state


def route_after_prediction(state: AnalysisState) -> str:
    if state.get("predictor_needs_context"):
        return "focused_reparse"
    return "parallel_post_prediction"


async def parallel_post_prediction_node(state: AnalysisState) -> AnalysisState:
    await emit(state, "parallel_started", "Running ATS checker and gap analysis in parallel...", 50)
    started = time.perf_counter()

    ats_task = semantic_ats_checker.acheck(state.get("parsed_resume", {}), state.get("job_description"))
    gap_task = run_gap_cert_branch(state)
    ats_report, gap_state = await asyncio.gather(ats_task, gap_task)

    state["ats_report"] = ats_report
    state["skill_gaps"] = gap_state.get("skill_gaps", {})
    state["certifications"] = gap_state.get("certifications", {"recommendations": []})
    state["gap_iterations"] = gap_state.get("gap_iterations", state.get("gap_iterations", 0))
    state.setdefault("metrics", {})["parallel_post_prediction_ms"] = int((time.perf_counter() - started) * 1000)
    state["scores"] = compute_scores(state)

    await emit(
        state,
        "parallel_completed",
        "ATS and gap analysis completed",
        85,
        {"ats_score": ats_report.get("ats_score"), "missing_skills": len(state["skill_gaps"].get("missing_skills", []))},
    )
    return state


async def run_gap_cert_branch(state: AnalysisState) -> AnalysisState:
    local = dict(state)
    previous = None
    while True:
        await emit(local, "agent_started", "Analyzing skill gaps...", 58, {"agent": "Gap Analyzer", "iteration": local.get("gap_iterations", 0) + 1})
        gaps = await gap_analyzer.aanalyze(
            resume_data=local.get("parsed_resume", {}),
            predicted_role=local.get("selected_role"),
            job_description=local.get("job_description"),
            min_missing=local.get("target_missing_count", 3),
            previous_gaps=previous,
        )
        local["skill_gaps"] = gaps
        local["gap_iterations"] = local.get("gap_iterations", 0) + 1
        missing_count = len(gaps.get("missing_skills", []))
        await emit(local, "agent_completed", "Gap analysis pass completed", 66, {"agent": "Gap Analyzer", "missing_count": missing_count, "iteration": local["gap_iterations"]})

        if missing_count == 0:
            await emit(local, "agent_skipped", "No gaps found, skipping certificate search", 78, {"agent": "Certificate Hunter", "reason": "zero_missing_skills"})
            local["certifications"] = {"recommendations": []}
            return local
        if missing_count >= local.get("target_missing_count", 3) or local["gap_iterations"] >= MAX_GAP_ITERATIONS:
            break
        previous = gaps
        await emit(local, "agent_loop", "Gap Analyzer is broadening search for more specific gaps...", 69, {"agent": "Gap Analyzer"})

    await emit(local, "agent_started", "Finding targeted certifications...", 74, {"agent": "Certificate Hunter"})
    certs = await certificate_hunter.afind(local.get("skill_gaps", {}))
    local["certifications"] = certs
    await emit(local, "agent_completed", "Certification recommendations ready", 80, {"agent": "Certificate Hunter", "count": len(certs.get("recommendations", []))})
    return local


async def persist_analysis_node(state: AnalysisState) -> AnalysisState:
    await emit(state, "agent_started", "Saving analysis...", 92, {"agent": "Persistence"})
    await save_analysis(build_analysis_document(state))
    await emit(state, "done", "Analysis complete", 100, {"analysis_id": state["analysis_id"]})
    return state


def build_analysis_document(state: AnalysisState) -> dict[str, Any]:
    return {
        "analysis_id": state.get("analysis_id"),
        "created_at": state.get("created_at") or now_iso(),
        "updated_at": now_iso(),
        "filename": state.get("filename"),
        "resume_hash": state.get("resume_hash"),
        "job_description_hash": sha256_text(state.get("job_description")),
        "job_description_text": state.get("job_description"),
        "parsed_resume": state.get("parsed_resume", {}),
        "predicted_roles": state.get("predicted_roles", {"predictions": []}),
        "skill_gaps": state.get("skill_gaps", {}),
        "certifications": state.get("certifications", {"recommendations": []}),
        "ats_report": state.get("ats_report", {}),
        "scores": state.get("scores", compute_scores(state)),
        "metrics": state.get("metrics", {}),
        "agent_trace": state.get("agent_trace", []),
        "errors": state.get("errors", []),
        "status": state.get("status", "completed"),
    }


def build_public_response(state: AnalysisState) -> dict[str, Any]:
    doc = build_analysis_document(state)
    return {
        "success": state.get("status") != "failed",
        "analysis_id": state.get("analysis_id"),
        "parsed_resume": doc["parsed_resume"],
        "predicted_roles": doc["predicted_roles"],
        "skill_gaps": doc["skill_gaps"],
        "certifications": doc["certifications"],
        "ats_report": doc["ats_report"],
        "scores": doc["scores"],
        "metrics": doc["metrics"],
        "agent_trace": doc["agent_trace"],
    }


def compute_parse_confidence(parsed: dict[str, Any]) -> float:
    checks = [
        bool(parsed.get("name")),
        bool(parsed.get("email")),
        bool(parsed.get("phone")),
        bool(parsed.get("skills")),
        bool(parsed.get("experience")),
        bool(parsed.get("education")),
    ]
    return round(sum(checks) / len(checks), 2)


def pick_top_role(prediction: dict[str, Any]) -> str:
    predictions = prediction.get("predictions", []) or []
    return predictions[0].get("role_name", "Backend Developer") if predictions else "Backend Developer"


def compute_scores(state: AnalysisState) -> dict[str, Any]:
    predictions = state.get("predicted_roles", {}).get("predictions", []) or []
    top = predictions[0] if predictions else {}
    ats = state.get("ats_report", {}) or {}
    gaps = state.get("skill_gaps", {}) or {}
    return {
        "ats_score": ats.get("ats_score", 0),
        "semantic_similarity": ats.get("semantic_similarity", 0),
        "top_role": top.get("role_name", state.get("selected_role")),
        "top_role_match": top.get("match_percentage", 0),
        "gap_count": len(gaps.get("missing_skills", []) or []),
    }
