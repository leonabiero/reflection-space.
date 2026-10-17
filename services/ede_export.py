"""Export of EDE reflection results.

An export contains ONLY validated findings (evidence excerpt or
'not documented' statement, observation, why it matters, alternative
perspective, questions, limitations) plus the professional's own
feedback notes. It never contains the full source document, a user
name, a score, or a ranking. Nothing is written to the server: the
text is produced in memory and handed to the browser's download button.
"""

import json
from datetime import datetime, timezone

from services.ede_framework import DIMENSIONS, EVIDENCE_ABSENCE


def _feedback_for(feedback, finding_id):
    entry = (feedback or {}).get(finding_id) or {}
    return {
        "rating": entry.get("rating"),
        "alternative_interpretation": (entry.get("alternative") or "").strip() or None,
        "team_discussion_question": (entry.get("team_question") or "").strip() or None,
    }


def build_export_data(result, feedback=None):
    """Plain-data export. Only fields of validated findings are copied
    (an allow-list), so nothing unexpected can leak into the file."""
    dimensions = {}
    for key in DIMENSIONS:
        items = []
        for f in (result.get("dimensions") or {}).get(key, []):
            ev = f["source_evidence"]
            items.append({
                "id": f["id"],
                "evidence": {
                    "type": ev["type"],
                    "quote": ev.get("quote"),
                    "not_documented": ev.get("not_documented"),
                    "paragraph": (ev.get("location") or {}).get("paragraph"),
                },
                "observation": f["observation"],
                "why_it_matters": f["why_it_matters"],
                "alternative_perspective": f["alternative_perspective"],
                "reflection_questions": list(f["reflection_questions"]),
                "limitations": list(f["limitations"]),
                "professional_feedback": _feedback_for(feedback, f["id"]),
            })
        dimensions[key] = items
    return {
        "notice": "AI-generated hypotheses for professional reflection; not verified conclusions.",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "programme": result.get("programme"),
        "document_type": result.get("document_type"),
        "document_language": result.get("detected_language"),
        "explanation_language": result.get("output_language"),
        "dimensions": dimensions,
    }


def export_json(result, feedback=None):
    return json.dumps(build_export_data(result, feedback), ensure_ascii=False, indent=2)


def export_markdown(result, T, feedback=None):
    """Readable export using the interface's own translations (T)."""
    data = build_export_data(result, feedback)
    labels = T["ede_dims"]
    lines = [f"# {T['ede_export_md_title']}", "", f"_{T['ede_ai_disclaimer']}_", ""]
    lines.append(f"- {T['ede_programme_label']}: {T['ede_programmes'][data['programme']]}")
    lines.append(f"- {T['ede_doctype_label']}: {T['ede_doctypes'][data['document_type']]}")
    lines.append("")
    for key in DIMENSIONS:
        lines += [f"## {labels[key]['label']}", ""]
        items = data["dimensions"][key]
        if not items:
            lines += [T["ede_no_findings"], ""]
            continue
        for item in items:
            ev = item["evidence"]
            if ev["type"] == EVIDENCE_ABSENCE:
                lines.append(f"**{T['ede_evidence_absence']}:** {ev['not_documented']}")
                lines.append(f"_{T['ede_absence_caveat']}_")
            else:
                where = T["ede_evidence_quote_loc"].format(n=ev["paragraph"])
                lines.append(f"**{where}:**")
                lines.append(f"> {ev['quote']}")
            lines += ["", f"**{T['ede_observation']}:** {item['observation']}", "",
                      f"**{T['ede_why']}:** {item['why_it_matters']}", "",
                      f"**{T['ede_alternative']}:** {item['alternative_perspective']}", "",
                      f"**{T['ede_questions']}:**"]
            lines += [f"- {q}" for q in item["reflection_questions"]]
            lines += ["", f"**{T['ede_limitations']}:**"]
            lines += [f"- {x}" for x in item["limitations"]]
            fb = item["professional_feedback"]
            if fb["rating"]:
                lines += ["", f"**{T['ede_feedback_header']}:** {T['ede_fb_rating'][fb['rating']]}"]
            if fb["alternative_interpretation"]:
                lines += ["", f"**{T['ede_fb_alternative_label']}:** {fb['alternative_interpretation']}"]
            if fb["team_discussion_question"]:
                lines += ["", f"**{T['ede_fb_team_question_label']}:** {fb['team_discussion_question']}"]
            lines.append("")
        if key == "contradictions_and_change":
            lines += [f"_{T['ede_single_doc_caveat']}_", ""]
    return "\n".join(lines).rstrip() + "\n"
