"""EDE Reflection -- reflection on professional practice for ONE selected text.

Lives in the Practitioner workspace like the existing Reflection Space
page and goes through exactly the same gates: login (init_identity),
work-mode authorisation (require_work_mode), the per-person hourly limit
(services.rate_limiter) and the error boundary. The analysis itself is in
services/ede_analysis.py, which re-checks authorisation on its own.

Data handling on this page (see README "EDE reflection workflow"):
- The text and the results live ONLY in st.session_state. Nothing is
  written to PostgreSQL or Qdrant by this page.
- The text is never put in a URL, a log line, an error message or an
  export. Professional feedback is also session-only.
- "Clear" removes the text, the results and the feedback from the session.
"""

import re

import streamlit as st

import config
from navigation.router import render_nav
from services.ede_analysis import EdeAnalysisError, validate_input, run_ede_analysis
from services.ede_export import export_json, export_markdown
from services.ede_framework import DIMENSIONS
from services.error_log import error_boundary
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.language import init_language
from services.rate_limiter import DEFAULT_MAX_PER_HOUR, check_and_record

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Practitioner")
render_nav(T, page_name="ede_reflection")
render_identity_footer(T)

_UI_LANG_CODES = {"Español": "es", "Euskera": "eu", "English": "en"}
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~$:<])")


def _md(text):
    """Show model/document text literally (no accidental markdown)."""
    return _MD_SPECIAL.sub(r"\\\1", str(text))


def _init_state():
    st.session_state.setdefault("ede_programme", config.EDE_DEFAULT_PROGRAMME)
    st.session_state.setdefault("ede_doctype", config.EDE_DEFAULT_DOCUMENT_TYPE)
    st.session_state.setdefault("ede_expl_lang", "auto")
    st.session_state.setdefault("ede_upload_nonce", 0)
    st.session_state.setdefault("ede_feedback", {})


def _clear_session_data():
    """Callback for the Clear button: forget text, results and feedback."""
    for key in list(st.session_state.keys()):
        if key in ("ede_text", "ede_result", "ede_error", "ede_feedback", "ede_last_upload") \
                or key.startswith("ede_fb_"):
            del st.session_state[key]
    st.session_state["ede_upload_nonce"] = st.session_state.get("ede_upload_nonce", 0) + 1
    st.session_state["ede_feedback"] = {}
    st.session_state["ede_just_cleared"] = True


def _set_error(code, retryable=False, issue_id=None):
    st.session_state["ede_error"] = {"code": code, "retryable": retryable, "issue_id": issue_id}


def _handle_upload():
    """Read an uploaded .txt/.md into the text box, validating type, size
    and encoding. The file name is never stored."""
    uploaded = st.file_uploader(
        T["ede_upload_label"], type=["txt", "md"], help=T["ede_upload_help"],
        key=f"ede_upload_{st.session_state['ede_upload_nonce']}",
    )
    if uploaded is None or st.session_state.get("ede_last_upload") == uploaded.file_id:
        return
    st.session_state["ede_last_upload"] = uploaded.file_id
    if not uploaded.name.lower().endswith((".txt", ".md")):
        _set_error("upload_type")
        return
    if uploaded.size > config.EDE_MAX_UPLOAD_BYTES:
        _set_error("upload_too_large")
        return
    try:
        decoded = uploaded.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError:
        _set_error("upload_decode")
        return
    st.session_state.pop("ede_error", None)
    st.session_state["ede_text"] = decoded


def _run_analysis():
    st.session_state.pop("ede_error", None)
    text = st.session_state.get("ede_text", "")
    try:
        validate_input(text)  # cheap checks first, so bad input never uses up the hourly allowance
    except EdeAnalysisError as exc:
        _set_error(exc.code)
        return
    allowed, _count = check_and_record(user_name, max_per_hour=DEFAULT_MAX_PER_HOUR)
    if not allowed:
        _set_error("rate_limited")
        return
    try:
        with st.spinner(T["ede_progress"]):
            result = run_ede_analysis(
                text,
                programme=st.session_state["ede_programme"],
                document_type=st.session_state["ede_doctype"],
                explanation_language=st.session_state["ede_expl_lang"],
                ui_language=_UI_LANG_CODES.get(st.session_state.get("lang"), "es"),
                actor_name=user_name, actor_role=user_role,
            )
    except EdeAnalysisError as exc:
        st.session_state.pop("ede_result", None)
        _set_error(exc.code, exc.retryable, exc.issue_id)
        return
    st.session_state["ede_result"] = result
    st.session_state["ede_feedback"] = {}


def _show_error():
    err = st.session_state.get("ede_error")
    if not err:
        return
    messages = T["ede_errors"]
    message = messages.get(err["code"], messages["unknown"]).format(max=config.EDE_MAX_DOCUMENT_CHARS)
    st.error(f"{T['ede_err_prefix']} {message}")
    if err.get("issue_id"):
        st.caption(T["ede_issue_ref"].format(id=err["issue_id"]))
    if err.get("retryable") and st.session_state.get("ede_text"):
        if st.button(T["ede_retry_button"], key="ede_retry"):
            _run_analysis()
            st.rerun()


