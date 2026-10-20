from datetime import date

import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.pattern_access import can_review_patterns
from services import corpus_store, corpus_service, corpus_reading_service, document_import
from services import corpus_terms
from services.corpus_report_builder import build_corpus_report
from services.anonymizer import anonymize
from services.corpus_engine import (
    CORPUS_SIMILARITY_LEVELS, DEFAULT_CORPUS_SIMILARITY_LEVEL, DEFAULT_MIN_PASSAGES,
    DEFAULT_MIN_DOCUMENTS, MAX_PASSAGES_PER_RUN, document_label,
)
from services.pattern_engine import MAX_PATTERNS_PER_RUN
from services.pattern_store import PATTERN_STATUSES, MAX_COMMENT_CHARS
from services.findings_ui import render_evidence

# Corpus analysis
# =================
#
# Step 1 of the corpus work (see CORPUS.md). For EDE's management team
# (Supervisors and Programme Managers) ONLY -- the data layer enforces
# this too, not just this page.
#
# Hard rules this page must never break:
#   - It shows "candidate patterns for reflection", never conclusions.
#     The texts carry no labels, so nothing here may claim anything about
#     unequal treatment of any group.
#   - Texts are known only by neutral numbers (T-001 ...). File names are
#     shown on screen while a file is being added but are never stored.
#   - The strength of a pattern is always "appears in X of N documents".
#   - The switch for AI-written questions hides them; they are not
#     requested from the AI at all when it is off.

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Manager")
render_nav(T, page_name="corpus_analysis")
render_identity_footer(T)

MAX_FILES_AT_ONCE = 80
MAX_PASSAGES_SHOWN = 15
MAX_DOCS_LISTED = 100

