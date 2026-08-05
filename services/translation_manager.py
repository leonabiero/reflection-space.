"""
Translation Manager
====================

Central, standalone engine behind the multilingual system. This module
does NOT replace services/language.py's `LANG` dictionary -- that
dictionary (Español / Euskera / English) remains the single source of
truth for every piece of translated text in the app, exactly as
before. What this module adds on top of it:

  1. STRUCTURAL SYNC -- `sync_missing_keys()` walks the three language
     dictionaries and guarantees they always have the exact same keys
     (including inside nested dicts and lists). If a key was added to
     one language but not the other two (e.g. a future feature that
     only got a Spanish label written for it), this fills the gap
     automatically using Spanish text as a placeholder -- so the app
     never crashes and never shows a blank/broken label, in any
     language, even before anyone gets around to writing the real
     Basque/English translation.

  2. RUNTIME FALLBACK -- `wrap_languages()` returns dict-like objects
     that behave EXACTLY like the plain dicts they wrap (so every
     existing `T["key"]` / `T.get("key", ...)` call site in the app
     keeps working untouched), except that looking up a key that
     somehow still doesn't exist no longer raises a KeyError. Instead
     it follows the required priority order:

         Selected language -> Español (master) -> English -> key name

  3. REPORTING -- `generate_report()` / `render_translation_health_panel()`
     give a human-readable summary of translation completeness, so
     gaps are visible (to a developer via CLI, or to a System
     Administrator inside the app) instead of silently happening.

Language priority for this application (never changes):
    1. Español (Español) -- default / master language
    2. Euskera (Basque)
    3. English

Nothing in this module talks to Streamlit except the optional
`render_translation_health_panel()` helper, so the sync/fallback
engine itself can be imported and unit-tested (or run from the
command line) with no Streamlit runtime required.
"""

from __future__ import annotations

import copy

MASTER_LANGUAGE = "Español"
SECONDARY_LANGUAGE = "English"


# =============================================================================
# 1. Structural comparison helpers
# =============================================================================

def _iter_dict_paths(node, prefix=""):
    """
    Recursively yield dotted key-paths for every entry in a nested
    dict. Lists and plain values are treated as leaves (their own
    completeness -- e.g. list length -- is checked separately in
    `_sync_list`), so this only walks further into nested dicts.
    """
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        yield path
        if isinstance(value, dict):
            yield from _iter_dict_paths(value, path)


def _get_by_path(node, path):
    current = node
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def detect_missing_keys(lang_data, languages, master=MASTER_LANGUAGE):
    """
    Compare every language's dict against the master language (and
    against every other language, so a key present only in e.g.
    Euskera but missing from Español is also surfaced) and return:

        {
          "Euskera": ["some_new_key", "role_labels.some_new_role", ...],
          "English": [...],
        }

    Keys that are missing from the master language itself (i.e. added
    directly to a non-master language, skipping Spanish) are reported
    separately as `extra_in_language` in the same shape, since Spanish
    must always stay authoritative.
    """
    all_paths = set()
    for lang in languages:
        all_paths |= set(_iter_dict_paths(lang_data.get(lang, {})))

    missing = {lang: [] for lang in languages}
    for path in sorted(all_paths):
        for lang in languages:
            _, found = _get_by_path(lang_data.get(lang, {}), path)
            if not found:
                missing[lang].append(path)

    return {lang: paths for lang, paths in missing.items() if paths}


def _resolve_fallback_value(path, lang_data, master, secondary):
    """Best available value for `path`: master, then secondary, then None."""
    value, found = _get_by_path(lang_data.get(master, {}), path)
    if found:
        return copy.deepcopy(value), master
    value, found = _get_by_path(lang_data.get(secondary, {}), path)
    if found:
        return copy.deepcopy(value), secondary
    return None, None


def _set_by_path(node, path, value):
    parts = path.split(".")
    current = node
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _sync_lists(lang_data, languages, master, added_report):
    """
    Beyond key existence, make sure list VALUES (e.g. dropdown options
    such as `doc_types`, or theme lists) are the same length across
    languages -- a shorter list in one language would silently drop
    options from that language's dropdown. Missing trailing items are
    padded using the master language's corresponding item.
    """
    def walk(master_node, prefix=""):
        if not isinstance(master_node, dict):
            return
        for key, master_value in master_node.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(master_value, dict):
                walk(master_value, path)
            elif isinstance(master_value, list):
                for lang in languages:
                    if lang == master:
                        continue
                    target_list, found = _get_by_path(lang_data.get(lang, {}), path)
                    if not found or not isinstance(target_list, list):
                        continue
                    if len(target_list) < len(master_value):
                        for idx in range(len(target_list), len(master_value)):
                            target_list.append(copy.deepcopy(master_value[idx]))
                            added_report.append({
                                "language": lang,
                                "path": f"{path}[{idx}]",
                                "source": master,
                            })

    walk(lang_data.get(master, {}))


