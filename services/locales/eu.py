"""Basque (Euskera) UI translation strings for Reflection Space.

Pure data -- no logic. Extracted verbatim from the original single-file
services/language.py (each value copied exactly, no rewording, no key
changes). See services/language.py for the language-selection and
fallback logic that consumes this dictionary.
"""

LANG_EU = {'title': '🧠 Hausnarketa Gunea',
 'doc': 'Dokumentazioa',
 'case_ref': 'Kasuaren erreferentzia',
 'doc_type': 'Dokumentu mota',
 'language': 'Hizkuntza',
 'text': 'Testua',
 'save': 'Gorde zirriborroa',
 'success': '✔ Zirriborroa ondo gorde da',
 'empty': 'Mesedez idatzi testua',
 'new': 'Dokumentu berria',
 'reflection': 'Hausnarketa gunea',
 'home_subtitle': 'Praktikan hausnartzeko gune bat.',
 'nav_hint': 'Erabili alboko barra nabigatzeko.',
 'nav_header': 'Nabigatu:',
 'nav_doc': '📝 Dokumentazioa',
 'nav_reflection': '🌿 Hausnarketa gunea',
 'no_drafts': 'Ez dago zirriborrorik eskuragarri.',
 'select_drafts': 'Hautatu hausnartzeko zirriborroak',
 'begin_reflection': 'Hasi hausnarketa',
 'reflection_folders_intro': 'Hausnartzeko dauden dokumentuak, kasuka multzokatuta.',
 'reflection_same_day_notice': '⚠️ Kasu honek egun bereko dokumentu bat baino gehiago ditu.',
 'reflection_no_case_ref': '(Kasu-erreferentziarik gabe)',
 'reflection_active_case_prefix': 'Hausnarketaren kodea:',
 'reflection_delete_button': 'Dokumentua ezabatu',
 'reflection_delete_confirm': 'Ziur zaude dokumentu hau ezabatu nahi duzula? Ekintza hau ezin da '
                              'desegin.',
 'reflection_deleted_success': '✔ Dokumentua ezabatu da.',
 'reflection_context_title': 'Hausnarketaren testuingurua',
 'reflection_context_current_label': 'Hautatutako dokumentua(k):',
 'reflection_context_historical_label': 'Kasu honetako dokumentu historiko garrantzitsuak:',
 'reflection_context_summary_strong': 'Hausnarketa honek gaurko kasua eta lotutako {count} aurreko '
                                      'hausnarketa erabiltzen ditu.',
 'reflection_context_summary_limited': 'Hausnarketa honek batez ere gaurko kasua erabiltzen du, '
                                       'lotutako aurreko hausnarketa gutxirekin.',
 'reflection_context_summary_none': 'Hausnarketa honek gaurko kasua bakarrik erabiltzen du.',
 'reflection_context_continue': 'Sortu hausnarketa',
 'reflection_context_back': 'Hautaketara itzuli',
 'reflection_partial_failure_notice': 'Hausnarketa-ikuspegi batzuk ({count}) ezin izan dira sortu. '
                                      'Hausnarketa hala ere sortu da. Hau berrikusteko '
                                      'erregistratu da. Eskuragarri dagoenarekin jarraitu dezakezu '
                                      'edo berriro saiatu.',
 'unknown_label': 'Ezezaguna',
 'audit_unknown_case_label': '(kasu ezezaguna)',
 'case_history_completed_label': 'amaituta',
 'themes': ['Pertsonaren ahotsa',
            'Ebidentzia vs. Interpretazioa',
            'Etiketak eta hizkera',
            'Balizko joerak',
            'Erabakien ebidentzia',
            'Falta den informazioa',
            'Indarguneak vs. Gabeziak',
            'Jarraitutasuna'],
 'section_labels': {'client_voice': 'Pertsonaren ahotsa',
                    'observation_vs_interpretation': 'Ebidentzia vs. Interpretazioa',
                    'labels_and_language': 'Etiketak eta hizkera',
                    'possible_bias': 'Balizko joerak',
                    'evidence_for_decisions': 'Erabakien ebidentzia',
                    'missing_information': 'Falta den informazioa',
                    'strengths_and_deficits': 'Indarguneak vs. Gabeziak',
                    'continuity': 'Jarraitutasuna'},
 'update_document': 'Eguneratu dokumentua',
 'edit_document_label': 'Editatu dokumentua hemen nahi baduzu',
 'submit_no_edit': 'Bidali editatu gabe',
 'submit_with_edit': 'Bidali aldaketekin',
 'submitted': '✔ Dokumentua bidalita',
 'error_parsing': '⚠ Ezin izan da hausnarketaren erantzuna prozesatu. Saiatu berriro.',
 'submit_draft_failed': '⚠ Ezin izan da dokumentua bidali. Saiatu berriro.',
 'delete_draft_failed': '⚠ Ezin izan da dokumentua ezabatu. Saiatu berriro.',
 'login_heading': '🔒 Hausnarketa Gunea',
 'username': 'Erabiltzaile-izena',
 'password_label': 'Pasahitza',
 'login_button': 'Hasi saioa',
 'login_error': 'Erabiltzaile-izena edo pasahitza okerra.',
 'login_locked': 'Saiakera huts gehiegi. Itxaron {minutes} minutu berriro saiatu aurretik.',
 'no_users_configured': 'Oraindik ez dago erabiltzaile-konturik konfiguratuta. Gehitu Ezarpenak → '
                        'Sekretuak atalean Streamlit Cloud-en.',
 'logout': 'Saioa itxi',
 'role_labels': {'Social Worker': 'Gizarte Langilea',
                 'Supervisor': 'Gainbegiralea',
                 'Programme Manager': 'Programaren Kudeatzailea',
                 'System Administrator': 'Sistemaren Administratzailea'},
 'admin_title': '🔒 Administrazioa',
 'admin_password_label': 'Pasahitza',
 'admin_enter_button': 'Sartu',
 'admin_incorrect_password': 'Pasahitz okerra.',
 'admin_visit_log': 'Bisiten erregistroa',
 'admin_no_visits': 'Oraindik ez dago bisitarik erregistratuta.',
 'admin_total_views_label': 'ikustaldi guztira',
 'admin_clear_log': 'Erregistroa garbitu',
 'admin_backfill_header': '🔄 Qdrant-en birindexatu',
 'admin_backfill_caption': 'Berreskuratze semantikoa (Hybrid RAG) aktibatu AURRETIK osatutako '
                           'dokumentuentzako embedding semantikoak sortzen ditu. Behin baino '
                           'gehiagotan exekutatzeko segurua: dokumentu bakoitza bere id-arekin '
                           'gainidazten da, ez da inoiz bikoiztuko. PostgreSQL ez da aldatzen.',
 'admin_backfill_button': 'Birindexatu osatutako dokumentu guztiak',
 'admin_backfill_running': '{current}/{total} dokumentua indexatzen...',
 'admin_backfill_done': '✔ Birindexatzea amaituta: {indexed}/{total} dokumentu Qdrant-en '
                        'indexatuta.',
 'admin_backfill_unavailable': 'Berreskuratze semantikoa oraindik ez dago konfiguratuta '
                               '(GEMINI_API_KEY edo QDRANT_URL falta da sekretuetan). '
                               'Aplikazioaren gainerakoak data araberako testuinguru '
                               'historikoarekin funtzionatzen jarraitzen du.',
 'admin_anon_header': 'Anonimizazio Demoa',
 'admin_anon_caption': 'Itsatsi lagin-testu bat (datu faltsuak soilik) sistematik Claude-ra iritsi '
                       'aurretik zer ateratzen den ikusteko. reflection_service.py fitxategian '
                       'erabiltzen den anonymize() funtzio bera exekutatzen du.',
 'admin_sample_label': 'Lagin-testua (datu faltsuak soilik)',
 'admin_run_button': 'Anonimizatzailea exekutatu',
 'admin_output_label': 'Irteera anonimizatua (Claude-ra bidaltzen dena):',
 'nav_case_history': '🗂️ Hausnarketen historia',
 'case_history_title': 'Hausnarketen historia',
 'case_history_no_items': 'Oraindik ez dago gordetako hausnarketarik.',
 'case_history_original_label': 'Jatorrizko bertsioa',
 'case_history_current_label': 'Uneko bertsioa',
 'case_history_edited_label': 'Editatua',
 'case_history_not_edited_label': 'Editatu gabe',
 'case_history_view_original_button': 'Jatorrizko bertsioa ikusi',
 'case_history_all_dates': 'Data guztiak',
 'submit_draft': 'Bidali',
 'admin_table_page': 'Orria',
 'admin_table_language': 'Hizkuntza',
 'admin_table_visited': 'Bisitatze data',
 'admin_sample_default': '2026/02/15ean, Sarah Kimani bezeroak, 9988776655 identifikazio-zenbakia '
                         'duenak, jarraipen-bilera batera joan zen. +254 722 334 455 zenbakian edo '
                         'sarah.kimani@testmail.com helbidean jar daiteke harremanetan. David '
                         'Otieno jauna izan zen esleitutako gizarte-langilea.',
 'case_history_date_filter_label': 'Historia ikusi:',
 'case_history_toggle_label': 'Erakutsi:',
 'case_history_edited_option': 'Editatuak',
 'case_history_not_edited_option': 'Editatu gabeak',
 'case_history_no_items_for_filter': 'Ez dago hausnarketarik hautapen honetarako.',
 'case_history_showing_recent': '{total} dokumentuetatik azken {shown} erakusten ari da. Erabili '
                                'data-iragazkia dokumentu zaharragoak ikusteko.',
 'feedback_prompt_title': 'Zenbateraino izan da baliagarria hausnarketa hau?',
 'feedback_rating_label': 'Balorazioa (1 = ez oso baliagarria, 5 = oso baliagarria)',
 'feedback_comment_label': 'Iruzkina (aukerakoa)',
 'feedback_submit_button': 'Balorazioa bidali',
 'feedback_skip_button': 'Saltatu',
 'feedback_thanks': '✔ Eskerrik asko zure balorazioagatik',
 'feedback_section_header': 'Profesionalen iruzkinak',
 'feedback_average_label': 'Batez besteko balorazioa',
 'feedback_no_items': 'Oraindik ez dago iruzkinik.',
 'case_history_delete_button': 'Kasua ezabatu',
 'case_history_delete_confirm': 'Ziur zaude kasu hau ezabatu nahi duzula? 48 orduz berreskura '
                                'dezakezu.',
 'case_history_delete_yes': 'Bai, ezabatu',
 'case_history_delete_cancel': 'Utzi',
 'case_history_deleted_success': '✔ Kasua ezabatu da. 48 orduz berreskura dezakezu.',
 'case_history_pending_deletion_header': 'Duela gutxi ezabatuak',
 'case_history_pending_deletion_no_items': 'Ez dago zain dagoen kasu ezabaturik.',
 'case_history_restore_button': 'Berreskuratu',
 'case_history_restored_success': '✔ Kasua berreskuratu da.',
 'case_history_deleted_by_label': 'Nork ezabatua',
 'nav_audit_log': '🧾 Auditoria-erregistroa',
 'audit_log_title': 'Auditoria-erregistroa',
 'audit_log_no_items': 'Oraindik ez dago auditoria-erregistrorik.',
 'audit_action_created': 'Sortua',
 'audit_action_submitted': 'Bidalia',
 'audit_action_deleted': 'Ezabatua',
 'audit_action_restored': 'Berreskuratua',
 'audit_action_purged': 'Behin betiko ezabatua',
 'workspace_opportunities_header': 'Hausnarketa aukerak',
 'workspace_document_header': 'Kasuaren testua',
 'workspace_context_header': 'Hausnarketaren testuingurua',
 'workspace_progress_label': 'Aztertuta: {explored} / {total}',
 'workspace_explore_button': 'Aztertu laguntzailearekin',
 'workspace_more_header': 'Zergatik galdera hauek? Ikusi IAk zer nabaritu duen',
 'workspace_questions_header': 'Hausnartzeko galderak',
 'rs_info_header': 'Hausnarketaren informazioa',
 'workspace_close_button': 'Itxi',
 'workspace_explored_badge': '🗨️ Aztertuta',
 'workspace_conversation_input_label': 'Zure hausnarketa',
 'workspace_conversation_placeholder': 'Idatzi zure erantzuna edo galdera hemen...',
 'workspace_send_button': 'Bidali',
 'workspace_ai_thinking': 'Pentsatzen...',
 'workspace_conversation_error': '⚠ Ezin izan da elkarrizketarekin jarraitu. Saiatu berriro.',
 'workspace_reminder': 'Hau hausnartzeko gonbidapen bat besterik ez da. Aztertzea, eta '
                       'dokumentazioan zerbait aldatzea, erabat zure erabaki profesionalaren '
                       'araberakoa da.',
 'nav_growth': '🌱 Nire Hausnarketa',
 'growth_title': '🌱 Zure Hausnarketa Bidea',
 'growth_intro': 'Hau zure gune pertsonala da. Ez da zure jardunaren ebaluazioa eta ez da inoiz '
                 'beste profesional batzuekin konparatzen. Elkarrizketetan aztertzen duzuna eta '
                 'zure oharrak zureak bakarrik dira. Zure hausnarketen gordetako behaketak (eta '
                 'haien testu anonimizatua) arduradunek ere ikus ditzakete Hausnarketen historian.',
 'growth_no_data': 'Oraindik ez duzu hausnarketarik aztertu. Hausnarketa Gunean «Aztertu '
                   'laguntzailearekin» botoia erabili ahala, zure bidea hemen agertuko da.',
 'growth_themes_header': 'Gehien aztertu dituzun arloak',
 'growth_themes_caption': 'Erregistratutako {total} azterketa-unetan oinarrituta',
 'growth_history_header': 'Duela gutxiko hausnarketa-uneak',
 'growth_entry_line': '**{theme}** — {case} hausnarketa — {count} truke — {date}',
 'growth_session_count_label': 'Guztira erregistratutako azterketa-uneak',
 'journey_step1': 'Zure kasua',
 'journey_step2': 'Aurreko hausnarketak',
 'journey_step3': 'Hausnarketa Profesionala',
 'journey_step4': 'Hausnarketa Galderak',
 'journey_step1_desc': 'Hausnartu nahi duzun kasua idatzi, itsatsi edo igotzen duzu.',
 'journey_step2_desc': 'Lotutako edo gai komunak dituzten zure aurreko hausnarketak bilatzen dira.',
 'journey_step3_desc': 'IAk gaurko kasua aztertzen du, barne hartu dituzun aurreko hausnarketekin '
                       'batera.',
 'journey_step4_desc': 'Hausnarketa galderak kontsideratzeko gonbidatzen zaitu.',
 'historical_timeline_header': 'Denbora-lerro historikoa',
 'historical_timeline_intro': 'Kasu honetako dokumentu garrantzitsuak, kronologikoki ordenatuta.',
 'timeline_today_label': '📍 Gaurko dokumentazioa',
 'dashboard_navigator_hint': 'Erabili fitxak hausnarketa-arloen artean mugitzeko orri osoan zehar '
                             'joan gabe.',
 'coverage_header': 'Hausnarketaren estaldura',
 'coverage_intro': 'Honek berresten du dimentsio bakoitza kontuan hartu dela hausnarketa honetan — '
                   'ez da puntuaziorik edo ebaluaziorik.',
 'coverage_considered': 'Aztertuta',
 'coverage_unavailable': 'Ezin izan da sortu oraingoan',
 'history_link_hint': 'Zure aurreko hausnarketak berrikusi nahi dituzu? Zure hausnarketa-bide '
                      'pertsonala hemen dago eskuragarri:',
 'workmode_switch_label': 'Lan modua',
 'workmode_practitioner': 'Praktika',
 'workmode_manager': 'Kudeaketa / Gainbegiratzea',
 'workmode_admin': 'Sistemaren Administrazioa',
 'workmode_access_denied': 'Ez duzu lan-espazio honetarako sarbiderik.',
 'nav_system_admin': '🛠️ Sistemaren Administrazioa',
 'admin_user_mgmt_header': '👥 Erabiltzaileen kudeaketa',
 'admin_user_mgmt_info': 'Erabiltzaileak Streamlit Sekretuen bidez kudeatzen dira. CRUD dinamikoa '
                         'ez dago nahita eskuragarri: kredentzialak eta rolak '
                         'zabalkunde-sekretuetan konfiguratzen dira, ez aplikazioaren tauletan.',
 'admin_user_mgmt_empty': 'Oraindik ez dago erabiltzailerik konfiguratuta. Gehitu Ezarpenak → '
                          'Sekretuak atalean Streamlit Cloud-en.',
 'admin_user_col_username': 'Erabiltzaile-izena',
 'admin_user_col_name': 'Izena',
 'admin_user_col_role': 'Rola',
 'admin_advanced_diagnostics': '🔧 Diagnostiko aurreratua',
 'admin_show_raw_response': 'Erakutsi erantzun gordina',
 'admin_status_connected': 'Konektatuta',
 'admin_status_not_connected': 'Konektatu gabe',
 'admin_status_present': '✅ Presente',
 'admin_status_missing': '❌ Falta da',
 'admin_health_header': '💚 Sistemaren osasuna',
 'admin_health_overall': '#### Egoera orokorra',
 'admin_health_critical': '🔴 Kritikoa',
 'admin_health_degraded': '🟡 Degradatuta (berreskuratze semantikoa ez dago konfiguratuta — '
                          'aplikazioa data araberako moduan dabil)',
 'admin_health_healthy': '🟢 Osasuntsua',
 'admin_health_components': '#### Osagaiak',
 'admin_health_component_col': 'Osagaia',
 'admin_health_status_col': 'Egoera',
 'admin_health_component_database': 'Datu-basea',
 'admin_health_component_embedding': 'Embedding zerbitzua (Gemini API)',
 'admin_health_component_reflection': 'Hausnarketa motorra (Claude API)',
 'admin_health_healthy_label': 'Osasuntsua',
 'admin_health_unreachable_label': 'Ezin da atzitu',
 'admin_health_available_label': 'Eskuragarri',
 'admin_health_not_configured_label': 'Konfiguratu gabe',
 'admin_health_operational_label': '✅ Funtzionamenduan',
 'admin_health_db_error_prefix': 'Datu-base errorea:',
 'admin_health_key_missing': 'ANTHROPIC_API_KEY ez dago konfiguratuta — ezin dira hausnarketak '
                             'sortu.',
 'admin_tools_header': '🧰 Administrazio-tresnak',
 'admin_anon_empty_warning': 'Idatzi edo itsatsi lehenik lagin-testu bat eta sakatu berriro '
                             'botoia.',
 'admin_anon_no_changes': 'Anonimizatzaileak ez du ordezkatzeko datu pertsonalik aurkitu testu '
                          'honetan.',
 'admin_anon_stale_note': 'Testua aldatu duzu azken probatik: sakatu berriro botoia emaitza '
                          'eguneratua ikusteko.',
 'admin_anon_tags_help': 'Etiketak: [PERSON] = pertsona-izena · [LOCATION] = tokia · [ADDRESS] = '
                         'helbidea · [ORGANISATION] = zentroa edo erakundea · [ID] = NAN/AIZ, '
                         'espedientea, kontua edo beste identifikatzaile bat · [PHONE] = telefonoa '
                         '· [EMAIL] = posta elektronikoa · [DATE] = data · [AGE_…] = adin '
                         'zehatza, bizitzako etapa batekin ordezkatua (INFANT = haurtxoa, CHILD = '
                         'haurra, ADOLESCENT = nerabe adingabea, YOUNG_ADULT = heldu gaztea, ADULT = '
                         'heldua, OLDER_ADULT = adinekoa).',
 'admin_tools_anon_test_header': 'Anonimizazio proba',
 'admin_tools_future': 'Etorkizuneko administrazio-tresnak hemen agertuko dira.',
 'admin_console_caption': 'Reflection Space-ren administrazio-kontsola -- erabiltzaileak, '
                          'sistemaren egoera, erregistratutako arazoak, kostuak eta datuen '
                          'ezabaketa.',
 'admin_error_log_unknown_page': 'orrialde ezezaguna',
 'admin_error_log_no_message': '(mezurik ez)',
 'event_labels': {'Opened page': 'Orria irekita',
                  'Changed page': 'Orria aldatuta',
                  'Email sent': 'Posta elektronikoa bidalita',
                  'User submitted report': 'Erabiltzaileak bidalitako txostena',
                  'Exception occurred': 'Salbuespen bat gertatu da',
                  'Error logged': 'Errorea erregistratuta'},
 'admin_error_log_caption': 'Aplikazioan erregistratutako arazoen zerrenda (hutsegiteak, IAren '
                            'dei hutsak edo erabiltzaileek jakinarazitako arazoak): zer gertatu '
                            'den, noiz eta zein egoeratan dagoen. IAren diagnostikoa alerta-mezu '
                            'elektronikoan iristen da.',
 'admin_problem_what_label': 'Zer gertatu da',
 'admin_problem_open_header': 'Arazo irekiak ({n})',
 'admin_problem_solved_header': 'Konpondutako arazoak ({n})',
 'admin_problem_none_open': 'Ez dago arazo irekirik.',
 'admin_reset_header': '🧹 Ezabatu datu guztiak',
 'admin_reset_intro': 'Aplikazioan gordetako guztia behin betiko ezabatzen du: hausnarketak eta '
                      'haien testuak, behaketak eta oharrak, balorazioak, patroien berrikuspenak, '
                      'dokumentu zaharrak, jardueraren historia, erregistratutako arazoak eta '
                      'erabilera- eta kostu-erregistroak. Aplikazioko zenbatzaile guztiak 0ra '
                      'itzultzen dira.',
 'admin_reset_kept_note': 'Erabiltzaile-kontuak eta konfigurazioa mantentzen dira. Inork ez du '
                          'saioa berriro hasi beharko.',
 'admin_reset_warning': 'Ekintza hau ezin da desegin.',
 'admin_reset_confirm_word': 'EZABATU',
 'admin_reset_confirm_label': 'Berresteko, idatzi {word}',
 'admin_reset_button': 'Ezabatu datu guztiak',
 'admin_reset_done': 'Datu guztiak ezabatu dira. Aplikazioa zerotik hasten da.',
 'admin_reset_refused': 'Sistemaren administratzaileak bakarrik egin dezake hau.',
 'admin_reset_failed': 'Ezin izan da ezabaketa osatu. Ez da ezer ezabatu. Saiatu berriro.',
 'admin_error_log_empty': 'Ez dago arazorik erregistratuta. Dena ondo dago.',
 'admin_error_log_first_seen_label': 'Lehen aldiz ikusia',
 'admin_error_log_header': '🩺 Diagnostiko Gunea',
 'admin_translation_health_header': '🌐 Itzulpen-sistemaren egoera',
 'admin_translation_health_caption': 'Español / Euskera / English itzulpen-sistemaren egoera '
                                     'zuzenean.',
 'admin_translation_autofilled_warning': 'Abioan {count} itzulpen-gako automatikoki bete dira '
                                         'behin-behineko testuarekin.',
 'admin_translation_autofilled_details': 'Ikusi automatikoki betetako gakoak',
 'admin_translation_copied_from': 'hemendik kopiatua:',
 'admin_translation_in_sync': 'Hiru hizkuntzak sinkronizatuta daude. Ez zen ezer bete behar.',
 'admin_translation_runtime_gaps': '⚠️ Saio honetan exekuzio-denboran falta izan diren gakoak '
                                   '({count})',
 'admin_translation_panel_error': 'Une honetan ezin izan da itzulpen-egoeraren panela kargatu.',
 'admin_error_log_occurrences_label': 'Gertaerak',
 'admin_error_log_page_label': 'Orria',
 'admin_error_log_status_label': 'Egoera',
 'admin_error_log_when_label': 'Noiz',
 'error_boundary_body': 'Hau {ref} errore gisa erregistratu da. Saiatu berriro -- gertatzen '
                        'jarraitzen badu, esan zure administratzaileari goiko erreferentzia '
                        'zenbakia.',
 'error_boundary_heading': 'Zerbait gaizki joan da orrialde honetan.',
 'rate_limit_exceeded_message': 'Kontu honetan azken orduan {max} hausnarketaren muga bete duzu. '
                                'Hau segurtasun-muga bat da nahi gabeko eskaera errepikatuak '
                                'saihesteko, ez zure ohiko lanaren murrizketa bat -- itxaron pixka '
                                'bat eta saiatu berriro, edo jarri harremanetan Sistemaren '
                                'Administratzailearekin hau errore bat dela uste baduzu.',
 'reflection_duplicate_message': 'Hausnarketa hau jadanik sortzen ari da. Itxaron pixka bat amaitu '
                                 'arte, berriro saiatu aurretik.',
 'report_problem_caption': 'Zerbait ez al dabil ondo? Deskribatu behean. Zure administratzaileari '
                           'berehala jakinaraziko zaio.',
 'report_problem_description_label': 'Zer gertatu da?',
 'report_problem_empty_warning': 'Gehitu deskribapen labur bat bidali aurretik.',
 'report_problem_header': '🚩 Arazo bat jakinarazi',
 'report_problem_send_button': 'Txostena bidali',
 'report_problem_sent': '✔ Txostena bidalita. Eskerrik asko -- zure administratzaileari jakinarazi '
                        'zaio.',
 'status_labels': {'New': 'Berria',
                   'Investigating': 'Ikertzen',
                   'Recurred': 'Berragertua',
                   'Fixed': 'Konponduta',
                   'Closed': 'Itxita',
                   'All': 'Guztiak',
                   'Any': 'Edozein'},
 'severity_labels': {'All': 'Guztiak',
                     'error': 'Errorea',
                     'warning': 'Abisua',
                     'user_reported': 'Erabiltzaileak jakinarazia'},
 'help': {'nav_label': '❓ Laguntza',
          'page_title': 'Reflection Spaceren gida azkarra',
          'intro_title': 'Zer da Reflection Space?',
          'intro_body': 'Reflection Spacek kasu bati buruz une berean hausnartzen laguntzen dizu: '
                        'kasua idatzi, itsatsi edo igotzen duzu eta hausnarketarako galderak '
                        'eskaintzen dizkizu zortzi dimentsio profesionaletan -- adibidez, '
                        'erabiltzailearen ahotsa agertzen den, edo zailtasunen ondoan haren '
                        'indarguneak ahazten ari diren. Ez da dokumentuak gordetzeko lekua: '
                        'hausnarketa bakarrik gordetzen da.',
          'guardrail_note': 'Tresnak ez du inoiz ezer kalifikatzen, puntuatzen edo zure ordez '
                            'erabakitzen. Zuk erabakitzen duzu zer egin, ezer egitekotan, '
                            'pentsarazi dizunarekin.',
          'journey_title': 'Nola dabilen',
          'journey_steps': ['1. Hausnar dezagun -- idatzi edo itsatsi zure testua, edo igo dokumentu bat (Word, PDF edo testua). Ez da erreferentziarik, testu motarik edo gairik behar.', '2. Aukeratu hausnarketaren hizkuntza (Español, Euskara edo English) eta sakatu Hausnartu. Testua automatikoki anonimizatzen da AAk jaso aurretik.', '3. Hausnarketa profesionala -- arakatu zortzi dimentsio erreflexiboak, hitz egin labur haietako bati buruz nahi baduzu, gehitu zure oharrak eta amaitu. Ondoren, kasuaren testua pantailatik kentzen da.'],
          'practitioner_title': 'Profesionalaren area',
          'doc_section_title': '📝 Zure kasua -- idatzi, itsatsi edo igo',
          'doc_section_body': 'Reflection Spacen zure testua koadro bakar batean idatzi edo itsasten duzu, edo Word, PDF edo testu bat igotzen duzu (testua bakarrik irakurtzen da; fitxategia ez da gordetzen). Testu bat idatzi eta dokumentu bat ere igotzen baduzu, zeri buruz hausnartu nahi duzun galdetuko zaizu. Ez duzu kasuaren erreferentziarik edo daturik eman behar: aplikazioak berak sortzen du kode neutro bat (adibidez RS-7F3K2Q), inor identifikatzen ez duena. Jatorrizko testua modu seguruan gordetzen da, geroago ereduak aztertzeko (ikus behean).',
          'original_saved_note': 'Jatorrizko testua modu seguruan gordetzen da EBko datu-base batean, gehienez {months} hilabetez, praktikako ereduak antzemateko. AAri bertsio anonimizatua bakarrik bidaltzen zaio. Zure testua Nire hausnarketan irakur dezakezu; gainbegiraleek eta programa-arduradunek testuak Patroien berrikuspenean irakur ditzakete, egilearen izenik gabe. Denbora hori igarotakoan automatikoki ezabatzen da; hausnarketak bere horretan jarraitzen du.',
          'reflection_section_title': '🪞 Reflection Space -- une berean hausnartu',
          'reflection_section_body': 'Hausnartu sakatzean, zure testua automatikoki anonimizatzen da '
                                     '(izenak eta beste datu pertsonal batzuk kentzen dira) eta bertsio '
                                     'babestu hori bakarrik bidaltzen zaio AAri. Anonimizazioak huts egingo '
                                     'balu, ez da ezer bidaltzen. Emaitzetan, «Ikusi testu anonimizatua» '
                                     'aukerak AAk jaso zuena erakusten dizu. Arakatu zortzi dimentsioetako '
                                     'edozein, ireki elkarrizketa labur bat nahi baduzu, gehitu zure '
                                     'oharrak eta sakatu Amaitu hausnarketa. Ondoren saioaren '
                                     'erabilgarritasuna balora dezakezu -- guztiz aukerakoa.',
          'cards_note': 'Zortzi hausnarketa-aukerak txartel gisa agertzen dira ikuspegi bakarrean. Izkinako '
                         'puntuak bakoitzak zer aurkitu duen adierazten du: berdea, badago zer hausnartu; '
                         'grisa, ezer nabarmenik ez testu honetan; laranja, orain ez dago erabilgarri '
                         '(txartelaren barruan berriro saia zaitezke). Txartel bat irekitzean galderak '
                         'ikusten dituzu; IAk nabaritu duena eta oinarri duen pasartea «Zergatik galdera '
                         'hauek?» atalean daude.',
          'dimensions_title': 'Zortzi gogoeta-dimentsioak',
          'dimensions': [{'label': 'Pertsonaren ahotsa',
                          'desc': 'Pertsonaren ahotsa, helburuak eta hobespenak presente al daude, '
                                  'edo narrazioa batez ere profesionalarengandik dator?'},
                         {'label': 'Behaketa vs interpretazioa',
                          'desc': 'Behatutako gertakari gisa aurkeztutako baieztapenak, egiazki '
                                  'interpretazio, suposizio edo iritzi al dira batzuk?'},
                         {'label': 'Etiketak eta hizkuntza',
                          'desc': 'Badira etiketa edo termino kargatuak pertsona edo familia hau '
                                  'nola hautematen den isilean bideratu dezaketenak?'},
                         {'label': 'Balizko alborapena',
                          'desc': 'Badira jatorriarekin, generoarekin, adinarekin, '
                                  'migrazio-egoerarekin, osasun mentalarekin edo substantzien '
                                  'kontsumoarekin lotutako estereotipo edo aztertu gabeko '
                                  'suposizioak?'},
                         {'label': 'Erabakietarako ebidentzia',
                          'desc': 'Interbentzio-erabakiak ebidentziaz argi babestuta al daude, ala '
                                  'suposizio inplizituetan oinarritzen dira?'},
                         {'label': 'Falta den informazioa',
                          'desc': 'Ba al da informazio garrantzitsurik falta, egoera ulertzeko '
                                  'modua alda lezakeena?'},
                         {'label': 'Indarguneak vs gabeziak',
                          'desc': 'Hizkuntza batez ere arazo eta gabezietan zentratzen al da, '
                                  'pertsonaren indarguneak eta baliabideak alboratuz?'},
                         {'label': 'Jarraitutasuna',
                          'desc': 'Badira kontraesan edo aldaketa nabarmenik dokumentu honen eta '
                                  'aurrekoen artean?'}],
          'delete_note': 'Zure hausnarketetako edozein ezaba dezakezu «Zure gordetako hausnarketak» '
                          'ataletik, Nire hausnarketa orriaren amaieran. Berehala desagertzen da leku '
                          'guztietatik; {hours} orduz berreskura dezakezu eta ondoren behin betiko ezabatzen '
                          'da.',
          'growth_section_title': '🌱 Nire Gogoeta -- zure egunkari pertsonala',
          'growth_section_body': 'Nire hausnarketa zure gune propioa da: gehien aztertu dituzun gaiak, zure '
                                  'hausnarketa-uneen denbora-lerroa, gordetako behaketak zure oharrekin eta '
                                  'zure hausnarketen zerrenda (ezaba ditzakezunak). Puntuaziorik eta '
                                  'inorekiko konparaziorik gabe. Zure oharrak eta aztertzen duzuna zureak '
                                  'bakarrik dira; gordetako behaketak arduradunek ere ikus ditzakete.',
          'manager_title': 'Zuzendaritza-taldearen area',
          'case_history_section_title': '🗂️ Hausnarketen historia',
          'case_history_section_body': 'Hausnarketen historiak erabilgarritasunaren batez besteko '
                                       'balorazioa erakusten du (inoiz ez banakako balorazioak, '
                                       'ezta nork eman dituen ere) eta gordetako hausnarketak, '
                                       'bakoitza bere kode neutroarekin, gaiekin eta IAren '
                                       'behaketekin. Data eta gaiaren arabera iragazi daiteke. Ez '
                                       'ditu inoiz profesionalen ohar pribatuak erakusten.',
          'admin_title': '🛠️ Sistemaren administrazioa',
          'admin_section_body': 'Sistemaren administrazioak biltzen ditu erabiltzaileen zerrenda, '
                                'sistemaren egoera, anonimizazio-proba, itzulpenen '
                                'osasun-egiaztapenak, Diagnostiko Gunea (erregistratutako arazoen '
                                'zerrenda) eta zerbitzuen erabilera eta kostuak. Gordetako datu '
                                'guztiak behin betiko ezabatzeko aukera ere ematen du, zerotik '
                                'hasteko.',
          'report_problem_title': '🚩 Arazo bat jakinaraztea',
          'report_problem_body': 'Orri bakoitzak 🚩 Arazo bat jakinarazi kontrol bat du alboko '
                                 'barran, edonorentzat eskuragarri. Deskribatu gertatutakoa zure '
                                 'hitzekin eta sakatu Bidali -- sistemak automatikoki gehitzen '
                                 'ditu orriaren, saioaren eta nabigazioaren datuak.',
          'privacy_title': '🔒 Pribatutasuna eta datuak',
          'privacy_points': ['Kasuaren jatorrizko testua modu seguruan gordetzen da EBko datu-base batean denbora mugatu batez, ereduak aztertzeko -- AAri bertsio anonimizatua bakarrik bidaltzen zaio, eta gainbegiraleek eta programa-arduradunek zure izenik gabe irakurtzen dute.', 'Hausnarketa bakoitza kode neutro batekin eta datu pertsonalik gabeko gaiekin identifikatzen da, inoiz ez izenekin.', 'Behaketei buruzko zure oharrak pribatuak dira -- zuk bakarrik ikus ditzakezu. IAren behaketak kudeaketa-taldearen patroien berrikuspenean erabiltzen dira, zure izenik gabe.', 'Elkarrizketa erreflexiboen edukia ez da inoiz saiotik haratago gordetzen -- zein gai arakatu zen eta noiz bakarrik erregistratzen da.', 'Nire Hausnarketa pertsonala da eta ez du konparaziorik onartzen: puntuaziorik gabe, sailkapenik gabe, zuk bakarrik ikus dezakezu.', 'Roletan oinarritutako sarbide-kontrola bi mailatan aplikatzen da aplikazio osoan.']},
 'admin_usage_header': '💰 Zerbitzuen Erabilera eta Kostuak',
 'admin_usage_caption': 'Kanpoko zerbitzu bakoitzak proiektu pilotu honetan zenbat kostatzen duen, '
                        'egiazko APIen erabileratik estimatuta. "Estimazioa" gisa markatutako '
                        'zifrak ezin izan dira hornitzailearen prezio zehatzarekin lotu eta '
                        'hurbilketatzat hartu behar dira.',
 'admin_usage_status_green': '🟢 Egoera ona',
 'admin_usage_status_yellow': '🟡 Mugara hurbiltzen',
 'admin_usage_status_orange': '🟠 Mugatik gertu',
 'admin_usage_status_red': '🔴 Mugan edo gainditua',
 'admin_usage_status_unknown': '⚪ Muga ez dago eskuragarri',
 'admin_usage_unavailable': 'Ez dago eskuragarri',
 'admin_usage_limit_unavailable': 'Muga ez dago eskuragarri',
 'admin_usage_overview_header': 'Laburpena',
 'admin_usage_col_service': 'Zerbitzua',
 'admin_usage_col_usage': 'Erabilera (hilabete honetan)',
 'admin_usage_col_limit': 'Aurrekontua',
 'admin_usage_col_pct': '% erabilia',
 'admin_usage_col_cost': 'Kostu estimatua (hilabetea)',
 'admin_usage_col_status': 'Egoera',
 'admin_usage_no_billing_api': 'Fakturazio APIrik ez',
 'admin_usage_connections': 'konexioak',
 'admin_usage_not_started': 'Oraindik hasi gabe',
 'admin_usage_provider_billing_unavailable': 'Hornitzailearen fakturazio-datuak ez daude '
                                             'eskuragarri',
 'admin_usage_active_users': 'erabiltzaile aktibo',
 'admin_usage_emails_sent': 'posta elektroniko bidalita',
 'admin_usage_claude_detail_header': 'Claude-ren (Anthropic) xehetasuna',
 'admin_usage_cost_today': 'Gaurko kostu estimatua',
 'admin_usage_cost_month': 'Hilabete honetako kostu estimatua',
 'admin_usage_cost_projected': 'Hilabete amaierarako kostu proiektatua',
 'admin_usage_input_tokens': 'Sarrerako token-ak (hilabetea)',
 'admin_usage_output_tokens': 'Irteerako token-ak (hilabetea)',
 'admin_usage_model_unrecognized': '⚠️ Deialdi batzuek prezio-taulan ez dagoen eredu bat erabili '
                                   'dute; horien kostua babeseko estimazio bat da.',
 'admin_usage_anthropic_not_configured': 'Anthropic APIaren gakoa ez dago konfiguratuta.',
 'admin_usage_per_reflection_header': 'Hausnarketa bakoitzeko kostua',
 'admin_usage_avg_cost_reflection': 'Claude-ren batez besteko kostua hausnarketa bakoitzeko',
 'admin_usage_reflections_generated': 'Sortutako hausnarketak (30 egun)',
 'admin_usage_companion_calls': 'Laguntzaileen deiak (30 egun, saiakerak barne)',
 'admin_usage_retry_rate': 'Berrsaiatze-tasa',
 'admin_usage_no_median_note': 'Ez dago medianarik eskuragarri: laguntzaile bakoitzaren deiak ez '
                               'daude oraindik dagokien hausnarketarekin etiketatuta, beraz batez '
                               'besteko orokorra bakarrik kalkula daiteke.',
 'admin_usage_gemini_detail_header': 'Gemini Embeddings-en xehetasuna',
 'admin_usage_embeddings_month': 'Embedding-ak hilabete honetan',
 'admin_usage_embeddings_failed': 'Huts egindako embedding eskaerak (hilabetea)',
 'admin_usage_gemini_estimate_note': '⚠️ Embedding dei batzuek ez dute hornitzailearen '
                                     'token-kopuru zehatzik itzuli; horien kostua estimazio gisa '
                                     'markatzen da.',
 'admin_usage_gemini_not_configured': 'Gemini APIaren gakoa ez dago konfiguratuta.',
 'admin_usage_pricing_header': 'Prezioen eta aurrekontuen konfigurazioa',
 'admin_usage_pricing_caption': 'Hornitzaileen prezioak leku bakarrean daude zentralizatuta '
                                '(services/cost_pricing.py), hornitzaile batek tarifak aldatzean '
                                'kodean zehar bilatu behar ez izateko. Goiko egoera-koloreetarako '
                                'erabiltzen diren hileko aurrekontuak config.py fitxategian '
                                'konfiguratzen dira (MONTHLY_BUDGET_ANTHROPIC_USD, '
                                'MONTHLY_BUDGET_GEMINI_USD).',
 'admin_usage_forecast_header': 'Erabiltzaile-bolumenaren aurreikuspena (estimazioa)',
 'admin_usage_forecast_caption': 'Hileko kostua proiektatzen du erabiltzaile-kopuru hipotetiko '
                                 'baterako, proiektu pilotu honetan neurtutako hausnarketa '
                                 'bakoitzeko batez besteko kostuan oinarrituta. Doitu beheko '
                                 'zenbakiak.',
 'admin_usage_forecast_users': 'Erabiltzaile kopurua',
 'admin_usage_forecast_reflections': 'Hausnarketak erabiltzaileko eta hilabeteko',
 'admin_usage_forecast_total_reflections': 'Hausnarketa guztiak/hilabete',
 'admin_usage_forecast_claude_cost': 'Claude-ren kostu proiektatua/hilabete',
 'admin_usage_forecast_gemini_cost': 'Gemini-ren kostu proiektatua/hilabete',
 'admin_usage_forecast_presets_header': 'Ohiko eszenatokiak',
 'admin_usage_forecast_current': 'Uneko',
 'admin_usage_forecast_col_users': 'Erabiltzaileak',
 'admin_usage_forecast_col_reflections': 'Hausnarketak/hilabete',
 'admin_usage_forecast_col_claude_cost': 'Claude-ren kostu estimatua/hilabete',
 'admin_usage_forecast_estimate_disclaimer': '⚠️ Goiko proiekzio guztiak ESTIMAZIOAK dira, gaur '
                                             'egun behatutako batez bestekoetan oinarrituta, ez '
                                             'bermatutako kosteak.',
 'findings_evidence_caption': 'Behaketa honen oinarri den kasuaren testuko pasartea:',
 'findings_unverified_notice': 'IAk proposatutako {count} pasarte ez datoz testuarekin zehazki '
                               'bat, eta ez dira erakusten.',
 'findings_notes_header': 'Nire oharrak',
 'findings_label_prompt': 'Zer iruditu zaizu?',
 'findings_label_none': 'Baloratu gabe',
 'findings_labels': {'useful': 'Baliagarria',
                     'not_relevant': 'Garrantzirik gabea',
                     'uncertain': 'Ez daukat argi',
                     'discuss': 'Geroago komentatzeko'},
 'findings_misread_label': 'Uste dut IAk ez duela testuingurua ondo ulertu',
 'findings_alternative_label': 'Beste azalpen posible bat (aukerakoa)',
 'findings_note_label': 'Nire hausnarketa edo oharra (aukerakoa)',
 'findings_save_button': 'Gorde nire oharrak',
 'findings_save_success': 'Oharrak gorde dira.',
 'findings_save_error': 'Ezin izan dira zure oharrak gorde. Saiatu berriro une batean.',
 'findings_not_saved_notice': 'Hausnarketa hau ezin izan da gorde; beraz, ezingo dituzu horri '
                              'buruzko oharrak gorde. Normaltasunez jarrai dezakezu lanean.',
 'findings_journal_header': 'Gordetako behaketak eta zure oharrak',
 'findings_journal_intro': 'Hemen zure hausnarketetako behaketetara itzul zaitezke, oinarri '
                           'dituzten pasarte zehatzekin, eta zure oharrak idatzi edo berrikusi. '
                           'Zure oharrak zuretzat bakarrik dira.',
 'findings_journal_empty': 'Oraindik ez dago gordetako behaketarik. Zure hurrengo hausnarketaren '
                           'ondoren agertuko dira hemen.',
 'findings_journal_count': '{total} gordetako behaketa — {page}. orria ({pages} orritik)',
 'findings_journal_count_reflections': '{total} hausnarketa — {page}. orria ({pages} orritik)',
 'findings_reflection_line': '{code} — {date} — {count} behaketa',
 'findings_reflection_notes_suffix': '· ✔ {count} oharrekin',
 'findings_pick_observation': 'Aukeratu behaketa bat',
 'findings_journal_newer': '← Berrienak',
 'findings_journal_older': 'Zaharrenak →',
 'nav_patterns': '🔎 Patroien berrikuspena',
 'findings_notes_privacy': 'Zure oharrak eta balorazioak pribatuak dira: zuk bakarrik ikus ditzakezu. IAk esandakotik bereizita gordetzen dira, eta hori ez da inoiz aldatzen. IAren behaketak (inoiz ez zure izena edo oharrak) kudeaketa-taldearen patroien berrikuspenean erabiltzen dira. Gordetzean, izenak, adin zehatzak eta beste datu pertsonal batzuk kentzen dira zure oharretatik.',
 'patterns_title': '🔎 Patroien berrikuspena',
 'patterns_no_access': 'Orri hau gainbegiratzerako eta programaren kudeaketarako bakarrik da.',
 'patterns_intro': 'Orri honek profesionalen hausnarketetako behaketetan errepikatzen diren gaiak bilatzen laguntzen dio taldeari. Erakusten duena hausnarketarako patroi hautagaiak dira, ez ondorioak: behaketa antzeko multzo batek ez du alborapenik edo jardun txarrik frogatzen, eta sortak ez du nahitaez erakundea ordezkatzen. Taldeak erabakitzen du patroi batek zer esan nahi duen, esan nahi badu.',
 'patterns_pool_header': 'Zer dago berrikusteko',
 'patterns_pool_caption': 'Profesionalen hausnarketetako behaketa guztiak agertzen dira hemen. Ez duzu inoiz ikusten nork idatzi dituen, ezta haien ohar pribatuak ere.',
 'patterns_filter_lenses': 'Mugatu hausnarketa-puntu hauetara (hutsik = guztiak)',
 'patterns_filter_from': 'Noiztik (aukerakoa)',
 'patterns_filter_to': 'Noiz arte (aukerakoa)',
 'patterns_pool_empty': 'Oraindik ez dago behaketarik iragazki hauekin.',
 'patterns_pool_counts': '{observations} behaketa, {reflections} hausnarketatik eta {cases} kasu-erreferentzia desberdinetatik.',
 'patterns_pool_no_case': '{count} hausnarketak ez dute kasu-erreferentziarik, beraz ez dira '
                          'kasutzat kontatzen.',
 'patterns_generate_header': 'Bilatu patroiak',
 'patterns_settings_header': 'Bilaketaren ezarpenak',
 'patterns_settings_intro': 'Ezarpen hauek abiapuntuak dira, ez frogatutako balioak. Aldatu itzazu '
                            'eta alderatu emaitzak.',
 'patterns_similarity_label': 'Zenbat antzeko izan behar diren behaketak',
 'patterns_similarity_levels': {'broad': 'Zabala', 'balanced': 'Orekatua', 'strict': 'Zorrotza'},
 'patterns_similarity_help': 'Zabalak antz lausoagoko behaketak multzokatzen ditu (multzo gehiago, '
                             'zarata gehiago). Zorrotzak antz handiagoa eskatzen du (multzo '
                             'gutxiago, fidagarriagoak).',
 'patterns_min_observations_label': 'Gutxieneko behaketak multzoko',
 'patterns_min_reflections_label': 'Gutxieneko hausnarketa desberdinak multzoko',
 'patterns_threshold_not_proof': 'Gutxieneko hauek betetzeak ez du ezer frogatzen: multzo bat '
                                 'eztabaidatzeko erakustea merezi duen ala ez erabakitzen du '
                                 'soilik.',
 'patterns_cost_note': 'Patroiak bilatzeak IA erabiltzen du {max_patterns} azalpen arte idazteko '
                       '(zentimo gutxi guztira). Botoia berriro sakatzen baduzu bakarrik '
                       'ordaintzen da berriro.',
 'patterns_pool_truncated': 'Aldi berean alderatzen direnak baino behaketa gehiago daude; azkeneko {max} erabiltzen dira.',
 'patterns_not_enough': 'Gutxienez {minimum} behaketa behar dira patroiak bilatzeko.',
 'patterns_generate_button': 'Bilatu patroiak',
 'patterns_generating': 'Patroiak bilatzen…',
 'patterns_busy': 'Bilaketa bat martxan dago jada. Itxaron amaitu arte eta saiatu berriro.',
 'patterns_unavailable': 'Esanahiaren araberako alderaketa-zerbitzua ez dago konfiguratuta; beraz, '
                         'orain ezin dira patroiak bilatu.',
 'patterns_none_found': 'Ez da gutxienekoak betetzen dituen multzorik aurkitu {observations} behaketen artean. Probatu ezarpen zabalago bat, edo itxaron hausnarketa gehiago egon arte.',
 'patterns_generated_ok': '{patterns} patroi hautagai aurkitu dira {observations} behaketen '
                          'artean.',
 'patterns_not_embedded': '{count} behaketa ezin izan dira alderatu oraingoan, eta kanpoan geratu '
                          'dira.',
 'patterns_fallback_notice': '{count} patroiren azalpena ezin izan da idatzi; testu sinple bat '
                             'erakusten da eta berriro saia zaitezke.',
 'patterns_review_header': 'Berrikusi patroi hautagaiak',
 'patterns_no_runs': 'Oraindik ez da patroirik bilatu.',
 'patterns_run_select': 'Berrikusteko bilaketa',
 'patterns_run_option': '{date} — {observations} behaketa — {patterns} patroi',
 'patterns_run_caption': 'Bilaketa honen ezarpenak: antzekotasun {level}; gutxienez {min_obs} '
                         'behaketa gutxienez {min_refl} hausnarketa desberdinetatik.',
 'patterns_filter_status': 'Erakutsi egoerak',
 'patterns_statuses': {'candidate': 'Hautagaia',
                       'under_review': 'Berrikusten',
                       'worth_discussing': 'Komentatzea merezi du',
                       'not_supported': 'Berrikusi ondoren ez da babesten',
                       'archived': 'Artxibatua'},
 'patterns_none_in_view': 'Ez dago patroirik iragazki hauekin.',
 'patterns_cases_none': 'Hausnarketa hauetako batek ere ez du kasu-erreferentziarik; beraz, ezin '
                        'da kasuei buruz ezer esan.',
 'patterns_cases_incomplete': '{total} hausnarketatik {missing}ek ez dute kasu-erreferentziarik; '
                              'beraz, ezin da ezarri kasuen artean errepikatzen denik, hainbat '
                              'hausnarketatan agertzen dela baino ezin da esan.',
 'patterns_cases_single': 'Behaketa guztiak kasu-erreferentzia bati dagozkio: kasu baten barruko '
                          'errepikapena da, ez kasuen artekoa.',
 'patterns_cases_multiple': 'Behaketak {cases} kasu-erreferentzia desberdinetatik datoz.',
 'patterns_item_header': '{title} — {status} — {observations} behaketa / {reflections} hausnarketa',
 'patterns_candidate_label': 'Hausnarketarako patroi hautagaia — ez da ondorio bat.',
 'patterns_counts_line': '{observations} behaketa · {reflections} hausnarketa desberdin · {cases} '
                         'kasu desberdin',
 'patterns_case_ref_caveat': 'Kasu-erreferentziak eskuz idazten dira: akats batek kasu bera bi '
                             'gisa kontatzea eragin dezake.',
 'patterns_dates_line': 'Hausnarketak {first} eta {last} artean',
 'patterns_lenses_line': 'Hausnarketa-puntuak: {lenses}',
 'patterns_lost_members': 'Patroi honetako {count} behaketa ez daude eskuragarri jada (haien hausnarketa ezabatu da). Idatzitako azalpenak oraindik islatu ditzake: bilatu patroiak berriro horretan fidatu aurretik.',
 'patterns_below_minimum': 'Oraingo behaketekin, multzo honek ez ditu jada aurkitu zenekoko '
                           'gutxienekoak betetzen.',
 'patterns_explanation_failed': 'Patroi honen azalpen automatikoa ezin izan da idatzi. Testu '
                                'sinple bat erakusten da.',
 'patterns_explanation_retry': 'Saiatu azalpena berriro',
 'patterns_retry_ok': 'Azalpena idatzi da.',
 'patterns_retry_failed': 'Azalpena oraindik ezin da idatzi. Saiatu berriro geroago.',
 'patterns_what_in_common': 'Zer duten komunean',
 'patterns_why_it_matters': 'Zergatik izan dezakeen garrantzia',
 'patterns_alternatives': 'Beste azalpen posible batzuk',
 'patterns_limitations': 'Honetatik zer ezin den jakin',
 'patterns_questions': 'Komentatzeko galderak',
 'patterns_observations_header': 'Multzoko behaketak (aipu zehatzarekin)',
 'patterns_exclude_button': 'Behaketa hau ez da patroi honetakoa',
 'patterns_excluded_ok': 'Behaketa patroitik kendu da.',
 'patterns_more_observations': 'Eta {count} behaketa gehiago, hemen erakusten ez direnak.',
 'patterns_excluded_header': 'Taldeak patroi honetatik kendutako behaketak',
 'patterns_restore_button': 'Sartu berriro',
 'patterns_restored_ok': 'Behaketa berriro sartu da.',
 'patterns_review_status_header': 'Taldearen balorazioa',
 'patterns_review_help': 'Erregistratu hemen zuen irizpidea. IAk proposatutakoa ez da inoiz '
                         'ezabatzen edo aldatzen.',
 'patterns_status_label': 'Egoera',
 'patterns_comment_label': 'Iruzkina (aukerakoa)',
 'patterns_save_review': 'Gorde balorazioa',
 'patterns_review_saved': 'Balorazioa gorde da.',
 'patterns_review_nothing': 'Ez dago gordetzeko aldaketarik.',
 'patterns_history_header': 'Historia',
 'patterns_event_kinds': {'generated': 'Patroia sortu da',
                          'status_changed': 'Egoera aldatu da',
                          'carried_over': 'Balorazioa aurreko bilaketa batetik heredatu da',
                          'member_excluded': 'Behaketa patroitik kendu da',
                          'member_restored': 'Behaketa berriro sartu da',
                          'explanation_regenerated': 'Azalpena berriro idatzi da'},
 'patterns_event_status_change': '({old} → {new})',
 'patterns_event_system': 'Sistema',
 'doc_import_label': 'Edo igo dokumentu bat (Word, PDF edo testua)',
 'doc_import_help': 'Testua bakarrik irakurtzen da; fitxategia ez da gordetzen. {max_mb} MB, '
                    '{max_pages} orrialde eta {max_chars} karaktere inguru arte. Eskaneatutako '
                    'PDFak (paperaren argazkiak) ezin dira irakurri.',
 'doc_import_loaded': 'Testua kargatuta. Berrikusi eta zuzendu jarraitu aurretik. Fitxategia bera ez da gordetzen.',
 'doc_import_errors': {'unsupported': 'Fitxategi mota hau ez da onartzen. Erabili Word (.docx), '
                                      'PDF edo testua (.txt).',
                       'too_large': 'Fitxategia handiegia da (gehienez {max_mb} MB).',
                       'too_long': 'Dokumentua luzeegia da (gehienez {max_chars} karaktere '
                                   'inguru). Zatitu eta igo zati bakoitza bereizita.',
                       'too_many_pages': 'PDFak orrialde gehiegi ditu (gehienez {max_pages}).',
                       'encrypted': 'Fitxategia pasahitzez babestuta dago. Kendu babesa eta igo '
                                    'berriro.',
                       'no_text': 'Ez da testurik aurkitu fitxategian. Eskaneatutako PDF bat bada, '
                                  'kopiatu testua eskuz edo erabili testua duen bertsio bat.',
                       'unreadable': 'Ezin izan da fitxategia irakurri. Hondatuta egon daiteke; '
                                     'saiatu berriro gordetzen edo itsatsi testua.',
                       'unavailable': 'Fitxategi mota hau irakurtzea ez dago erabilgarri orain. '
                                      'Itsatsi testua zuzenean.'},
 'report_doc_title': 'Hausnarketarako patroi hautagaien txostena',
 'report_confidential': 'Kudeaketa-taldearentzako dokumentu konfidentziala',
 'report_prepared': '{date}(e)an prestatua',
 'report_how_to_read_title': 'Nola irakurri txosten hau',
 'report_how_to_read': 'Txosten honek patroi hautagaiak biltzen ditu: taldeak komentatu nahi ditzakeen behaketa antzeko multzoak. Ez dira ondorioak. Behaketa antzeko multzo batek ez du alborapenik edo jardun txarrik frogatzen, eta behaketak aplikazioan egindako hausnarketetatik datoz; beraz, ez dute nahitaez erakundea ordezkatzen. Taldeak erabakitzen du patroi bakoitzak zer esan nahi duen, esan nahi badu.',
 'report_search_title': 'Zein bilaketatik datorren',
 'report_search_line': '{date}(e)ko bilaketa: {observations} behaketa alderatu dira eta {patterns} patroi hautagai aurkitu dira.',
 'report_filters_line': 'Bilaketaren iragazkiak: {filters}',
 'report_no_filters': 'bat ere ez',
 'report_statuses_line': 'Txosten honetan sartutako egoerak: {statuses}',
 'report_summary_title': 'Laburpena',
 'report_col_pattern': 'Patroi hautagaia',
 'report_col_status': 'Egoera',
 'report_col_obs': 'Behaketak',
 'report_col_refl': 'Hausnarketa desberdinak',
 'report_col_cases': 'Kasu desberdinak',
 'report_pattern_heading': '{n}. patroia: {title}',
 'report_no_patterns': 'Ez dago hautatutako egoerak dituen patroirik.',
 'report_team_comments': 'Taldearen iruzkinak',
 'report_observations_omitted': 'Behaketak eta aipuak ez dira txosten honetan sartzen.',
 'report_quote_label': 'Aipu zehatza',
 'report_limits_title': 'Txosten honen mugak',
 'report_limits_list': ['Esanahiaren antzagatiko multzokatze automatikoa da; erlazionatu gabeko behaketak elkartu ditzake edo erlazionatuak bereizi.', 'Behaketak aplikazioan egindako IAren laguntzako hausnarketetatik datoz; ez dira erregistro osoa edo adierazgarria.', 'Kasu-erreferentziak eskuz idazten dira: akats batek kasu bera bi gisa kontatzea eragin dezake.', 'Azalpen-testua IAk idazten du behaketetatik abiatuta, eta bilaketaren ondoren kendutako behaketak islatu ditzake.', 'Txosten honetako ezerk ez du identifikatzen behaketa nork idatzi duen, ezta bere ohar pribatuak barne hartzen ere.'],
 'report_footer': 'Konfidentziala · Hausnarketarako patroi hautagaiak, ez ondorioak · {date}',
 'report_section_header': 'Inprimatzeko txostena',
 'report_section_intro': 'Goian erakusten diren patroiekin (hautatutako egoeren arabera) '
                         'inprimatzeko edo PDF gisa gordetzeko dokumentu bat sortzen du.',
 'report_opt_observations': 'Sartu behaketak eta haien aipu zehatzak',
 'report_opt_case_refs': 'Sartu kasu-erreferentziak (lehenespenez markatu gabe: paperak pantailak '
                         'baino gehiago zirkulatzen du)',
 'report_opt_comments': 'Sartu taldearen iruzkinak',
 'report_prepare_button': 'Prestatu txostena',
 'report_ready': 'Txostena prestatu da.',
 'report_download_button': 'Deskargatu txostena',
 'report_how_to_print': 'Ireki deskargatutako fitxategia nabigatzailean eta sakatu Ctrl+P (edo '
                        'Inprimatu) inprimatzeko edo PDF gisa gordetzeko.',
 'report_outdated': 'Bilaketa, egoerak edo aukerak aldatu dituzu: prestatu txostena berriro.',
 'rs_intro': 'Idatzi, itsatsi edo igo hausnartu nahi duzun kasua eta hausnartu une berean. AAri zure testuaren bertsio anonimizatu bat bakarrik bidaltzen zaio. Jatorrizko testua modu seguruan gordetzen da hausnarketarekin batera, geroago ereduak aztertzeko.',
 'rs_code_label': 'Hausnarketa honen kodea:',
 'rs_code_help': 'Aplikazioak sortutako kode neutroa. Ez du inor identifikatzen. Idatzi ezazu '
                 'geroago egoera berari buruzko beste hausnarketa bat lotu nahi baduzu.',
 'rs_note_type_label': 'Testu mota',
 'rs_tags_label': 'Kasuaren gaiak (datu pertsonalik gabe)',
 'rs_tags_placeholder': 'Aukeratu gai bat edo gehiago',
 'rs_tags_help': 'Markatu gehienez {max} gai, egoera deskribatzen dutenak, inoiz ez pertsona. '
                 'Geroago antzeko egoerei buruzko zure hausnarketak aurkitzeko balio dute.',
 'rs_tags_short_label': 'Gaiak',
 'rs_no_tags': 'Gairik gabe',
 'rs_previous_code_label': 'Aurreko hausnarketa baten jarraipena da? (aukerakoa)',
 'rs_previous_code_placeholder': 'RS-XXXXXX',
 'rs_previous_code_help': 'Egoera berari buruz lehenago hausnartu bazenuen, idatzi hemen '
                          'hausnarketa haren kodea kontuan hartzeko. Zure hausnarketak bakarrik '
                          'lotu ditzakezu.',
 'rs_previous_code_invalid': 'Kode horrek ez du formatu zuzena. RS-7F3K2Q bezalakoa izan behar du.',
 'rs_previous_code_not_found': 'Ez da {code} kodea duen zure hausnarketarik aurkitu. Egiaztatu '
                               'kodea edo utzi eremua hutsik.',
 'rs_previous_code_check_failed': 'Ezin izan da aurreko kodea orain egiaztatu. Saiatu berriro edo '
                                  'utzi eremua hutsik.',
 'rs_case_text_label': 'Kasuaren testua',
 'rs_case_text_placeholder': 'Idatzi edo itsatsi kasua hemen…',
 'rs_case_text_not_saved_note': '🔒 Testu hau ez da gordetzen. Hausnarketak irauten duen bitartean '
                                'bakarrik dago.',
 'rs_continue_button': 'Jarraitu',
 'rs_case_text_review_label': 'Kasuaren testua',
 'rs_similar_header': 'Zure aurreko hausnarketa lotuak',
 'rs_similar_intro': 'Honekin lotutako edo gai komunak dituzten zure hausnarketak. Kendu marka '
                     'kontuan hartu nahi ez dituzunei.',
 'rs_similar_none': 'Ez dago zure aurreko hausnarketarik lotuta edo gai komunekin. Hausnarketa '
                    'gaurko testuarekin bakarrik egingo da.',
 'rs_similar_failed': 'Ezin izan dira zure aurreko hausnarketak orain bilatu. Jarrai dezakezu: '
                      'hausnarketa gaurko testuarekin bakarrik egingo da.',
 'rs_similar_reason_linked': 'Egoera honen aurreko hausnarketa gisa lotuta',
 'rs_similar_reason_tags': 'Gai komunak',
 'rs_similar_include_label': 'Hausnarketa hau kontuan hartu',
 'rs_similar_observations_label': 'Ikusi bere behaketak',
 'rs_similar_used_label': 'Barne hartutako aurreko hausnarketak',
 'rs_back_to_case_button': 'Itzuli kasura',
 'rs_finish_header': 'Amaitu hausnarketa',
 'rs_finish_caption': 'Zure hausnarketa eta oharrak {code} kodearekin gordeta geratzen dira. Amaitzean, kasuaren testua pantaila honetatik kentzen da.',
 'rs_finish_caption_unsaved': 'Ezin izan da hausnarketa hau gorde. Amaitzean, kasuaren testua pantaila honetatik kentzen da.',
 'rs_finish_button': 'Amaitu hausnarketa',
 'rs_finished_success': '✔ Hausnarketa amaituta. Kasuaren testua pantaila honetatik kendu da.',
 'rs_start_over_button': 'Hasi berriro',
 'ch_reflections_header': 'Gordetako hausnarketak',
 'ch_reflections_intro': 'Hausnarketa bakoitza bere kode neutroarekin eta gaiekin agertzen da. AAren behaketak erakusten dira; inoiz ez profesionalen ohar pribatuak. Jatorrizko testuak ez dira hemen erakusten: Patroien berrikuspenean irakur daitezke, egileen izenik gabe.',
 'ch_tag_filter_label': 'Gaia',
 'ch_all_tags': 'Gai guztiak',
 'ch_showing_recent': '{total} hausnarketetatik azken {shown}ak erakusten dira. Aukeratu data edo '
                      'gai bat mugatzeko.',
 'ch_author_label': 'Egilea',
 'ch_linked_label': 'Hausnarketa honen jarraipena',
 'ch_no_observations': 'Hausnarketa honek ez du gordetako behaketarik.',
 'ch_delete_button': 'Ezabatu hausnarketa',
 'ch_delete_confirm': 'Ziur zaude hausnarketa hau ezabatu nahi duzula? Bere behaketak eta lotutako '
                      'oharrak ezabatuko dira. Ekintza hau ezin da desegin.',
 'ch_deleted_success': '✔ Hausnarketa ezabatuta.',
 'ch_delete_failed': '⚠ Ezin izan da hausnarketa ezabatu.',
 'case_tag_labels': {'housing': 'Etxebizitza / etxegabetasuna',
                     'employment_training': 'Enplegua eta prestakuntza',
                     'income_benefits': 'Diru-sarrerak eta prestazioak',
                     'mental_health': 'Osasun mentala',
                     'physical_health': 'Osasun fisikoa',
                     'addictions': 'Mendekotasunak',
                     'disability': 'Desgaitasuna',
                     'family_relationships': 'Familia-harremanak',
                     'children_youth': 'Haurtzaroa eta gazteria',
                     'older_people': 'Adinekoak',
                     'gender_violence': 'Genero-indarkeria',
                     'social_isolation': 'Bakardadea / isolamendu soziala',
                     'migration_integration': 'Migrazioa eta integrazioa',
                     'legal_administrative': 'Lege- eta administrazio-izapideak'},
 'rs_heading': 'Hausnar dezagun.',
 'rs_subheading': 'Hartu une bat zure lanbide-praktikako egoera bat aztertzeko.',
 'rs_material_label': 'Zure hausnarketarako materiala',
 'rs_material_placeholder': 'Idatzi edo itsatsi zure testua hemen. Kasu-egoera bat, behaketa bat, '
                            'lanbide-esperientzia bat edo aztertu nahi duzun zerbait parteka '
                            'dezakezu...',
 'rs_file_loaded': 'Dokumentua irakurrita: **{name}**. Aldatzeko, kendu ✕ botoiarekin edo igo '
                   'beste bat.',
 'rs_both_inputs_notice': 'Testu bat idatzi duzu eta dokumentu bat ere igo duzu. Zeri buruz '
                          'hausnartu nahi duzu?',
 'rs_source_label': 'Zeri buruz hausnartu',
 'rs_source_options': {'text': 'Nik idatzitako testua',
                       'file': 'Igotako dokumentua',
                       'both': 'Biak batera'},
 'rs_choose_source_warning': 'Aukeratu lehenik zein testuri buruz hausnartu nahi duzun.',
 'rs_need_material': 'Idatzi, itsatsi edo igo testu bat Hausnartu sakatu aurretik.',
 'rs_language_label': 'Hausnarketaren hizkuntza',
 'rs_language_names': {'Español': 'Español', 'Euskera': 'Euskara', 'English': 'English'},
 'rs_privacy_note': '🛡️ AAri ezer bidali aurretik, izenak, adin zehatzak eta beste datu '
                    'pertsonal batzuk automatikoki kentzen dira.',
 'privacy_message_blocked': 'Ezin izan dugu zure mezua babestu, beraz ez da ezer bidali AAra. '
                            'Saiatu berriro; arazoak jarraitzen badu, jakinarazi '
                            'laguntza-taldeari.',
 'rs_reflect_button': 'Hausnartu',
 'rs_anonymised_status': 'Zure testua anonimizatu da.',
 'rs_preparing_status': 'Zure hausnarketa prestatzen...',
 'rs_anonymise_failed': 'Ezin izan dugu zure testua babestu, beraz ez da ezer bidali AAra. Zure '
                        'testua hemen dago oraindik. Saiatu berriro; arazoak jarraitzen badu, '
                        'jakinarazi laguntza-taldeari.',
 'rs_anonymised_preview_label': 'Ikusi testu anonimizatua',
 'rs_anonymised_preview_help': 'Egiaztatu zure materialaren bertsio babestua. Hau da, hain zuzen '
                               'ere, AAk jaso duena.',
 'rs_try_again_button': 'Saiatu berriro testu berarekin',
 'rs_original_saved_note': '📁 Jatorrizko testua modu seguruan gordetzen da (EBko datu-basean) gehienez {months} hilabetez, praktikako ereduak antzemateko. Gainbegiraleek eta programa-arduradunek irakur dezakete helburu horretarako, zure izenik gabe. AAri bertsio anonimizatua bakarrik bidaltzen zaio.',
 'ch_show_anonymised_text': 'Ikusi gordetako testu anonimizatua',
 'ch_anonymised_text_caption': 'AAk jaso zuen bertsio babestua (inoiz ez jatorrizko testua). '
                               '{months} hilabete igarotakoan automatikoki ezabatzen da.',
 'ch_anonymised_text_unavailable': 'Hausnarketa honen testu anonimizatua ez dago erabilgarri jada.',
 'ch_show_saved_text': 'Ikusi gordetako testua',
 'ch_original_text_caption': 'Jatorrizko testua, zuk idatzi bezala. Ez zaio inoiz AAri bidaltzen eta {months} hilabete igarotakoan automatikoki ezabatzen da.',
 'ch_saved_text_unavailable': 'Hausnarketa honen testua ez dago erabilgarri (ez zen gorde edo dagoeneko ezabatu da).',
 'ch_original_text_in_patterns_note': '📄 Hausnarketa honen jatorrizko testua gordeta dago. Gainbegiraleek eta programa-arduradunek Patroien berrikuspenean irakur dezakete, egilearen izenik gabe.',
 'patterns_texts_header': '📄 Gordetako jatorrizko testuak',
 'patterns_texts_caption': 'Hausnarketak egiteko erabili ziren jatorrizko testuak, kasuak nola idazten diren aztertzeko. Ez dira inoiz erakusten egileen izenak, hausnarketa-kodeak edo ordu zehatzak. Testu bakoitza {months} hilabete igarotakoan automatikoki ezabatzen da. Testu hauek konfidentzialak dira: ez itzazu aplikaziotik kanpora kopiatu.',
 'patterns_texts_empty': 'Oraindik ez da jatorrizko testurik gorde.',
 'patterns_texts_showing': 'Gordetako {total} testuetatik azken {shown}ak erakusten dira.',
 'patterns_texts_item': '{date}(e)ko testua · {language}',
 'rs_cards_hint': 'Aukeratu edozein txartel irekitzeko.',
 'rs_cards_choose': 'Aukeratu txartel bat bere hausnarketa ikusteko.',
 'rs_card_explored': '✓ Arakatua',
 'rs_card_status': {'finding': 'Badago zer hausnartu',
                    'none': 'Ez da ezer nabarmenik aurkitu',
                    'unavailable': 'Orain ez dago erabilgarri, berriro saia zaitezke'},
 'my_reflections_header': 'Zure gordetako hausnarketak',
 'my_reflections_intro': 'Zure hausnarketetako edozein ezaba dezakezu. Leku guztietatik '
                         'desagertzen da (arduradunentzat eta ereduen analisitik ere), bere '
                         'behaketekin, zure oharrekin eta bere testu anonimizatuarekin. {hours} '
                         'orduz berreskura dezakezu; ondoren behin betiko ezabatzen da.',
 'my_reflections_empty': 'Oraindik ez duzu gordetako hausnarketarik.',
 'my_reflections_showing': '{total}etik azken {shown}ak erakusten dira.',
 'my_reflections_line': '{date} · {count} behaketa',
 'my_reflections_delete': 'Ezabatu',
 'my_reflections_confirm': '{code} hausnarketa ezabatu? Leku guztietatik desagertuko da. {hours} '
                           'orduz berreskuratu ahal izango duzu.',
 'my_reflections_confirm_yes': 'Bai, ezabatu',
 'my_reflections_confirm_cancel': 'Utzi',
 'my_reflections_deleted': '{code} hausnarketa ezabatu da. {hours} orduz berreskura dezakezu.',
 'my_reflections_restored': '{code} hausnarketa berreskuratu da.',
 'my_reflections_failed': 'Ezin izan da osatu. Saiatu berriro.',
 'my_reflections_deleted_header': 'Duela gutxi ezabatuak',
 'my_reflections_restore': 'Berreskuratu',
 'my_reflections_erase_on': 'Behin betiko ezabatuko da: {date} (UTC).'}
