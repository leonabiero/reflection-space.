"""
Diagnostic Fingerprint (Phase 2: Issue Tracking)
====================================================

Purpose
---------
Phase 1 built the diagnostic engine: every unexpected error produces
one complete, structured Diagnostic Package. Phase 2.1 (now being
replaced by this module) grouped occurrences into stable "Issues" --
but it did so with an exact-string match on (page, error_type,
message). That's fragile: two occurrences of the exact same bug often
have different messages (a KeyError for a different key, a different
user's id embedded in the text, a slightly different wording from a
retried API call) and would never be recognised as the same issue.

This module builds a DIAGNOSTIC FINGERPRINT instead -- a single stable
identifier for "what kind of problem is this", built from several
signals that stay stable even when the message text or line numbers
change:

    - Root Cause Classification -- a coarse, pattern-based read of
      WHY this class of thing tends to fail (see classify_root_cause).
    - Exception Type -- the plain Python/logical exception type.
    - Operation -- WHERE in our own code this happened: the
      deepest frame that is part of Reflection Space itself (not a
      third-party library), identified by file + function, never by
      line number.
    - Page -- which page/area of the app this happened on.
    - Traceback Signature -- the ordered sequence of (file, function)
      frames within OUR OWN code (never third-party/library frames,
      whose internals change across dependency upgrades and add
      noise), with line numbers and all dynamic content stripped out,
      hashed into a short signature. Two occurrences that took the
      exact same path through our own code produce the exact same
      signature, REGARDLESS of which line each frame was on --
      because line numbers shift constantly between deployments as
      unrelated code changes elsewhere in the same file.

The exception MESSAGE is deliberately never part of the fingerprint --
only ever used for display. Comparing on message text is exactly the
fragile approach this module replaces.

Used by services/error_log.py:_get_or_create_issue, which is the only
caller. Nothing here touches the database.
"""

import hashlib
import re

# ---------------------------------------------------------------------
# Traceback parsing
# ---------------------------------------------------------------------
#
# Standard CPython traceback frame line:
#   File "/mount/src/reflection-space/services/reflection_service.py", line 142, in generate_companion_reflection
_FRAME_RE = re.compile(r'File "([^"]+)", line \d+, in (\S+)')

# Top-level directories that are part of Reflection Space's own code
# (see the repo layout) -- a frame is treated as "our own" if its file
# lives directly under one of these, or is a bare root-level file
# (e.g. config.py, app.py). Everything else (site-packages,
# dist-packages, the Python standard library, Streamlit's own
# internals) is third-party and deliberately excluded: those frames'
# line numbers and even call shapes shift on every dependency upgrade,
# and including them would make the fingerprint LESS stable, not more.
_APP_DIRS = {"services", "rdi", "pages", "navigation", "components", "rdi/companions"}


def _normalize_frame(file_path, func_name):
    """
    Turns one raw traceback frame into a stable, deployment-independent
    identifier, or None if the frame belongs to third-party code.

    '/mount/src/reflection-space/services/reflection_service.py',
    'generate_companion_reflection'
        -> 'services/reflection_service.py:generate_companion_reflection'

    Deliberately keyed on (directory, filename, function) -- NEVER on
    line number, and never on the full absolute path (which differs
    between local dev, Streamlit Cloud, and any future host).
    """
    parts = file_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        # A bare filename with no directory at all -- treat as a
        # root-level app file (e.g. "config.py") only if it's plainly
        # one of ours; otherwise it's unrecognisable and excluded.
        return None
    filename = parts[-1]
    parent_dir = parts[-2]
    if parent_dir in _APP_DIRS:
        return f"{parent_dir}/{filename}:{func_name}"
    # Root-level app files sit directly under the repo root, so their
    # "parent_dir" is whatever the deployment's checkout folder is
    # named (e.g. "reflection-space" or "app") -- not a fixed, known
    # name. Recognise these instead by filename alone, only for the
    # small set of known root-level modules, so we don't accidentally
    # swallow third-party frames whose parent folder we don't
    # recognise either.
    _KNOWN_ROOT_FILES = {"config.py", "app.py", "Home.py"}
    if filename in _KNOWN_ROOT_FILES:
        return f"{filename}:{func_name}"
    return None


