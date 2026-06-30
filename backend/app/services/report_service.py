from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def build_pdf_report(analysis: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="AuraAnalyze Resume Report")
    styles = getSampleStyleSheet()
    story = []

    scores = analysis.get("scores", {})
    parsed = analysis.get("parsed_resume", {})

    story.append(Paragraph("AuraAnalyze Resume Intelligence Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Candidate: {parsed.get('name') or 'Unknown'}", styles["Normal"]))
    story.append(Paragraph(f"Analysis ID: {analysis.get('analysis_id')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(f"ATS Score: <b>{scores.get('ats_score', 'N/A')}/100</b>", styles["Normal"]))
    story.append(Paragraph(f"Top Role: <b>{scores.get('top_role', 'N/A')}</b>", styles["Normal"]))
    story.append(Paragraph(f"Semantic Similarity: {scores.get('semantic_similarity', 'N/A')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    roles = analysis.get("predicted_roles", {}).get("predictions", [])
    if roles:
        story.append(Paragraph("Predicted Roles", styles["Heading2"]))
        data = [["Role", "Match", "Matched Skills"]]
        for r in roles:
            data.append([
                r.get("role_name", ""),
                f"{r.get('match_percentage', 0)}%",
                ", ".join(r.get("matched_skills", [])[:6]),
            ])
        story.append(_table(data))
        story.append(Spacer(1, 12))

    gaps = analysis.get("skill_gaps", {})
    story.append(Paragraph("Skill Gaps", styles["Heading2"]))
    story.append(Paragraph("Missing: " + (", ".join(gaps.get("missing_skills", [])) or "None"), styles["Normal"]))
    story.append(Paragraph("Strong: " + (", ".join(gaps.get("strong_skills", [])) or "None detected"), styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Improvement Plan", styles["Heading3"]))
    story.append(Paragraph((gaps.get("improvement_plan") or "No plan required.").replace("\n", "<br/>"), styles["Normal"]))
    story.append(Spacer(1, 12))

    ats = analysis.get("ats_report", {})
    story.append(Paragraph("ATS Feedback", styles["Heading2"]))
    story.append(Paragraph("Matched: " + (", ".join(ats.get("matched_keywords", [])) or "None"), styles["Normal"]))
    story.append(Paragraph("Missing: " + (", ".join(ats.get("missing_keywords", [])) or "None"), styles["Normal"]))
    for suggestion in ats.get("suggestions", [])[:6]:
        story.append(Paragraph("• " + suggestion, styles["Normal"]))

    certs = analysis.get("certifications", {}).get("recommendations", [])
    if certs:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Recommended Certifications", styles["Heading2"]))
        data = [["Skill", "Course", "Platform", "Duration"]]
        for cert in certs[:6]:
            data.append([cert.get("skill", ""), cert.get("title", ""), cert.get("platform", ""), cert.get("duration_estimate", "")])
        story.append(_table(data))

    doc.build(story)
    return buffer.getvalue()


def _table(data):
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#313540")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table
