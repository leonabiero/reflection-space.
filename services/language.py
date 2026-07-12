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

        # Authentication / identity
        "login_heading": "🔒 Espacio de Reflexión",
        "username": "Usuario",
        "password_label": "Contraseña",
        "login_button": "Iniciar sesión",
        "login_error": "Usuario o contraseña incorrectos.",
        "no_users_configured": "Aún no hay cuentas de usuario configuradas. Añádelas en Configuración → Secretos en Streamlit Cloud.",
        "logout": "Cerrar sesión",
        "role_labels": {
            "Social Worker": "Trabajador/a Social",
            "Supervisor": "Supervisor/a",
            "Programme Manager": "Gestor/a de Programa",
            "System Administrator": "Administrador/a del Sistema",
        },

        # Admin page
        "admin_title": "🔒 Administración",
        "admin_password_label": "Contraseña",
        "admin_enter_button": "Entrar",
        "admin_incorrect_password": "Contraseña incorrecta.",
        "admin_visit_log": "Registro de visitas",
        "admin_no_visits": "Aún no hay visitas registradas.",
        "admin_total_views_label": "vistas totales",
        "admin_clear_log": "Borrar registro",
        "admin_anon_header": "Demostración de anonimización",
        "admin_anon_caption": "Pega cualquier texto de muestra (solo datos ficticios) para ver qué sale del sistema antes de llegar a Claude. Ejecuta la misma función anonymize() utilizada en reflection_service.py.",
        "admin_sample_label": "Texto de muestra (solo datos ficticios)",
        "admin_run_button": "Ejecutar anonimizador",
        "admin_output_label": "Salida anonimizada (lo que se envía a Claude):",
        "admin_table_page": "Página",
        "admin_table_language": "Idioma",
        "admin_table_visited": "Visitado el",
        "admin_sample_default": (
            "El 15/02/2026 la clienta, Sarah Kimani, con número de identificación 9988776655, "
            "asistió a una reunión de seguimiento. Se le puede contactar en +254 722 334 455 "
            "o sarah.kimani@testmail.com. El Sr. David Otieno fue el trabajador social asignado."
        ),
        "learning_preview_caption": "Vista previa — datos ilustrativos, aún no activos",
        "learning_flagged_caption": "Detectado en {count} de las últimas 10 reflexiones",
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

        # Authentication / identity
        "login_heading": "🔒 Hausnarketa Gunea",
        "username": "Erabiltzaile-izena",
        "password_label": "Pasahitza",
        "login_button": "Hasi saioa",
        "login_error": "Erabiltzaile-izena edo pasahitza okerra.",
        "no_users_configured": "Oraindik ez dago erabiltzaile-konturik konfiguratuta. Gehitu Ezarpenak → Sekretuak atalean Streamlit Cloud-en.",
        "logout": "Saioa itxi",
        "role_labels": {
            "Social Worker": "Gizarte Langilea",
            "Supervisor": "Gainbegiralea",
            "Programme Manager": "Programaren Kudeatzailea",
            "System Administrator": "Sistemaren Administratzailea",
        },

        # Admin page
        "admin_title": "🔒 Administrazioa",
        "admin_password_label": "Pasahitza",
        "admin_enter_button": "Sartu",
        "admin_incorrect_password": "Pasahitz okerra.",
        "admin_visit_log": "Bisiten erregistroa",
        "admin_no_visits": "Oraindik ez dago bisitarik erregistratuta.",
        "admin_total_views_label": "ikustaldi guztira",
        "admin_clear_log": "Erregistroa garbitu",
        "admin_anon_header": "Anonimizazio Demoa",
        "admin_anon_caption": "Itsatsi lagin-testu bat (datu faltsuak soilik) sistematik Claude-ra iritsi aurretik zer ateratzen den ikusteko. reflection_service.py fitxategian erabiltzen den anonymize() funtzio bera exekutatzen du.",
        "admin_sample_label": "Lagin-testua (datu faltsuak soilik)",
        "admin_run_button": "Anonimizatzailea exekutatu",
        "admin_output_label": "Irteera anonimizatua (Claude-ra bidaltzen dena):",
        "admin_table_page": "Orria",
        "admin_table_language": "Hizkuntza",
        "admin_table_visited": "Bisitatze data",
        "admin_sample_default": (
            "2026/02/15ean, Sarah Kimani bezeroak, 9988776655 identifikazio-zenbakia duenak, "
            "jarraipen-bilera batera joan zen. +254 722 334 455 zenbakian edo "
            "sarah.kimani@testmail.com helbidean jar daiteke harremanetan. David Otieno jauna "
            "izan zen esleitutako gizarte-langilea."
        ),
        "learning_preview_caption": "Aurrebista — datu ilustragarriak, oraindik ez daude martxan",
        "learning_flagged_caption": "Azken 10 hausnarketetatik {count}-tan identifikatua",
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

        # Authentication / identity
        "login_heading": "🔒 Reflection Space",
        "username": "Username",
        "password_label": "Password",
        "login_button": "Log in",
        "login_error": "Incorrect username or password.",
        "no_users_configured": "No user accounts are configured yet. Add them under Settings → Secrets in Streamlit Cloud.",
        "logout": "Log out",
        "role_labels": {
            "Social Worker": "Social Worker",
            "Supervisor": "Supervisor",
            "Programme Manager": "Programme Manager",
            "System Administrator": "System Administrator",
        },

        # Admin page
        "admin_title": "🔒 Admin",
        "admin_password_label": "Password",
        "admin_enter_button": "Enter",
        "admin_incorrect_password": "Incorrect password.",
        "admin_visit_log": "Visit Log",
        "admin_no_visits": "No visits logged yet.",
        "admin_total_views_label": "total page views",
        "admin_clear_log": "Clear log",
        "admin_anon_header": "Anonymization Demo",
        "admin_anon_caption": "Paste sample text (fake details only) to see what leaves the system before it reaches Claude. Runs the same anonymize() function used in reflection_service.py.",
        "admin_sample_label": "Sample text (fake details only)",
        "admin_run_button": "Run anonymizer",
        "admin_output_label": "Anonymized output (what is sent to Claude):",
        "admin_table_page": "Page",
        "admin_table_language": "Language",
        "admin_table_visited": "Visited at",
        "admin_sample_default": (
            "On 15/02/2026 the client, Sarah Kimani, of ID number 9988776655, "
            "attended a follow-up meeting. She can be reached at "
            "+254 722 334 455 or sarah.kimani@testmail.com. "
            "Mr. David Otieno was the assigned caseworker."
        ),
        "learning_preview_caption": "Preview — illustrative data, not yet live",
        "learning_flagged_caption": "Flagged in {count} of the last 10 reflections",
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
    # Call on every page (after init_identity, before
    # render_identity_footer) to keep the sidebar navigation links
    # visible. Streamlit does not persist sidebar content across pages
    # automatically, so this must be called explicitly on each page file.
    st.sidebar.success(T["nav_header"])
    st.sidebar.page_link("pages/documentation.py", label=T["nav_doc"])
    st.sidebar.page_link("pages/reflection_space.py", label=T["nav_reflection"])

    # Learning dashboard link is only shown for roles it's meant for.
    # NOTE: this hides the link, it does not block direct URL access —
    # real access control still depends on proper authentication, which
    # is now in place via services/identity.py.
    visible_roles = {"Supervisor", "Programme Manager", "System Administrator"}
    current_role = st.session_state.get("user_role", "").strip()
    if current_role in visible_roles:
        st.sidebar.page_link("pages/learning.py", label=T["nav_learning"])