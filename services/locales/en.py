"""English (English) UI translation strings for Reflection Space.

Pure data -- no logic. Extracted verbatim from the original single-file
services/language.py (each value copied exactly, no rewording, no key
changes). See services/language.py for the language-selection and
fallback logic that consumes this dictionary.
"""

LANG_EN = {'title': '🧠 Reflection Space',
 'doc': 'Documentation',
 'case_ref': 'Case reference',
 'doc_type': 'Document type',
 'language': 'Language',
 'text': 'Text',
 'save': 'Save draft',
 'success': '✔ Draft saved successfully',
 'empty': 'Please write some text',
 'new': 'New document',
 'reflection': 'Reflection space',
 'home_subtitle': 'A space for reflection in practice.',
 'nav_hint': 'Use the sidebar to navigate.',
 'nav_header': 'Navigate:',
 'nav_doc': '📝 Documentation',
 'nav_reflection': '🌿 Reflection Space',
 'no_drafts': 'No drafts available.',
 'select_drafts': 'Select drafts to reflect on',
 'begin_reflection': 'Begin Reflection',
 'reflection_folders_intro': 'Documents awaiting reflection, grouped by case.',
 'reflection_same_day_notice': '⚠️ This case has more than one document from the same day.',
 'reflection_no_case_ref': '(No case reference)',
 'reflection_active_case_prefix': 'Reflection code:',
 'reflection_delete_button': 'Delete document',
 'reflection_delete_confirm': 'Are you sure you want to delete this document? This cannot be '
                              'undone.',
 'reflection_deleted_success': '✔ Document deleted.',
 'reflection_context_title': 'Reflection Context',
 'reflection_context_current_label': 'Selected document(s):',
 'reflection_context_historical_label': 'Relevant historical documents for this case:',
 'reflection_context_summary_strong': "This reflection uses today's case together with {count} "
                                      'related earlier reflections.',
 'reflection_context_summary_limited': "This reflection mainly uses today's case, with few related "
                                       'earlier reflections.',
 'reflection_context_summary_none': "This reflection uses today's case only.",
 'reflection_context_continue': 'Generate the reflection',
 'reflection_context_back': 'Back to selection',
 'reflection_partial_failure_notice': 'Some reflection perspectives ({count}) could not be '
                                      'generated. The reflection has still been produced. This has '
                                      "been recorded for review. You can continue with what's "
                                      'available or try again.',
 'unknown_label': 'Unknown',
 'audit_unknown_case_label': '(unknown case)',
 'case_history_completed_label': 'completed',
 'themes': ["Client's Voice",
            'Observation vs Interpretation',
            'Labels & Language',
            'Possible Bias',
            'Evidence for Decisions',
            'Missing Information',
            'Strengths vs Deficits',
            'Continuity'],
 'section_labels': {'client_voice': "Client's Voice",
                    'observation_vs_interpretation': 'Observation vs Interpretation',
                    'labels_and_language': 'Labels & Language',
                    'possible_bias': 'Possible Bias',
                    'evidence_for_decisions': 'Evidence for Decisions',
                    'missing_information': 'Missing Information',
                    'strengths_and_deficits': 'Strengths vs Deficits',
                    'continuity': 'Continuity'},
 'update_document': 'Update document',
 'edit_document_label': "Edit the document here if you'd like",
 'submit_no_edit': 'Submit without editing',
 'submit_with_edit': 'Submit with edits',
 'submitted': '✔ Document submitted',
 'error_parsing': '⚠ Could not process the reflection response. Please try again.',
 'submit_draft_failed': '⚠ Could not submit the document. Please try again.',
 'delete_draft_failed': '⚠ Could not delete the document. Please try again.',
 'login_heading': '🔒 Reflection Space',
 'username': 'Username',
 'password_label': 'Password',
 'login_button': 'Log in',
 'login_error': 'Incorrect username or password.',
 'login_locked': 'Too many failed attempts. Please wait {minutes} minute(s) before trying again.',
 'no_users_configured': 'No user accounts are configured yet. Add them under Settings → Secrets in '
                        'Streamlit Cloud.',
 'logout': 'Log out',
 'role_labels': {'Social Worker': 'Social Worker',
                 'Supervisor': 'Supervisor',
                 'Programme Manager': 'Programme Manager',
                 'System Administrator': 'System Administrator'},
 'admin_title': '🔒 Admin',
 'admin_password_label': 'Password',
 'admin_enter_button': 'Enter',
 'admin_incorrect_password': 'Incorrect password.',
 'admin_visit_log': 'Visit Log',
 'admin_no_visits': 'No visits logged yet.',
 'admin_total_views_label': 'total page views',
 'admin_clear_log': 'Clear log',
 'admin_backfill_header': '🔄 Reindex documents in Qdrant',
 'admin_backfill_caption': 'Generates semantic embeddings for documents that were completed BEFORE '
                           'semantic retrieval (Hybrid RAG) was enabled. Safe to run more than '
                           'once: each document is overwritten by its id, never duplicated. '
                           'PostgreSQL is not modified.',
 'admin_backfill_button': 'Reindex all completed documents',
 'admin_backfill_running': 'Indexing document {current} of {total}...',
 'admin_backfill_done': '✔ Reindexing complete: {indexed} of {total} documents indexed in Qdrant.',
 'admin_backfill_unavailable': "Semantic retrieval isn't configured yet (GEMINI_API_KEY or "
                               'QDRANT_URL missing from secrets). The rest of the app keeps '
                               'working with date-based historical context.',
 'admin_anon_header': 'Anonymization Demo',
 'admin_anon_caption': 'Paste sample text (fake details only) to see what leaves the system before '
                       'it reaches Claude. Runs the same anonymize() function used in '
                       'reflection_service.py.',
 'admin_sample_label': 'Sample text (fake details only)',
 'admin_run_button': 'Run anonymizer',
 'admin_output_label': 'Anonymized output (what is sent to Claude):',
 'nav_case_history': '🗂️ Reflection History',
 'case_history_title': 'Reflection History',
 'case_history_no_items': 'No saved reflections yet.',
 'case_history_original_label': 'Original version',
 'case_history_current_label': 'Current version',
 'case_history_edited_label': 'Edited',
 'case_history_not_edited_label': 'Not edited',
 'case_history_view_original_button': 'View original version',
 'case_history_all_dates': 'All dates',
 'submit_draft': 'Submit',
 'admin_table_page': 'Page',
 'admin_table_language': 'Language',
 'admin_table_visited': 'Visited at',
 'admin_sample_default': 'On 15/02/2026 the client, Sarah Kimani, of ID number 9988776655, '
                         'attended a follow-up meeting. She can be reached at +254 722 334 455 or '
                         'sarah.kimani@testmail.com. Mr. David Otieno was the assigned caseworker.',
 'case_history_date_filter_label': 'View history for:',
 'case_history_toggle_label': 'Show:',
 'case_history_edited_option': 'Edited',
 'case_history_not_edited_option': 'Not edited',
 'case_history_no_items_for_filter': 'No reflections for this selection.',
 'case_history_showing_recent': 'Showing the {shown} most recent documents out of {total}. Use the '
                                'date filter above to see older documents.',
 'feedback_prompt_title': 'How useful was this reflection?',
 'feedback_rating_label': 'Rating (1 = not useful, 5 = very useful)',
 'feedback_comment_label': 'Comment (optional)',
 'feedback_submit_button': 'Submit rating',
 'feedback_skip_button': 'Skip',
 'feedback_thanks': '✔ Thanks for your feedback',
 'feedback_section_header': 'Practitioner Feedback',
 'feedback_average_label': 'Average rating',
 'feedback_no_items': 'No feedback yet.',
 'case_history_delete_button': 'Delete case',
 'case_history_delete_confirm': 'Are you sure you want to delete this case? You can restore it for '
                                '48 hours.',
 'case_history_delete_yes': 'Yes, delete',
 'case_history_delete_cancel': 'Cancel',
 'case_history_deleted_success': '✔ Case deleted. You can restore it for 48 hours.',
 'case_history_pending_deletion_header': 'Recently Deleted',
 'case_history_pending_deletion_no_items': 'No pending deletions.',
 'case_history_restore_button': 'Restore',
 'case_history_restored_success': '✔ Case restored.',
 'case_history_deleted_by_label': 'Deleted by',
 'nav_audit_log': '🧾 Audit Log',
 'audit_log_title': 'Audit Log',
 'audit_log_no_items': 'No audit records yet.',
 'audit_action_created': 'Created',
 'audit_action_submitted': 'Submitted',
 'audit_action_deleted': 'Deleted',
 'audit_action_restored': 'Restored',
 'audit_action_purged': 'Permanently purged',
 'workspace_opportunities_header': 'Reflection Opportunities',
 'workspace_document_header': 'Case text',
 'workspace_context_header': 'Reflection context',
 'workspace_progress_label': 'Explored: {explored} of {total}',
 'workspace_explore_button': 'Explore this with the companion',
 'workspace_more_header': 'Why these questions? See what the AI noticed',
 'workspace_questions_header': 'Questions to reflect on',
 'rs_info_header': 'Reflection info',
 'workspace_close_button': 'Close',
 'workspace_explored_badge': '🗨️ Explored',
 'workspace_conversation_input_label': 'Your reflection',
 'workspace_conversation_placeholder': 'Type your response or question here...',
 'workspace_send_button': 'Send',
 'workspace_ai_thinking': 'Thinking...',
 'workspace_conversation_error': '⚠ Could not continue the conversation. Please try again.',
 'workspace_reminder': 'This is offered as a reflective prompt only. Whether to explore it, and '
                       'whether to change anything in the documentation, is entirely your '
                       'professional decision.',
 'nav_growth': '🌱 My Reflection',
 'growth_title': '🌱 Your Reflective Journey',
 'growth_intro': 'This is your personal space. It is not an evaluation of your performance and it '
                 'is never compared with other professionals. What you explore in conversations '
                 'and your notes are yours alone. The saved observations from your reflections '
                 '(and their anonymised text) can also be seen by managers in Reflection History.',
 'growth_no_data': 'You haven\'t explored a reflection yet. As you use the "Explore this with the '
                   'companion" button in the '
                   'Reflection Space, your journey will appear here.',
 'growth_themes_header': "Areas you've explored most",
 'growth_themes_caption': 'Based on {total} recorded exploration moment(s)',
 'growth_history_header': 'Recent reflective moments',
 'growth_entry_line': '**{theme}** — reflection {case} — {count} exchange(s) — {date}',
 'growth_session_count_label': 'Total exploration moments recorded',
 'journey_step1': 'Your Case',
 'journey_step2': 'Earlier Reflections',
 'journey_step3': 'Professional Reflection',
 'journey_step4': 'Reflective Questions',
 'journey_step1_desc': 'You write, paste or upload the case you want to reflect on.',
 'journey_step2_desc': 'Your earlier reflections that are linked or share themes are found.',
 'journey_step3_desc': "The AI analyses today's case together with any earlier reflections you "
                       'included.',
 'journey_step4_desc': "You're invited to consider reflective questions.",
 'historical_timeline_header': 'Historical Timeline',
 'historical_timeline_intro': 'Relevant documents for this case, arranged chronologically.',
 'timeline_today_label': "📍 Today's Documentation",
 'dashboard_navigator_hint': 'Use the tabs to move between reflection areas without scrolling '
                             'through the whole page.',
 'coverage_header': 'Reflection Coverage',
 'coverage_intro': 'This confirms that every dimension was considered in this reflection -- it is '
                   'not a score or an evaluation.',
 'coverage_considered': 'Analysed',
 'coverage_unavailable': "Couldn't be generated this time",
 'history_link_hint': 'Want to revisit your past reflections? Your personal reflective journey is '
                      'available on',
 'workmode_switch_label': 'Work mode',
 'workmode_practitioner': 'Practitioner',
 'workmode_manager': 'Manager / Supervisor',
 'workmode_admin': 'System Administration',
 'workmode_access_denied': 'You do not have access to this workspace.',
 'nav_system_admin': '🛠️ System Administration',
 'admin_user_mgmt_header': '👥 User Management',
 'admin_user_mgmt_info': 'Users are managed through Streamlit Secrets. Dynamic CRUD is '
                         'intentionally unavailable because credentials and roles are configured '
                         'in deployment secrets, not application tables.',
 'admin_user_mgmt_empty': 'No users are configured yet. Add them under Settings → Secrets in '
                          'Streamlit Cloud.',
 'admin_user_col_username': 'Username',
 'admin_user_col_name': 'Name',
 'admin_user_col_role': 'Role',
 'admin_advanced_diagnostics': '🔧 Advanced Diagnostics',
 'admin_show_raw_response': 'Show raw response',
 'admin_status_connected': 'Connected',
 'admin_status_not_connected': 'Not connected',
 'admin_status_present': '✅ Present',
 'admin_status_missing': '❌ Missing',
 'admin_health_header': '💚 System Health',
 'admin_health_overall': '#### Overall Status',
 'admin_health_critical': '🔴 Critical',
 'admin_health_degraded': '🟡 Degraded (semantic retrieval not configured -- app is using '
                          'date-based fallback)',
 'admin_health_healthy': '🟢 Healthy',
 'admin_health_components': '#### Components',
 'admin_health_component_col': 'Component',
 'admin_health_status_col': 'Status',
 'admin_health_component_database': 'Database',
 'admin_health_component_embedding': 'Embedding service (Gemini API)',
 'admin_health_component_reflection': 'Reflection engine (Claude API)',
 'admin_health_healthy_label': 'Healthy',
 'admin_health_unreachable_label': 'Unreachable',
 'admin_health_available_label': 'Available',
 'admin_health_not_configured_label': 'Not configured',
 'admin_health_operational_label': '✅ Operational',
 'admin_health_db_error_prefix': 'Database error:',
 'admin_health_key_missing': 'ANTHROPIC_API_KEY is not configured -- reflections cannot be '
                             'generated.',
 'admin_tools_header': '🧰 Administrative Tools',
 'admin_anon_empty_warning': 'Type or paste a sample text first, then press the button again.',
 'admin_anon_no_changes': 'The anonymizer found no personal details to replace in this text.',
 'admin_anon_stale_note': 'You have changed the text since the last test: press the button again '
                          'to see the updated result.',
 'admin_anon_tags_help': "Tags: [PERSON] = person's name · [LOCATION] = place · [ADDRESS] = "
                         'address · [ORGANISATION] = centre or organisation · [ID] = DNI/NIE, case '
                         'file, account or other identifier · [PHONE] = phone · [EMAIL] = email · '
                         '[DATE] = date · [AGE_…] = exact age replaced by a life stage (INFANT = '
                         'baby, CHILD = child, ADOLESCENT = teenager under 18, YOUNG_ADULT = young '
                         'adult, ADULT = adult, OLDER_ADULT = older adult).',
 'admin_tools_anon_test_header': 'Anonymization Test',
 'admin_tools_future': 'Future administrator tools will appear here.',
 'admin_console_caption': 'Administration console for Reflection Space -- users, system status, '
                          'recorded problems, costs and data erasure.',
 'admin_error_log_unknown_page': 'unknown page',
 'admin_error_log_no_message': '(no message)',
 'event_labels': {'Opened page': 'Opened page',
                  'Changed page': 'Changed page',
                  'Email sent': 'Email sent',
                  'User submitted report': 'User submitted report',
                  'Exception occurred': 'Exception occurred',
                  'Error logged': 'Error logged'},
 'admin_error_log_caption': 'A list of the problems recorded in the app (crashes, failed AI '
                            'calls, or problems people reported): what happened, when, and its '
                            'status. The AI diagnosis arrives in the alert email.',
 'admin_problem_what_label': 'What happened',
 'admin_problem_open_header': 'Open problems ({n})',
 'admin_problem_solved_header': 'Solved problems ({n})',
 'admin_problem_none_open': 'There are no open problems.',
 'admin_reset_header': '🧹 Erase all data',
 'admin_reset_intro': 'Permanently erases everything saved in the app: reflections and their '
                      'texts, observations and notes, ratings, pattern reviews, old documents, '
                      'activity history, recorded problems, and usage and cost records. Every '
                      'count in the app goes back to 0.',
 'admin_reset_kept_note': 'User accounts and settings are kept. Nobody will have to sign in again.',
 'admin_reset_warning': 'This action cannot be undone.',
 'admin_reset_confirm_word': 'ERASE',
 'admin_reset_confirm_label': 'To confirm, type {word}',
 'admin_reset_button': 'Erase all data',
 'admin_reset_done': 'All data has been erased. The app starts from zero.',
 'admin_reset_refused': 'Only the System Administrator can do this.',
 'admin_reset_failed': 'The erase could not be completed. Nothing was erased. Please try again.',
 'admin_error_log_empty': 'No problems recorded. Everything looks fine.',
 'admin_error_log_first_seen_label': 'First seen',
 'admin_error_log_header': '🩺 Diagnostic Centre',
 'admin_translation_health_header': '🌐 Translation System Health',
 'admin_translation_health_caption': 'Live status of the Español / Euskera / English translation '
                                     'system.',
 'admin_translation_autofilled_warning': '{count} translation key(s) were auto-filled with '
                                         'placeholder text on startup.',
 'admin_translation_autofilled_details': 'View auto-filled keys',
 'admin_translation_copied_from': 'copied from',
 'admin_translation_in_sync': 'All languages are structurally in sync. Nothing needed '
                              'auto-filling.',
 'admin_translation_runtime_gaps': '⚠️ Keys missing at runtime this session ({count})',
 'admin_translation_panel_error': 'Translation health panel could not be loaded right now.',
 'admin_error_log_occurrences_label': 'Occurrences',
 'admin_error_log_page_label': 'Page',
 'admin_error_log_status_label': 'Status',
 'admin_error_log_when_label': 'When',
 'error_boundary_body': 'This has been recorded as error {ref}. Please try again -- if it keeps '
                        'happening, tell your administrator the reference number above.',
 'error_boundary_heading': 'Something went wrong on this page.',
 'rate_limit_exceeded_message': "You've reached the limit of {max} reflections in the last hour on "
                                'this account. This is a safety limit to prevent accidental '
                                'repeated requests, not a restriction on your normal work -- '
                                'please wait a little and try again, or contact your System '
                                'Administrator if you believe this is a mistake.',
 'reflection_duplicate_message': 'This reflection is already being generated. Please wait a moment '
                                 'for it to finish before trying again.',
 'report_problem_caption': 'Something look wrong? Describe it below. Your administrator will be '
                           'notified right away.',
 'report_problem_description_label': 'What happened?',
 'report_problem_empty_warning': 'Please add a short description before sending.',
 'report_problem_header': '🚩 Report a problem',
 'report_problem_send_button': 'Send Report',
 'report_problem_sent': 'Report sent. Thank you -- your administrator has been notified.',
 'status_labels': {'New': 'New',
                   'Investigating': 'Investigating',
                   'Recurred': 'Recurred',
                   'Fixed': 'Fixed',
                   'Closed': 'Closed',
                   'All': 'All',
                   'Any': 'Any'},
 'severity_labels': {'All': 'All',
                     'error': 'Error',
                     'warning': 'Warning',
                     'user_reported': 'User reported'},
 'help': {'nav_label': '❓ Help',
          'page_title': 'Reflection Space Quick Guide',
          'intro_title': 'What is Reflection Space?',
          'intro_body': 'Reflection Space helps you reflect on a case on the spot: you write, '
                        'paste or upload the case and it offers reflective questions across eight '
                        "professional dimensions -- such as whether the client's own voice is "
                        'present, or whether strengths are being overlooked alongside '
                        'difficulties. It is not a place to store documents: only the reflection '
                        'is saved.',
          'guardrail_note': 'The tool never grades, scores, or decides anything for you. You '
                            'decide what, if anything, to do with what it made you think about.',
          'journey_title': 'How it works',
          'journey_steps': ["1. Let's reflect -- write or paste your text, or upload a document (Word, PDF or text). No reference, type of text or theme is needed.", '2. Choose the reflection language (Español, Euskara or English) and press Reflect. The text is anonymised automatically before the AI receives it.', '3. Professional Reflection -- explore the eight reflective dimensions, optionally have a short conversation about any of them, add your notes and finish. The case text is then cleared from the screen.'],
          'practitioner_title': 'Practitioner workspace',
          'doc_section_title': '📝 Your case -- write, paste or upload',
          'doc_section_body': "On Reflection Space you write or paste your text into a single box, or upload a Word, PDF or text file (only the text is read; the file is never kept). If you both write text and upload a document, you'll be asked which one to reflect on. You don't have to give any case reference or details: the app creates a neutral code by itself (for example RS-7F3K2Q) that identifies no one. The original text is saved securely for later pattern analysis (see below).",
          'original_saved_note': "The original text is kept securely in a database in the EU, for up to {months} months, to help identify patterns in practice. Only the anonymised version is ever sent to the AI. You can read your own text in My Reflection; supervisors and programme managers can read the texts in Pattern Review, without the author's name. After that time it is deleted automatically; the reflection itself stays.",
          'reflection_section_title': '🪞 Reflection Space -- reflecting on the spot',
          'reflection_section_body': 'When you press Reflect, your text is anonymised automatically (names '
                                     'and other personal details are removed) and only that protected '
                                     'version is sent to the AI. If anonymisation fails, nothing is sent. '
                                     'On the results, "View anonymised text" shows you exactly what the AI '
                                     'received. Explore any of the eight dimensions, optionally open a '
                                     'short conversation about one, add your notes and select Finish '
                                     'reflection. Afterwards you can rate how useful the session was -- '
                                     'entirely optional.',
          'cards_note': 'The eight reflection opportunities are shown as cards in one view. The dot in the '
                         'corner shows what each one found: green, something to reflect on; grey, nothing '
                         'notable in this text; amber, not available right now (you can retry inside the '
                         'card). Opening a card shows the questions; what the AI noticed and the passage '
                         'it is based on are under "Why these questions?".',
          'dimensions_title': 'The eight reflective dimensions',
          'dimensions': [{'label': "Client's Voice",
                          'desc': "Is the person's own voice, goals, and preferences reflected, or "
                                  'does the narrative come mostly from the professional?'},
                         {'label': 'Observation vs Interpretation',
                          'desc': 'Are statements presented as observed fact, when some are '
                                  'actually interpretation, assumption, or opinion?'},
                         {'label': 'Labels & Language',
                          'desc': 'Are there labels or charged terms that could quietly steer how '
                                  'this person or family is perceived?'},
                         {'label': 'Possible Bias',
                          'desc': 'Are there stereotypes or unexamined assumptions tied to origin, '
                                  'gender, age, migration status, mental health, or substance '
                                  'use?'},
                         {'label': 'Evidence for Decisions',
                          'desc': 'Are intervention decisions clearly supported by evidence, or do '
                                  'they rely on implicit assumptions?'},
                         {'label': 'Missing Information',
                          'desc': 'Is there relevant information missing whose absence could '
                                  'change how the situation is understood?'},
                         {'label': 'Strengths vs Deficits',
                          'desc': 'Does the language focus mainly on problems and deficits, '
                                  "overlooking the person's strengths and resources?"},
                         {'label': 'Continuity',
                          'desc': 'Are there contradictions or notable shifts across documents '
                                  'compared with what came before?'}],
          'delete_note': 'You can delete any of your reflections from "Your saved reflections" at the '
                          'bottom of My Reflection. It disappears everywhere at once; you can restore it for '
                          '{hours} hours, after which it is erased for good.',
          'growth_section_title': '🌱 My Reflection -- your personal journal',
          'growth_section_body': "My Reflection is your own space: the themes you've explored most, a "
                                  'timeline of your reflective moments, your saved observations with your '
                                  'notes, and the list of your reflections (which you can delete). No '
                                  'scores, no comparison to anyone else. Your notes and what you explore are '
                                  'yours alone; the saved observations can also be seen by managers.',
          'manager_title': 'Manager workspace',
          'case_history_section_title': '🗂️ Reflection History',
          'case_history_section_body': 'Reflection History shows the average usefulness rating '
                                       '(never individual ratings or who gave them) and the saved '
                                       'reflections, each with its neutral code, themes and the '
                                       "AI's observations. You can filter by date and theme. It "
                                       "never shows professionals' private notes.",
          'admin_title': '🛠️ System Administration',
          'admin_section_body': 'System Administration brings together the user list, system '
                                'health, the anonymisation test, translation health checks, the '
                                'Diagnostic Centre (the list of recorded problems), and service '
                                'usage and costs. It also lets you permanently erase all saved '
                                'data to start from zero.',
          'report_problem_title': '🚩 Reporting a problem',
          'report_problem_body': 'Every page has a 🚩 Report a problem control in the sidebar, '
                                 'available to everyone. Describe what happened in your own words '
                                 'and select Send -- the system automatically attaches page, '
                                 'session, and navigation context.',
          'privacy_title': '🔒 Privacy and data',
          'privacy_points': ['The original case text is kept securely in an EU database for a limited time, for pattern analysis -- only the anonymised version is ever sent to the AI, and supervisors and programme managers read it without your name.', 'Each reflection is identified by a neutral code and themes with no personal details, never by names.', "Your notes on the observations are private -- only you can see them. The AI's observations are used in the management team's pattern review, without your name.", 'Reflective conversation content is never stored beyond the session -- only which theme was explored, and when.', 'My Reflection is personal and comparison-free: no scores, no ranking, visible to no one but you.', 'Two-layer role-based access control is enforced throughout the app.']},
 'admin_usage_header': '💰 Service Usage & Costs',
 'admin_usage_caption': 'What each external service is costing this pilot, estimated from actual '
                        'recorded API usage. Figures marked "estimate" could not be tied to an '
                        'exact provider price and should be treated as approximate.',
 'admin_usage_status_green': '🟢 OK',
 'admin_usage_status_yellow': '🟡 Approaching limit',
 'admin_usage_status_orange': '🟠 Near limit',
 'admin_usage_status_red': '🔴 At/over limit',
 'admin_usage_status_unknown': '⚪ Limit unavailable',
 'admin_usage_unavailable': 'Unavailable',
 'admin_usage_limit_unavailable': 'Limit unavailable',
 'admin_usage_overview_header': 'Overview',
 'admin_usage_col_service': 'Service',
 'admin_usage_col_usage': 'Usage (this month)',
 'admin_usage_col_limit': 'Budget',
 'admin_usage_col_pct': '% used',
 'admin_usage_col_cost': 'Est. cost (month)',
 'admin_usage_col_status': 'Status',
 'admin_usage_no_billing_api': 'No billing API',
 'admin_usage_connections': 'connections',
 'admin_usage_not_started': 'Not started yet',
 'admin_usage_provider_billing_unavailable': 'Provider billing data unavailable',
 'admin_usage_active_users': 'active users',
 'admin_usage_emails_sent': 'emails sent',
 'admin_usage_claude_detail_header': 'Claude (Anthropic) detail',
 'admin_usage_cost_today': 'Est. cost today',
 'admin_usage_cost_month': 'Est. cost this month',
 'admin_usage_cost_projected': 'Projected month-end cost',
 'admin_usage_input_tokens': 'Input tokens (month)',
 'admin_usage_output_tokens': 'Output tokens (month)',
 'admin_usage_model_unrecognized': '⚠️ Some calls used a model not in the pricing table -- their '
                                   'cost is a fallback estimate.',
 'admin_usage_anthropic_not_configured': 'Anthropic API key is not configured.',
 'admin_usage_per_reflection_header': 'Cost per successful reflection',
 'admin_usage_avg_cost_reflection': 'Average Claude cost per reflection',
 'admin_usage_reflections_generated': 'Reflections generated (30 days)',
 'admin_usage_companion_calls': 'Companion calls (30 days, incl. retries)',
 'admin_usage_retry_rate': 'Retry rate',
 'admin_usage_no_median_note': "A median isn't available: individual companion calls aren't "
                               'currently tagged with which reflection they belong to, so only the '
                               'overall average can be computed.',
 'admin_usage_gemini_detail_header': 'Gemini Embeddings detail',
 'admin_usage_embeddings_month': 'Embeddings this month',
 'admin_usage_embeddings_failed': 'Failed embedding requests (month)',
 'admin_usage_gemini_estimate_note': '⚠️ Some embedding calls did not return an exact token count '
                                     'from the provider; their cost is marked as an estimate.',
 'admin_usage_gemini_not_configured': 'Gemini API key is not configured.',
 'admin_usage_pricing_header': 'Pricing & budget configuration',
 'admin_usage_pricing_caption': 'Provider prices are centralized in one place '
                                '(services/cost_pricing.py) so they never have to be hunted down '
                                'across the codebase when a provider changes its rates. Monthly '
                                'budgets used for the status colours above are configured in '
                                'config.py (MONTHLY_BUDGET_ANTHROPIC_USD, '
                                'MONTHLY_BUDGET_GEMINI_USD).',
 'admin_usage_forecast_header': 'User volume forecast (estimate)',
 'admin_usage_forecast_caption': 'Projects monthly cost at a hypothetical number of users, based '
                                 "on this pilot's own measured average cost per reflection. Adjust "
                                 'the numbers below.',
 'admin_usage_forecast_users': 'Number of users',
 'admin_usage_forecast_reflections': 'Reflections per user per month',
 'admin_usage_forecast_total_reflections': 'Total reflections/month',
 'admin_usage_forecast_claude_cost': 'Projected Claude cost/month',
 'admin_usage_forecast_gemini_cost': 'Projected Gemini cost/month',
 'admin_usage_forecast_presets_header': 'Common scenarios',
 'admin_usage_forecast_current': 'Current',
 'admin_usage_forecast_col_users': 'Users',
 'admin_usage_forecast_col_reflections': 'Reflections/month',
 'admin_usage_forecast_col_claude_cost': 'Est. Claude cost/month',
 'admin_usage_forecast_estimate_disclaimer': '⚠️ All projections above are ESTIMATES based on '
                                             'currently observed averages, not guaranteed costs.',
 'findings_evidence_caption': 'Passage from the case text this observation is based on:',
 'findings_unverified_notice': '{count} passage(s) proposed by the AI did not match the text '
                               'exactly and are not shown.',
 'findings_notes_header': 'My notes',
 'findings_label_prompt': 'How did you find it?',
 'findings_label_none': 'Not rated',
 'findings_labels': {'useful': 'Useful',
                     'not_relevant': 'Not relevant',
                     'uncertain': 'Not sure',
                     'discuss': 'To discuss later'},
 'findings_misread_label': 'I think the AI misunderstood the context',
 'findings_alternative_label': 'Another possible explanation (optional)',
 'findings_note_label': 'My reflection or note (optional)',
 'findings_save_button': 'Save my notes',
 'findings_save_success': 'Notes saved.',
 'findings_save_error': "Your notes couldn't be saved. Please try again in a moment.",
 'findings_not_saved_notice': "This reflection couldn't be saved, so you won't be able to keep "
                              'notes on it. You can carry on working as normal.',
 'findings_journal_header': 'Saved observations and your notes',
 'findings_journal_intro': 'Here you can return to the observations from your reflections, with '
                           'the exact passage each is based on, and write or review your own '
                           'notes. Your notes are for you alone.',
 'findings_journal_empty': 'There are no saved observations yet. They will appear here after your '
                           'next reflection.',
 'findings_journal_count': '{total} saved observation(s) — page {page} of {pages}',
 'findings_journal_count_reflections': '{total} reflection(s) — page {page} of {pages}',
 'findings_reflection_line': '{code} — {date} — {count} observation(s)',
 'findings_reflection_notes_suffix': '· ✔ {count} with notes',
 'findings_pick_observation': 'Choose an observation',
 'findings_journal_newer': '← Newer',
 'findings_journal_older': 'Older →',
 'nav_patterns': '🔎 Pattern Review',
 'findings_notes_privacy': "Your notes and ratings are private: only you can see them. They are saved separately from what the AI said, which is never changed. The AI's observations (never your name or your notes) are used in the management team's pattern review. When you save, names, exact ages and other personal details are removed from your notes.",
 'patterns_title': '🔎 Pattern Review',
 'patterns_no_access': 'This page is only for supervision and programme management.',
 'patterns_intro': "This page helps the team look for themes that recur across the observations made in professionals' reflections. What it shows are candidate patterns for reflection, not conclusions: a group of similar observations is not evidence of bias or poor practice, and the set does not necessarily represent the organisation. The team decides what a pattern means, if anything.",
 'patterns_pool_header': 'What is available to review',
 'patterns_pool_caption': "All observations from professionals' reflections appear here. You never see who wrote them or their private notes.",
 'patterns_filter_lenses': 'Limit to these reflection points (empty = all)',
 'patterns_filter_from': 'From (optional)',
 'patterns_filter_to': 'To (optional)',
 'patterns_pool_empty': 'There are no observations with these filters yet.',
 'patterns_pool_counts': '{observations} observation(s) from {reflections} reflection(s) and {cases} distinct case reference(s).',
 'patterns_pool_no_case': '{count} reflection(s) have no case reference, so they do not count as '
                          'cases.',
 'patterns_generate_header': 'Look for patterns',
 'patterns_settings_header': 'Search settings',
 'patterns_settings_intro': 'These settings are starting points, not proven values. Change them '
                            'and compare the results.',
 'patterns_similarity_label': 'How alike observations must be',
 'patterns_similarity_levels': {'broad': 'Broad', 'balanced': 'Balanced', 'strict': 'Strict'},
 'patterns_similarity_help': 'Broad groups looser resemblances (more groups, more noise). Strict '
                             'needs a closer resemblance (fewer, more reliable groups).',
 'patterns_min_observations_label': 'Minimum observations per group',
 'patterns_min_reflections_label': 'Minimum distinct reflections per group',
 'patterns_threshold_not_proof': 'Reaching these minimums proves nothing: it only decides whether '
                                 'a group is worth showing for discussion.',
 'patterns_cost_note': 'Looking for patterns uses AI to write up to {max_patterns} explanations (a '
                       'few cents in total). You only pay again if you press the button again.',
 'patterns_pool_truncated': 'There are more observations than are compared at once; the {max} most recent are used.',
 'patterns_not_enough': 'At least {minimum} observations are needed to look for patterns.',
 'patterns_generate_button': 'Look for patterns',
 'patterns_generating': 'Looking for patterns…',
 'patterns_busy': 'A search is already running. Wait for it to finish and try again.',
 'patterns_unavailable': 'The meaning-matching service is not configured, so patterns cannot be '
                         'searched for right now.',
 'patterns_none_found': 'No group met the minimums among {observations} observations. Try a broader setting, or wait for more reflections.',
 'patterns_generated_ok': 'Found {patterns} candidate pattern(s) among {observations} '
                          'observations.',
 'patterns_not_embedded': '{count} observation(s) could not be compared this time and were left '
                          'out.',
 'patterns_fallback_notice': 'The explanation for {count} pattern(s) could not be written; a plain '
                             'text is shown and you can retry it.',
 'patterns_review_header': 'Review candidate patterns',
 'patterns_no_runs': 'No patterns have been searched for yet.',
 'patterns_run_select': 'Search to review',
 'patterns_run_option': '{date} — {observations} observations — {patterns} pattern(s)',
 'patterns_run_caption': 'Settings of this search: {level} similarity; at least {min_obs} '
                         'observations from at least {min_refl} distinct reflections.',
 'patterns_filter_status': 'Show statuses',
 'patterns_statuses': {'candidate': 'Candidate',
                       'under_review': 'Under review',
                       'worth_discussing': 'Worth discussing',
                       'not_supported': 'Not supported after review',
                       'archived': 'Archived'},
 'patterns_none_in_view': 'There are no patterns with these filters.',
 'patterns_cases_none': 'None of these reflections has a case reference, so nothing can be said '
                        'about cases.',
 'patterns_cases_incomplete': '{missing} of the {total} reflections have no case reference, so '
                              'recurrence across cases cannot be established; it can only be said '
                              'to appear in several reflections.',
 'patterns_cases_single': 'All the observations relate to one case reference: this is repetition '
                          'within a case, not across cases.',
 'patterns_cases_multiple': 'The observations come from {cases} distinct case references.',
 'patterns_item_header': '{title} — {status} — {observations} obs. / {reflections} reflections',
 'patterns_candidate_label': 'Candidate pattern for reflection — not a conclusion.',
 'patterns_counts_line': '{observations} observation(s) · {reflections} distinct reflection(s) · '
                         '{cases} distinct case(s)',
 'patterns_case_ref_caveat': 'Case references are typed by hand: a typo can make one case count as '
                             'two.',
 'patterns_dates_line': 'Reflections between {first} and {last}',
 'patterns_lenses_line': 'Reflection points: {lenses}',
 'patterns_lost_members': '{count} of the observations in this pattern are no longer available (their reflection was deleted). The written explanation may still reflect them: look for patterns again before relying on it.',
 'patterns_below_minimum': 'With the current observations, this group no longer reaches the '
                           'minimums it was found with.',
 'patterns_explanation_failed': 'The automatic explanation for this pattern could not be written. '
                                'A plain text is shown.',
 'patterns_explanation_retry': 'Retry the explanation',
 'patterns_retry_ok': 'Explanation written.',
 'patterns_retry_failed': 'The explanation still could not be written. Please try again later.',
 'patterns_what_in_common': 'What they have in common',
 'patterns_why_it_matters': 'Why it may matter',
 'patterns_alternatives': 'Other possible explanations',
 'patterns_limitations': 'What cannot be known from this',
 'patterns_questions': 'Questions to discuss',
 'patterns_observations_header': 'Observations in this group (with the exact quotation)',
 'patterns_exclude_button': 'This observation does not belong in this pattern',
 'patterns_excluded_ok': 'Observation removed from the pattern.',
 'patterns_more_observations': 'And {count} more observation(s) not shown here.',
 'patterns_excluded_header': 'Observations the team removed from this pattern',
 'patterns_restore_button': 'Include it again',
 'patterns_restored_ok': 'Observation included again.',
 'patterns_review_status_header': "The team's assessment",
 'patterns_review_help': 'Record your own judgement here. What the AI proposed is never deleted or '
                         'changed.',
 'patterns_status_label': 'Status',
 'patterns_comment_label': 'Comment (optional)',
 'patterns_save_review': 'Save assessment',
 'patterns_review_saved': 'Assessment saved.',
 'patterns_review_nothing': 'There is no change to save.',
 'patterns_history_header': 'History',
 'patterns_event_kinds': {'generated': 'Pattern generated',
                          'status_changed': 'Status changed',
                          'carried_over': 'Assessment carried over from an earlier search',
                          'member_excluded': 'Observation removed from the pattern',
                          'member_restored': 'Observation included again',
                          'explanation_regenerated': 'Explanation written again'},
 'patterns_event_status_change': '({old} → {new})',
 'patterns_event_system': 'System',
 'doc_import_label': 'Or upload a document (Word, PDF or text)',
 'doc_import_help': 'Only the text is read; the file itself is not saved. Up to {max_mb} MB, '
                    '{max_pages} pages and about {max_chars} characters. Scanned PDFs (photos of '
                    'paper) cannot be read.',
 'doc_import_loaded': 'Text loaded. Check and correct it before continuing. The file itself is not saved.',
 'doc_import_errors': {'unsupported': 'This type of file is not supported. Use Word (.docx), PDF '
                                      'or text (.txt).',
                       'too_large': 'The file is too large (maximum {max_mb} MB).',
                       'too_long': 'The document is too long (maximum about {max_chars} '
                                   'characters). Split it into parts and upload each one '
                                   'separately.',
                       'too_many_pages': 'The PDF has too many pages (maximum {max_pages}).',
                       'encrypted': 'The file is password-protected. Remove the protection and '
                                    'upload it again.',
                       'no_text': 'No text was found in the file. If it is a scanned PDF, copy the '
                                  'text by hand or use a version with text.',
                       'unreadable': 'The file could not be read. It may be damaged; try saving it '
                                     'again or paste the text.',
                       'unavailable': 'Reading this type of file is not available right now. '
                                      'Please paste the text directly.'},
 'report_doc_title': 'Report of candidate patterns for reflection',
 'report_confidential': 'Confidential document for the management team',
 'report_prepared': 'Prepared on {date}',
 'report_how_to_read_title': 'How to read this report',
 'report_how_to_read': 'This report lists candidate patterns: groups of similar observations the team may wish to discuss. They are not conclusions. A group of similar observations is not evidence of bias or poor practice, and the observations come from the reflections made in the app, so they do not necessarily represent the organisation. The team decides what each pattern means, if anything.',
 'report_search_title': 'The search it comes from',
 'report_search_line': 'Search of {date}: {observations} observations compared and {patterns} candidate pattern(s) found.',
 'report_filters_line': 'Search filters: {filters}',
 'report_no_filters': 'none',
 'report_statuses_line': 'Statuses included in this report: {statuses}',
 'report_summary_title': 'Summary',
 'report_col_pattern': 'Candidate pattern',
 'report_col_status': 'Status',
 'report_col_obs': 'Observations',
 'report_col_refl': 'Distinct reflections',
 'report_col_cases': 'Distinct cases',
 'report_pattern_heading': 'Pattern {n}: {title}',
 'report_no_patterns': 'There are no patterns with the selected statuses.',
 'report_team_comments': 'Team comments',
 'report_observations_omitted': 'Observations and quotations are not included in this report.',
 'report_quote_label': 'Exact quotation',
 'report_limits_title': 'Limits of this report',
 'report_limits_list': ['It is an automatic grouping by similarity of meaning; it may join unrelated observations or separate related ones.', 'The observations come from AI-assisted reflections made in the app; they are not a complete or representative record.', 'Case references are typed by hand: a typo can make one case count as two.', 'The explanatory text is written by AI from the observations and may reflect observations withdrawn after the search.', 'Nothing in this report identifies who wrote an observation or includes their private notes.'],
 'report_footer': 'Confidential · Candidate patterns for reflection, not conclusions · {date}',
 'report_section_header': 'Printable report',
 'report_section_intro': 'Creates a document to print or save as PDF with the patterns shown above '
                         '(according to the chosen statuses).',
 'report_opt_observations': 'Include the observations and their exact quotations',
 'report_opt_case_refs': 'Include case references (off by default: paper travels further than a '
                         'screen)',
 'report_opt_comments': 'Include the team comments',
 'report_prepare_button': 'Prepare report',
 'report_ready': 'Report prepared.',
 'report_download_button': 'Download report',
 'report_how_to_print': 'Open the downloaded file in your browser and press Ctrl+P (or Print) to '
                        'print it or save it as a PDF.',
 'report_outdated': 'You changed the search, the statuses or the options: prepare the report '
                    'again.',
 'rs_intro': 'Write, paste or upload the case you want to reflect on, and reflect on it straight away. Only an anonymised version of your text is sent to the AI. The original text is saved securely together with the reflection, for later pattern analysis.',
 'rs_code_label': 'Code for this reflection:',
 'rs_code_help': 'A neutral code created by the app. It does not identify anyone. Note it down if '
                 'you later want to link another reflection about the same situation.',
 'rs_note_type_label': 'Type of text',
 'rs_tags_label': 'Case themes (no personal details)',
 'rs_tags_placeholder': 'Choose one or more themes',
 'rs_tags_help': 'Tick up to {max} themes that describe the situation, never the person. They are '
                 'used later to find your reflections on similar situations.',
 'rs_tags_short_label': 'Themes',
 'rs_no_tags': 'No themes',
 'rs_previous_code_label': 'Does this continue an earlier reflection? (optional)',
 'rs_previous_code_placeholder': 'RS-XXXXXX',
 'rs_previous_code_help': "If you reflected on this same situation before, enter that reflection's "
                          'code here so it is taken into account. You can only link your own '
                          'reflections.',
 'rs_previous_code_invalid': "That code isn't in the right format. It should look like RS-7F3K2Q.",
 'rs_previous_code_not_found': 'No reflection of yours with the code {code} was found. Check the '
                               'code or leave the field empty.',
 'rs_previous_code_check_failed': "The earlier code couldn't be checked right now. Try again or "
                                  'leave the field empty.',
 'rs_case_text_label': 'Case text',
 'rs_case_text_placeholder': 'Write or paste the case here…',
 'rs_case_text_not_saved_note': '🔒 This text is not saved. It only exists while this reflection '
                                'lasts.',
 'rs_continue_button': 'Continue',
 'rs_case_text_review_label': 'Case text',
 'rs_similar_header': 'Your related earlier reflections',
 'rs_similar_intro': 'Your reflections linked to this one or sharing themes with it. Untick any '
                     "you don't want taken into account.",
 'rs_similar_none': 'You have no earlier reflections linked to this one or sharing its themes. The '
                    "reflection will use today's text only.",
 'rs_similar_failed': "Your earlier reflections couldn't be searched right now. You can continue: "
                      "the reflection will use today's text only.",
 'rs_similar_reason_linked': 'Linked as an earlier reflection on this situation',
 'rs_similar_reason_tags': 'Shared themes',
 'rs_similar_include_label': 'Take this reflection into account',
 'rs_similar_observations_label': 'See its observations',
 'rs_similar_used_label': 'Earlier reflections included',
 'rs_back_to_case_button': 'Back to the case',
 'rs_finish_header': 'Finish the reflection',
 'rs_finish_caption': 'Your reflection and your notes are saved under the code {code}. When you finish, the case text is cleared from this screen.',
 'rs_finish_caption_unsaved': "This reflection couldn't be saved. When you finish, the case text is cleared from this screen.",
 'rs_finish_button': 'Finish reflection',
 'rs_finished_success': '✔ Reflection finished. The case text has been cleared from this screen.',
 'rs_start_over_button': 'Start again',
 'ch_reflections_header': 'Saved reflections',
 'ch_reflections_intro': "Each reflection is shown with its neutral code and themes. The AI's observations are shown; never professionals' private notes. Original texts are not shown here: they can be read in Pattern Review, without author names.",
 'ch_tag_filter_label': 'Theme',
 'ch_all_tags': 'All themes',
 'ch_showing_recent': 'Showing the {shown} most recent of {total} reflections. Pick a date or '
                      'theme to narrow it down.',
 'ch_author_label': 'Done by',
 'ch_linked_label': 'Continues reflection',
 'ch_no_observations': 'This reflection has no saved observations.',
 'ch_delete_button': 'Delete reflection',
 'ch_delete_confirm': 'Are you sure you want to delete this reflection? Its observations and the '
                      'notes on them will be erased. This cannot be undone.',
 'ch_deleted_success': '✔ Reflection deleted.',
 'ch_delete_failed': '⚠ The reflection could not be deleted.',
 'case_tag_labels': {'housing': 'Housing / homelessness',
                     'employment_training': 'Employment and training',
                     'income_benefits': 'Income and benefits',
                     'mental_health': 'Mental health',
                     'physical_health': 'Physical health',
                     'addictions': 'Addictions',
                     'disability': 'Disability',
                     'family_relationships': 'Family relationships',
                     'children_youth': 'Children and young people',
                     'older_people': 'Older people',
                     'gender_violence': 'Gender-based violence',
                     'social_isolation': 'Loneliness / social isolation',
                     'migration_integration': 'Migration and integration',
                     'legal_administrative': 'Legal and administrative matters'},
 'rs_heading': "Let's reflect.",
 'rs_subheading': 'Take a moment to explore a situation from your professional practice.',
 'rs_material_label': 'Your reflection material',
 'rs_material_placeholder': 'Write or paste your text here. You can share a case situation, an '
                            'observation, a professional experience or something you would like to '
                            'explore...',
 'rs_file_loaded': 'Document read: **{name}**. To change it, remove it with the ✕ or upload '
                   'another.',
 'rs_both_inputs_notice': 'You have written some text and also uploaded a document. Which would '
                          'you like to reflect on?',
 'rs_source_label': 'Reflect on',
 'rs_source_options': {'text': 'My written text',
                       'file': 'The uploaded document',
                       'both': 'Both together'},
 'rs_choose_source_warning': 'Please choose which text you want to reflect on first.',
 'rs_need_material': 'Please write, paste or upload some text before pressing Reflect.',
 'rs_language_label': 'Reflection language',
 'rs_language_names': {'Español': 'Español', 'Euskera': 'Euskara', 'English': 'English'},
 'rs_privacy_note': '🛡️ Before anything is sent to the AI, names, exact ages and other personal '
                    'details are removed automatically.',
 'privacy_message_blocked': "We couldn't protect your message, so nothing was sent to the AI. "
                            'Please try again; if the problem continues, let the support team '
                            'know.',
 'rs_reflect_button': 'Reflect',
 'rs_anonymised_status': 'Your text has been anonymised.',
 'rs_preparing_status': 'Preparing your reflection...',
 'rs_anonymise_failed': "We couldn't protect your text, so nothing was sent to the AI. Your text "
                        'is still here. Please try again; if the problem continues, let the '
                        'support team know.',
 'rs_anonymised_preview_label': 'View anonymised text',
 'rs_anonymised_preview_help': 'Check the protected version of your material. This is exactly what '
                               'the AI received.',
 'rs_try_again_button': 'Try again with the same text',
 'rs_original_saved_note': '📁 The original text is kept securely (database in the EU) for up to {months} months, to help identify patterns in practice. Supervisors and programme managers may read it for that purpose, without your name. Only the anonymised version is sent to the AI.',
 'ch_show_anonymised_text': 'Show the saved anonymised text',
 'ch_anonymised_text_caption': 'The protected version the AI received (never the original text). '
                               'Deleted automatically after {months} months.',
 'ch_anonymised_text_unavailable': 'The anonymised text of this reflection is no longer available.',
 'ch_show_saved_text': 'Show the saved text',
 'ch_original_text_caption': 'The original text, as you wrote it. It is never sent to the AI and is deleted automatically after {months} months.',
 'ch_saved_text_unavailable': 'The text of this reflection is not available (it was not saved or has been deleted).',
 'ch_original_text_in_patterns_note': "📄 The original text of this reflection is saved. Supervisors and programme managers can read it in Pattern Review, without the author's name.",
 'patterns_texts_header': '📄 Saved original texts',
 'patterns_texts_caption': 'The original texts the reflections were made from, for studying patterns in how cases are written. Author names, reflection codes and exact times are never shown. Each text is deleted automatically after {months} months. These texts are confidential: do not copy them outside the app.',
 'patterns_texts_empty': 'No original texts have been saved yet.',
 'patterns_texts_showing': 'Showing the {shown} most recent of {total} saved texts.',
 'patterns_texts_item': 'Text from {date} · {language}',
 'rs_cards_hint': 'Choose any card to open it.',
 'rs_cards_choose': 'Choose a card to see its reflection.',
 'rs_card_explored': '✓ Explored',
 'rs_card_status': {'finding': 'Something to reflect on',
                    'none': 'Nothing notable found',
                    'unavailable': 'Not available right now, you can retry'},
 'my_reflections_header': 'Your saved reflections',
 'my_reflections_intro': 'You can delete any of your reflections. It disappears everywhere (for '
                         'managers and from pattern analysis too), with its observations, your '
                         'notes and its anonymised text. You can restore it for {hours} hours; '
                         'after that it is erased for good.',
 'my_reflections_empty': "You don't have any saved reflections yet.",
 'my_reflections_showing': 'Showing the {shown} most recent of {total}.',
 'my_reflections_line': '{date} · {count} observation(s)',
 'my_reflections_delete': 'Delete',
 'my_reflections_confirm': 'Delete reflection {code}? It will disappear everywhere. You can '
                           'restore it for {hours} hours.',
 'my_reflections_confirm_yes': 'Yes, delete',
 'my_reflections_confirm_cancel': 'Cancel',
 'my_reflections_deleted': 'Reflection {code} deleted. You can restore it for {hours} hours.',
 'my_reflections_restored': 'Reflection {code} restored.',
 'my_reflections_failed': "That didn't work. Please try again.",
 'my_reflections_deleted_header': 'Recently deleted',
 'my_reflections_restore': 'Restore',
 'my_reflections_erase_on': 'Will be erased for good on {date} (UTC).'}