def _own_code_frames(traceback_text):
    """
    Returns the ordered list of normalized (see _normalize_frame)
    frames, for ONLY the frames that are part of Reflection Space's
    own code, in the order they appear in the traceback (outermost
    call first, innermost/deepest failure last). Never raises --
    returns [] for empty/unparseable input.
    """
    if not traceback_text:
        return []
    frames = []
    for file_path, func_name in _FRAME_RE.findall(traceback_text):
        normalized = _normalize_frame(file_path, func_name)
        if normalized:
            frames.append(normalized)
    return frames


def normalize_traceback(traceback_text):
    """
    Reduces a full traceback down to a short, stable signature: the
    sequence of our own code's (file, function) frames, joined and
    hashed. Two tracebacks that took the same path through our own
    code -- even on different deployments, different line numbers, or
    with different specific values in the error message -- produce the
    IDENTICAL signature.

    Returns "" if there are no recognisable frames of our own code to
    work with (e.g. no traceback exists, or the failure happened
    entirely inside a third-party call with no app-code frame at all).
    """
    frames = _own_code_frames(traceback_text)
    if not frames:
        return ""
    joined = " > ".join(frames)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def extract_operation(traceback_text, page):
    """
    Identifies WHERE (which function, in our own code) this failure
    happened -- the single most useful "what was running" signal,
    used both as a fingerprint component and as a human-readable
    field. This is the DEEPEST frame that is part of Reflection
    Space's own code (i.e. the closest point in our code to the
    actual failure, even if the traceback continues further into a
    third-party library after that).

    Falls back to a normalized form of `page` (e.g. "reflection_space
    (companion API call)" -> "reflection_space_companion_api_call")
    when no traceback/no recognisable own-code frame exists, so this
    never returns an empty string as long as a page is known.
    """
    frames = _own_code_frames(traceback_text)
    if frames:
        # frames[-1] looks like "services/reflection_service.py:generate_companion_reflection"
        return frames[-1].split(":")[-1]
    if not page:
        return "unknown"
    return re.sub(r"[^a-z0-9]+", "_", page.lower()).strip("_") or "unknown"


