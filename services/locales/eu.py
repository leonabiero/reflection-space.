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
 'home_subtitle': 'Praktikan hausnartzeko gune bat.',
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
 'learning_preview_caption': 'Azken {total} hausnarketetan oinarrituta',
 'learning_flagged_caption': 'Azken {total} hausnarketetatik {count}-tan identifikatua',
 'case_history_date_filter_label': 'Historia ikusi:',
 'case_history_toggle_label': 'Erakutsi:',
 'case_history_edited_option': 'Editatuak',
 'case_history_not_edited_option': 'Editatu gabeak',
 'case_history_no_items_for_filter': 'Ez dago hausnarketarik hautapen honetarako.',
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
 'workspace_document_header': 'Kasuaren testua (ez da gordetzen)',
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
 'growth_entry_line': '**{theme}** — {case} hausnarketa — {count} truke — {date}',
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
             'erreflexiboari buruz. Erantzunak gordetako hausnarketetan oinarritzen dira soilik — '
             'inoiz ez kanpoko ezagutza orokorrean.',
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
 'ka_evidence_case_col': 'Hausnarketaren kodea',
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
 'admin_anon_empty_warning': 'Idatzi edo itsatsi lehenik lagin-testu bat eta sakatu berriro '
                             'botoia.',
 'admin_anon_no_changes': 'Anonimizatzaileak ez du ordezkatzeko datu pertsonalik aurkitu testu '
                          'honetan.',
 'admin_anon_stale_note': 'Testua aldatu duzu azken probatik: sakatu berriro botoia emaitza '
                          'eguneratua ikusteko.',
 'admin_anon_tags_help': 'Etiketak: [PERSON] = pertsona-izena · [LOCATION] = tokia · [ADDRESS] = '
                         'helbidea · [ORGANISATION] = zentroa edo erakundea · [ID] = NAN/AIZ, '
                         'espedientea, kontua edo beste identifikatzaile bat · [PHONE] = telefonoa '
                         '· [EMAIL] = posta elektronikoa · [DATE] = data.',
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
          'intro_body': 'Reflection Spacek kasu bati buruz une berean hausnartzen laguntzen dizu: '
                        'kasua idatzi, itsatsi edo igotzen duzu eta hausnarketarako galderak '
                        'eskaintzen dizkizu zortzi dimentsio profesionaletan -- adibidez, '
                        'erabiltzailearen ahotsa agertzen den, edo zailtasunen ondoan haren '
                        'indarguneak ahazten ari diren. Ez da dokumentuak gordetzeko lekua: '
                        'hausnarketa bakarrik gordetzen da.',
          'guardrail_note': 'Tresnak ez du inoiz ezer kalifikatzen, puntuatzen edo zure ordez '
                            'erabakitzen. Zuk erabakitzen duzu zer egin, ezer egitekotan, '
                            'pentsarazi dizunarekin.',
          'journey_title': 'Hiru urratseko gogoeta-bidea',
          'journey_steps': ['1. Zure kasua -- idatzi, itsatsi edo igo kasua, aukeratu testu mota, '
                            'markatu datu pertsonalik gabeko gai batzuk eta, nahi baduzu, lotu '
                            'aurreko hausnarketa bat bere kodearekin.',
                            '2. Aurreko hausnarketak -- berrikusi lotutako edo gai komunak '
                            'dituzten zure aurreko hausnarketak, eta sartu edo kendu nahi '
                            'dituzunak.',
                            '3. Hausnarketa profesionala -- arakatu zortzi dimentsio '
                            'erreflexiboak, hitz egin labur haietako bati buruz nahi baduzu, '
                            'gehitu zure oharrak eta amaitu. Kasuaren testua baztertu egiten da '
                            'amaitzean.'],
          'practitioner_title': 'Profesionalaren area',
          'doc_section_title': '📝 Zure kasua -- idatzi, itsatsi edo igo',
          'doc_section_body': 'Jada ez dago Dokumentazio orri bereizirik. Reflection Spacen kasua '
                              'idatzi edo itsasten duzu (edo Word, PDF edo testu bat igo: testua '
                              'bakarrik irakurtzen da). Hausnarketa bakoitzak kode neutro bat '
                              'jasotzen du (adibidez RS-7F3K2Q) eta markatzen dituzun gaiak; '
                              'horietako ezerk ez du pertsona identifikatzen. Kasuaren testua ez '
                              'da inoiz gordetzen.',
          'reflection_section_title': '🪞 Reflection Space -- une berean hausnartu',
          'reflection_section_body': 'Jarraitu ondoren, lotutako edo gai komunak dituzten zure '
                                     'aurreko hausnarketak ikusiko dituzu (kontuan hartu nahi ez '
                                     'dituzunei marka ken diezaiekezu) eta zure hausnarketa '
                                     'sortuko duzu. Arakatu zortzi dimentsioetako edozein, ireki '
                                     'elkarrizketa labur bat nahi baduzu, gehitu zure oharrak eta '
                                     'sakatu Amaitu hausnarketa. Ondoren saioaren '
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
                                   'aktibo), Ezagutza-laguntzailea (egin galdera bat eta jaso '
                                   'erakundearen gordetako hausnarketetan oinarritutako '
                                   'erantzuna), Ikaskuntzak (zein dimentsio agertu diren maizen) '
                                   'eta Taldearen ikaskuntza (azken sei hilabeteetako gai '
                                   'bateratuak). Hemen dena da bateratua eta anonimoa -- ezin da '
                                   'inoren lana bereiz seinalatu.',
          'case_history_section_title': '🗂️ Hausnarketen historia',
          'case_history_section_body': 'Hausnarketen historiak jasotako feedbacka '
                                       '(erabilgarritasun-balorazioak eta iruzkinak) eta gordetako '
                                       'hausnarketak erakusten ditu, bakoitza bere kode '
                                       'neutroarekin, gaiekin eta IAren behaketekin. Data eta '
                                       'gaiaren arabera iragazi daiteke. Ez du inoiz kasuaren '
                                       'testua edo profesionalen ohar pribatuak erakusten.',
          'research_metrics_section_title': '📊 Ikerketa-metrikak',
          'research_metrics_section_body': 'Ikerketa-metrikek (Sistemaren administratzailea '
                                           'bakarrik) piloto-mailako ikuspegi bateratua eskaintzen '
                                           'dute: hausnarketa-saioak eta gordetako behaketak '
                                           'guztira, dimentsio bakoitza zenbatetan seinalatu den '
                                           'eta zenbatetan arakatu den, feedback-balorazioak eta '
                                           'CSV esportazio bat.',
          'admin_title': '🛠️ Sistemaren administrazioa',
          'admin_section_body': 'Sistemaren administrazioak biltzen ditu erabiltzaileen kudeaketa, '
                                'dokumentuen indexazioa eta berreskurapen-probak, sistemaren '
                                'osasun-egoera, konfigurazioa, itzulpenen osasun-egiaztapenak, IA '
                                'Diagnostiko Zentroa (errore-erregistroa) eta kasuen ezagutzan '
                                'bilaketa. «Hausnarketak bakarrik» aldaketaren aurretik gordetako '
                                'dokumentu zaharrak behin betiko ezabatzeko aukera ere ematen du.',
          'report_problem_title': '🚩 Arazo bat jakinaraztea',
          'report_problem_body': 'Orri bakoitzak 🚩 Arazo bat jakinarazi kontrol bat du alboko '
                                 'barran, edonorentzat eskuragarri. Deskribatu gertatutakoa zure '
                                 'hitzekin eta sakatu Bidali -- sistemak automatikoki gehitzen '
                                 'ditu orriaren, saioaren eta nabigazioaren datuak.',
          'privacy_title': '🔒 Pribatutasuna eta datuak',
          'privacy_points': ['Kasuaren testua ez da inoiz gordetzen -- hausnarketak irauten duen '
                             'bitartean bakarrik dago eta amaitzean baztertzen da.',
                             'Hausnarketa bakoitza kode neutro batekin eta datu pertsonalik gabeko '
                             'gaiekin identifikatzen da, inoiz ez izenekin.',
                             'Behaketei buruzko zure oharrak pribatuak dira -- zuk bakarrik ikus '
                             'ditzakezu.',
                             'Elkarrizketa erreflexiboen edukia ez da inoiz saiotik haratago '
                             'gordetzen -- zein gai arakatu zen eta noiz bakarrik erregistratzen '
                             'da.',
                             'Nire Hausnarketa pertsonala da eta ez du konparaziorik onartzen: '
                             'puntuaziorik gabe, sailkapenik gabe, zuk bakarrik ikus dezakezu.',
                             'Roletan oinarritutako sarbide-kontrola bi mailatan aplikatzen da '
                             'aplikazio osoan.']},
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
 'findings_evidence_caption': 'Behaketa honen oinarri den kasuaren testuko pasartea:',
 'findings_unverified_notice': 'IAk proposatutako {count} pasarte ez datoz testuarekin zehazki '
                               'bat, eta ez dira erakusten.',
 'findings_notes_header': 'Nire oharrak eta taldearekin partekatzea',
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
 'findings_journal_newer': '← Berrienak',
 'findings_journal_older': 'Zaharrenak →',
 'nav_patterns': '🔎 Patroien berrikuspena',
 'findings_share_label': 'Partekatu behaketa hau taldearen berrikuspenarekin',
 'findings_share_help': 'Markatzen baduzu, behaketa eta bere aipu zehatza kudeaketa-taldearen '
                        'patroien berrikuspenean ager daitezke, zure izenik eta oharrik gabe. '
                        'Noiznahi kendu dezakezu. Markatzen ez baduzu, inork ez du ikusiko.',
 'findings_notes_privacy': 'Zure oharrak eta balorazioak pribatuak dira: zuk bakarrik ikus '
                           'ditzakezu. IAk esandakotik bereizita gordetzen dira, eta hori ez da '
                           'inoiz aldatzen. «Partekatu» markatzen baduzu bakarrik partekatzen dira '
                           'behaketa eta bere aipua (inoiz ez zure izena edo oharrak).',
 'patterns_title': '🔎 Patroien berrikuspena',
 'patterns_no_access': 'Orri hau gainbegiratzerako eta programaren kudeaketarako bakarrik da.',
 'patterns_intro': 'Orri honek partekatutako behaketetan errepikatzen diren gaiak bilatzen '
                   'laguntzen dio taldeari. Erakusten duena hausnarketarako patroi hautagaiak '
                   'dira, ez ondorioak: behaketa antzeko multzo batek ez du alborapenik edo jardun '
                   'txarrik frogatzen, eta borondatez partekatutako sorta txiki honek ez du '
                   'erakundea ordezkatzen. Taldeak erabakitzen du patroi batek zer esan nahi duen, '
                   'esan nahi badu.',
 'patterns_pool_header': 'Zer dago berrikusteko',
 'patterns_pool_caption': 'Profesionalek partekatzea erabaki dituzten behaketak soilik agertzen '
                          'dira hemen. Ez duzu inoiz ikusten nork idatzi dituen, ezta haien ohar '
                          'pribatuak ere.',
 'patterns_filter_lenses': 'Mugatu hausnarketa-puntu hauetara (hutsik = guztiak)',
 'patterns_filter_from': 'Noiztik (aukerakoa)',
 'patterns_filter_to': 'Noiz arte (aukerakoa)',
 'patterns_pool_empty': 'Oraindik ez dago partekatutako behaketarik iragazki hauekin.',
 'patterns_pool_counts': '{observations} partekatutako behaketa, {reflections} hausnarketatik eta '
                         '{cases} kasu-erreferentzia desberdinetatik.',
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
 'patterns_pool_truncated': 'Aldi berean alderatzen direnak baino partekatutako behaketa gehiago '
                            'daude; azkeneko {max} erabiltzen dira.',
 'patterns_not_enough': 'Gutxienez {minimum} partekatutako behaketa behar dira patroiak bilatzeko.',
 'patterns_generate_button': 'Bilatu patroiak',
 'patterns_generating': 'Patroiak bilatzen…',
 'patterns_busy': 'Bilaketa bat martxan dago jada. Itxaron amaitu arte eta saiatu berriro.',
 'patterns_unavailable': 'Esanahiaren araberako alderaketa-zerbitzua ez dago konfiguratuta; beraz, '
                         'orain ezin dira patroiak bilatu.',
 'patterns_none_found': 'Ez da gutxienekoak betetzen dituen multzorik aurkitu {observations} '
                        'behaketen artean. Probatu ezarpen zabalago bat, edo itxaron partekatutako '
                        'behaketa gehiago izan arte.',
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
 'patterns_lost_members': 'Patroi honetako {count} behaketa ez daude eskuragarri jada (egileak '
                          'kenduak edo ezabatuak). Idatzitako azalpenak oraindik islatu ditzake: '
                          'bilatu patroiak berriro horretan fidatu aurretik.',
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
 'doc_import_loaded': 'Testua kargatuta. Berrikusi eta zuzendu jarraitu aurretik: ez fitxategia ez '
                      'testua ez dira gordetzen.',
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
 'report_how_to_read': 'Txosten honek patroi hautagaiak biltzen ditu: taldeak komentatu nahi '
                       'ditzakeen behaketa antzeko multzoak. Ez dira ondorioak. Behaketa antzeko '
                       'multzo batek ez du alborapenik edo jardun txarrik frogatzen, eta behaketak '
                       'profesionalek borondatez partekatzea erabaki duten sorta txiki batetik '
                       'datoz; beraz, ez dute erakundea ordezkatzen. Taldeak erabakitzen du patroi '
                       'bakoitzak zer esan nahi duen, esan nahi badu.',
 'report_search_title': 'Zein bilaketatik datorren',
 'report_search_line': '{date}(e)ko bilaketa: partekatutako {observations} behaketa alderatu dira '
                       'eta {patterns} patroi hautagai aurkitu dira.',
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
 'report_limits_list': ['Esanahiaren antzagatiko multzokatze automatikoa da; erlazionatu gabeko '
                        'behaketak elkartu ditzake edo erlazionatuak bereizi.',
                        'Behaketak IAren laguntzako hausnarketetatik eta partekatzea erabaki duten '
                        'profesionalengandik datoz; ez dira erregistro osoa edo adierazgarria.',
                        'Kasu-erreferentziak eskuz idazten dira: akats batek kasu bera bi gisa '
                        'kontatzea eragin dezake.',
                        'Azalpen-testua IAk idazten du behaketetatik abiatuta, eta bilaketaren '
                        'ondoren kendutako behaketak islatu ditzake.',
                        'Txosten honetako ezerk ez du identifikatzen behaketa nork idatzi duen, '
                        'ezta bere ohar pribatuak barne hartzen ere.'],
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
 'nav_corpus': '📚 Testuen azterketa',
 'corpus_title': '📚 Testuen azterketa',
 'corpus_no_access': 'Orri hau gainbegiratzerako eta programaren koordinaziorako soilik da.',
 'corpus_intro': 'Hemen kudeaketa-taldeak lehendik dauden testuak (adibidez, EDEren testu '
                 'gordinak) kargatu ditzake, eta hainbat dokumentutan errepikatzen diren esanahi '
                 'antzeko pasarteak bilatu. Agertzen direnak hausnarketarako eredu hautagaiak '
                 'dira, ez ondorioak: esamolde errepikatu batek ez du alborapenik edo jardun '
                 'txarrik frogatzen, eta dokumentu motagatik edo txantiloi batengatik izan '
                 'daiteke.',
 'corpus_privacy_note': 'Gorde aurretik, testu bakoitzari izenak eta datu pertsonalak kentzen '
                        'zaizkio aplikazioaren sistema automatikoarekin, eta baliteke dena ez '
                        'detektatzea: kargatu anonimizatuta dauden testuak soilik. Testuak zenbaki '
                        'batekin identifikatzen dira (T-001, T-002…); fitxategien izenak ez dira '
                        'gordetzen. Bilduma hau profesionalen hausnarketetatik bereizita dago, eta '
                        'gainbegiratzeak eta koordinazioak soilik ikusten dute.',
 'corpus_collection_header': 'Testu-bilduma',
 'corpus_create_header': 'Sortu bilduma berri bat',
 'corpus_create_name_label': 'Bildumaren izena',
 'corpus_create_button': 'Sortu bilduma',
 'corpus_created_ok': 'Bilduma sortu da.',
 'corpus_name_needed': 'Idatzi izen bat. (Gehienez {max} bilduma izan daitezke.)',
 'corpus_none_yet': 'Oraindik ez dago bildumarik. Sortu bat hasteko.',
 'corpus_select_label': 'Bilduma',
 'corpus_option': '{name} ({documents} testu)',
 'corpus_add_header': 'Gehitu testuak',
 'corpus_add_intro': 'Testuak banan-banan, batera edo guztiak aldi berean gehi ditzakezu. Testu '
                     'bera bi aldiz gehitzen baduzu, aplikazioak antzematen du eta ez du '
                     'bikoizten.',
 'corpus_upload_label': 'Igo fitxategiak (Word, PDF edo testua)',
 'corpus_too_many_files': 'Fitxategi gehiegi hautatu dituzu aldi berean: lehenengo {max} soilik '
                          'gehituko dira. Igo gainerakoak gero.',
 'corpus_add_files_button': 'Gehitu hautatutako fitxategiak',
 'corpus_adding': 'Testuak gehitzen…',
 'corpus_paste_label': 'Edo itsatsi testu bat hemen',
 'corpus_add_paste_button': 'Gehitu itsatsitako testua',
 'corpus_paste_empty': 'Itsatsi lehenik testu bat.',
 'corpus_pasted_name': 'Itsatsitako testua',
 'corpus_added_summary': '{total} testutik {added} gehitu dira.',
 'corpus_result_added': '{name}: {label} gisa gehitu da ({passages} pasarte).',
 'corpus_result_duplicate': '{name}: dagoeneko bildumako {label} da; ez da bikoiztu.',
 'corpus_result_empty': '{name}: ezin izan da pasarte erabilgarririk atera (testu laburregia).',
 'corpus_result_full': '{name}: bilduma beteta dago (gehienez {max} testu).',
 'corpus_result_refused': '{name}: {reason}',
 'corpus_result_error': '{name}: ezin izan da gehitu. Saiatu berriro.',
 'corpus_docs_header': 'Bildumako testuak',
 'corpus_docs_empty': 'Bilduma honek ez du testurik oraindik.',
 'corpus_docs_counts': 'Bildumak {documents} testu ditu, {passages} pasartetan banatuta.',
 'corpus_docs_list_header': 'Ikusi eta ezabatu testuak',
 'corpus_doc_line': '{label} — {chars} karaktere — {passages} pasarte',
 'corpus_doc_delete': 'Ezabatu',
 'corpus_doc_deleted_ok': 'Testua ezabatu da, bere pasarteekin eta ereduetan zuen lekuarekin.',
 'corpus_docs_more': 'Eta {count} testu gehiago.',
 'corpus_delete_collection': 'Ezabatu bilduma osoa',
 'corpus_delete_collection_help': 'Bilduma honetako testu, pasarte eta eredu guztiak ezabatzen '
                                  'dira. Ezin da desegin.',
 'corpus_delete_collection_confirm': 'Ulertzen dut dena ezabatuko dela eta ezin dela desegin',
 'corpus_delete_collection_button': 'Ezabatu bilduma',
 'corpus_deleted_ok': 'Bilduma ezabatu da.',
 'corpus_generate_header': 'Bilatu errepikatzen diren pasarteak',
 'corpus_settings_header': 'Bilaketaren doikuntzak',
 'corpus_settings_intro': 'Doikuntza hauek abiapuntuak dira, ez balio frogatuak. Aldatu itzazu eta '
                          'alderatu emaitzak.',
 'corpus_similarity_label': 'Pasarteen artean eskatutako antzekotasuna',
 'corpus_similarity_help': 'Zabalak antzekotasun ahulagoa duten pasarteak multzokatzen ditu '
                           '(multzo gehiago, zarata gehiago). Zorrotzak antzekotasun handiagoa '
                           'eskatzen du (multzo gutxiago, fidagarriagoak).',
 'corpus_min_passages_label': 'Gutxieneko pasarte kopurua ereduko',
 'corpus_min_documents_label': 'Gutxieneko testu desberdinen kopurua ereduko',
 'corpus_questions_switch': 'Sartu AAk idatzitako galderak',
 'corpus_questions_help': 'Desaktibatzen baduzu, AAk ez du galderarik idatziko eta ez da bat ere '
                          'erakutsiko. Gainerako azalpenak idatziko dira.',
 'corpus_cost_note': 'Bilatzeak AA erabiltzen du gehienez {max_patterns} azalpen idazteko (zentimo '
                     'gutxi batzuk guztira) eta pasarte berriei esanahia emateko (oso merkea, eta '
                     'pasarte bakoitzeko behin bakarrik). Botoia berriro sakatzen baduzu soilik '
                     'ordaintzen da berriro.',
 'corpus_truncated': 'Bildumak bilaketa batean sartzen direnak baino pasarte gehiago ditu; '
                     'lehenengo {max} erabiliko dira (testuen ordenaren arabera).',
 'corpus_not_enough': 'Bilatzeko gutxienez {minimum} testu behar dira bilduman.',
 'corpus_generate_button': 'Bilatu errepikatzen diren pasarteak',
 'corpus_generating': 'Lanean… minutu bat behar izan dezake.',
 'corpus_busy': 'Bilaketa bat martxan dago jada. Itxaron amaitu arte.',
 'corpus_unavailable': 'Esanahiak alderatzen dituen zerbitzua ez dago konfiguratuta, beraz ezin da '
                       'bilatu orain.',
 'corpus_none_found': 'Ez da testu desberdin nahikotan agertzen den multzorik aurkitu ({documents} '
                      'testu, {passages} pasarte aztertuta). Probatu antzekotasun zabalagoarekin '
                      'edo gutxieneko txikiagoekin.',
 'corpus_generated_ok': '{patterns} eredu hautagai aurkitu dira {documents} testutan.',
 'corpus_not_embedded': '{count} pasarte ezin izan dira alderatu oraingoan eta kanpoan geratu '
                        'dira.',
 'corpus_fallback_notice': '{count} eredutan ezin izan da azalpen automatikoa idatzi; testu sinple '
                           'bat erakusten da eta berriro saia zaitezke.',
 'corpus_review_header': 'Berrikusi eredu hautagaiak',
 'corpus_no_runs': 'Oraindik ez da bilaketarik egin bilduma honetan.',
 'corpus_run_select': 'Bilaketa',
 'corpus_run_option': '{date} — {documents} testu — {patterns} eredu',
 'corpus_run_caption': 'Antzekotasuna: {level} · gutxieneko pasarteak: {min_passages} · gutxieneko '
                       'testuak: {min_documents} · AAren galderak: {questions}',
 'corpus_yes': 'bai',
 'corpus_no': 'ez',
 'corpus_none_in_view': 'Hautatutako egoeretan ez dago eredurik.',
 'corpus_no_groups_note': 'Testuek ez daramate etiketarik (ez nork idatzi dituen, ez nori '
                          'buruzkoak diren), beraz orri honek ezin du ezer esan talde desberdinak '
                          'berdin ala desberdin tratatzen diren. Zer errepikatzen den eta zenbat '
                          'testutan bakarrik erakusten du.',
 'corpus_item_header': '{title} — {status} — testuak: {documents} / {total}',
 'corpus_counts_line': 'Agertzen den testu kopurua: {documents} / {total} (% {percent}) · '
                       '{passages} pasarte',
 'corpus_documents_line': 'Testuak: {labels}',
 'corpus_lost_members': 'Eredu honetako {count} pasarte ez daude eskuragarri jada (testua ezabatu '
                        'da). Idatzitako azalpenak oraindik haiek islatu ditzake: bilatu berriro '
                        'fidatu aurretik.',
 'corpus_below_minimum': 'Oraingo testuekin, multzo honek ez ditu jada aurkitu zenean zituen '
                         'gutxienekoak betetzen.',
 'corpus_passages_header': 'Pasarte zehatzak',
 'corpus_more_passages': 'Eta {count} pasarte gehiago ez dira hemen erakusten.',
 'corpus_exclude_button': 'Pasarte hau ez dagokio eredu honi',
 'corpus_excluded_ok': 'Pasartea ereduatik kendu da.',
 'corpus_restored_ok': 'Pasartea berriro sartu da.',
 'corpus_read_header': 'Irakurri testu bakoitza hausnarketa-lenteekin',
 'corpus_read_intro': 'AAk testu bakoitza bereizita irakurtzen du profesionalek erabiltzen '
                      'dituzten zortzi hausnarketa-lente berberekin (pertsonaren ahotsa, behaketa '
                      'eta interpretazioa, etiketak eta hizkuntza, alborapen posiblea, etab.) eta '
                      'testuan benetan agertzen diren aipuak soilik gordetzen ditu. Ez ditu '
                      'testuak elkarren artean alderatzen: kontaketak aplikazioak kalkulatzen '
                      'ditu.',
 'corpus_read_no_texts': 'Gehitu testuak irakurri ahal izateko.',
 'corpus_read_status': '{documents} testutik {read} irakurrita; {unread} falta dira.',
 'corpus_read_nothing': 'Testu guztiak irakurrita daude.',
 'corpus_read_cost_note': 'Testu bakoitza AAri egindako zortzi deirekin irakurtzen da: gutxi '
                          'gorabehera {per_text} $ testuko. Sorta honek (gehienez {batch} testu) '
                          '{cost} $ inguru kostatuko du. Testuak sortetan irakurtzen dira, klik '
                          'bakoitzak asko ez luzatzeko; sakatu berriro hurrengoekin jarraitzeko.',
 'corpus_read_button': 'Irakurri hurrengo {count} testuak',
 'corpus_reading': 'Testuak irakurtzen…',
 'corpus_read_progress': '{total} testutik {done} irakurrita',
 'corpus_read_busy': 'Irakurketa bat martxan dago jada. Itxaron amaitu arte.',
 'corpus_read_unavailable': 'AA zerbitzua ez dago konfiguratuta, beraz ezin da irakurri orain.',
 'corpus_read_done': '{count} testu irakurri dira. {remaining} falta dira.',
 'corpus_read_failed_lenses': '{count} irakurketa ezin izan dira osatu; hurrengoan berriro '
                              'saiatuko dira.',
 'corpus_read_caveat': '"Aipatua" esan nahi du AAk testu horretan lente horrekin behaketa bat '
                       'planteatu duela. Ez du neurtzen zerbait zenbatetan gertatzen den, eta ezer '
                       'aipatzen ez duenean horrek ez du esan nahi testua horretatik libre '
                       'dagoenik.',
 'corpus_lens_counts_header': 'Zein lente aipatu diren, testuka',
 'corpus_lens_item': '{lens} — aipatutako testuak: {raised} / {considered}',
 'corpus_lens_failed_note': '{count} testutan lente hau ezin izan da irakurri.',
 'corpus_lens_none': 'AAk ez du ezer planteatu lente honekin.',
 'corpus_lens_no_quote': 'Aipu zehatzik gabe (behaketa testuan falta den zerbaiti buruzkoa izan '
                         'daiteke).',
 'corpus_lens_unverified': 'Proposatutako {count} pasarte ezin izan dira testuan egiaztatu eta ez '
                           'dira erakusten.',
 'corpus_text_view_header': 'Ikusi testu baten irakurketa',
 'corpus_text_select': 'Testua',
 'corpus_text_no_reading': 'Testu hau ez da oraindik irakurri.',
 'corpus_text_lens_failed': 'Lente hau ezin izan da irakurri.',
 'corpus_text_lens_none': 'AAk ez du ezer planteatu.',
 'corpus_read_again_header': 'Irakurri berriro testu guztiak',
 'corpus_read_again_help': 'Bilduma honen irakurketa guztiak ezabatzen ditu hutsetik berriro '
                           'irakurri ahal izateko (berriro ordaintzen da).',
 'corpus_read_again_confirm': 'Ulertzen dut irakurketak ezabatuko direla eta berriro irakurtzeak '
                              'berriro kostatzen duela',
 'corpus_read_again_button': 'Ezabatu irakurketak',
 'corpus_read_cleared_ok': 'Irakurketak ezabatu dira.',
 'corpus_terms_header': 'Hitzen eta esamoldeen zerrenda',
 'corpus_terms_intro': 'Zerrendako hitz edo esamolde bakoitza zenbat testutan agertzen den '
                       'zenbatzen du. Idatzitako hitzen zenbaketa soila da: ez du esanahia '
                       'interpretatzen, eta hitz bat ez agertzeak ez du esan nahi ideia testuan '
                       'beste hitz batzuekin ez dagoenik.',
 'corpus_terms_how': 'Idatzi hitz edo esamolde bat lerroko. Maiuskulek eta azentuek ez dute '
                     'axolarik. Gehitu * hitz baten amaieran bere bukaerak barne hartzeko: «etxe*» '
                     'hitzak etxea, etxeak, etxean… aurkitzen ditu. Batez ere euskaraz '
                     'erabilgarria da, hitzek amaieran aldatzen baitira; gaztelaniaz, «agresiv*» '
                     'hitzak agresivo, agresiva, agresivos… aurkitzen ditu.',
 'corpus_terms_add_label': 'Hitzak edo esamoldeak (bat lerroko)',
 'corpus_terms_add_button': 'Gehitu zerrendara',
 'corpus_terms_empty_input': 'Idatzi gutxienez hitz edo esamolde bat.',
 'corpus_terms_added': 'Gehituta: {added}. Zerrendan zeuden: {duplicates}. Baliogabeak: {invalid}.',
 'corpus_terms_invalid_lines': 'Lerro hauek ezin izan dira erabili: {lines}. Letrak eta zenbakiak '
                               'bakarrik onartzen dira (eta * hitzaren amaieran, gutxienez hiru '
                               'letraren ondoren), gehienez {words} hitz esamolde bakoitzeko.',
 'corpus_terms_full': 'Zerrendak gehienezko mugara iritsi da: {max} hitz edo esamolde.',
 'corpus_terms_starter_help': 'Abiapuntu bat: kasu-oharretan batzuetan pertsonak modu negatibo edo '
                              'itxian deskribatzeko agertzen diren hitz eta esamoldeak. '
                              'Adibide-zerrenda bat da: editatu, kendu balio ez duena eta gehitu '
                              'zurea. Euskarazko zatia euskaraz dakien pertsona batek berrikusi '
                              'behar du benetan erabili aurretik.',
 'corpus_terms_starter_button': 'Gehitu hasierako zerrenda (gaztelania eta euskara)',
 'corpus_terms_starter_done': 'Hasierako zerrenda gehituta: {added} berri ({duplicates} bazeuden).',
 'corpus_terms_basque_review': 'Hasierako zerrendako euskarazko hitzak lehen proposamen bat dira: '
                               'euskaraz dakien pertsona batek berrikusi behar ditu.',
 'corpus_terms_none_yet': 'Zerrenda hutsik dago. Gehitu hitzak edo erabili hasierako zerrenda.',
 'corpus_terms_no_texts': 'Gehitu testuak bildumara zenbatzeko zerbait egon dadin.',
 'corpus_terms_counts_header': 'Emaitzak',
 'corpus_terms_caveat': '«Testuak» zutabeak hitza gutxienez behin duten testuak zenbatzen ditu. Ez '
                        'du neurtzen zerbait ohikoa den, ezta on edo txarra den ere: hitz bat '
                        'zerbait ukatzeko ere erabil daiteke («ez da oldarkorra»). Begiratu beti '
                        'testuingurua.',
 'corpus_terms_col_term': 'Hitza edo esamoldea',
 'corpus_terms_col_texts': 'Testuak',
 'corpus_terms_col_times': 'Aldiak',
 'corpus_terms_texts_cell': '{documents} / {total}',
 'corpus_terms_remove_label': 'Kendu zerrendatik',
 'corpus_terms_remove_button': 'Kendu hautatutakoak',
 'corpus_terms_removed_ok': 'Hitzak zerrendatik kendu dira.',
 'corpus_terms_context_header': 'Non agertzen den',
 'corpus_terms_context_select': 'Aukeratu hitz edo esamolde bat',
 'corpus_terms_context_none': 'Ez da testu batean ere agertzen.',
 'corpus_terms_context_caption': 'Parentesi artean, testu horretan zenbat aldiz agertzen den.',
 'corpus_terms_context_line': '{label} ({times})',
 'corpus_terms_context_more': '… eta {count} testu gehiago.',
 'corpus_terms_text_header': 'Zerrendako hitzak testu batean',
 'corpus_terms_text_select': 'Aukeratu testu bat',
 'corpus_terms_text_none': 'Zerrendako hitzik ez da agertzen testu honetan.',
 'corpus_terms_text_line': '{term}: {times}',
 'corpus_terms_download': 'Deskargatu taula osoa (CSV)',
 'corpus_report_header': 'Inprimatzeko txostena',
 'corpus_report_intro': 'Inprimatzeko edo PDF gisa gordetzeko dokumentu bat sortzen du, hautatzen '
                        'dituzun zatiekin. Testuak zenbakiarekin bakarrik agertzen dira (T-001…).',
 'corpus_report_opt_patterns': 'Sartu bilaketa bateko ereduak',
 'corpus_report_run_label': 'Sartu beharreko eredu-bilaketa',
 'corpus_report_opt_readings': 'Sartu lenteekin egindako irakurketa',
 'corpus_report_opt_terms': 'Sartu hitzen zerrenda',
 'corpus_report_opt_passages': 'Sartu pasarteak eta aipu zehatzak (hautatu gabe: zenbaketak eta '
                               'azalpenak bakarrik)',
 'corpus_report_nothing_selected': 'Hautatu txostenaren zati bat gutxienez.',
 'corpus_report_no_run': 'Oraindik ez dago eredu-bilaketarik: ez da eredurik sartuko.',
 'corpus_report_doc_title': 'Testuen azterketaren txostena',
 'corpus_report_how_to_read': 'Txosten honek lehendik idatzita dauden testu-multzo batean zer '
                              'errepikatzen den biltzen du. Ereduak hausnarketarako hautagaiak '
                              'dira, ez ondorioak: gai bat errepikatzeak ez du alborapenik edo '
                              'jardun txarrik frogatzen. Aurkikuntza bakoitzaren indarra beti '
                              '«testuen zenbatetan agertzen den» gisa adierazten da. Taldeak '
                              'erabakitzen du zer esan nahi duen, esan nahi badu.',
 'corpus_report_collection_title': 'Bilduma',
 'corpus_report_collection_line': '«{name}» bilduma: {documents} testu eta {passages} pasarte.',
 'corpus_report_search_title': 'Eredu-bilaketa',
 'corpus_report_search_line': '{date}(e)ko bilaketa: {documents} testu eta {passages} pasarte '
                              'alderatu dira; eredu hautagai {patterns} aurkitu dira.',
 'corpus_report_col_texts': 'Zenbat testutan',
 'corpus_report_col_passages': 'Pasarteak',
 'corpus_report_passages_omitted': 'Pasarteak eta aipuak ez dira txosten honetan sartzen.',
 'corpus_report_readings_title': 'Testu bakoitzaren irakurketa lenteekin',
 'corpus_report_readings_omitted': 'Behaketak eta aipu zehatzak ez dira txosten honetan sartzen; '
                                   'behean, AAk zerbait planteatu duen testuak.',
 'corpus_report_terms_title': 'Hitzen eta esamoldeen zerrenda',
 'corpus_report_col_where': 'Agertzen den testuak',
 'corpus_report_more_texts': '(eta {count} gehiago)',
 'corpus_report_limits_list': ['Testuek ez daramate etiketarik (ez nork idatzi dituen, ez nori '
                               'buruzkoak diren): txosten honek ezin du ezer esan talde '
                               'desberdinak berdin ala desberdin tratatzen diren.',
                               'Ereduen multzokatzea automatikoa da, esanahiaren antzagatik; '
                               'erlazionatu gabeko pasarteak elkartu ditzake edo erlazionatuak '
                               'bereizi.',
                               'Lenteekin egindako irakurketa AAk egiten du, testuz testu: '
                               '«aipatua» ez du neurtzen zerbait zenbatetan gertatzen den, eta '
                               'ezer aipatzen ez duenean horrek ez du esan nahi testua horretatik '
                               'libre dagoenik.',
                               'Hitzen zenbaketak idatzitako hitzak soilik hartzen ditu kontuan: '
                               'ez ditu testuingurua ez sinonimoak ulertzen.',
                               'Bildumako testuak taldeak kargatzea erabaki dituenak dira; ez dira '
                               'nahitaez dokumentazio osoaren adierazgarri.',
                               'Anonimizazio automatikoak baliteke datu pertsonal guztiak ez '
                               'detektatzea: berrikusi txosten hau partekatu aurretik.'],
 'corpus_report_footer': 'Konfidentziala · Hausnarketarako hautagaiak, ez ondorioak · {date}',
 'rs_intro': 'Idatzi, itsatsi edo igo hausnartu nahi duzun kasua eta hausnartu une berean. '
             'Kasuaren testua hausnarketa honetan bakarrik erabiltzen da eta ez da inoiz '
             'gordetzen: hausnarketa da gordetzen dena.',
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
 'rs_case_text_review_label': 'Kasuaren testua (ez da gordetzen)',
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
 'rs_finish_caption': 'Zure hausnarketa eta oharrak {code} kodearekin gordeta geratzen dira. '
                      'Amaitzean, kasuaren testua baztertu egiten da.',
 'rs_finish_caption_unsaved': 'Ezin izan da hausnarketa hau gorde. Amaitzean, kasuaren testua '
                              'baztertu egiten da.',
 'rs_finish_button': 'Amaitu hausnarketa',
 'rs_finished_success': '✔ Hausnarketa amaituta. Kasuaren testua baztertu da.',
 'rs_start_over_button': 'Hasi berriro',
 'ch_reflections_header': 'Gordetako hausnarketak',
 'ch_reflections_intro': 'Hausnarketa bakoitza bere kode neutroarekin eta gaiekin agertzen da. '
                         'IAren behaketak erakusten dira; inoiz ez kasuaren testua (ez da '
                         'gordetzen) ezta profesionalen ohar pribatuak ere.',
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
 'research_observations_label': 'Gordetako behaketak',
 'admin_legacy_docs_header': '🗑️ Ezabatu gordetako dokumentu zaharrak',
 'admin_legacy_docs_none': 'Ez da gordetako dokumentu zaharrik geratzen. Reflection Spacek '
                           'hausnarketak bakarrik gordetzen ditu.',
 'admin_legacy_docs_count': '«Hausnarketak bakarrik» aldaketaren aurretik gordetako {count} '
                            'dokumentu geratzen dira.',
 'admin_legacy_docs_caption': 'Betiko ezabatuko dira: dokumentu zahar guztiak, haien aldaketen '
                              'historia, haietatik sortutako hausnarketak (behaketa eta oharrekin) '
                              'eta haien bilaketa-kopiak. Hausnarketa berriak ez dira ukitzen. '
                              'Ekintza hau ezin da desegin.',
 'admin_legacy_docs_confirm_word': 'EZABATU',
 'admin_legacy_docs_confirm_label': 'Berresteko, idatzi {word}',
 'admin_legacy_docs_button': 'Ezabatu dokumentu zahar guztiak',
 'admin_legacy_docs_done': '✔ {count} dokumentu zahar ezabatu dira.',
 'admin_legacy_docs_refused': 'Sistemaren administratzaileak bakarrik egin dezake hau.',
 'admin_legacy_docs_count_failed': 'Ezin izan da kontsultatu zenbat dokumentu zahar geratzen '
                                   'diren.',
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
                     'legal_administrative': 'Lege- eta administrazio-izapideak'}}
