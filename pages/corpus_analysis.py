import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.pattern_access import can_review_patterns
from services import corpus_store, corpus_service, document_import
from services.anonymizer import anonymize
from services.corpus_engine import (
    CORPUS_SIMILARITY_LEVELS, DEFAULT_CORPUS_SIMILARITY_LEVEL, DEFAULT_MIN_PASSAGES,
    DEFAULT_MIN_DOCUMENTS, MAX_PASSAGES_PER_RUN, document_label,
)
from services.pattern_engine import MAX_PATTERNS_PER_RUN
from services.pattern_store import PATTERN_STATUSES, MAX_COMMENT_CHARS

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

    include_questions = st.toggle(T["corpus_questions_switch"], value=True, key="corpus_questions_on")
    st.caption(T["corpus_questions_help"])
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