# ---------------------------------------------------------------------
# Root cause classification
# ---------------------------------------------------------------------
#
# Deliberately coarser and more technical than
# services/diagnostics.py:categorize_error (which answers "which part
# of the SYSTEM is this?" -- Database, AI/Claude API, etc., for a
# human reading one report). This answers "what KIND of failure is
# this, mechanically?" -- used specifically to make the fingerprint
# recognise the same underlying bug even when it surfaces with
# different messages. Order matters: first match wins, most specific
# checks first.
#
# Quality pass (post-Phase 5): previously most "we don't recognise
# this" occurrences fell through to a single, unhelpful
# "Unclassified error" label -- true even for cases that ARE
# recognisable with a bit more pattern-matching (a developer's own
# "TEST:" exception left in a page, a person testing the "Report a
# problem" widget by typing something like "just testing this",
# ImportError vs. a genuine config problem, authentication vs. plain
# permission failures, etc.). This block adds those specific,
# actionable labels and narrows the final catch-all to "Unknown" --
# reserved ONLY for occurrences that truly don't match anything below.
# Order matters: first match wins, most specific checks first.
_ROOT_CAUSE_RULES = (
    # (match test, label)
    #
    # -- Test traffic, checked first so it's never miscategorised as a
    # real production failure --
    #
    # A developer left a deliberate, self-labelled test exception in
    # the code (see e.g. pages/growth_dashboard.py's
    # `raise Exception("TEST: ...")`, used to verify error capture
    # itself works). Always starts with the literal "TEST:" marker by
    # convention, regardless of the exception type used.
    (lambda et, msg, tb: msg.startswith("test:") or "test:" in msg.split("\n", 1)[0],
     "Developer Test Exception"),
    # A person manually exercising the "Report a problem" widget to
    # confirm it works, rather than reporting a genuine issue -- their
    # own typed description says so (e.g. "just testing", "test
    # report", "testing this feature").
    (lambda et, msg, tb: et == "UserReport" and re.search(r"\btest(ing|s|ed)?\b", msg),
     "Manual Test Exception"),
    (lambda et, msg, tb: et == "UserReport", "User-reported issue (no exception)"),
    # Phase 3 (Reflection Generation): these two error_types always
    # arrive with an explicit root_cause_hint from
    # rdi/orchestrator.py's classify_reflection_failure_root_cause()
    # (below) -- see build_fingerprint's root_cause_hint parameter.
    # This rule is only a defensive fallback for the rare case a
    # caller logs one of these error_types WITHOUT a hint -- labelled
    # by what actually happened (reflection generation failed) rather
    # than the uninformative generic "Unknown".
    (lambda et, msg, tb: et in ("ReflectionGenerationFailed", "PartialReflectionGeneration"),
     "Reflection Generation Failed"),
    # -- Configuration, checked before the generic exception-type
    # rules below, since a KeyError/AttributeError/ImportError whose
    # message clearly points at missing/broken configuration is far
    # more actionable labelled that way than as a bare "missing key"
    # or "import error" --
    (lambda et, msg, tb: (
        ("config" in msg or "environment variable" in msg or "env var" in msg)
        and et in ("KeyError", "AttributeError", "ImportError", "ModuleNotFoundError", "ValueError")
    ) or "not configured" in msg or "misconfigured" in msg or "configuration error" in msg,
     "Configuration Error"),
    (lambda et, msg, tb: et in ("ImportError", "ModuleNotFoundError"), "Import Error"),
    (lambda et, msg, tb: et in ("KeyError",), "Missing key / attribute"),
    (lambda et, msg, tb: et in ("AttributeError",), "Missing attribute / None reference"),
    (lambda et, msg, tb: et in ("TypeError",), "Type mismatch"),
    (lambda et, msg, tb: et in ("ValueError",), "Validation Error"),
    (lambda et, msg, tb: et in ("IndexError",), "Index / bounds error"),
    (lambda et, msg, tb: "jsondecodeerror" in (et or "").lower() or "json" in msg and "pars" in msg, "Response parsing failure"),
    # -- Authentication vs. plain Permission, now kept separate so
    # "wrong/expired credentials" and "logged in but not allowed to do
    # this" no longer share one vague "Permission / authorization
    # failure" label --
    (lambda et, msg, tb: any(
        s in msg for s in (
            "authentication", "unauthorized", "401", "invalid api key",
            "invalid x-api-key", "not authenticated", "login failed",
            "invalid credentials",
        )
    ), "Authentication Error"),
    (lambda et, msg, tb: any(
        s in msg for s in ("permission", "forbidden", "403", "access denied", "insufficient privileges")
    ), "Permission Error"),
    (lambda et, msg, tb: "rate limit" in msg or "429" in msg or "overloaded" in msg, "Rate Limit"),
    (lambda et, msg, tb: "timeout" in msg or "timed out" in msg or "timeout" in (et or "").lower(), "Timeout"),
    (lambda et, msg, tb: "psycopg2" in msg or "psycopg2" in tb or "database" in msg, "Database Error"),
    (lambda et, msg, tb: "connection" in msg or "network" in msg or "connectionerror" in (et or "").lower(), "Network Error"),
)


def classify_root_cause(error_type, message, traceback_text):
    """
    Returns a short, stable Root Cause Classification label (see
    _ROOT_CAUSE_RULES above). Falls back to "Unknown" only when
    nothing above recognises the occurrence. Never raises.
    """
    try:
        et = error_type or ""
        msg = (message or "").lower()
        tb = (traceback_text or "").lower()
        for test, label in _ROOT_CAUSE_RULES:
            if test(et, msg, tb):
                return label
        return "Unknown"
    except Exception:
        return "Unknown"


# ---------------------------------------------------------------------
# Reflection Generation root cause classification (Phase 3)
# ---------------------------------------------------------------------
#
# Reflection Generation (rdi/orchestrator.py) is Claude-API-specific --
# every companion call is the same kind of operation (one Anthropic API
# call), so its failures cluster into a handful of well-known, DOMAIN-
# SPECIFIC causes that the general-purpose classify_root_cause() above
# isn't precise enough to distinguish (it would lump all of these
# together as one generic "AI response parsing or generation failure").
# This is what actually separates:
#   "Reflection Generation Failed -- Anthropic Authentication"
#   "Reflection Generation Failed -- Rate Limit"
#   "Reflection Generation Failed -- Network Timeout"
#   "Reflection Generation Failed -- Invalid Model Response"
#   "Reflection Generation Failed -- Unknown"
# into different issues, while genuinely-the-same cause (regardless of
# WHICH of the 8 companions hit it) stays one issue. Order matters:
# first match wins, most specific checks first.
_REFLECTION_ROOT_CAUSE_RULES = (
    (lambda haystack, has_traceback: any(
        s in haystack for s in ("authentication", "invalid x-api-key", "invalid api key", "unauthorized", "401")
    ), "Anthropic Authentication"),
    (lambda haystack, has_traceback: any(
        s in haystack for s in ("rate limit", "rate_limit", "429", "overloaded")
    ), "Rate Limit"),
    (lambda haystack, has_traceback: any(
        s in haystack for s in ("timeout", "timed out", "connection", "network")
    ), "Network Timeout"),
    # No exception was ever raised (has_traceback is False) -- the API
    # call itself completed, but its response couldn't be parsed into
    # a valid reflection. This is the single most common failure mode
    # in practice (a companion returning malformed/incomplete JSON),
    # so it's checked before falling back to "Unknown".
    (lambda haystack, has_traceback: not has_traceback, "Invalid Model Response"),
)