with error_boundary(
    "corpus_analysis", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["corpus_title"])

    if not can_review_patterns(user_role):
        st.info(T["corpus_no_access"])
        st.stop()

    st.info(T["corpus_intro"])
    st.caption(T["corpus_privacy_note"])

    flash_key = st.session_state.pop("_corpus_flash", None)
    if flash_key:
        st.success(T[flash_key])

    # ------------------------------------------------------------------
    # 1. Collection
    # ------------------------------------------------------------------
    st.subheader(T["corpus_collection_header"])
    corpora = corpus_store.list_corpora(user_role)

    with st.expander(T["corpus_create_header"], expanded=not corpora):
        with st.form("corpus_create_form", clear_on_submit=True):
            new_name = st.text_input(T["corpus_create_name_label"],
                                     max_chars=corpus_store.MAX_NAME_CHARS)
            created = st.form_submit_button(T["corpus_create_button"])
        if created:
            new_id = corpus_store.create_corpus(user_role, user_name, new_name)
            if new_id is None:
                st.warning(T["corpus_name_needed"].format(max=corpus_store.MAX_CORPORA))
            else:
                st.session_state["corpus_selected"] = new_id
                st.session_state["_corpus_flash"] = "corpus_created_ok"
                st.rerun()

    if not corpora:
        st.info(T["corpus_none_yet"])
        st.stop()

    corpus_ids = [c["id"] for c in corpora]
    by_id = {c["id"]: c for c in corpora}
    wanted = st.session_state.get("corpus_selected")
    corpus_id = st.selectbox(
        T["corpus_select_label"], options=corpus_ids,
        index=corpus_ids.index(wanted) if wanted in corpus_ids else 0,
        format_func=lambda i: T["corpus_option"].format(
            name=by_id[i]["name"], documents=by_id[i]["documents"]),
        key="corpus_select_box",
    )
    st.session_state["corpus_selected"] = corpus_id

    # ------------------------------------------------------------------
    # 2. Add texts
    # ------------------------------------------------------------------
    st.subheader(T["corpus_add_header"])
    st.caption(T["corpus_add_intro"])

    upload_round = st.session_state.get("_corpus_upload_round", 0)
    limits = dict(max_mb=document_import.MAX_FILE_BYTES // (1024 * 1024),
                  max_pages=document_import.MAX_PDF_PAGES,
                  max_chars=document_import.MAX_CHARS)

    def _show_result(name, result):
        """One line per text, on screen only (names are never stored)."""
        status = result["status"]
        if status == "added":
            st.success(T["corpus_result_added"].format(
                name=name, label=document_label(result["doc_no"]), passages=result["passages"]))
        elif status == "duplicate":
            st.info(T["corpus_result_duplicate"].format(
                name=name, label=document_label(result["doc_no"])))
        elif status == "empty":
            st.warning(T["corpus_result_empty"].format(name=name))
        elif status == "full":
            st.warning(T["corpus_result_full"].format(
                name=name, max=corpus_store.MAX_DOCUMENTS_PER_CORPUS))
        elif status == "refused":
            st.error(T["corpus_result_refused"].format(
                name=name, reason=T["doc_import_errors"].get(
                    result["reason"], T["doc_import_errors"]["unreadable"]).format(**limits)))
        else:
            st.error(T["corpus_result_error"].format(name=name))

    def _add_text(text):
        """Remove names from the text, then store it. Returns the store's result."""
        return corpus_store.add_document(user_role, user_name, corpus_id, anonymize(text))

    uploads = st.file_uploader(
        T["corpus_upload_label"], type=list(document_import.ALLOWED_EXTENSIONS),
        accept_multiple_files=True, key=f"corpus_upload_{upload_round}",
        help=T["doc_import_help"].format(**limits),
    )
    if uploads and len(uploads) > MAX_FILES_AT_ONCE:
        st.warning(T["corpus_too_many_files"].format(max=MAX_FILES_AT_ONCE))
    if uploads and st.button(T["corpus_add_files_button"], type="primary", key="corpus_add_files"):
        results, added = [], 0
        with st.spinner(T["corpus_adding"]):
            for upload in uploads[:MAX_FILES_AT_ONCE]:
                try:
                    text = document_import.extract_text(upload.name, upload.getvalue())
                    result = _add_text(text)
                except document_import.DocumentImportError as exc:
                    result = {"status": "refused", "reason": exc.reason}
                except Exception:
                    result = {"status": "error"}
                added += result["status"] == "added"
                results.append((upload.name, result))
        st.session_state["_corpus_upload_round"] = upload_round + 1
        st.session_state["_corpus_results"] = (added, results)
        st.rerun()

    with st.form("corpus_paste_form", clear_on_submit=True):
        pasted = st.text_area(T["corpus_paste_label"], height=160,
                              max_chars=document_import.MAX_CHARS)
        paste_submitted = st.form_submit_button(T["corpus_add_paste_button"])
    if paste_submitted:
        if not pasted.strip():
            st.warning(T["corpus_paste_empty"])
        else:
            try:
                result = _add_text(pasted)
            except Exception:
                result = {"status": "error"}
            st.session_state["_corpus_results"] = (
                int(result["status"] == "added"), [(T["corpus_pasted_name"], result)])
            st.rerun()

    shown = st.session_state.pop("_corpus_results", None)
    if shown:
        added, results = shown
        st.markdown(f"**{T['corpus_added_summary'].format(added=added, total=len(results))}**")
        for name, result in results:
            _show_result(name, result)

    # ------------------------------------------------------------------
    # 3. The texts already in the collection
    # ------------------------------------------------------------------
    counts_now = corpus_store.get_counts(user_role, corpus_id)
    st.subheader(T["corpus_docs_header"])
    documents = corpus_store.list_documents(user_role, corpus_id)
    if not documents:
        st.info(T["corpus_docs_empty"])
    else:
        st.write(T["corpus_docs_counts"].format(
            documents=counts_now["documents"], passages=counts_now["passages"]))
        with st.expander(T["corpus_docs_list_header"], expanded=False):
            for doc in documents[:MAX_DOCS_LISTED]:
                left, right = st.columns([4, 1])
                left.write(T["corpus_doc_line"].format(
                    label=document_label(doc["doc_no"]), chars=doc["char_count"],
                    passages=doc["passages"]))
                if right.button(T["corpus_doc_delete"], key=f"corpus_del_{corpus_id}_{doc['doc_no']}"):
                    corpus_store.delete_document(user_role, user_name, corpus_id, doc["doc_no"])
                    st.session_state["_corpus_flash"] = "corpus_doc_deleted_ok"
                    st.rerun()
            if len(documents) > MAX_DOCS_LISTED:
                st.caption(T["corpus_docs_more"].format(count=len(documents) - MAX_DOCS_LISTED))

    with st.expander(T["corpus_delete_collection"], expanded=False):
        st.caption(T["corpus_delete_collection_help"])
        sure = st.checkbox(T["corpus_delete_collection_confirm"], key=f"corpus_sure_{corpus_id}")
        if st.button(T["corpus_delete_collection_button"], disabled=not sure,
                     key=f"corpus_delete_btn_{corpus_id}"):
            corpus_store.delete_corpus(user_role, user_name, corpus_id)
            st.session_state.pop("corpus_selected", None)
            st.session_state["_corpus_flash"] = "corpus_deleted_ok"
            st.rerun()

    # ------------------------------------------------------------------
    # 3b. Step 2: read each text through the reflection lenses
    # ------------------------------------------------------------------
    st.divider()
    include_questions = st.toggle(T["corpus_questions_switch"], value=True, key="corpus_questions_on")
    st.caption(T["corpus_questions_help"])

    st.subheader(T["corpus_read_header"])
    st.caption(T["corpus_read_intro"])
    lens_labels = T["section_labels"]
    overview = corpus_store.get_reading_overview(user_role, corpus_id)

    if overview["documents"] == 0:
        st.info(T["corpus_read_no_texts"])
    else:
        st.write(T["corpus_read_status"].format(
            read=overview["read"], documents=overview["documents"], unread=overview["unread"]))
        if overview["unread"] == 0:
            st.success(T["corpus_read_nothing"])
        else:
            batch = min(corpus_reading_service.BATCH_SIZE, overview["unread"])
            st.caption(T["corpus_read_cost_note"].format(
                batch=batch, cost=f"{batch * corpus_reading_service.APPROX_COST_PER_TEXT_USD:.2f}",
                per_text=f"{corpus_reading_service.APPROX_COST_PER_TEXT_USD:.2f}"))
            if st.button(T["corpus_read_button"].format(count=batch), type="primary",
                         key="corpus_read_btn"):
                bar = st.progress(0.0, text=T["corpus_reading"])
                outcome = corpus_reading_service.read_texts(
                    user_role, user_name, corpus_id, st.session_state.lang,
                    include_questions=include_questions,
                    progress=lambda done, total: bar.progress(
                        done / total, text=T["corpus_read_progress"].format(done=done, total=total)))
                bar.empty()
                if outcome["status"] == "busy":
                    st.warning(T["corpus_read_busy"])
                elif outcome["status"] == "unavailable":
                    st.error(T["corpus_read_unavailable"])
                elif outcome["status"] == "nothing_to_read":
                    st.info(T["corpus_read_nothing"])
                else:
                    st.session_state["_corpus_read_result"] = outcome
                    st.rerun()

        result = st.session_state.pop("_corpus_read_result", None)
        if result:
            st.success(T["corpus_read_done"].format(
                count=result["documents_read"], remaining=result["remaining"]))
            if result["failed_lenses"]:
                st.warning(T["corpus_read_failed_lenses"].format(count=result["failed_lenses"]))

        if overview["read"] or any(v["finding"] or v["no_finding"] for v in overview["lenses"].values()):
            st.caption(T["corpus_read_caveat"])
            st.markdown(f"**{T['corpus_lens_counts_header']}**")
            for lens, counts in overview["lenses"].items():
                considered = counts["finding"] + counts["no_finding"]
                if not considered:
                    continue
                label = T["corpus_lens_item"].format(
                    lens=lens_labels.get(lens, lens), raised=counts["finding"], considered=considered)
                with st.expander(label, expanded=False):
                    if counts["failed"]:
                        st.caption(T["corpus_lens_failed_note"].format(count=counts["failed"]))
                    items = corpus_store.list_lens_readings(user_role, corpus_id, lens)
                    if not items:
                        st.write(T["corpus_lens_none"])
                    for item in items:
                        st.markdown(f"**{document_label(item['doc_no'])}**")
                        st.write(item["observation"])
                        if item["evidence"]:
                            render_evidence(T, item["evidence"], 0)
                        else:
                            st.caption(T["corpus_lens_no_quote"])
                        if item["unverified_count"]:
                            st.caption(T["corpus_lens_unverified"].format(count=item["unverified_count"]))
                        if include_questions and item["questions"]:
                            for question in item["questions"]:
                                st.markdown(f"- {question}")

            with st.expander(T["corpus_text_view_header"], expanded=False):
                doc_numbers = [d["doc_no"] for d in documents]
                chosen = st.selectbox(T["corpus_text_select"], options=doc_numbers,
                                      format_func=document_label, key=f"corpus_text_pick_{corpus_id}")
                readings = corpus_store.get_text_readings(user_role, corpus_id, chosen)
                if not readings:
                    st.info(T["corpus_text_no_reading"])
                for lens in corpus_store.READING_LENSES:
                    reading = readings.get(lens)
                    if reading is None:
                        continue
                    st.markdown(f"**{lens_labels.get(lens, lens)}**")
                    if reading["status"] == "failed":
                        st.caption(T["corpus_text_lens_failed"])
                    elif reading["status"] == "no_finding":
                        st.caption(T["corpus_text_lens_none"])
                    else:
                        st.write(reading["observation"])
                        if reading["evidence"]:
                            render_evidence(T, reading["evidence"], 0)
                        else:
                            st.caption(T["corpus_lens_no_quote"])
                        if reading["unverified_count"]:
                            st.caption(T["corpus_lens_unverified"].format(count=reading["unverified_count"]))
                        if include_questions and reading["questions"]:
                            for question in reading["questions"]:
                                st.markdown(f"- {question}")

            with st.expander(T["corpus_read_again_header"], expanded=False):
                st.caption(T["corpus_read_again_help"])
                sure_again = st.checkbox(T["corpus_read_again_confirm"], key=f"corpus_again_{corpus_id}")
                if st.button(T["corpus_read_again_button"], disabled=not sure_again,
                             key=f"corpus_again_btn_{corpus_id}"):
                    corpus_store.clear_readings(user_role, user_name, corpus_id)
                    st.session_state["_corpus_flash"] = "corpus_read_cleared_ok"
                    st.rerun()

    # ------------------------------------------------------------------
    # 3c. Step 3: the word and phrase list
    # ------------------------------------------------------------------
    st.divider()
    st.subheader(T["corpus_terms_header"])
    st.caption(T["corpus_terms_intro"])
    st.caption(T["corpus_terms_how"])

    terms_result = st.session_state.pop("_corpus_terms_result", None)
    if terms_result:
        if terms_result["status"] != "ok":
            st.error(T["corpus_result_error"].format(name=T["corpus_terms_header"]))
        else:
            st.success(T["corpus_terms_added"].format(
                added=terms_result["added"], duplicates=terms_result["duplicates"],
                invalid=len(terms_result["invalid"])))
            if terms_result["invalid"]:
                st.warning(T["corpus_terms_invalid_lines"].format(
                    lines="; ".join(terms_result["invalid"][:10]),
                    words=corpus_terms.MAX_TERM_WORDS))
            if terms_result["full"]:
                st.warning(T["corpus_terms_full"].format(max=corpus_terms.MAX_TERMS_PER_CORPUS))

    with st.form(f"corpus_terms_form_{corpus_id}", clear_on_submit=True):
        typed_terms = st.text_area(T["corpus_terms_add_label"], height=120, max_chars=4000)
        terms_submitted = st.form_submit_button(T["corpus_terms_add_button"])
    if terms_submitted:
        typed_lines = [line for line in typed_terms.splitlines() if line.strip()]
        if not typed_lines:
            st.warning(T["corpus_terms_empty_input"])
        else:
            st.session_state["_corpus_terms_result"] = corpus_store.add_terms(
                user_role, user_name, corpus_id, typed_lines)
            st.rerun()

    st.caption(T["corpus_terms_starter_help"])
    if st.button(T["corpus_terms_starter_button"], key=f"corpus_terms_starter_{corpus_id}"):
        starter = corpus_store.add_terms(
            user_role, user_name, corpus_id, list(corpus_terms.STARTER_TERMS))
        st.session_state["_corpus_terms_starter"] = starter
        st.rerun()
    starter_done = st.session_state.pop("_corpus_terms_starter", None)
    if starter_done and starter_done["status"] == "ok":
        st.success(T["corpus_terms_starter_done"].format(
            added=starter_done["added"], duplicates=starter_done["duplicates"]))
        if starter_done["full"]:
            st.warning(T["corpus_terms_full"].format(max=corpus_terms.MAX_TERMS_PER_CORPUS))

    word_list = corpus_store.list_terms(user_role, corpus_id)
    word_counts = None
    word_texts = []
    if not word_list:
        st.info(T["corpus_terms_none_yet"])
    else:
        if any(t["origin"] == "starter_eu" for t in word_list):
            st.caption(T["corpus_terms_basque_review"])
        if counts_now["documents"] == 0:
            st.info(T["corpus_terms_no_texts"])
        else:
            word_texts = corpus_store.get_document_contents(user_role, corpus_id)
            word_counts = corpus_terms.count_terms(word_list, word_texts)
            st.markdown(f"**{T['corpus_terms_counts_header']}**")
            st.caption(T["corpus_terms_caveat"])
            ordered_terms = sorted(word_counts["terms"],
                                   key=lambda t: (-t["documents"], t["term"].casefold()))
            st.dataframe(
                [{T["corpus_terms_col_term"]: t["term"],
                  T["corpus_terms_col_texts"]: T["corpus_terms_texts_cell"].format(
                      documents=t["documents"], total=word_counts["total_documents"]),
                  T["corpus_terms_col_times"]: t["occurrences"]} for t in ordered_terms],
                hide_index=True, use_container_width=True)
            st.download_button(
                T["corpus_terms_download"],
                data=corpus_terms.matrix_csv(
                    word_counts, document_label,
                    (T["corpus_terms_col_term"], T["corpus_terms_col_texts"],
                     T["corpus_terms_col_times"])).encode("utf-8-sig"),
                file_name=f"word-list-{corpus_id}-{date.today().isoformat()}.csv",
                mime="text/csv", key=f"corpus_terms_csv_{corpus_id}")

            with st.expander(T["corpus_terms_context_header"], expanded=False):
                st.caption(T["corpus_terms_context_caption"])
                by_term_id = {t["id"]: t for t in word_list}
                picked_id = st.selectbox(
                    T["corpus_terms_context_select"], options=[t["id"] for t in ordered_terms],
                    format_func=lambda i: by_term_id[i]["term"], key=f"corpus_terms_pick_{corpus_id}")
                picked = next(t for t in word_counts["terms"] if t["id"] == picked_id)
                if not picked["doc_numbers"]:
                    st.info(T["corpus_terms_context_none"])
                content_by_no = {d["doc_no"]: d["content"] for d in word_texts}
                for doc_no in picked["doc_numbers"][:20]:
                    st.markdown("**" + T["corpus_terms_context_line"].format(
                        label=document_label(doc_no), times=picked["per_doc"][doc_no]) + "**")
                    for snippet in corpus_terms.term_snippets(
                            by_term_id[picked_id]["norm"], content_by_no[doc_no], limit=2):
                        st.caption("“" + snippet + "”")
                hidden_texts = len(picked["doc_numbers"]) - 20
                if hidden_texts > 0:
                    st.caption(T["corpus_terms_context_more"].format(count=hidden_texts))

            with st.expander(T["corpus_terms_text_header"], expanded=False):
                chosen_text = st.selectbox(
                    T["corpus_terms_text_select"], options=word_counts["doc_numbers"],
                    format_func=document_label, key=f"corpus_terms_text_{corpus_id}")
                rows_for_text = corpus_terms.counts_for_text(word_counts, chosen_text)
                if not rows_for_text:
                    st.info(T["corpus_terms_text_none"])
                for term_text, times in rows_for_text:
                    st.write(T["corpus_terms_text_line"].format(term=term_text, times=times))

        with st.expander(T["corpus_terms_remove_label"], expanded=False):
            by_id_terms = {t["id"]: t for t in word_list}
            to_remove = st.multiselect(
                T["corpus_terms_remove_label"], options=list(by_id_terms),
                format_func=lambda i: by_id_terms[i]["term"], key=f"corpus_terms_rm_{corpus_id}")
            if st.button(T["corpus_terms_remove_button"], disabled=not to_remove,
                         key=f"corpus_terms_rm_btn_{corpus_id}"):
                corpus_store.delete_terms(user_role, user_name, corpus_id, to_remove)
                st.session_state["_corpus_flash"] = "corpus_terms_removed_ok"
                st.rerun()

    # ------------------------------------------------------------------
    # 3d. Printable report (built only from what the sections above hold)
    # ------------------------------------------------------------------
    st.divider()
    with st.expander(T["corpus_report_header"], expanded=False):
        st.caption(T["corpus_report_intro"])
        report_runs = corpus_store.list_runs(user_role, corpus_id, limit=10)
        opt_patterns = st.checkbox(T["corpus_report_opt_patterns"], value=bool(report_runs),
                                   key=f"corpus_rep_patterns_{corpus_id}")
        report_run_id, report_statuses = None, []
        if opt_patterns:
            if not report_runs:
                st.caption(T["corpus_report_no_run"])
            else:
                report_run_by_id = {r["id"]: r for r in report_runs}
                report_run_id = st.selectbox(
                    T["corpus_report_run_label"], options=list(report_run_by_id),
                    format_func=lambda i: T["corpus_run_option"].format(
                        date=(report_run_by_id[i]["created_at"] or "")[:16],
                        documents=report_run_by_id[i]["documents_considered"],
                        patterns=report_run_by_id[i]["patterns_created"]),
                    key=f"corpus_rep_run_{corpus_id}")
                report_statuses = st.multiselect(
                    T["patterns_filter_status"], options=list(PATTERN_STATUSES),
                    default=[s for s in PATTERN_STATUSES if s != "archived"],
                    format_func=lambda s: T["patterns_statuses"][s],
                    key=f"corpus_rep_statuses_{corpus_id}")
        opt_readings = st.checkbox(T["corpus_report_opt_readings"], value=bool(overview["read"]),
                                   key=f"corpus_rep_readings_{corpus_id}")
        opt_terms = st.checkbox(T["corpus_report_opt_terms"], value=bool(word_list),
                                key=f"corpus_rep_terms_{corpus_id}")
        opt_passages = st.checkbox(T["corpus_report_opt_passages"], value=True,
                                   key=f"corpus_rep_passages_{corpus_id}")
        opt_comments = st.checkbox(T["report_opt_comments"], value=True,
                                   key=f"corpus_rep_comments_{corpus_id}")

        signature = (
            corpus_id, counts_now["documents"], counts_now["passages"], report_run_id,
            tuple(sorted(report_statuses)), opt_patterns, opt_readings, opt_terms,
            opt_passages, opt_comments, include_questions, st.session_state.lang,
            overview["read"], tuple(sorted((k, v["finding"], v["no_finding"])
                                           for k, v in overview["lenses"].items())),
            tuple(t["id"] for t in word_list),
        )
        wants_patterns = bool(opt_patterns and report_run_id)
        wants_terms = bool(opt_terms and word_list and counts_now["documents"])
        if not (wants_patterns or opt_readings or wants_terms):
            st.warning(T["corpus_report_nothing_selected"])
        elif st.button(T["report_prepare_button"], key=f"corpus_rep_prepare_{corpus_id}"):
            report_patterns, report_events = None, {}
            if wants_patterns:
                report_patterns = corpus_store.list_patterns(
                    user_role, report_run_id, statuses=report_statuses or None)
                report_patterns.sort(key=lambda p: (-p["counts"]["documents"],
                                                    -p["counts"]["passages"], p["id"]))
                if opt_comments:
                    report_events = {p["id"]: corpus_store.get_pattern_events(user_role, p["id"])
                                     for p in report_patterns}
            report_readings = None
            if opt_readings:
                report_readings = {
                    "overview": overview,
                    "items": {lens: corpus_store.list_lens_readings(user_role, corpus_id, lens)
                              for lens, c in overview["lenses"].items()
                              if c["finding"] or c["no_finding"]},
                }
            report_terms = None
            if wants_terms:
                report_terms = corpus_terms.count_terms(
                    word_list, corpus_store.get_document_contents(user_role, corpus_id))
            st.session_state["_corpus_report"] = {
                "signature": signature,
                "html": build_corpus_report(
                    T, st.session_state.lang, lens_labels, by_id[corpus_id], counts_now,
                    prepared_on=date.today().isoformat(),
                    run=(next((r for r in report_runs if r["id"] == report_run_id), None)
                         if wants_patterns else None),
                    patterns=report_patterns, events_by_pattern=report_events,
                    readings=report_readings, terms=report_terms,
                    include_passages=opt_passages, include_questions=include_questions,
                    include_comments=opt_comments),
            }
        prepared_report = st.session_state.get("_corpus_report")
        if prepared_report and prepared_report["signature"] == signature:
            st.success(T["report_ready"])
            st.download_button(
                T["report_download_button"], data=prepared_report["html"].encode("utf-8"),
                file_name=f"text-analysis-report-{corpus_id}-{date.today().isoformat()}.html",
                mime="text/html", key=f"corpus_rep_download_{corpus_id}")
            st.caption(T["report_how_to_print"])
        elif prepared_report:
            st.info(T["report_outdated"])

    # ------------------------------------------------------------------
    # 4. Search
    # ------------------------------------------------------------------
    st.divider()
    st.subheader(T["corpus_generate_header"])
    with st.expander(T["corpus_settings_header"], expanded=False):
        st.caption(T["corpus_settings_intro"])
        level = st.select_slider(
            T["corpus_similarity_label"], options=list(CORPUS_SIMILARITY_LEVELS),
            value=DEFAULT_CORPUS_SIMILARITY_LEVEL,
            format_func=lambda k: T["patterns_similarity_levels"][k], key="corpus_similarity",
        )
        st.caption(T["corpus_similarity_help"])
        min_passages = st.number_input(
            T["corpus_min_passages_label"], min_value=2, max_value=50,
            value=DEFAULT_MIN_PASSAGES, step=1, key="corpus_min_passages")
        min_documents = st.number_input(
            T["corpus_min_documents_label"], min_value=2, max_value=50,
            value=DEFAULT_MIN_DOCUMENTS, step=1, key="corpus_min_documents")
        st.caption(T["patterns_threshold_not_proof"])

    st.caption(T["corpus_cost_note"].format(max_patterns=MAX_PATTERNS_PER_RUN))
    if counts_now["passages"] > MAX_PASSAGES_PER_RUN:
        st.caption(T["corpus_truncated"].format(max=MAX_PASSAGES_PER_RUN))

    can_generate = counts_now["documents"] >= int(min_documents)
    if not can_generate:
        st.caption(T["corpus_not_enough"].format(minimum=int(min_documents)))

    if st.button(T["corpus_generate_button"], type="primary", disabled=not can_generate,
                 key="corpus_generate_btn"):
        with st.spinner(T["corpus_generating"]):
            outcome = corpus_service.generate_corpus_patterns(
                user_role, user_name, corpus_id, st.session_state.lang,
                similarity_level=level, min_passages=int(min_passages),
                min_documents=int(min_documents), include_questions=include_questions,
            )
        if outcome["status"] == "busy":
            st.warning(T["corpus_busy"])
        elif outcome["status"] == "unavailable":
            st.error(T["corpus_unavailable"])
        elif outcome["status"] == "empty":
            st.info(T["corpus_not_enough"].format(minimum=int(min_documents)))
        else:
            st.session_state["corpus_run_id"] = outcome["run_id"]
            if outcome["patterns_created"] == 0:
                st.info(T["corpus_none_found"].format(
                    documents=outcome["documents_considered"],
                    passages=outcome["passages_considered"]))
            else:
                st.success(T["corpus_generated_ok"].format(
                    patterns=outcome["patterns_created"],
                    documents=outcome["documents_considered"]))
            if outcome["not_embedded"]:
                st.warning(T["corpus_not_embedded"].format(count=outcome["not_embedded"]))
            if outcome["fallback_count"]:
                st.warning(T["corpus_fallback_notice"].format(count=outcome["fallback_count"]))

    # ------------------------------------------------------------------
    # 5. Review
    # ------------------------------------------------------------------
    st.divider()
    st.subheader(T["corpus_review_header"])

    runs = corpus_store.list_runs(user_role, corpus_id, limit=10)
    if not runs:
        st.info(T["corpus_no_runs"])
        st.stop()

    run_ids = [r["id"] for r in runs]
    current = st.session_state.get("corpus_run_id")
    run_by_id = {r["id"]: r for r in runs}
    run_id = st.selectbox(
        T["corpus_run_select"], options=run_ids,
        index=run_ids.index(current) if current in run_ids else 0,
        format_func=lambda i: T["corpus_run_option"].format(
            date=(run_by_id[i]["created_at"] or "")[:16],
            documents=run_by_id[i]["documents_considered"],
            patterns=run_by_id[i]["patterns_created"]),
        key=f"corpus_run_select_box_{corpus_id}",
    )
    run = run_by_id[run_id]
    params = run["parameters"] or {}
    questions_on = bool(params.get("include_questions", True))
    st.caption(T["corpus_run_caption"].format(
        level=T["patterns_similarity_levels"].get(params.get("similarity_level"), "—"),
        min_passages=params.get("min_passages", "—"),
        min_documents=params.get("min_documents", "—"),
        questions=T["corpus_yes"] if questions_on else T["corpus_no"],
    ))

    status_choices = list(PATTERN_STATUSES)
    shown_statuses = st.multiselect(
        T["patterns_filter_status"], options=status_choices,
        default=[s for s in status_choices if s != "archived"],
        format_func=lambda s: T["patterns_statuses"][s], key="corpus_filter_status",
    )

    patterns = corpus_store.list_patterns(user_role, run_id, statuses=shown_statuses or None)
    patterns.sort(key=lambda p: (-p["counts"]["documents"], -p["counts"]["passages"], p["id"]))
    if not patterns:
        st.info(T["corpus_none_in_view"])
        st.stop()

    st.caption(T["corpus_no_groups_note"])

    for pattern in patterns:
        counts = pattern["counts"]
        status_label = T["patterns_statuses"].get(pattern["status"], pattern["status"])
        header = T["corpus_item_header"].format(
            title=pattern["title"], status=status_label,
            documents=counts["documents"], total=counts["total_documents"])
        with st.expander(header, expanded=False):
            st.caption(T["patterns_candidate_label"])
            st.write(T["corpus_counts_line"].format(
                documents=counts["documents"], total=counts["total_documents"],
                percent=round(counts["share"] * 100), passages=counts["passages"]))
            st.caption(T["corpus_documents_line"].format(
                labels=", ".join(document_label(n) for n in counts["doc_numbers"])))

            if pattern["lost_members"]:
                st.warning(T["corpus_lost_members"].format(count=pattern["lost_members"]))
            if pattern["below_minimum"]:
                st.warning(T["corpus_below_minimum"])

            if pattern["explanation_status"] == "fallback":
                st.warning(T["patterns_explanation_failed"])
                if st.button(T["patterns_explanation_retry"], key=f"cp_retry_{pattern['id']}"):
                    with st.spinner(T["corpus_generating"]):
                        ok = corpus_service.retry_explanation(
                            user_role, user_name, pattern["id"], pattern["members"],
                            st.session_state.lang, include_questions=questions_on)
                    st.session_state["_corpus_flash"] = (
                        "patterns_retry_ok" if ok else "patterns_retry_failed")
                    st.rerun()

            st.markdown(f"**{T['patterns_what_in_common']}**")
            st.write(pattern["description"])
            st.markdown(f"**{T['patterns_why_it_matters']}**")
            st.write(pattern["why_it_matters"])
            st.markdown(f"**{T['patterns_alternatives']}**")
            for item in pattern["alternative_explanations"]:
                st.markdown(f"- {item}")
            st.markdown(f"**{T['patterns_limitations']}**")
            for item in pattern["limitations"]:
                st.markdown(f"- {item}")
            # The switch: with questions off, nothing is requested, stored
            # or shown. (Only shown if this search was made with them on.)
            if questions_on and pattern["questions"]:
                st.markdown(f"**{T['patterns_questions']}**")
                for item in pattern["questions"]:
                    st.markdown(f"- {item}")

            st.divider()
            st.markdown(f"**{T['corpus_passages_header']}**")
            for member in pattern["members"][:MAX_PASSAGES_SHOWN]:
                st.markdown(f"**{document_label(member['doc_no'])}**")
                st.write(member["text"])
                if st.button(T["corpus_exclude_button"], key=f"cp_ex_{pattern['id']}_{member['id']}"):
                    corpus_store.set_member_excluded(
                        user_role, user_name, pattern["id"], member["id"], True)
                    st.session_state["_corpus_flash"] = "corpus_excluded_ok"
                    st.rerun()
            hidden = len(pattern["members"]) - MAX_PASSAGES_SHOWN
            if hidden > 0:
                st.caption(T["corpus_more_passages"].format(count=hidden))

            if pattern["excluded_members"]:
                st.markdown(f"**{T['patterns_excluded_header']}**")
                for member in pattern["excluded_members"]:
                    st.write(member["text"])
                    if st.button(T["patterns_restore_button"],
                                 key=f"cp_rs_{pattern['id']}_{member['id']}"):
                        corpus_store.set_member_excluded(
                            user_role, user_name, pattern["id"], member["id"], False)
                        st.session_state["_corpus_flash"] = "corpus_restored_ok"
                        st.rerun()

            st.divider()
            st.markdown(f"**{T['patterns_review_status_header']}**")
            st.caption(T["patterns_review_help"])
            with st.form(key=f"cp_form_{pattern['id']}"):
                new_status = st.selectbox(
                    T["patterns_status_label"], options=status_choices,
                    index=status_choices.index(pattern["status"]),
                    format_func=lambda s: T["patterns_statuses"][s],
                    key=f"cp_status_{pattern['id']}",
                )
                comment = st.text_area(
                    T["patterns_comment_label"], max_chars=MAX_COMMENT_CHARS,
                    key=f"cp_comment_{pattern['id']}",
                )
                saved = st.form_submit_button(T["patterns_save_review"])
            if saved:
                changed = corpus_store.set_pattern_status(
                    user_role, user_name, pattern["id"], new_status, comment)
                if changed:
                    st.session_state["_corpus_flash"] = "patterns_review_saved"
                    st.rerun()
                st.info(T["patterns_review_nothing"])

            events = corpus_store.get_pattern_events(user_role, pattern["id"])
            if events:
                st.markdown(f"**{T['patterns_history_header']}**")
                for event in events[-20:]:
                    kind = T["patterns_event_kinds"].get(event["kind"], event["kind"])
                    detail = ""
                    if event["kind"] == "status_changed":
                        detail = " " + T["patterns_event_status_change"].format(
                            old=T["patterns_statuses"].get(event["old_value"], event["old_value"]),
                            new=T["patterns_statuses"].get(event["new_value"], event["new_value"]))
                    who = event["actor"] if event["actor"] not in ("", "system") else T["patterns_event_system"]
                    st.caption(f"{(event['created_at'] or '')[:16]} — {who} — {kind}{detail}")
                    if event["comment"]:
                        st.caption("“" + event["comment"] + "”")
