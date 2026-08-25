import streamlit as st
import streamlit.components.v1 as components

from services.translation_manager import (
    sync_missing_keys,
    wrap_languages,
    set_last_sync_result,
)
from services.locales.es import LANG_ES
from services.locales.eu import LANG_EU
from services.locales.en import LANG_EN

# BCP-47 codes for the <html>/textarea "lang" attribute, so the browser's
# built-in spellchecker uses the right dictionary instead of defaulting to
# English (which is what causes correctly-spelled Spanish/Basque words to
# get red-underlined). Chrome and Firefox ship a Spanish dictionary, but
# neither ships one for Basque -- so for Euskera we turn spellcheck off
# entirely rather than have it flag every word as a false positive.
_BROWSER_LANG_CODES = {"Español": "es", "Euskera": "eu", "English": "en"}
_BROWSER_SPELLCHECK = {"Español": "true", "Euskera": "false", "English": "true"}


def _sync_browser_language(lang_name):
    code = _BROWSER_LANG_CODES.get(lang_name, "es")
    spellcheck = _BROWSER_SPELLCHECK.get(lang_name, "true")

    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;
            const code = "{code}";
            const spellcheck = "{spellcheck}";

            function applyLang() {{
                doc.documentElement.lang = code;
                doc.querySelectorAll(
                    'textarea, input[type="text"], input[type="password"]'
                ).forEach(function(el) {{
                    if (el.lang !== code) el.lang = code;
                    if (el.getAttribute('spellcheck') !== spellcheck) {{
                        el.setAttribute('spellcheck', spellcheck);
                    }}
                }});
            }}

            applyLang();

            // Streamlit re-renders the app on every interaction, which can
            // create fresh textarea/input nodes without these attributes,
            // so keep re-applying whenever the DOM changes.
            if (!doc.__reflectionLangObserverAttached) {{
                const observer = new MutationObserver(applyLang);
                observer.observe(doc.body, {{ childList: true, subtree: true }});
                doc.__reflectionLangObserverAttached = true;
            }}
        }})();
        </script>
        """,
        height=0,
    )


LANG = {
    "Español": LANG_ES,
    "Euskera": LANG_EU,
    "English": LANG_EN,
}


LANGUAGE_ORDER = ["Español", "Euskera", "English"]

# ---------------------------------------------------------------------------
# Translation system hardening (Translation Manager)
# ---------------------------------------------------------------------------
# On import, make sure the three language dictionaries above are
# structurally identical -- any key present in one language but
# missing from another gets auto-filled with the best available
# fallback text (Español, the master language, is preferred; English
# is the secondary source). This mutates LANG in place, so it only
# ever ADDS missing entries; every real translation already written
# above is preserved untouched. It is a fast no-op once everything is
# already in sync, which is the normal case.
#
# On top of that, `wrap_languages()` builds a fallback-aware version
# of each language dict so that even a key missing from ALL THREE
# dictionaries (e.g. a future typo in a T["..."] call) degrades
# gracefully instead of crashing the app, following the required
# lookup order: selected language -> Español -> English -> key name.
#
# `get_lang()` below returns these wrapped dicts. Every existing call
# site across the app (`T["key"]`, `T.get("key", ...)`, nested lookups
# like `T["role_labels"][role]`) keeps working exactly as before --
# this is purely additive safety, not a change in behaviour for any
# key that already exists.
_SYNC_RESULT = sync_missing_keys(LANG, LANGUAGE_ORDER, master="Español", secondary="English")
set_last_sync_result(_SYNC_RESULT)
_WRAPPED_LANG = wrap_languages(LANG, LANGUAGE_ORDER, master="Español", secondary="English")


def get_lang(lang):
    return _WRAPPED_LANG.get(lang, _WRAPPED_LANG["Español"])


def init_language():
    """
    Single source of truth for the active UI language: st.session_state["lang"].

    ROOT CAUSE of "must pick the language twice" (this revision)
    ------------------------------------------------------------
    This app is pinned to streamlit==1.47.1 (see requirements.txt),
    which predates Streamlit 1.55.0 -- the release that made an
    explicit `key` the SOLE determinant of a widget's identity. Before
    1.55.0, a widget's `label` still counted toward its identity even
    when a `key` was supplied ("limited exceptions", per Streamlit's
    own widget-behaviour docs): if the label differs from the one used
    on the previous render, Streamlit can treat it as a different
    widget and reset it, discarding whatever value the frontend had
    just sent up for that rerun.

    That is exactly what the previous version of this selectbox did:
    its label was `get_lang(st.session_state.lang)["language"]` --
    i.e. it read the language that had JUST changed, so the label
    itself flipped ("Idioma" -> "Language") on the very same rerun
    that carried the newly picked value. Label + key both changing at
    once is precisely the reset case above, so the fresh selection was
    dropped on that run and the dropdown fell back toward its old
    value. Picking again worked because, on that second run, the label
    was already stable (no longer changing), so nothing reset it.

    THE FIX: the selectbox's own `label` argument is now a fixed,
    language-independent string that never changes between reruns --
    its identity now depends on `key="lang"` alone, exactly as
    intended. The live, translated label ("Idioma" / "Hizkuntza" /
    "Language") is still shown, but as a plain `st.sidebar.caption`,
    which is not a stateful widget, so it can change text every run
    with no effect on the selector's identity.

    Belt-and-braces hardening on top of that real fix: `_lang_applied`
    is a single tracker for "which language has the rest of the page
    already been fully rendered with". The moment st.session_state.lang
    no longer matches it, that's a genuine, just-applied language
    change, so we update the tracker (so this can only fire once per
    change -- no rerun loop) and call st.rerun() immediately, from the
    plain script body rather than a widget callback (same pattern
    already used elsewhere in this app, e.g. navigation/router.py).
    That guarantees every part of the page -- not just the sidebar --
    picks up the new translations on the very next paint, with no
    flicker of stale text in between.

    Persistence note: language selection lives only in
    st.session_state["lang"] -- it is the single source of truth, with
    no second/duplicate state variable anywhere else in the app. There
    is also no browser localStorage/cookie sync that writes back into
    Python state; _sync_browser_language() below only sets the <html>
    lang/spellcheck attributes in the DOM, it never reads from or
    overwrites st.session_state, so it cannot race with or clobber a
    freshly picked language.
    """
    if "lang" not in st.session_state:
        st.session_state.lang = "Español"

    # Live, translated label ("Idioma" / "Hizkuntza" / "Language"),
    # shown as a plain caption -- NOT passed as the selectbox's own
    # `label`, so it's free to change every run without resetting the
    # widget below.
    current_label = get_lang(st.session_state.lang)["language"]
    st.sidebar.caption(current_label)

    st.sidebar.selectbox(
        "🌐",  # fixed, language-independent label -- never changes
        LANGUAGE_ORDER,
        key="lang",
        label_visibility="collapsed",
    )

    # One-shot, guarded rerun: fires only on an actual language
    # change, and only once per change (the tracker is updated before
    # rerun() is called), so this cannot loop.
    if st.session_state.get("_lang_applied") != st.session_state.lang:
        st.session_state["_lang_applied"] = st.session_state.lang
        st.rerun()

    _sync_browser_language(st.session_state.lang)

    return get_lang(st.session_state.lang)