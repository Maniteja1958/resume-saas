from __future__ import annotations

import asyncio
from typing import Any

ROLE_SKILLS = {
    "Backend Developer": ["python", "java", "node.js", "fastapi", "django", "flask", "spring boot", "sql", "postgresql", "mysql", "mongodb", "redis", "rest api", "microservices", "docker", "system design"],
    "Frontend Developer": ["javascript", "typescript", "react", "angular", "vue", "html", "css", "graphql"],
    "Full Stack Developer": ["javascript", "typescript", "react", "node.js", "express", "python", "sql", "html", "css", "mongodb", "rest api"],
    "ML Engineer": ["python", "pytorch", "tensorflow", "scikit-learn", "machine learning", "deep learning", "nlp", "llm", "pandas", "numpy"],
    "Data Scientist": ["python", "scikit-learn", "pandas", "numpy", "machine learning", "deep learning", "sql", "tableau", "power bi"],
    "DevOps Engineer": ["docker", "kubernetes", "aws", "azure", "gcp", "git", "ci/cd", "devops", "terraform", "linux"],
    "Data Analyst": ["sql", "pandas", "numpy", "tableau", "excel", "power bi", "python"],
}


async def apredict(resume_data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(predict, resume_data)


def predict(resume_data: dict[str, Any]) -> dict[str, Any]:
    skills_original = resume_data.get("skills", []) or []
    skills = {str(s).lower() for s in skills_original}

    predictions = []
    for role, required in ROLE_SKILLS.items():
        required_set = set(required)
        matched_lower = sorted(skills & required_set)
        coverage = len(matched_lower) / max(len(required_set), 1)
        experience_bonus = _experience_bonus(resume_data, role)
        match_pct = int(28 + coverage * 62 + experience_bonus)
        if not matched_lower:
            match_pct = min(match_pct, 42 + len(skills) * 2)
        match_pct = max(15, min(98, match_pct))

        matched = [_original_case(m, skills_original) for m in matched_lower]
        predictions.append(
            {
                "role_name": role,
                "match_percentage": match_pct,
                "matched_skills": matched,
                "required_skills": [r.title() if r not in ["ci/cd", "sql"] else r.upper() for r in required[:8]],
            }
        )

    predictions.sort(key=lambda x: x["match_percentage"], reverse=True)
    return {"predictions": predictions[:3]}


def should_request_more_context(resume_data: dict[str, Any], prediction: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
    skills = resume_data.get("skills", []) or []
    experience = resume_data.get("experience", []) or []
    predictions = prediction.get("predictions", []) or []
    top = predictions[0].get("match_percentage", 0) if predictions else 0
    second = predictions[1].get("match_percentage", 0) if len(predictions) > 1 else 0

    if len(skills) < 3:
        return True, {
            "reason": "Too few skills extracted for reliable role prediction",
            "fields": ["skills", "projects", "tools", "technologies"],
        }
    if not experience:
        return True, {
            "reason": "No experience entries found; checking projects and achievements again",
            "fields": ["experience", "projects", "internships", "achievements"],
        }
    if abs(top - second) <= 4:
        return True, {
            "reason": "Top two role predictions are close; requesting more context",
            "fields": ["project_descriptions", "impact_metrics", "domain_keywords"],
        }
    return False, None


def _original_case(skill: str, originals: list[str]) -> str:
    return next((s for s in originals if str(s).lower() == skill), skill.title())


def _experience_bonus(resume_data: dict[str, Any], role: str) -> int:
    text = " ".join(
        f"{exp.get('role', '')} {exp.get('description', '')}" for exp in resume_data.get("experience", [])
    ).lower()
    if "backend" in role.lower() and any(w in text for w in ["api", "server", "database"]):
        return 6
    if "frontend" in role.lower() and any(w in text for w in ["ui", "react", "component"]):
        return 6
    if "devops" in role.lower() and any(w in text for w in ["deploy", "pipeline", "cloud"]):
        return 6
    if "ml" in role.lower() and any(w in text for w in ["model", "training", "prediction"]):
        return 6
    return 0
