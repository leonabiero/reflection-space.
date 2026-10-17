"""Textos en español del flujo EDE Reflection Space (idioma maestro)."""

EDE_ES = {
    "nav_ede": "Reflexión EDE",
    "ede_title": "Reflexión EDE sobre la práctica profesional",
    "ede_intro": (
        "Esta herramienta ayuda a reflexionar sobre cómo se documenta la intervención: "
        "qué se describe, con qué palabras y qué queda sin documentar. El objeto de "
        "aprendizaje es la práctica profesional, no las personas atendidas."
    ),
    "ede_ai_disclaimer": (
        "Las observaciones generadas por IA son hipótesis para la reflexión profesional, "
        "no conclusiones verificadas. No evalúan a personas ni a profesionales, no "
        "puntúan, no clasifican y no sustituyen el juicio profesional."
    ),
    "ede_privacy_notice": (
        "Privacidad: antes de enviarse al modelo de IA, el texto pasa por el filtro de "
        "anonimización de la aplicación (nombres, contactos, fechas, identificadores). "
        "Ese filtro reduce el riesgo, pero no garantiza el anonimato: puede quedar "
        "información indirecta que identifique a alguien. No incluyas datos personales "
        "innecesarios. El texto no se guarda en la base de datos ni en el buscador "
        "semántico; solo permanece en esta sesión hasta que lo borres o cierres sesión. "
        "No uses informes reales hasta que EDE haya aprobado el tratamiento con el "
        "proveedor de IA."
    ),
    "ede_step1": "1. Contexto",
    "ede_programme_label": "Programa",
    "ede_doctype_label": "Tipo de documento",
    "ede_language_label": "Idioma de las explicaciones",
    "ede_lang_auto": "Automático (idioma del documento)",
    "ede_step2": "2. Texto a analizar",
    "ede_upload_label": "Cargar un archivo de texto (.txt o .md)",
    "ede_upload_help": "Solo se admiten archivos de texto plano (.txt, .md) codificados en UTF-8.",
    "ede_text_label": "Texto del documento",
    "ede_text_placeholder": "Pega aquí el texto seleccionado (sin datos personales innecesarios).",
    "ede_char_counter": "{n} de {max} caracteres",
    "ede_step3": "3. Análisis",
    "ede_analyse_button": "Explorar la práctica profesional",
    "ede_progress": "Analizando el texto con el modelo de IA configurado…",
    "ede_retry_button": "Reintentar",
    "ede_clear_button": "Borrar texto y resultados de esta sesión",
    "ede_cleared": "Se han borrado el texto y los resultados de esta sesión.",
    "ede_step4": "4. Observaciones para la reflexión",
    "ede_detected_language": "Idioma detectado del documento: {lang}",
    "ede_explained_in": "Explicaciones en: {lang}",
    "ede_counts": "Observaciones validadas: {accepted}",
    "ede_discarded_notice": (
        "{n} observación(es) generada(s) por el modelo se descartaron porque no cumplían "
        "el formato exigido o porque su cita no aparece literalmente en el texto analizado."
    ),
    "ede_no_findings": (
        "No se planteó ninguna observación para esta dimensión. Eso no significa que no "
        "haya nada que reflexionar: solo que el análisis no encontró un apoyo claro en este texto."
    ),
    "ede_evidence_quote_loc": "Fragmento del texto (párrafo {n})",
    "ede_evidence_absence": "No documentado en este texto",
    "ede_absence_caveat": (
        "Que algo no aparezca en este texto no demuestra que se desconozca ni que no exista "
        "en otros documentos o en la realidad."
    ),
    "ede_ai_hypothesis_tag": "Hipótesis de la IA",
    "ede_observation": "Observación provisional",
    "ede_why": "Por qué puede ser relevante",
    "ede_alternative": "Perspectiva alternativa",
    "ede_questions": "Preguntas para la conversación profesional",
    "ede_limitations": "Limitaciones: lo que no se puede concluir",
    "ede_single_doc_caveat": (
        "Se ha analizado un solo documento: aquí solo pueden señalarse contradicciones "
        "internas del propio texto, no evolución ni tendencias en el tiempo."
    ),
    "ede_feedback_header": "Valoración profesional",
    "ede_fb_rating_label": "¿Cómo valoras esta observación?",
    "ede_fb_rating": {
        "none": "Sin valorar",
        "useful": "Útil",
        "unsupported": "No respaldada o no relevante",
    },
    "ede_fb_alternative_label": "Mi interpretación alternativa",
    "ede_fb_team_question_label": "Pregunta para la reunión de equipo",
    "ede_feedback_caption": (
        "Estas anotaciones solo se guardan en esta sesión y en la exportación que descargues. "
        "No se usan para entrenar el modelo, ni para cambiar las instrucciones, ni como "
        "indicador de desempeño."
    ),
    "ede_export_header": "Exportar",
    "ede_export_caption": (
        "La exportación incluye solo las observaciones validadas y tus anotaciones, con sus "
        "fragmentos de evidencia y limitaciones. No incluye el documento completo."
    ),
    "ede_export_json": "Descargar (JSON)",
    "ede_export_md": "Descargar (Markdown)",
    "ede_export_md_title": "Reflexión sobre la práctica profesional",
    "ede_issue_ref": "Referencia de la incidencia: #{id}",
    "ede_err_prefix": "No se pudo completar el análisis.",
    "ede_errors": {
        "input_empty": "El texto está vacío. Pega o carga un documento.",
        "input_too_short": "El texto es demasiado corto para analizarlo.",
        "input_too_long": "El texto supera la longitud máxima permitida ({max} caracteres). Selecciona un fragmento más breve.",
        "input_invalid": "El texto o las opciones elegidas no son válidos.",
        "not_authorised": "No tienes permiso para usar esta función.",
        "provider_not_configured": "El servicio de IA no está configurado correctamente. Avisa a la administración del sistema.",
        "provider_unavailable": "El servicio de IA no está disponible en este momento. Puedes reintentarlo.",
        "output_invalid": "El modelo devolvió una respuesta que no cumple el formato exigido. Puedes reintentarlo.",
        "output_truncated": "La respuesta del modelo se cortó antes de terminar. Puedes reintentarlo.",
        "busy": "El servicio está muy ocupado ahora mismo. Inténtalo de nuevo en un momento.",
        "rate_limited": "Has alcanzado el límite de análisis por hora. Espera un poco e inténtalo de nuevo.",
        "upload_type": "Solo se admiten archivos .txt o .md.",
        "upload_too_large": "El archivo es demasiado grande.",
        "upload_decode": "No se pudo leer el archivo. Debe ser texto plano en UTF-8.",
        "unknown": "Ocurrió un error inesperado.",
    },
    "ede_langs": {
        "es": "español", "eu": "euskera", "en": "inglés",
        "mixed": "mezcla de idiomas", "unknown": "no determinado",
    },
    "ede_programmes": {
        "social_accommodation_bizkaia": "Alojamientos sociales – Bizkaia",
        "supported_housing_gipuzkoa": "Viviendas de inclusión social – Gipuzkoa",
        "kulunka_bilbao": "Kulunka – Bilbao",
        "olakueta_etxea_berriz": "Olakueta Etxea – Berriz",
    },
    "ede_doctypes": {
        "follow_up_report": "Informe de seguimiento",
        "case_note": "Nota de caso",
        "follow_up_diary": "Diario de seguimiento",
        "interview_record": "Registro de entrevista",
        "social_work_report": "Informe social",
        "referral_proposal": "Propuesta de derivación",
        "intervention_plan": "Plan de intervención",
        "professional_email": "Correo entre profesionales",
        "coordination_record": "Registro de coordinación",
        "other": "Otro documento profesional",
    },
    "ede_dims": {
        "strengths_vs_deficits": {
            "label": "Lenguaje centrado en déficits o en fortalezas",
            "desc": "¿El relato recoge también fortalezas, recursos, autonomía y avances?"},
        "observation_vs_interpretation": {
            "label": "Hechos observables e interpretaciones",
            "desc": "¿Qué es observable, qué lo cuentan terceros y qué es interpretación o suposición?"},
        "labels_and_language": {
            "label": "Etiquetas que pueden influir en el juicio profesional",
            "desc": "¿Hay palabras o generalizaciones que condicionen la mirada?"},
        "stereotypes_and_assumptions": {
            "label": "Posibles estereotipos y supuestos implícitos",
            "desc": "Solo cuando la redacción o el razonamiento dan una base razonable para reflexionar."},
        "evidence_for_decisions": {
            "label": "Evidencia que respalda las decisiones de intervención",
            "desc": "¿Se ve en el texto en qué se apoyan interpretaciones, objetivos y decisiones?"},
        "missing_information": {
            "label": "Información ausente y perspectivas alternativas",
            "desc": "Lo no documentado en este texto (que no es lo mismo que desconocido)."},
        "contradictions_and_change": {
            "label": "Contradicciones y cambios",
            "desc": "Con un solo documento, solo contradicciones internas del propio texto."},
        "persons_voice": {
            "label": "La voz, las preferencias y los objetivos de vida de la persona",
            "desc": "¿Se recogen sus palabras, decisiones y aspiraciones?"},
    },
}
