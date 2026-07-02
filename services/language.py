import streamlit as st

LANG = {
    "Español": {
        "title": "🧠 Espacio de Reflexión",
        "doc": "Documentación",
        "case_ref": "Referencia del caso",
        "doc_type": "Tipo de documento",
        "doc_types": [
            "Nota de caso",
            "Diario de seguimiento",
            "Registro de entrevista",
            "Informe social",
            "Propuesta de derivación",
            "Plan de intervención",
            "Correo electrónico",
        ],
        "language": "Idioma",
        "text": "Texto",
        "save": "Guardar borrador",
        "success": "✔ Borrador guardado correctamente",
        "empty": "Por favor escribe un texto",
        "new": "Nuevo documento",
        "reflection": "Espacio de reflexión",
        "home_subtitle": "Un espacio para la documentación y la reflexión en la práctica.",
        "nav_hint": "Usa la barra lateral para navegar.",
        "nav_header": "Navegar:",
        "nav_doc": "📝 Documentación",
        "nav_reflection": "🌿 Espacio de reflexión",
        "nav_learning": "📚 Aprendizaje",
        "no_drafts": "No hay borradores disponibles.",
        "select_drafts": "Selecciona borradores para reflexionar",
        "begin_reflection": "Comenzar reflexión",
        "learning_phase2": "Los temas reflexivos emergentes apareceran aqui en la Fase 2.",
        "themes": [
            "Voz de la persona",
            "Hechos vs. Interpretación",
            "Etiquetas y lenguaje",
            "Posibles sesgos",
            "Evidencia de las decisiones",
            "Información ausente",
            "Fortalezas vs. Déficits",
            "Continuidad",
        ],
        "section_labels": {
            "client_voice": "Voz de la persona",
            "observation_vs_interpretation": "Hechos vs. Interpretación",
            "labels_and_language": "Etiquetas y lenguaje",
            "possible_bias": "Posibles sesgos",
            "evidence_for_decisions": "Evidencia de las decisiones",
            "missing_information": "Información ausente",
            "strengths_and_deficits": "Fortalezas vs. Déficits",
            "continuity": "Continuidad",
        },
        "update_document": "Actualizar documento",
        "edit_document_label": "Edita el documento aquí si lo deseas",
        "submit_no_edit": "Enviar sin editar",
        "submit_with_edit": "Enviar con los cambios",
        "submitted": "✔ Documento enviado",
        "error_parsing": "⚠ No se pudo procesar la respuesta de la reflexión. Inténtalo de nuevo.",
    },
    "Euskera": {
        "title": "🧠 Hausnarketa Gunea",
        "doc": "Dokumentazioa",
        "case_ref": "Kasuaren erreferentzia",
        "doc_type": "Dokumentu mota",
        "doc_types": [
            "Kasu-oharra",
            "Jarraipen egunkaria",
            "Elkarrizketaren erregistroa",
            "Gizarte-txostena",
            "Deribazio proposamena",
            "Esku-hartze plana",
            "Posta elektronikoa",
        ],
        "language": "Hizkuntza",
        "text": "Testua",
        "save": "Gorde zirriborroa",
        "success": "✔ Zirriborroa ondo gorde da",
        "empty": "Mesedez idatzi testua",
        "new": "Dokumentu berria",
        "reflection": "Hausnarketa gunea",
        "home_subtitle": "Praktikan dokumentatzeko eta hausnartzeko gune bat.",
        "nav_hint": "Erabili alboko barra nabigatzeko.",
        "nav_header": "Nabigatu:",
        "nav_doc": "📝 Dokumentazioa",
        "nav_reflection": "🌿 Hausnarketa gunea",
        "nav_learning": "📚 Ikaskuntza",
        "no_drafts": "Ez dago zirriborrorik eskuragarri.",
        "select_drafts": "Hautatu hausnartzeko zirriborroak",
        "begin_reflection": "Hasi hausnarketa",
        "learning_phase2": "Sortzen ari diren hausnarketa-gaiak hemen agertuko dira 2. fasean.",
        "themes": [
            "Pertsonaren ahotsa",
            "Ebidentzia vs. Interpretazioa",
            "Etiketak eta hizkera",
            "Balizko joerak",
            "Erabakien ebidentzia",
            "Falta den informazioa",
            "Indarguneak vs. Gabeziak",
            "Jarraitutasuna",
        ],
        "section_labels": {
            "client_voice": "Pertsonaren ahotsa",
            "observation_vs_interpretation": "Ebidentzia vs. Interpretazioa",
            "labels_and_language": "Etiketak eta hizkera",
            "possible_bias": "Balizko joerak",
            "evidence_for_decisions": "Erabakien ebidentzia",
            "missing_information": "Falta den informazioa",
            "strengths_and_deficits": "Indarguneak vs. Gabeziak",
            "continuity": "Jarraitutasuna",
        },
        "update_document": "Eguneratu dokumentua",
        "edit_document_label": "Editatu dokumentua hemen nahi baduzu",
        "submit_no_edit": "Bidali editatu gabe",
        "submit_with_edit": "Bidali aldaketekin",
        "submitted": "✔ Dokumentua bidalita",
        "error_parsing": "⚠ Ezin izan da hausnarketaren erantzuna prozesatu. Saiatu berriro.",
    },
    "English": {
        "title": "🧠 Reflection Space",
        "doc": "Documentation",
        "case_ref": "Case reference",
        "doc_type": "Document type",
        "doc_types": [
            "Case note",
            "Follow-up diary",
            "Interview record",
            "Social work report",
            "Referral proposal",
            "Intervention plan",
            "Email",
        ],
        "language": "Language",
        "text": "Text",
        "save": "Save draft",
        "success": "✔ Draft saved successfully",
        "empty": "Please write some text",
        "new": "New document",
        "reflection": "Reflection space",
        "home_subtitle": "A space for documentation and reflection in practice.",
        "nav_hint": "Use the sidebar to navigate.",
        "nav_header": "Navigate:",
        "nav_doc": "📝 Documentation",
        "nav_reflection": "🌿 Reflection Space",
        "nav_learning": "📚 Learning",
        "no_drafts": "No drafts available.",
        "select_drafts": "Select drafts to reflect on",
        "begin_reflection": "Begin Reflection",
        "learning_phase2": "Emerging reflective themes will appear here in Phase 2.",
        "themes": [
            "Client's Voice",
            "Observation vs Interpretation",
            "Labels & Language",
            "Possible Bias",
            "Evidence for Decisions",
            "Missing Information",
            "Strengths vs Deficits",
            "Continuity",
        ],
        "section_labels": {
            "client_voice": "Client's Voice",
            "observation_vs_interpretation": "Observation vs Interpretation",
            "labels_and_language": "Labels & Language",
            "possible_bias": "Possible Bias",
            "evidence_for_decisions": "Evidence for Decisions",
            "missing_information": "Missing Information",
            "strengths_and_deficits": "Strengths vs Deficits",
            "continuity": "Continuity",
        },
        "update_document": "Update document",
        "edit_document_label": "Edit the document here if you'd like",
        "submit_no_edit": "Submit without editing",
        "submit_with_edit": "Submit with edits",
        "submitted": "✔ Document submitted",
        "error_parsing": "⚠ Could not process the reflection response. Please try again.",
    }
}

# Priority order everywhere a language list is shown:
# Spanish (default) -> Euskera -> English
LANGUAGE_ORDER = ["Español", "Euskera", "English"]


def get_lang(lang):
    return LANG.get(lang, LANG["Español"])


def init_language():
    # Call at the top of every page. Sets Spanish as default on first
    # load, and renders the sidebar switcher so the choice is visible
    # and persists across pages via st.session_state.
    if "lang" not in st.session_state:
        st.session_state.lang = "Español"

    T = get_lang(st.session_state.lang)

    st.sidebar.selectbox(
        T["language"],
        LANGUAGE_ORDER,
        index=LANGUAGE_ORDER.index(st.session_state.lang),
        key="lang",
    )

    return get_lang(st.session_state.lang)


def render_nav(T):
    # Call on every page (after init_language) to keep the sidebar
    # navigation links visible. Streamlit does not persist sidebar
    # content across pages automatically, so this must be called
    # explicitly on each page file.
    st.sidebar.success(T["nav_header"])
    st.sidebar.page_link("pages/documentation.py", label=T["nav_doc"])
    st.sidebar.page_link("pages/reflection_space.py", label=T["nav_reflection"])
    st.sidebar.page_link("pages/learning.py", label=T["nav_learning"])