def sync_missing_keys(lang_data, languages, master=MASTER_LANGUAGE, secondary=SECONDARY_LANGUAGE):
    """
    Mutates `lang_data` IN PLACE so all languages are structurally
    identical, then returns a report of everything that was added.

    This is safe to call every time the app starts: once everything is
    already in sync it is a fast no-op that adds nothing. It only ever
    ADDS missing entries -- it never removes or overwrites existing
    translated text, so real translations already written for Euskera
    or English are always preserved untouched.
    """
    added = []
    missing = detect_missing_keys(lang_data, languages, master=master)

    for lang, paths in missing.items():
        for path in paths:
            value, source = _resolve_fallback_value(path, lang_data, master, secondary)
            if source is None:
                # Not defined anywhere (shouldn't normally happen since
                # `path` came from the union of all languages) -- skip
                # rather than inventing text.
                continue
            _set_by_path(lang_data.setdefault(lang, {}), path, value)
            added.append({"language": lang, "path": path, "source": source})

    _sync_lists(lang_data, languages, master, added)

    return added


# =============================================================================
# 2. Runtime fallback wrapping (Selected -> Español -> English -> key)
# =============================================================================

_missing_key_log = []  # runtime-observed gaps, for the admin health panel


def record_missing_key(language, key):
    entry = (language, key)
    if entry not in _missing_key_log:
        _missing_key_log.append(entry)


def get_missing_keys_log():
    """Keys that were actually requested at runtime and had to fall back."""
    return list(_missing_key_log)


def _humanize_key(key):
    """Last-resort display text when a key exists nowhere at all."""
    return str(key).replace("_", " ").replace(".", " ").strip().capitalize()


class FallbackDict(dict):
    """
    Drop-in replacement for a plain `dict` that never raises KeyError.
    Every existing call site in the app (`T["key"]`, `T.get("key", ...)`,
    `T["role_labels"]["Supervisor"]`, etc.) keeps working exactly as
    before when the key exists. When it doesn't, `__getitem__` (and
    therefore plain `T["key"]` access) resolves it via the fallback
    chain instead of crashing:

        selected language -> Español -> English -> readable key name

    `.get()` is inherited from dict and is unaffected for call sites
    that already pass their own default -- this class only changes
    behaviour for the previously-crashing case of a bare `T["key"]`
    lookup on a genuinely missing key.
    """

    def __init__(self, data, language, fallback_nodes):
        super().__init__(data)
        self._language = language
        self._fallback_nodes = fallback_nodes  # list of raw dicts, priority order

    def __missing__(self, key):
        for node in self._fallback_nodes:
            if isinstance(node, dict) and key in node:
                record_missing_key(self._language, key)
                return node[key]
        record_missing_key(self._language, key)
        return _humanize_key(key)


def _wrap_node(language, node, fallback_nodes):
    """Recursively wrap a language's dict (and nested dicts) so every
    level of nesting gets the same fallback behaviour, not just the
    top level."""
    if not isinstance(node, dict):
        return node
    wrapped = {}
    for key, value in node.items():
        if isinstance(value, dict):
            child_fallbacks = [
                fb[key] for fb in fallback_nodes
                if isinstance(fb, dict) and isinstance(fb.get(key), dict)
            ]
            wrapped[key] = _wrap_node(language, value, child_fallbacks)
        else:
            wrapped[key] = value
    return FallbackDict(wrapped, language, fallback_nodes)


def wrap_languages(lang_data, languages, master=MASTER_LANGUAGE, secondary=SECONDARY_LANGUAGE):
    """
    Build the fallback-aware version of every language in `lang_data`.
    Returns a plain dict: {language_name: FallbackDict(...)}.
    """
    wrapped = {}
    for language in languages:
        fallback_nodes = []
        if language != master:
            fallback_nodes.append(lang_data.get(master, {}))
        if language != secondary:
            fallback_nodes.append(lang_data.get(secondary, {}))
        wrapped[language] = _wrap_node(language, lang_data.get(language, {}), fallback_nodes)
    return wrapped


# =============================================================================
# 3. Reporting
# =============================================================================

def generate_report(lang_data, languages, sync_result, master=MASTER_LANGUAGE):
    """Human-readable, developer-facing summary. Used by the CLI entry
    point below and by the in-app admin health panel."""
    lines = []
    lines.append("Translation System Health Report")
    lines.append("=" * 33)
    lines.append("")
    lines.append(f"Master language: {master}")
    lines.append(f"Language order: {' -> '.join(languages)}")
    lines.append("")

    for language in languages:
        key_count = len(list(_iter_dict_paths(lang_data.get(language, {}))))
        lines.append(f"  {language}: {key_count} translation entries")

    lines.append("")
    if sync_result:
        lines.append(f"Auto-filled this run ({len(sync_result)} entries):")
        by_lang = {}
        for item in sync_result:
            by_lang.setdefault(item["language"], []).append(item)
        for language, items in by_lang.items():
            lines.append(f"  {language}:")
            for item in items[:25]:
                lines.append(f"    - {item['path']}  (placeholder copied from {item['source']})")
            if len(items) > 25:
                lines.append(f"    ... and {len(items) - 25} more")
    else:
        lines.append("All languages are structurally in sync -- nothing to auto-fill.")

    runtime_missing = get_missing_keys_log()
    lines.append("")
    if runtime_missing:
        lines.append(f"Keys requested at runtime that needed a fallback ({len(runtime_missing)}):")
        for language, key in runtime_missing[:25]:
            lines.append(f"    - [{language}] {key}")
    else:
        lines.append("No runtime fallback lookups recorded yet this session.")

    return "\n".join(lines)


