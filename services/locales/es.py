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
 'language': 'Idioma',
 'text': 'Texto',
 'save': 'Guardar borrador',
 'success': '✔ Borrador guardado correctamente',
 'empty': 'Por favor escribe un texto',
 'new': 'Nuevo documento',
 'reflection': 'Espacio de reflexión',
 'home_subtitle': 'Un espacio para la reflexión en la práctica.',
 'nav_hint': 'Usa la barra lateral para navegar.',
 'nav_header': 'Navegar:',
 'nav_doc': '📝 Documentación',
 'nav_reflection': '🌿 Espacio de reflexión',
 'no_drafts': 'No hay borradores disponibles.',
 'select_drafts': 'Selecciona borradores para reflexionar',
 'begin_reflection': 'Comenzar reflexión',
 'reflection_folders_intro': 'Documentos pendientes de reflexión, agrupados por caso.',
 'reflection_same_day_notice': '⚠️ Este caso tiene más de un documento del mismo día.',
 'reflection_no_case_ref': '(Sin referencia de caso)',
 'reflection_active_case_prefix': 'Código de la reflexión:',
 'reflection_delete_button': 'Eliminar documento',
 'reflection_delete_confirm': '¿Confirmas que quieres eliminar este documento? Esta acción no se '
                              'puede deshacer.',
 'reflection_deleted_success': '✔ Documento eliminado.',
 'reflection_context_title': 'Contexto de la reflexión',
 'reflection_context_current_label': 'Documento(s) seleccionado(s):',
 'reflection_context_historical_label': 'Documentos históricos relevantes de este caso:',
 'reflection_context_summary_strong': 'Esta reflexión usa el caso de hoy junto con {count} '
                                      'reflexiones anteriores relacionadas.',
 'reflection_context_summary_limited': 'Esta reflexión usa sobre todo el caso de hoy, con pocas '
                                       'reflexiones anteriores relacionadas.',
 'reflection_context_summary_none': 'Esta reflexión usa solo el caso de hoy.',
 'reflection_context_continue': 'Generar la reflexión',
 'reflection_context_back': 'Volver a la selección',
 'reflection_partial_failure_notice': 'Algunas perspectivas de reflexión no se pudieron generar '
                                      '({count}). La reflexión se ha producido de todas formas. '
                                      'Esto ha quedado registrado para revisión. Puede continuar '
                                      'con lo disponible o intentarlo de nuevo.',
 'unknown_label': 'Desconocido/a',
 'audit_unknown_case_label': '(caso desconocido)',
 'case_history_completed_label': 'completado',
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
 'nav_case_history': '🗂️ Historial de reflexiones',
 'case_history_title': 'Historial de reflexiones',
 'case_history_no_items': 'Aún no hay reflexiones guardadas.',
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
 'case_history_date_filter_label': 'Ver historial de:',
 'case_history_toggle_label': 'Mostrar:',
 'case_history_edited_option': 'Editados',
 'case_history_not_edited_option': 'No editados',
 'case_history_no_items_for_filter': 'No hay reflexiones para esta selección.',
 'case_history_showing_recent': 'Mostrando los {shown} documentos más recientes de {total}. Usa el '
                                'filtro de fecha para ver documentos anteriores.',
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
 'workspace_document_header': 'Texto del caso',
 'workspace_context_header': 'Contexto de la reflexión',
 'workspace_progress_label': 'Explorado(s): {explored} de {total}',
 'workspace_explore_button': 'Explorar con el acompañante',
 'workspace_more_header': '¿Por qué estas preguntas? Mira lo que observó la IA',
 'workspace_questions_header': 'Preguntas para reflexionar',
 'rs_info_header': 'Información de la reflexión',
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
 'growth_intro': 'Este es tu espacio personal. No es una evaluación de tu desempeño y nunca se '
                 'compara con otros profesionales. Lo que exploras en las conversaciones y tus '
                 'notas son solo tuyos. Las observaciones guardadas de tus reflexiones (y su texto '
                 'anonimizado) también las pueden ver los responsables en el Historial de '
                 'reflexiones.',
 'growth_no_data': 'Aún no has explorado ninguna reflexión. A medida que uses el botón «Explorar con el '
                   'acompañante» en el Espacio de Reflexión, tu trayectoria aparecerá aquí.',
 'growth_themes_header': 'Áreas que más has explorado',
 'growth_themes_caption': 'Basado en {total} momento(s) de exploración registrados',
 'growth_history_header': 'Momentos reflexivos recientes',
 'growth_entry_line': '**{theme}** — reflexión {case} — {count} intercambio(s) — {date}',
 'growth_session_count_label': 'Momentos de exploración registrados en total',
 'journey_step1': 'Tu caso',
 'journey_step2': 'Reflexiones anteriores',
 'journey_step3': 'Reflexión Profesional',
 'journey_step4': 'Preguntas Reflexivas',
 'journey_step1_desc': 'Escribes, pegas o subes el caso sobre el que quieres reflexionar.',
 'journey_step2_desc': 'Se buscan tus reflexiones anteriores enlazadas o con temas en común.',
 'journey_step3_desc': 'La IA analiza el caso de hoy junto con las reflexiones anteriores que '
                       'hayas incluido.',
 'journey_step4_desc': 'Se te invita a considerar preguntas reflexivas.',
 'historical_timeline_header': 'Línea temporal histórica',
 'historical_timeline_intro': 'Documentos relevantes de este caso, ordenados cronológicamente.',
 'timeline_today_label': '📍 Documentación de hoy',
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
 'admin_advanced_diagnostics': '🔧 Diagnóstico avanzado',
 'admin_show_raw_response': 'Mostrar respuesta sin procesar',
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
 'admin_health_component_embedding': 'Servicio de embeddings (Gemini API)',
 'admin_health_component_reflection': 'Motor de reflexión (API de Claude)',
 'admin_health_healthy_label': 'Saludable',
 'admin_health_unreachable_label': 'No accesible',
 'admin_health_available_label': 'Disponible',
 'admin_health_not_configured_label': 'No configurado',
 'admin_health_operational_label': '✅ Operativo',
 'admin_health_db_error_prefix': 'Error de base de datos:',
 'admin_health_key_missing': 'ANTHROPIC_API_KEY no está configurado — no se pueden generar '
                             'reflexiones.',
 'admin_tools_header': '🧰 Herramientas administrativas',
 'admin_anon_empty_warning': 'Escribe o pega primero un texto de muestra y vuelve a pulsar el '
                             'botón.',
 'admin_anon_no_changes': 'El anonimizador no ha encontrado datos personales que sustituir en este '
                          'texto.',
 'admin_anon_stale_note': 'Has cambiado el texto desde la última prueba: pulsa el botón otra vez '
                          'para ver el resultado actualizado.',
 'admin_anon_tags_help': 'Etiquetas: [PERSON] = nombre de persona · [LOCATION] = lugar · [ADDRESS] '
                         '= dirección · [ORGANISATION] = centro u organización · [ID] = DNI/NIE, '
                         'expediente, cuenta u otro identificador · [PHONE] = teléfono · [EMAIL] = '
                         'correo · [DATE] = fecha · [AGE_…] = edad exacta sustituida por una '
                         'etapa de la vida (INFANT = bebé, CHILD = niño/a, ADOLESCENT = adolescente '
                         'menor de edad, YOUNG_ADULT = adulto/a joven, ADULT = adulto/a, OLDER_ADULT = '
                         'persona mayor).',
 'admin_tools_anon_test_header': 'Prueba de anonimización',
 'admin_tools_future': 'Las futuras herramientas de administración aparecerán aquí.',
 'admin_console_caption': 'Consola de administración de Reflection Space -- usuarios, estado del '
                          'sistema, problemas registrados, costes y borrado de datos.',
 'admin_error_log_unknown_page': 'página desconocida',
 'admin_error_log_no_message': '(sin mensaje)',
 'event_labels': {'Opened page': 'Página abierta',
                  'Changed page': 'Página cambiada',
                  'Email sent': 'Correo enviado',
                  'User submitted report': 'Informe enviado por el usuario',
                  'Exception occurred': 'Se produjo una excepción',
                  'Error logged': 'Error registrado'},
 'admin_error_log_caption': 'Lista de los problemas registrados en la aplicación (fallos, '
                            'llamadas fallidas de la IA o problemas comunicados por las personas '
                            'usuarias): qué ha pasado, cuándo y en qué estado está. El '
                            'diagnóstico de la IA llega en el correo de alerta.',
 'admin_problem_what_label': 'Qué ha pasado',
 'admin_problem_open_header': 'Problemas abiertos ({n})',
 'admin_problem_solved_header': 'Problemas resueltos ({n})',
 'admin_problem_none_open': 'No hay problemas abiertos.',
 'admin_reset_header': '🧹 Borrar todos los datos',
 'admin_reset_intro': 'Borra de forma definitiva todo lo guardado en la aplicación: las '
                      'reflexiones y sus textos, las observaciones y las notas, las valoraciones, '
                      'las revisiones de patrones, los documentos antiguos, el historial de '
                      'actividad, los problemas registrados y los registros de uso y costes. '
                      'Todos los contadores de la aplicación vuelven a 0.',
 'admin_reset_kept_note': 'Se conservan las cuentas de usuario y la configuración. Nadie tendrá '
                          'que volver a iniciar sesión.',
 'admin_reset_warning': 'Esta acción no se puede deshacer.',
 'admin_reset_confirm_word': 'BORRAR',
 'admin_reset_confirm_label': 'Para confirmar, escribe {word}',
 'admin_reset_button': 'Borrar todos los datos',
 'admin_reset_done': 'Se han borrado todos los datos. La aplicación empieza de cero.',
 'admin_reset_refused': 'Solo el Administrador del sistema puede hacer esto.',
 'admin_reset_failed': 'No se ha podido completar el borrado. No se ha borrado nada. Inténtalo de '
                       'nuevo.',
 'admin_error_log_empty': 'No hay problemas registrados. Todo está en orden.',
 'admin_error_log_first_seen_label': 'Visto por primera vez',
 'admin_error_log_header': '🩺 Centro de Diagnóstico',
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
 'admin_error_log_occurrences_label': 'Ocurrencias',
 'admin_error_log_page_label': 'Página',
 'admin_error_log_status_label': 'Estado',
 'admin_error_log_when_label': 'Cuándo',
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
          'intro_body': 'Reflection Space te ayuda a reflexionar sobre un caso en el momento: '
                        'escribes, pegas o subes el caso y te ofrece preguntas reflexivas en ocho '
                        'dimensiones profesionales -- por ejemplo, si la voz de la persona usuaria '
                        'está presente, o si se están pasando por alto sus fortalezas junto a las '
                        'dificultades. No es un lugar para guardar documentos: solo se guarda la '
                        'reflexión.',
          'guardrail_note': 'La herramienta nunca califica, puntúa ni decide nada por ti. Tú '
                            'decides qué hacer, si acaso, con lo que te haya hecho pensar.',
          'journey_title': 'Cómo funciona',
          'journey_steps': ['1. Reflexionemos -- escribe o pega tu texto, o sube un documento (Word, PDF o texto). No hace falta ninguna referencia, tipo de texto ni tema.', '2. Elige el idioma de la reflexión (Español, Euskara o English) y pulsa Reflexionar. El texto se anonimiza automáticamente antes de que lo reciba la IA.', '3. Reflexión profesional -- explora las ocho dimensiones reflexivas, conversa brevemente sobre alguna si quieres, añade tus notas y termina. Después, el texto del caso se retira de la pantalla.'],
          'practitioner_title': 'Espacio del profesional',
          'doc_section_title': '📝 Tu caso -- escribir, pegar o subir',
          'doc_section_body': 'En Reflection Space escribes o pegas tu texto en un solo cuadro, o subes un Word, PDF o texto (solo se lee el texto; el archivo no se guarda). Si escribes un texto y además subes un documento, se te preguntará sobre cuál quieres reflexionar. No tienes que dar ninguna referencia ni dato del caso: la aplicación crea sola un código neutro (por ejemplo RS-7F3K2Q) que no identifica a nadie. El texto original se guarda de forma segura para analizar patrones más adelante (ver abajo).',
          'original_saved_note': 'El texto original se guarda de forma segura en una base de datos de la UE, durante un máximo de {months} meses, para ayudar a detectar patrones en la práctica. A la IA solo se envía la versión anonimizada. Puedes leer tu propio texto en Mi reflexión; las personas supervisoras y responsables de programa pueden leer los textos en Revisión de patrones, sin el nombre de quien los escribió. Pasado ese tiempo se borra automáticamente; la reflexión se mantiene.',
          'reflection_section_title': '🪞 Reflection Space -- reflexionar en el momento',
          'reflection_section_body': 'Al pulsar Reflexionar, tu texto se anonimiza automáticamente (se '
                                     'quitan nombres y otros datos personales) y solo esa versión protegida '
                                     'se envía a la IA. Si la anonimización fallara, no se envía nada. En '
                                     'los resultados, «Ver texto anonimizado» te muestra exactamente lo que '
                                     'recibió la IA. Explora cualquiera de las ocho dimensiones, abre una '
                                     'breve conversación sobre alguna si quieres, añade tus notas y pulsa '
                                     'Terminar reflexión. Después puedes valorar la utilidad de la sesión '
                                     '-- totalmente opcional.',
          'cards_note': 'Las ocho oportunidades de reflexión se muestran como tarjetas en una sola vista. '
                         'El punto de la esquina indica qué encontró cada una: verde, hay algo sobre lo que '
                         'reflexionar; gris, nada destacable en este texto; naranja, no disponible ahora '
                         '(puedes reintentarlo dentro de la tarjeta). Al abrir una tarjeta ves las preguntas; '
                         'lo que observó la IA y el pasaje en que se basa están en «¿Por qué estas '
                         'preguntas?».',
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
          'delete_note': 'Puedes borrar cualquiera de tus reflexiones desde «Tus reflexiones guardadas», al '
                          'final de Mi reflexión. Desaparece en todas partes al momento; durante {hours} '
                          'horas puedes recuperarla y después se borra definitivamente.',
          'growth_section_title': '🌱 Mi Reflexión -- tu diario personal',
          'growth_section_body': 'Mi reflexión es tu propio espacio: los temas que más has explorado, una '
                                  'línea de tiempo de tus momentos de reflexión, las observaciones guardadas '
                                  'con tus notas y la lista de tus reflexiones (que puedes borrar). Sin '
                                  'puntuaciones ni comparaciones con nadie. Tus notas y lo que exploras son '
                                  'solo tuyos; las observaciones guardadas también las pueden ver los '
                                  'responsables.',
          'manager_title': 'Espacio del equipo directivo',
          'case_history_section_title': '🗂️ Historial de reflexiones',
          'case_history_section_body': 'Historial de reflexiones muestra la valoración media de '
                                       'utilidad (nunca las valoraciones individuales ni quién '
                                       'las dio) y las reflexiones guardadas, cada una con su '
                                       'código neutro, sus temas y las observaciones de la IA. Se '
                                       'puede filtrar por fecha y por tema. Nunca muestra las '
                                       'notas privadas de los profesionales.',
          'admin_title': '🛠️ Administración del sistema',
          'admin_section_body': 'Administración del sistema reúne la lista de usuarios, el estado '
                                'del sistema, la prueba de anonimización, las comprobaciones de '
                                'estado de las traducciones, el Centro de Diagnóstico (la lista '
                                'de problemas registrados) y el uso y los costes de los '
                                'servicios. También permite borrar de forma definitiva todos los '
                                'datos guardados para empezar de cero.',
          'report_problem_title': '🚩 Reportar un problema',
          'report_problem_body': 'Cada página tiene un control 🚩 Reportar un problema en la barra '
                                 'lateral, disponible para todo el mundo. Describe lo ocurrido con '
                                 'tus propias palabras y pulsa Enviar -- el sistema añade '
                                 'automáticamente el contexto de página, sesión y navegación.',
          'privacy_title': '🔒 Privacidad y datos',
          'privacy_points': ['El texto original del caso se guarda de forma segura en una base de datos de la UE durante un tiempo limitado, para analizar patrones -- a la IA solo se envía la versión anonimizada, y las personas supervisoras y responsables de programa lo leen sin tu nombre.', 'Cada reflexión se identifica con un código neutro y temas sin datos personales, nunca con nombres.', 'Tus notas sobre las observaciones son privadas -- solo tú puedes verlas. Las observaciones de la IA se usan en la revisión de patrones del equipo de gestión, sin tu nombre.', 'El contenido de las conversaciones reflexivas nunca se guarda más allá de la sesión -- solo se registra qué tema se exploró y cuándo.', 'Mi Reflexión es personal y no admite comparaciones: sin puntuaciones, sin clasificaciones, visible solo para ti.', 'El control de acceso basado en roles se aplica en dos niveles en toda la aplicación.']},
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
 'admin_usage_forecast_presets_header': 'Escenarios habituales',
 'admin_usage_forecast_current': 'Actual',
 'admin_usage_forecast_col_users': 'Usuarios',
 'admin_usage_forecast_col_reflections': 'Reflexiones/mes',
 'admin_usage_forecast_col_claude_cost': 'Coste de Claude estimado/mes',
 'admin_usage_forecast_estimate_disclaimer': '⚠️ Todas las proyecciones anteriores son '
                                             'ESTIMACIONES basadas en promedios observados '
                                             'actualmente, no costes garantizados.',
 'findings_evidence_caption': 'Pasaje del texto del caso en el que se basa esta observación:',
 'findings_unverified_notice': '{count} pasaje(s) propuesto(s) por la IA no coincidía(n) '
                               'exactamente con el texto y no se muestra(n).',
 'findings_notes_header': 'Mis notas',
 'findings_label_prompt': '¿Cómo te ha resultado?',
 'findings_label_none': 'Sin valorar',
 'findings_labels': {'useful': 'Útil',
                     'not_relevant': 'No relevante',
                     'uncertain': 'No lo tengo claro',
                     'discuss': 'Para comentar más adelante'},
 'findings_misread_label': 'Creo que la IA no ha entendido bien el contexto',
 'findings_alternative_label': 'Otra explicación posible (opcional)',
 'findings_note_label': 'Mi reflexión o nota (opcional)',
 'findings_save_button': 'Guardar mis notas',
 'findings_save_success': 'Notas guardadas.',
 'findings_save_error': 'No se han podido guardar tus notas. Inténtalo de nuevo en un momento.',
 'findings_not_saved_notice': 'Esta reflexión no se ha podido guardar, así que no podrás conservar '
                              'notas sobre ella. Puedes seguir trabajando con normalidad.',
 'findings_journal_header': 'Observaciones guardadas y tus notas',
 'findings_journal_intro': 'Aquí puedes volver a las observaciones de tus reflexiones, con el '
                           'pasaje exacto en el que se basan, y escribir o revisar tus propias '
                           'notas. Tus notas son solo para ti.',
 'findings_journal_empty': 'Todavía no hay observaciones guardadas. Aparecerán aquí después de tu '
                           'próxima reflexión.',
 'findings_journal_count': '{total} observación(es) guardada(s) — página {page} de {pages}',
 'findings_journal_count_reflections': '{total} reflexión(es) — página {page} de {pages}',
 'findings_reflection_line': '{code} — {date} — {count} observación(es)',
 'findings_reflection_notes_suffix': '· ✔ {count} con notas',
 'findings_pick_observation': 'Elige una observación',
 'findings_journal_newer': '← Más recientes',
 'findings_journal_older': 'Más antiguas →',
 'nav_patterns': '🔎 Revisión de patrones',
 'findings_notes_privacy': 'Tus notas y valoraciones son privadas: solo tú puedes verlas. Se guardan aparte de lo que dijo la IA, que nunca se modifica. Las observaciones de la IA (nunca tu nombre ni tus notas) se usan en la revisión de patrones del equipo de gestión. Al guardar, se quitan de tus notas los nombres, las edades exactas y otros datos personales.',
 'patterns_title': '🔎 Revisión de patrones',
 'patterns_no_access': 'Esta página es solo para supervisión y coordinación del programa.',
 'patterns_intro': 'Esta página ayuda al equipo a buscar temas que se repiten en las observaciones de las reflexiones de los profesionales. Lo que muestra son patrones candidatos para la reflexión, no conclusiones: un grupo de observaciones parecidas no demuestra sesgo ni mala práctica, y el conjunto no representa necesariamente a la organización. El equipo decide qué significa, si es que significa algo.',
 'patterns_pool_header': 'Qué hay para revisar',
 'patterns_pool_caption': 'Aquí aparecen todas las observaciones de las reflexiones de los profesionales. Nunca ves quién las escribió ni sus notas privadas.',
 'patterns_filter_lenses': 'Limitar a estos puntos de reflexión (vacío = todos)',
 'patterns_filter_from': 'Desde (opcional)',
 'patterns_filter_to': 'Hasta (opcional)',
 'patterns_pool_empty': 'Todavía no hay observaciones con estos filtros.',
 'patterns_pool_counts': '{observations} observación(es), de {reflections} reflexión(es) y {cases} referencia(s) de caso distinta(s).',
 'patterns_pool_no_case': '{count} reflexión(es) no tienen referencia de caso, por lo que no '
                          'cuentan como casos.',
 'patterns_generate_header': 'Buscar patrones',
 'patterns_settings_header': 'Ajustes de la búsqueda',
 'patterns_settings_intro': 'Estos ajustes son puntos de partida, no valores demostrados. '
                            'Cámbialos y compara los resultados.',
 'patterns_similarity_label': 'Cuánto deben parecerse las observaciones',
 'patterns_similarity_levels': {'broad': 'Amplio', 'balanced': 'Equilibrado', 'strict': 'Estricto'},
 'patterns_similarity_help': 'Amplio agrupa observaciones con un parecido más flojo (más grupos, '
                             'más ruido). Estricto exige un parecido mayor (menos grupos, más '
                             'fiables).',
 'patterns_min_observations_label': 'Mínimo de observaciones por grupo',
 'patterns_min_reflections_label': 'Mínimo de reflexiones distintas por grupo',
 'patterns_threshold_not_proof': 'Alcanzar estos mínimos no demuestra nada: solo decide si un '
                                 'grupo merece mostrarse para su discusión.',
 'patterns_cost_note': 'Buscar patrones usa IA para redactar hasta {max_patterns} explicaciones '
                       '(unos pocos céntimos en total). Solo se vuelve a pagar si pulsas el botón '
                       'de nuevo.',
 'patterns_pool_truncated': 'Hay más observaciones de las que se comparan de una vez; se usan las {max} más recientes.',
 'patterns_not_enough': 'Hacen falta al menos {minimum} observaciones para buscar patrones.',
 'patterns_generate_button': 'Buscar patrones',
 'patterns_generating': 'Buscando patrones…',
 'patterns_busy': 'Ya hay una búsqueda en curso. Espera a que termine e inténtalo de nuevo.',
 'patterns_unavailable': 'El servicio de comparación por significado no está configurado, así que '
                         'ahora no se pueden buscar patrones.',
 'patterns_none_found': 'No se ha encontrado ningún grupo que cumpla los mínimos entre {observations} observaciones. Prueba con un ajuste más amplio o espera a que haya más reflexiones.',
 'patterns_generated_ok': 'Se han encontrado {patterns} patrón(es) candidato(s) entre '
                          '{observations} observaciones.',
 'patterns_not_embedded': '{count} observación(es) no se pudieron comparar esta vez y han quedado '
                          'fuera.',
 'patterns_fallback_notice': 'No se pudo redactar la explicación de {count} patrón(es); se muestra '
                             'un texto sencillo y puedes reintentarlo.',
 'patterns_review_header': 'Revisar patrones candidatos',
 'patterns_no_runs': 'Todavía no se ha buscado ningún patrón.',
 'patterns_run_select': 'Búsqueda a revisar',
 'patterns_run_option': '{date} — {observations} observaciones — {patterns} patrón(es)',
 'patterns_run_caption': 'Ajustes de esta búsqueda: parecido {level}; mínimo {min_obs} '
                         'observaciones de al menos {min_refl} reflexiones distintas.',
 'patterns_filter_status': 'Mostrar estados',
 'patterns_statuses': {'candidate': 'Candidato',
                       'under_review': 'En revisión',
                       'worth_discussing': 'Merece comentarse',
                       'not_supported': 'No respaldado tras revisar',
                       'archived': 'Archivado'},
 'patterns_none_in_view': 'No hay patrones con estos filtros.',
 'patterns_cases_none': 'Ninguna de estas reflexiones tiene referencia de caso, así que no se '
                        'puede decir nada sobre casos.',
 'patterns_cases_incomplete': '{missing} de las {total} reflexiones no tienen referencia de caso, '
                              'así que no se puede establecer que se repita entre casos; solo que '
                              'aparece en varias reflexiones.',
 'patterns_cases_single': 'Todas las observaciones corresponden a una misma referencia de caso: es '
                          'una repetición dentro de un caso, no entre casos.',
 'patterns_cases_multiple': 'Las observaciones proceden de {cases} referencias de caso distintas.',
 'patterns_item_header': '{title} — {status} — {observations} obs. / {reflections} reflexiones',
 'patterns_candidate_label': 'Patrón candidato para la reflexión — no es una conclusión.',
 'patterns_counts_line': '{observations} observación(es) · {reflections} reflexión(es) distinta(s) '
                         '· {cases} caso(s) distinto(s)',
 'patterns_case_ref_caveat': 'Las referencias de caso se escriben a mano: una errata puede hacer '
                             'que un mismo caso cuente como dos.',
 'patterns_dates_line': 'Reflexiones entre {first} y {last}',
 'patterns_lenses_line': 'Puntos de reflexión: {lenses}',
 'patterns_lost_members': '{count} de las observaciones de este patrón ya no están disponibles (su reflexión fue eliminada). La explicación escrita puede seguir reflejándolas: conviene volver a buscar patrones antes de fiarse de ella.',
 'patterns_below_minimum': 'Con las observaciones actuales, este grupo ya no alcanza los mínimos '
                           'con los que se encontró.',
 'patterns_explanation_failed': 'La explicación automática de este patrón no se pudo redactar. Se '
                                'muestra un texto sencillo.',
 'patterns_explanation_retry': 'Reintentar la explicación',
 'patterns_retry_ok': 'Explicación redactada.',
 'patterns_retry_failed': 'Sigue sin poder redactarse la explicación. Inténtalo más tarde.',
 'patterns_what_in_common': 'Qué tienen en común',
 'patterns_why_it_matters': 'Por qué puede importar',
 'patterns_alternatives': 'Otras explicaciones posibles',
 'patterns_limitations': 'Lo que no se puede saber a partir de esto',
 'patterns_questions': 'Preguntas para comentar',
 'patterns_observations_header': 'Observaciones del grupo (con la cita exacta)',
 'patterns_exclude_button': 'Esta observación no pertenece a este patrón',
 'patterns_excluded_ok': 'Observación retirada del patrón.',
 'patterns_more_observations': 'Y {count} observación(es) más no se muestran aquí.',
 'patterns_excluded_header': 'Observaciones retiradas del patrón por el equipo',
 'patterns_restore_button': 'Volver a incluirla',
 'patterns_restored_ok': 'Observación incluida de nuevo.',
 'patterns_review_status_header': 'Valoración del equipo',
 'patterns_review_help': 'Registra aquí vuestro propio juicio. Lo que propuso la IA no se borra ni '
                         'se modifica.',
 'patterns_status_label': 'Estado',
 'patterns_comment_label': 'Comentario (opcional)',
 'patterns_save_review': 'Guardar valoración',
 'patterns_review_saved': 'Valoración guardada.',
 'patterns_review_nothing': 'No hay ningún cambio que guardar.',
 'patterns_history_header': 'Historial',
 'patterns_event_kinds': {'generated': 'Patrón generado',
                          'status_changed': 'Estado cambiado',
                          'carried_over': 'Valoración heredada de una búsqueda anterior',
                          'member_excluded': 'Observación retirada del patrón',
                          'member_restored': 'Observación incluida de nuevo',
                          'explanation_regenerated': 'Explicación redactada de nuevo'},
 'patterns_event_status_change': '({old} → {new})',
 'patterns_event_system': 'Sistema',
 'doc_import_label': 'O sube un documento (Word, PDF o texto)',
 'doc_import_help': 'Solo se lee el texto; el archivo no se guarda. Hasta {max_mb} MB, {max_pages} '
                    'páginas y unos {max_chars} caracteres. Los PDF escaneados (fotos de papel) no '
                    'se pueden leer.',
 'doc_import_loaded': 'Texto cargado. Revísalo y corrígelo antes de continuar. El archivo en sí no se guarda.',
 'doc_import_errors': {'unsupported': 'Este tipo de archivo no se admite. Usa Word (.docx), PDF o '
                                      'texto (.txt).',
                       'too_large': 'El archivo es demasiado grande (máximo {max_mb} MB).',
                       'too_long': 'El documento es demasiado largo (máximo unos {max_chars} '
                                   'caracteres). Divídelo en partes y sube cada una por separado.',
                       'too_many_pages': 'El PDF tiene demasiadas páginas (máximo {max_pages}).',
                       'encrypted': 'El archivo está protegido con contraseña. Quita la protección '
                                    'y vuelve a subirlo.',
                       'no_text': 'No se ha encontrado texto en el archivo. Si es un PDF '
                                  'escaneado, copia el texto a mano o usa una versión con texto.',
                       'unreadable': 'No se ha podido leer el archivo. Puede estar dañado; prueba '
                                     'a guardarlo de nuevo o pega el texto.',
                       'unavailable': 'La lectura de este tipo de archivo no está disponible ahora '
                                      'mismo. Pega el texto directamente.'},
 'report_doc_title': 'Informe de patrones candidatos para la reflexión',
 'report_confidential': 'Documento confidencial para el equipo de gestión',
 'report_prepared': 'Preparado el {date}',
 'report_how_to_read_title': 'Cómo leer este informe',
 'report_how_to_read': 'Este informe recoge patrones candidatos: grupos de observaciones parecidas que el equipo puede querer comentar. No son conclusiones. Un grupo de observaciones parecidas no demuestra sesgo ni mala práctica, y las observaciones proceden de las reflexiones hechas en la aplicación, por lo que no representan necesariamente a la organización. El equipo decide qué significa cada patrón, si es que significa algo.',
 'report_search_title': 'Búsqueda de la que procede',
 'report_search_line': 'Búsqueda del {date}: {observations} observaciones comparadas y {patterns} patrón(es) candidato(s) encontrado(s).',
 'report_filters_line': 'Filtros de la búsqueda: {filters}',
 'report_no_filters': 'ninguno',
 'report_statuses_line': 'Estados incluidos en este informe: {statuses}',
 'report_summary_title': 'Resumen',
 'report_col_pattern': 'Patrón candidato',
 'report_col_status': 'Estado',
 'report_col_obs': 'Observaciones',
 'report_col_refl': 'Reflexiones distintas',
 'report_col_cases': 'Casos distintos',
 'report_pattern_heading': 'Patrón {n}: {title}',
 'report_no_patterns': 'No hay patrones con los estados seleccionados.',
 'report_team_comments': 'Comentarios del equipo',
 'report_observations_omitted': 'Las observaciones y las citas no se incluyen en este informe.',
 'report_quote_label': 'Cita exacta',
 'report_limits_title': 'Límites de este informe',
 'report_limits_list': ['Es una agrupación automática por parecido de significado; puede unir observaciones que no tienen relación o separar otras que sí la tienen.', 'Las observaciones proceden de reflexiones asistidas por IA hechas en la aplicación; no son un registro completo ni representativo.', 'Las referencias de caso se escriben a mano: una errata puede hacer que un mismo caso cuente como dos.', 'El texto explicativo lo redacta la IA a partir de las observaciones y puede reflejar observaciones retiradas después de la búsqueda.', 'Ningún elemento de este informe identifica a quien escribió una observación ni incluye sus notas privadas.'],
 'report_footer': 'Confidencial · Patrones candidatos para la reflexión, no conclusiones · {date}',
 'report_section_header': 'Informe imprimible',
 'report_section_intro': 'Genera un documento para imprimir o guardar como PDF con los patrones '
                         'que se muestran arriba (según el estado elegido).',
 'report_opt_observations': 'Incluir las observaciones y sus citas exactas',
 'report_opt_case_refs': 'Incluir las referencias de caso (desmarcado por defecto: el papel '
                         'circula más que la pantalla)',
 'report_opt_comments': 'Incluir los comentarios del equipo',
 'report_prepare_button': 'Preparar informe',
 'report_ready': 'Informe preparado.',
 'report_download_button': 'Descargar informe',
 'report_how_to_print': 'Abre el archivo descargado en tu navegador y pulsa Ctrl+P (o Imprimir) '
                        'para imprimirlo o guardarlo como PDF.',
 'report_outdated': 'Has cambiado la búsqueda, los estados o las opciones: vuelve a preparar el '
                    'informe.',
 'rs_intro': 'Escribe, pega o sube el caso sobre el que quieres reflexionar y reflexiona en el momento. A la IA solo se envía una versión anonimizada de tu texto. El texto original se guarda de forma segura junto con la reflexión, para analizar patrones más adelante.',
 'rs_code_label': 'Código de esta reflexión:',
 'rs_code_help': 'Código neutro generado por la aplicación. No identifica a ninguna persona. '
                 'Anótalo si más adelante quieres enlazar otra reflexión sobre la misma situación.',
 'rs_note_type_label': 'Tipo de texto',
 'rs_tags_label': 'Temas del caso (sin datos personales)',
 'rs_tags_placeholder': 'Elige uno o varios temas',
 'rs_tags_help': 'Marca hasta {max} temas que describan la situación, nunca a la persona. Sirven '
                 'para encontrar después tus reflexiones sobre situaciones parecidas.',
 'rs_tags_short_label': 'Temas',
 'rs_no_tags': 'Sin temas',
 'rs_previous_code_label': '¿Continúa una reflexión anterior? (opcional)',
 'rs_previous_code_placeholder': 'RS-XXXXXX',
 'rs_previous_code_help': 'Si ya reflexionaste antes sobre esta misma situación, escribe aquí el '
                          'código de aquella reflexión para tenerla en cuenta. Solo puedes enlazar '
                          'tus propias reflexiones.',
 'rs_previous_code_invalid': 'Ese código no tiene el formato correcto. Debe ser como RS-7F3K2Q.',
 'rs_previous_code_not_found': 'No se ha encontrado ninguna reflexión tuya con el código {code}. '
                               'Revisa el código o deja el campo vacío.',
 'rs_previous_code_check_failed': 'No se ha podido comprobar el código anterior en este momento. '
                                  'Inténtalo de nuevo o deja el campo vacío.',
 'rs_case_text_label': 'Texto del caso',
 'rs_case_text_placeholder': 'Escribe o pega aquí el caso…',
 'rs_case_text_not_saved_note': '🔒 Este texto no se guarda. Solo existe mientras dura esta '
                                'reflexión.',
 'rs_continue_button': 'Continuar',
 'rs_case_text_review_label': 'Texto del caso',
 'rs_similar_header': 'Tus reflexiones anteriores relacionadas',
 'rs_similar_intro': 'Reflexiones tuyas enlazadas con esta o con temas en común. Desmarca las que '
                     'no quieras tener en cuenta.',
 'rs_similar_none': 'No hay reflexiones anteriores tuyas enlazadas o con temas en común. La '
                    'reflexión se hará solo con el texto de hoy.',
 'rs_similar_failed': 'No se han podido buscar tus reflexiones anteriores en este momento. Puedes '
                      'continuar: la reflexión se hará solo con el texto de hoy.',
 'rs_similar_reason_linked': 'Enlazada como reflexión anterior de esta situación',
 'rs_similar_reason_tags': 'Temas en común',
 'rs_similar_include_label': 'Tener en cuenta esta reflexión',
 'rs_similar_observations_label': 'Ver sus observaciones',
 'rs_similar_used_label': 'Reflexiones anteriores incluidas',
 'rs_back_to_case_button': 'Volver al caso',
 'rs_finish_header': 'Terminar la reflexión',
 'rs_finish_caption': 'Tu reflexión y tus notas quedan guardadas con el código {code}. Al terminar, el texto del caso se retira de esta pantalla.',
 'rs_finish_caption_unsaved': 'Esta reflexión no se ha podido guardar. Al terminar, el texto del caso se retira de esta pantalla.',
 'rs_finish_button': 'Terminar reflexión',
 'rs_finished_success': '✔ Reflexión terminada. El texto del caso se ha retirado de esta pantalla.',
 'rs_start_over_button': 'Empezar de nuevo',
 'ch_reflections_header': 'Reflexiones guardadas',
 'ch_reflections_intro': 'Cada reflexión aparece con su código neutro y sus temas. Se muestran las observaciones de la IA; nunca las notas privadas de los profesionales. Los textos originales no se muestran aquí: pueden leerse en Revisión de patrones, sin el nombre de quien los escribió.',
 'ch_tag_filter_label': 'Tema',
 'ch_all_tags': 'Todos los temas',
 'ch_showing_recent': 'Mostrando las {shown} reflexiones más recientes de {total}. Elige una fecha '
                      'o un tema para acotar.',
 'ch_author_label': 'Realizada por',
 'ch_linked_label': 'Continúa la reflexión',
 'ch_no_observations': 'Esta reflexión no tiene observaciones guardadas.',
 'ch_delete_button': 'Eliminar reflexión',
 'ch_delete_confirm': '¿Confirmas que quieres eliminar esta reflexión? Se borrarán sus '
                      'observaciones y las notas asociadas. Esta acción no se puede deshacer.',
 'ch_deleted_success': '✔ Reflexión eliminada.',
 'ch_delete_failed': '⚠ No se pudo eliminar la reflexión.',
 'case_tag_labels': {'housing': 'Vivienda / sinhogarismo',
                     'employment_training': 'Empleo y formación',
                     'income_benefits': 'Ingresos y prestaciones',
                     'mental_health': 'Salud mental',
                     'physical_health': 'Salud física',
                     'addictions': 'Adicciones',
                     'disability': 'Discapacidad',
                     'family_relationships': 'Relaciones familiares',
                     'children_youth': 'Infancia y juventud',
                     'older_people': 'Personas mayores',
                     'gender_violence': 'Violencia de género',
                     'social_isolation': 'Soledad / aislamiento social',
                     'migration_integration': 'Migración e integración',
                     'legal_administrative': 'Trámites legales y administrativos'},
 'rs_heading': 'Reflexionemos.',
 'rs_subheading': 'Tómate un momento para explorar una situación de tu práctica profesional.',
 'rs_material_label': 'Tu material de reflexión',
 'rs_material_placeholder': 'Escribe o pega aquí tu texto. Puedes compartir una situación de un '
                            'caso, una observación, una experiencia profesional o algo que quieras '
                            'explorar...',
 'rs_file_loaded': 'Documento leído: **{name}**. Para cambiarlo, quítalo con la ✕ o sube otro.',
 'rs_both_inputs_notice': 'Has escrito un texto y también has subido un documento. ¿Sobre cuál '
                          'quieres reflexionar?',
 'rs_source_label': 'Reflexionar sobre',
 'rs_source_options': {'text': 'Mi texto escrito',
                       'file': 'El documento subido',
                       'both': 'Ambos juntos'},
 'rs_choose_source_warning': 'Elige primero sobre qué texto quieres reflexionar.',
 'rs_need_material': 'Escribe, pega o sube un texto antes de pulsar Reflexionar.',
 'rs_language_label': 'Idioma de la reflexión',
 'rs_language_names': {'Español': 'Español', 'Euskera': 'Euskara', 'English': 'English'},
 'rs_privacy_note': '🛡️ Antes de enviar nada a la IA, se quitan automáticamente los nombres, '
                    'las edades exactas y otros datos personales.',
 'privacy_message_blocked': 'No hemos podido proteger tu mensaje, así que no se ha enviado nada a '
                            'la IA. Inténtalo de nuevo; si el problema continúa, avisa al equipo '
                            'de soporte.',
 'rs_reflect_button': 'Reflexionar',
 'rs_anonymised_status': 'Tu texto ha sido anonimizado.',
 'rs_preparing_status': 'Preparando tu reflexión...',
 'rs_anonymise_failed': 'No hemos podido proteger tu texto, así que no se ha enviado nada a la IA. '
                        'Tu texto sigue aquí. Inténtalo de nuevo; si el problema continúa, avisa '
                        'al equipo de soporte.',
 'rs_anonymised_preview_label': 'Ver texto anonimizado',
 'rs_anonymised_preview_help': 'Comprueba la versión protegida de tu material. Es exactamente lo '
                               'que ha recibido la IA.',
 'rs_try_again_button': 'Volver a intentarlo con el mismo texto',
 'rs_original_saved_note': '📁 El texto original se guarda de forma segura (base de datos en la UE) durante un máximo de {months} meses, para ayudar a detectar patrones en la práctica. Las personas supervisoras y responsables de programa pueden leerlo con ese fin, sin tu nombre. A la IA solo se envía la versión anonimizada.',
 'ch_show_anonymised_text': 'Ver el texto anonimizado guardado',
 'ch_anonymised_text_caption': 'Versión protegida que recibió la IA (nunca el texto original). Se '
                               'borra automáticamente a los {months} meses.',
 'ch_anonymised_text_unavailable': 'El texto anonimizado de esta reflexión ya no está disponible.',
 'ch_show_saved_text': 'Ver el texto guardado',
 'ch_original_text_caption': 'El texto original, tal como lo escribiste. Nunca se envía a la IA y se borra automáticamente a los {months} meses.',
 'ch_saved_text_unavailable': 'El texto de esta reflexión no está disponible (no se guardó o ya se ha borrado).',
 'ch_original_text_in_patterns_note': '📄 El texto original de esta reflexión está guardado. Las personas supervisoras y responsables de programa pueden leerlo en Revisión de patrones, sin el nombre de quien lo escribió.',
 'patterns_texts_header': '📄 Textos originales guardados',
 'patterns_texts_caption': 'Los textos originales a partir de los que se hicieron las reflexiones, para estudiar patrones en cómo se escriben los casos. Nunca se muestran nombres de autores, códigos de reflexión ni horas exactas. Cada texto se borra automáticamente a los {months} meses. Estos textos son confidenciales: no los copies fuera de la aplicación.',
 'patterns_texts_empty': 'Todavía no se ha guardado ningún texto original.',
 'patterns_texts_showing': 'Se muestran los {shown} más recientes de {total} textos guardados.',
 'patterns_texts_item': 'Texto del {date} · {language}',
 'rs_cards_hint': 'Elige cualquier tarjeta para abrirla.',
 'rs_cards_choose': 'Elige una tarjeta para ver su reflexión.',
 'rs_card_explored': '✓ Explorada',
 'rs_card_status': {'finding': 'Hay algo sobre lo que reflexionar',
                    'none': 'No se ha encontrado nada destacable',
                    'unavailable': 'No disponible ahora, puedes reintentar'},
 'my_reflections_header': 'Tus reflexiones guardadas',
 'my_reflections_intro': 'Puedes borrar cualquiera de tus reflexiones. Desaparece en todas partes '
                         '(también para los responsables y del análisis de patrones), con sus '
                         'observaciones, tus notas y su texto anonimizado. Durante {hours} horas '
                         'puedes recuperarla; después se borra definitivamente.',
 'my_reflections_empty': 'Todavía no tienes reflexiones guardadas.',
 'my_reflections_showing': 'Se muestran las {shown} más recientes de {total}.',
 'my_reflections_line': '{date} · {count} observación(es)',
 'my_reflections_delete': 'Borrar',
 'my_reflections_confirm': '¿Borrar la reflexión {code}? Desaparecerá en todas partes. Podrás '
                           'recuperarla durante {hours} horas.',
 'my_reflections_confirm_yes': 'Sí, borrar',
 'my_reflections_confirm_cancel': 'Cancelar',
 'my_reflections_deleted': 'Reflexión {code} borrada. Puedes recuperarla durante {hours} horas.',
 'my_reflections_restored': 'Reflexión {code} recuperada.',
 'my_reflections_failed': 'No se ha podido completar. Inténtalo de nuevo.',
 'my_reflections_deleted_header': 'Borradas recientemente',
 'my_reflections_restore': 'Recuperar',
 'my_reflections_erase_on': 'Se borrará definitivamente el {date} (UTC).'}
