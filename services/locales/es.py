"""Spanish (Español) UI translation strings for Reflection Space.

Pure data -- no logic. Extracted verbatim from the original single-file
services/language.py (each value copied exactly, no rewording, no key
changes). See services/language.py for the language-selection and
fallback logic that consumes this dictionary.
"""

LANG_ES = {'title': '🧠 Espacio de Reflexión',
 'doc': 'Documentación',
 'case_ref': 'Referencia del caso',
 'doc_type': 'Tipo de documento',
 'doc_types': ['Nota de caso',
               'Diario de seguimiento',
               'Registro de entrevista',
               'Informe social',
               'Propuesta de derivación',
               'Plan de intervención',
               'Correo electrónico'],
 'language': 'Idioma',
 'text': 'Texto',
 'save': 'Guardar borrador',
 'success': '✔ Borrador guardado correctamente',
 'empty': 'Por favor escribe un texto',
 'new': 'Nuevo documento',
 'reflection': 'Espacio de reflexión',
 'home_subtitle': 'Un espacio para la documentación y la reflexión en la práctica.',
 'nav_hint': 'Usa la barra lateral para navegar.',
 'nav_header': 'Navegar:',
 'nav_doc': '📝 Documentación',
 'nav_reflection': '🌿 Espacio de reflexión',
 'nav_learning': '📚 Aprendizaje',
 'no_drafts': 'No hay borradores disponibles.',
 'select_drafts': 'Selecciona borradores para reflexionar',
 'begin_reflection': 'Comenzar reflexión',
 'reflection_folders_intro': 'Documentos pendientes de reflexión, agrupados por caso.',
 'reflection_same_day_notice': '⚠️ Este caso tiene más de un documento del mismo día.',
 'reflection_no_case_ref': '(Sin referencia de caso)',
 'reflection_active_case_prefix': 'Reflexionando sobre el caso:',
 'reflection_delete_button': 'Eliminar documento',
 'reflection_delete_confirm': '¿Confirmas que quieres eliminar este documento? Esta acción no se '
                              'puede deshacer.',
 'reflection_deleted_success': '✔ Documento eliminado.',
 'reflection_context_title': 'Contexto de la reflexión',
 'reflection_context_current_label': 'Documento(s) seleccionado(s):',
 'reflection_context_historical_label': 'Documentos históricos relevantes de este caso:',
 'reflection_context_summary_strong': 'Esta reflexión utiliza la documentación de hoy junto con '
                                      '{count} documentos históricos relevantes.',
 'reflection_context_summary_limited': 'Esta reflexión utiliza principalmente la documentación de '
                                       'hoy, ya que se encontró información histórica limitada '
                                       'relevante.',
 'reflection_context_summary_none': 'Esta parece ser la primera interacción documentada para este '
                                    'caso.',
 'reflection_context_continue': 'Continuar a la reflexión',
 'reflection_context_back': 'Volver a la selección',
 'reflection_partial_failure_notice': 'Algunas perspectivas de reflexión no se pudieron generar '
                                      '({count}). La reflexión se ha producido de todas formas. '
                                      'Esto ha quedado registrado para revisión. Puede continuar '
                                      'con lo disponible o intentarlo de nuevo.',
 'unknown_label': 'Desconocido/a',
 'audit_unknown_case_label': '(caso desconocido)',
 'case_history_completed_label': 'completado',
 'learning_phase2': 'Temas reflexivos que emergen en las reflexiones generadas en la aplicación.',
 'learning_no_data': 'Aún no hay reflexiones registradas. Los temas aparecerán aquí a medida que '
                     'se generen reflexiones.',
 'themes': ['Voz de la persona',
            'Hechos vs. Interpretación',
            'Etiquetas y lenguaje',
            'Posibles sesgos',
            'Evidencia de las decisiones',
            'Información ausente',
            'Fortalezas vs. Déficits',
            'Continuidad'],
 'section_labels': {'client_voice': 'Voz de la persona',
                    'observation_vs_interpretation': 'Hechos vs. Interpretación',
                    'labels_and_language': 'Etiquetas y lenguaje',
                    'possible_bias': 'Posibles sesgos',
                    'evidence_for_decisions': 'Evidencia de las decisiones',
                    'missing_information': 'Información ausente',
                    'strengths_and_deficits': 'Fortalezas vs. Déficits',
                    'continuity': 'Continuidad'},
 'update_document': 'Actualizar documento',
 'edit_document_label': 'Edita el documento aquí si lo deseas',
 'submit_no_edit': 'Enviar sin editar',
 'submit_with_edit': 'Enviar con los cambios',
 'submitted': '✔ Documento enviado',
 'error_parsing': '⚠ No se pudo procesar la respuesta de la reflexión. Inténtalo de nuevo.',
 'submit_draft_failed': '⚠ No se pudo enviar el documento. Inténtalo de nuevo.',
 'delete_draft_failed': '⚠ No se pudo eliminar el documento. Inténtalo de nuevo.',
 'login_heading': '🔒 Espacio de Reflexión',
 'username': 'Usuario',
 'password_label': 'Contraseña',
 'login_button': 'Iniciar sesión',
 'login_error': 'Usuario o contraseña incorrectos.',
 'login_locked': 'Demasiados intentos fallidos. Por favor, espera {minutes} minuto(s) antes de '
                 'volver a intentarlo.',
 'no_users_configured': 'Aún no hay cuentas de usuario configuradas. Añádelas en Configuración → '
                        'Secretos en Streamlit Cloud.',
 'logout': 'Cerrar sesión',
 'role_labels': {'Social Worker': 'Trabajador/a Social',
                 'Supervisor': 'Supervisor/a',
                 'Programme Manager': 'Gestor/a de Programa',
                 'System Administrator': 'Administrador/a del Sistema'},
 'admin_title': '🔒 Administración',
 'admin_password_label': 'Contraseña',
 'admin_enter_button': 'Entrar',
 'admin_incorrect_password': 'Contraseña incorrecta.',
 'admin_visit_log': 'Registro de visitas',
 'admin_no_visits': 'Aún no hay visitas registradas.',
 'admin_total_views_label': 'vistas totales',
 'admin_clear_log': 'Borrar registro',
 'admin_backfill_header': '🔄 Reindexar documentos en Qdrant',
 'admin_backfill_caption': 'Genera embeddings semánticos para los documentos completados ANTES de '
                           'activar la recuperación semántica (Hybrid RAG). Seguro de ejecutar '
                           'varias veces: cada documento se sobrescribe por su id, nunca se '
                           'duplica. PostgreSQL no se modifica.',
 'admin_backfill_button': 'Reindexar todos los documentos completados',
 'admin_backfill_running': 'Indexando documento {current} de {total}...',
 'admin_backfill_done': '✔ Reindexación completa: {indexed} de {total} documentos indexados en '
                        'Qdrant.',
 'admin_backfill_unavailable': 'La recuperación semántica no está configurada todavía (falta '
                               'GEMINI_API_KEY o QDRANT_URL en los secretos). El resto de la '
                               'aplicación sigue funcionando con el contexto histórico por fecha.',
 'admin_anon_header': 'Demostración de anonimización',
 'admin_anon_caption': 'Pega cualquier texto de muestra (solo datos ficticios) para ver qué sale '
                       'del sistema antes de llegar a Claude. Ejecuta la misma función anonymize() '
                       'utilizada en reflection_service.py.',
 'admin_sample_label': 'Texto de muestra (solo datos ficticios)',
 'admin_run_button': 'Ejecutar anonimizador',
 'admin_output_label': 'Salida anonimizada (lo que se envía a Claude):',
 'nav_case_history': '🗂️ Historial de casos',
 'case_history_title': 'Historial de casos',
 'case_history_no_items': 'Aún no hay reflexiones completadas.',
 'case_history_original_label': 'Versión original',
 'case_history_current_label': 'Versión actual',
 'case_history_edited_label': 'Editado',
 'case_history_not_edited_label': 'No editado',
 'case_history_view_original_button': 'Ver versión original',
 'case_history_all_dates': 'Todas las fechas',
 'submit_draft': 'Enviar',
 'admin_table_page': 'Página',
 'admin_table_language': 'Idioma',
 'admin_table_visited': 'Visitado el',
 'admin_sample_default': 'El 15/02/2026 la clienta, Sarah Kimani, con número de identificación '
                         '9988776655, asistió a una reunión de seguimiento. Se le puede contactar '
                         'en +254 722 334 455 o sarah.kimani@testmail.com. El Sr. David Otieno fue '
                         'el trabajador social asignado.',
 'learning_preview_caption': 'Basado en las últimas {total} reflexiones registradas',
 'learning_flagged_caption': 'Detectado en {count} de las últimas {total} reflexiones',
 'case_history_date_filter_label': 'Ver historial de:',
 'case_history_toggle_label': 'Mostrar:',
 'case_history_edited_option': 'Editados',
 'case_history_not_edited_option': 'No editados',
 'case_history_no_items_for_filter': 'No hay documentos para esta selección.',
 'case_history_showing_recent': 'Mostrando los {shown} documentos más recientes de {total}. Usa el '
                                'filtro de fecha para ver documentos anteriores.',
 'feedback_showing_recent': 'Mostrando los {shown} comentarios más recientes de {total}.',
 'feedback_prompt_title': '¿Qué tan útil fue esta reflexión?',
 'feedback_rating_label': 'Valoración (1 = poco útil, 5 = muy útil)',
 'feedback_comment_label': 'Comentario (opcional)',
 'feedback_submit_button': 'Enviar valoración',
 'feedback_skip_button': 'Omitir',
 'feedback_thanks': '✔ Gracias por tu valoración',
 'feedback_section_header': 'Comentarios de los profesionales',
 'feedback_average_label': 'Valoración media',
 'feedback_no_items': 'Aún no hay comentarios.',
 'case_history_delete_button': 'Eliminar caso',
 'case_history_delete_confirm': '¿Confirmas que quieres eliminar este caso? Podrás restaurarlo '
                                'durante 48 horas.',
 'case_history_delete_yes': 'Sí, eliminar',
 'case_history_delete_cancel': 'Cancelar',
 'case_history_deleted_success': '✔ Caso eliminado. Podrás restaurarlo durante 48 horas.',
 'case_history_pending_deletion_header': 'Eliminados recientemente',
 'case_history_pending_deletion_no_items': 'No hay casos eliminados pendientes.',
 'case_history_restore_button': 'Restaurar',
 'case_history_restored_success': '✔ Caso restaurado.',
 'case_history_deleted_by_label': 'Eliminado por',
 'nav_audit_log': '🧾 Registro de auditoría',
 'audit_log_title': 'Registro de auditoría',
 'audit_log_no_items': 'Aún no hay registros de auditoría.',
 'audit_action_created': 'Creado',
 'audit_action_submitted': 'Enviado',
 'audit_action_deleted': 'Eliminado',
 'audit_action_restored': 'Restaurado',
 'audit_action_purged': 'Purgado permanentemente',
 'workspace_opportunities_header': 'Oportunidades de reflexión',
 'workspace_document_header': 'Documento actual',
 'workspace_context_header': 'Contexto de la reflexión',
 'workspace_progress_label': 'Explorado(s): {explored} de {total}',
 'workspace_explore_button': 'Explorar',
 'workspace_close_button': 'Cerrar',
 'workspace_explored_badge': '🗨️ Explorado',
 'workspace_conversation_input_label': 'Tu reflexión',
 'workspace_conversation_placeholder': 'Escribe tu respuesta o pregunta aquí...',
 'workspace_send_button': 'Enviar',
 'workspace_ai_thinking': 'Pensando...',
 'workspace_conversation_error': '⚠ No se pudo continuar la conversación. Inténtalo de nuevo.',
 'workspace_reminder': 'Esto es solo una invitación a reflexionar. Explorarlo, y decidir si '
                       'cambiar algo en la documentación, depende por completo de tu criterio '
                       'profesional.',
 'nav_growth': '🌱 Mi Reflexión',
 'growth_title': '🌱 Tu Trayectoria Reflexiva',
 'growth_intro': 'Este es tu espacio personal. Muestra únicamente lo que tú has explorado — no es '
                 'una evaluación de tu desempeño, no se compara con otros profesionales y no es '
                 'visible para supervisores.',
 'growth_no_data': 'Aún no has explorado ninguna reflexión. A medida que uses el botón «Explorar» '
                   'en el Espacio de Reflexión, tu trayectoria aparecerá aquí.',
 'growth_themes_header': 'Áreas que más has explorado',
 'growth_themes_caption': 'Basado en {total} momento(s) de exploración registrados',
 'growth_history_header': 'Momentos reflexivos recientes',
 'growth_entry_line': '**{theme}** — caso {case} — {count} intercambio(s) — {date}',
 'growth_session_count_label': 'Momentos de exploración registrados en total',
 'nav_team_learning': '🌍 Aprendizaje del Equipo',
 'team_learning_title': '🌍 Temas Reflexivos del Equipo',
 'team_learning_intro': 'Esta vista muestra patrones agregados y anónimos de toda la organización. '
                        'No identifica a ningún profesional, no identifica ningún caso concreto y '
                        'no muestra el historial de reflexión de nadie en particular. Su propósito '
                        'es ayudar a la organización a identificar qué áreas de la práctica '
                        'merecen atención colectiva — no evaluar a las personas.',
 'team_learning_period_caption': 'Últimos 6 meses — {total} momento(s) de exploración registrados '
                                 'en total, de todos los equipos',
 'team_learning_no_data': 'Aún no hay suficientes datos de exploración registrados en los últimos '
                          '6 meses.',
 'team_learning_header': 'Áreas reflexivas más comunes',
 'team_learning_rank_line': '{rank}. {theme} — {count} exploraciones',
 'nav_research_metrics': '📊 Métricas de Investigación',
 'research_title': '📊 Métricas de Investigación',
 'research_intro': 'Estas métricas describen la actividad reflexiva de la organización — no '
                   'evalúan ni comparan a ningún profesional. No contienen nombres, casos '
                   'concretos ni contenido de documentos.',
 'research_period_caption': 'Periodo: últimos {days} días (desde {since})',
 'research_overview_header': 'Resumen de actividad',
 'research_sessions_label': 'Sesiones de reflexión generadas',
 'research_documents_label': 'Documentos completados',
 'research_theme_table_header': 'Temas: señalados por la IA vs. explorados por profesionales',
 'research_theme_flagged_col': 'Señalado por la IA',
 'research_theme_explored_col': 'Explorado por un profesional',
 'research_feedback_header': 'Valoraciones de utilidad',
 'research_feedback_count_label': 'Valoraciones recibidas',
 'research_feedback_average_label': 'Valoración media',
 'research_feedback_comments_label': 'Con comentario',
 'research_feedback_no_data': 'Aún no se han recibido valoraciones.',
 'research_export_button': 'Descargar CSV para investigación',
 'research_export_caption': 'El archivo contiene únicamente recuentos agregados — sin nombres, sin '
                            'casos, sin texto de documentos.',
 'research_no_data': 'Aún no hay suficiente actividad registrada para este periodo.',
 'why_included_label': '¿Por qué se incluyó este documento?',
 'why_reason_must_include_plan': 'Este es el Plan de Intervención más reciente y aporta contexto '
                                 'importante para la reflexión de hoy.',
 'why_reason_must_include_assessment': 'Este es el informe social más reciente disponible para '
                                       'este caso.',
 'why_reason_must_include_generic': 'Este es uno de los documentos clave de este caso.',
 'why_reason_semantic_specific': 'Este documento trata sobre {themes}, temas que también aparecen '
                                 'en la documentación de hoy.',
 'why_reason_semantic_generic': 'Este documento trata temas estrechamente relacionados con la '
                                'documentación de hoy.',
 'why_reason_recency': 'Este documento se creó recientemente y puede contener novedades '
                       'importantes para la reflexión de hoy.',
 'why_technical_details_label': 'Detalles técnicos',
 'why_similarity_label': 'Similitud:',
 'why_similarity_very_high': 'Muy alta',
 'why_similarity_high': 'Alta',
 'why_similarity_moderate': 'Moderada',
 'why_similarity_low': 'Baja',
 'journey_step1': 'Documentación de Hoy',
 'journey_step2': 'Contexto Histórico',
 'journey_step3': 'Reflexión Profesional',
 'journey_step4': 'Preguntas Reflexivas',
 'journey_step1_desc': 'Se seleccionan los documentos de hoy para la reflexión.',
 'journey_step2_desc': 'Se recuperan documentos históricos relevantes de este caso.',
 'journey_step3_desc': 'La IA analiza la documentación de hoy junto con el contexto histórico.',
 'journey_step4_desc': 'Se te invita a considerar preguntas reflexivas.',
 'historical_timeline_header': 'Línea temporal histórica',
 'historical_timeline_intro': 'Documentos relevantes de este caso, ordenados cronológicamente.',
 'timeline_today_label': '📍 Documentación de hoy',
 'historical_docs_used_label': 'Documentos históricos incluidos actualmente',
 'dashboard_navigator_hint': 'Usa las pestañas para moverte entre las áreas de reflexión sin '
                             'desplazarte por toda la página.',
 'coverage_header': 'Cobertura de la reflexión',
 'coverage_intro': 'Esto confirma que cada dimensión fue considerada en esta reflexión — no es una '
                   'puntuación ni una evaluación.',
 'coverage_considered': 'Analizada',
 'coverage_unavailable': 'No se pudo generar esta vez',
 'history_link_hint': '¿Quieres revisar tus reflexiones anteriores? Tu trayectoria reflexiva '
                      'personal está disponible en',
 'workmode_switch_label': 'Modo de trabajo',
 'workmode_practitioner': 'Práctica',
 'workmode_manager': 'Gestión / Supervisión',
 'workmode_admin': 'Administración del Sistema',
 'workmode_access_denied': 'No tienes acceso a este espacio de trabajo.',
 'nav_system_admin': '🛠️ Administración del Sistema',
 'presence_header': 'Presencia del Equipo',
 'presence_intro': 'Trabajadores/as sociales actualmente activos en la aplicación. No se muestra '
                   'información de casos ni contenido de documentos.',
 'presence_active_count': '{count} trabajador(es) social(es) activo(s) o recientemente activo(s)',
 'presence_status_active': '🟢 Activo/a ahora',
 'presence_status_recent': '🟡 Activo/a hace {minutes} minuto(s)',
 'presence_status_offline': '⚪ Sin actividad reciente',
 'presence_no_data': 'Aún no hay datos de actividad registrados.',
 'learning_tab_presence': '👥 Presencia del Equipo',
 'learning_tab_knowledge': '💬 Aprendizaje Organizacional',
 'learning_tab_insights': '📚 Perspectivas de Aprendizaje',
 'learning_tab_team': '🌍 Aprendizaje del Equipo',
 'ka_header': 'Pregunta sobre el conocimiento organizacional',
 'ka_intro': 'Haz una pregunta en lenguaje natural sobre los patrones, temas y actividad reflexiva '
             'de la organización. Las respuestas se basan únicamente en la documentación y '
             'reflexiones indexadas — nunca en conocimiento general externo.',
 'ka_question_label': 'Tu pregunta',
 'ka_question_placeholder': 'Por ejemplo: ¿Qué patrones han surgido en Kulunka este trimestre?',
 'ka_ask_button': 'Preguntar',
 'ka_thinking': 'Analizando la base de conocimiento organizacional...',
 'ka_error': '⚠ No se pudo generar una respuesta. Inténtalo de nuevo.',
 'ka_empty_question': 'Por favor escribe una pregunta.',
 'ka_duplicate_message': 'Esta pregunta ya se está procesando. Espera un momento a que termine '
                         'antes de volver a preguntar.',
 'ka_rate_limit_exceeded_message': 'Has alcanzado el límite de {max} preguntas al Asistente de '
                                   'Conocimiento en la última hora en esta cuenta. Este es un '
                                   'límite de seguridad para prevenir solicitudes repetidas '
                                   'accidentales, no una restricción de tu trabajo habitual -- '
                                   'espera un poco e inténtalo de nuevo, o contacta con tu '
                                   'Administrador del Sistema si crees que esto es un error.',
 'ka_confidence_label': 'Nivel de evidencia:',
 'ka_confidence_strong': '🟢 Evidencia sólida',
 'ka_confidence_limited': '🟡 Evidencia limitada',
 'ka_confidence_insufficient': '🔴 Evidencia insuficiente',
 'ka_limitations_label': 'Limitaciones:',
 'ka_evidence_header': 'Evidencia utilizada',
 'ka_evidence_count': '{count} documento(s) relevante(s) recuperado(s)',
 'ka_evidence_doc_type_col': 'Tipo de documento',
 'ka_evidence_date_col': 'Fecha',
 'ka_evidence_case_col': 'Referencia de caso/servicio',
 'ka_evidence_relevance_col': 'Relevancia',
 'ka_evidence_none': 'No se recuperó ningún documento relevante para esta pregunta.',
 'admin_user_mgmt_header': '👥 Gestión de usuarios',
 'admin_user_mgmt_info': 'Los usuarios se gestionan mediante los Secretos de Streamlit. La gestión '
                         'dinámica no está disponible intencionadamente: las credenciales y roles '
                         'se configuran en los secretos de despliegue, no en tablas de la '
                         'aplicación.',
 'admin_user_mgmt_empty': 'Aún no hay usuarios configurados. Añádelos en Configuración → Secretos '
                          'en Streamlit Cloud.',
 'admin_user_col_username': 'Usuario',
 'admin_user_col_name': 'Nombre',
 'admin_user_col_role': 'Rol',
 'admin_doc_indexing_header': '📇 Indexación de documentos',
 'admin_doc_indexing_caption': 'Utilidad de reindexado del Hybrid RAG — genera embeddings de '
                               'Qdrant para los documentos completados antes de activar la '
                               'recuperación semántica.',
 'admin_doc_indexing_cost': '💰 Nota de coste: esto llama a Gemini API (embeddings) una vez por '
                            'documento completado, nunca a Claude.',
 'admin_doc_indexing_unavailable': 'Qdrant no está configurado, por lo que la indexación semántica '
                                   'no está disponible.',
 'admin_doc_indexing_button': 'Ejecutar reindexado de documentos',
 'admin_doc_indexing_success': '✅ Indexados {indexed} de {total} documentos.',
 'admin_doc_indexing_none_failed': '✅ No hay documentos pendientes de indexar. Todo está al día.',
 'admin_doc_indexing_failed_label': '⚠️ {failed} documento(s) se guardaron correctamente pero no '
                                    'se indexaron para la búsqueda.',
 'admin_doc_indexing_failed_caption': 'Estos documentos están completos y visibles con normalidad '
                                      'en toda la aplicación — solo falló el paso que los hace '
                                      'localizables en el Asistente de Conocimiento y en el '
                                      'histórico de casos de Contexto de Reflexión. Ningún dato se '
                                      'ha perdido; basta con reintentar la indexación.',
 'admin_doc_indexing_retry_button': 'Reintentar solo los documentos fallidos',
 'admin_doc_indexing_retry_success': '✅ Reintento completado: {indexed} de {total} documentos '
                                     'indexados correctamente.',
 'admin_retrieval_test_header': '🔍 Prueba de recuperación',
 'admin_retrieval_test_caption': 'Ejecuta una búsqueda semántica real en Qdrant para verificar que '
                                 'la recuperación funciona de extremo a extremo — con alcance a un '
                                 'caso o a toda la base de conocimiento.',
 'admin_retrieval_test_cost': '💰 Nota de coste: esto solo genera el embedding de tu texto de '
                              'búsqueda vía Gemini API — nunca llama a la API de Claude/Anthropic.',
 'admin_retrieval_case_label': 'Referencia de caso (opcional — déjalo en blanco para buscar en '
                               'toda la base de conocimiento)',
 'admin_retrieval_query_label': 'Consulta de búsqueda',
 'admin_retrieval_run_button': 'Ejecutar prueba de recuperación',
 'admin_retrieval_summary_header': '#### Resumen de la recuperación',
 'admin_retrieval_mode_global': '🌍 Búsqueda global en la base de conocimiento',
 'admin_retrieval_mode_case': '📁 Específico del caso ({case_ref})',
 'admin_retrieval_status_label': 'Estado',
 'admin_retrieval_status_success': '✅ Correcto',
 'admin_retrieval_status_failed': '❌ Fallido',
 'admin_retrieval_mode_row_label': 'Modo de recuperación',
 'admin_retrieval_time_label': 'Tiempo de búsqueda',
 'admin_retrieval_query_row_label': 'Consulta',
 'admin_retrieval_docs_returned_label': 'Documentos devueltos',
 'admin_retrieval_embedding_model_label': 'Modelo de embeddings',
 'admin_retrieval_global_notice': '🌍 Modo global: esta búsqueda no aplicó filtro de caso y puede '
                                  'devolver documentos de más de un caso.',
 'admin_retrieval_failed_label': 'La recuperación falló:',
 'admin_retrieval_documents_header': '#### Documentos recuperados',
 'admin_retrieval_no_docs': 'No se devolvieron documentos para esta consulta.',
 'admin_retrieval_col_rank': 'Posición',
 'admin_retrieval_col_doctype': 'Tipo de documento',
 'admin_retrieval_col_reason': 'Motivo de recuperación',
 'admin_retrieval_col_similarity': 'Similitud',
 'admin_retrieval_col_case': 'Referencia de caso',
 'admin_advanced_diagnostics': '🔧 Diagnóstico avanzado',
 'admin_show_raw_response': 'Mostrar respuesta sin procesar',
 'admin_rag_status_header': '📡 Estado del RAG',
 'admin_rag_status_ok': '✅ La capa de recuperación semántica es accesible.',
 'admin_rag_status_item': 'Elemento',
 'admin_rag_status_value': 'Estado',
 'admin_rag_qdrant_connection': 'Conexión con Qdrant',
 'admin_rag_collection': 'Colección',
 'admin_rag_embedding_model': 'Modelo de embeddings',
 'admin_rag_embedding_dims': 'Dimensiones de embeddings',
 'admin_rag_indexed_docs': 'Documentos indexados',
 'admin_rag_case_ref_index': 'Índice de referencia de caso',
 'admin_rag_doc_id_index': 'Índice de ID de documento',
 'admin_rag_latest_doc_id': 'Último ID de documento',
 'admin_rag_latest_case': 'Último caso',
 'admin_rag_latest_doctype': 'Último tipo de documento',
 'admin_rag_last_indexed': 'Última indexación',
 'admin_status_connected': 'Conectado',
 'admin_status_not_connected': 'No conectado',
 'admin_status_present': '✅ Presente',
 'admin_status_missing': '❌ Ausente',
 'admin_health_header': '💚 Estado del sistema',
 'admin_health_overall': '#### Estado general',
 'admin_health_critical': '🔴 Crítico',
 'admin_health_degraded': '🟡 Degradado (la recuperación semántica no está configurada — la '
                          'aplicación usa el modo alternativo por fecha)',
 'admin_health_healthy': '🟢 Saludable',
 'admin_health_components': '#### Componentes',
 'admin_health_component_col': 'Componente',
 'admin_health_status_col': 'Estado',
 'admin_health_component_database': 'Base de datos',
 'admin_health_component_qdrant': 'Qdrant',
 'admin_health_component_embedding': 'Servicio de embeddings (Gemini API)',
 'admin_health_component_retrieval': 'Servicio de recuperación',
 'admin_health_component_reflection': 'Motor de reflexión (API de Claude)',
 'admin_health_healthy_label': 'Saludable',
 'admin_health_unreachable_label': 'No accesible',
 'admin_health_available_label': 'Disponible',
 'admin_health_not_configured_label': 'No configurado',
 'admin_health_operational_label': '✅ Operativo',
 'admin_health_fallback_label': '🟡 Modo alternativo (basado en fecha)',
 'admin_health_db_error_prefix': 'Error de base de datos:',
 'admin_health_key_missing': 'ANTHROPIC_API_KEY no está configurado — no se pueden generar '
                             'reflexiones.',
 'admin_config_header': '⚙️ Configuración',
 'admin_tools_header': '🧰 Herramientas administrativas',
 'admin_tools_anon_test_header': 'Prueba de anonimización',
 'admin_tools_reset_index_header': 'Reiniciar el índice de búsqueda (Qdrant)',
 'admin_tools_reset_index_caption': 'Elimina y vuelve a crear el índice de búsqueda semántica '
                                    'desde cero, usando el proveedor de embeddings configurado '
                                    'actualmente. Úsalo después de cambiar de proveedor de '
                                    'embeddings (por ejemplo, de Voyage a Gemini) para que los '
                                    'datos antiguos e incompatibles no interfieran con las '
                                    'búsquedas nuevas.',
 'admin_tools_reset_index_warning': '⚠️ Esta acción eliminará permanentemente todos los vectores '
                                    'de búsqueda existentes en Qdrant. Los documentos en sí NO se '
                                    'pierden -- siguen intactos en la base de datos -- pero '
                                    'dejarán de aparecer en las búsquedas del Asistente de '
                                    'Conocimiento o en el Contexto de Reflexión hasta que se '
                                    'vuelvan a indexar. ¿Confirmas que quieres continuar?',
 'admin_tools_reset_index_button': 'Reiniciar índice de búsqueda',
 'admin_tools_reset_index_yes': 'Sí, reiniciar',
 'admin_tools_reset_index_cancel': 'Cancelar',
 'admin_tools_reset_index_success': 'El índice de búsqueda se ha reiniciado correctamente. Ya está '
                                    'vacío y listo para indexar documentos nuevos con el proveedor '
                                    'de embeddings actual.',
 'admin_tools_reset_index_failed': 'No se pudo reiniciar el índice de búsqueda:',
 'admin_tools_reset_index_unavailable': 'Qdrant no está configurado -- no hay ningún índice que '
                                        'reiniciar.',
 'admin_tools_future': 'Las futuras herramientas de administración aparecerán aquí.',
 'admin_console_caption': 'Consola de administración de Reflection Space -- estado del sistema, '
                          'indexación y herramientas de diagnóstico.',
 'admin_error_log_unknown_page': 'página desconocida',
 'admin_error_log_generic_error': 'Error',
 'admin_error_log_no_message': '(sin mensaje)',
 'admin_error_log_unknown_role': 'rol desconocido',
 'readiness_category_exception': 'Excepción',
 'readiness_category_traceback_evidence': 'Traceback',
 'readiness_category_root_cause': 'Causa raíz',
 'readiness_category_timeline': 'Línea temporal',
 'readiness_category_session_context': 'Contexto de la sesión',
 'readiness_category_environment': 'Entorno',
 'readiness_category_user_information': 'Información del usuario',
 'readiness_category_configuration': 'Configuración',
 'readiness_category_ai_prompt': 'Prompt de IA generado',
 'event_labels': {'Opened page': 'Página abierta',
                  'Changed page': 'Página cambiada',
                  'Email sent': 'Correo enviado',
                  'User submitted report': 'Informe enviado por el usuario',
                  'Exception occurred': 'Se produjo una excepción',
                  'Error logged': 'Error registrado'},
 'admin_case_export_download': 'Descargar caso #{n}',
 'admin_case_export_failed': 'No se pudo generar la exportación.',
 'admin_case_export_format': 'Formato',
 'admin_case_export_header': '📤 Exportar este caso',
 'admin_case_field_common_cause': 'Causa común',
 'admin_case_field_deployment_date': 'Fecha de despliegue (si aplica)',
 'admin_case_field_documentation_link': 'Enlace a documentación',
 'admin_case_field_external_reference': 'Referencia externa',
 'admin_case_field_fix_applied': 'Corrección aplicada',
 'admin_case_field_git_commit': 'Commit de Git',
 'admin_case_field_known_fix': 'Solución conocida',
 'admin_case_field_known_workaround': 'Solución temporal conocida',
 'admin_case_field_lessons_learned': 'Lecciones aprendidas',
 'admin_case_field_prevention_notes': 'Notas de prevención futura',
 'admin_case_field_resolution_summary': 'Resumen de la resolución',
 'admin_case_field_root_cause': 'Causa raíz (conclusión del administrador)',
 'admin_case_field_version_fixed': 'Versión corregida',
 'admin_case_investigation_add': 'Guardar una nueva investigación',
 'admin_case_investigation_by': 'Añadido por',
 'admin_case_investigation_delete': '🗑️ Eliminar esta entrada',
 'admin_case_investigation_notes': 'Notas del administrador',
 'admin_case_investigation_notes_input': 'Notas del administrador',
 'admin_case_investigation_prompt': 'Prompt',
 'admin_case_investigation_prompt_input': 'Prompt',
 'admin_case_investigation_response': 'Respuesta de la IA',
 'admin_case_investigation_response_input': 'Respuesta de la IA',
 'admin_case_investigation_save': '💾 Guardar investigación',
 'admin_case_investigation_save_failed': 'No se pudo guardar -- inténtalo de nuevo.',
 'admin_case_investigation_saved': 'Investigación guardada.',
 'admin_case_investigation_tool': 'Herramienta utilizada',
 'admin_case_investigations_caption': 'Reflection Space nunca llama a una IA automáticamente aquí '
                                      '-- esto es simplemente un lugar para guardar '
                                      'investigaciones que ya has hecho en otro sitio (ChatGPT, '
                                      'Claude, Gemini, o una investigación manual), para que la '
                                      'siguiente persona no tenga que repetir el trabajo.',
 'admin_case_investigations_empty': 'Aún no hay investigaciones guardadas.',
 'admin_case_investigations_header': '🧠 Historial de Investigación IA',
 'admin_case_knowledge_no_issue_id': 'Este registro es anterior a las referencias de incidencia '
                                     'estables, por lo que el conocimiento del caso (seguimiento '
                                     'de resolución, historial de investigación IA, incidencias '
                                     'similares, exportación) no está disponible para él.',
 'admin_case_knowledge_subheader': 'Conocimiento del caso (todo opcional)',
 'admin_case_resolution_header': '✅ Resolución y Conocimiento del Caso',
 'admin_case_resolution_history_caption': 'Esta incidencia se marcó anteriormente como Corregida o '
                                          'Cerrada y desde entonces ha reaparecido. La resolución '
                                          'registrada antes de cada reaparición se conserva abajo, '
                                          'aunque el formulario de arriba ahora refleja la '
                                          'investigación actual.',
 'admin_case_resolution_history_header': '📜 Historial de resoluciones anteriores ({n} guardadas)',
 'admin_case_resolution_history_occurrence': 'ocurrencia',
 'admin_case_resolution_history_reopened_at': 'Reabierto el',
 'admin_case_resolution_last_updated': 'Última actualización {when} por {who}',
 'admin_case_resolution_save': '💾 Guardar resolución y conocimiento del caso',
 'admin_case_resolution_save_failed': 'No se pudo guardar -- inténtalo de nuevo.',
 'admin_case_resolution_saved': 'Guardado.',
 'admin_case_search_ai_tool': 'Herramienta de IA utilizada',
 'admin_case_search_button': 'Buscar',
 'admin_case_search_caption': 'Busca casos resueltos y sin resolver por lo que sabes de ellos, no '
                              'solo por cuándo ocurrieron. Rellena cualquier combinación de campos '
                              '-- los resultados coinciden con TODOS los campos que proporciones.',
 'admin_case_search_exception': 'Tipo de excepción',
 'admin_case_search_find_hint': 'Abre el caso correspondiente arriba en la AI Diagnostic Centre '
                                '(por su referencia #) para ver el registro completo.',
 'admin_case_search_header': '🔎 Búsqueda de Conocimiento de Casos',
 'admin_case_search_lesson': 'La lección aprendida contiene',
 'admin_case_search_min_occurrences': 'Número mínimo de ocurrencias',
 'admin_case_search_no_results': 'Ningún caso coincide con esos filtros. Prueba con menos campos.',
 'admin_case_search_page': 'Página',
 'admin_case_search_resolution': 'La resolución contiene',
 'admin_case_search_resolution_label': 'Resolución',
 'admin_case_search_result_count': '{n} caso(s) encontrado(s).',
 'admin_case_search_root_cause': 'La causa raíz contiene',
 'admin_case_search_root_cause_label': 'Causa raíz',
 'admin_case_search_status': 'Estado',
 'admin_case_search_user': 'Usuario',
 'admin_case_search_version_fixed': 'Versión corregida',
 'admin_case_similar_empty': 'No se encontraron incidencias previas similares.',
 'admin_case_similar_header': 'Incidencias Previas Similares',
 'admin_error_log_caption': 'Todos los problemas registrados en la aplicación -- fallos, llamadas '
                            'fallidas de la IA acompañante, o problemas reportados por las '
                            'personas usuarias -- mostrados como un espacio de diagnóstico '
                            'completo: qué ocurrió, qué gravedad tiene, y un prompt ya preparado '
                            'que puedes copiar directamente en una conversación con Claude para '
                            'diagnosticarlo y solucionarlo.',
 'admin_error_log_category_label': 'Categoría',
 'admin_error_log_context_label': 'Contexto',
 'admin_error_log_copy_hint': 'Pasa el cursor sobre el cuadro de abajo y haz clic en el icono de '
                              'copiar en la esquina superior derecha.',
 'admin_error_log_count_caption': 'Mostrando {n} de {total} incidencia(s).',
 'admin_error_log_empty': 'No hay errores registrados. Todo está en orden.',
 'admin_error_log_env_app_version': 'Versión de la aplicación',
 'admin_error_log_env_browser': 'Navegador',
 'admin_error_log_env_os': 'Sistema operativo',
 'admin_error_log_env_python': 'Versión de Python',
 'admin_error_log_environment_label': '💻 Entorno',
 'admin_error_log_evidence_label': '📋 Evidencia Recopilada',
 'admin_error_log_exception_message_label': 'Mensaje de excepción',
 'admin_error_log_exception_type_label': 'Tipo de excepción',
 'admin_error_log_explanation_label': '🗣️ Qué ocurrió, en lenguaje sencillo',
 'admin_error_log_first_seen_label': 'Visto por primera vez',
 'admin_error_log_header': '🩺 Centro de Diagnóstico IA',
 'admin_error_log_last_seen_label': 'Visto por última vez',
 'admin_translation_health_header': '🌐 Estado del sistema de traducción',
 'admin_translation_health_caption': 'Estado en vivo del sistema de traducción Español / Euskera / '
                                     'English.',
 'admin_translation_autofilled_warning': '{count} clave(s) de traducción se han rellenado '
                                         'automáticamente con texto provisional al iniciar.',
 'admin_translation_autofilled_details': 'Ver claves rellenadas automáticamente',
 'admin_translation_copied_from': 'copiado de',
 'admin_translation_in_sync': 'Los tres idiomas están sincronizados. No fue necesario rellenar '
                              'nada.',
 'admin_translation_runtime_gaps': '⚠️ Claves que faltaron en tiempo de ejecución esta sesión '
                                   '({count})',
 'admin_translation_panel_error': 'No se ha podido cargar el panel de estado de traducción en este '
                                  'momento.',
 'admin_error_log_no_matches': 'Ningún error coincide con los filtros actuales.',
 'admin_error_log_no_package': 'No se generó ningún Paquete de Diagnóstico IA para este registro '
                               '-- se registró antes de que existiera el Motor de Diagnóstico. Los '
                               'detalles técnicos siguen disponibles abajo.',
 'admin_error_log_no_traceback': 'Sin traceback -- esto fue un informe enviado por una persona '
                                 'usuaria, no una excepción automática.',
 'admin_error_log_not_available': 'no disponible',
 'admin_error_log_occurrences_label': 'Ocurrencias',
 'admin_error_log_page_label': 'Página',
 'admin_error_log_prompt_label': '🤖 Prompt IA',
 'admin_error_log_readiness_explainer': 'La puntuación de Preparación IA no está generada por IA '
                                        '-- es un simple recuento de cuántas de las 7 categorías '
                                        'de evidencia siguientes están presentes para este '
                                        'registro.',
 'admin_error_log_readiness_label': 'Preparación IA',
 'admin_error_log_screenshot_error': '(no se pudo mostrar la captura de pantalla)',
 'admin_error_log_screenshot_label': 'Captura de pantalla',
 'admin_error_log_search_label': '🔍 Buscar (página, tipo de error o mensaje)',
 'admin_error_log_session_label': '🧭 Contexto de la sesión',
 'admin_error_log_severity_filter_label': 'Filtrar por gravedad',
 'admin_error_log_severity_label': 'Gravedad',
 'admin_error_log_status_filter_label': 'Filtrar por estado',
 'admin_error_log_status_label': 'Estado',
 'admin_error_log_summary_label': 'Resumen',
 'admin_error_log_technical_label': '🔧 Detalles técnicos',
 'admin_error_log_timeline_label': '🕒 Línea temporal de evidencias',
 'admin_error_log_traceback_label': 'Traceback técnico completo',
 'admin_error_log_user_label': 'Usuario',
 'admin_error_log_when_label': 'Cuándo',
 'admin_error_log_who_experienced_label': '👥 Quién lo experimentó ({n} mostrados)',
 'admin_error_log_who_experienced_partial': 'Mostrando las ocurrencias cargadas actualmente; el '
                                            'recuento total de arriba refleja cada ocurrencia '
                                            'registrada.',
 'admin_diag_filters_header': '🔍 Filtros',
 'admin_diag_filter_page': 'La página contiene',
 'admin_diag_filter_root_cause': 'La causa raíz contiene',
 'admin_diag_filter_user': 'El usuario contiene',
 'admin_diag_filter_date_from': 'Desde la fecha',
 'admin_diag_filter_date_to': 'Hasta la fecha',
 'admin_diag_metric_total': 'Total de incidencias',
 'admin_diag_metric_open': '🟥 Abiertas',
 'admin_diag_metric_fixed': '✅ Corregidas',
 'admin_diag_metric_warnings': '⚠️ Advertencias',
 'admin_diag_section_selector': 'Ver',
 'admin_diag_tab_open': '🟥 Incidencias abiertas ({n})',
 'admin_diag_tab_fixed': '✅ Incidencias corregidas ({n})',
 'admin_diag_tab_warnings': '⚠️ Advertencias ({n})',
 'admin_diag_tab_trends': '📈 Análisis de tendencias',
 'admin_diag_open_empty': 'No hay incidencias abiertas que coincidan con los filtros actuales.',
 'admin_diag_fixed_empty': 'No hay incidencias corregidas que coincidan con los filtros actuales.',
 'admin_diag_warnings_empty': 'No hay advertencias que coincidan con los filtros actuales.',
 'admin_diag_trends_empty': 'Aún no hay suficientes datos para el análisis de tendencias.',
 'admin_diag_trends_caption': 'Elaborado enteramente a partir de las incidencias ya cargadas '
                              'arriba: volumen, puntos críticos y los problemas más frecuentes, de '
                              'un vistazo.',
 'admin_diag_warnings_caption': 'Los avisos son situaciones no críticas que conviene conocer -- '
                                'como una generación de reflexión parcial -- y se mantienen '
                                'separados de los errores de la aplicación de arriba.',
 'admin_diag_trends_volume_header': '📅 Ocurrencias a lo largo del tiempo',
 'admin_diag_trends_pages_header': '📍 Páginas más afectadas',
 'admin_diag_trends_category_header': '🗂️ Ocurrencias por categoría',
 'admin_diag_trends_uncategorized': 'Sin categoría',
 'admin_diag_trends_top_issues_header': '🔁 Incidencias más frecuentes',
 'admin_diag_trends_no_issues': 'Aún no hay incidencias registradas.',
 'error_boundary_body': 'Esto se ha registrado como el error {ref}. Inténtalo de nuevo -- si sigue '
                        'ocurriendo, indica a tu administrador el número de referencia anterior.',
 'error_boundary_heading': 'Algo salió mal en esta página.',
 'rate_limit_exceeded_message': 'Has alcanzado el límite de {max} reflexiones en la última hora en '
                                'esta cuenta. Este es un límite de seguridad para prevenir '
                                'solicitudes repetidas accidentales, no una restricción de tu '
                                'trabajo habitual -- espera un poco e inténtalo de nuevo, o '
                                'contacta con tu Administrador del Sistema si crees que esto es un '
                                'error.',
 'reflection_duplicate_message': 'Esta reflexión ya se está generando. Espera un momento a que '
                                 'termine antes de intentarlo de nuevo.',
 'report_problem_caption': '¿Algo no va bien? Descríbelo abajo. Tu administrador será notificado '
                           'de inmediato.',
 'report_problem_description_label': '¿Qué ocurrió?',
 'report_problem_empty_warning': 'Añade una breve descripción antes de enviar.',
 'report_problem_header': '🚩 Reportar un problema',
 'report_problem_send_button': 'Enviar informe',
 'report_problem_sent': '✔ Informe enviado. Gracias -- tu administrador ha sido notificado.',
 'status_labels': {'New': 'Nuevo',
                   'Investigating': 'Investigando',
                   'Recurred': 'Reaparecido',
                   'Fixed': 'Corregido',
                   'Closed': 'Cerrado',
                   'All': 'Todos',
                   'Any': 'Cualquiera'},
 'severity_labels': {'All': 'Todas',
                     'error': 'Error',
                     'warning': 'Advertencia',
                     'user_reported': 'Reportado por usuario'},
 'help': {'nav_label': '❓ Ayuda',
          'page_title': 'Guía rápida de Reflection Space',
          'intro_title': '¿Qué es Reflection Space?',
          'intro_body': 'Reflection Space lee la documentación del caso que acabas de escribir y, '
                        'antes de que quede finalizada, te ofrece preguntas reflexivas en ocho '
                        'dimensiones profesionales -- por ejemplo, si la voz de la persona usuaria '
                        'está presente, o si se están pasando por alto sus fortalezas junto a las '
                        'dificultades.',
          'guardrail_note': 'La herramienta nunca califica, puntúa ni decide nada por ti. Tú '
                            'decides qué cambiar, si acaso, en tu documentación.',
          'journey_title': 'El recorrido de reflexión en tres pasos',
          'journey_steps': ['1. Documentación de hoy -- elige la(s) nota(s) de caso que acabas de '
                            'escribir y sobre las que quieres reflexionar.',
                            '2. Contexto histórico -- revisa qué documentos anteriores del caso se '
                            'han mostrado como relevantes, e incluye o excluye los que quieras.',
                            '3. Reflexión profesional -- explora las ocho dimensiones reflexivas, '
                            'conversa brevemente sobre alguna si quieres, y después actualiza y '
                            'envía tu documento.'],
          'practitioner_title': 'Espacio del profesional',
          'doc_section_title': '📝 Documentación -- escribir una nota de caso',
          'doc_section_body': 'En la página Documentación, indica la referencia del caso, elige el '
                              'tipo de documento y el idioma, y escribe tu nota. Al pulsar Guardar '
                              'se almacena como borrador privado -- solo tú puedes verlo -- hasta '
                              'que lo envíes desde Reflection Space.',
          'reflection_section_title': '🪞 Reflection Space -- reflexionar antes de enviar',
          'reflection_section_body': 'En la página Reflection Space: elige el/los borrador(es) '
                                     'sobre los que quieres reflexionar, revisa el contexto '
                                     'histórico que se ha mostrado (puedes desmarcar lo que no '
                                     'quieras tener en cuenta) y continúa para generar tu '
                                     'reflexión. Explora cualquiera de las ocho dimensiones, abre '
                                     'una breve conversación sobre alguna si quieres, y luego '
                                     'edita y envía tu documento. Después puedes valorar la '
                                     'utilidad de la sesión -- totalmente opcional.',
          'dimensions_title': 'Las ocho dimensiones reflexivas',
          'dimensions': [{'label': 'Voz de la persona usuaria',
                          'desc': '¿Está presente la voz, los objetivos y las preferencias de la '
                                  'persona, o el relato viene sobre todo del profesional?'},
                         {'label': 'Observación frente a interpretación',
                          'desc': '¿Hay afirmaciones presentadas como hechos observados que en '
                                  'realidad son interpretación, suposición u opinión?'},
                         {'label': 'Etiquetas y lenguaje',
                          'desc': '¿Hay etiquetas o términos cargados que puedan influir '
                                  'silenciosamente en cómo se percibe a esta persona o familia?'},
                         {'label': 'Posibles sesgos',
                          'desc': '¿Hay estereotipos o suposiciones no examinadas relacionadas con '
                                  'origen, género, edad, situación migratoria, salud mental o '
                                  'consumo de sustancias?'},
                         {'label': 'Evidencia para las decisiones',
                          'desc': '¿Están las decisiones de intervención claramente respaldadas '
                                  'por evidencia, o dependen de supuestos implícitos?'},
                         {'label': 'Información ausente',
                          'desc': '¿Falta información relevante cuya ausencia podría cambiar cómo '
                                  'se entiende la situación?'},
                         {'label': 'Fortalezas frente a déficits',
                          'desc': '¿El lenguaje se centra sobre todo en los problemas y déficits, '
                                  'dejando de lado las fortalezas y recursos de la persona?'},
                         {'label': 'Continuidad',
                          'desc': '¿Hay contradicciones o cambios notables entre este documento y '
                                  'los anteriores?'}],
          'growth_section_title': '🌱 Mi Reflexión -- tu diario personal',
          'growth_section_body': 'Mi Reflexión es tu espacio personal: qué temas has explorado más '
                                 'y una línea de tiempo de tus momentos reflexivos recientes. Sin '
                                 'puntuaciones, sin comparación con nadie más, visible solo para '
                                 'ti.',
          'manager_title': 'Espacio del equipo directivo',
          'learning_section_title': '📚 Aprendizaje',
          'learning_section_body': 'Aprendizaje tiene cuatro pestañas: Presencia del equipo (quién '
                                   'está activo), Asistente de conocimiento (haz una pregunta y '
                                   'obtén una respuesta basada en la documentación de casos de la '
                                   'organización), Aprendizajes (qué dimensiones han aparecido más '
                                   'a menudo) y Aprendizaje del equipo (temas agregados de los '
                                   'últimos seis meses). Todo aquí es agregado y anónimo -- no se '
                                   'puede señalar el trabajo de ninguna persona en concreto.',
          'case_history_section_title': '🗂️ Historial de casos',
          'case_history_section_body': 'Historial de casos muestra la documentación completada y '
                                       'el feedback recibido: una visión general de las '
                                       'valoraciones de utilidad y los comentarios, y los '
                                       'documentos completados agrupados por profesional, con un '
                                       'interruptor entre editado y no editado para ver qué '
                                       'cambió.',
          'research_metrics_section_title': '📊 Métricas de investigación',
          'research_metrics_section_body': 'Métricas de investigación (solo Administrador del '
                                           'sistema) ofrece una vista agregada a nivel de piloto: '
                                           'sesiones y documentos completados en total, con qué '
                                           'frecuencia se señaló cada dimensión frente a cuántas '
                                           'veces se exploró, valoraciones de feedback, y una '
                                           'exportación en CSV.',
          'admin_title': '🛠️ Administración del sistema',
          'admin_section_body': 'Administración del sistema reúne la gestión de usuarios, la '
                                'indexación de documentos y pruebas de recuperación, el estado de '
                                'salud del sistema, la configuración, las comprobaciones de estado '
                                'de las traducciones, el Centro de diagnóstico con IA (el registro '
                                'de errores) y la búsqueda en el conocimiento de casos.',
          'report_problem_title': '🚩 Reportar un problema',
          'report_problem_body': 'Cada página tiene un control 🚩 Reportar un problema en la barra '
                                 'lateral, disponible para todo el mundo. Describe lo ocurrido con '
                                 'tus propias palabras y pulsa Enviar -- el sistema añade '
                                 'automáticamente el contexto de página, sesión y navegación.',
          'privacy_title': '🔒 Privacidad y datos',
          'privacy_points': ['Los borradores pendientes son privados -- solo tú puedes verlos o '
                             'abrirlos antes de enviarlos.',
                             'El contenido de las conversaciones reflexivas nunca se guarda más '
                             'allá de la sesión -- solo se registra qué tema se exploró y cuándo.',
                             'Mi Reflexión es personal y no admite comparaciones: sin '
                             'puntuaciones, sin clasificaciones, visible solo para ti.',
                             'Las vistas de toda la organización solo funcionan con datos '
                             'agregados y anónimos.',
                             'El control de acceso basado en roles se aplica en dos niveles en '
                             'toda la aplicación.']},
 'admin_usage_header': '💰 Uso y Costes de Servicios',
 'admin_usage_caption': 'Lo que cuesta cada servicio externo en este proyecto piloto, estimado a '
                        'partir del uso real registrado de las API. Las cifras marcadas como '
                        '"estimación" no pudieron vincularse a un precio exacto del proveedor y '
                        'deben tratarse como aproximadas.',
 'admin_usage_status_green': '🟢 Correcto',
 'admin_usage_status_yellow': '🟡 Acercándose al límite',
 'admin_usage_status_orange': '🟠 Cerca del límite',
 'admin_usage_status_red': '🔴 En el límite o superado',
 'admin_usage_status_unknown': '⚪ Límite no disponible',
 'admin_usage_unavailable': 'No disponible',
 'admin_usage_limit_unavailable': 'Límite no disponible',
 'admin_usage_overview_header': 'Resumen',
 'admin_usage_col_service': 'Servicio',
 'admin_usage_col_usage': 'Uso (este mes)',
 'admin_usage_col_limit': 'Presupuesto',
 'admin_usage_col_pct': '% usado',
 'admin_usage_col_cost': 'Coste estimado (mes)',
 'admin_usage_col_status': 'Estado',
 'admin_usage_no_billing_api': 'Sin API de facturación',
 'admin_usage_connections': 'conexiones',
 'admin_usage_not_started': 'Aún no iniciado',
 'admin_usage_provider_billing_unavailable': 'Datos de facturación del proveedor no disponibles',
 'admin_usage_active_users': 'usuarios activos',
 'admin_usage_emails_sent': 'correos enviados',
 'admin_usage_claude_detail_header': 'Detalle de Claude (Anthropic)',
 'admin_usage_cost_today': 'Coste estimado hoy',
 'admin_usage_cost_month': 'Coste estimado este mes',
 'admin_usage_cost_projected': 'Coste proyectado a fin de mes',
 'admin_usage_input_tokens': 'Tokens de entrada (mes)',
 'admin_usage_output_tokens': 'Tokens de salida (mes)',
 'admin_usage_model_unrecognized': '⚠️ Algunas llamadas usaron un modelo que no está en la tabla '
                                   'de precios; su coste es una estimación de respaldo.',
 'admin_usage_anthropic_not_configured': 'La clave de la API de Anthropic no está configurada.',
 'admin_usage_per_reflection_header': 'Coste por reflexión completada',
 'admin_usage_avg_cost_reflection': 'Coste medio de Claude por reflexión',
 'admin_usage_reflections_generated': 'Reflexiones generadas (30 días)',
 'admin_usage_companion_calls': 'Llamadas de acompañantes (30 días, incl. reintentos)',
 'admin_usage_retry_rate': 'Tasa de reintentos',
 'admin_usage_no_median_note': 'No hay mediana disponible: las llamadas de cada acompañante no '
                               'están actualmente etiquetadas con la reflexión a la que '
                               'pertenecen, así que solo se puede calcular el promedio general.',
 'admin_usage_gemini_detail_header': 'Detalle de Gemini Embeddings',
 'admin_usage_embeddings_month': 'Embeddings este mes',
 'admin_usage_embeddings_failed': 'Solicitudes de embedding fallidas (mes)',
 'admin_usage_gemini_estimate_note': '⚠️ Algunas llamadas de embedding no devolvieron un recuento '
                                     'exacto de tokens del proveedor; su coste se marca como '
                                     'estimación.',
 'admin_usage_gemini_not_configured': 'La clave de la API de Gemini no está configurada.',
 'admin_usage_qdrant_detail_header': 'Detalle de Qdrant',
 'admin_usage_qdrant_vectors': 'Vectores almacenados',
 'admin_usage_qdrant_capacity': 'Capacidad configurada',
 'admin_usage_pricing_header': 'Configuración de precios y presupuestos',
 'admin_usage_pricing_caption': 'Los precios de los proveedores están centralizados en un solo '
                                'lugar (services/cost_pricing.py) para no tener que buscarlos por '
                                'todo el código cuando un proveedor cambia sus tarifas. Los '
                                'presupuestos mensuales usados para los colores de estado se '
                                'configuran en config.py (MONTHLY_BUDGET_ANTHROPIC_USD, '
                                'MONTHLY_BUDGET_GEMINI_USD).',
 'admin_usage_forecast_header': 'Previsión según volumen de usuarios (estimación)',
 'admin_usage_forecast_caption': 'Proyecta el coste mensual con un número hipotético de usuarios, '
                                 'basándose en el coste medio por reflexión medido en este '
                                 'proyecto piloto. Ajusta los números a continuación.',
 'admin_usage_forecast_users': 'Número de usuarios',
 'admin_usage_forecast_reflections': 'Reflexiones por usuario y mes',
 'admin_usage_forecast_total_reflections': 'Total de reflexiones/mes',
 'admin_usage_forecast_claude_cost': 'Coste de Claude proyectado/mes',
 'admin_usage_forecast_gemini_cost': 'Coste de Gemini proyectado/mes',
 'admin_usage_forecast_vectors': 'Recuento de vectores proyectado',
 'admin_usage_forecast_presets_header': 'Escenarios habituales',
 'admin_usage_forecast_current': 'Actual',
 'admin_usage_forecast_col_users': 'Usuarios',
 'admin_usage_forecast_col_reflections': 'Reflexiones/mes',
 'admin_usage_forecast_col_claude_cost': 'Coste de Claude estimado/mes',
 'admin_usage_forecast_estimate_disclaimer': '⚠️ Todas las proyecciones anteriores son '
                                             'ESTIMACIONES basadas en promedios observados '
                                             'actualmente, no costes garantizados.'}


# EDE Reflection Space workflow strings (kept in their own files; see services/locales/ede_es.py)
from services.locales.ede_es import EDE_ES as _EDE_ES  # noqa: E402
LANG_ES.update(_EDE_ES)