def scan_codebase_for_missing_keys(root_dir, lang_data, master=MASTER_LANGUAGE):
    """
    Developer maintenance tool: scans every .py file under `root_dir`
    for `T["key"]` / `T.get("key", ...)` references and reports any
    key used in code that isn't defined in the master language dict at
    all (a likely typo, since the runtime fallback can only show
    *something* -- it can't invent a correct translation).

    Not run automatically (it touches the filesystem), but intended to
    be run occasionally during development, e.g.:

        python -m services.translation_manager
    """
    import os
    import re

    pattern = re.compile(r'T(?:_[a-z_]*)?(?:\.get\(\s*|\[\s*)["\']([^"\']+)["\']')
    master_keys = set(_iter_dict_paths(lang_data.get(master, {})))
    used_keys = set()

    for dirpath, _dirnames, filenames in os.walk(root_dir):
        if "/.git" in dirpath or "__pycache__" in dirpath:
            continue
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    contents = fh.read()
            except OSError:
                continue
            for match in pattern.finditer(contents):
                used_keys.add(match.group(1))

    # Keys ending in "_" come from dynamic f-string key construction
    # (e.g. T[f"readiness_category_{category}"]) and can't be resolved
    # statically -- skip those rather than false-flagging them.
    used_keys = {k for k in used_keys if not k.endswith("_")}

    return sorted(used_keys - master_keys)


def render_translation_health_panel(T):
    """
    Optional Streamlit admin panel showing translation completeness.
    Kept intentionally self-contained and defensive (wrapped in a
    try/except by the caller is recommended) so it can never break the
    page that embeds it -- translation health is diagnostic, not
    critical, information.
    """
    import streamlit as st
    from services.language import LANG, LANGUAGE_ORDER

    sync_result = getattr(_this_module_sync_cache, "last_result", [])

    st.caption(T.get(
        "admin_translation_health_caption",
        "Live status of the Español / Euskera / English translation system.",
    ))

    cols = st.columns(len(LANGUAGE_ORDER))
    for col, language in zip(cols, LANGUAGE_ORDER):
        count = len(list(_iter_dict_paths(LANG.get(language, {}))))
        col.metric(language, count)

    if sync_result:
        st.warning(
            T.get(
                "admin_translation_autofilled_warning",
                "{count} translation key(s) were auto-filled with placeholder text on startup.",
            ).format(count=len(sync_result))
        )
        with st.expander(T.get("admin_translation_autofilled_details", "View auto-filled keys"), expanded=False):
            for item in sync_result:
                st.caption(f"[{item['language']}] {item['path']} — {T.get('admin_translation_copied_from', 'copied from')} {item['source']}")
    else:
        st.success(T.get(
            "admin_translation_in_sync",
            "All languages are structurally in sync. Nothing needed auto-filling.",
        ))

    runtime_missing = get_missing_keys_log()
    if runtime_missing:
        with st.expander(
            T.get("admin_translation_runtime_gaps", "⚠️ Keys missing at runtime this session ({count})").format(
                count=len(runtime_missing)
            ),
            expanded=False,
        ):
            for language, key in runtime_missing:
                st.caption(f"[{language}] {key}")


class _this_module_sync_cache:
    """Tiny holder so `render_translation_health_panel` can read the
    result of the sync that ran at import time (set by
    services/language.py right after calling `sync_missing_keys`)."""
    last_result = []


def set_last_sync_result(result):
    _this_module_sync_cache.last_result = result


def get_last_sync_result():
    return _this_module_sync_cache.last_result


if __name__ == "__main__":
    # Manual developer audit: `python -m services.translation_manager`
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from services.language import LANG, LANGUAGE_ORDER  # noqa: E402

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = sync_missing_keys(LANG, LANGUAGE_ORDER)
    print(generate_report(LANG, LANGUAGE_ORDER, result))

    print()
    print("Scanning codebase for keys used in code but undefined in Español...")
    orphan_keys = scan_codebase_for_missing_keys(root, LANG)
    if orphan_keys:
        print(f"  Found {len(orphan_keys)} undefined key(s):")
        for key in orphan_keys:
            print(f"    - {key}")
    else:
        print("  None found -- every key referenced in code is defined.")