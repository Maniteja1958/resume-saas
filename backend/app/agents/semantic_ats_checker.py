from __future__ import annotations

import asyncio
import math
import re
from collections import Counter
from typing import Any

SKILL_TAXONOMY = {
    "Python": ["python", "python programming", "scripting"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "typed javascript"],
    "Node.js": ["node.js", "nodejs", "node js", "backend javascript runtime", "server-side javascript runtime"],
    "React": ["react", "react.js", "component based ui"],
    "FastAPI": ["fastapi", "python async api framework"],
    "Django": ["django", "python web framework"],
    "Spring Boot": ["spring boot", "java microservice framework"],
    "SQL": ["sql", "structured query language"],
    "PostgreSQL": ["postgresql", "postgres", "relational database", "database schema design"],
    "MongoDB": ["mongodb", "document database", "nosql database"],
    "Redis": ["redis", "in-memory cache", "caching"],
    "Docker": ["docker", "containerization", "containers"],
    "Kubernetes": ["kubernetes", "k8s", "container orchestration", "orchestrating containers"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda", "cloud infrastructure"],
    "Azure": ["azure", "microsoft cloud"],
    "GCP": ["gcp", "google cloud platform", "google cloud"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "deployment pipeline", "github actions", "jenkins"],
    "REST API": ["rest api", "restful", "api development", "http api"],
    "Microservices": ["microservices", "distributed services", "service oriented architecture"],
    "System Design": ["system design", "scalable architecture", "distributed systems"],
    "Unit Testing": ["unit testing", "test automation", "pytest", "jest"],
    "Machine Learning": ["machine learning", "ml", "predictive modeling"],
    "Deep Learning": ["deep learning", "neural networks"],
    "NLP": ["nlp", "natural language processing"],
    "Pandas": ["pandas", "dataframes"],
    "NumPy": ["numpy", "numerical computing"],
    "Kafka": ["kafka", "event streaming", "message broker"],
    "Terraform": ["terraform", "infrastructure as code", "iac"],
}

MATCH_THRESHOLD = 0.72
WEAK_THRESHOLD = 0.48


async def acheck(resume_data: dict[str, Any], job_description: str | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(check, resume_data, job_description)


def check(resume_data: dict[str, Any], job_description: str | None = None) -> dict[str, Any]:
    resume_text = build_resume_text(resume_data)
    requirements = extract_required_skills(job_description or "", resume_data)

    semantic_matches = []
    matched_keywords = []
    weak_matches = []
    missing_keywords = []

    for req in requirements:
        skill = req["skill"]
        similarity, evidence = semantic_similarity_for_skill(skill, resume_text, resume_data)
        if similarity >= MATCH_THRESHOLD:
            status = "matched"
            matched_keywords.append(skill)
        elif similarity >= WEAK_THRESHOLD:
            status = "weak_match"
            weak_matches.append(
                {
                    "required_skill": skill,
                    "best_resume_evidence": evidence,
                    "similarity": round(similarity, 3),
                    "status": status,
                }
            )
        else:
            status = "missing"
            missing_keywords.append(skill)

        semantic_matches.append(
            {
                "required_skill": skill,
                "best_resume_evidence": evidence,
                "similarity": round(similarity, 3),
                "status": status,
            }
        )

    semantic_coverage = sum(
        1.0 if m["status"] == "matched" else 0.5 if m["status"] == "weak_match" else 0.0
        for m in semantic_matches
    ) / max(len(semantic_matches), 1)

    formatting_issues = detect_formatting_issues(resume_data)
    section_score = section_completeness(resume_data)
    achievement_score = achievement_quality(resume_text)

    ats_score = int(semantic_coverage * 65 + section_score * 20 + achievement_score * 15 - len(formatting_issues) * 4)
    ats_score = max(0, min(100, ats_score))

    return {
        "ats_score": ats_score,
        "semantic_similarity": round(semantic_coverage, 3),
        "matched_keywords": matched_keywords,
        "weak_matches": weak_matches,
        "missing_keywords": missing_keywords,
        "formatting_issues": formatting_issues,
        "suggestions": build_suggestions(missing_keywords, weak_matches, formatting_issues),
        "semantic_matches": semantic_matches,
        "skill_vector": build_skill_vector(requirements, semantic_matches),
        "method": "semantic_synonym_cosine",
    }


def extract_required_skills(job_description: str, resume_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    jd = (job_description or "").lower()
    requirements = []

    if jd:
        for skill, aliases in SKILL_TAXONOMY.items():
            if any(alias in jd for alias in aliases):
                requirements.append({"skill": skill, "description": "; ".join(aliases), "importance": _importance(skill, jd)})

        # Also detect broad bullet requirements.
        for line in job_description.splitlines():
            clean = line.strip(" -•\t")
            if 35 <= len(clean) <= 140 and any(w in clean.lower() for w in ["experience", "knowledge", "build", "design", "develop", "deploy"]):
                # Map line back to nearest known skill if possible.
                nearest = nearest_skill(clean)
                if nearest and nearest not in [r["skill"] for r in requirements]:
                    requirements.append({"skill": nearest, "description": clean, "importance": 0.7})

    if not requirements:
        # If no JD, infer a practical default from resume/top role.
        defaults = ["Python", "SQL", "REST API", "System Design", "Git", "Unit Testing"]
        for skill in defaults:
            if skill in SKILL_TAXONOMY:
                requirements.append({"skill": skill, "description": "; ".join(SKILL_TAXONOMY[skill]), "importance": 0.65})

    return dedupe_requirements(requirements)[:12]


def semantic_similarity_for_skill(skill: str, resume_text: str, resume_data: dict[str, Any]) -> tuple[float, str]:
    low_resume = resume_text.lower()
    aliases = SKILL_TAXONOMY.get(skill, [skill.lower()])

    # Strong semantic alias match.
    for alias in aliases:
        if alias in low_resume:
            return 0.92, alias

    # Exact skill tag match.
    for s in resume_data.get("skills", []) or []:
        if str(s).lower() == skill.lower():
            return 0.9, f"Skill tag: {s}"

    # Token cosine over resume chunks as semantic fallback.
    query = " ".join(aliases)
    chunks = build_evidence_chunks(resume_data)
    best_score = 0.0
    best_chunk = ""
    for chunk in chunks:
        score = cosine_token_similarity(query, chunk)
        if score > best_score:
            best_score = score
            best_chunk = chunk[:220]

    # Convert lexical cosine into ATS-friendly similarity scale.
    scaled = min(0.7, best_score * 1.8)
    return scaled, best_chunk


def cosine_token_similarity(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)
    if not ta or not tb:
        return 0.0
    ca = Counter(ta)
    cb = Counter(tb)
    dot = sum(ca[t] * cb[t] for t in set(ca) | set(cb))
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / max(na * nb, 1e-9)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}", text.lower()) if t not in STOPWORDS]


STOPWORDS = {
    "and", "or", "the", "with", "for", "to", "of", "in", "on", "a", "an", "is", "are", "be", "as",
    "using", "experience", "knowledge", "build", "design", "develop", "work", "team", "ability",
}


def build_resume_text(resume_data: dict[str, Any]) -> str:
    parts = [resume_data.get("raw_text", "")]
    parts.extend([str(s) for s in resume_data.get("skills", []) or []])
    for exp in resume_data.get("experience", []) or []:
        parts.append(f"{exp.get('role', '')} {exp.get('company', '')} {exp.get('description', '')}")
    parts.extend([str(c) for c in resume_data.get("certifications", []) or []])
    return "\n".join(parts)


def build_evidence_chunks(resume_data: dict[str, Any]) -> list[str]:
    chunks = []
    chunks.extend([f"Skill: {s}" for s in resume_data.get("skills", []) or []])
    for exp in resume_data.get("experience", []) or []:
        chunks.append(f"Experience: {exp.get('role', '')} {exp.get('description', '')}")
    raw = resume_data.get("raw_text", "") or ""
    words = raw.split()
    for i in range(0, len(words), 70):
        chunks.append(" ".join(words[i : i + 90]))
    return [c for c in chunks if c.strip()]


def detect_formatting_issues(resume_data: dict[str, Any]) -> list[str]:
    issues = []
    if not resume_data.get("email"):
        issues.append("Missing email address")
    if not resume_data.get("phone"):
        issues.append("Missing phone number")
    if not resume_data.get("experience"):
        issues.append("Experience section is missing or not detected")
    if len(resume_data.get("skills", []) or []) < 5:
        issues.append("Skills section has fewer than five detected skills")
    if not re.search(r"\b(\d+%|\$\d+|\d+x|\d+\s*(users|requests|projects|hours|seconds))\b", resume_data.get("raw_text", ""), re.I):
        issues.append("Few quantified achievements detected")
    return issues


def section_completeness(resume_data: dict[str, Any]) -> float:
    checks = [
        bool(resume_data.get("name")),
        bool(resume_data.get("email")),
        bool(resume_data.get("phone")),
        bool(resume_data.get("skills")),
        bool(resume_data.get("experience")),
        bool(resume_data.get("education")),
    ]
    return sum(checks) / len(checks)


def achievement_quality(resume_text: str) -> float:
    metrics = re.findall(r"\b(\d+%|\$\d+|\d+x|\d+\s*(users|requests|projects|hours|seconds|ms))\b", resume_text, re.I)
    verbs = re.findall(r"\b(built|led|created|designed|improved|reduced|increased|optimized|deployed|automated)\b", resume_text, re.I)
    return min(1.0, len(metrics) * 0.2 + len(verbs) * 0.08)


def build_suggestions(missing: list[str], weak: list[dict[str, Any]], issues: list[str]) -> list[str]:
    suggestions = []
    if missing:
        suggestions.append("Add evidence for missing JD skills: " + ", ".join(missing[:4]) + ".")
    if weak:
        suggestions.append("Strengthen weak matches with project bullets and measurable impact.")
    if any("quantified" in i.lower() for i in issues):
        suggestions.append("Quantify achievements, for example: 'Reduced API latency by 35% using Redis caching'.")
    if any("phone" in i.lower() or "email" in i.lower() for i in issues):
        suggestions.append("Add complete contact details in a simple ATS-readable header.")
    if not suggestions:
        suggestions.append("Resume is well aligned. Add more role-specific metrics for an even stronger score.")
    return suggestions


def build_skill_vector(requirements: list[dict[str, Any]], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    match_by_skill = {m["required_skill"]: m for m in matches}
    vector = []
    for req in requirements[:8]:
        m = match_by_skill.get(req["skill"], {})
        vector.append(
            {
                "skill": req["skill"],
                "jd_importance": round(float(req.get("importance", 0.75)), 2),
                "resume_strength": round(float(m.get("similarity", 0.0)), 2),
                "status": m.get("status", "missing"),
            }
        )
    return vector


def _importance(skill: str, jd: str) -> float:
    count = sum(jd.count(alias) for alias in SKILL_TAXONOMY.get(skill, [skill.lower()]))
    return min(1.0, 0.62 + count * 0.12)


def nearest_skill(text: str) -> str | None:
    best = None
    score = 0.0
    for skill, aliases in SKILL_TAXONOMY.items():
        s = cosine_token_similarity(text, " ".join(aliases))
        if s > score:
            best = skill
            score = s
    return best if score > 0.18 else None


def dedupe_requirements(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for req in requirements:
        skill = req["skill"]
        if skill not in seen:
            seen.add(skill)
            result.append(req)
    return result