def _render_finding(finding, index):
    ev = finding["source_evidence"]
    fid = finding["id"]
    title = finding["observation"]
    title = (title[:90] + "…") if len(title) > 90 else title
    with st.expander(f"{index}. {title}"):
        st.caption(f"🤖 {T['ede_ai_hypothesis_tag']}")
        if ev["type"] == "direct_quote":
            st.markdown(f"**{T['ede_evidence_quote_loc'].format(n=ev['location']['paragraph'])}**")
            st.markdown("> " + _md(ev["quote"]))
        else:
            st.markdown(f"**{T['ede_evidence_absence']}:** {_md(ev['not_documented'])}")
            st.caption(T["ede_absence_caveat"])
        st.markdown(f"**{T['ede_observation']}**  \n{_md(finding['observation'])}")
        st.markdown(f"**{T['ede_why']}**  \n{_md(finding['why_it_matters'])}")
        st.markdown(f"**{T['ede_alternative']}**  \n{_md(finding['alternative_perspective'])}")
        st.markdown(f"**{T['ede_questions']}**")
        for q in finding["reflection_questions"]:
            st.markdown("- " + _md(q))
        st.markdown(f"**{T['ede_limitations']}**")
        for item in finding["limitations"]:
            st.markdown("- " + _md(item))

        st.divider()
        st.markdown(f"**{T['ede_feedback_header']}**")
        rating = st.radio(
            T["ede_fb_rating_label"], ["none", "useful", "unsupported"],
            format_func=lambda k: T["ede_fb_rating"][k], key=f"ede_fb_{fid}_rating", horizontal=True,
        )
        alternative = st.text_area(T["ede_fb_alternative_label"], key=f"ede_fb_{fid}_alt", height=80)
        team_question = st.text_input(T["ede_fb_team_question_label"], key=f"ede_fb_{fid}_q")
        st.session_state["ede_feedback"][fid] = {
            "rating": None if rating == "none" else rating,
            "alternative": alternative,
            "team_question": team_question,
        }
        st.caption(T["ede_feedback_caption"])


def _render_results(result):
    st.subheader(T["ede_step4"])
    langs = T["ede_langs"]
    st.caption(T["ede_detected_language"].format(lang=langs.get(result["detected_language"], langs["unknown"])))
    st.caption(T["ede_explained_in"].format(lang=langs.get(result["output_language"], langs["unknown"])))
    st.caption(T["ede_counts"].format(accepted=result["accepted_count"]))
    st.info(T["ede_ai_disclaimer"])
    if result["discarded_count"]:
        st.warning(T["ede_discarded_notice"].format(n=result["discarded_count"]))

    for key in DIMENSIONS:
        label = T["ede_dims"][key]
        st.markdown(f"### {label['label']}")
        st.caption(label["desc"])
        findings = result["dimensions"][key]
        if not findings:
            st.info(T["ede_no_findings"])
        for number, finding in enumerate(findings, start=1):
            _render_finding(finding, number)
        if key == "contradictions_and_change":
            st.caption(T["ede_single_doc_caveat"])

    st.divider()
    st.subheader(T["ede_export_header"])
    st.caption(T["ede_export_caption"])
    feedback = st.session_state.get("ede_feedback", {})
    col_json, col_md = st.columns(2)
    with col_json:
        st.download_button(T["ede_export_json"], export_json(result, feedback),
                           file_name="ede_reflection.json", mime="application/json", key="ede_dl_json")
    with col_md:
        st.download_button(T["ede_export_md"], export_markdown(result, T, feedback),
                           file_name="ede_reflection.md", mime="text/markdown", key="ede_dl_md")


with error_boundary("ede_reflection", T=T, user_name=user_name, user_role=user_role):
    _init_state()
    st.title(T["ede_title"])
    st.write(T["ede_intro"])
    st.info(T["ede_ai_disclaimer"])
    st.warning(T["ede_privacy_notice"])
    if st.session_state.pop("ede_just_cleared", False):
        st.success(T["ede_cleared"])

    # Step 1 -- context (defaults come from config, not from this file)
    st.subheader(T["ede_step1"])
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox(T["ede_programme_label"], config.EDE_PROGRAMME_KEYS, key="ede_programme",
                     format_func=lambda k: T["ede_programmes"][k])
    with c2:
        st.selectbox(T["ede_doctype_label"], config.EDE_DOCUMENT_TYPE_KEYS, key="ede_doctype",
                     format_func=lambda k: T["ede_doctypes"][k])
    with c3:
        st.selectbox(T["ede_language_label"], ["auto", "es", "eu", "en"], key="ede_expl_lang",
                     format_func=lambda k: T["ede_lang_auto"] if k == "auto" else T["ede_langs"][k])

    # Step 2 -- text
    st.subheader(T["ede_step2"])
    _handle_upload()
    st.text_area(T["ede_text_label"], key="ede_text", height=260,
                 placeholder=T["ede_text_placeholder"])
    current_text = st.session_state.get("ede_text", "")
    st.caption(T["ede_char_counter"].format(n=len(current_text), max=config.EDE_MAX_DOCUMENT_CHARS))

    # Step 3 -- analyse
    st.subheader(T["ede_step3"])
    b1, b2 = st.columns([2, 1])
    with b1:
        if st.button(T["ede_analyse_button"], type="primary", key="ede_analyse"):
            _run_analysis()
    with b2:
        st.button(T["ede_clear_button"], key="ede_clear", on_click=_clear_session_data)
    _show_error()

    # Step 4 -- results
    if st.session_state.get("ede_result"):
        _render_results(st.session_state["ede_result"])
