from __future__ import annotations

from typing import Any


def compare_analyses(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    skills_a = {str(s).lower(): s for s in a.get("parsed_resume", {}).get("skills", []) or []}
    skills_b = {str(s).lower(): s for s in b.get("parsed_resume", {}).get("skills", []) or []}

    ats_a = a.get("scores", {}).get("ats_score") or a.get("ats_report", {}).get("ats_score", 0)
    ats_b = b.get("scores", {}).get("ats_score") or b.get("ats_report", {}).get("ats_score", 0)
    sim_a = a.get("scores", {}).get("semantic_similarity") or a.get("ats_report", {}).get("semantic_similarity", 0)
    sim_b = b.get("scores", {}).get("semantic_similarity") or b.get("ats_report", {}).get("semantic_similarity", 0)

    roles_a = {r.get("role_name"): r for r in a.get("predicted_roles", {}).get("predictions", [])}
    roles_b = {r.get("role_name"): r for r in b.get("predicted_roles", {}).get("predictions", [])}
    role_names = sorted(set(roles_a) | set(roles_b))

    role_delta = []
    for role in role_names:
        before = roles_a.get(role, {}).get("match_percentage", 0)
        after = roles_b.get(role, {}).get("match_percentage", 0)
        role_delta.append({"role_name": role, "before": before, "after": after, "delta": after - before})

    missing_a = set(a.get("ats_report", {}).get("missing_keywords", []) or [])
    missing_b = set(b.get("ats_report", {}).get("missing_keywords", []) or [])

    return {
        "ats_score_delta": ats_b - ats_a,
        "semantic_similarity_delta": round(float(sim_b) - float(sim_a), 3),
        "skills_added": sorted([skills_b[k] for k in set(skills_b) - set(skills_a)], key=str.lower),
        "skills_removed": sorted([skills_a[k] for k in set(skills_a) - set(skills_b)], key=str.lower),
        "missing_keywords_resolved": sorted(list(missing_a - missing_b)),
        "new_missing_keywords": sorted(list(missing_b - missing_a)),
        "role_match_delta": sorted(role_delta, key=lambda x: x["delta"], reverse=True),
    }
