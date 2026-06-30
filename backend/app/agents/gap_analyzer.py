from __future__ import annotations

import asyncio
import re
from typing import Any

from app.agents.job_predictor import ROLE_SKILLS

JD_EXTRA_SKILLS = [
    "kafka", "rabbitmq", "terraform", "helm", "kubernetes", "docker", "aws", "azure", "gcp", "postgresql",
    "mongodb", "redis", "graphql", "fastapi", "django", "spring boot", "react", "typescript", "node.js",
    "system design", "unit testing", "ci/cd", "microservices", "rest api", "linux", "security", "observability",
]


async def aanalyze(
    resume_data: dict[str, Any],
    predicted_role: str | None = None,
    job_description: str | None = None,
    min_missing: int = 3,
    previous_gaps: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(analyze, resume_data, predicted_role, job_description, min_missing, previous_gaps)


def analyze(
    resume_data: dict[str, Any],
    predicted_role: str | None = None,
    job_description: str | None = None,
    min_missing: int = 3,
    previous_gaps: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role = predicted_role or "Backend Developer"
    current = {str(s).lower() for s in resume_data.get("skills", []) or []}
    required = list(ROLE_SKILLS.get(role, ROLE_SKILLS["Backend Developer"]))

    jd_required = _extract_jd_skills(job_description or "")
    for skill in jd_required:
        if skill not in required:
            required.append(skill)

    missing = [s for s in required if s.lower() not in current]
    strong = [s for s in required if s.lower() in current]

    # Agentic loop support: if previous pass found too few gaps, broaden from adjacent role/JD skills.
    if previous_gaps and 0 < len(previous_gaps.get("missing_skills", [])) < min_missing:
        expanded = []
        for skills in ROLE_SKILLS.values():
            for s in skills:
                if s not in required and s not in current:
                    expanded.append(s)
        for s in expanded:
            if len(missing) >= min_missing:
                break
            missing.append(s)

    weak = []
    raw = (resume_data.get("raw_text") or "").lower()
    for skill in strong:
        # If mentioned only once and not in experience/projects, mark as weak.
        if raw.count(skill.lower()) <= 1:
            weak.append(skill)

    missing_title = [_pretty(s) for s in missing[:8]]
    strong_title = [_pretty(s) for s in strong[:8]]
    weak_title = [_pretty(s) for s in weak[:5]]

    plan = build_improvement_plan(missing_title, role)
    return {
        "target_role": role,
        "missing_skills": missing_title,
        "weak_skills": weak_title,
        "strong_skills": strong_title,
        "improvement_plan": plan,
    }


def _extract_jd_skills(jd: str) -> list[str]:
    low = jd.lower()
    found = []
    aliases = {
        "node.js": ["node", "backend javascript runtime", "server-side javascript"],
        "kubernetes": ["kubernetes", "k8s", "container orchestration"],
        "ci/cd": ["ci/cd", "continuous integration", "continuous delivery"],
        "rest api": ["rest api", "restful", "api development"],
    }
    for skill in JD_EXTRA_SKILLS:
        tokens = aliases.get(skill, [skill])
        if any(re.search(r"\b" + re.escape(token) + r"\b", low) for token in tokens):
            found.append(skill)
    return found


def _pretty(skill: str) -> str:
    mapping = {
        "ci/cd": "CI/CD",
        "sql": "SQL",
        "rest api": "REST API",
        "node.js": "Node.js",
        "aws": "AWS",
        "gcp": "GCP",
    }
    return mapping.get(skill.lower(), skill.title())


def build_improvement_plan(missing: list[str], role: str) -> str:
    if not missing:
        return f"You already cover the core {role} requirements. Improve by adding quantified impact metrics and project depth."

    first = missing[:4]
    lines = [
        f"Week 1: Add one resume bullet showing practical usage of {first[0]}.",
    ]
    if len(first) > 1:
        lines.append(f"Week 2: Build a small project using {first[1]} and document measurable outcomes.")
    if len(first) > 2:
        lines.append(f"Week 3: Complete a focused course or lab for {first[2]}.")
    if len(first) > 3:
        lines.append(f"Week 4: Update resume keywords and portfolio with {first[3]} evidence.")
    return "\n".join(lines)
