from __future__ import annotations

import asyncio
from typing import Any

CERT_MAP = {
    "python": ("Python for Everybody", "https://www.coursera.org/learn/python", "Coursera", "2-4 weeks"),
    "fastapi": ("FastAPI - The Complete Guide", "https://www.udemy.com/course/fastapi-the-complete-guide/", "Udemy", "10-20 hours"),
    "docker": ("Docker for Beginners", "https://www.udemy.com/course/docker-for-beginners/", "Udemy", "10-20 hours"),
    "kubernetes": ("Getting Started with Google Kubernetes Engine", "https://www.coursera.org/learn/google-kubernetes-engine", "Coursera", "10-20 hours"),
    "aws": ("AWS Cloud Practitioner Essentials", "https://www.coursera.org/learn/aws-cloud-practitioner-essentials", "Coursera", "10-20 hours"),
    "ci/cd": ("Introduction to CI/CD", "https://www.coursera.org/learn/introduction-continuous-integration-delivery", "Coursera", "10-20 hours"),
    "react": ("Front-End Web Development with React", "https://www.coursera.org/learn/react", "Coursera", "2-4 weeks"),
    "machine learning": ("Machine Learning Specialization", "https://www.coursera.org/specializations/machine-learning-introduction", "Coursera", "1-2 months"),
    "sql": ("SQL for Data Science", "https://www.coursera.org/learn/sql-for-data-science", "Coursera", "10-20 hours"),
}


async def afind(gaps: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(find, gaps)


def find(gaps: dict[str, Any]) -> dict[str, Any]:
    missing = gaps.get("missing_skills", []) or []
    recommendations = []
    for skill in missing[:6]:
        key = str(skill).lower()
        cert = next((value for k, value in CERT_MAP.items() if k in key or key in k), None)
        if cert:
            title, url, platform, duration = cert
        else:
            title = f"Advanced {skill} Career Certificate"
            url = f"https://www.coursera.org/search?query={str(skill).replace(' ', '%20')}"
            platform = "Coursera"
            duration = "2-4 weeks"
        recommendations.append(
            {
                "skill": skill,
                "title": title,
                "url": url,
                "platform": platform,
                "duration_estimate": duration,
            }
        )
    return {"recommendations": recommendations}