def classify_reflection_failure_root_cause(error_message, raw_response, traceback_text):
    """
    Phase 3 (Reflection Generation): classifies ONE failed companion
    call into one of a fixed set of Reflection-Generation-specific
    root causes (see _REFLECTION_ROOT_CAUSE_RULES above). Used by
    rdi/orchestrator.py for every failed companion, and the dominant
    cause across all failed companions in one run_reflection() call
    becomes that operation's Root Cause Classification -- see
    build_fingerprint's root_cause_hint parameter below.

    Deliberately never returns anything based on WHICH companion
    failed -- companion identity is not a signal here at all, only the
    error message, the raw response text, and whether a real Python
    exception/traceback exists. Falls back to "Unknown" if nothing
    matches. Never raises.
    """
    try:
        haystack = " ".join(
            str(x).lower() for x in (error_message, raw_response) if x
        )
        has_traceback = bool(traceback_text)
        for test, label in _REFLECTION_ROOT_CAUSE_RULES:
            if test(haystack, has_traceback):
                return label
        return "Unknown"
    except Exception:
        return "Unknown"


# ---------------------------------------------------------------------
# The fingerprint itself
# ---------------------------------------------------------------------
def build_fingerprint(page, error_type, message, traceback_text, root_cause_hint=None):
    """
    The one entry point every caller should use. Combines Root Cause,
    Exception Type, Operation, Page, and the normalized Traceback
    Signature into one stable fingerprint string -- deliberately
    EXCLUDING the exception message, which is the fragile, dynamic
    part that should never decide whether two occurrences are "the
    same issue".

    root_cause_hint: when the caller already knows a more precise Root
    Cause Classification than the generic classify_root_cause() above
    could determine (e.g. rdi/orchestrator.py already ran
    classify_reflection_failure_root_cause() across all 8 companions
    and knows the dominant cause was "Rate Limit"), pass it here and
    it's used as-is instead of re-deriving one generically. This is
    what makes "Different root causes -> Different Issue Numbers, Same
    root cause -> Same Issue Number" work for Reflection Generation
    specifically, without teaching this general-purpose module
    anything about companions or the Anthropic API.

    Returns a dict:
        {
            "fingerprint": str (short stable hash -- the grouping key),
            "root_cause": str (Root Cause Classification, for display),
            "operation": str (for display),
            "traceback_signature": str (for display / debugging),
        }

    Never raises -- if anything here fails, returns a minimal fallback
    fingerprint built only from (page, error_type), which is still far
    better than crashing error logging entirely, though it groups more
    coarsely than usual until the underlying issue is understood.
    """
    try:
        root_cause = root_cause_hint or classify_root_cause(error_type, message, traceback_text)
        operation = extract_operation(traceback_text, page)
        traceback_signature = normalize_traceback(traceback_text)

        raw = "|".join([
            root_cause.strip().lower(),
            (error_type or "").strip().lower(),
            operation.strip().lower(),
            (page or "").strip().lower(),
            traceback_signature,
        ])
        fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

        return {
            "fingerprint": fingerprint,
            "root_cause": root_cause,
            "operation": operation,
            "traceback_signature": traceback_signature,
        }
    except Exception:
        fallback_raw = f"{(page or '').lower()}|{(error_type or '').lower()}"
        return {
            "fingerprint": hashlib.sha256(fallback_raw.encode("utf-8")).hexdigest()[:24],
            "root_cause": root_cause_hint or "Unknown",
            "operation": "unknown",
            "traceback_signature": "",
        }