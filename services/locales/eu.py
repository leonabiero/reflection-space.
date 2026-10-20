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
 'doc_types': ['Kasu-oharra',
               'Jarraipen egunkaria',
               'Elkarrizketaren erregistroa',
               'Gizarte-txostena',
               'Deribazio proposamena',
               'Esku-hartze plana',
               'Posta elektronikoa'],
 'language': 'Hizkuntza',
 'text': 'Testua',
 'save': 'Gorde zirriborroa',
 'success': '✔ Zirriborroa ondo gorde da',
 'empty': 'Mesedez idatzi testua',
 'new': 'Dokumentu berria',
 'reflection': 'Hausnarketa gunea',
 'home_subtitle': 'Praktikan dokumentatzeko eta hausnartzeko gune bat.',
 'nav_hint': 'Erabili alboko barra nabigatzeko.',
 'nav_header': 'Nabigatu:',
 'nav_doc': '📝 Dokumentazioa',
 'nav_reflection': '🌿 Hausnarketa gunea',
 'nav_learning': '📚 Ikaskuntza',
 'no_drafts': 'Ez dago zirriborrorik eskuragarri.',
 'select_drafts': 'Hautatu hausnartzeko zirriborroak',
 'begin_reflection': 'Hasi hausnarketa',
 'reflection_folders_intro': 'Hausnartzeko dauden dokumentuak, kasuka multzokatuta.',
 'reflection_same_day_notice': '⚠️ Kasu honek egun bereko dokumentu bat baino gehiago ditu.',
 'reflection_no_case_ref': '(Kasu-erreferentziarik gabe)',
 'reflection_active_case_prefix': 'Hausnartzen ari zaren kasua:',
 'reflection_delete_button': 'Dokumentua ezabatu',
 'reflection_delete_confirm': 'Ziur zaude dokumentu hau ezabatu nahi duzula? Ekintza hau ezin da '
                              'desegin.',
 'reflection_deleted_success': '✔ Dokumentua ezabatu da.',
 'reflection_context_title': 'Hausnarketaren testuingurua',
 'reflection_context_current_label': 'Hautatutako dokumentua(k):',
 'reflection_context_historical_label': 'Kasu honetako dokumentu historiko garrantzitsuak:',
 'reflection_context_summary_strong': 'Hausnarketa honek gaurko dokumentazioa eta garrantzitsuak '
                                      'diren {count} dokumentu historiko erabiltzen ditu.',
 'reflection_context_summary_limited': 'Hausnarketa honek batez ere gaurko dokumentazioa '
                                       'erabiltzen du, informazio historiko garrantzitsu gutxi '
                                       'aurkitu baita.',
 'reflection_context_summary_none': 'Kasu honetarako dokumentatutako lehen interakzioa dirudi.',
 'reflection_context_continue': 'Hausnarketara jarraitu',
 'reflection_context_back': 'Hautaketara itzuli',
 'reflection_partial_failure_notice': 'Hausnarketa-ikuspegi batzuk ({count}) ezin izan dira sortu. '
                                      'Hausnarketa hala ere sortu da. Hau berrikusteko '
                                      'erregistratu da. Eskuragarri dagoenarekin jarraitu dezakezu '
                                      'edo berriro saiatu.',
 'unknown_label': 'Ezezaguna',
 'audit_unknown_case_label': '(kasu ezezaguna)',
 'case_history_completed_label': 'amaituta',
 'learning_phase2': 'Aplikazioan sortutako hausnarketetan agertzen diren gaiak.',
 'learning_no_data': 'Oraindik ez dago hausnarketarik erregistratuta. Gaiak hemen agertuko dira '
                     'hausnarketak sortu ahala.',
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
 'nav_case_history': '🗂️ Kasuen historia',
 'case_history_title': 'Kasuen historia',
 'case_history_no_items': 'Oraindik ez dago osatutako hausnarketarik.',
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
 'learning_preview_caption': 'Azken {total} hausnarketetan oinarrituta',
 'learning_flagged_caption': 'Azken {total} hausnarketetatik {count}-tan identifikatua',
 'case_history_date_filter_label': 'Historia ikusi:',
 'case_history_toggle_label': 'Erakutsi:',
 'case_history_edited_option': 'Editatuak',
 'case_history_not_edited_option': 'Editatu gabeak',
 'case_history_no_items_for_filter': 'Ez dago dokumenturik hautapen honetarako.',
 'case_history_showing_recent': '{total} dokumentuetatik azken {shown} erakusten ari da. Erabili '
                                'data-iragazkia dokumentu zaharragoak ikusteko.',
 'feedback_showing_recent': '{total} iruzkinetatik azken {shown} erakusten ari da.',
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
 'workspace_document_header': 'Uneko dokumentua',
 'workspace_context_header': 'Hausnarketaren testuingurua',
 'workspace_progress_label': 'Aztertuta: {explored} / {total}',
 'workspace_explore_button': 'Aztertu',
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
 'growth_intro': 'Hau zure gune pertsonala da. Zuk zeuk aztertutakoa bakarrik erakusten du — ez da '
                 'zure jardunaren ebaluazioa, ez da beste profesional batzuekin konparatzen eta ez '
                 'da gainbegiraleentzat ikusgai.',
 'growth_no_data': 'Oraindik ez duzu hausnarketarik aztertu. Hausnarketa Gunean «Aztertu» botoia '
                   'erabili ahala, zure bidea hemen agertuko da.',
 'growth_themes_header': 'Gehien aztertu dituzun arloak',
 'growth_themes_caption': 'Erregistratutako {total} azterketa-unetan oinarrituta',
 'growth_history_header': 'Duela gutxiko hausnarketa-uneak',
 'growth_entry_line': '**{theme}** — {case} kasua — {count} truke — {date}',
 'growth_session_count_label': 'Guztira erregistratutako azterketa-uneak',
 'nav_team_learning': '🌍 Taldearen Ikaskuntza',
 'team_learning_title': '🌍 Taldearen Hausnarketa Gaiak',
 'team_learning_intro': 'Ikuspegi honek erakusten ditu erakunde osoko eredu agregatu eta '
                        'anonimoak. Ez du profesionalik identifikatzen, ez du kasu zehatzik '
                        'identifikatzen eta ez du inoren hausnarketa-historiala erakusten. Bere '
                        'helburua da erakundeari laguntzea zein arlok merezi duten arreta '
                        'kolektiboa identifikatzen — ez pertsonak ebaluatzea.',
 'team_learning_period_caption': 'Azken 6 hilabeteak — {total} azterketa-une erregistratuta '
                                 'guztira, talde guztietan',
 'team_learning_no_data': 'Oraindik ez dago nahikoa azterketa-daturik azken 6 hilabeteetan '
                          'erregistratuta.',
 'team_learning_header': 'Hausnarketa-arlo ohikoenak',
 'team_learning_rank_line': '{rank}. {theme} — {count} azterketa',
 'nav_research_metrics': '📊 Ikerketa Metrikak',
 'research_title': '📊 Ikerketa Metrikak',
 'research_intro': 'Metrika hauek erakundearen hausnarketa-jarduera deskribatzen dute — ez dute '
                   'inolako profesionalik ebaluatzen edo konparatzen. Ez dute izenik, kasu '
                   'zehatzik edo dokumentu-edukirik.',
 'research_period_caption': 'Epea: azken {days} egun (hemendik: {since})',
 'research_overview_header': 'Jardueraren laburpena',
 'research_sessions_label': 'Sortutako hausnarketa-saioak',
 'research_documents_label': 'Osatutako dokumentuak',
 'research_theme_table_header': 'Gaiak: IAk seinalatuak vs. profesionalek aztertuak',
 'research_theme_flagged_col': 'IAk seinalatua',
 'research_theme_explored_col': 'Profesional batek aztertua',
 'research_feedback_header': 'Erabilgarritasun-balorazioak',
 'research_feedback_count_label': 'Jasotako balorazioak',
 'research_feedback_average_label': 'Batez besteko balorazioa',
 'research_feedback_comments_label': 'Iruzkinarekin',
 'research_feedback_no_data': 'Oraindik ez da balorazio bakar bat ere jaso.',
 'research_export_button': 'Ikerketarako CSVa deskargatu',
 'research_export_caption': 'Fitxategiak zenbaketa agregatuak bakarrik ditu — izenik, kasurik edo '
                            'dokumentu-testurik gabe.',
 'research_no_data': 'Oraindik ez dago nahikoa jarduera erregistratuta epe honetarako.',
 'why_included_label': 'Zergatik sartu da dokumentu hau?',
 'why_reason_must_include_plan': 'Hau da azken Esku-hartze Plana, eta gaurko hausnarketarako '
                                 'testuinguru garrantzitsua ematen du.',
 'why_reason_must_include_assessment': 'Hau da kasu honetarako eskuragarri dagoen azken '
                                       'gizarte-txostena.',
 'why_reason_must_include_generic': 'Hau kasu honetako funtsezko dokumentuetako bat da.',
 'why_reason_semantic_specific': 'Dokumentu honek {themes} jorratzen ditu, gaurko dokumentazioan '
                                 'ere aipatzen direnak.',
 'why_reason_semantic_generic': 'Dokumentu honek gaurko dokumentazioarekin lotura estua duten '
                                'gaiak jorratzen ditu.',
 'why_reason_recency': 'Dokumentu hau duela gutxi sortu zen eta gaurko hausnarketarako '
                       'garrantzitsuak izan daitezkeen garapenak izan ditzake.',
 'why_technical_details_label': 'Xehetasun teknikoak',
 'why_similarity_label': 'Antzekotasuna:',
 'why_similarity_very_high': 'Oso altua',
 'why_similarity_high': 'Altua',
 'why_similarity_moderate': 'Ertaina',
 'why_similarity_low': 'Baxua',
 'journey_step1': 'Gaurko Dokumentazioa',
 'journey_step2': 'Testuinguru Historikoa',
 'journey_step3': 'Hausnarketa Profesionala',
 'journey_step4': 'Hausnarketa Galderak',
 'journey_step1_desc': 'Gaurko dokumentuak hautatzen dira hausnartzeko.',
 'journey_step2_desc': 'Kasu honetako dokumentu historiko garrantzitsuak berreskuratzen dira.',
 'journey_step3_desc': 'IAk gaurko dokumentazioa testuinguru historikoarekin batera aztertzen du.',
 'journey_step4_desc': 'Hausnarketa galderak kontsideratzeko gonbidatzen zaitu.',
 'historical_timeline_header': 'Denbora-lerro historikoa',
 'historical_timeline_intro': 'Kasu honetako dokumentu garrantzitsuak, kronologikoki ordenatuta.',
 'timeline_today_label': '📍 Gaurko dokumentazioa',
 'historical_docs_used_label': 'Une honetan sartutako dokumentu historikoak',
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
 'presence_header': 'Taldearen Presentzia',
 'presence_intro': 'Une honetan aplikazioan aktibo dauden gizarte-langileak. Ez da '
                   'kasu-informaziorik edo dokumentu-edukirik erakusten.',
 'presence_active_count': '{count} gizarte-langile aktibo edo duela gutxi aktibo',
 'presence_status_active': '🟢 Aktibo orain',
 'presence_status_recent': '🟡 Aktibo duela {minutes} minutu',
 'presence_status_offline': '⚪ Ez du azken jarduerarik izan',
 'presence_no_data': 'Oraindik ez dago jarduera-daturik erregistratuta.',
 'learning_tab_presence': '👥 Taldearen Presentzia',
 'learning_tab_knowledge': '💬 Erakundearen Ikaskuntza',
 'learning_tab_insights': '📚 Ikaskuntza Ikuspegiak',
 'learning_tab_team': '🌍 Taldearen Ikaskuntza',
 'ka_header': 'Galdetu erakundearen ezagutzari buruz',
 'ka_intro': 'Egin galdera bat hizkuntza naturalean erakundearen eredu, gai eta jarduera '
             'erreflexiboari buruz. Erantzunak indexatutako dokumentazio eta hausnarketetan '
             'oinarritzen dira soilik — inoiz ez kanpoko ezagutza orokorrean.',
 'ka_question_label': 'Zure galdera',
 'ka_question_placeholder': 'Adibidez: Zein eredu sortu dira Kulunkan hiruhileko honetan?',
 'ka_ask_button': 'Galdetu',
 'ka_thinking': 'Erakundearen ezagutza-basea aztertzen...',
 'ka_error': '⚠ Ezin izan da erantzunik sortu. Saiatu berriro.',
 'ka_empty_question': 'Mesedez idatzi galdera bat.',
 'ka_duplicate_message': 'Galdera hau jadanik prozesatzen ari da. Itxaron pixka bat amaitu arte, '
                         'berriro galdetu aurretik.',
 'ka_rate_limit_exceeded_message': 'Kontu honetan azken orduan Ezagutza Laguntzaileari egindako '
                                   '{max} galderaren muga bete duzu. Hau segurtasun-muga bat da '
                                   'nahi gabeko eskaera errepikatuak saihesteko, ez zure ohiko '
                                   'lanaren murrizketa bat -- itxaron pixka bat eta saiatu '
                                   'berriro, edo jarri harremanetan Sistemaren '
                                   'Administratzailearekin hau errore bat dela uste baduzu.',
 'ka_confidence_label': 'Ebidentzia maila:',
 'ka_confidence_strong': '🟢 Ebidentzia sendoa',
 'ka_confidence_limited': '🟡 Ebidentzia mugatua',
 'ka_confidence_insufficient': '🔴 Ebidentzia nahikoa ez',
 'ka_limitations_label': 'Mugak:',
 'ka_evidence_header': 'Erabilitako ebidentzia',
 'ka_evidence_count': '{count} dokumentu garrantzitsu berreskuratuta',
 'ka_evidence_doc_type_col': 'Dokumentu mota',
 'ka_evidence_date_col': 'Data',
 'ka_evidence_case_col': 'Kasu/zerbitzu erreferentzia',
 'ka_evidence_relevance_col': 'Garrantzia',
 'ka_evidence_none': 'Ez da galdera honentzako dokumentu garrantzitsurik berreskuratu.',
 'admin_user_mgmt_header': '👥 Erabiltzaileen kudeaketa',
 'admin_user_mgmt_info': 'Erabiltzaileak Streamlit Sekretuen bidez kudeatzen dira. CRUD dinamikoa '
                         'ez dago nahita eskuragarri: kredentzialak eta rolak '
                         'zabalkunde-sekretuetan konfiguratzen dira, ez aplikazioaren tauletan.',
 'admin_user_mgmt_empty': 'Oraindik ez dago erabiltzailerik konfiguratuta. Gehitu Ezarpenak → '
                          'Sekretuak atalean Streamlit Cloud-en.',
 'admin_user_col_username': 'Erabiltzaile-izena',
 'admin_user_col_name': 'Izena',
 'admin_user_col_role': 'Rola',
 'admin_doc_indexing_header': '📇 Dokumentuen indexazioa',
 'admin_doc_indexing_caption': 'Hybrid RAG birindexatze-tresna — berreskuratze semantikoa aktibatu '
                               'aurretik osatutako dokumentuentzako Qdrant embeddingak sortzen '
                               'ditu.',
 'admin_doc_indexing_cost': '💰 Kostu-oharra: honek Gemini API (embeddings) deitzen du osatutako '
                            'dokumentu bakoitzeko behin, inoiz ez Claude.',
 'admin_doc_indexing_unavailable': 'Qdrant ez dago konfiguratuta, beraz indexazio semantikoa ez '
                                   'dago eskuragarri.',
 'admin_doc_indexing_button': 'Exekutatu dokumentuen birindexatzea',
 'admin_doc_indexing_success': '✅ {indexed}/{total} dokumentu indexatuta.',
 'admin_doc_indexing_none_failed': '✅ Ez dago indexatzeke dagoen dokumenturik. Dena eguneratuta '
                                   'dago.',
 'admin_doc_indexing_failed_label': '⚠️ {failed} dokumentu ondo gorde dira, baina ez dira '
                                    'bilaketarako indexatu.',
 'admin_doc_indexing_failed_caption': 'Dokumentu horiek osatuta daude eta aplikazio osoan normal '
                                      'ikusten dira — huts egin duen urrats bakarra Ezagutza '
                                      'Laguntzailean eta Hausnarketa Testuinguruaren '
                                      'kasu-historikoan bilagarri egiten dituena da. Ez da daturik '
                                      'galdu; indexazioa berriro saiatzea nahikoa da.',
 'admin_doc_indexing_retry_button': 'Saiatu berriro huts egindako dokumentuekin bakarrik',
 'admin_doc_indexing_retry_success': '✅ Berriz saiatzea amaituta: {indexed}/{total} dokumentu ondo '
                                     'indexatu dira.',
 'admin_retrieval_test_header': '🔍 Berreskuratze-proba',
 'admin_retrieval_test_caption': 'Qdrant-en aurkako benetako bilaketa semantikoa exekutatzen du '
                                 'berreskuratzea muturretik muturrera funtzionatzen duela '
                                 'egiaztatzeko — kasu batera mugatuta edo ezagutza-base osoan.',
 'admin_retrieval_test_cost': '💰 Kostu-oharra: honek zure bilaketa-testuaren embedding-a sortzen '
                              'du Gemini API bidez soilik — inoiz ez du Claude/Anthropic APIa '
                              'deitzen.',
 'admin_retrieval_case_label': 'Kasuaren erreferentzia (aukerakoa — utzi hutsik ezagutza-base '
                               'osoan bilatzeko)',
 'admin_retrieval_query_label': 'Bilaketa-kontsulta',
 'admin_retrieval_run_button': 'Exekutatu berreskuratze-proba',
 'admin_retrieval_summary_header': '#### Berreskuratzearen laburpena',
 'admin_retrieval_mode_global': '🌍 Ezagutza-basean bilaketa globala',
 'admin_retrieval_mode_case': '📁 Kasuaren araberakoa ({case_ref})',
 'admin_retrieval_status_label': 'Egoera',
 'admin_retrieval_status_success': '✅ Arrakastatsua',
 'admin_retrieval_status_failed': '❌ Huts egin du',
 'admin_retrieval_mode_row_label': 'Berreskuratze modua',
 'admin_retrieval_time_label': 'Bilaketa-denbora',
 'admin_retrieval_query_row_label': 'Kontsulta',
 'admin_retrieval_docs_returned_label': 'Itzulitako dokumentuak',
 'admin_retrieval_embedding_model_label': 'Embedding eredua',
 'admin_retrieval_global_notice': '🌍 Modu globala: bilaketa honek ez du kasu-iragazkirik aplikatu '
                                  'eta kasu bat baino gehiagotako dokumentuak itzul ditzake.',
 'admin_retrieval_failed_label': 'Berreskuratzeak huts egin du:',
 'admin_retrieval_documents_header': '#### Berreskuratutako dokumentuak',
 'admin_retrieval_no_docs': 'Ez da dokumenturik itzuli kontsulta honetarako.',
 'admin_retrieval_col_rank': 'Postua',
 'admin_retrieval_col_doctype': 'Dokumentu mota',
 'admin_retrieval_col_reason': 'Berreskuratze arrazoia',
 'admin_retrieval_col_similarity': 'Antzekotasuna',
 'admin_retrieval_col_case': 'Kasuaren erreferentzia',
 'admin_advanced_diagnostics': '🔧 Diagnostiko aurreratua',
 'admin_show_raw_response': 'Erakutsi erantzun gordina',
 'admin_rag_status_header': '📡 RAG egoera',
 'admin_rag_status_ok': '✅ Berreskuratze-geruza semantikoa eskuragarri dago.',
 'admin_rag_status_item': 'Elementua',
 'admin_rag_status_value': 'Egoera',
 'admin_rag_qdrant_connection': 'Qdrant konexioa',
 'admin_rag_collection': 'Bilduma',
 'admin_rag_embedding_model': 'Embedding eredua',
 'admin_rag_embedding_dims': 'Embedding dimentsioak',
 'admin_rag_indexed_docs': 'Indexatutako dokumentuak',
 'admin_rag_case_ref_index': 'Kasu-erreferentzia indizea',
 'admin_rag_doc_id_index': 'Dokumentu ID indizea',
 'admin_rag_latest_doc_id': 'Azken dokumentu ID',
 'admin_rag_latest_case': 'Azken kasua',
 'admin_rag_latest_doctype': 'Azken dokumentu mota',
 'admin_rag_last_indexed': 'Azken indexazioa',
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
 'admin_health_component_qdrant': 'Qdrant',
 'admin_health_component_embedding': 'Embedding zerbitzua (Gemini API)',
 'admin_health_component_retrieval': 'Berreskuratze zerbitzua',
 'admin_health_component_reflection': 'Hausnarketa motorra (Claude API)',
 'admin_health_healthy_label': 'Osasuntsua',
 'admin_health_unreachable_label': 'Ezin da atzitu',
 'admin_health_available_label': 'Eskuragarri',
 'admin_health_not_configured_label': 'Konfiguratu gabe',
 'admin_health_operational_label': '✅ Funtzionamenduan',
 'admin_health_fallback_label': '🟡 Ordezko modua (data araberakoa)',
 'admin_health_db_error_prefix': 'Datu-base errorea:',
 'admin_health_key_missing': 'ANTHROPIC_API_KEY ez dago konfiguratuta — ezin dira hausnarketak '
                             'sortu.',
 'admin_config_header': '⚙️ Konfigurazioa',
 'admin_tools_header': '🧰 Administrazio-tresnak',
 'admin_tools_anon_test_header': 'Anonimizazio proba',
 'admin_tools_reset_index_header': 'Bilaketa-indizea berrezarri (Qdrant)',
 'admin_tools_reset_index_caption': 'Bilaketa semantikoaren indizea ezabatu eta hutsik berriz '
                                    'sortzen du, une honetan konfiguratutako embedding '
                                    'hornitzailea erabiliz. Erabili hau embedding hornitzailea '
                                    'aldatu ondoren (adibidez, Voyage-tik Gemini-ra), datu zahar '
                                    'eta bateraezinek bilaketa berriak oztopatu ez ditzaten.',
 'admin_tools_reset_index_warning': '⚠️ Ekintza honek Qdrant-en dauden bilaketa-bektore guztiak '
                                    'betiko ezabatuko ditu. Dokumentuak beraiek EZ dira galduko -- '
                                    'datu-basean osorik jarraituko dute -- baina ez dira agertuko '
                                    'Ezagutza Laguntzailearen bilaketetan edo Hausnarketa '
                                    'Testuinguruan berriro indexatu arte. Ziur zaude jarraitu nahi '
                                    'duzula?',
 'admin_tools_reset_index_button': 'Bilaketa-indizea berrezarri',
 'admin_tools_reset_index_yes': 'Bai, berrezarri',
 'admin_tools_reset_index_cancel': 'Utzi',
 'admin_tools_reset_index_success': 'Bilaketa-indizea ondo berrezarri da. Orain hutsik dago eta '
                                    'prest dago dokumentu berriak uneko embedding '
                                    'hornitzailearekin indexatzeko.',
 'admin_tools_reset_index_failed': 'Ezin izan da bilaketa-indizea berrezarri:',
 'admin_tools_reset_index_unavailable': 'Qdrant ez dago konfiguratuta -- ez dago berrezarri '
                                        'beharreko indizerik.',
 'admin_tools_future': 'Etorkizuneko administrazio-tresnak hemen agertuko dira.',
 'admin_console_caption': 'Reflection Space-ren administrazio-kontsola -- sistemaren egoera, '
                          'indexazioa eta diagnostiko-tresnak.',
 'admin_error_log_unknown_page': 'orrialde ezezaguna',
 'admin_error_log_generic_error': 'Errorea',
 'admin_error_log_no_message': '(mezurik ez)',
 'admin_error_log_unknown_role': 'rol ezezaguna',
 'readiness_category_exception': 'Salbuespena',
 'readiness_category_traceback_evidence': 'Traceback-a',
 'readiness_category_root_cause': 'Jatorrizko kausa',
 'readiness_category_timeline': 'Denbora-lerroa',
 'readiness_category_session_context': 'Saioaren testuingurua',
 'readiness_category_environment': 'Ingurunea',
 'readiness_category_user_information': 'Erabiltzailearen informazioa',
 'readiness_category_configuration': 'Konfigurazioa',
 'readiness_category_ai_prompt': 'AI prompt-a sortuta',
 'event_labels': {'Opened page': 'Orria irekita',
                  'Changed page': 'Orria aldatuta',
                  'Email sent': 'Posta elektronikoa bidalita',
                  'User submitted report': 'Erabiltzaileak bidalitako txostena',
                  'Exception occurred': 'Salbuespen bat gertatu da',
                  'Error logged': 'Errorea erregistratuta'},
 'admin_case_export_download': '#{n} kasua deskargatu',
 'admin_case_export_failed': 'Ezin izan da esportazioa sortu.',
 'admin_case_export_format': 'Formatua',
 'admin_case_export_header': '📤 Kasu hau esportatu',
 'admin_case_field_common_cause': 'Kausa arrunta',
 'admin_case_field_deployment_date': 'Zabalkunde-data (aplikagarria bada)',
 'admin_case_field_documentation_link': 'Dokumentaziorako esteka',
 'admin_case_field_external_reference': 'Kanpo-erreferentzia',
 'admin_case_field_fix_applied': 'Aplikatutako konponketa',
 'admin_case_field_git_commit': 'Git commit-a',
 'admin_case_field_known_fix': 'Konponbide ezaguna',
 'admin_case_field_known_workaround': 'Aldi baterako irtenbide ezaguna',
 'admin_case_field_lessons_learned': 'Ikasitako lezioak',
 'admin_case_field_prevention_notes': 'Etorkizuneko prebentzio-oharrak',
 'admin_case_field_resolution_summary': 'Ebazpenaren laburpena',
 'admin_case_field_root_cause': 'Erro-kausa (administratzailearen ondorioa)',
 'admin_case_field_version_fixed': 'Konpondutako bertsioa',
 'admin_case_investigation_add': 'Gorde ikerketa berri bat',
 'admin_case_investigation_by': 'Nork gehitua',
 'admin_case_investigation_delete': '🗑️ Sarrera hau kendu',
 'admin_case_investigation_notes': 'Administratzailearen oharrak',
 'admin_case_investigation_notes_input': 'Administratzailearen oharrak',
 'admin_case_investigation_prompt': 'Prompt-a',
 'admin_case_investigation_prompt_input': 'Prompt-a',
 'admin_case_investigation_response': 'IAren erantzuna',
 'admin_case_investigation_response_input': 'IAren erantzuna',
 'admin_case_investigation_save': '💾 Ikerketa gorde',
 'admin_case_investigation_save_failed': 'Ezin izan da gorde -- saiatu berriro.',
 'admin_case_investigation_saved': 'Ikerketa gordeta.',
 'admin_case_investigation_tool': 'Erabilitako tresna',
 'admin_case_investigations_caption': 'Hausnarketa Gunek ez du inoiz IA bat automatikoki deitzen '
                                      'hemen -- hau, besterik gabe, beste nonbait (ChatGPT, '
                                      'Claude, Gemini, edo eskuzko ikerketa bat) egindako '
                                      'ikerketak gordetzeko lekua da, hurrengo pertsonak lana '
                                      'errepikatu behar ez izateko.',
 'admin_case_investigations_empty': 'Oraindik ez dago gordetako ikerketarik.',
 'admin_case_investigations_header': '🧠 IA Ikerketaren Historia',
 'admin_case_knowledge_no_issue_id': 'Erregistro hau erreferentzia egonkorrak baino lehenagokoa '
                                     'da, beraz kasuaren ezagutza (ebazpen-jarraipena, IA '
                                     'ikerketaren historia, antzeko arazoak, esportazioa) ez dago '
                                     'eskuragarri honentzat.',
 'admin_case_knowledge_subheader': 'Kasuaren ezagutza (guztia aukerakoa)',
 'admin_case_resolution_header': '✅ Ebazpena eta Kasuaren Ezagutza',
 'admin_case_resolution_history_caption': 'Arazo hau lehen Konponduta edo Itxita gisa markatu zen '
                                          'eta ordutik berriro agertu da. Errepikapen bakoitzaren '
                                          'aurretik erregistratutako ebazpena behean gordeta dago, '
                                          'goiko formularioak uneko ikerketa erakusten badu ere.',
 'admin_case_resolution_history_header': '📜 Aurreko ebazpenen historia ({n} gordeta)',
 'admin_case_resolution_history_occurrence': 'gertaera',
 'admin_case_resolution_history_reopened_at': 'Berrirekita:',
 'admin_case_resolution_last_updated': 'Azken eguneraketa: {when}, {who}',
 'admin_case_resolution_save': '💾 Ebazpena eta kasuaren ezagutza gorde',
 'admin_case_resolution_save_failed': 'Ezin izan da gorde -- saiatu berriro.',
 'admin_case_resolution_saved': 'Gordeta.',
 'admin_case_search_ai_tool': 'Erabilitako IA tresna',
 'admin_case_search_button': 'Bilatu',
 'admin_case_search_caption': 'Bilatu ebatzitako eta ebatzi gabeko kasuak haiei buruz dakizunaren '
                              'arabera, ez soilik noiz gertatu ziren. Bete edozein eremu '
                              'konbinazio -- emaitzek emandako eremu GUZTIAK betetzen dituzte.',
 'admin_case_search_exception': 'Salbuespen mota',
 'admin_case_search_find_hint': 'Ireki goiko kasu bat datorren IA Diagnostiko Gunean (bere # '
                                'erreferentziaren bidez) erregistro osoa ikusteko.',
 'admin_case_search_header': '🔎 Kasuen Ezagutza Bilaketa',
 'admin_case_search_lesson': 'Ikasitako lezioak hau dauka',
 'admin_case_search_min_occurrences': 'Gertaera kopuru minimoa',
 'admin_case_search_no_results': 'Ez dago iragazki horiekin bat datorren kasurik. Saiatu eremu '
                                 'gutxiagorekin.',
 'admin_case_search_page': 'Orria',
 'admin_case_search_resolution': 'Ebazpenak hau dauka',
 'admin_case_search_resolution_label': 'Ebazpena',
 'admin_case_search_result_count': '{n} kasu aurkituta.',
 'admin_case_search_root_cause': 'Erro-kausak hau dauka',
 'admin_case_search_root_cause_label': 'Erro-kausa',
 'admin_case_search_status': 'Egoera',
 'admin_case_search_user': 'Erabiltzailea',
 'admin_case_search_version_fixed': 'Konpondutako bertsioa',
 'admin_case_similar_empty': 'Ez da antzeko arazo aurrekorik aurkitu.',
 'admin_case_similar_header': 'Antzeko Arazo Aurrekoak',
 'admin_error_log_caption': 'Aplikazioan erregistratutako arazo guztiak -- hutsegiteak, IA '
                            'laguntzailearen dei hutsak, edo pertsonek jakinarazitako arazoak -- '
                            'diagnostiko-espazio oso gisa erakutsita: zer gertatu den, zein larria '
                            'den, eta Claude-rekin elkarrizketa batean zuzenean itsatsi dezakezun '
                            'prest dagoen prompt bat, diagnostikatu eta konpontzeko.',
 'admin_error_log_category_label': 'Kategoria',
 'admin_error_log_context_label': 'Testuingurua',
 'admin_error_log_copy_hint': 'Pasatu kurtsorea beheko koadroaren gainetik eta klik egin goiko '
                              'eskuineko kopiatzeko ikonoan.',
 'admin_error_log_count_caption': '{total} arazotik {n} erakusten.',
 'admin_error_log_empty': 'Ez dago errorerik erregistratuta. Dena garbi dago.',
 'admin_error_log_env_app_version': 'Aplikazioaren bertsioa',
 'admin_error_log_env_browser': 'Nabigatzailea',
 'admin_error_log_env_os': 'Sistema eragilea',
 'admin_error_log_env_python': 'Python bertsioa',
 'admin_error_log_environment_label': '💻 Ingurunea',
 'admin_error_log_evidence_label': '📋 Bildutako Ebidentzia',
 'admin_error_log_exception_message_label': 'Salbuespen-mezua',
 'admin_error_log_exception_type_label': 'Salbuespen mota',
 'admin_error_log_explanation_label': '🗣️ Zer gertatu den, hizkuntza arruntean',
 'admin_error_log_first_seen_label': 'Lehen aldiz ikusia',
 'admin_error_log_header': '🩺 IA Diagnostiko Gunea',
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
 'admin_error_log_last_seen_label': 'Azken aldiz ikusia',
 'admin_error_log_no_matches': 'Ez dago uneko iragazkiekin bat datorren errorerik.',
 'admin_error_log_no_package': 'Ez zen IA Diagnostiko Paketerik sortu erregistro honentzat -- '
                               'Diagnostiko Motorra existitu baino lehen erregistratu zen. '
                               'Xehetasun teknikoak oraindik eskuragarri daude behean.',
 'admin_error_log_no_traceback': 'Traceback-ik gabe -- hau pertsona batek bidalitako txosten bat '
                                 'izan zen, ez salbuespen automatiko bat.',
 'admin_error_log_not_available': 'ez dago eskuragarri',
 'admin_error_log_occurrences_label': 'Gertaerak',
 'admin_error_log_page_label': 'Orria',
 'admin_error_log_prompt_label': '🤖 IA Prompt-a',
 'admin_error_log_readiness_explainer': 'IA Prestutasun puntuazioa ez dago IAk sortuta -- '
                                        'erregistro honetarako beheko 7 ebidentzia-kategorietatik '
                                        'zenbat dauden aurkeztuta zenbatzen duen kontaketa sinplea '
                                        'da.',
 'admin_error_log_readiness_label': 'IA Prestutasuna',
 'admin_error_log_screenshot_error': '(ezin izan da pantaila-argazkia erakutsi)',
 'admin_error_log_screenshot_label': 'Pantaila-argazkia',
 'admin_error_log_search_label': '🔍 Bilatu (orria, errore mota edo mezua)',
 'admin_error_log_session_label': '🧭 Saioaren testuingurua',
 'admin_error_log_severity_filter_label': 'Larritasunaren arabera iragazi',
 'admin_error_log_severity_label': 'Larritasuna',
 'admin_error_log_status_filter_label': 'Egoeraren arabera iragazi',
 'admin_error_log_status_label': 'Egoera',
 'admin_error_log_summary_label': 'Laburpena',
 'admin_error_log_technical_label': '🔧 Xehetasun teknikoak',
 'admin_error_log_timeline_label': '🕒 Ebidentziaren denbora-lerroa',
 'admin_error_log_traceback_label': 'Traceback tekniko osoa',
 'admin_error_log_user_label': 'Erabiltzailea',
 'admin_error_log_when_label': 'Noiz',
 'admin_error_log_who_experienced_label': '👥 Nork bizi izan zuen ({n} erakutsita)',
 'admin_error_log_who_experienced_partial': 'Une honetan kargatutako gertaerak erakusten ari da; '
                                            'goiko kontaketa osoak erregistratutako gertaera '
                                            'guztiak islatzen ditu.',
 'admin_diag_filters_header': '🔍 Iragazkiak',
 'admin_diag_filter_page': 'Orrialdeak hau izan behar du',
 'admin_diag_filter_root_cause': 'Jatorrizko kausak hau izan behar du',
 'admin_diag_filter_user': 'Erabiltzaileak hau izan behar du',
 'admin_diag_filter_date_from': 'Data honetatik',
 'admin_diag_filter_date_to': 'Data honetara',
 'admin_diag_metric_total': 'Guztizko intzidentziak',
 'admin_diag_metric_open': '🟥 Irekiak',
 'admin_diag_metric_fixed': '✅ Konponduta',
 'admin_diag_metric_warnings': '⚠️ Abisuak',
 'admin_diag_section_selector': 'Ikusi',
 'admin_diag_tab_open': '🟥 Intzidentzia irekiak ({n})',
 'admin_diag_tab_fixed': '✅ Konpondutako intzidentziak ({n})',
 'admin_diag_tab_warnings': '⚠️ Abisuak ({n})',
 'admin_diag_tab_trends': '📈 Joeren analisia',
 'admin_diag_open_empty': 'Ez dago uneko iragazkiekin bat datorren intzidentzia irekirik.',
 'admin_diag_fixed_empty': 'Ez dago uneko iragazkiekin bat datorren konpondutako intzidentziarik.',
 'admin_diag_warnings_empty': 'Ez dago uneko iragazkiekin bat datorren abisurik.',
 'admin_diag_trends_empty': 'Oraindik ez dago nahikoa daturik joeren analisirako.',
 'admin_diag_trends_caption': 'Goian jadanik kargatutako gorabeherekin osorik eraikia: bolumena, '
                              'arazo-guneak eta arazo ohikoenak, begi-kolpe batean.',
 'admin_diag_warnings_caption': 'Abisuak ez dira kritikoak baina jakitea komeni da -- adibidez, '
                                'hausnarketa baten sorrera partziala -- eta goiko '
                                'aplikazio-erroreetatik bereizita mantentzen dira.',
 'admin_diag_trends_volume_header': '📅 Gertaerak denboran zehar',
 'admin_diag_trends_pages_header': '📍 Orrialde eraginenak',
 'admin_diag_trends_category_header': '🗂️ Gertaerak kategoriaka',
 'admin_diag_trends_uncategorized': 'Kategoriarik gabe',
 'admin_diag_trends_top_issues_header': '🔁 Intzidentzia ohikoenak',
 'admin_diag_trends_no_issues': 'Oraindik ez dago intzidentziarik erregistratuta.',
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
          'intro_body': 'Reflection Spacek idatzi berri duzun kasuaren dokumentazioa irakurtzen du '
                        'eta, behin betiko bihurtu aurretik, gogoeta-galderak eskaintzen ditu '
                        'zortzi dimentsio profesionaletan -- adibidez, pertsonaren ahotsa presente '
                        'dagoen ala ez, edo indarguneak alboratzen ari diren zailtasunen ondoan.',
          'guardrail_note': 'Tresnak inoiz ez du ebaluatzen, puntuatzen edo zure ordez '
                            'erabakitzen. Zuk erabakitzen duzu zer aldatu, hala badagokio, zure '
                            'dokumentazioan.',
          'journey_title': 'Hiru urratseko gogoeta-bidea',
          'journey_steps': ['1. Gaurko dokumentazioa -- aukeratu gogoeta egin nahi duzun '
                            'kasu-ohar(rak).',
                            '2. Aurrekari historikoa -- errebisatu kasu honetako aurreko zein '
                            'dokumentu agertu diren garrantzitsu gisa, eta sartu edo kendu nahi '
                            'dituzunak.',
                            '3. Gogoeta profesionala -- arakatu zortzi gogoeta-dimentsioak, nahi '
                            'izanez gero elkarrizketa labur bat izan haietako edozeinetan, eta '
                            'ondoren eguneratu eta bidali zure dokumentua.'],
          'practitioner_title': 'Profesionalaren area',
          'doc_section_title': '📝 Dokumentazioa -- kasu-ohar bat idaztea',
          'doc_section_body': 'Dokumentazioa orrian, sartu kasuaren erreferentzia, aukeratu '
                              'dokumentu mota eta hizkuntza, eta idatzi zure oharra. Gorde '
                              'sakatzean zirriborro pribatu gisa gordetzen da -- zuk bakarrik ikus '
                              'dezakezu -- Reflection Spacetik bidali arte.',
          'reflection_section_title': '🪞 Reflection Space -- bidali aurretik gogoeta egitea',
          'reflection_section_body': 'Reflection Space orrian: aukeratu gogoeta egin nahi duzun '
                                     'zirriborroa(k), errebisatu agertu den aurrekari historikoa '
                                     '(nahi ez duzuna desmarka dezakezu) eta jarraitu zure gogoeta '
                                     'sortzeko. Arakatu zortzi dimentsioetako edozein, ireki '
                                     'elkarrizketa labur bat nahi izanez gero, eta gero editatu '
                                     'eta bidali zure dokumentua. Ondoren saioaren '
                                     'erabilgarritasuna balora dezakezu -- guztiz aukerakoa.',
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
          'growth_section_title': '🌱 Nire Gogoeta -- zure egunkari pertsonala',
          'growth_section_body': 'Nire Gogoeta zure espazio pertsonala da: zein gai landu dituzun '
                                 'gehien eta zure azken gogoeta-uneen denbora-lerroa. Puntuaziorik '
                                 'gabe, beste inorekiko konparaziorik gabe, zuk bakarrik ikusgai.',
          'manager_title': 'Zuzendaritza-taldearen area',
          'learning_section_title': '📚 Ikaskuntza',
          'learning_section_body': 'Ikaskuntzak lau fitxa ditu: Taldearen presentzia (nor dagoen '
                                   'aktibo), Ezagutza-laguntzailea (galdera bat egin eta '
                                   'erakundearen kasu-dokumentazioan oinarritutako erantzuna '
                                   'jaso), Ikaskuntza-ikuspegiak (zein dimentsio agertu diren '
                                   'gehien) eta Taldearen ikaskuntza (azken sei hilabeteetako gai '
                                   'agregatuak). Hemengo guztia agregatua eta anonimoa da -- '
                                   'inoren lana ezin da bereizita seinalatu.',
          'case_history_section_title': '🗂️ Kasuen historiala',
          'case_history_section_body': 'Kasuen historialak dokumentazio osatua eta jasotako '
                                       'feedbacka erakusten ditu: erabilgarritasun-balorazioen eta '
                                       'iruzkinen ikuspegi orokorra, eta profesionalka '
                                       'multzokatutako dokumentu osatuak, editatuaren eta editatu '
                                       'gabearen artean aldatzeko aukerarekin, zer aldatu den '
                                       'ikusteko.',
          'research_metrics_section_title': '📊 Ikerketa-metrikak',
          'research_metrics_section_body': 'Ikerketa-metrikak (Sistema-administratzaileak '
                                           'bakarrik) proiektu-mailako ikuspegi agregatu bat '
                                           'eskaintzen du: guztira egindako saioak eta osatutako '
                                           'dokumentuak, dimentsio bakoitza zenbat aldiz seinalatu '
                                           'den arakatu den aldean, feedback-balorazioak eta CSV '
                                           'esportazioa.',
          'admin_title': '🛠️ Sistemaren administrazioa',
          'admin_section_body': 'Sistemaren administrazioak biltzen ditu erabiltzaileen kudeaketa, '
                                'dokumentuen indexazioa eta berreskurapen-probak, sistemaren '
                                'osasun-egoera, konfigurazioa, itzulpenen osasun-egiaztapenak, IA '
                                'Diagnostiko Zentroa (errore-erregistroa) eta kasuen ezagutzan '
                                'bilaketa.',
          'report_problem_title': '🚩 Arazo bat jakinaraztea',
          'report_problem_body': 'Orri bakoitzak 🚩 Arazo bat jakinarazi kontrol bat du alboko '
                                 'barran, edonorentzat eskuragarri. Deskribatu gertatutakoa zure '
                                 'hitzekin eta sakatu Bidali -- sistemak automatikoki gehitzen '
                                 'ditu orriaren, saioaren eta nabigazioaren datuak.',
          'privacy_title': '🔒 Pribatutasuna eta datuak',
          'privacy_points': ['Zirriborro pendienteak pribatuak dira -- zuk bakarrik ikus edo ireki '
                             'ditzakezu bidali baino lehen.',
                             'Gogoeta-elkarrizketen edukia ez da inoiz saioaren mugetatik haratago '
                             'gordetzen -- zein gai landu den eta noiz bakarrik erregistratzen da.',
                             'Nire Gogoeta pertsonala da eta ez du konparaziorik onartzen: '
                             'puntuaziorik gabe, sailkapenik gabe, zuk bakarrik ikusgai.',
                             'Erakunde osoko ikuspegiek soilik datu agregatu eta anonimoekin '
                             'funtzionatzen dute.',
                             'Rolen araberako sarbide-kontrola bi mailatan aplikatzen da aplikazio '
                             'osoan.']},
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
 'admin_usage_qdrant_detail_header': 'Qdrant-en xehetasuna',
 'admin_usage_qdrant_vectors': 'Gordetako bektoreak',
 'admin_usage_qdrant_capacity': 'Konfiguratutako edukiera',
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
 'admin_usage_forecast_vectors': 'Bektore-kopuru proiektatua',
 'admin_usage_forecast_presets_header': 'Ohiko eszenatokiak',
 'admin_usage_forecast_current': 'Uneko',
 'admin_usage_forecast_col_users': 'Erabiltzaileak',
 'admin_usage_forecast_col_reflections': 'Hausnarketak/hilabete',
 'admin_usage_forecast_col_claude_cost': 'Claude-ren kostu estimatua/hilabete',
 'admin_usage_forecast_estimate_disclaimer': '⚠️ Goiko proiekzio guztiak ESTIMAZIOAK dira, gaur '
                                             'egun behatutako batez bestekoetan oinarrituta, ez '
                                             'bermatutako kosteak.',
 'findings_evidence_caption': 'Behaketa honen oinarri den dokumentazioko pasartea:',
 'findings_unverified_notice': 'IAk proposatutako {count} pasarte ez datoz testuarekin zehazki bat, eta ez dira erakusten.',
 'findings_notes_header': 'Behaketa honi buruzko nire oharrak',
 'findings_notes_privacy': 'Zure oharrak eta balorazioak pribatuak dira: zuk bakarrik ikus ditzakezu. IAk esandakotik bereizita gordetzen dira, eta hori ez da inoiz aldatzen.',
 'findings_label_prompt': 'Zer iruditu zaizu?',
 'findings_label_none': 'Baloratu gabe',
 'findings_labels': {'useful': 'Baliagarria', 'not_relevant': 'Garrantzirik gabea', 'uncertain': 'Ez daukat argi', 'discuss': 'Geroago komentatzeko'},
 'findings_misread_label': 'Uste dut IAk ez duela testuingurua ondo ulertu',
 'findings_alternative_label': 'Beste azalpen posible bat (aukerakoa)',
 'findings_note_label': 'Nire hausnarketa edo oharra (aukerakoa)',
 'findings_save_button': 'Gorde nire oharrak',
 'findings_save_success': 'Oharrak gorde dira.',
 'findings_save_error': 'Ezin izan dira zure oharrak gorde. Saiatu berriro une batean.',
 'findings_not_saved_notice': 'Hausnarketa hau ezin izan da gorde; beraz, ezingo dituzu horri buruzko oharrak gorde. Normaltasunez jarrai dezakezu lanean.',
 'findings_journal_header': 'Gordetako behaketak eta zure oharrak',
 'findings_journal_intro': 'Hemen zure hausnarketetako behaketetara itzul zaitezke, oinarri dituzten pasarte zehatzekin, eta zure oharrak idatzi edo berrikusi. Zure oharrak zuretzat bakarrik dira.',
 'findings_journal_empty': 'Oraindik ez dago gordetako behaketarik. Zure hurrengo hausnarketaren ondoren agertuko dira hemen.',
 'findings_journal_count': '{total} gordetako behaketa — {page}. orria ({pages} orritik)',
 'findings_journal_newer': '← Berrienak',
 'findings_journal_older': 'Zaharrenak →'}
