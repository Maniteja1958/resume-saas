from __future__ import annotations

import asyncio
import re
from typing import Any

BASE_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "React", "Angular", "Vue", "Node.js",
    "Express", "Django", "Flask", "FastAPI", "Spring Boot", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "Redis", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "CI/CD", "PyTorch", "TensorFlow",
    "scikit-learn", "Pandas", "NumPy", "HTML", "CSS", "Machine Learning", "Deep Learning", "NLP",
    "LLM", "DevOps", "GraphQL", "REST API", "Microservices", "Solidity", "Rust", "Go", "Kotlin", "Swift",
    "Kafka", "RabbitMQ", "Terraform", "Linux", "Tableau", "Power BI", "Excel", "Jenkins", "GitHub Actions",
    "System Design", "Unit Testing", "Agile", "Scrum", "REST", "API", "NoSQL", "Data Structures", "Algorithms",
]

ALIASES = {
    "Node.js": ["nodejs", "node js", "backend javascript runtime", "server-side javascript"],
    "Kubernetes": ["k8s", "container orchestration"],
    "CI/CD": ["continuous integration", "continuous delivery", "deployment pipeline", "github actions"],
    "REST API": ["restful", "api development", "web api"],
    "PostgreSQL": ["postgres", "relational database"],
    "Machine Learning": ["ml", "predictive modeling"],
    "AWS": ["amazon web services", "s3", "ec2", "lambda"],
}


async def aparse(raw_text: str, focus_fields: list[str] | None = None, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(parse, raw_text, focus_fields, existing)


def parse(raw_text: str, focus_fields: list[str] | None = None, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_text = raw_text or ""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    lower = raw_text.lower()

    name = ""
    for line in lines[:8]:
        if "@" in line or re.search(r"\d{6,}", line):
            continue
        if any(x in line.lower() for x in ["resume", "curriculum", "linkedin", "github", "email", "phone"]):
            continue
        name = line[:80]
        break

    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw_text)
    phone_match = re.search(r"(?:\+?\d[\d\-\s()]{8,}\d)", raw_text)

    skills = []
    for skill in BASE_SKILLS:
        patterns = [skill]
        patterns.extend(ALIASES.get(skill, []))
        for pattern in patterns:
            escaped = re.escape(pattern.lower())
            if pattern.lower() in ["c++", "c#", "go", "rust"]:
                found = re.search(r"(?:^|[^a-zA-Z0-9])" + escaped + r"(?:$|[^a-zA-Z0-9])", lower)
            else:
                found = re.search(r"\b" + escaped + r"\b", lower)
            if found:
                skills.append(skill)
                break

    skills = sorted(set(skills), key=lambda s: s.lower())

    experience = _extract_experience(lines)
    education = _extract_education(lines)
    certifications = _extract_certifications(lines)

    parsed = {
        "raw_text": raw_text,
        "name": name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "education": education,
        "skills": skills,
        "experience": experience,
        "certifications": certifications,
    }

    if existing:
        parsed = merge_resume_data(existing, parsed)
    return parsed


def merge_resume_data(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(old or {})
    for key in ["raw_text", "name", "email", "phone"]:
        merged[key] = new.get(key) or merged.get(key, "")
    for key in ["skills", "certifications"]:
        merged[key] = sorted(set((old or {}).get(key, []) + (new or {}).get(key, [])), key=lambda s: str(s).lower())
    for key in ["education", "experience"]:
        merged[key] = (old or {}).get(key) or (new or {}).get(key, [])
    return merged


def _extract_experience(lines: list[str]) -> list[dict[str, str]]:
    role_words = ["engineer", "developer", "analyst", "scientist", "intern", "manager", "architect", "consultant"]
    experience = []
    for i, line in enumerate(lines):
        low = line.lower()
        if any(w in low for w in role_words) and len(line) < 140:
            description = " ".join(lines[i + 1 : i + 4])[:500]
            company = ""
            role = line
            if " at " in line.lower():
                parts = re.split(r"\bat\b", line, flags=re.IGNORECASE, maxsplit=1)
                role = parts[0].strip()
                company = parts[1].strip(" ,-|")[:80]
            duration_match = re.search(r"(20\d{2}|19\d{2}).{0,20}(present|20\d{2}|19\d{2})", line, re.I)
            experience.append(
                {
                    "role": role[:100],
                    "company": company,
                    "duration": duration_match.group(0) if duration_match else "",
                    "description": description,
                }
            )
        if len(experience) >= 4:
            break
    return experience


def _extract_education(lines: list[str]) -> list[dict[str, str]]:
    education = []
    markers = ["b.tech", "m.tech", "bachelor", "master", "b.sc", "m.sc", "phd", "degree", "university", "college"]
    for line in lines:
        if any(m in line.lower() for m in markers):
            year = re.search(r"\b(19\d{2}|20\d{2})\b", line)
            education.append({"degree": line[:120], "institution": "", "year": year.group(0) if year else ""})
        if len(education) >= 3:
            break
    return education


def _extract_certifications(lines: list[str]) -> list[str]:
    certs = []
    for line in lines:
        low = line.lower()
        if any(w in low for w in ["certified", "certification", "certificate", "coursera", "nptel", "udemy"]):
            certs.append(line[:160])
    return certs[:6]
