"""English strings for the EDE Reflection Space workflow."""

EDE_EN = {
    "nav_ede": "EDE Reflection",
    "ede_title": "EDE reflection on professional practice",
    "ede_intro": (
        "This tool helps you reflect on how an intervention is documented: what is described, "
        "in which words, and what remains undocumented. The object of learning is professional "
        "practice, not the people receiving support."
    ),
    "ede_ai_disclaimer": (
        "AI-generated observations are hypotheses for professional reflection, not verified "
        "conclusions. They do not evaluate people or professionals, give no scores, classify "
        "no one, and do not replace professional judgement."
    ),
    "ede_privacy_notice": (
        "Privacy: before being sent to the AI model, the text goes through the application's "
        "anonymisation filter (names, contact details, dates, identifiers). The filter reduces "
        "risk but does not guarantee anonymity: indirect information may still identify someone. "
        "Do not include unnecessary personal data. The text is not saved to the database or the "
        "semantic search index; it stays only in this session until you clear it or log out. "
        "Do not use real reports until EDE has approved processing with the AI provider."
    ),
    "ede_step1": "1. Context",
    "ede_programme_label": "Programme",
    "ede_doctype_label": "Document type",
    "ede_language_label": "Language of the explanations",
    "ede_lang_auto": "Automatic (document's language)",
    "ede_step2": "2. Text to analyse",
    "ede_upload_label": "Upload a text file (.txt or .md)",
    "ede_upload_help": "Only plain-text files (.txt, .md) encoded in UTF-8 are supported.",
    "ede_text_label": "Document text",
    "ede_text_placeholder": "Paste the selected text here (without unnecessary personal data).",
    "ede_char_counter": "{n} of {max} characters",
    "ede_step3": "3. Analysis",
    "ede_analyse_button": "Explore professional practice",
    "ede_progress": "Analysing the text with the configured AI model…",
    "ede_retry_button": "Try again",
    "ede_clear_button": "Clear text and results from this session",
    "ede_cleared": "The text and results of this session have been cleared.",
    "ede_step4": "4. Observations for reflection",
    "ede_detected_language": "Detected document language: {lang}",
    "ede_explained_in": "Explanations in: {lang}",
    "ede_counts": "Validated observations: {accepted}",
    "ede_discarded_notice": (
        "{n} observation(s) produced by the model were discarded because they did not follow the "
        "required format or because their quotation does not appear verbatim in the analysed text."
    ),
    "ede_no_findings": (
        "No observation was raised for this dimension. That does not mean there is nothing to "
        "reflect on, only that the analysis found no clear support in this text."
    ),
    "ede_evidence_quote_loc": "Passage from the text (paragraph {n})",
    "ede_evidence_absence": "Not documented in this text",
    "ede_absence_caveat": (
        "That something does not appear in this text does not show that it is unknown, or that it "
        "does not exist in other documents or in reality."
    ),
    "ede_ai_hypothesis_tag": "AI hypothesis",
    "ede_observation": "Tentative observation",
    "ede_why": "Why it may matter",
    "ede_alternative": "Alternative perspective",
    "ede_questions": "Questions for professional discussion",
    "ede_limitations": "Limitations: what cannot be concluded",
    "ede_single_doc_caveat": (
        "Only one document was analysed: here only internal contradictions within the text can be "
        "pointed out, not change or trends over time."
    ),
    "ede_feedback_header": "Professional feedback",
    "ede_fb_rating_label": "How do you rate this observation?",
    "ede_fb_rating": {
        "none": "Not rated",
        "useful": "Useful",
        "unsupported": "Unsupported or not relevant",
    },
    "ede_fb_alternative_label": "My alternative interpretation",
    "ede_fb_team_question_label": "Question for team discussion",
    "ede_feedback_caption": (
        "These notes are kept only in this session and in the export you download. They are not "
        "used to train the model, to change the instructions, or as a performance indicator."
    ),
    "ede_export_header": "Export",
    "ede_export_caption": (
        "The export contains only validated observations and your notes, with their evidence "
        "excerpts and limitations. It does not include the full document."
    ),
    "ede_export_json": "Download (JSON)",
    "ede_export_md": "Download (Markdown)",
    "ede_export_md_title": "Reflection on professional practice",
    "ede_issue_ref": "Issue reference: #{id}",
    "ede_err_prefix": "The analysis could not be completed.",
    "ede_errors": {
        "input_empty": "The text is empty. Paste or upload a document.",
        "input_too_short": "The text is too short to analyse.",
        "input_too_long": "The text exceeds the maximum allowed length ({max} characters). Select a shorter passage.",
        "input_invalid": "The text or the selected options are not valid.",
        "not_authorised": "You do not have permission to use this feature.",
        "provider_not_configured": "The AI service is not configured correctly. Please tell your system administrator.",
        "provider_unavailable": "The AI service is not available right now. You can try again.",
        "output_invalid": "The model returned a response that does not follow the required format. You can try again.",
        "output_truncated": "The model's response was cut off before it finished. You can try again.",
        "busy": "The service is very busy right now. Please try again in a moment.",
        "rate_limited": "You have reached the hourly analysis limit. Please wait a little and try again.",
        "upload_type": "Only .txt or .md files are supported.",
        "upload_too_large": "The file is too large.",
        "upload_decode": "The file could not be read. It must be plain text in UTF-8.",
        "unknown": "An unexpected error occurred.",
    },
    "ede_langs": {
        "es": "Spanish", "eu": "Basque", "en": "English",
        "mixed": "mixed languages", "unknown": "not determined",
    },
    "ede_programmes": {
        "social_accommodation_bizkaia": "Social Accommodation – Bizkaia",
        "supported_housing_gipuzkoa": "Supported Housing – Gipuzkoa",
        "kulunka_bilbao": "Kulunka – Bilbao",
        "olakueta_etxea_berriz": "Olakueta Etxea – Berriz",
    },
    "ede_doctypes": {
        "follow_up_report": "Follow-up report",
        "case_note": "Case note",
        "follow_up_diary": "Follow-up diary",
        "interview_record": "Interview record",
        "social_work_report": "Social-work report",
        "referral_proposal": "Referral proposal",
        "intervention_plan": "Intervention plan",
        "professional_email": "Email between professionals",
        "coordination_record": "Coordination record",
        "other": "Other professional document",
    },
    "ede_dims": {
        "strengths_vs_deficits": {
            "label": "Deficit-focused versus strengths-based language",
            "desc": "Does the account also record strengths, resources, autonomy and progress?"},
        "observation_vs_interpretation": {
            "label": "Observable facts versus professional interpretations",
            "desc": "What is observable, what is reported by others, and what is interpretation or assumption?"},
        "labels_and_language": {
            "label": "Labels that may influence professional judgement",
            "desc": "Are there words or generalisations that may shape how the person is seen?"},
        "stereotypes_and_assumptions": {
            "label": "Possible stereotypes and implicit assumptions",
            "desc": "Only where the wording or reasoning gives a defensible basis for reflection."},
        "evidence_for_decisions": {
            "label": "Evidence supporting intervention decisions",
            "desc": "Can you see in the text what interpretations, goals and decisions rest on?"},
        "missing_information": {
            "label": "Missing information and alternative perspectives",
            "desc": "What is not documented in this text (which is not the same as unknown)."},
        "contradictions_and_change": {
            "label": "Contradictions and changes",
            "desc": "With a single document, only internal contradictions within the text."},
        "persons_voice": {
            "label": "The person's voice, preferences and life goals",
            "desc": "Are their own words, choices and aspirations reflected?"},
    },
}
