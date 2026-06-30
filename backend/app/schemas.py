from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RescoreRequest(BaseModel):
    analysis_id: str
    resume_data: dict[str, Any]
    job_description: str | None = None


class JobUrlRequest(BaseModel):
    url: str


class BatchJD(BaseModel):
    company: str = ""
    title: str = ""
    text: str


class AnalysisSummary(BaseModel):
    analysis_id: str
    created_at: str | None = None
    filename: str | None = None
    resume_hash: str | None = None
    top_role: str | None = None
    top_role_match: int | None = None
    ats_score: int | None = None
    gap_count: int | None = None
    semantic_similarity: float | None = None
    status: str | None = None
